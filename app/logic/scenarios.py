from copy import deepcopy
import math


SCENARIOS = {
    "A": {
        "name": "Scenario A - Severe Complex Collapse",
        "story": (
            "A heavy rocket impacts the upper residential floors near the building core. "
            "Multiple rooms lose electricity immediately, the upper floors drop sharply, "
            "and several occupants show weak movement or abnormal vital signs."
        ),
        "payload_weight_kg": 245,
        "impact_velocity_mps": 650,
        "impact_angle_elevation_deg": 38,
        "epicenter_coordinates": {"x": 12.5, "y": 8.0, "z": 12.0},
        "damage_multiplier": 1.35,
        "signal_loss_multiplier": 1.25,
    },
    "B": {
        "name": "Scenario B - Localized Lighter Damage",
        "story": (
            "A smaller impact hits the lower outer side of the structure. "
            "Damage is localized, most infrastructure remains online, and rescue teams "
            "receive cleaner phone, Wi-Fi, and BLE signals."
        ),
        "payload_weight_kg": 85,
        "impact_velocity_mps": 390,
        "impact_angle_elevation_deg": 62,
        "epicenter_coordinates": {"x": 4.5, "y": 5.0, "z": 3.0},
        "damage_multiplier": 0.62,
        "signal_loss_multiplier": 0.65,
    },
}


def available_scenarios():
    return SCENARIOS


def apply_scenario(base_data, scenario_key):
    scenario = SCENARIOS[scenario_key]
    data = deepcopy(base_data)

    data["missile_impact"]["payload_weight_kg"] = scenario["payload_weight_kg"]
    data["missile_impact"]["impact_velocity_mps"] = scenario["impact_velocity_mps"]
    data["missile_impact"]["impact_angle_elevation_deg"] = scenario["impact_angle_elevation_deg"]
    data["missile_impact"]["epicenter_coordinates"] = deepcopy(scenario["epicenter_coordinates"])

    rooms_by_id = {}
    for room in data["bim"]["rooms"]:
        original = room["original_coordinates"]
        dist = _distance_xyz(original, scenario["epicenter_coordinates"])
        payload_factor = scenario["payload_weight_kg"] / 150.0
        raw_damage = (1.0 / (dist + 1.0)) * 350.0 * payload_factor * scenario["damage_multiplier"]
        damage_pct = int(max(8, min(98, raw_damage)))

        z_drop = (damage_pct / 100.0) * max(original["z"] - 0.5, 0.0)
        room["structural_damage_pct"] = damage_pct
        room["post_collapse_coordinates"] = {
            "x": round(original["x"] + damage_pct / 55.0, 2),
            "y": round(original["y"], 2),
            "z": round(max(0.5, original["z"] - z_drop), 2),
        }
        room["heavy_furniture"]["creates_void"] = (
            "Bedroom" in room["room_name"]
            or "Main" in room["room_name"]
            or damage_pct < 45
        )
        rooms_by_id[room["room_id"]] = room

    for meter in data["meters"]:
        room = rooms_by_id[meter["room_id"]]
        meter["transmitted_last_gasp"] = room["structural_damage_pct"] > (38 if scenario_key == "A" else 62)

    for ble in data["ble"]:
        room = rooms_by_id[ble["home_room_id"]]
        damage = room["structural_damage_pct"]
        telemetry = ble["telemetry"]
        vitals = telemetry["vital_signs"]
        telemetry["rssi_dbm"] = round(
            telemetry["rssi_dbm"] - damage * 0.12 * scenario["signal_loss_multiplier"],
            1,
        )
        vitals["heart_rate_bpm"] = int(
            max(45, min(165, vitals["heart_rate_bpm"] + damage * 0.18 * scenario["damage_multiplier"]))
        )
        vitals["movement_index"] = round(
            max(0.0, min(1.0, vitals["movement_index"] - damage * 0.004 * scenario["damage_multiplier"])),
            2,
        )

    return data, scenario


def _distance_xyz(a, b):
    return math.sqrt(
        (a["x"] - b["x"]) ** 2
        + (a["y"] - b["y"]) ** 2
        + (a["z"] - b["z"]) ** 2
    )