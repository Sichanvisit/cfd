import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_live_runner_pipeline.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_live_runner_pipeline", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_live_runner_pipeline_rebuilds_when_live_runner_present(tmp_path: Path) -> None:
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T16:10:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_runner",
                "surface_name": "continuation_hold_surface",
                "leg_id": "NAS100_UP_1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS100_UP_1_CP001",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_index_in_leg": 1,
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "avg_entry_price": 100.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "mfe_since_entry": 0.6,
                "mae_since_entry": -0.1,
                "current_profit": 0.3,
                "giveback_from_peak": 0.05,
                "giveback_ratio": 0.08,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "exit_stage_family": "runner",
                "runtime_continuation_odds": 0.75,
                "runtime_reversal_odds": 0.25,
                "runtime_hold_quality_score": 0.62,
                "runtime_partial_exit_ev": 0.41,
                "runtime_full_exit_risk": 0.17,
                "runtime_rebuy_readiness": 0.35,
                "management_action_label": "HOLD",
                "management_action_confidence": 0.8,
                "management_action_reason": "runner_locked_hold_continue",
                "management_action_score_gap": 0.2,
                "outcome": "runner_hold",
                "blocked_by": "runner_observe:no_exit",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(json.dumps({"updated_at": "2026-04-10T16:11:00+09:00"}), encoding="utf-8")

    watch_output_path = tmp_path / "watch.json"
    observation_output_path = tmp_path / "observation.json"
    management_output_path = tmp_path / "management.json"
    dataset_output_path = tmp_path / "checkpoint_dataset.csv"
    resolved_output_path = tmp_path / "checkpoint_dataset_resolved.csv"
    eval_output_path = tmp_path / "eval.json"
    pipeline_output_path = tmp_path / "pipeline.json"

    rc = module.main(
        [
            "--runtime-status-detail-path",
            str(runtime_status_detail_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--watch-output-path",
            str(watch_output_path),
            "--observation-output-path",
            str(observation_output_path),
            "--management-output-path",
            str(management_output_path),
            "--dataset-output-path",
            str(dataset_output_path),
            "--resolved-output-path",
            str(resolved_output_path),
            "--eval-output-path",
            str(eval_output_path),
            "--json-output-path",
            str(pipeline_output_path),
            "--skip-backfill",
        ]
    )

    assert rc == 0
    payload = json.loads(pipeline_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["rebuild_triggered"] is True
    assert payload["summary"]["live_runner_source_row_count"] == 1
    assert json.loads(observation_output_path.read_text(encoding="utf-8"))["summary"]["live_runner_source_row_count"] == 1
    assert json.loads(eval_output_path.read_text(encoding="utf-8"))["summary"]["resolved_row_count"] == 1


def test_build_checkpoint_live_runner_pipeline_supports_loop_iterations(tmp_path: Path) -> None:
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T16:10:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_hold",
                "surface_name": "continuation_hold_surface",
                "leg_id": "NAS100_UP_1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS100_UP_1_CP001",
                "checkpoint_type": "LATE_TREND_CHECK",
                "checkpoint_index_in_leg": 1,
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "avg_entry_price": 100.0,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": False,
                "mfe_since_entry": 0.4,
                "mae_since_entry": -0.1,
                "current_profit": 0.1,
                "giveback_from_peak": 0.0,
                "giveback_ratio": 0.0,
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "exit_stage_family": "hold",
                "management_action_label": "HOLD",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(json.dumps({"updated_at": "2026-04-10T16:11:00+09:00"}), encoding="utf-8")
    watch_output_path = tmp_path / "watch.json"
    pipeline_output_path = tmp_path / "pipeline.json"

    rc = module.main(
        [
            "--runtime-status-detail-path",
            str(runtime_status_detail_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--watch-output-path",
            str(watch_output_path),
            "--json-output-path",
            str(pipeline_output_path),
            "--skip-backfill",
            "--iterations",
            "2",
            "--sleep-seconds",
            "0",
        ]
    )

    assert rc == 0
    payload = json.loads(pipeline_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["iterations"] == 2
    assert payload["summary"]["sleep_seconds"] == 0
    assert len(payload["iteration_summaries"]) == 2
