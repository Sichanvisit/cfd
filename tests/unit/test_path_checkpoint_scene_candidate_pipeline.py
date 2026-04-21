import json
from pathlib import Path

import pandas as pd

from backend.services.path_checkpoint_scene_candidate_pipeline import (
    build_checkpoint_scene_candidate_pipeline,
)


def _build_scene_row(
    *,
    index: int,
    symbol: str,
    surface_name: str,
    checkpoint_type: str,
    hindsight_scene_fine_label: str,
    runtime_scene_fine_label: str,
    runtime_scene_gate_label: str = "none",
    position_side: str = "BUY",
    unrealized_pnl_state: str = "OPEN_PROFIT",
    current_profit: float = 0.0,
    mfe_since_entry: float = 0.0,
    mae_since_entry: float = 0.0,
    giveback_ratio: float = 0.0,
    continuation: float = 0.5,
    reversal: float = 0.5,
    hold_quality: float = 0.4,
    partial_exit: float = 0.4,
    full_exit: float = 0.2,
) -> dict:
    return {
        "generated_at": f"2026-04-10T20:{index:02d}:00+09:00",
        "source": "scene_test",
        "symbol": symbol,
        "surface_name": surface_name,
        "leg_id": f"{symbol}_LEG_{index // 4}",
        "leg_direction": "UP",
        "checkpoint_id": f"{symbol}_CP_{index}",
        "checkpoint_type": checkpoint_type,
        "checkpoint_index_in_leg": (index % 5) + 1,
        "position_side": position_side,
        "unrealized_pnl_state": unrealized_pnl_state,
        "runner_secured": hindsight_scene_fine_label == "trend_exhaustion",
        "current_profit": current_profit,
        "mfe_since_entry": mfe_since_entry,
        "mae_since_entry": mae_since_entry,
        "giveback_ratio": giveback_ratio,
        "runtime_scene_coarse_family": "ENTRY_INITIATION",
        "runtime_scene_fine_label": runtime_scene_fine_label,
        "runtime_scene_gate_label": runtime_scene_gate_label,
        "runtime_scene_modifier_json": "{}",
        "runtime_scene_confidence": 0.72,
        "runtime_scene_confidence_band": "medium",
        "runtime_scene_action_bias_strength": "medium",
        "runtime_scene_source": "heuristic_v1",
        "runtime_scene_maturity": "probable",
        "runtime_scene_transition_from": "unresolved",
        "runtime_scene_transition_bars": 0,
        "runtime_scene_transition_speed": "fast",
        "runtime_scene_family_alignment": "aligned",
        "runtime_scene_gate_block_level": "entry_block" if runtime_scene_gate_label != "none" else "none",
        "hindsight_scene_fine_label": hindsight_scene_fine_label,
        "hindsight_scene_quality_tier": "auto_medium",
        "hindsight_scene_label_source": "scene_bootstrap_v1",
        "hindsight_scene_confidence": 0.74,
        "hindsight_scene_reason": "scene_test_fixture",
        "hindsight_scene_resolution_state": "bootstrap_confirmed",
        "runtime_hindsight_scene_match": runtime_scene_fine_label == hindsight_scene_fine_label,
        "runtime_proxy_management_action_label": "REBUY",
        "hindsight_best_management_action_label": "REBUY",
        "checkpoint_rule_family_hint": "scene_fixture",
        "exit_stage_family": "scene_fixture",
        "runtime_continuation_odds": continuation,
        "runtime_reversal_odds": reversal,
        "runtime_hold_quality_score": hold_quality,
        "runtime_partial_exit_ev": partial_exit,
        "runtime_full_exit_risk": full_exit,
    }


def _build_scene_dataset_fixture() -> pd.DataFrame:
    rows: list[dict] = []
    for idx in range(12):
        rows.append(
            _build_scene_row(
                index=idx,
                symbol="XAUUSD",
                surface_name="follow_through_surface",
                checkpoint_type="RECLAIM_CHECK",
                hindsight_scene_fine_label="breakout_retest_hold",
                runtime_scene_fine_label="breakout_retest_hold",
                position_side="FLAT",
                unrealized_pnl_state="FLAT",
                continuation=0.78,
                reversal=0.22,
                hold_quality=0.26,
                partial_exit=0.21,
                full_exit=0.08,
            )
        )
    for idx in range(12, 24):
        rows.append(
            _build_scene_row(
                index=idx,
                symbol="NAS100",
                surface_name="continuation_hold_surface",
                checkpoint_type="RUNNER_CHECK",
                hindsight_scene_fine_label="trend_exhaustion",
                runtime_scene_fine_label="trend_exhaustion",
                current_profit=0.24,
                mfe_since_entry=0.38,
                giveback_ratio=0.28,
                continuation=0.84,
                reversal=0.56,
                hold_quality=0.49,
                partial_exit=0.62,
                full_exit=0.24,
            )
        )
    for idx in range(24, 36):
        rows.append(
            _build_scene_row(
                index=idx,
                symbol="BTCUSD",
                surface_name="continuation_hold_surface",
                checkpoint_type="LATE_TREND_CHECK",
                hindsight_scene_fine_label="time_decay_risk",
                runtime_scene_fine_label="time_decay_risk",
                current_profit=0.03,
                mfe_since_entry=0.11,
                mae_since_entry=0.09,
                continuation=0.58,
                reversal=0.61,
                hold_quality=0.27,
                partial_exit=0.38,
                full_exit=0.31,
            )
        )
    for idx in range(36, 48):
        rows.append(
            _build_scene_row(
                index=idx,
                symbol="NAS100" if idx % 2 == 0 else "BTCUSD",
                surface_name="initial_entry_surface",
                checkpoint_type="INITIAL_PUSH",
                hindsight_scene_fine_label="unresolved",
                runtime_scene_fine_label="unresolved",
                runtime_scene_gate_label="low_edge_state",
                position_side="FLAT",
                unrealized_pnl_state="FLAT",
                current_profit=0.0,
                mfe_since_entry=0.0,
                mae_since_entry=0.0,
                continuation=0.44,
                reversal=0.39,
                hold_quality=0.19,
                partial_exit=0.12,
                full_exit=0.09,
            )
        )
    return pd.DataFrame(rows)


def test_build_checkpoint_scene_candidate_pipeline_writes_candidate_artifacts(tmp_path: Path) -> None:
    scene_dataset = _build_scene_dataset_fixture()
    candidate_root = tmp_path / "scene_candidates"

    manifest = build_checkpoint_scene_candidate_pipeline(
        scene_dataset,
        scene_eval_summary={
            "resolved_row_count": int(len(scene_dataset)),
            "runtime_scene_filled_row_count": int(len(scene_dataset)),
            "hindsight_scene_resolved_row_count": int((scene_dataset["hindsight_scene_fine_label"] != "unresolved").sum()),
            "runtime_hindsight_scene_match_rate": 1.0,
        },
        candidate_root=candidate_root,
        candidate_id="20260410_210000",
    )

    assert manifest["candidate_id"] == "20260410_210000"
    assert manifest["promotion_decision"]["decision"] == "shadow_only_first_candidate"

    metrics_path = Path(manifest["candidate_metrics_path"])
    compare_path = Path(manifest["compare_report_path"])
    promotion_path = Path(manifest["promotion_decision_path"])
    summary_path = Path(manifest["summary_md_path"])
    latest_run_path = candidate_root / "latest_candidate_run.json"

    assert metrics_path.exists()
    assert compare_path.exists()
    assert promotion_path.exists()
    assert summary_path.exists()
    assert latest_run_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["ready_task_count"] >= 3
    assert metrics["tasks"]["gate_task"]["skipped"] is False
    assert metrics["tasks"]["resolved_scene_task"]["skipped"] is False
