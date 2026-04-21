from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa7_review_queue_packet import build_checkpoint_pa7_review_queue_packet


def test_build_checkpoint_pa7_review_queue_packet_groups_manual_exceptions() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "scene_candidate_selected_label": "trend_exhaustion",
                "scene_candidate_selected_confidence": 0.91,
                "runtime_hold_quality_score": 0.42,
                "runtime_partial_exit_ev": 0.56,
                "runtime_full_exit_risk": 0.21,
                "runtime_hindsight_match": False,
                "generated_at": "2026-04-10T23:00:00+09:00",
            },
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "scene_candidate_selected_label": "trend_exhaustion",
                "scene_candidate_selected_confidence": 0.89,
                "runtime_hold_quality_score": 0.44,
                "runtime_partial_exit_ev": 0.58,
                "runtime_full_exit_risk": 0.2,
                "runtime_hindsight_match": False,
                "generated_at": "2026-04-10T23:01:00+09:00",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_queue_packet(frame, top_n_groups=5, sample_rows_per_group=2)
    assert payload["summary"]["manual_exception_row_count"] == 2
    assert payload["summary"]["review_group_count"] == 1
    assert payload["group_rows"][0]["row_count"] == 2
    assert payload["group_rows"][0]["symbol"] == "NAS100"
