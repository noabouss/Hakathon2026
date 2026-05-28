import json
import os
import random


def generate_all_separate_entities():
    print("Generating comprehensive, multi-building baseline configurations for USAR Engine...")

    # הגדרת שם התיקייה באותיות קטנות ויצירתה במידה ולא קיימת
    target_folder = "mock_data"
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"Created directory: '{target_folder}'")

    # ==========================================
    # 1. BUILDING HISTORY (מאגר היסטוריית והנדסת המבנים בשכונה)
    # ==========================================
    building_history = [
        {
            "building_id": "B-BLDG-99",
            "building_name": "Old Residential Block",
            "year_built": 1978,
            "construction_standard": "Pre-Structural-Standard-413",
            "primary_materials": ["Reinforced Concrete Columns", "Unreinforced Hollow Blocks"],
            "structural_integrity_pre_event": 85.0
        },
        {
            "building_id": "B-BLDG-105",
            "building_name": "Modern Residential Tower",
            "year_built": 2015,
            "construction_standard": "Tamam-38-Compliant",
            "primary_materials": ["High-Strength Concrete", "Steel Shear Walls", "Safe Rooms (MAMAD)"],
            "structural_integrity_pre_event": 98.5
        },
        {
            "building_id": "B-BLDG-202",
            "building_name": "Regional Elementary School",
            "year_built": 1995,
            "construction_standard": "Standard-413-Public",
            "primary_materials": ["Precast Concrete Panels", "Steel Trusses"],
            "structural_integrity_pre_event": 90.0
        }
    ]

    # ==========================================
    # 2. RESIDENT REGISTRY (מרשם האוכלוסייה - כולל טלפון וסטטוס שיחה מובנה לכל אדם)
    # ==========================================
    resident_registry = [
        # בניין 99 - הבניין המקורי
        {
            "occupant_id": "OCC-R-101-A",
            "name": "Yossi Levi",
            "age": 42,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-101",
            "mobility_index": 1.0,
            "phone_number": "+972-50-1234567",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 45,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-R-102-A",
            "name": "Grandpa Abraham",
            "age": 81,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-102",
            "mobility_index": 0.2,
            "phone_number": "+972-52-9876543",
            "phone_call_status": {"called": True, "answered": False, "reason": "No Answer / Ringing",
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-R-201-A",
            "name": "Noam Cohen",
            "age": 28,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-201",
            "mobility_index": 1.0,
            "phone_number": "+972-54-1112233",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 12,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-R-202-A",
            "name": "Michal Cohen",
            "age": 26,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-202",
            "mobility_index": 1.0,
            "phone_number": "+972-54-4445566",
            "phone_call_status": {"called": True, "answered": False, "reason": "Line Disconnected Abruptly",
                                  "device_status": "Disconnected"}
        },
        {
            "occupant_id": "OCC-R-301-A",
            "name": "Baby Emily",
            "age": 1,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-301",
            "mobility_index": 0.0,
            "phone_number": "None",  # תינוקת - אין טלפון
            "phone_call_status": {"called": False, "answered": False, "reason": "No Device Registered",
                                  "device_status": "None"}
        },
        {
            "occupant_id": "OCC-R-302-A",
            "name": "David Levi",
            "age": 12,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-302",
            "mobility_index": 1.0,
            "phone_number": "+972-53-7778899",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 120,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-R-401-A",
            "name": "Tomer Green",
            "age": 35,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-401",
            "mobility_index": 1.0,
            "phone_number": "+972-50-5556677",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 5,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-R-402-A",
            "name": "Elena Rostova",
            "age": 67,
            "associated_building": "B-BLDG-99",
            "home_room_id": "R-99-402",
            "mobility_index": 0.5,
            "phone_number": "+972-58-3334455",
            "phone_call_status": {"called": True, "answered": False, "reason": "Destination Unreachable / Dead Zone",
                                  "device_status": "Unreachable"}
        },

        # בניין 105 - מגדל מודרני עם ממ"דים
        {
            "occupant_id": "OCC-105-A",
            "name": "Dana Regev",
            "age": 31,
            "associated_building": "B-BLDG-105",
            "home_room_id": "R-105-101",
            "mobility_index": 1.0,
            "phone_number": "+972-52-6667788",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 95,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-105-B",
            "name": "Eitan Regev",
            "age": 7,
            "associated_building": "B-BLDG-105",
            "home_room_id": "R-105-102-MAMAD",
            "mobility_index": 1.0,
            "phone_number": "+972-55-1239874",
            "phone_call_status": {"called": True, "answered": False, "reason": "Busy", "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-105-C",
            "name": "Miriam Goldstein",
            "age": 75,
            "associated_building": "B-BLDG-105",
            "home_room_id": "R-105-202-MAMAD",
            "mobility_index": 0.4,
            "phone_number": "+972-50-9990011",
            "phone_call_status": {"called": True, "answered": False, "reason": "Device Powered Off",
                                  "device_status": "Off"}
        },

        # בניין 202 - בית ספר יסודי
        {
            "occupant_id": "OCC-202-TEACHER",
            "name": "Sarah Miller (Teacher)",
            "age": 45,
            "associated_building": "B-BLDG-202",
            "home_room_id": "R-202-F2",
            "mobility_index": 1.0,
            "phone_number": "+972-54-7771122",
            "phone_call_status": {"called": True, "answered": True, "call_duration_seconds": 60,
                                  "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-202-STUDENT1",
            "name": "Danielle",
            "age": 10,
            "associated_building": "B-BLDG-202",
            "home_room_id": "R-202-G1",
            "mobility_index": 1.0,
            "phone_number": "+972-50-8883344",
            "phone_call_status": {"called": True, "answered": False, "reason": "No Answer", "device_status": "Active"}
        },
        {
            "occupant_id": "OCC-202-STUDENT2",
            "name": "Roy",
            "age": 9,
            "associated_building": "B-BLDG-202",
            "home_room_id": "R-202-AUD",
            "mobility_index": 1.0,
            "phone_number": "+972-52-4449911",
            "phone_call_status": {"called": True, "answered": False, "reason": "Device Powered Off",
                                  "device_status": "Off"}
        }
    ]

    # Setup המבנים לצורך חישוב ה-BIM הדינמי מראש
    rooms_setup = {
        "R-99-101": {"b_id": "B-BLDG-99", "name": "1st Floor - Living Room", "orig": [5.0, 5.0, 3.0], "safe": False},
        "R-99-102": {"b_id": "B-BLDG-99", "name": "1st Floor - Bedroom", "orig": [5.0, 12.0, 3.0], "safe": False},
        "R-99-201": {"b_id": "B-BLDG-99", "name": "2nd Floor - Living Room", "orig": [5.0, 5.0, 6.0], "safe": False},
        "R-99-202": {"b_id": "B-BLDG-99", "name": "2nd Floor - Bedroom", "orig": [5.0, 12.0, 6.0], "safe": False},
        "R-99-301": {"b_id": "B-BLDG-99", "name": "3rd Floor - Living Room", "orig": [12.0, 5.0, 9.0], "safe": False},
        "R-99-302": {"b_id": "B-BLDG-99", "name": "3rd Floor - Bedroom", "orig": [12.0, 12.0, 9.0], "safe": False},
        "R-99-401": {"b_id": "B-BLDG-99", "name": "4th Floor - Main Room", "orig": [12.0, 5.0, 12.0], "safe": False},
        "R-99-402": {"b_id": "B-BLDG-99", "name": "4th Floor - Kitchen", "orig": [12.0, 12.0, 12.0], "safe": False},

        "R-105-101": {"b_id": "B-BLDG-105", "name": "Apt 1 - Salon", "orig": [4.0, 4.0, 3.0], "safe": False},
        "R-105-102-MAMAD": {"b_id": "B-BLDG-105", "name": "Apt 1 - Safe Room", "orig": [4.0, 10.0, 3.0], "safe": True},
        "R-105-201": {"b_id": "B-BLDG-105", "name": "Apt 2 - Salon", "orig": [4.0, 4.0, 6.0], "safe": False},
        "R-105-202-MAMAD": {"b_id": "B-BLDG-105", "name": "Apt 2 - Safe Room", "orig": [4.0, 10.0, 6.0], "safe": True},

        "R-202-G1": {"b_id": "B-BLDG-202", "name": "Ground Floor - Class 1A", "orig": [10.0, 8.0, 4.0], "safe": False},
        "R-202-AUD": {"b_id": "B-BLDG-202", "name": "Auditorium / Sport Hall", "orig": [18.0, 25.0, 5.0],
                      "safe": False},
        "R-202-F2": {"b_id": "B-BLDG-202", "name": "1st Floor - Teachers Lounge", "orig": [25.0, 8.0, 8.0],
                     "safe": False}
    }

    # ==========================================
    # 3. BUILDING BIM
    # ==========================================
    building_bim = {"buildings": []}
    by_bldg = {}
    for r_id, r_info in rooms_setup.items():
        b_id = r_info["b_id"]
        if b_id not in by_bldg:
            by_bldg[b_id] = []

        dist = ((r_info["orig"][0] - 12.5) ** 2 + (r_info["orig"][1] - 8.0) ** 2 + (
                    r_info["orig"][2] - 12.0) ** 2) ** 0.5
        damage_pct = max(10, min(95, int((1 / (dist + 1)) * 350)))

        if r_info["safe"]:
            damage_pct = max(5, int(damage_pct * 0.2))

        z_drop = (damage_pct / 100.0) * (r_info["orig"][2] - 0.5)

        by_bldg[b_id].append({
            "room_id": r_id,
            "room_name": r_info["name"],
            "is_safe_room": r_info["safe"],
            "original_coordinates": {"x": r_info["orig"][0], "y": r_info["orig"][1], "z": r_info["orig"][2]},
            "post_collapse_coordinates": {
                "x": round(r_info["orig"][0] + (damage_pct / 60.0), 2),
                "y": r_info["orig"][1],
                "z": round(r_info["orig"][2] - z_drop, 2)
            },
            "structural_damage_pct": damage_pct,
            "heavy_furniture": {
                "type": "Heavy Bed" if "Bedroom" in r_info["name"] or "MAMAD" in r_id else "Integrated Desk",
                "creates_void": True if "Bedroom" in r_info["name"] or "MAMAD" in r_id or "Sport" in r_info[
                    "name"] else False
            }
        })

    for b_id, rooms_list in by_bldg.items():
        building_bim["buildings"].append({
            "building_id": b_id,
            "rooms": rooms_list
        })

    # ==========================================
    # 4. MISSILE IMPACT
    # ==========================================
    missile_impact = {
        "missile_type": "Heavy Artillery Rocket",
        "payload_weight_kg": 150,
        "impact_velocity_mps": 450,
        "impact_angle_azimuth_deg": 210,
        "impact_angle_elevation_deg": 45,
        "epicenter_coordinates": {"x": 12.5, "y": 8.0, "z": 12.0},
        "operational_zone_max_radius_meters": 50.0
    }

    # ==========================================
    # 5. SMART METERS HISTORICAL
    # ==========================================
    smart_meters = []
    for b_data in building_bim["buildings"]:
        for room in b_data["rooms"]:
            smart_meters.append({
                "meter_id": f"METER-{room['room_id']}",
                "building_id": b_data["building_id"],
                "room_id": room["room_id"],
                "history_last_2h_kwh": [round(random.uniform(0.1, 1.4), 2) for _ in range(8)],
                "transmitted_last_gasp": True if room["structural_damage_pct"] > 40 else False
            })

    # ==========================================
    # 6. CELLULAR TELEMETRY
    # ==========================================
    steps_presets = {
        "OCC-R-101-A": (92, "Running"), "OCC-R-102-A": (2, "Resting"),
        "OCC-R-201-A": (45, "Walking"), "OCC-R-202-A": (0, "Resting"),
        "OCC-R-301-A": (0, "Resting"), "OCC-R-302-A": (110, "Running"),
        "OCC-R-401-A": (14, "Walking"), "OCC-R-402-A": (5, "Resting"),
        "OCC-105-A": (80, "Running"), "OCC-105-B": (120, "Running"), "OCC-105-C": (4, "Resting"),
        "OCC-202-TEACHER": (60, "Walking"), "OCC-202-STUDENT1": (140, "Running"), "OCC-202-STUDENT2": (5, "Resting")
    }
    cellular_telemetry = []
    for res in resident_registry:
        occ_id = res["occupant_id"]
        cellular_telemetry.append({
            "occupant_id": occ_id,
            "device_type": "smartphone",
            "pedometer_5min_pre_event": {"steps": steps_presets[occ_id][0], "state": steps_presets[occ_id][1]}
        })

    # ==========================================
    # 7. WIFI ROUTERS
    # ==========================================
    wifi_routers = [
        {"router_id": "WIFI-AP-99-FL1", "building_id": "B-BLDG-99",
         "connected_occupants_pre_event": ["OCC-R-101-A", "OCC-R-102-A"]},
        {"router_id": "WIFI-AP-99-FL2", "building_id": "B-BLDG-99",
         "connected_occupants_pre_event": ["OCC-R-201-A", "OCC-R-202-A"]},
        {"router_id": "WIFI-AP-99-FL3", "building_id": "B-BLDG-99",
         "connected_occupants_pre_event": ["OCC-R-301-A", "OCC-R-302-A"]},
        {"router_id": "WIFI-AP-99-FL4", "building_id": "B-BLDG-99",
         "connected_occupants_pre_event": ["OCC-R-401-A", "OCC-R-402-A"]},
        {"router_id": "WIFI-AP-105", "building_id": "B-BLDG-105",
         "connected_occupants_pre_event": ["OCC-105-A", "OCC-105-B", "OCC-105-C"]},
        {"router_id": "WIFI-AP-202", "building_id": "B-BLDG-202",
         "connected_occupants_pre_event": ["OCC-202-TEACHER", "OCC-202-STUDENT1", "OCC-202-STUDENT2"]}
    ]

    # ==========================================
    # 8. BLE ACTIVE SIGNALS
    # ==========================================
    ble_presets = {
        "OCC-R-101-A": {"rssi": -57.2, "hr": 91, "mov": 0.74, "bat": 83},
        "OCC-R-102-A": {"rssi": -56.0, "hr": 94, "mov": 0.05, "bat": 78},
        "OCC-R-201-A": {"rssi": -67.3, "hr": 100, "mov": 0.55, "bat": 45},
        "OCC-R-202-A": {"rssi": -60.9, "hr": 107, "mov": 0.55, "bat": 50},
        "OCC-R-301-A": {"rssi": -66.5, "hr": 114, "mov": 0.38, "bat": 70},
        "OCC-R-302-A": {"rssi": -64.1, "hr": 117, "mov": 0.95, "bat": 58},
        "OCC-R-401-A": {"rssi": -74.4, "hr": 130, "mov": 0.26, "bat": 46},
        "OCC-R-402-A": {"rssi": -67.7, "hr": 124, "mov": 0.10, "bat": 82},
        "OCC-105-A": {"rssi": -52.1, "hr": 110, "mov": 0.80, "bat": 90},
        "OCC-105-B": {"rssi": -48.5, "hr": 125, "mov": 0.90, "bat": 95},
        "OCC-105-C": {"rssi": -85.0, "hr": 88, "mov": 0.02, "bat": 34},
        "OCC-202-TEACHER": {"rssi": -60.0, "hr": 99, "mov": 0.40, "bat": 76},
        "OCC-202-STUDENT1": {"rssi": -55.2, "hr": 140, "mov": 0.98, "bat": 89},
        "OCC-202-STUDENT2": {"rssi": -72.1, "hr": 105, "mov": 0.15, "bat": 62}
    }
    ble_active_signals = []
    for res in resident_registry:
        occ_id = res["occupant_id"]
        info = ble_presets[occ_id]
        ble_active_signals.append({
            "occupant_id": occ_id,
            "associated_building": res["associated_building"],
            "home_room_id": res["home_room_id"],
            "telemetry": {
                "rssi_dbm": info["rssi"],
                "battery_pct": info["bat"],
                "vital_signs": {"heart_rate_bpm": info["hr"], "movement_index": info["mov"]}
            }
        })

    # ==========================================
    # 9. EMERGENCY CONTACTS
    # ==========================================
    responses = {
        "OCC-R-101-A": {"spoke_last_5_mins": True, "known_at_home": False, "going_to_shelter": False},
        "OCC-R-401-A": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": False},
        "OCC-R-302-A": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": True},
        "OCC-105-B": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": True},
        "OCC-202-STUDENT1": {"spoke_last_5_mins": True, "known_at_home": True, "going_to_shelter": True}
    }
    emergency_contacts = []
    for res in resident_registry:
        occ_id = res["occupant_id"]
        response_data = responses.get(occ_id,
                                      {"spoke_last_5_mins": False, "known_at_home": None, "going_to_shelter": False})
        emergency_contacts.append({"occupant_id": occ_id, "emergency_contact_response": response_data})

    # איסוף ושמירה לתוך תיקיית היעד mock_data
    all_files = {
        "missile_impact.json": missile_impact,
        "building_history.json": building_history,
        "resident_registry.json": resident_registry,
        "building_bim.json": building_bim,
        "smart_meters_historical.json": smart_meters,
        "cellular_telemetry.json": cellular_telemetry,
        "wifi_routers.json": wifi_routers,
        "ble_active_signals.json": ble_active_signals,
        "emergency_contacts.json": emergency_contacts
    }

    for filename, content in all_files.items():
        file_path = os.path.join(target_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)

    print(f"[SUCCESS] All 9 expanded multi-building JSON files written into '{target_folder}/' successfully.")


if __name__ == "__main__":
    generate_all_separate_entities()