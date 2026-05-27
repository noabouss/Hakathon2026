import datetime


def calculate_u_sar_priority(data):
    """
    מנוע היתוך מידע מרחבי והסתברותי (Multi-Layered USAR Intelligence Fusion)
    מחשב עבור כל דייר את סיכויי ההישרדות, דחיפות החילוץ ומיקומו המשוער בהריסות.
    """
    if not data:
        return []

    # חילוץ שכבות המידע
    missile = data["missile_impact"]
    building = data["building_history"]
    residents = data["resident_registry"]
    bim_rooms = {r["room_id"]: r for r in data["bim"]["rooms"]}
    meters = {m["room_id"]: m for m in data["meters"]}
    cellular = {c["occupant_id"]: c for c in data["cellular"]}
    wifi = data["wifi"]
    ble_signals = {b["occupant_id"]: b for b in data["ble"]}

    # סימולציה של מערכת ה-SMS האינטראקטיבית (השתלטות חכמה) שהגית!
    # במציאות זה יגיע מקובץ נתונים אקטיבי, כאן נדמה תגובות אמת לשם הדמו
    mock_sms_responses = {
        "OCC-R-101-A": {"responded": True, "status": "safe", "note": "I escaped outside before the collapse!"},
        "OCC-R-102-A": {"responded": False, "status": "unknown", "note": ""},  # סבא לא ענה
        "OCC-R-401-A": {"responded": True, "status": "trapped",
                        "note": "Ceiling collapsed on my legs, near the dining table!"}
    }

    triage_results = []

    # 1. חישוב מקדם קריסה מבני (Disaster Severity Matrix)
    # בניין ישן סופג נזק קטסטרופלי יותר מטיל כבד
    base_collapse_risk = 1.2 if building["year_built"] < 1980 else 0.8
    payload_modifier = missile["payload_weight_kg"] / 100.0
    structural_severity_factor = base_collapse_risk * payload_modifier

    # 2. לולאת עיבוד מרכזית עבור כל ישות אדם (Occupant Core Loop)
    for res in residents:
        occ_id = res["occupant_id"]
        home_room_id = res["home_room_id"]
        room_data = bim_rooms.get(home_room_id)

        # נקודת מוצא: קואורדינטות החדר המקורי שלו מה-BIM
        target_x = room_data["post_collapse_coordinates"]["x"]
        target_y = room_data["post_collapse_coordinates"]["y"]
        target_z = room_data["post_collapse_coordinates"]["z"]

        # מדדי בסיס לאלגוריתם
        presence_probability = 50.0  # ברירת מחדל: 50% סיכוי שהיה בבית
        urgency_score = 0.0
        medical_status = "Unknown"
        location_confidence = "Low"

        # --- שלב א': בדיקת מערכת ההשתלטות ה-SMS (החזון האנושי שלך) ---
        sms = mock_sms_responses.get(occ_id, {"responded": False, "status": "unknown", "note": ""})
        if sms["responded"] and sms["status"] == "safe":
            # האדם בחוץ ובטוח! מורידים עדיפות ל-0 כדי לא לבזבז משאבי חילוץ
            continue

            # --- שלב ב': היתוך נתבים וסלולר לזיהוי נוכחות (הצלבת רשתות) ---
        # האם היה מחובר ל-Wi-Fi הביתי רגע לפני הפיצוץ?
        is_wifi_connected = False
        for router in wifi:
            if occ_id in router["connected_occupants_pre_event"]:
                is_wifi_connected = True
                break

        if is_wifi_connected:
            presence_probability += 40.0  # הוכחה חותכת שהיה בטווח הדירה

        # הצלבה עם מוני חשמל - האם הייתה צריכה בחדר האם שלו?
        room_meter = meters.get(home_room_id)
        if room_meter and any(kwh > 0.4 for kwh in room_meter["history_last_2h_kwh"]):
            presence_probability += 10.0

        presence_probability = min(presence_probability, 100.0)

        # --- שלב ג': וקטור פינוי ומד צעדים (Evacuation Vectoring) ---
        cell_data = cellular.get(occ_id)
        moved_during_alarm = False

        if cell_data:
            pedometer = cell_data["pedometer_5min_pre_event"]
            # אם הוא רץ או הלך הרבה צעדים ויש לו ניידות גבוהה, הוא כנראה נע לממ"ד / מרחב מוגן
            if pedometer["steps"] > 60 and res["mobility_index"] > 0.7:
                moved_during_alarm = True
                # תיקון קואורדינטות: נניח שהוא הספיק לנוע למיקום מוגן יותר (למשל חדר הממ"ד של הבניין)
                # לצורך הסימולציה נניח שהממ"ד נמצא במרכז ציר ה-Y של המבנה
                target_y = 6.0
                location_confidence = "Medium (Evacuation Vector Applied)"
            else:
                # קשיש, תינוק או אדם שלא זז - נשאר במיקום המקור בחדר שלו
                if room_data["heavy_furniture"]["creates_void"]:
                    # פיצ'ר כיס האויר: אם יש רהיט כבד בחדר, נתקן את המיקום המדוייק אליו!
                    target_x += 0.5
                    location_confidence = "High (Void Space Correlation)"

        # --- שלב ד': אותות חיים מבוססי BLE מההריסות (Vitality Layer) ---
        ble = ble_signals.get(occ_id)
        if ble:
            presence_probability = 100.0  # אות רדיו חי מהאתר = 100% הוא שם!
            vitals = ble["telemetry"]["vital_signs"]
            rssi = ble["telemetry"]["rssi_dbm"]
            battery = ble["telemetry"]["battery_pct"]

            # חישוב עומק קבורה לפי עמעום אות הבלוטוס (RSSI Attenuation)
            # אות חלש מ-70dBm מעיד על קבורה עמוקה תחת בטון
            estimated_depth_meters = round(abs(rssi + 50) / 10.0, 1) if rssi < -50 else 0.2

            # תיקון ציר ה-Z (גובה) על פי עומק הקבורה המשוער
            target_z = max(0.5, target_z - estimated_depth_meters)

            # חישוב דחיפות רפואית לפי דופק ותנועה
            # דופק מעל 120 (סטרס קיצוני/איבוד דם) + חוסר תנועה (לכוד ללא יכולת תזוזה)
            if vitals["heart_rate_bpm"] > 115 and vitals["movement_index"] < 0.4:
                urgency_score += 50.0
                medical_status = "Critical (Trapped / High Stress)"
            elif vitals["heart_rate_bpm"] > 90:
                urgency_score += 30.0
                medical_status = "Stable (Trapped)"

            # שילוב סיכון סוללה (Battery Time-to-Live TTL)
            if battery < 20:
                urgency_score += 20.0  # מקפיצים דחיפות כי האות עומד למות!

            location_confidence = "Extremely High (Live Radio Pinging)"
        else:
            # אין אות BLE - או שהמכשיר נהרס, או שהאדם קבור עמוק מדי או לא שם
            if presence_probability > 75.0:
                urgency_score += 40.0  # סיכון שקט: נוכחות גבוהה ללא אות = חשד לקבורה עמוקה
                medical_status = "Unresponsive / Potential Deep Burial"

        # אם יש הודעת טקסט אקטיבית שהאדם לכוד, נקפיץ את הציון למקסימום
        if sms["status"] == "trapped":
            urgency_score += 30.0
            medical_status = "Confirmed Trapped (Active SMS Report)"
            # ניתוח טקסט קצר (NLP בסיסי) - אם רשם מיקום ספציפי, נעדכן קואורדינטות
            if "dining table" in sms["note"].lower():
                location_confidence = "Verified via User SMS Text"

        # --- שלב ה': שקלול הציון הסופי (Final Priority Formula) ---
        # שילוב של הסתברות נוכחות, דחיפות רפואית, ומקדם חומרת ההרס של המבנה
        final_priority_score = (presence_probability * 0.4) + (urgency_score * 0.6)
        final_priority_score *= (1.0 + (room_data["structural_damage_pct"] / 200.0) if room_data else 1.0)
        final_priority_score = round(min(100.0, max(0.0, final_priority_score)), 1)

        triage_results.append({
            "occupant_id": occ_id,
            "name": res["name"],
            "age": res["age"],
            "priority_score": final_priority_score,
            "medical_status": medical_status,
            "estimated_coordinates": {"x": round(target_x, 2), "y": round(target_y, 2), "z": round(target_z, 2)},
            "location_confidence": location_confidence,
            "home_room": room_data["room_name"] if room_data else "Unknown"
        })

    # מיון התוצאות מהציון הגבוה לנמוך - המלצה ישירה לכוחות בשטח את מי להציל קודם!
    triage_results.sort(key=lambda x: x["priority_score"], reverse=True)
    return triage_results