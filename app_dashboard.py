import asyncio
import hashlib
import json
import math
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None

from app.logic.fusion_engine import FusionEngine
from app.logic.training_data import generate_training_cases, train_calibration_model
from generate_data import (
    DEVICE_HUMAN_SEPARATION_PROBABILITY,
    DISPLACED_OCCUPANT_PROBABILITY,
    ROOM_HEIGHT_METERS,
    SENSOR_CONTRADICTION_PROBABILITY,
    adjacent_floor_room_id,
    calculate_structural_damage_pct,
    clamp,
    estimate_rssi_dbm,
    floor_from_room_id,
    generate_battery_pct,
    generate_contact_context,
    generate_pedometer_steps,
    generate_room_energy_profile,
    generate_vitals,
    movement_state,
    owns_smartphone,
    owns_smartwatch,
    room_bounds_3d,
    room_setup_from_grid_template,
    should_room_be_occupied,
    should_blackout,
    transitional_location_for_floor,
)


BUILDING_X_RANGE = (0, 36)
BUILDING_Y_RANGE = (0, 24)
BUILDING_Z_RANGE = (0, 18)
FLOOR_Z_LEVELS = (3.2, 6.4, 9.6, 12.8)
ROOM_HALF_WIDTH = 2.15
ROOM_HALF_DEPTH = 2.15
ROOM_HEIGHT = 2.8
BLE_SCANNER_XY = (18.0, 12.0)
BLE_SCANNER_FLOOR = 2
BLE_REFRESH_SECONDS = 2.5
BLE_OVERLAY_TRACE_NAME = "LIVE BLE critical overlay"
BLE_OVERLAY_SERVER_PORT = 8765
CORE_X_RANGE = (16.8, 19.2)
CORE_Y_RANGE = (9.5, 12.0)
ATRIUM_X_RANGE = (25.0, 35.0)
ATRIUM_Y_RANGE = (1.0, 9.5)
VIP_DEVICES = {
    "Shira_Phone": "הפלאפון של שירה - אותר בהצלחה!",
    "AviyaPhone": "הפלאפון של אביה - אותר בהצלחה!",
}


def distance_3d(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def xyz_tuple(point):
    return (point["x"], point["y"], point["z"])


def display_name_for_ble_device(raw_name):
    if not raw_name:
        return "Unknown BLE"

    cleaned_name = raw_name.strip()
    return VIP_DEVICES.get(cleaned_name, cleaned_name)


def room_dimensions(room):
    if "dimensions" in room:
        return room["dimensions"]

    name = room["room_name"].lower()
    if "living" in name or "main" in name:
        return {"width": 5.8, "depth": 5.2, "height": 2.8}
    if "kitchen" in name:
        return {"width": 5.0, "depth": 4.5, "height": 2.8}
    if "bedroom" in name:
        return {"width": 5.0, "depth": 4.6, "height": 2.8}
    return {"width": 5.0, "depth": 4.6, "height": 2.8}


def ble_distance_from_rssi(rssi, measured_power=-59, path_loss_exponent=2.15):
    rssi = max(-100, min(-35, int(rssi)))
    return 10 ** ((measured_power - rssi) / (10 * path_loss_exponent))


def deterministic_angle(device_key):
    digest = hashlib.sha1(device_key.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 360) * math.pi / 180.0


def live_device_to_map_point(address, rssi, scanner_floor=BLE_SCANNER_FLOOR):
    distance = ble_distance_from_rssi(rssi)
    angle = deterministic_angle(address)
    floor_z = scanner_floor * 3.2
    x = BLE_SCANNER_XY[0] + math.cos(angle) * distance
    y = BLE_SCANNER_XY[1] + math.sin(angle) * distance
    z_jitter = ((int(hashlib.sha1(address.encode("utf-8")).hexdigest()[8:10], 16) / 255.0) - 0.5) * 1.1
    z = floor_z + z_jitter
    return (
        round(clamp(x, BUILDING_X_RANGE[0] + 0.5, BUILDING_X_RANGE[1] - 0.5), 2),
        round(clamp(y, BUILDING_Y_RANGE[0] + 0.5, BUILDING_Y_RANGE[1] - 0.5), 2),
        round(clamp(z, BUILDING_Z_RANGE[0] + 0.5, BUILDING_Z_RANGE[1] - 0.5), 2),
    )


class LiveBleScanner:
    def __init__(self):
        self.lock = threading.Lock()
        self.devices = {}
        self.status = "idle"
        self.error = None
        self.thread = None
        self.stop_event = threading.Event()

    def start(self):
        if BleakScanner is None:
            self.status = "bleak is not installed"
            self.error = "Install bleak to enable live Bluetooth scanning: py -m pip install bleak"
            return
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name="live-ble-scanner", daemon=True)
        self.thread.start()
        self.status = "starting"

    def stop(self):
        self.stop_event.set()
        self.status = "stopping"

    def snapshot(self):
        with self.lock:
            now = time.time()
            fresh_devices = [
                device
                for device in self.devices.values()
                if now - device["last_seen_ts"] <= 20
            ]
            return sorted(fresh_devices, key=lambda item: item["rssi"], reverse=True)

    def _run_loop(self):
        asyncio.run(self._scan_forever())

    async def _scan_forever(self):
        while not self.stop_event.is_set():
            try:
                self.status = "scanning"
                try:
                    discovered = await BleakScanner.discover(timeout=2.0, return_adv=True)
                except TypeError:
                    discovered_list = await BleakScanner.discover(timeout=2.0)
                    discovered = {
                        device.address: (device, None)
                        for device in discovered_list
                    }
                now = time.time()
                updates = {}
                for address, payload in discovered.items():
                    device, advertisement = payload
                    rssi = getattr(advertisement, "rssi", None) if advertisement is not None else None
                    if rssi is None:
                        rssi = getattr(device, "rssi", -90)
                    raw_name = device.name or (getattr(advertisement, "local_name", None) if advertisement is not None else None) or "Unknown BLE"
                    name = display_name_for_ble_device(raw_name)
                    coords = live_device_to_map_point(address, rssi)
                    updates[address] = {
                        "device_id": f"LIVE-{address[-5:].replace(':', '')}",
                        "short_id": address[-5:].replace(":", ""),
                        "name": name,
                        "raw_name": raw_name,
                        "address": address,
                        "rssi": int(rssi),
                        "estimated_coordinates": coords,
                        "last_seen": time.strftime("%H:%M:%S", time.localtime(now)),
                        "last_seen_ts": now,
                    }
                with self.lock:
                    self.devices.update(updates)
                    self.error = None
            except Exception as exc:
                self.status = "scan error"
                self.error = str(exc)
                await asyncio.sleep(2.0)


@st.cache_resource
def get_live_ble_scanner():
    return LiveBleScanner()


def ble_devices_to_plotly_payload(live_devices):
    return {
        "x": [device["estimated_coordinates"][0] for device in live_devices],
        "y": [device["estimated_coordinates"][1] for device in live_devices],
        "z": [device["estimated_coordinates"][2] for device in live_devices],
        "text": [f"LIVE<br>{device.get('name') or device['short_id']}" for device in live_devices],
        "hovertext": [
            (
                f"<b>LIVE BLE DEVICE</b><br>"
                f"Name: {device.get('name') or 'Unknown'}<br>"
                f"Address: {device['address']}<br>"
                f"RSSI: {device['rssi']} dBm<br>"
                f"Estimated: {device['estimated_coordinates']}<br>"
                f"Last seen: {device['last_seen']}"
            )
            for device in live_devices
        ],
        "count": len(live_devices),
        "devices": [
            {
                "name": device.get("name") or "Unknown",
                "raw_name": device.get("raw_name", ""),
                "address": device["address"],
                "rssi_dbm": device["rssi"],
                "estimated_xyz": device["estimated_coordinates"],
                "last_seen": device["last_seen"],
            }
            for device in live_devices
        ],
    }


class BleOverlayRequestHandler(BaseHTTPRequestHandler):
    scanner = None

    def log_message(self, _format, *_args):
        return

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path != "/ble":
            self._send_json(404, {"error": "not found"})
            return

        scanner = self.__class__.scanner
        live_devices = scanner.snapshot() if scanner else []
        self._send_json(
            200,
            {
                **ble_devices_to_plotly_payload(live_devices),
                "scanner_status": scanner.status if scanner else "not started",
                "scanner_floor": BLE_SCANNER_FLOOR,
                "updated_at": time.strftime("%H:%M:%S"),
            },
        )


@st.cache_resource
def start_ble_overlay_server(_scanner):
    BleOverlayRequestHandler.scanner = _scanner
    server = ThreadingHTTPServer(("127.0.0.1", BLE_OVERLAY_SERVER_PORT), BleOverlayRequestHandler)
    thread = threading.Thread(target=server.serve_forever, name="ble-overlay-http", daemon=True)
    thread.start()
    return f"http://127.0.0.1:{BLE_OVERLAY_SERVER_PORT}/ble"


def make_validation_case():
    building_history = {
        "building_id": "B-MACHON-TAL-BEIT-HADFUS-7",
        "site_name": "Machon Tal Campus - Beit HaDfus 7, Jerusalem",
        "year_built": random.choice([1978, 1984, 1994, 2008]),
        "construction_standard": random.choice([
            "Reinforced Academic Campus Block",
            "Legacy-Reinforced-Frame",
            "Post-Structural-Standard-413 Academic Wing",
        ]),
        "primary_materials": random.choice([
            ["Reinforced Concrete Frame", "Concrete Block Interior Walls"],
            ["Aged Reinforced Concrete", "Masonry Infill", "Glass Facade Panels"],
            ["Reinforced Concrete Shear Walls", "Concrete Blocks", "Steel Stair Core"],
        ]),
        "structural_integrity_pre_event": round(clamp(random.gauss(86, 6), 68, 96), 1),
    }

    missile_impact = {
        "missile_type": random.choice(["Heavy Artillery Rocket", "Medium Ballistic Rocket", "Short Range Missile"]),
        "payload_weight_kg": int(round(random.triangular(80, 270, 185))),
        "impact_velocity_mps": int(round(clamp(random.gauss(500, 95), 320, 720))),
        "impact_angle_azimuth_deg": int(random.uniform(0, 360)),
        "impact_angle_elevation_deg": int(clamp(random.gauss(45, 13), 25, 75)),
        "epicenter_coordinates": {
            "x": round(random.uniform(12.0, 28.0), 1),
            "y": round(random.uniform(5.0, 18.0), 1),
            "z": round(random.choice(FLOOR_Z_LEVELS), 1),
        },
        "operational_zone_max_radius_meters": 50.0,
    }

    resident_registry = [
        {"occupant_id": "DT-101-A", "name": "Yossi Levi", "age": 42, "home_room_id": "R-101", "mobility_index": 1.0},
        {"occupant_id": "DT-102-A", "name": "Abraham Levi", "age": 81, "home_room_id": "R-102", "mobility_index": 0.2},
        {"occupant_id": "DT-201-A", "name": "Noam Cohen", "age": 28, "home_room_id": "R-201", "mobility_index": 1.0},
        {"occupant_id": "DT-202-A", "name": "Michal Cohen", "age": 26, "home_room_id": "R-202", "mobility_index": 1.0},
        {"occupant_id": "DT-301-A", "name": "Emily Cohen", "age": 3, "home_room_id": "R-301", "mobility_index": 0.1},
        {"occupant_id": "DT-302-A", "name": "David Levi", "age": 12, "home_room_id": "R-302", "mobility_index": 1.0},
        {"occupant_id": "DT-401-A", "name": "Tomer Green", "age": 35, "home_room_id": "R-401", "mobility_index": 1.0},
        {"occupant_id": "DT-402-A", "name": "Elena Rostova", "age": 67, "home_room_id": "R-402", "mobility_index": 0.5},
    ]

    room_setup = room_setup_from_grid_template()

    rooms = []
    for room_id, room_info in room_setup.items():
        original = tuple(room_info["orig"])
        damage = calculate_structural_damage_pct(original, missile_impact, building_history)
        z_drop = (damage / 100.0) * random.uniform(0.12, ROOM_HEIGHT_METERS * 0.42)
        lateral_shift = (damage / 100.0) * random.uniform(0.25, 0.95)
        post_x = round(original[0] + lateral_shift, 2)
        post_y = round(original[1] + random.gauss(0, 0.18) * damage / 100.0, 2)
        post_z = round(max(ROOM_HEIGHT_METERS / 2.0, original[2] - z_drop), 2)
        room_name = room_info["name"]
        furniture_type = "Heavy Bed" if "Bedroom" in room_name else "Dining Table"
        creates_void = "Bedroom" in room_name or "Main" in room_name or (damage < 50 and random.random() < 0.5)

        rooms.append({
            "room_id": room_id,
            "room_name": room_name,
            "floor": room_info["floor"],
            "grid_cell": room_info["grid_cell"],
            "dimensions": room_info["dimensions"],
            "bounds": room_bounds_3d(room_info["bounds"], room_info["floor"]),
            "post_collapse_bounds": room_bounds_3d(room_info["bounds"], room_info["floor"], z_center=post_z),
            "original_coordinates": {"x": original[0], "y": original[1], "z": original[2]},
            "post_collapse_coordinates": {
                "x": post_x,
                "y": post_y,
                "z": post_z,
            },
            "structural_damage_pct": damage,
            "heavy_furniture": {"type": furniture_type, "creates_void": creates_void},
        })

    rooms_by_id = {room["room_id"]: room for room in rooms}
    occupant_context = {}
    for resident in resident_registry:
        room = rooms_by_id[resident["home_room_id"]]
        floor = floor_from_room_id(resident["home_room_id"])
        has_phone = owns_smartphone(resident)
        has_watch = owns_smartwatch(resident)
        displaced = random.random() < DISPLACED_OCCUPANT_PROBABILITY
        ghost_phone = has_phone and random.random() < DEVICE_HUMAN_SEPARATION_PROBABILITY
        contradiction = random.random() < SENSOR_CONTRADICTION_PROBABILITY
        actual_location = transitional_location_for_floor(floor) if displaced or ghost_phone else xyz_tuple(room["post_collapse_coordinates"])
        nearest_actual_room = min(
            rooms,
            key=lambda candidate: distance_3d(actual_location, xyz_tuple(candidate["post_collapse_coordinates"])),
        )
        actual_damage = max(room["structural_damage_pct"], nearest_actual_room["structural_damage_pct"])
        blackout = should_blackout(max(actual_damage, room["structural_damage_pct"]))
        occupant_context[resident["occupant_id"]] = {
            "has_phone": has_phone,
            "has_watch": has_watch,
            "displaced": displaced,
            "ghost_phone": ghost_phone,
            "contradiction": contradiction,
            "actual_location": actual_location,
            "actual_damage": actual_damage,
            "blackout": blackout,
        }

    meters = []
    for room in rooms:
        meters.append({
            "meter_id": f"METER-{room['room_id']}",
            "room_id": room["room_id"],
            "history_last_2h_kwh": generate_room_energy_profile(
                room["room_name"],
                should_room_be_occupied(room["room_name"]),
            ),
            "transmitted_last_gasp": room["structural_damage_pct"] > random.gauss(47, 5),
        })

    contacts = []
    cellular = []
    steps_by_occupant = {}
    for resident in resident_registry:
        room = rooms_by_id[resident["home_room_id"]]
        context = occupant_context[resident["occupant_id"]]
        contact = generate_contact_context(resident, room["room_name"])
        if context["displaced"] or context["ghost_phone"]:
            contact["known_at_home"] = False
            contact["going_to_shelter"] = True

        if context["has_phone"] and not (context["blackout"] and random.random() < 0.45):
            steps = 0 if context["ghost_phone"] else generate_pedometer_steps(resident, context["actual_damage"], contact)
            steps_by_occupant[resident["occupant_id"]] = steps
            cellular.append({
                "occupant_id": resident["occupant_id"],
                "device_type": "smartphone",
                "pedometer_5min_pre_event": {"steps": steps, "state": movement_state(steps)},
            })
        else:
            steps_by_occupant[resident["occupant_id"]] = 0

        contacts.append({
            "occupant_id": resident["occupant_id"],
            "emergency_contact_response": contact,
        })

    wifi = []
    for floor in range(1, 5):
        connected = []
        for resident in resident_registry:
            context = occupant_context[resident["occupant_id"]]
            if not context["has_phone"] or context["blackout"]:
                continue

            home_floor = floor_from_room_id(resident["home_room_id"])
            target_floor = 1 if context["contradiction"] and home_floor != 1 else 2 if context["contradiction"] else home_floor
            if target_floor != floor:
                continue

            room = rooms_by_id[resident["home_room_id"]]
            rssi = estimate_rssi_dbm(xyz_tuple(room["original_coordinates"]), room["structural_damage_pct"], floor)
            if random.random() < clamp((rssi + 105.0) / 45.0, 0.08, 0.92):
                connected.append(resident["occupant_id"])
        wifi.append({"router_id": f"WIFI-AP-FL{floor}", "connected_occupants_pre_event": connected})

    ble = []
    ground_truth = {}
    high_risk_residents = sorted(
        resident_registry,
        key=lambda resident: rooms_by_id[resident["home_room_id"]]["structural_damage_pct"],
        reverse=True,
    )
    forced_outlier_ids = {
        resident["occupant_id"]
        for resident in high_risk_residents[:2]
    }
    for resident in resident_registry:
        context = occupant_context[resident["occupant_id"]]
        room = rooms_by_id[resident["home_room_id"]]
        floor = floor_from_room_id(resident["home_room_id"])
        room_origin = xyz_tuple(room["original_coordinates"])
        damage = max(room["structural_damage_pct"], context["actual_damage"])
        vitals = generate_vitals(resident, damage, steps_by_occupant[resident["occupant_id"]])
        rssi = estimate_rssi_dbm(room_origin, damage, floor)
        if context["has_watch"] and not context["blackout"]:
            ble_room_id = adjacent_floor_room_id(resident["home_room_id"]) if context["contradiction"] else resident["home_room_id"]
            ble_room_id = ble_room_id if ble_room_id in rooms_by_id else resident["home_room_id"]
            rssi = estimate_rssi_dbm(xyz_tuple(rooms_by_id[ble_room_id]["original_coordinates"]), damage, floor_from_room_id(ble_room_id))
            if damage >= 70:
                rssi = round(clamp(rssi - random.uniform(4.0, 12.0), -98.0, -45.0), 1)
                vitals["movement_index"] = round(vitals["movement_index"] * random.uniform(0.15, 0.65), 2)
            if context["contradiction"]:
                rssi = round(clamp(rssi + random.uniform(6, 14), -98.0, -45.0), 1)
            if damage >= 82 and random.random() < 0.35:
                vitals["heart_rate_bpm"] = int(clamp(vitals["heart_rate_bpm"] + random.choice([-28, 24, 36]), 38, 168))

            ble.append({
                "occupant_id": resident["occupant_id"],
                "home_room_id": ble_room_id,
                "telemetry": {
                    "rssi_dbm": rssi,
                    "battery_pct": generate_battery_pct(damage),
                    "vital_signs": {
                        "heart_rate_bpm": vitals["heart_rate_bpm"],
                        "movement_index": vitals["movement_index"],
                    },
                },
            })
        ground_truth[resident["occupant_id"]] = generate_ground_truth_location(
            room,
            resident,
            steps_by_occupant[resident["occupant_id"]],
            rssi,
            force_outlier=resident["occupant_id"] in forced_outlier_ids,
        )

    operational_stories = [
        "Initial report: an impact near Machon Tal, Beit HaDfus 7 in Jerusalem damaged the academic wing, stair core, and several lecture spaces. The command post is fusing BIM, smart-meter last-gasp signals, cellular movement, and live Bluetooth detections from the scanning laptop.",
        "Initial report: heavy structural vibration at Beit HaDfus 7 triggered partial ceiling failures around the computer labs and student services wing. Rescue teams are using the live BLE overlay to distinguish real nearby devices from the baseline mock sensor model.",
        "Initial report: debris and concrete attenuation are blocking line-of-sight inside the Machon Tal campus building. The USAR dashboard keeps the existing FusionEngine triage output intact while highlighting live Bluetooth devices as critical red search cues."
    ]

    return {
        "case_name": "Machon Tal Beit HaDfus 7 - Live USAR incident",
        "case_story": random.choice(operational_stories),
        "missile_impact": missile_impact,
        "building_history": building_history,
        "resident_registry": resident_registry,
        "bim": {
            "building_model": {
                "model_type": "machon_tal_academic_block_v1",
                "site_name": "Machon Tal Campus - Beit HaDfus 7, Jerusalem",
                "floor_height_m": 3.2,
                "room_height_m": ROOM_HEIGHT_METERS,
                "footprint": {"x_min": 0.0, "x_max": 36.0, "y_min": 0.0, "y_max": 24.0, "z_min": 0.0, "z_max": 18.0},
                "floor_levels_z": list(FLOOR_Z_LEVELS),
            },
            "rooms": rooms,
        },
        "meters": meters,
        "cellular": cellular,
        "wifi": wifi,
        "ble": ble,
        "contacts": contacts,
        "ground_truth": ground_truth,
    }


def generate_ground_truth_location(room, resident, steps, rssi_dbm, force_outlier=False):
    collapsed = xyz_tuple(room["post_collapse_coordinates"])
    damage = room["structural_damage_pct"]
    dims = room_dimensions(room)
    half_width = dims["width"] / 2
    half_depth = dims["depth"] / 2
    half_height = dims["height"] / 2
    movement = clamp(steps / 140.0, 0.0, 1.0)
    poor_signal = 1.0 if rssi_dbm <= -82 else 0.0
    central_probability = clamp(
        0.97
        - damage / 520.0
        - poor_signal * 0.03
        - movement * 0.01
        + (0.03 if room["heavy_furniture"]["creates_void"] else 0.0),
        0.86,
        0.96,
    )

    if (not force_outlier) and random.random() < central_probability:
        x_offset = random.gauss(0, half_width * 0.20)
        y_offset = random.gauss(0, half_depth * 0.20)
        z_offset = random.gauss(0, half_height * 0.16)
    else:
        x_offset = random.uniform(-half_width, half_width)
        y_offset = random.uniform(-half_depth, half_depth)
        z_offset = random.uniform(-half_height * 0.75, half_height * 0.75)
        if force_outlier:
            x_offset = random.choice([-1, 1]) * random.uniform(half_width * 0.9, half_width)
            y_offset = random.choice([-1, 1]) * random.uniform(half_depth * 0.9, half_depth)
            z_offset = random.choice([-1, 1]) * random.uniform(half_height * 0.35, half_height * 0.75)
        elif damage >= 70 or poor_signal:
            if random.random() < 0.55:
                x_offset = random.choice([-1, 1]) * random.uniform(half_width * 0.65, half_width)
            if random.random() < 0.45:
                y_offset = random.choice([-1, 1]) * random.uniform(half_depth * 0.65, half_depth)

    x_offset = clamp(x_offset, -half_width, half_width)
    y_offset = clamp(y_offset, -half_depth, half_depth)
    z_offset = clamp(z_offset, -half_height, half_height)
    return (
        round(clamp(collapsed[0] + x_offset, BUILDING_X_RANGE[0] + 0.5, BUILDING_X_RANGE[1] - 0.5), 2),
        round(clamp(collapsed[1] + y_offset, BUILDING_Y_RANGE[0] + 0.5, BUILDING_Y_RANGE[1] - 0.5), 2),
        round(clamp(collapsed[2] + z_offset, BUILDING_Z_RANGE[0] + 0.4, BUILDING_Z_RANGE[1] - 0.5), 2),
    )


def run_validation_case():
    case = make_validation_case()
    random_state = random.getstate()
    training_cases = generate_training_cases(num_events=50, occupants_per_event=12)
    calibration_model = train_calibration_model(training_cases)
    random.setstate(random_state)
    predictions = FusionEngine(calibration_model=calibration_model).run(case)

    occupants_by_id = {row["occupant_id"]: row for row in case["resident_registry"]}
    ble_by_id = {row["occupant_id"]: row for row in case["ble"]}
    enriched = []

    for prediction in predictions:
        occupant_id = prediction["occupant_id"]
        predicted = tuple(prediction["estimated_coordinates"])
        actual = case["ground_truth"][occupant_id]
        error = distance_3d(predicted, actual)
        ble = ble_by_id.get(occupant_id, {}).get("telemetry", {})
        vitals = ble.get("vital_signs", {})

        enriched.append({
            **prediction,
            "actual_coordinates": actual,
            "prediction_error_m": round(error, 2),
            "heart_rate_bpm": vitals.get("heart_rate_bpm", "אין נתון"),
            "battery_pct": ble.get("battery_pct", "אין נתון"),
            "name": occupants_by_id[occupant_id]["name"],
        })

    avg_error = sum(row["prediction_error_m"] for row in enriched) / len(enriched)
    max_error = max(row["prediction_error_m"] for row in enriched)
    within_2m = sum(1 for row in enriched if row["prediction_error_m"] <= 4.0)

    metrics = {
        "training_cases": len(training_cases),
        "average_error_m": round(avg_error, 2),
        "max_error_m": round(max_error, 2),
        "within_2m_pct": round(within_2m / len(enriched) * 100, 1),
    }
    return case, enriched, metrics


@st.cache_data(ttl=120)
def cached_validation_case():
    return run_validation_case()


def inject_live_ble_overlay(case, live_devices):
    case["live_ble_devices"] = live_devices
    case["live_override_layer"] = {
        "source": "bleak_background_scanner",
        "scanner_coordinates": (BLE_SCANNER_XY[0], BLE_SCANNER_XY[1], BLE_SCANNER_FLOOR * 3.2),
        "device_count": len(live_devices),
        "priority": "overlays base FusionEngine output without mutating mock sensor JSON",
    }
    return case


def add_live_ble_trace(fig, live_devices):
    ble_payload = ble_devices_to_plotly_payload(live_devices)

    fig.add_trace(
        go.Scatter3d(
            x=ble_payload["x"],
            y=ble_payload["y"],
            z=ble_payload["z"],
            mode="markers+text",
            text=ble_payload["text"],
            textposition="top center",
            hovertext=ble_payload["hovertext"],
            hoverinfo="text",
            marker={
                "size": 15,
                "color": "#ef0000",
                "symbol": "circle",
                "opacity": 1.0,
                "line": {"color": "#ffffff", "width": 3},
            },
            name=BLE_OVERLAY_TRACE_NAME,
        )
    )


def build_validation_figure(case, rows, live_devices=None):
    fig = go.Figure()
    add_floor_planes(fig)
    add_room_volumes(fig, case["bim"])
    add_building_wireframe(fig)

    pred_x = [row["estimated_coordinates"][0] for row in rows]
    pred_y = [row["estimated_coordinates"][1] for row in rows]
    pred_z = [row["estimated_coordinates"][2] for row in rows]
    actual_x = [row["actual_coordinates"][0] for row in rows]
    actual_y = [row["actual_coordinates"][1] for row in rows]
    actual_z = [row["actual_coordinates"][2] for row in rows]
    urgency = [row["medical_urgency_score"] for row in rows]

    fig.add_trace(
        go.Scatter3d(
            x=pred_x,
            y=pred_y,
            z=pred_z,
            mode="markers+text",
            text=[
                f"{row['occupant_id']}<br>({row['estimated_coordinates'][0]:.1f}, "
                f"{row['estimated_coordinates'][1]:.1f}, {row['estimated_coordinates'][2]:.1f})"
                for row in rows
            ],
            textposition="top center",
            hovertext=[_hover_template(row, "מיקום משוער של המודל") for row in rows],
            hoverinfo="text",
            marker={
                "size": [12 + score * 0.32 for score in urgency],
                "color": urgency,
                "colorscale": [
                    [0.00, "#16a34a"],
                    [0.45, "#22c55e"],
                    [0.65, "#f59e0b"],
                    [0.82, "#f97316"],
                    [1.00, "#dc2626"],
                ],
                "cmin": 0,
                "cmax": 100,
                "opacity": 0.92,
                "line": {"color": "rgba(255,255,255,0.95)", "width": 2},
                "colorbar": {"title": "דחיפות", "ticksuffix": "%"},
            },
            name="מיקומים משוערים",
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=actual_x,
            y=actual_y,
            z=actual_z,
            mode="markers+text",
            text=[f"אמת<br>({x:.1f}, {y:.1f}, {z:.1f})" for x, y, z in zip(actual_x, actual_y, actual_z)],
            textposition="bottom center",
            hovertext=[_hover_template(row, "מיקום חילוץ אמיתי") for row in rows],
            hoverinfo="text",
            marker={
                "size": 8,
                "color": "#22c55e",
                "symbol": "diamond",
                "opacity": 0.95,
                "line": {"color": "#064e3b", "width": 2},
            },
            name="מיקומי אמת",
        )
    )

    for row in rows:
        predicted = row["estimated_coordinates"]
        actual = row["actual_coordinates"]
        fig.add_trace(
            go.Scatter3d(
                x=[predicted[0], actual[0], None],
                y=[predicted[1], actual[1], None],
                z=[predicted[2], actual[2], None],
                mode="lines",
                line={"color": "rgba(15, 23, 42, 0.5)", "width": 3, "dash": "dash"},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter3d(
            x=[BLE_SCANNER_XY[0]],
            y=[BLE_SCANNER_XY[1]],
            z=[BLE_SCANNER_FLOOR * 3.2],
            mode="markers+text",
            text=["Scanner"],
            textposition="bottom center",
            hovertext=["Bluetooth scanning laptop assumed position"],
            hoverinfo="text",
            marker={"size": 9, "color": "#0f172a", "symbol": "square", "opacity": 0.95},
            name="BLE scanner position",
        )
    )
    add_live_ble_trace(fig, live_devices or [])

    fig.update_layout(
        title="Machon Tal Beit HaDfus 7 - Live BLE + Fusion Engine 3D Map",
        height=780,
        paper_bgcolor="#f8fafc",
        plot_bgcolor="#f8fafc",
        font={"family": "Arial, sans-serif", "color": "#0f172a"},
        scene={
            "xaxis": {"title": "ציר X במטרים", "range": list(BUILDING_X_RANGE), "backgroundcolor": "#eef2f7"},
            "yaxis": {"title": "ציר Y במטרים", "range": list(BUILDING_Y_RANGE), "backgroundcolor": "#eef2f7"},
            "zaxis": {"title": "ציר Z במטרים", "range": list(BUILDING_Z_RANGE), "backgroundcolor": "#eef2f7"},
            "aspectmode": "manual",
            "aspectratio": {"x": 1.35, "y": 0.9, "z": 0.72},
            "camera": {"eye": {"x": 1.45, "y": 1.65, "z": 1.05}},
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        legend={"orientation": "h", "y": 0.98, "x": 0.02, "font": {"size": 13}},
        uirevision="machon-tal-static-camera",
    )
    return fig


@st.cache_resource
def cached_static_validation_figure():
    case, rows, _ = cached_validation_case()
    return build_validation_figure(case, rows, live_devices=None)


def figure_with_live_ble_trace(live_devices):
    fig = go.Figure(cached_static_validation_figure().to_dict())
    add_live_ble_trace(fig, live_devices)
    return fig


def render_client_side_ble_map(ble_endpoint):
    fig = go.Figure(cached_static_validation_figure().to_dict())
    html_chart = pio.to_html(
        fig,
        include_plotlyjs="cdn",
        full_html=False,
        div_id="usar_ble_map",
        config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
    )
    endpoint_json = json.dumps(ble_endpoint)
    refresh_ms = int(BLE_REFRESH_SECONDS * 1000)
    trace_name_json = json.dumps(BLE_OVERLAY_TRACE_NAME)
    component_html = f"""
    <div class="ble-shell">
      <div class="ble-toolbar">
        <div><strong>Live BLE devices</strong><span id="ble-count">0</span></div>
        <div><strong>Scanner status</strong><span id="ble-status">starting</span></div>
        <div><strong>Last update</strong><span id="ble-updated">--:--:--</span></div>
      </div>
      {html_chart}
      <div id="ble-table"></div>
    </div>
    <style>
      .ble-shell {{
        direction: ltr;
        font-family: Arial, sans-serif;
        color: #0f172a;
      }}
      .ble-toolbar {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 10px;
      }}
      .ble-toolbar > div {{
        min-width: 0;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-right: 5px solid #0f766e;
        border-radius: 8px;
        padding: 10px 12px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      }}
      .ble-toolbar strong {{
        display: block;
        color: #475569;
        font-size: 13px;
        font-weight: 700;
      }}
      .ble-toolbar span {{
        display: block;
        color: #0f766e;
        font-size: 22px;
        font-weight: 700;
        margin-top: 4px;
      }}
      #ble-table {{
        margin-top: 8px;
        max-height: 190px;
        overflow: auto;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        background: #ffffff;
      }}
      #ble-table table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }}
      #ble-table th, #ble-table td {{
        padding: 8px 10px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
        white-space: nowrap;
      }}
      #ble-table th {{
        position: sticky;
        top: 0;
        background: #f8fafc;
        color: #475569;
      }}
      .ble-new {{
        color: #16a34a;
        font-weight: 700;
      }}
      .ble-live {{
        color: #dc2626;
        font-weight: 700;
      }}
      .ble-lost {{
        color: #64748b;
        font-weight: 700;
      }}
      @media (max-width: 720px) {{
        .ble-toolbar {{ grid-template-columns: 1fr; }}
      }}
    </style>
    <script>
      const BLE_ENDPOINT = {endpoint_json};
      const BLE_REFRESH_MS = {refresh_ms};
      const BLE_TRACE_NAME = {trace_name_json};
      const LOST_TTL_MS = 7000;
      const knownDevices = new Map();

      function escapeHtml(value) {{
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({{
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;",
        }}[char]));
      }}

      function bleTraceIndex() {{
        const graph = document.getElementById("usar_ble_map");
        return graph.data.findIndex((trace) => trace.name === BLE_TRACE_NAME);
      }}

      function renderTable(rows) {{
        const tableHost = document.getElementById("ble-table");
        if (!rows.length) {{
          tableHost.innerHTML = "<table><tbody><tr><td>No live BLE devices detected yet.</td></tr></tbody></table>";
          return;
        }}
        tableHost.innerHTML = `
          <table>
            <thead>
              <tr>
                <th>State</th><th>Name</th><th>Address</th><th>RSSI</th><th>XYZ</th><th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              ${{rows.map((row) => `
                <tr>
                  <td class="ble-${{row.stateClass}}">${{row.state}}</td>
                  <td>${{escapeHtml(row.name)}}</td>
                  <td>${{escapeHtml(row.address)}}</td>
                  <td>${{escapeHtml(row.rssi_dbm)}}</td>
                  <td>${{escapeHtml(row.estimated_xyz.join(", "))}}</td>
                  <td>${{escapeHtml(row.last_seen)}}</td>
                </tr>
              `).join("")}}
            </tbody>
          </table>
        `;
      }}

      async function refreshBleLayer() {{
        const graph = document.getElementById("usar_ble_map");
        if (!graph || !window.Plotly) return;

        try {{
          const response = await fetch(`${{BLE_ENDPOINT}}?t=${{Date.now()}}`, {{ cache: "no-store" }});
          const payload = await response.json();
          const now = Date.now();
          const liveAddresses = new Set(payload.devices.map((device) => device.address));

          payload.devices.forEach((device, index) => {{
            const previous = knownDevices.get(device.address);
            knownDevices.set(device.address, {{
              ...device,
              x: payload.x[index],
              y: payload.y[index],
              z: payload.z[index],
              text: payload.text[index],
              hovertext: payload.hovertext[index],
              lastClientSeen: now,
              firstClientSeen: previous?.firstClientSeen ?? now,
            }});
          }});

          const rows = [];
          const nextX = [];
          const nextY = [];
          const nextZ = [];
          const nextText = [];
          const nextHover = [];
          const nextColor = [];
          const nextSize = [];

          for (const [address, device] of knownDevices.entries()) {{
            const isLive = liveAddresses.has(address);
            const ageMs = now - device.lastClientSeen;
            if (!isLive && ageMs > LOST_TTL_MS) {{
              knownDevices.delete(address);
              continue;
            }}

            const isNew = isLive && now - device.firstClientSeen < BLE_REFRESH_MS * 1.6;
            const state = isLive ? (isNew ? "NEW" : "LIVE") : "LOST";
            const stateClass = isLive ? (isNew ? "new" : "live") : "lost";
            nextX.push(device.x);
            nextY.push(device.y);
            nextZ.push(device.z);
            nextText.push(isLive ? device.text : `LOST<br>${{device.name || "BLE"}}`);
            nextHover.push(isLive ? device.hovertext : `${{device.hovertext}}<br>Status: signal dropped`);
            nextColor.push(isLive ? (isNew ? "#16a34a" : "#ef0000") : "#64748b");
            nextSize.push(isLive ? (isNew ? 18 : 15) : 10);
            rows.push({{ ...device, state, stateClass }});
          }}

          const traceIndex = bleTraceIndex();
          if (traceIndex >= 0) {{
            Plotly.restyle(graph, {{
              x: [nextX],
              y: [nextY],
              z: [nextZ],
              text: [nextText],
              hovertext: [nextHover],
              "marker.color": [nextColor],
              "marker.size": [nextSize],
            }}, [traceIndex]);
          }}

          document.getElementById("ble-count").textContent = payload.count;
          document.getElementById("ble-status").textContent = payload.scanner_status;
          document.getElementById("ble-updated").textContent = payload.updated_at;
          renderTable(rows);
        }} catch (error) {{
          document.getElementById("ble-status").textContent = `overlay error: ${{error.message}}`;
        }}
      }}

      refreshBleLayer();
      window.setInterval(refreshBleLayer, BLE_REFRESH_MS);
    </script>
    """
    components.html(component_html, height=1060, scrolling=True)


def _hover_template(row, title):
    predicted = row["estimated_coordinates"]
    actual = row["actual_coordinates"]
    return (
        f"<span dir='rtl'>"
        f"<b>{title}</b><br>"
        f"<b>לכוד:</b> {row['name']} / {row['occupant_id']}<br>"
        f"<b>מדדים חיים:</b> דופק {row['heart_rate_bpm']} פעימות לדקה, סוללה {row['battery_pct']}%<br>"
        f"<b>מיקום משוער:</b> X={predicted[0]:.2f}, Y={predicted[1]:.2f}, Z={predicted[2]:.2f}<br>"
        f"<b>מיקום חילוץ אמיתי:</b> X={actual[0]:.2f}, Y={actual[1]:.2f}, Z={actual[2]:.2f}<br>"
        f"<b>סטיית מודל:</b> {row['prediction_error_m']:.2f} מטר<br>"
        f"<b>דחיפות רפואית:</b> {row['medical_urgency_score']:.1f}%<br>"
        f"<b>רמת ביטחון:</b> {row['location_confidence']}"
        f"</span>"
    )


def add_building_wireframe(fig):
    x0, x1 = BUILDING_X_RANGE
    y0, y1 = BUILDING_Y_RANGE
    z0, z1 = BUILDING_Z_RANGE
    corners = {
        "000": (x0, y0, z0),
        "100": (x1, y0, z0),
        "110": (x1, y1, z0),
        "010": (x0, y1, z0),
        "001": (x0, y0, z1),
        "101": (x1, y0, z1),
        "111": (x1, y1, z1),
        "011": (x0, y1, z1),
    }
    edges = [
        ("000", "100"), ("100", "110"), ("110", "010"), ("010", "000"),
        ("001", "101"), ("101", "111"), ("111", "011"), ("011", "001"),
        ("000", "001"), ("100", "101"), ("110", "111"), ("010", "011"),
    ]

    for start, end in edges:
        fig.add_trace(
            go.Scatter3d(
                x=[corners[start][0], corners[end][0]],
                y=[corners[start][1], corners[end][1]],
                z=[corners[start][2], corners[end][2]],
                mode="lines",
                line={"color": "rgba(100, 116, 139, 0.32)", "width": 3},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    for x in (CORE_X_RANGE[0], CORE_X_RANGE[1]):
        for y in (CORE_Y_RANGE[0], CORE_Y_RANGE[1]):
            fig.add_trace(
                go.Scatter3d(
                    x=[x, x],
                    y=[y, y],
                    z=[z0, z1],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.42)", "width": 2},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    for x in (ATRIUM_X_RANGE[0], ATRIUM_X_RANGE[1]):
        fig.add_trace(
            go.Scatter3d(
                x=[x, x],
                y=[ATRIUM_Y_RANGE[0], ATRIUM_Y_RANGE[0]],
                z=[z0, z1],
                mode="lines",
                line={"color": "rgba(8, 145, 178, 0.34)", "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )


def add_floor_planes(fig):
    x0, x1 = BUILDING_X_RANGE
    y0, y1 = BUILDING_Y_RANGE
    for z in FLOOR_Z_LEVELS:
        fig.add_trace(
            go.Surface(
                x=[[x0, x1], [x0, x1]],
                y=[[y0, y0], [y1, y1]],
                z=[[z, z], [z, z]],
                opacity=0.055,
                colorscale=[[0, "rgb(148, 163, 184)"], [1, "rgb(148, 163, 184)"]],
                showscale=False,
                hoverinfo="skip",
            )
        )
        for x in range(x0, x1 + 1, 5):
            fig.add_trace(
                go.Scatter3d(
                    x=[x, x],
                    y=[y0, y1],
                    z=[z, z],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.18)", "width": 1},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        for y in range(y0, y1 + 1, 5):
            fig.add_trace(
                go.Scatter3d(
                    x=[x0, x1],
                    y=[y, y],
                    z=[z, z],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.18)", "width": 1},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        for x_range, y_range, color in [
            (CORE_X_RANGE, CORE_Y_RANGE, "rgba(15, 23, 42, 0.36)"),
            (ATRIUM_X_RANGE, ATRIUM_Y_RANGE, "rgba(8, 145, 178, 0.35)"),
        ]:
            fig.add_trace(
                go.Scatter3d(
                    x=[x_range[0], x_range[1], x_range[1], x_range[0], x_range[0]],
                    y=[y_range[0], y_range[0], y_range[1], y_range[1], y_range[0]],
                    z=[z, z, z, z, z],
                    mode="lines",
                    line={"color": color, "width": 3},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def box_vertices(center, half_width=ROOM_HALF_WIDTH, half_depth=ROOM_HALF_DEPTH, height=ROOM_HEIGHT):
    x, y, z = center
    z0 = max(0.0, z - height / 2)
    z1 = z0 + height
    x0, x1 = x - half_width, x + half_width
    y0, y1 = y - half_depth, y + half_depth
    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]


def room_render_bounds(room):
    bounds = room.get("post_collapse_bounds") or room.get("bounds")
    if bounds:
        return bounds

    center = xyz_tuple(room["post_collapse_coordinates"])
    dims = room_dimensions(room)
    x, y, z = center
    return {
        "x_min": x - dims["width"] / 2,
        "x_max": x + dims["width"] / 2,
        "y_min": y - dims["depth"] / 2,
        "y_max": y + dims["depth"] / 2,
        "z_min": max(0.0, z - dims["height"] / 2),
        "z_max": max(0.0, z - dims["height"] / 2) + dims["height"],
    }


def box_vertices_from_bounds(bounds):
    x0, x1 = bounds["x_min"], bounds["x_max"]
    y0, y1 = bounds["y_min"], bounds["y_max"]
    z0, z1 = bounds["z_min"], bounds["z_max"]
    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]


def box_edges(vertices):
    edge_indices = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    x_values = []
    y_values = []
    z_values = []
    for start, end in edge_indices:
        x_values.extend([vertices[start][0], vertices[end][0], None])
        y_values.extend([vertices[start][1], vertices[end][1], None])
        z_values.extend([vertices[start][2], vertices[end][2], None])
    return x_values, y_values, z_values


def add_room_volumes(fig, bim_data):
    for room in bim_data["rooms"]:
        vertices = box_vertices_from_bounds(room_render_bounds(room))
        x, y, z = zip(*vertices)
        damage = room["structural_damage_pct"]
        color = "rgba(220, 38, 38, 0.22)" if damage >= 70 else "rgba(245, 158, 11, 0.17)" if damage >= 45 else "rgba(14, 165, 233, 0.13)"

        fig.add_trace(
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=[0, 0, 0, 1, 2, 4, 5, 6, 4, 5, 1, 2],
                j=[1, 2, 4, 5, 3, 5, 6, 7, 7, 6, 5, 6],
                k=[2, 3, 5, 6, 7, 7, 7, 4, 0, 1, 2, 3],
                color=color,
                opacity=0.45,
                flatshading=True,
                hovertext=(
                    f"<span dir='rtl'><b>{room['room_name']}</b><br>"
                    f"מזהה חדר: {room['room_id']}<br>"
                    f"נזק מבני: {damage}%</span>"
                ),
                hoverinfo="text",
                showlegend=False,
            )
        )
        edge_x, edge_y, edge_z = box_edges(vertices)
        fig.add_trace(
            go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode="lines",
                line={"color": "rgba(15, 23, 42, 0.38)", "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )


def render_live_ble_fragment():
    scanner = get_live_ble_scanner()
    ble_endpoint = start_ble_overlay_server(scanner)

    if scanner.error:
        st.warning(scanner.error)

    render_client_side_ble_map(ble_endpoint)


def render_dashboard():
    st.set_page_config(page_title="PULSE MAP", page_icon="P", layout="wide")
    scanner = get_live_ble_scanner()
    scanner.start()
    case, rows, metrics = cached_validation_case()

    st.markdown(
        """
        <style>
        .stApp {
            direction: rtl;
            text-align: right;
            background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 42%, #e2e8f0 100%);
            color: #0f172a;
        }
        h1, h2, h3, h4, p, div, span, label {
            font-family: Arial, "Noto Sans Hebrew", sans-serif;
        }
        h1 {
            direction: ltr;
            text-align: center;
            color: #0f172a;
            letter-spacing: 0;
            border-bottom: 3px solid #0f766e;
            padding-bottom: 0.45rem;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-right: 5px solid #0f766e;
            border-radius: 8px;
            padding: 0.75rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        }
        [data-testid="stMetricValue"] { color: #0f766e; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("PULSE MAP - Machon Tal Live USAR Demo")
    st.caption("Machon Tal Campus, Beit HaDfus 7, Jerusalem. Mock fusion-engine targets remain intact; live Bluetooth devices are injected as a critical real-time overlay.")

    if scanner.error:
        st.warning(scanner.error)

    with st.expander("Machon Tal campus visual placeholders"):
        photo_1, photo_2, photo_3 = st.columns(3)
        photo_1.file_uploader("Drop exterior photo", type=["png", "jpg", "jpeg"], key="campus_exterior")
        photo_2.file_uploader("Drop floor plan", type=["png", "jpg", "jpeg", "pdf"], key="campus_floor_plan")
        photo_3.file_uploader("Drop 3D rendering", type=["png", "jpg", "jpeg"], key="campus_render")

    st.subheader("חלק א' - תיאור האירוע")
    st.markdown(f"**{case['case_name']}**")
    st.write(case["case_story"])

    impact = case["missile_impact"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("משקל רש״ק", f"{impact['payload_weight_kg']} ק״ג")
    col2.metric("מהירות פגיעה", f"{impact['impact_velocity_mps']} מ׳/ש׳")
    col3.metric("מוקד פגיעה", f"({impact['epicenter_coordinates']['x']}, {impact['epicenter_coordinates']['y']}, {impact['epicenter_coordinates']['z']})")
    col4.metric("מספר דיירים", len(case["resident_registry"]))

    st.divider()
    st.subheader("חלק ב' - עיבוד המערכת")

    processing_stories = [
        "מערכת היתוך המידע מסננת רעשי רקע מאותות ה-BLE ומשלבת נתוני צריכת חשמל (Last-Gasp) כדי לייצר מפת חללי הישרדות תלת-ממדית. המערכת מתעדפת יעדי חילוץ על בסיס דחיפות רפואית.",
        "מתבצע עיבוד בזמן אמת של עשרות אינדיקציות סלולריות קטועות ופינגים מראוטרים מקומיים. מנוע הלוקליזציה מצליב את התשדורות עם שרטוטי המבנה (BIM) להערכת מיקומי הלכודים תחת ההריסות.",
        "ניתוח דפוסי תנועה טרום-הקריסה (Pedometer) והצלבתם עם מודל נזק פיזיקלי. המערכת מחשבת את הסתברות ההישרדות בכל חלל ומפיקה ציוני דחיפות לכוחות הרפואה והחילוץ בשטח.",
        "סינתזת נתוני שטח: שילוב בין דיווחי חירום לבין מדדי דופק שנקלטו משעונים חכמים. המערכת מנכה שגיאות מיקום הנגרמות מחסימות בטון וברזל (Attenuation) ומציגה אזורי חיפוש ממוקדים."
    ]
    st.write(random.choice(processing_stories))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("מקרי אימון היסטוריים", metrics["training_cases"])
    col2.metric("סטייה ממוצעת", f"{metrics['average_error_m']} מ׳")
    col3.metric("סטייה מקסימלית", f"{metrics['max_error_m']} מ׳")
    col4.metric("דיוק עד 2 מטר", f"{metrics['within_2m_pct']}%")

    with st.expander("טבלת תחזיות ואימות"):
        st.dataframe(
            [
                {
                    "שם הלכוד": row["name"],
                    "מזהה": row["occupant_id"],
                    "דחיפות רפואית": row["medical_urgency_score"],
                    "רמת ביטחון": row["location_confidence"],
                    "מיקום משוער": row["estimated_coordinates"],
                    "מיקום חילוץ אמיתי": row["actual_coordinates"],
                    "סטיית מודל במטרים": row["prediction_error_m"],
                    "דופק": row["heart_rate_bpm"],
                    "סוללה": row["battery_pct"],
                }
                for row in rows
            ],
            use_container_width=True,
        )

    st.divider()
    st.subheader("חלק ג' - מפת תלת־ממד אינטראקטיבית")
    st.write(
        "Transparent volumes represent Machon Tal BIM spaces. Mock FusionEngine victims remain color-coded by urgency, "
        "green diamonds show validation truth, and critical red dots show live Bluetooth devices from the scanner."
    )
    render_live_ble_fragment()


if __name__ == "__main__":
    render_dashboard()