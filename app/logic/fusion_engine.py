import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from torch.utils.data import DataLoader, TensorDataset


class USARSpatialNeuralNet(nn.Module):
    def __init__(self, input_dim=14):  # שודרג ל-14 פיצ'רים
        super(USARSpatialNeuralNet, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 4)
        )

    def forward(self, x):
        return self.network(x)


def generate_historical_training_data(num_samples=600):
    X, y = [], []
    for _ in range(num_samples):
        age = random.randint(1, 90)
        mobility = random.uniform(0.0, 1.0)
        damage_pct = random.uniform(15.0, 95.0)
        heavy_furniture = random.choice([0, 1])
        mean_kwh = random.uniform(0.1, 1.2)
        steps_pre_event = random.randint(0, 150)
        wifi_connected = random.choice([0, 1])
        ble_rssi = random.uniform(-90.0, -50.0)
        heart_rate = random.randint(60, 150)
        battery_pct = random.randint(0, 100)

        # פיצ'רים חדשים
        immediate_movement_idx = random.uniform(0.0, 1.0)
        contact_spoke = random.choice([0, 1])
        contact_confirmed_home = random.choice([0, 1]) if contact_spoke else 0
        contact_shelter_intent = random.choice([0, 1]) if contact_spoke else 0

        features = [age, mobility, damage_pct, heavy_furniture, mean_kwh,
                    steps_pre_event, wifi_connected, ble_rssi, heart_rate, battery_pct,
                    immediate_movement_idx, contact_spoke, contact_confirmed_home, contact_shelter_intent]

        true_x = 5.0 + (damage_pct / 20.0) + random.uniform(-0.5, 0.5)

        # למידה פיזיקלית: אם הצהיר שרץ לממ"ד או שתנועתו הייתה חדה, המיקום מתעדכן
        if contact_shelter_intent == 1 or immediate_movement_idx > 0.8:
            true_y = 6.0 + random.uniform(-1, 1)
        else:
            true_y = 8.0 + (steps_pre_event / 30.0) + random.uniform(-0.5, 0.5)

        true_z = max(0.5, (12.0 - (damage_pct / 10.0)) + (ble_rssi + 50) / 10.0)
        true_priority = (100.0 - battery_pct * 0.1) + (heart_rate * 0.3) if immediate_movement_idx < 0.3 else 45.0

        X.append(features)
        y.append([true_x, true_y, true_z, min(100.0, max(0.0, true_priority))])

    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)


def train_model():
    model = USARSpatialNeuralNet(input_dim=14)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    X_train, y_train = generate_historical_training_data(600)
    dataset = TensorDataset(X_train, y_train)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

    model.train()
    print("\n🏋️ [PyTorch] Training Deep Learning Fusion Network (14 Dimensions)...")
    for epoch in range(50):
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            loss = criterion(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()
    return model


def calculate_u_sar_priority(data):
    if not data:
        return []

    trained_net = train_model()
    trained_net.eval()

    residents = data.get("resident_registry", [])
    bim_rooms = {r["room_id"]: r for r in data.get("bim", {}).get("rooms", [])}
    meters = {m["room_id"]: m for m in data.get("meters", [])}
    cellular = {c["occupant_id"]: c for c in data.get("cellular", [])}
    wifi = data.get("wifi", [])
    ble_signals = {b["occupant_id"]: b for b in data.get("ble", [])}
    contacts = {c["occupant_id"]: c.get("emergency_contact_response", {}) for c in data.get("contacts", [])}

    triage_results = []

    for res in residents:
        occ_id = res["occupant_id"]
        home_room_id = res["home_room_id"]
        room_data = bim_rooms.get(home_room_id)

        age = res.get("age", 30)
        mobility = res.get("mobility_index", 1.0)
        damage_pct = room_data["structural_damage_pct"] if room_data else 50.0
        heavy_furniture = 1 if (room_data and room_data.get("heavy_furniture", {}).get("creates_void")) else 0

        room_meter = meters.get(home_room_id)
        mean_kwh = np.mean(room_meter["history_last_2h_kwh"]) if room_meter else 0.5

        cell_data = cellular.get(occ_id)
        steps = cell_data["pedometer_5min_pre_event"]["steps"] if cell_data else 0

        wifi_connected = 0
        for router in wifi:
            if occ_id in router.get("connected_occupants_pre_event", []):
                wifi_connected = 1
                break

        if occ_id in ble_signals:
            ble = ble_signals[occ_id]
            telemetry = ble.get("telemetry", {})
            vitals = telemetry.get("vital_signs", {})

            rssi = telemetry.get("rssi_dbm", -90)
            battery_pct = telemetry.get("battery_pct", 50)
            heart_rate = vitals.get("heart_rate_bpm", 80)
            immediate_movement_idx = vitals.get("movement_index", 0.0)

            confidence_string = "High (AI Live Radio Inference)"
            medical_status = "Analyzed by AI"
            if heart_rate > 115 and immediate_movement_idx < 0.4:
                medical_status = "Critical (Trapped)"
        else:
            rssi = -95.0
            battery_pct = 0.0
            heart_rate = 0.0
            immediate_movement_idx = 0.0
            confidence_string = "Medium (Deep Spatial Estimation)"
            medical_status = "Unknown / Deep Burial"

        contact_info = contacts.get(occ_id, {})
        contact_spoke = 1 if contact_info.get("spoke_last_5_mins") else 0
        contact_confirmed_home = 1 if contact_info.get("known_at_home") else 0
        contact_shelter_intent = 1 if contact_info.get("going_to_shelter") else 0

        feature_vector = [age, mobility, damage_pct, heavy_furniture, mean_kwh,
                          steps, wifi_connected, rssi, heart_rate, battery_pct,
                          immediate_movement_idx, contact_spoke, contact_confirmed_home, contact_shelter_intent]

        with torch.no_grad():
            input_tensor = torch.tensor([feature_vector], dtype=torch.float32)
            prediction = trained_net(input_tensor).numpy()[0]

        triage_results.append({
            "occupant_id": occ_id,
            "name": res.get("name", "Unknown"),
            "age": age,
            "priority_score": round(max(0.0, min(100.0, float(prediction[3]))), 1),
            "medical_status": medical_status,
            "estimated_coordinates": {"x": round(float(prediction[0]), 2), "y": round(float(prediction[1]), 2),
                                      "z": round(max(0.2, float(prediction[2])), 2)},
            "location_confidence": confidence_string,
            "home_room": room_data["room_name"] if room_data else "Unknown"
        })

    triage_results.sort(key=lambda x: x["priority_score"], reverse=True)
    return triage_results