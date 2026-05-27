import json
import os


def load_json_data(file_name):
    """
    פונקציה גנרית לקריאת קובץ JSON מהתיקייה הראשית של הפרויקט
    """
    # מכיוון שהקבצים נמצאים בתיקייה הראשית, נחפש אותם שם
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_path = os.path.join(base_dir, file_name)

    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_sensors_data():
    """
    פונקציה שטוענת את כל שלושת מאגרי המידע שלנו ומחזירה אותם כמילון אחד מסודר
    """
    print("Loading data from mock databases (JSONs)...")

    # טעינת שלושת הקבצים
    bim_data = load_json_data('building_bim.json')
    meters_data = load_json_data('smart_meters_historical.json')
    ble_data = load_json_data('ble_active_signals.json')

    return {
        "bim": bim_data,
        "meters": meters_data,
        "ble": ble_data
    }