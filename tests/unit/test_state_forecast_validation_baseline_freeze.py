import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "state_forecast_validation_baseline_freeze.py"
spec = importlib.util.spec_from_file_location("state_forecast_validation_baseline_freeze", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_state_forecast_validation_baseline_report_contains_core_inventory_counts():
    report = module.build_state_forecast_validation_baseline_report(
        now=datetime.fromisoformat("2026-03-30T19:05:00")
    )

    summary = report["baseline_summary"]
    inventories = report["inventories"]
    assessment = report["baseline_assessment"]

    assert report["report_version"] == module.REPORT_VERSION
    assert summary["state_raw_snapshot_field_count"] >= 30
    assert summary["state_vector_v2_field_count"] >= 10
    assert summary["forecast_harvest_section_count"] == 4
    assert summary["forecast_harvest_field_count"] >= 20
    assert summary["advanced_input_collector_count"] == 3
    assert summary["relevant_test_file_count"] == len(module.RELEVANT_TEST_FILES_V1)
    assert summary["existing_relevant_test_file_count"] == len(module.RELEVANT_TEST_FILES_V1)
    assert len(inventories["state_execution_bridge_fields"]) == len(module.STATE_EXECUTION_BRIDGE_FIELDS_V1)
    assert len(inventories["advanced_input_activation_reasons"]) == len(module.ADVANCED_INPUT_ACTIVATION_REASONS_V1)
    assert assessment["recommended_next_step"] == "SF1_state_coverage_audit"


def test_write_state_forecast_validation_baseline_report_writes_json_csv_and_markdown(tmp_path):
    result = module.write_state_forecast_validation_baseline_report(
        output_dir=tmp_path,
        now=datetime.fromisoformat("2026-03-30T19:05:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["baseline_assessment"]["baseline_locked"] is True
    assert payload["baseline_summary"]["advanced_input_collector_count"] == 3

    markdown = md_path.read_text(encoding="utf-8")
    assert "State / Forecast Validation SF0 Baseline" in markdown
    assert "forecast_harvest_field_count" in markdown

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "advanced_input_collectors" in csv_text
    assert "state_execution_bridge_fields" in csv_text
