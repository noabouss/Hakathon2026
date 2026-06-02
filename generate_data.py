import json
import math
import random


RANDOM_SEED = None
DISPLACED_OCCUPANT_PROBABILITY = 0.30
DEVICE_HUMAN_SEPARATION_PROBABILITY = 0.15
SENSOR_CONTRADICTION_PROBABILITY = 0.10
HIGH_DAMAGE_BLACKOUT_PROBABILITY = 0.25
FLOOR_HEIGHT_METERS = 3.2
ROOM_HEIGHT_METERS = 2.8
BUILDING_FOOTPRINT = {
    "x_min": 0.0,
    "x_max": 36.0,
    "y_min": 0.0,
    "y_max": 24.0,
    "z_min": 0.0,
    "z_max": 18.0,
}


ROOM_GRID_TEMPLATE = {
    "R-101": {
        "name": "Machon Tal Beit HaDfus 7 - Ground Floor Lobby",
        "floor": 1,
        "grid_cell": {"column": 1, "row": 1},
        "bounds": {"x_min": 1.2, "x_max": 12.0, "y_min": 1.0, "y_max": 9.5},
    },
    "R-102": {
        "name": "Machon Tal Beit HaDfus 7 - Security and Entrance Wing",
        "floor": 1,
        "grid_cell": {"column": 2, "row": 1},
        "bounds": {"x_min": 13.5, "x_max": 25.0, "y_min": 1.0, "y_max": 9.5},
    },
    "R-201": {
        "name": "Machon Tal Beit HaDfus 7 - Computer Lab 201",
        "floor": 2,
        "grid_cell": {"column": 1, "row": 1},
        "bounds": {"x_min": 1.2, "x_max": 12.0, "y_min": 1.0, "y_max": 9.5},
    },
    "R-202": {
        "name": "Machon Tal Beit HaDfus 7 - Lecture Hall 202",
        "floor": 2,
        "grid_cell": {"column": 1, "row": 2},
        "bounds": {"x_min": 1.2, "x_max": 17.0, "y_min": 12.0, "y_max": 23.0},
    },
    "R-301": {
        "name": "Machon Tal Beit HaDfus 7 - Faculty Office Wing",
        "floor": 3,
        "grid_cell": {"column": 2, "row": 1},
        "bounds": {"x_min": 13.5, "x_max": 25.0, "y_min": 1.0, "y_max": 9.5},
    },
    "R-302": {
        "name": "Machon Tal Beit HaDfus 7 - Seminar Room 302",
        "floor": 3,
        "grid_cell": {"column": 2, "row": 2},
        "bounds": {"x_min": 18.8, "x_max": 34.8, "y_min": 12.0, "y_max": 23.0},
    },
    "R-401": {
        "name": "Machon Tal Beit HaDfus 7 - Library Reading Area",
        "floor": 4,
        "grid_cell": {"column": 2, "row": 1},
        "bounds": {"x_min": 13.5, "x_max": 34.8, "y_min": 1.0, "y_max": 9.5},
    },
    "R-402": {
        "name": "Machon Tal Beit HaDfus 7 - Student Services Wing",
        "floor": 4,
        "grid_cell": {"column": 2, "row": 2},
        "bounds": {"x_min": 18.8, "x_max": 34.8, "y_min": 12.0, "y_max": 23.0},
    },
}


def clamp(value, low, high):
    return max(low, min(high, value))


def distance_3d(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def sigmoid(value):
    return 1.0 / (1.0 + math.exp(-value))


def room_type_from_name(room_name):
    lower_name = room_name.lower()
    if "bedroom" in lower_name:
        return "bedroom"
    if "kitchen" in lower_name:
        return "kitchen"
    if "living" in lower_name or "main" in lower_name:
        return "living"
    return "general"


def floor_from_room_id(room_id):
    return int(room_id.split("-")[1][0])


def room_center_from_bounds(bounds, floor):
    return [
        round((bounds["x_min"] + bounds["x_max"]) / 2.0, 2),
        round((bounds["y_min"] + bounds["y_max"]) / 2.0, 2),
        round(floor * FLOOR_HEIGHT_METERS, 2),
    ]


def room_dimensions_from_bounds(bounds):
    return {
        "width": round(bounds["x_max"] - bounds["x_min"], 2),
        "depth": round(bounds["y_max"] - bounds["y_min"], 2),
        "height": ROOM_HEIGHT_METERS,
    }


def room_bounds_3d(bounds, floor, z_center=None):
    z = floor * FLOOR_HEIGHT_METERS if z_center is None else z_center
    return {
        "x_min": bounds["x_min"],
        "x_max": bounds["x_max"],
        "y_min": bounds["y_min"],
        "y_max": bounds["y_max"],
        "z_min": round(max(0.0, z - ROOM_HEIGHT_METERS / 2.0), 2),
        "z_max": round(max(0.0, z - ROOM_HEIGHT_METERS / 2.0) + ROOM_HEIGHT_METERS, 2),
    }


def room_setup_from_grid_template():
    return {
        room_id: {
            "name": template["name"],
            "floor": template["floor"],
            "grid_cell": template["grid_cell"],
            "bounds": template["bounds"],
            "orig": room_center_from_bounds(template["bounds"], template["floor"]),
            "dimensions": room_dimensions_from_bounds(template["bounds"]),
        }
        for room_id, template in ROOM_GRID_TEMPLATE.items()
    }


def material_fragility_factor(materials, construction_standard):
    """
    BRIGHT-style damage generation: damage probability is driven by exposure,
    vulnerability, and observed material classes. Masonry infill and pre-code
    buildings receive higher fragility than post-standard reinforced frames.
    """
    text = " ".join(materials + [construction_standard]).lower()
    fragility = 1.0
    if "unreinforced" in text or "hollow blocks" in text:
        fragility += 0.28
    if "pre-structural" in text:
        fragility += 0.22
    if "reinforced concrete" in text:
        fragility -= 0.08
    return clamp(fragility, 0.75, 1.55)


def calculate_structural_damage_pct(room_origin, missile_impact, building_history):
    """
    Non-linear blast falloff inspired by building-damage datasets such as BRIGHT:
    close rooms saturate toward heavy/destroyed classes, while far rooms decay
    exponentially. Payload is cube-root scaled, matching blast similarity laws.
    """
    epicenter = missile_impact["epicenter_coordinates"]
    epicenter_tuple = (epicenter["x"], epicenter["y"], epicenter["z"])
    dist = distance_3d(room_origin, epicenter_tuple)
    payload = missile_impact["payload_weight_kg"]
    integrity = building_history["structural_integrity_pre_event"] / 100.0
    fragility = material_fragility_factor(
        building_history["primary_materials"],
        building_history["construction_standard"],
    )

    scaled_distance = dist / max(payload ** (1.0 / 3.0), 1.0)
    damage_probability = sigmoid((2.8 - scaled_distance) * 1.35)
    vulnerability = (1.0 - integrity) * 0.42 + (fragility - 1.0) * 0.35
    elevation_bonus = 0.08 if abs(room_origin[2] - epicenter_tuple[2]) <= 3.2 else 0.0
    noise = random.gauss(0, 5.5)

    damage = 100.0 * clamp(damage_probability + vulnerability + elevation_bonus, 0.0, 1.0)
    return int(clamp(round(damage + noise), 8, 97))


def generate_room_energy_profile(room_name, occupied_probability):
    """
    ENERTALK and REFIT both contain high-resolution aggregate/appliance traces.
    For this schema we emit eight 15-minute kWh bins, using a log-normal profile:
    residential loads are positive, right-skewed, and appliance bursts create
    short spikes rather than uniform random values.
    """
    room_type = room_type_from_name(room_name)
    base_kw_by_room = {
        "bedroom": 0.18,
        "living": 0.42,
        "kitchen": 0.68,
        "general": 0.28,
    }
    base_kw = base_kw_by_room[room_type]
    occupancy_multiplier = random.uniform(1.25, 2.6) if random.random() < occupied_probability else random.uniform(0.35, 0.9)
    evening_activity = random.uniform(0.85, 1.35)

    profile = []
    appliance_spike_index = random.randrange(8) if room_type in {"kitchen", "living"} and random.random() < 0.45 else None
    for idx in range(8):
        kw = random.lognormvariate(math.log(base_kw * occupancy_multiplier * evening_activity), 0.32)
        if idx == appliance_spike_index:
            kw += random.uniform(0.45, 1.2)
        kwh_15min = kw * 0.25
        profile.append(round(clamp(kwh_15min, 0.03, 1.55), 2))
    return profile


def should_room_be_occupied(room_name):
    room_type = room_type_from_name(room_name)
    probabilities = {
        "bedroom": 0.42,
        "living": 0.68,
        "kitchen": 0.58,
        "general": 0.46,
    }
    return probabilities[room_type]


def movement_state(steps):
    if steps >= 70:
        return "Running"
    if steps >= 12:
        return "Walking"
    return "Resting"


def generate_pedometer_steps(resident, room_damage_pct, contact_context):
    """
    Replaces hardcoded step presets. Steps are correlated with mobility, age,
    shelter intent, and damage. High damage can abruptly stop motion, while
    shelter intent increases pre-collapse movement.
    """
    age = resident["age"]
    mobility = resident["mobility_index"]
    age_factor = 0.55 if age < 5 else 0.75 if age > 75 else 1.0
    shelter_boost = 1.7 if contact_context["going_to_shelter"] else 1.0
    mean_steps = 28.0 * mobility * age_factor * shelter_boost
    steps = random.gauss(mean_steps, 18.0)

    if room_damage_pct >= 80:
        steps *= random.uniform(0.05, 0.55)
    elif room_damage_pct >= 55:
        steps *= random.uniform(0.35, 0.95)

    return int(clamp(round(steps), 0, 145))


def generate_contact_context(resident, room_name):
    room_type = room_type_from_name(room_name)
    mobility = resident["mobility_index"]
    known_at_home_probability = 0.72 if room_type == "bedroom" else 0.48
    shelter_probability = clamp(0.18 + mobility * 0.38, 0.05, 0.74)
    spoke_probability = clamp(0.22 + mobility * 0.25, 0.08, 0.58)

    return {
        "spoke_last_5_mins": random.random() < spoke_probability,
        "known_at_home": random.random() < known_at_home_probability,
        "going_to_shelter": random.random() < shelter_probability,
    }


def estimate_rssi_dbm(room_origin, room_damage_pct, home_floor):
    """
    SODIndoorLoc-style RSSI simulation: log-distance path loss plus attenuation
    from floors, interior walls, and concrete debris. Higher damage therefore
    weakens BLE/WiFi signals in the same direction as the structural model.
    """
    receiver = (0.0, 0.0, 1.5)
    dist = max(distance_3d(room_origin, receiver), 1.0)
    path_loss_exponent = random.uniform(2.0, 2.8)
    wall_loss = random.uniform(3.0, 8.0)
    floor_loss = max(0, home_floor - 1) * random.uniform(5.0, 9.0)
    debris_loss = room_damage_pct * random.uniform(0.10, 0.22)
    noise = random.gauss(0, 3.2)
    tx_at_1m = -43.0
    rssi = tx_at_1m - 10.0 * path_loss_exponent * math.log10(dist) - wall_loss - floor_loss - debris_loss + noise
    return round(clamp(rssi, -96.0, -45.0), 1)


def generate_vitals(resident, room_damage_pct, steps):
    """
    PerHeart-inspired wearable telemetry: heart rate baseline depends on age and
    recent movement, then rises with stress/injury. Movement index drops sharply
    when high damage suggests entrapment or injury.
    """
    age = resident["age"]
    mobility = resident["mobility_index"]
    pediatric_or_elderly = age < 10 or age > 70
    resting_hr = 78 if pediatric_or_elderly else 68
    activity_hr = min(42, steps * 0.22)
    stress_hr = room_damage_pct * random.uniform(0.22, 0.55)
    heart_rate = resting_hr + activity_hr + stress_hr + random.gauss(0, 7)

    if room_damage_pct >= 82 and random.random() < 0.25:
        heart_rate -= random.uniform(25, 45)

    injury_factor = clamp(room_damage_pct / 100.0, 0.0, 1.0)
    movement_index = mobility * (1.0 - injury_factor) * random.uniform(0.15, 0.95)
    if room_damage_pct >= 75:
        movement_index *= random.uniform(0.05, 0.35)

    return {
        "heart_rate_bpm": int(clamp(round(heart_rate), 38, 168)),
        "movement_index": round(clamp(movement_index, 0.0, 1.0), 2),
    }


def generate_battery_pct(room_damage_pct):
    base = random.gauss(72, 18)
    damage_penalty = room_damage_pct * random.uniform(0.03, 0.12)
    return int(clamp(round(base - damage_penalty), 8, 100))


def owns_smartphone(resident):
    """
    Demographic ownership model: infants do not carry phones, elderly residents
    have lower carry probability, and most adults/teens carry one.
    """
    age = resident["age"]
    if age < 6:
        return False
    if age > 75:
        return random.random() < 0.45
    if age > 65:
        return random.random() < 0.70
    return random.random() < 0.92


def owns_smartwatch(resident):
    """
    Wearable ownership is intentionally sparse. Roughly 35-40% of adults/teens
    have BLE watch telemetry; toddlers and most elderly residents do not.
    """
    age = resident["age"]
    if age < 12:
        return False
    if age > 75:
        return random.random() < 0.18
    return random.random() < 0.38


def transitional_location_for_floor(floor):
    """
    Displaced occupants are placed in transitional spaces such as stairwells,
    hallways, or shelter approaches. These latent locations are not written to
    the existing JSON schema, but they drive sensor contradictions and vitals.
    """
    z = floor * FLOOR_HEIGHT_METERS
    candidates = [
        (8.5, 8.5, z),    # central stairwell
        (9.5, 3.2, z),    # corridor toward exit
        (15.2, 8.5, z),   # shelter-side hallway
        (2.8, 8.5, z),    # outer corridor
    ]
    base = random.choice(candidates)
    return (
        round(clamp(base[0] + random.gauss(0, 0.8), BUILDING_FOOTPRINT["x_min"] + 0.5, BUILDING_FOOTPRINT["x_max"] - 0.5), 2),
        round(clamp(base[1] + random.gauss(0, 0.8), BUILDING_FOOTPRINT["y_min"] + 0.5, BUILDING_FOOTPRINT["y_max"] - 0.5), 2),
        round(clamp(base[2] + random.gauss(0, 0.35), BUILDING_FOOTPRINT["z_min"] + 0.5, BUILDING_FOOTPRINT["z_max"] - 0.5), 2),
    )


def home_room_location(room):
    collapsed = room["post_collapse_coordinates"]
    bounds = room.get("post_collapse_bounds") or room.get("bounds")
    if bounds:
        z_min = bounds.get("z_min", collapsed["z"] - ROOM_HEIGHT_METERS / 2.0)
        z_max = bounds.get("z_max", collapsed["z"] + ROOM_HEIGHT_METERS / 2.0)
        return (
            round(clamp(random.gauss(collapsed["x"], room["dimensions"]["width"] * 0.18), bounds["x_min"] + 0.35, bounds["x_max"] - 0.35), 2),
            round(clamp(random.gauss(collapsed["y"], room["dimensions"]["depth"] * 0.18), bounds["y_min"] + 0.35, bounds["y_max"] - 0.35), 2),
            round(clamp(random.gauss(collapsed["z"], ROOM_HEIGHT_METERS * 0.14), z_min + 0.25, z_max - 0.25), 2),
        )

    return (
        round(clamp(collapsed["x"] + random.gauss(0, 0.65), BUILDING_FOOTPRINT["x_min"] + 0.5, BUILDING_FOOTPRINT["x_max"] - 0.5), 2),
        round(clamp(collapsed["y"] + random.gauss(0, 0.65), BUILDING_FOOTPRINT["y_min"] + 0.5, BUILDING_FOOTPRINT["y_max"] - 0.5), 2),
        round(clamp(collapsed["z"] + random.gauss(0, 0.28), BUILDING_FOOTPRINT["z_min"] + 0.5, BUILDING_FOOTPRINT["z_max"] - 0.5), 2),
    )


def nearest_room_damage(location, rooms_by_id):
    nearest_room = min(
        rooms_by_id.values(),
        key=lambda room: distance_3d(
            location,
            tuple(room["post_collapse_coordinates"].values()),
        ),
    )
    return nearest_room["structural_damage_pct"]


def should_blackout(room_damage_pct):
    """
    Catastrophic signal loss is only common in heavy-damage zones, where rebar
    and concrete can block BLE/WiFi and sometimes destroy carried phones.
    """
    if room_damage_pct <= 75:
        return False
    probability = HIGH_DAMAGE_BLACKOUT_PROBABILITY + (room_damage_pct - 75) * 0.012
    return random.random() < clamp(probability, 0.25, 0.60)


def adjacent_floor_room_id(home_room_id):
    floor = floor_from_room_id(home_room_id)
    room_suffix = home_room_id[-2:]
    target_floor = 2 if floor == 1 else floor - 1
    return f"R-{target_floor}{room_suffix}"


def generate_all_separate_entities():
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    print("Generating 9 dynamic USAR data files from dataset-inspired statistical models...")

    missile_impact = {
        "missile_type": random.choice(["Heavy Artillery Rocket", "Medium Ballistic Rocket", "Short Range Missile"]),
        "payload_weight_kg": int(round(random.triangular(80, 260, 150))),
        "impact_velocity_mps": int(round(random.gauss(450, 85))),
        "impact_angle_azimuth_deg": int(random.uniform(0, 360)),
        "impact_angle_elevation_deg": int(clamp(random.gauss(45, 12), 25, 75)),
        "epicenter_coordinates": {
            "x": round(random.uniform(12.0, 28.0), 1),
            "y": round(random.uniform(5.0, 18.0), 1),
            "z": round(random.choice([floor * FLOOR_HEIGHT_METERS for floor in range(1, 5)]), 1),
        },
        "operational_zone_max_radius_meters": 50.0,
    }

    building_history = {
        "building_id": "B-MACHON-TAL-BEIT-HADFUS-7",
        "site_name": "Machon Tal Campus - Beit HaDfus 7, Jerusalem",
        "year_built": 1980,
        "construction_standard": "Reinforced Academic Campus Block",
        "primary_materials": ["Reinforced Concrete Frame", "Concrete Block Interior Walls", "Glass Facade Panels"],
        "structural_integrity_pre_event": round(clamp(random.gauss(86, 6), 68, 96), 1),
    }

    resident_registry = [
        {"occupant_id": "OCC-R-101-A", "name": "Yossi Levi", "age": 42, "home_room_id": "R-101", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-102-A", "name": "Grandpa Abraham", "age": 81, "home_room_id": "R-102", "mobility_index": 0.2},
        {"occupant_id": "OCC-R-201-A", "name": "Noam Cohen", "age": 28, "home_room_id": "R-201", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-202-A", "name": "Michal Cohen", "age": 26, "home_room_id": "R-202", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-301-A", "name": "Baby Emily", "age": 1, "home_room_id": "R-301", "mobility_index": 0.0},
        {"occupant_id": "OCC-R-302-A", "name": "David Levi", "age": 12, "home_room_id": "R-302", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-401-A", "name": "Tomer Green", "age": 35, "home_room_id": "R-401", "mobility_index": 1.0},
        {"occupant_id": "OCC-R-402-A", "name": "Elena Rostova", "age": 67, "home_room_id": "R-402", "mobility_index": 0.5},
    ]

    rooms_setup = room_setup_from_grid_template()

    building_bim = {
        "building_model": {
            "model_type": "machon_tal_academic_block_v1",
            "site_name": "Machon Tal Campus - Beit HaDfus 7, Jerusalem",
            "floor_height_m": FLOOR_HEIGHT_METERS,
            "room_height_m": ROOM_HEIGHT_METERS,
            "footprint": BUILDING_FOOTPRINT,
            "floor_levels_z": [round(floor * FLOOR_HEIGHT_METERS, 1) for floor in range(1, 5)],
            "compatibility_note": "original_coordinates and post_collapse_coordinates remain the fusion-engine anchors.",
        },
        "rooms": [],
    }
    for room_id, room_info in rooms_setup.items():
        original = tuple(room_info["orig"])
        damage_pct = calculate_structural_damage_pct(original, missile_impact, building_history)
        max_sag = ROOM_HEIGHT_METERS * 0.42
        z_drop = (damage_pct / 100.0) * random.uniform(0.12, max_sag)
        lateral_shift = (damage_pct / 100.0) * random.uniform(0.25, 0.95)
        post_x = round(room_info["orig"][0] + lateral_shift, 2)
        post_y = round(room_info["orig"][1] + random.gauss(0, 0.18) * damage_pct / 100.0, 2)
        post_z = round(max(ROOM_HEIGHT_METERS / 2.0, room_info["orig"][2] - z_drop), 2)

        room_name = room_info["name"]
        heavy_type = "Heavy Bed" if "Bedroom" in room_name else "Dining Table"
        creates_void = "Bedroom" in room_name or "Main" in room_name or (damage_pct < 45 and random.random() < 0.45)

        building_bim["rooms"].append({
            "room_id": room_id,
            "room_name": room_name,
            "floor": room_info["floor"],
            "grid_cell": room_info["grid_cell"],
            "dimensions": room_info["dimensions"],
            "bounds": room_bounds_3d(room_info["bounds"], room_info["floor"]),
            "post_collapse_bounds": room_bounds_3d(room_info["bounds"], room_info["floor"], z_center=post_z),
            "original_coordinates": {"x": room_info["orig"][0], "y": room_info["orig"][1], "z": room_info["orig"][2]},
            "post_collapse_coordinates": {
                "x": post_x,
                "y": post_y,
                "z": post_z,
            },
            "structural_damage_pct": damage_pct,
            "heavy_furniture": {
                "type": heavy_type,
                "creates_void": creates_void,
            },
        })

    rooms_by_id = {room["room_id"]: room for room in building_bim["rooms"]}

    occupant_context = {}
    for resident in resident_registry:
        home_room = rooms_by_id[resident["home_room_id"]]
        floor = floor_from_room_id(resident["home_room_id"])
        has_phone = owns_smartphone(resident)
        has_watch = owns_smartwatch(resident)
        displaced = random.random() < DISPLACED_OCCUPANT_PROBABILITY
        ghost_phone = has_phone and random.random() < DEVICE_HUMAN_SEPARATION_PROBABILITY

        actual_location = (
            transitional_location_for_floor(floor)
            if displaced or ghost_phone
            else home_room_location(home_room)
        )
        actual_damage = nearest_room_damage(actual_location, rooms_by_id)
        home_damage = home_room["structural_damage_pct"]
        blackout = should_blackout(max(actual_damage, home_damage))
        contradiction = random.random() < SENSOR_CONTRADICTION_PROBABILITY

        occupant_context[resident["occupant_id"]] = {
            "has_phone": has_phone,
            "has_watch": has_watch,
            "displaced": displaced,
            "ghost_phone": ghost_phone,
            "actual_location": actual_location,
            "actual_damage": actual_damage,
            "blackout": blackout,
            "contradiction": contradiction,
        }

    smart_meters = []
    for room in building_bim["rooms"]:
        occupied_probability = should_room_be_occupied(room["room_name"])
        profile = generate_room_energy_profile(room["room_name"], occupied_probability)
        damage_pct = room["structural_damage_pct"]
        last_gasp_threshold = random.gauss(47, 5)
        smart_meters.append({
            "meter_id": f"METER-{room['room_id']}",
            "room_id": room["room_id"],
            "history_last_2h_kwh": profile,
            "transmitted_last_gasp": True if damage_pct > last_gasp_threshold else False,
        })

    cellular_telemetry = []
    emergency_contacts = []
    contact_context_by_occupant = {}
    for resident in resident_registry:
        room = rooms_by_id[resident["home_room_id"]]
        context = occupant_context[resident["occupant_id"]]
        contact_context = generate_contact_context(resident, room["room_name"])
        if context["displaced"]:
            contact_context["known_at_home"] = False
            contact_context["going_to_shelter"] = True
        if context["ghost_phone"]:
            contact_context["known_at_home"] = False
            contact_context["going_to_shelter"] = True
        contact_context_by_occupant[resident["occupant_id"]] = contact_context

        if context["has_phone"] and not (context["blackout"] and random.random() < 0.45):
            if context["ghost_phone"]:
                # Phone left behind: perfect bedroom/home signal, but no movement.
                steps = 0
            else:
                steps = generate_pedometer_steps(
                    resident,
                    max(room["structural_damage_pct"], context["actual_damage"]),
                    contact_context,
                )

            cellular_telemetry.append({
                "occupant_id": resident["occupant_id"],
                "device_type": "smartphone",
                "pedometer_5min_pre_event": {"steps": steps, "state": movement_state(steps)},
            })

        emergency_contacts.append({
            "occupant_id": resident["occupant_id"],
            "emergency_contact_response": contact_context,
        })

    wifi_routers = []
    for floor in range(1, 5):
        connected = []
        for resident in resident_registry:
            context = occupant_context[resident["occupant_id"]]
            if not context["has_phone"] or context["blackout"]:
                continue

            home_floor = floor_from_room_id(resident["home_room_id"])
            if context["contradiction"]:
                target_floor = 1 if home_floor != 1 else 2
            else:
                target_floor = home_floor

            if target_floor != floor:
                continue

            room = rooms_by_id[resident["home_room_id"]]
            rssi = estimate_rssi_dbm(
                tuple(room["original_coordinates"].values()),
                room["structural_damage_pct"],
                floor,
            )
            connection_probability = clamp((rssi + 105.0) / 45.0, 0.08, 0.92)
            if random.random() < connection_probability:
                connected.append(resident["occupant_id"])

        wifi_routers.append({
            "router_id": f"WIFI-AP-FL{floor}",
            "connected_occupants_pre_event": connected,
        })

    ble_active_signals = []
    cellular_by_occupant = {
        item["occupant_id"]: item["pedometer_5min_pre_event"]["steps"]
        for item in cellular_telemetry
    }
    for resident in resident_registry:
        context = occupant_context[resident["occupant_id"]]
        if not context["has_watch"] or context["blackout"]:
            continue

        room = rooms_by_id[resident["home_room_id"]]
        home_floor = floor_from_room_id(resident["home_room_id"])
        ble_room_id = adjacent_floor_room_id(resident["home_room_id"]) if context["contradiction"] else resident["home_room_id"]
        ble_room_id = ble_room_id if ble_room_id in rooms_by_id else resident["home_room_id"]
        ble_room = rooms_by_id[ble_room_id]
        room_origin = tuple(room["original_coordinates"].values())
        damage_pct = max(room["structural_damage_pct"], context["actual_damage"])
        rssi = estimate_rssi_dbm(tuple(ble_room["original_coordinates"].values()), damage_pct, floor_from_room_id(ble_room_id))
        if context["contradiction"]:
            rssi = round(clamp(rssi + random.uniform(6, 14), -96, -45), 1)
        vitals = generate_vitals(resident, damage_pct, cellular_by_occupant.get(resident["occupant_id"], 0))

        ble_active_signals.append({
            "occupant_id": resident["occupant_id"],
            "home_room_id": ble_room_id,
            "telemetry": {
                "rssi_dbm": rssi,
                "battery_pct": generate_battery_pct(damage_pct),
                "vital_signs": {
                    "heart_rate_bpm": vitals["heart_rate_bpm"],
                    "movement_index": vitals["movement_index"],
                },
            },
        })

    all_files = {
        "missile_impact.json": missile_impact,
        "building_history.json": building_history,
        "resident_registry.json": resident_registry,
        "building_bim.json": building_bim,
        "smart_meters_historical.json": smart_meters,
        "cellular_telemetry.json": cellular_telemetry,
        "wifi_routers.json": wifi_routers,
        "ble_active_signals.json": ble_active_signals,
        "emergency_contacts.json": emergency_contacts,
    }

    for filename, content in all_files.items():
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=4, ensure_ascii=False)

    print("[SUCCESS] All 9 dynamic JSON files written successfully.")


if __name__ == "__main__":
    generate_all_separate_entities()