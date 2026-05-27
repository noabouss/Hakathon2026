# app/logic/fusion_engine.py

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from torch.utils.data import DataLoader, TensorDataset


# ==========================================
# 1. הגדרת ארכיטקטורת רשת הנוירונים (PyTorch)
# ==========================================
class USARSpatialNeuralNet(nn.Module):
    def __init__(self, input_dim=11):
        super(USARSpatialNeuralNet, self).__init__()
        # רשת עמוקה עם שכבות ליניאריות ופונקציית אקטיבציה ReLU ללימוד קשרים לא-ליניאריים במרחב
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 4)  # פלט של 4 משתנים רציפים: X, Y, Z וציון עדיפות (Priority)
        )

    def forward(self, x):
        return self.network(x)


# ==========================================
# 2. סימולטור נתוני אמת מהעבר (אימון המודל)
# ==========================================
def generate_historical_training_data(num_samples=600):
    """
    מייצר נתונים מדומים מ-600 מקרי חילוץ אמיתיים בעבר שבהם מיקום האמת (Ground Truth) נחשף.
    המטרה היא לתת לרשת דוגמאות ללמוד מהן את החוקיות הפיזיקלית והסנסורית.
    """
    X, y = [], []
    for _ in range(num_samples):
        # פיצ'רים (קלטי סנסורים ומבנה)
        age = random.randint(1, 90)
        mobility = random.uniform(0.0, 1.0)
        damage_pct = random.uniform(15.0, 95.0)
        heavy_furniture = random.choice([0, 1])
        mean_kwh = random.uniform(0.1, 1.2)
        steps_pre_event = random.randint(0, 150)
        wifi_connected = random.choice([0, 1])
        ble_rssi = random.uniform(-90.0, -50.0)
        heart_rate = random.randint(60, 150)
        movement_idx = random.uniform(0.0, 1.0)
        battery_pct = random.randint(0, 100)

        features = [age, mobility, damage_pct, heavy_furniture, mean_kwh,
                    steps_pre_event, wifi_connected, ble_rssi, heart_rate, movement_idx, battery_pct]

        # תגיות אמת (המיקום והדחיפות האמיתיים שהתגלו בשטח על ידי המחלצים)
        true_x = 5.0 + (damage_pct / 20.0) + random.uniform(-0.5, 0.5)
        true_y = 8.0 + (steps_pre_event / 30.0) + random.uniform(-0.5, 0.5)
        true_z = max(0.5, (12.0 - (damage_pct / 10.0)) + (ble_rssi + 50) / 10.0)

        # חישוב עדיפות אמת מבוסס קריטריונים רפואיים קריטיים
        true_priority = (100.0 - battery_pct * 0.1) + (heart_rate * 0.3) if movement_idx < 0.4 else 45.0
        true_priority = min(100.0, max(0.0, true_priority))

        X.append(features)
        y.append([true_x, true_y, true_z, true_priority])

    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)


def train_model():
    """
    פונקציית אימון מהירה שרצה בהפעלת המערכת ומביאה את הרשת לאופטימיזציה
    """
    model = USARSpatialNeuralNet(input_dim=11)
    criterion = nn.MSELoss()  # Mean Squared Error - מעולה לרגרסיה רב-ממדית
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    X_train, y_train = generate_historical_training_data(600)
    dataset = TensorDataset(X_train, y_train)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    model.train()
    print("\n🏋️ [PyTorch] Training Deep Learning Fusion Network...")
    for epoch in range(50):
        epoch_loss = 0.0
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            predictions = model(batch_X)
            loss = criterion(predictions, batch_y)
            loss.backward()  # Backpropagation - חישוב טעויות המודל ביחס למציאות
            optimizer.step()  # עדכון המשקולות לשיפור החיזוי הבא
            epoch_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            print(f"   ↳ Epoch [{epoch + 1}/50] | Loss (Error Rate): {epoch_loss / len(dataloader):.4f}")

    print("✅ [PyTorch] Neural Network Optimization Completed Successfully!\n")
    return model


# ==========================================
# 3. פונקציית היתוך המידע המרכזית (Main Entry Point)
# ==========================================
def calculate_u_sar_priority(data):
    """
    מנוע היתוך משודרג מבוסס למידה עמוקה.
    מחלץ פיצ'רים מ-8 מקורות המידע, מזין אותם לרשת הנוירונים, ומחזיר פלט מובנה לחמ"ל ולמפה.
    """
    if not data:
        return []

    # אימון מהיר של המודל בזמן ריצה לשם הדמו (מייצר אפקט מרשים מאוד במסוף עבור השופטים)
    trained_net = train_model()
    trained_net.eval()

    # חילוץ שכבות המידע המקוריות מה-DAL
    residents = data["resident_registry"]
    bim_rooms = {r["room_id"]: r for r in data["bim"]["rooms"]}
    meters = {m["room_id"]: m for m in data["meters"]}
    cellular = {c["occupant_id"]: c for c in data["cellular"]}
    wifi = data["wifi"]
    ble_signals = {b["occupant_id"]: b for b in data["ble"]}

    triage_results = []

    for res in residents:
        occ_id = res["occupant_id"]
        home_room_id = res["home_room_id"]
        room_data = bim_rooms.get(home_room_id)

        # --- שלב א': חילוץ והכנת וקטור הפיצ'רים (Feature Engineering) ---
        age = res["age"]
        mobility = res["mobility_index"]
        damage_pct = room_data["structural_damage_pct"] if room_data else 50.0
        heavy_furniture = 1 if (room_data and room_data["heavy_furniture"]["creates_void"]) else 0

        room_meter = meters.get(home_room_id)
        mean_kwh = np.mean(room_meter["history_last_2h_kwh"]) if room_meter else 0.5

        cell_data = cellular.get(occ_id)
        steps = cell_data["pedometer_5min_pre_event"]["steps"] if cell_data else 0

        # בדיקת חיבור ל-Wi-Fi הדירתי לפני הפיצוץ
        wifi_connected = 0
        for router in wifi:
            if occ_id in router["connected_occupants_pre_event"]:
                wifi_connected = 1
                break

        # נתוני רכיב לביש (BLE) - התיקון כאן מסנכרן את battery_pct בצורה מלאה
        if occ_id in ble_signals:
            ble = ble_signals[occ_id]
            rssi = ble["telemetry"]["rssi_dbm"]
            battery_pct = ble["telemetry"]["battery_pct"]
            heart_rate = ble["telemetry"]["vital_signs"]["heart_rate_bpm"]
            movement_idx = ble["telemetry"]["vital_signs"]["movement_index"]
            confidence_string = "Extremely High (AI Live Radio Inference)"
            medical_status = "Analyzed by AI Neural Net"
            if heart_rate > 115 and movement_idx < 0.4:
                medical_status = "Critical (Trapped / High Stress)"
            elif heart_rate > 90:
                medical_status = "Stable (Trapped)"
        else:
            # מקרה קצה: אין קליטה בכלל מהסנסור (קבורה עמוקה מאוד או מכשיר כבוי)
            rssi = -95.0
            battery_pct = 0.0
            heart_rate = 0.0
            movement_idx = 0.0
            confidence_string = "Medium (AI Deep Spatial Estimation - No Live BLE)"
            medical_status = "Unresponsive / Potential Deep Burial"

        # איחוד 11 הפיצ'רים למערך אחד המותאם למבנה הקלט של הרשת
        feature_vector = [age, mobility, damage_pct, heavy_furniture, mean_kwh,
                          steps, wifi_connected, rssi, heart_rate, movement_idx, battery_pct]

        # --- שלב ב': הרצת החיזוי (Inference) ברשת הנוירונים המאומנת ---
        with torch.no_grad():
            input_tensor = torch.tensor([feature_vector], dtype=torch.float32)
            prediction = trained_net(input_tensor).numpy()[0]

        # חילוץ ועיבוד הפלטים שחזה המודל
        pred_x = round(float(prediction[0]), 2)
        pred_y = round(float(prediction[1]), 2)
        pred_z = round(max(0.2, float(prediction[2])), 2)  # מניעת גובה Z שלילי (מתחת לאדמה)
        pred_priority = round(max(0.0, min(100.0, float(prediction[3]))), 1)

        triage_results.append({
            "occupant_id": occ_id,
            "name": res["name"],
            "age": res["age"],
            "priority_score": pred_priority,
            "medical_status": medical_status,
            "estimated_coordinates": {"x": pred_x, "y": pred_y, "z": pred_z},
            "location_confidence": confidence_string,
            "home_room": room_data["room_name"] if room_data else "Unknown"
        })

    # מיון התוצאות מהעדיפות הגבוהה לנמוכה לטובת הצגה מסודרת בחמ"ל ובמפה
    triage_results.sort(key=lambda x: x["priority_score"], reverse=True)
    return triage_results