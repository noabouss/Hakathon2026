from app.data.sensors_dal import get_all_sensors_data, get_missing_data_files
from app.logic.fusion_engine import FusionEngine
from app.logic.scenarios import apply_scenario, available_scenarios
from app.logic.training_data import generate_training_cases, train_calibration_model
from app.presentation.map_view import build_figure


def ensure_data_files_exist():
    missing_files = get_missing_data_files()
    if not missing_files:
        return

    print("[INFO] Missing JSON data files. Running generate_data.py...")
    from generate_data import generate_all_separate_entities

    generate_all_separate_entities()

    still_missing = get_missing_data_files()
    if still_missing:
        raise FileNotFoundError(f"Data generation failed. Missing: {still_missing}")


def choose_scenario():
    scenarios = available_scenarios()

    print("\nChoose a live rescue scenario:")
    for key, scenario in scenarios.items():
        print(f"  {key}. {scenario['name']}")

    selected = input("\nEnter scenario A or B: ").strip().upper()
    if selected not in scenarios:
        print("[INFO] Invalid selection. Defaulting to Scenario A.")
        selected = "A"

    return selected


def print_source_usage(engine):
    print("\nData sources used by the fusion engine:")
    for line in engine.explain_data_source_usage():
        print(f"  - {line}")


def print_story(scenario):
    print("\nLIVE EVENT STORY")
    print("=" * 72)
    print(scenario["name"])
    print(scenario["story"])
    print("=" * 72)


def print_process_summary(training_cases, calibration_model, sensor_data, targets):
    damaged_rooms = [
        room for room in sensor_data["bim"]["rooms"]
        if room["structural_damage_pct"] >= 45
    ]
    last_gasp_meters = [
        meter for meter in sensor_data["meters"]
        if meter.get("transmitted_last_gasp")
    ]

    print("\nSYSTEM THINKING SUMMARY")
    print("=" * 72)
    print(f"Generated historical training cases: {len(training_cases)}")
    print(f"Training calibration average urgency: {calibration_model['global_average_urgency']}%")
    print(f"Live damaged rooms >=45%: {len(damaged_rooms)}")
    print(f"Smart meters with last-gasp signal: {len(last_gasp_meters)}")
    print(f"Residents processed: {len(sensor_data['resident_registry'])}")
    print(f"Final rescue targets mapped: {len(targets)}")
    print("=" * 72)


def print_priority_table(targets):
    print("\nLIVE RESCUE PRIORITY DASHBOARD")
    print("=" * 108)
    print(f"{'RANK':<6} {'OCCUPANT':<18} {'URGENCY':<10} {'CONF':<8} {'COORDINATES (X,Y,Z)':<28} {'ROOM'}")
    print("-" * 108)

    for rank, target in enumerate(targets, start=1):
        coords = target["estimated_coordinates"]
        coords_text = f"({coords[0]}, {coords[1]}, {coords[2]})"
        print(
            f"{rank:<6} "
            f"{target['occupant_id']:<18} "
            f"{target['medical_urgency_score']:<10} "
            f"{target['location_confidence']:<8} "
            f"{coords_text:<28} "
            f"{target.get('home_room', 'Unknown')}"
        )

    print("=" * 108)


def main():
    print("USAR Digital Data Fusion Engine - Command Post")
    print("=" * 56)

    ensure_data_files_exist()
    base_sensor_data = get_all_sensors_data()

    scenario_key = choose_scenario()
    sensor_data, scenario = apply_scenario(base_sensor_data, scenario_key)
    print_story(scenario)

    print("\nTraining historical brain from synthetic correlated cases...")
    training_cases = generate_training_cases(num_events=50, occupants_per_event=12)
    calibration_model = train_calibration_model(training_cases)

    engine = FusionEngine(calibration_model=calibration_model)
    print_source_usage(engine)

    print("\nRunning 2-step fusion pipeline...")
    print("  Step 1: Mapping collapse geometry and void spaces.")
    print("  Step 2: Identifying human presence and medical urgency.")
    rescue_targets = engine.run(sensor_data)

    print_process_summary(training_cases, calibration_model, sensor_data, rescue_targets)
    print_priority_table(rescue_targets)

    input("\nPress Enter to open the 3D command map...")
    figure = build_figure(rescue_targets, bim_data=sensor_data["bim"])
    figure.show()


if __name__ == "__main__":
    main()