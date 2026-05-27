from app.data.sensors_dal import load_all_sensors_data
from app.logic.fusion_engine import calculate_u_sar_priority


def main():
    print("====================================================================")
    print(" 🛡️  USAR 3D MULTI-LAYERED SPATIAL FUSION ENGINE - COMMAND POST v2026")
    print("====================================================================")

    # 1. טעינת הנתונים (Data Layer)
    data = load_all_sensors_data()

    # בדיקת תקינות טעינה
    all_loaded = all(data[key] is not None for key in data)

    if not all_loaded:
        print("\n[ERROR] Failed to load one or more data sources. Please run generate_data.py first.")
        return

    print("\n[SUCCESS] All 8 separate operational data layers synchronized.")
    print("🚀 Triggering Probability Fusion Analytics Engine...")
    print("--------------------------------------------------------------------\n")

    # 2. הרצת מנוע ההיתוך וההסתברויות (Logic Layer)
    triage_dashboard = calculate_u_sar_priority(data)

    # 3. הצגת הפלט הפיקודי הממוין (Presentation Layer)
    print("=====================================================================================================")
    print(f" 🔥 LIVE RESCUE PRIORITY MISSION DASHBOARD ({len(triage_dashboard)} TARGETS IDENTIFIED)")
    print("=====================================================================================================")
    print(
        f"{'PRIORITY':<10} | {'NAME (AGE)':<22} | {'MEDICAL STATUS':<35} | {'TARGET 3D COORDS (X,Y,Z)':<24} | {'CONFIDENCE'}")
    print("-" * 101)

    for idx, target in enumerate(triage_dashboard):
        # התאמת צבעים או סימונים לפי רמת הסיכון (למראה ויזואלי מדהים במסוף)
        prefix = "🚨 [CRITICAL]" if target["priority_score"] > 85 else "⚠️ [HIGH]" if target[
                                                                                         "priority_score"] > 60 else "🔹 [MEDIUM]"

        coords = f"({target['estimated_coordinates']['x']}, {target['estimated_coordinates']['y']}, {target['estimated_coordinates']['z']})"
        name_age = f"{target['name']} ({target['age']})"
        score_str = f"{prefix} {target['priority_score']}%"

        print(
            f"{score_str:<10} | {name_age:<22} | {target['medical_status']:<35} | {coords:<24} | {target['location_confidence']}")

    print("=====================================================================================================")
    print("💡 [ACTIONABLE INTELLIGENCE] Dispatch heavy breach rescue units to Top 3 critical coordinates immediately.")
    print("=====================================================================================================\n")


if __name__ == "__main__":
    main()