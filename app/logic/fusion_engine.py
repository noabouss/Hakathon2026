"""
fusion_engine.py  –  USAR Probabilistic Inference Engine (v2)
================================================================
Upgrade over v1
---------------
1. Smart Conflict Resolution (Device Separation)
   Cross-references cellular pedometer + BLE movement_index to detect when the
   phone was left behind (ghost-phone scenario). Penalises or drops cellular /
   WiFi location evidence when separation is detected.

2. Dynamic Signal Weighting (Attenuation / Multipath Awareness)
   High structural-damage rooms produce multipath-corrupted RSSI. In those zones
   the engine lowers BLE/WiFi positional trust and biases the final estimate
   toward the physical BIM post-collapse coordinate.

3. Weighted-Centroid Coordinate Estimation
   Replaces the single "nudge" heuristic with a proper weighted average across
   up to four evidence anchors:
       • BIM void/collapse coordinates  (physics ground truth)
       • BLE home_room_id coordinates   (wearable, stays on body)
       • WiFi floor association         (phone, unreliable when separated)
       • Pedometer displacement vector  (movement before impact)

4. Threshold Variables
   All key decision thresholds are named constants at the top of the file so a
   future ML tuning loop can expose and optimise them without touching logic.

Output schema is identical to v1 so the dashboard works without changes.
"""

import math
from dataclasses import dataclass

from app.logic.training_data import calibration_adjustment


# ---------------------------------------------------------------------------
# Tuneable threshold constants  (future ML sweep targets)
# ---------------------------------------------------------------------------

# Device-Separation detection
SEPARATION_PHONE_MAX_STEPS        = 8      # pedometer steps considered "phone at rest"
SEPARATION_BLE_MIN_MOVEMENT       = 0.25   # BLE movement_index considered "body in motion"
SEPARATION_BLE_MIN_HEART_RATE     = 90     # elevated HR corroborates body activity

# Signal attenuation / multipath
MULTIPATH_DAMAGE_THRESHOLD        = 75     # structural_damage_pct above which RSSI is unreliable
HIGH_DAMAGE_THRESHOLD             = 55     # above which phone/WiFi weights are discounted

# BLE trust
BLE_RSSI_USABLE_DBM               = -92.0  # weaker than this → BLE location unreliable
TRUST_THRESHOLD_BLE               = 0.60   # normalised BLE quality above which full weight is used

# Confidence increments (kept identical to v1 so urgency maths is unchanged)
CONF_METER_MEAN_HIGH              = 0.6    # kWh threshold for occupancy bonus
CONF_INCREMENT_METER_HIGH         = 0.12
CONF_INCREMENT_METER_LAST_GASP    = 0.10
CONF_INCREMENT_STEPS              = 0.15
CONF_INCREMENT_WIFI               = 0.10
CONF_INCREMENT_KNOWN_AT_HOME      = 0.12
CONF_INCREMENT_GOING_TO_SHELTER   = 0.05
CONF_BASE_VOID                    = 0.35
CONF_VOID_SCALE                   = 0.25
CONF_BASE_ROOM_ONLY               = 0.25

# Pedometer displacement
STEPS_NORMALISER                  = 130.0
MAX_STEPS_DISPLACEMENT            = 0.35


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def xyz_to_tuple(point):
    return (float(point["x"]), float(point["y"]), float(point["z"]))


def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    )


def weighted_centroid(anchors):
    """
    anchors: list of ((x, y, z), weight)
    Returns the weighted average coordinate.
    Falls back to the first anchor when total weight is zero.
    """
    total_w = sum(w for _, w in anchors if w > 0)
    if total_w == 0:
        return anchors[0][0]
    x = sum(c[0] * w for c, w in anchors if w > 0) / total_w
    y = sum(c[1] * w for c, w in anchors if w > 0) / total_w
    z = sum(c[2] * w for c, w in anchors if w > 0) / total_w
    return (x, y, z)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VoidSpace:
    room_id: str
    room_name: str
    coordinates: tuple
    survival_probability: float
    evidence: str


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class FusionEngine:
    """
    Two-step USAR fusion engine (v2 – Probabilistic Inference):
    1. Map collapse and survivable void spaces  (unchanged from v1).
    2. Locate humans inside those spaces with smart conflict resolution,
       dynamic signal weighting, and weighted-centroid estimation.
    """

    def __init__(self, calibration_model=None):
        self.calibration_model = calibration_model

    def run(self, data):
        void_spaces = self.map_collapse_and_void_spaces(data)
        return self.identify_humans_in_void_spaces(data, void_spaces)

    def explain_data_source_usage(self):
        return [
            "Cellular & Pedometer: steps before impact raise confidence; zero steps + high BLE movement → device separation detected.",
            "Smart Electricity Meters: high recent kWh indicates room occupancy; last-gasp meters verify impact/damage zones.",
            "Static Building Data: BIM supplies room coordinates, post-collapse coordinates, damage %, and void-forming furniture.",
            "Building History: structural integrity changes void survival and collapse severity estimates.",
            "Resident Registry: age, mobility, home room, and name drive triage and baseline location.",
            "Missile Impact: epicenter and payload shape blast distance, verified impact zone, and urgency.",
            "Home Wi-Fi Routers: pre-event router association corroborates floor/building presence; penalised during device-separation.",
            "BLE Wearable: stays on the body – trusted more than phone during separation and in high-damage multipath zones.",
        ]

    # ------------------------------------------------------------------
    # Step 1: identical to v1 – map collapse geometry
    # ------------------------------------------------------------------

    def map_collapse_and_void_spaces(self, data):
        missile          = data["missile_impact"]
        rooms            = data["bim"]["rooms"]
        meters           = data["meters"]
        building_history = data["building_history"]

        epicenter           = xyz_to_tuple(missile["epicenter_coordinates"])
        verified_impact     = self._verify_impact_zone_with_meters(epicenter, rooms, meters)
        structural_integrity = building_history.get("structural_integrity_pre_event", 80.0) / 100.0
        payload_factor       = missile.get("payload_weight_kg", 150.0) / 150.0

        void_spaces = []
        for room in rooms:
            room_coordinates = xyz_to_tuple(room["post_collapse_coordinates"])
            damage_pct       = room["structural_damage_pct"]
            has_void_furniture = room["heavy_furniture"]["creates_void"]

            blast_distance    = distance(room_coordinates, verified_impact)
            proximity_bonus   = clamp(1.0 - blast_distance / (30.0 + payload_factor * 8.0))
            furniture_bonus   = 0.3 if has_void_furniture else 0.0
            damage_factor     = clamp(damage_pct / 100.0)
            integrity_bonus   = clamp(structural_integrity * 0.18)
            fragility_penalty = clamp((1.0 - structural_integrity) * damage_factor * 0.16)
            survival_probability = clamp(
                0.12
                + furniture_bonus
                + proximity_bonus * 0.2
                + (1.0 - damage_factor) * 0.22
                + integrity_bonus
                - fragility_penalty
            )

            if has_void_furniture or damage_pct >= 25:
                void_spaces.append(
                    VoidSpace(
                        room_id=room["room_id"],
                        room_name=room["room_name"],
                        coordinates=room_coordinates,
                        survival_probability=round(survival_probability, 3),
                        evidence=(
                            f"{room['room_name']} damage={damage_pct}% "
                            f"void_furniture={has_void_furniture}"
                        ),
                    )
                )

        return sorted(void_spaces, key=lambda item: item.survival_probability, reverse=True)

    # ------------------------------------------------------------------
    # Step 2: upgraded human localisation with probabilistic inference
    # ------------------------------------------------------------------

    def identify_humans_in_void_spaces(self, data, void_spaces):
        residents           = data["resident_registry"]
        missile             = data["missile_impact"]
        rooms_by_id         = {room["room_id"]: room for room in data["bim"]["rooms"]}
        meters_by_room      = {meter["room_id"]: meter for meter in data["meters"]}
        cellular_by_occupant = {item["occupant_id"]: item for item in data["cellular"]}
        ble_by_occupant     = {item["occupant_id"]: item for item in data["ble"]}
        contacts_by_occupant = {
            item["occupant_id"]: item["emergency_contact_response"]
            for item in data["contacts"]
        }
        wifi_by_occupant    = self._index_wifi_connections(data["wifi"])
        void_by_room        = {void.room_id: void for void in void_spaces}

        results = []
        for resident in residents:
            occupant_id = resident["occupant_id"]
            room_id     = resident["home_room_id"]
            room        = rooms_by_id.get(room_id)
            void        = void_by_room.get(room_id)
            meter       = meters_by_room.get(room_id)
            cellular    = cellular_by_occupant.get(occupant_id, {})
            ble         = ble_by_occupant.get(occupant_id, {})
            contact     = contacts_by_occupant.get(occupant_id, {})

            damage_pct  = room["structural_damage_pct"] if room else 50

            # ----------------------------------------------------------
            # RULE 1: Device-Separation detection
            # ----------------------------------------------------------
            phone_steps      = cellular.get("pedometer_5min_pre_event", {}).get("steps", 0)
            telemetry        = ble.get("telemetry", {})
            vitals           = telemetry.get("vital_signs", {})
            ble_movement     = vitals.get("movement_index", 0.0)
            ble_heart_rate   = vitals.get("heart_rate_bpm") or 0

            device_separated = (
                phone_steps <= SEPARATION_PHONE_MAX_STEPS
                and (
                    ble_movement  >= SEPARATION_BLE_MIN_MOVEMENT
                    or ble_heart_rate >= SEPARATION_BLE_MIN_HEART_RATE
                )
            )
            # If the phone is confirmed left behind, zero out its step count
            # for downstream coordinate calculation (keep original for reporting).
            effective_steps = 0 if device_separated else phone_steps

            # ----------------------------------------------------------
            # RULE 2: Signal quality assessment (multipath / attenuation)
            # ----------------------------------------------------------
            high_damage        = damage_pct >= HIGH_DAMAGE_THRESHOLD
            multipath_zone     = damage_pct >= MULTIPATH_DAMAGE_THRESHOLD
            ble_rssi           = telemetry.get("rssi_dbm", -100.0)
            ble_signal_quality = clamp((ble_rssi - (-105.0)) / (BLE_RSSI_USABLE_DBM - (-105.0)))
            # quality ∈ [0,1]: 1.0 = strong signal, 0 = too weak

            # ----------------------------------------------------------
            # RULE 3: Weighted-centroid anchor preparation
            # ----------------------------------------------------------

            # Anchor A – BIM physics (post-collapse coordinate of home void/room)
            if void:
                bim_coord  = void.coordinates
                bim_weight = 2.0 + void.survival_probability  # always trusted
            elif room:
                bim_coord  = xyz_to_tuple(room["post_collapse_coordinates"])
                bim_weight = 1.5
            else:
                bim_coord  = (0.0, 0.0, 0.0)
                bim_weight = 0.3

            # Increase BIM dominance when multipath corrupts RF signals
            if multipath_zone:
                bim_weight *= 1.8

            # Anchor B – BLE wearable room origin
            # BLE home_room_id is the room the watch was associated with.
            ble_room_id  = ble.get("home_room_id", room_id)
            ble_room     = rooms_by_id.get(ble_room_id)
            if ble_room and ble_signal_quality > 0:
                if ble_room_id == room_id:
                    # Watch in home room → corroborates BIM
                    ble_coord  = xyz_to_tuple(ble_room["post_collapse_coordinates"])
                    ble_weight = clamp(ble_signal_quality / TRUST_THRESHOLD_BLE) * 1.5
                else:
                    # Watch associated with a different room → occupant may have
                    # moved; use that room's post-collapse coord but weight lower.
                    ble_coord  = xyz_to_tuple(ble_room["post_collapse_coordinates"])
                    ble_weight = clamp(ble_signal_quality / TRUST_THRESHOLD_BLE) * 0.8
                # In multipath zones the wearable coord is still useful but
                # noisier – reduce its weight relative to BIM.
                if multipath_zone:
                    ble_weight *= 0.55
            else:
                ble_coord  = bim_coord
                ble_weight = 0.0

            # Anchor C – WiFi floor association (phone-based)
            # Heavily penalised during device-separation or high-damage zones.
            wifi_floor_coord = self._wifi_floor_centroid(
                occupant_id, wifi_by_occupant, rooms_by_id
            )
            if wifi_floor_coord and not device_separated and not high_damage:
                wifi_weight = 0.6
            elif wifi_floor_coord and device_separated:
                # Phone left behind – its location is irrelevant for the person.
                wifi_weight = 0.0
            elif wifi_floor_coord and high_damage:
                wifi_weight = 0.15  # slight soft constraint only
            else:
                wifi_floor_coord = bim_coord
                wifi_weight      = 0.0

            # Anchor D – Pedometer displacement from room exit direction
            if effective_steps > 0 and room:
                displacement_strength = clamp(effective_steps / STEPS_NORMALISER,
                                              0.0, MAX_STEPS_DISPLACEMENT)
                # Project slightly toward room centre-exit (room post-collapse coord)
                room_exit_coord = xyz_to_tuple(room["post_collapse_coordinates"])
                steps_coord = (
                    bim_coord[0] * (1.0 - displacement_strength) + room_exit_coord[0] * displacement_strength,
                    bim_coord[1] * (1.0 - displacement_strength) + room_exit_coord[1] * displacement_strength,
                    bim_coord[2] * (1.0 - displacement_strength) + room_exit_coord[2] * displacement_strength,
                )
                steps_weight = displacement_strength * 0.9
            else:
                steps_coord  = bim_coord
                steps_weight = 0.0

            # Final coordinate: weighted centroid over all four anchors
            anchors = [
                (bim_coord,        bim_weight),
                (ble_coord,        ble_weight),
                (wifi_floor_coord, wifi_weight),
                (steps_coord,      steps_weight),
            ]
            estimated_coordinates = weighted_centroid(anchors)

            # ----------------------------------------------------------
            # Location confidence (same incremental logic as v1 plus
            # separation penalty so the dashboard reflects uncertainty)
            # ----------------------------------------------------------
            if void:
                location_confidence = CONF_BASE_VOID + void.survival_probability * CONF_VOID_SCALE
            elif room:
                location_confidence = CONF_BASE_ROOM_ONLY
            else:
                location_confidence = 0.05

            if meter:
                mean_kwh = sum(meter["history_last_2h_kwh"]) / len(meter["history_last_2h_kwh"])
                if mean_kwh > CONF_METER_MEAN_HIGH:
                    location_confidence += CONF_INCREMENT_METER_HIGH
                if meter["transmitted_last_gasp"]:
                    location_confidence += CONF_INCREMENT_METER_LAST_GASP

            if effective_steps > 0:
                location_confidence += CONF_INCREMENT_STEPS

            if wifi_by_occupant.get(occupant_id) and not device_separated:
                location_confidence += CONF_INCREMENT_WIFI

            if contact.get("known_at_home"):
                location_confidence += CONF_INCREMENT_KNOWN_AT_HOME
            if contact.get("going_to_shelter"):
                location_confidence += CONF_INCREMENT_GOING_TO_SHELTER

            # Penalty: if we detected device separation, reduce confidence
            # because we lost phone-based evidence.
            if device_separated:
                location_confidence -= 0.08

            location_confidence = clamp(location_confidence)

            # ----------------------------------------------------------
            # Medical urgency (unchanged from v1)
            # ----------------------------------------------------------
            medical_urgency_score = self._calculate_medical_urgency(
                resident=resident,
                room=room,
                ble=ble,
                location_confidence=location_confidence,
            )
            medical_urgency_score += self._training_adjustment(
                missile=missile,
                room=room,
                resident=resident,
                meter=meter,
                wifi_connected=bool(wifi_by_occupant.get(occupant_id)),
            )
            medical_urgency_score = clamp(medical_urgency_score, 0.0, 100.0)

            results.append(
                {
                    "occupant_id": occupant_id,
                    "name": resident.get("name", "Unknown"),
                    "estimated_coordinates": tuple(round(v, 2) for v in estimated_coordinates),
                    "medical_urgency_score": round(medical_urgency_score, 1),
                    "location_confidence": round(location_confidence, 3),
                    "home_room": room["room_name"] if room else "Unknown",
                    "source_evidence": {
                        "cellular_pedometer_steps": phone_steps,
                        "smart_meter_last_gasp": bool(meter and meter.get("transmitted_last_gasp")),
                        "wifi_connected": bool(wifi_by_occupant.get(occupant_id)),
                        "room_damage_pct": room.get("structural_damage_pct") if room else None,
                        # v2 diagnostic fields
                        "device_separated": device_separated,
                        "multipath_zone": multipath_zone,
                        "ble_signal_quality": round(ble_signal_quality, 3),
                    },
                }
            )

        return sorted(results, key=lambda row: row["medical_urgency_score"], reverse=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _verify_impact_zone_with_meters(self, epicenter, rooms, meters):
        rooms_by_id = {room["room_id"]: room for room in rooms}
        last_gasp_rooms = [
            rooms_by_id[meter["room_id"]]
            for meter in meters
            if meter.get("transmitted_last_gasp") and meter["room_id"] in rooms_by_id
        ]
        if not last_gasp_rooms:
            return epicenter
        n  = len(last_gasp_rooms)
        x  = (epicenter[0] * 2 + sum(xyz_to_tuple(r["original_coordinates"])[0] for r in last_gasp_rooms)) / (2 + n)
        y  = (epicenter[1] * 2 + sum(xyz_to_tuple(r["original_coordinates"])[1] for r in last_gasp_rooms)) / (2 + n)
        z  = (epicenter[2] * 2 + sum(xyz_to_tuple(r["original_coordinates"])[2] for r in last_gasp_rooms)) / (2 + n)
        return (x, y, z)

    def _index_wifi_connections(self, routers):
        index = {}
        for router in routers:
            for occupant_id in router.get("connected_occupants_pre_event", []):
                index[occupant_id] = router["router_id"]
        return index

    def _wifi_floor_centroid(self, occupant_id, wifi_by_occupant, rooms_by_id):
        """
        Return the average post-collapse coordinate of all rooms on the floor
        that the occupant's phone was associated with.  Returns None when no
        WiFi association exists.
        """
        router_id = wifi_by_occupant.get(occupant_id)
        if not router_id:
            return None

        # Router IDs follow the pattern WIFI-AP-FL{floor}
        try:
            floor = int(router_id.split("FL")[-1])
        except (ValueError, IndexError):
            return None

        floor_rooms = [
            room for room in rooms_by_id.values()
            if room["room_id"].startswith(f"R-{floor}")
        ]
        if not floor_rooms:
            return None

        coords = [xyz_to_tuple(room["post_collapse_coordinates"]) for room in floor_rooms]
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        cz = sum(c[2] for c in coords) / len(coords)
        return (cx, cy, cz)

    def _calculate_medical_urgency(self, resident, room, ble, location_confidence):
        age        = resident.get("age", 35)
        mobility   = resident.get("mobility_index", 1.0)
        damage_pct = room.get("structural_damage_pct", 50) if room else 50

        urgency  = 20.0
        urgency += damage_pct * 0.35
        urgency += (1.0 - mobility) * 20.0

        if age < 12 or age > 70:
            urgency += 18.0
        elif age > 60:
            urgency += 10.0

        telemetry   = ble.get("telemetry", {})
        vitals      = telemetry.get("vital_signs", {})
        heart_rate  = vitals.get("heart_rate_bpm")
        movement_index = vitals.get("movement_index", 0.0)
        battery_pct = telemetry.get("battery_pct")

        if heart_rate is None:
            urgency += 14.0
        elif heart_rate < 50 or heart_rate > 125:
            urgency += 24.0
        elif heart_rate < 60 or heart_rate > 110:
            urgency += 14.0

        if movement_index < 0.1:
            urgency += 16.0
        elif movement_index < 0.3:
            urgency += 8.0

        if battery_pct is not None and battery_pct < 25:
            urgency += 6.0

        urgency += clamp(location_confidence) * 8.0
        return clamp(urgency, 0.0, 100.0)

    def _training_adjustment(self, missile, room, resident, meter, wifi_connected):
        if not self.calibration_model or not room:
            return 0.0
        features = {
            "distance_to_blast": distance(
                xyz_to_tuple(room["original_coordinates"]),
                xyz_to_tuple(missile["epicenter_coordinates"]),
            ),
            "meter_last_gasp": bool(meter and meter.get("transmitted_last_gasp")),
            "mobility_index": resident.get("mobility_index", 1.0),
            "wifi_connected": wifi_connected,
        }
        return calibration_adjustment(self.calibration_model, features)