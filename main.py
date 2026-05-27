from app.data.sensors_dal import load_all_sensors_data


def main():
    print("========================================")
    print(" USAR 3D Spatial Probability Engine     ")
    print("========================================")

    # 1. טעינת הנתונים (Data Layer)
    data = load_all_sensors_data()

    # בדיקה שהנתונים אכן נטענו בהצלחה
    if data["bim"] and data["meters"] and data["ble"]:
        print("\n[SUCCESS] All data sources loaded successfully!")
        print(f" - Loaded {len(data['bim']['rooms'])} rooms from BIM Structural Data.")
        print(f" - Loaded {len(data['meters'])} Smart Meters Data.")
        print(f" - Loaded {len(data['ble'])} Active BLE Signals.")
    else:
        print("\n[ERROR] Failed to load one or more data sources.")


if __name__ == "__main__":
    main()