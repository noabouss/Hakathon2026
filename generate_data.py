import json
import random
import math
from datetime import datetime, timedelta

# --- Configuration & Constants ---
IMPACT_TIME = datetime.utcnow()
START_TIME = IMPACT_TIME - timedelta(hours=2)
IMPACT_EPICENTER = {"x": 5.0, "y": 5.0, "z": 12.0}  # Top floor, corner strike
BASE_RSSI = -55
CONCRETE_ATTENUATION = -20  # dB drop per layer of rubble/collapse


def calculate_distance(p1, p2):
    return math.sqrt((p1['x'] - p2['x']) ** 2 + (p1['y'] - p2['y']) ** 2 + (p1['z'] - p2['z']) ** 2)


def generate_building_data():
    building = {
        "building_id": "BLD-ALPHA-01",
        "floors": 4,
        "rooms": []
    }

    # 4 floors, 2 rooms per floor = 8 rooms
    for floor in range(1, 5):
        for room_num in range(1, 3):
            room_id = f"R-{floor}0{room_num}"
            # Base coordinates
            z_min = (floor - 1) * 3.0
            z_max = floor * 3.0
            x_min = (room_num - 1) * 5.0
            x_max = room_num * 5.0
            y_min, y_max = 0.0, 5.0

            # Calculate center point of the room for physics math
            center = {"x": (x_min + x_max) / 2, "y": (y_min + y_max) / 2, "z": (z_min + z_max) / 2}

            # --- SIMULATE LEAN-TO COLLAPSE ---
            distance_to_impact = calculate_distance(center, IMPACT_EPICENTER)

            # If closer to impact, structural failure is higher, z-drop is massive
            collapse_factor = max(0, 1 - (distance_to_impact / 15.0))
            z_shift = - (z_min * collapse_factor * 0.8)  # Up to 80% pancake drop on impact side

            room = {
                "room_id": room_id,
                "floor": floor,
                "original_coordinates": {
                    "x_min": x_min, "x_max": x_max,
                    "y_min": y_min, "y_max": y_max,
                    "z_min": z_min, "z_max": z_max
                },
                "post_collapse_coordinates": {
                    "x_min": x_min + (collapse_factor * 1.5),  # Slight lateral shift outward
                    "x_max": x_max + (collapse_factor * 1.5),
                    "y_min": y_min, "y_max": y_max,
                    "z_min": max(0, z_min + z_shift),  # Can't go below ground (0)
                    "z_max": max(0.5, z_max + z_shift)
                },
                "structural_damage_pct": round(collapse_factor * 100, 2),
                "heavy_furniture": [{"type": "bed", "creates_void": True}]
            }
            building["rooms"].append(room)

    return building


def generate_smart_meters(building_data):
    meters = []
    for room in building_data["rooms"]:
        damage = room["structural_damage_pct"]
        is_destroyed = damage > 40.0

        meter = {
            "meter_id": f"ELEC-{room['room_id']}",
            "room_id": room["room_id"],
            "resource_type": "electricity",
            "transmitted_last_gasp": is_destroyed,
            "last_gasp_timestamp": IMPACT_TIME.isoformat() + "Z" if is_destroyed else None,
            "history": []
        }

        # Generate 15-min intervals leading up to impact
        current_time = START_TIME
        while current_time < IMPACT_TIME:
            consumption = round(random.uniform(0.1, 1.5), 2)
            meter["history"].append({
                "timestamp": current_time.isoformat() + "Z",
                "consumption": consumption
            })
            current_time += timedelta(minutes=15)

        # Post-impact interval (0 consumption if destroyed)
        meter["history"].append({
            "timestamp": current_time.isoformat() + "Z",
            "consumption": 0.0 if is_destroyed else round(random.uniform(0.1, 0.5), 2)
        })
        meters.append(meter)
    return meters


def generate_ble_signals(building_data):
    ble_devices = []
    for room in building_data["rooms"]:
        damage = room["structural_damage_pct"]

        # Calculate signal attenuation based on damage/rubble
        # Healthy signal is -55dBm. Add -20dBm for major collapse.
        attenuation = (damage / 100.0) * CONCRETE_ATTENUATION
        final_rssi = BASE_RSSI + attenuation + random.uniform(-5, 5)  # Add noise

        # Simulate elevated heart rate due to trauma/stress if damage is high
        base_hr = 70
        hr_spike = damage * 0.8

        device = {
            "device_id": f"BLE-MAC-{random.randint(10, 99)}:{random.randint(10, 99)}",
            "occupant_id": f"OCC-{room['room_id']}-A",
            "home_room_id": room["room_id"],
            "device_type": "smartwatch",
            "telemetry": {
                "timestamp": (IMPACT_TIME + timedelta(minutes=5)).isoformat() + "Z",
                "rssi_dbm": round(final_rssi, 1),
                "battery_pct": random.randint(40, 90),
                "vital_signs": {
                    "heart_rate_bpm": int(base_hr + hr_spike + random.randint(-5, 10)),
                    "movement_index": round(max(0.0, 1.0 - (damage / 100.0)), 2)  # Less movement if trapped
                }
            }
        }
        ble_devices.append(device)
    return ble_devices


def main():
    print("Generating USAR Hackathon Data...")

    # 1. Generate Structural BIM Data
    bim_data = generate_building_data()
    with open("building_bim.json", "w") as f:
        json.dump(bim_data, f, indent=2)

    # 2. Generate Smart Meter AMI Data
    meter_data = generate_smart_meters(bim_data)
    with open("smart_meters_historical.json", "w") as f:
        json.dump(meter_data, f, indent=2)

    # 3. Generate BLE Telemetry Data
    ble_data = generate_ble_signals(bim_data)
    with open("ble_active_signals.json", "w") as f:
        json.dump(ble_data, f, indent=2)

    print("Success! Created building_bim.json, smart_meters_historical.json, and ble_active_signals.json")


if __name__ == "__main__":
    main()