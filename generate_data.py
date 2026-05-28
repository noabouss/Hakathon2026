import json
import os
import random


def generate_all_separate_entities():
    print("Generating 9 separate comprehensive USAR data files (including Emergency Contacts)...")

    # 1. פגיעת טיל
    missile_impact = {
        "missile_type": "Heavy Artillery Rocket",
        "payload_weight_kg": 150,
        "impact_velocity_mps": 450,
        "impact_angle_azimuth_deg": 210,
        "impact_angle_elevation_deg": 45,
        "epicenter_coordinates": {"x": 12.5, "y": 8.0, "z": 12.0},
        "operational_zone_max_radius_meters": 50.0
    }

    # 2. היסטוריית מבנה
    building_history = {
        "building_id": "B-BLDG-99",
        "year_built": 1978,
        "construction_standard": "Pre-Structural-Standard-413",
        "primary_materials": ["Reinforced Concrete Columns", "Unreinforced Hollow Blocks"],
        "structural_integrity_pre_event": 85.0
    }

    # 3. מרשם תושבים
    resident_registry = [
        {"occupant_id": "OCC-R-101-A", "name": "Yossi Levi", "age": 42, "home_room_id": "R-101", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-102-A", "name": "Grandpa Abraham", "age": 81, "home_room_id": "R-102",
         "mobility_index": 0.2},
        {"occupant_id": "OCC-R-201-A", "name": "Noam Cohen", "age": 28, "home_room_id": "R-201", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-202-A", "name": "Michal Cohen", "age": 26, "home_room_id": "R-202",
         "mobility_index": 1.0},
        {"occupant_id": "OCC-R-301-A", "name": "Baby Emily", "age": 1, "home_room_id": "R-301", "mobility_index": 0.0},
        {"occupant_id": "OCC-R-302-A", "name": "David Levi", "age": 12, "home_room_id": "R-302", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-401-A", "name": "Tomer Green", "age": 35, "home_room_id": "R-401",
         "mobility_index": 1.0},
        {"occupant_id": "OCC-R-402-A", "name": "Elena Rostova", "age": 67, "home_room_id": "R-402",
         "mobility_index": 0.5}
    ]

    rooms_setup = {
        "R-101": {"name": "1st Floor - Living Room", "orig": [5.0, 5.0, 3.0]},
        "R-102": {"name": "1st Floor - Bedroom", "orig": [5.0, 12.0, 3.0]},
        "R-201": {"name": "2nd Floor - Living Room", "orig": [5.0, 5.0, 6.0]},
        "R-202": {"name": "2nd Floor - Bedroom", "orig": [5.0, 12.0, 6.0]},
        "R-301": {"name": "3rd Floor - Living Room", "orig": [12.0, 5.0, 9.0]},
        "R-302": {"name": "3rd Floor - Bedroom", "orig": [12.0, 12.0, 9.0]},
        "R-401": {"name": "4th Floor - Main Room", "orig": [12.0, 5.0, 12.0]},
        "R-402": {"name": "4th Floor - Kitchen", "orig": [12.0, 12.0, 12.0]}
    }

    # 4. BIM
    building_bim = {"rooms": []}
    for r_id, r_info in rooms_setup.items():
        dist = ((r_info["orig"][0] - 12.5) ** 2 + (r_info["orig"][1] - 8.0) ** 2 + (
                    r_info["orig"][2] - 12.0) ** 2) ** 0.5
        damage_pct = max(15, min(95, int((1 / (dist + 1)) * 350)))
        z_drop = (damage_pct / 100.0) * (r_info["orig"][2] - 0.5)

        building_bim["rooms"].append({
            "room_id": r_id,
            "room_name": r_info["name"],
            "original_coordinates": {"x": r_info["orig"][0], "y": r_info["orig"][1], "z": r_info["orig"][2]},
            "post_collapse_coordinates": {"x": round(r_info["orig"][0] + (damage_pct / 50.0), 2),
                                          "y": r_info["orig"][1], "z": round(r_info["orig"][2] - z_drop, 2)},
            "structural_damage_pct": damage_pct,
            "heavy_furniture": {
                "type": "Heavy Bed" if "Bedroom" in r_info["name"] else "Dining Table",
                "creates_void": True if "Bedroom" in r_info["name"] or "Main" in r_info["name"] else False
            }
        })

    # 5. מונים
    smart_meters = []
    for room in building_bim["rooms"]:
        smart_meters.append({
            "meter_id": f"METER-{room['room_id']}",
            "room_id": room["room_id"],
            "history_last_2h_kwh": [round(random.uniform(0.1, 1.2), 2) for _ in range(8)],
            "transmitted_last_gasp": True if room["structural_damage_pct"] > 45 else False
        })

    # 6. סלולר
    cellular_telemetry = []
    steps_presets = {
        "OCC-R-101-A": (92, "Running"), "OCC-R-102-A": (2, "Resting"),
        "OCC-R-201-A": (45, "Walking"), "OCC-R-202-A": (0, "Resting"),
        "OCC-R-301-A": (0, "Resting"), "OCC-R-302-A": (110, "Running"),
        "OCC-R-401-A": (14, "Walking"), "OCC-R-402-A": (5, "Resting")
    }
    for res in resident_registry:
        occ_id = res["occupant_id"]
        cellular_telemetry.append({
            "occupant_id": occ_id,
            "device_type": "smartphone",
            "pedometer_5min_pre_event": {"steps": steps_presets[occ_id][0], "state": steps_presets[occ_id][1]}
        })

    # 7. Wi-Fi
    wifi_routers = [
        {"router_id": "WIFI-AP-FL1", "connected_occupants_pre_event": ["OCC-R-101-A", "OCC-R-102-A"]},
        {"router_id": "WIFI-AP-FL2", "connected_occupants_pre_event": ["OCC-R-201-A", "OCC-R-202-A"]},
        {"router_id": "WIFI-AP-FL3", "connected_occupants_pre_event": ["OCC-R-301-A", "OCC-R-302-A"]},
        {"router_id": "WIFI-AP-FL4", "connected_occupants_pre_event": ["OCC-R-401-A", "OCC-R-402-A"]}
    ]

    # 8. BLE
    ble_active_signals = []
    ble_presets = {
        "OCC-R-101-A": {"mac": "94:21", "rssi": -57.2, "hr": 91, "mov": 0.74, "bat": 83},
        "OCC-R-102-A": {"mac": "27:41", "rssi": -56.0, "hr": 94, "mov": 0.05, "bat": 78},
        "OCC-R-201-A": {"mac": "44:49", "rssi": -67.3, "hr": 100, "mov": 0.55, "bat": 45},
        "OCC-R-202-A": {"mac": "17:74", "rssi": -60.9, "hr": 107, "mov": 0.55, "bat": 50},
        "OCC-R-301-A": {"mac": "22:37", "rssi": -66.5, "hr": 114, "mov": 0.38, "bat": 70},
        "OCC-R-302-A": {"mac": "47:23", "rssi": -64.1, "hr": 117, "mov": 0.95, "bat": 58},
        "OCC-R-401-A": {"mac": "98:49", "rssi": -74.4, "hr": 130, "mov": 0.26, "bat": 46},
        "OCC-R-402-A": {"mac": "59:40", "rssi": -67.7, "hr": 124, "mov": 0.10, "bat": 82}
    }
    for occ_id, info in ble_presets.items():
        home_room = next(res["home_room_id"] for res in resident_registry if res["occupant_id"] == occ_id)
        ble_active_signals.append({
            "occupant_id": occ_id,
            "home_room_id": home_room,
            "telemetry": {
                "rssi_dbm": info["rssi"],
                "battery_pct": info["bat"],
                "vital_signs": {"heart_rate_bpm": info["hr"], "movement_index": info["mov"]}
            }
        })

    # --- 9. אנשי קשר חירום (השכבה החדשה!) ---
    emergency_contacts = []
    responses = {
        "OCC-R-101-A": {"spoke_last_5_mins": True, "known_at_home": False, "going_to_shelter": False},
        "OCC-R-401-A": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": False},
        "OCC-R-302-A": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": True}
    }
    for res in resident_registry:
        occ_id = res["occupant_id"]
        response_data = responses.get(occ_id,
                                      {"spoke_last_5_mins": False, "known_at_home": None, "going_to_shelter": False})
        emergency_contacts.append({"occupant_id": occ_id, "emergency_contact_response": response_data})

    all_files = {
        "missile_impact.json": missile_impact,
        "building_history.json": building_history,
        "resident_registry.json": resident_registry,
        "building_bim.json": building_bim,
        "smart_meters_historical.json": smart_meters,
        "cellular_telemetry.json": cellular_telemetry,
        "wifi_routers.json": wifi_routers,
        "ble_active_signals.json": ble_active_signals,
        "emergency_contacts.json": emergency_contacts  # שמירת הקובץ החדש
    }

    for filename, content in all_files.items():
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)

    print(f"[SUCCESS] All 9 distinct JSON files written successfully.")


if __name__ == "__main__":
    generate_all_separate_entities()