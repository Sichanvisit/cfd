import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_scene_candidate_pipeline.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_scene_candidate_pipeline", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_scene_candidate_pipeline_script_writes_manifest(tmp_path: Path) -> None:
    scene_dataset_path = tmp_path / "checkpoint_scene_dataset.csv"
    scene_eval_path = tmp_path / "checkpoint_scene_eval_latest.json"
    candidate_root = tmp_path / "scene_candidates"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T20:00:00+09:00",
                "source": "scene_test",
                "symbol": "XAUUSD",
                "surface_name": "follow_through_surface",
                "leg_id": "XAU_L1",
                "leg_direction": "UP",
                "checkpoint_id": "XAU_CP_1",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_index_in_leg": 1,
                "position_side": "FLAT",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "current_profit": 0.0,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.0,
                "runtime_scene_coarse_family": "ENTRY_INITIATION",
                "runtime_scene_fine_label": "breakout_retest_hold",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{}",
                "runtime_scene_confidence": 0.82,
                "runtime_scene_confidence_band": "high",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "confirmed",
                "runtime_scene_transition_from": "unresolved",
                "runtime_scene_transition_bars": 0,
                "runtime_scene_transition_speed": "fast",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "breakout_retest_hold",
                "hindsight_scene_quality_tier": "auto_medium",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.82,
                "hindsight_scene_reason": "fixture",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "REBUY",
                "hindsight_best_management_action_label": "REBUY",
                "checkpoint_rule_family_hint": "fixture",
                "exit_stage_family": "fixture",
                "runtime_continuation_odds": 0.76,
                "runtime_reversal_odds": 0.24,
                "runtime_hold_quality_score": 0.24,
                "runtime_partial_exit_ev": 0.18,
                "runtime_full_exit_risk": 0.08,
            },
            {
                "generated_at": "2026-04-10T20:01:00+09:00",
                "source": "scene_test",
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "leg_id": "NAS_L1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_CP_1",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_index_in_leg": 2,
                "position_side": "BUY",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "current_profit": 0.18,
                "mfe_since_entry": 0.31,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.22,
                "runtime_scene_coarse_family": "DEFENSIVE_EXIT",
                "runtime_scene_fine_label": "trend_exhaustion",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{}",
                "runtime_scene_confidence": 0.67,
                "runtime_scene_confidence_band": "medium",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "probable",
                "runtime_scene_transition_from": "runner_healthy",
                "runtime_scene_transition_bars": 1,
                "runtime_scene_transition_speed": "normal",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "trend_exhaustion",
                "hindsight_scene_quality_tier": "auto_medium",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.71,
                "hindsight_scene_reason": "fixture",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "checkpoint_rule_family_hint": "fixture",
                "exit_stage_family": "fixture",
                "runtime_continuation_odds": 0.84,
                "runtime_reversal_odds": 0.56,
                "runtime_hold_quality_score": 0.48,
                "runtime_partial_exit_ev": 0.62,
                "runtime_full_exit_risk": 0.21,
            },
            {
                "generated_at": "2026-04-10T20:02:00+09:00",
                "source": "scene_test",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "leg_id": "BTC_L1",
                "leg_direction": "UP",
                "checkpoint_id": "BTC_CP_1",
                "checkpoint_type": "LATE_TREND_CHECK",
                "checkpoint_index_in_leg": 3,
                "position_side": "BUY",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "current_profit": 0.02,
                "mfe_since_entry": 0.1,
                "mae_since_entry": 0.08,
                "giveback_ratio": 0.06,
                "runtime_scene_coarse_family": "POSITION_MANAGEMENT",
                "runtime_scene_fine_label": "time_decay_risk",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{}",
                "runtime_scene_confidence": 0.63,
                "runtime_scene_confidence_band": "medium",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "probable",
                "runtime_scene_transition_from": "unresolved",
                "runtime_scene_transition_bars": 0,
                "runtime_scene_transition_speed": "fast",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "time_decay_risk",
                "hindsight_scene_quality_tier": "auto_medium",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.63,
                "hindsight_scene_reason": "fixture",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "checkpoint_rule_family_hint": "fixture",
                "exit_stage_family": "fixture",
                "runtime_continuation_odds": 0.57,
                "runtime_reversal_odds": 0.61,
                "runtime_hold_quality_score": 0.25,
                "runtime_partial_exit_ev": 0.37,
                "runtime_full_exit_risk": 0.33,
            },
        ]
        * 10
    ).to_csv(scene_dataset_path, index=False, encoding="utf-8-sig")
    scene_eval_path.write_text(
        json.dumps(
            {
                "summary": {
                    "resolved_row_count": 30,
                    "runtime_scene_filled_row_count": 30,
                    "hindsight_scene_resolved_row_count": 30,
                    "runtime_hindsight_scene_match_rate": 1.0,
                },
                "rows": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    rc = module.main(
        [
            "--scene-dataset-path",
            str(scene_dataset_path),
            "--scene-eval-path",
            str(scene_eval_path),
            "--candidate-root",
            str(candidate_root),
            "--candidate-id",
            "20260410_220000",
        ]
    )

    assert rc == 0
    latest_run = json.loads((candidate_root / "latest_candidate_run.json").read_text(encoding="utf-8"))
    assert latest_run["candidate_id"] == "20260410_220000"
    assert Path(latest_run["candidate_metrics_path"]).exists()
