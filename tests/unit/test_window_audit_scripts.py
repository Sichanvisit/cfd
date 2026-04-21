import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    script_path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chart_window_timebox_audit_script_writes_outputs(tmp_path):
    module = _load_script("build_chart_window_timebox_audit.py")
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "payload": {
                    "time": "2026-04-14T16:40:00",
                    "symbol": "NAS100",
                    "consumer_check_side": "BUY",
                    "consumer_check_stage": "PROBE",
                    "consumer_check_reason": "trend_resume_probe",
                    "outcome": "skipped",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = module.main(
        [
            "--detail-path",
            str(detail_path),
            "--symbol",
            "NAS100",
            "--start",
            "2026-04-14T16:35:00",
            "--end",
            "2026-04-14T16:45:00",
            "--window-id",
            "nas_resume",
            "--shadow-auto-dir",
            str(tmp_path),
            "--output-stem",
            "chart_window_script_test",
        ]
    )

    assert rc == 0
    payload = json.loads((tmp_path / "chart_window_script_test.json").read_text(encoding="utf-8"))
    assert payload["windows"][0]["window_id"] == "nas_resume"
    assert payload["windows"][0]["row_count"] == 1
    assert (tmp_path / "chart_window_script_test.md").exists()


def test_window_direction_numeric_audit_script_writes_outputs(tmp_path):
    module = _load_script("build_window_direction_numeric_audit.py")
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "payload": {
                    "time": "2026-04-15T02:00:00",
                    "symbol": "XAUUSD",
                    "leg_direction": "DOWN",
                    "breakout_candidate_direction": "DOWN",
                    "checkpoint_transition_reason": "checkpoint_continuation",
                    "core_reason": "directional_continuation_overlay_structural_promotion",
                    "box_state": "BELOW",
                    "bb_state": "LOWER_EDGE",
                    "consumer_check_side": "BUY",
                    "consumer_check_reason": "lower_break_fail_confirm",
                    "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
                    "belief_candidate_recommended_family": "reduce_alert",
                    "barrier_candidate_recommended_family": "block_bias",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = module.main(
        [
            "--detail-path",
            str(detail_path),
            "--symbol",
            "XAUUSD",
            "--start",
            "2026-04-15T01:59:00",
            "--end",
            "2026-04-15T02:05:00",
            "--window-id",
            "xau_down",
            "--expected-direction",
            "DOWN",
            "--shadow-auto-dir",
            str(tmp_path),
            "--output-stem",
            "window_direction_script_test",
        ]
    )

    assert rc == 0
    payload = json.loads((tmp_path / "window_direction_script_test.json").read_text(encoding="utf-8"))
    window = payload["windows"][0]
    assert window["window_id"] == "xau_down"
    assert window["candidate_threshold_hints_v1"]["calibration_state"] == "CONTINUATION_UNDER_VETO"
    assert (tmp_path / "window_direction_script_test.md").exists()
