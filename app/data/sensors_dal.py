import json
import os

def load_json_data(file_name):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_path = os.path.join(base_dir, file_name)

    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_all_sensors_data():
    return {
        "missile_impact": load_json_data('missile_impact.json'),
        "building_history": load_json_data('building_history.json'),
        "resident_registry": load_json_data('resident_registry.json'),
        "bim": load_json_data('building_bim.json'),
        "meters": load_json_data('smart_meters_historical.json'),
        "cellular": load_json_data('cellular_telemetry.json'),
        "wifi": load_json_data('wifi_routers.json'),
        "ble": load_json_data('ble_active_signals.json'),
        "contacts": load_json_data('emergency_contacts.json')
    }