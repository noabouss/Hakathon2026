import json
import os

# משתנה גלובלי שישמור את הנתונים בזיכרון (Cache)
_cached_data = None


def load_json_data(file_name):
    """
    פונקציה גנרית לקריאת קובץ JSON מתוך תיקיית mock_data
    """
    # עולים 3 רמות למעלה מ-app/data/sensors_dal.py אל תיקיית השורש
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # הוספנו כאן את 'mock_data' לנתיב החיפוש!
    file_path = os.path.join(base_dir, 'mock_data', file_name)

    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_sensors_data(force_reload=False):
    """
    מחזיר את כל הנתונים כמילון אחד.
    משתמש ב-Cache כדי לא להכביד על קריאות חוזרות מהדיסק בכל פעם שהאלגוריתם רץ.
    """
    global _cached_data

    # אם הנתונים כבר נטענו לזיכרון, נחזיר אותם מיד (חיסכון עצום בזמן ריצה)
    if _cached_data is not None and not force_reload:
        return _cached_data

    print("Loading data from mock_data directory into memory...")

    _cached_data = {
        "missile_impact": load_json_data('missile_impact.json'),
        "building_history": load_json_data('building_history.json'),
        "resident_registry": load_json_data('resident_registry.json'),
        "bim": load_json_data('building_bim.json'),
        "meters": load_json_data('smart_meters_historical.json'),
        "cellular": load_json_data('cellular_telemetry.json'),
        "wifi": load_json_data('wifi_routers.json'),
        "ble": load_json_data('ble_active_signals.json')
    }

    return _cached_data