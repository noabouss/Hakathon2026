import math
import random


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def generate_training_cases(num_events=50, occupants_per_event=12, seed=2026):
    """
    Generate 600 correlated historical cases:
    50 synthetic missile events x 12 static occupants.

    Each event shares one missile strike, so all 12 rows from the same event are
    physically correlated instead of being isolated random samples.
    """
    random.seed(seed)
    static_occupants = _static_occupants(occupants_per_event)
    cases = []

    for event_idx in range(1, num_events + 1):
        missile = {
            "event_id": f"TRAIN-{event_idx:03d}",
            "payload_weight_kg": random.uniform(70, 270),
            "epicenter_x": random.uniform(0, 20),
            "epicenter_y": random.uniform(0, 20),
            "epicenter_z": random.choice([3, 6, 9, 12]),
        }

        for occupant in static_occupants:
            dist = math.sqrt(
                (occupant["x"] - missile["epicenter_x"]) ** 2
                + (occupant["y"] - missile["epicenter_y"]) ** 2
                + (occupant["z"] - missile["epicenter_z"]) ** 2
            )
            blast_radius = 5.0 + math.sqrt(missile["payload_weight_kg"]) * 1.15
            blast_intensity = math.exp(-dist / blast_radius) * (missile["payload_weight_kg"] / 180.0)
            fragility = 1.0 - occupant["building_integrity"]
            damage = clamp(0.08 + blast_intensity * 0.78 + fragility * 0.2)
            phone_signal = clamp(1.0 - damage * 0.85 + dist / 170.0)
            meter_last_gasp = damage > 0.45
            steps = max(0, int(random.triangular(0, 120, 18) * occupant["mobility"] * (1.0 - damage * 0.35)))
            wifi_connected = phone_signal > 0.35 and random.random() < 0.85
            heart_rate = 72 + damage * 55 + (18 if occupant["age"] > 70 or occupant["age"] < 10 else 0)
            movement_index = clamp((1.0 - damage) * random.uniform(0.05, 0.9))

            true_urgency = clamp(
                0.18
                + damage * 0.42
                + (1.0 - occupant["mobility"]) * 0.18
                + (1.0 if heart_rate > 125 or movement_index < 0.1 else 0.0) * 0.18
                + (1.0 if occupant["age"] > 70 or occupant["age"] < 10 else 0.0) * 0.12
            ) * 100

            cases.append({
                "event_id": missile["event_id"],
                "occupant_id": occupant["occupant_id"],
                "age": occupant["age"],
                "mobility_index": occupant["mobility"],
                "building_integrity": occupant["building_integrity"],
                "payload_weight_kg": missile["payload_weight_kg"],
                "distance_to_blast": dist,
                "room_damage_pct": round(damage * 100, 2),
                "meter_last_gasp": meter_last_gasp,
                "steps": steps,
                "wifi_connected": wifi_connected,
                "phone_signal_pct": round(phone_signal * 100, 2),
                "heart_rate_bpm": round(heart_rate, 1),
                "movement_index": round(movement_index, 3),
                "true_urgency_score": round(true_urgency, 2),
            })

    return cases


def train_calibration_model(training_cases):
    """
    Build a tiny dependency-free calibration model from the synthetic history.

    The live fusion engine remains physics/heuristic based. This model learns
    average urgency offsets from historical patterns and nudges the final score.
    """
    buckets = {
        "near_blast": [],
        "far_blast": [],
        "meter_last_gasp": [],
        "no_meter_last_gasp": [],
        "low_mobility": [],
        "normal_mobility": [],
        "wifi_connected": [],
        "wifi_missing": [],
    }

    for case in training_cases:
        urgency = case["true_urgency_score"]
        buckets["near_blast" if case["distance_to_blast"] < 10 else "far_blast"].append(urgency)
        buckets["meter_last_gasp" if case["meter_last_gasp"] else "no_meter_last_gasp"].append(urgency)
        buckets["low_mobility" if case["mobility_index"] < 0.5 else "normal_mobility"].append(urgency)
        buckets["wifi_connected" if case["wifi_connected"] else "wifi_missing"].append(urgency)

    global_average = sum(case["true_urgency_score"] for case in training_cases) / len(training_cases)
    bucket_averages = {
        name: (sum(values) / len(values) if values else global_average)
        for name, values in buckets.items()
    }

    return {
        "training_case_count": len(training_cases),
        "global_average_urgency": round(global_average, 2),
        "bucket_averages": bucket_averages,
    }


def calibration_adjustment(model, features):
    bucket_names = [
        "near_blast" if features["distance_to_blast"] < 10 else "far_blast",
        "meter_last_gasp" if features["meter_last_gasp"] else "no_meter_last_gasp",
        "low_mobility" if features["mobility_index"] < 0.5 else "normal_mobility",
        "wifi_connected" if features["wifi_connected"] else "wifi_missing",
    ]

    expected = sum(model["bucket_averages"][name] for name in bucket_names) / len(bucket_names)
    return (expected - model["global_average_urgency"]) * 0.18


def _static_occupants(count):
    base = [
        ("TRAIN-OCC-001", 42, 1.0, 0.78, 5, 5, 3),
        ("TRAIN-OCC-002", 81, 0.2, 0.78, 5, 12, 3),
        ("TRAIN-OCC-003", 28, 1.0, 0.91, 40, 5, 3),
        ("TRAIN-OCC-004", 26, 1.0, 0.91, 40, 12, 6),
        ("TRAIN-OCC-005", 1, 0.0, 0.78, 12, 5, 9),
        ("TRAIN-OCC-006", 12, 1.0, 0.91, 47, 12, 9),
        ("TRAIN-OCC-007", 35, 1.0, 0.91, 47, 5, 12),
        ("TRAIN-OCC-008", 67, 0.5, 0.78, 12, 12, 12),
        ("TRAIN-OCC-009", 74, 0.4, 0.66, 5, 40, 3),
        ("TRAIN-OCC-010", 33, 1.0, 0.66, 12, 40, 6),
        ("TRAIN-OCC-011", 6, 0.8, 0.66, 5, 47, 6),
        ("TRAIN-OCC-012", 58, 0.7, 0.66, 12, 47, 12),
    ][:count]

    return [
        {
            "occupant_id": occupant_id,
            "age": age,
            "mobility": mobility,
            "building_integrity": integrity,
            "x": x,
            "y": y,
            "z": z,
        }
        for occupant_id, age, mobility, integrity, x, y, z in base
    ]