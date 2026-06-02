import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_JSON_FILES = {
    "missile_impact": "missile_impact.json",
    "building_history": "building_history.json",
    "resident_registry": "resident_registry.json",
    "bim": "building_bim.json",
    "meters": "smart_meters_historical.json",
    "cellular": "cellular_telemetry.json",
    "wifi": "wifi_routers.json",
    "ble": "ble_active_signals.json",
    "contacts": "emergency_contacts.json",
}


def load_json_data(file_name):
    file_path = PROJECT_ROOT / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Missing data file: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_missing_data_files():
    return [
        file_name
        for file_name in REQUIRED_JSON_FILES.values()
        if not (PROJECT_ROOT / file_name).exists()
    ]


def get_all_sensors_data():
    return {
        data_key: load_json_data(file_name)
        for data_key, file_name in REQUIRED_JSON_FILES.items()
    }
