import pandas as pd

from backend.services.bounded_rollout_candidate_gate import (
    build_bounded_rollout_candidate_gate,
)
from backend.services.initial_entry_label_resolution_apply import (
    build_initial_entry_label_resolution_apply,
)
from backend.services.symbol_surface_preview_evaluation import (
    build_symbol_surface_preview_evaluation,
)


def test_initial_entry_label_resolution_apply_updates_rows_and_unblocks_nas_xau() -> None:
    initial_entry = pd.DataFrame(
        [
            {"preview_row_id": "btc-1", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "btc-2", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.8, "time_axis_phase": "late_initial"},
            {"preview_row_id": "btc-3", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "btc-4", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.7, "time_axis_phase": "late_initial"},
            {"preview_row_id": "btc-5", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "btc-6", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.7, "time_axis_phase": "late_initial"},
            {"preview_row_id": "btc-7", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "late_release", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "late_initial", "failure_label": "failed_follow_through"},
            {"preview_row_id": "btc-8", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "btc-9", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "btc-10", "symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "late_initial"},
            {"preview_row_id": "nas-1", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "nas-2", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "nas-3", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "nas-4", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "timing_better_entry", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "early_initial"},
            {"preview_row_id": "nas-5", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.8, "time_axis_phase": "late_initial"},
            {"preview_row_id": "nas-6", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.8, "time_axis_phase": "late_initial"},
            {"preview_row_id": "nas-7", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "late_initial", "failure_label": "missed_good_wait_release"},
            {"preview_row_id": "nas-8", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "timing_better_entry", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "nas-9", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "timing_better_entry", "action_target": "PROBE_ENTRY", "enter_now_binary": None, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "nas-10", "symbol": "NAS100", "market_family": "NAS100", "surface_state": "timing_better_entry", "action_target": "PROBE_ENTRY", "enter_now_binary": None, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "xau-1", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "xau-2", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "xau-3", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "initial_break", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"preview_row_id": "xau-4", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "timing_better_entry", "action_target": "ENTER_NOW", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "early_initial"},
            {"preview_row_id": "xau-5", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.8, "time_axis_phase": "late_initial"},
            {"preview_row_id": "xau-6", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "late_initial", "failure_label": "failed_follow_through"},
            {"preview_row_id": "xau-7", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "timing_better_entry", "action_target": "PROBE_ENTRY", "enter_now_binary": None, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "xau-8", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "timing_better_entry", "action_target": "PROBE_ENTRY", "enter_now_binary": None, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "xau-9", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "timing_better_entry", "action_target": "PROBE_ENTRY", "enter_now_binary": None, "training_weight": 0.45, "time_axis_phase": "early_initial"},
            {"preview_row_id": "xau-10", "symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "observe_filter", "action_target": "WAIT_MORE", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "late_initial", "failure_label": "late_entry_chase_fail"},
        ]
    )
    draft_payload = {
        "rows": [
            {"market_family": "NAS100", "preview_row_id": "nas-9", "adapter_mode": "nas_conflict_observe_adapter", "recommended_bias_action": "bias_release_wait", "proposed_action_target": "ENTER_NOW", "proposed_enter_now_binary": 1, "proposal_confidence": 0.62, "proposal_reason": "nas release wait"},
            {"market_family": "NAS100", "preview_row_id": "nas-10", "adapter_mode": "nas_conflict_observe_adapter", "recommended_bias_action": "bias_release_wait", "proposed_action_target": "ENTER_NOW", "proposed_enter_now_binary": 1, "proposal_confidence": 0.62, "proposal_reason": "nas release wait"},
            {"market_family": "XAUUSD", "preview_row_id": "xau-7", "adapter_mode": "xau_initial_entry_selective_adapter", "recommended_bias_action": "bias_initial_entry_selectivity", "proposed_action_target": "WAIT_MORE", "proposed_enter_now_binary": 0, "proposal_confidence": 0.64, "proposal_reason": "xau selective"},
            {"market_family": "XAUUSD", "preview_row_id": "xau-8", "adapter_mode": "xau_initial_entry_selective_adapter", "recommended_bias_action": "bias_initial_entry_selectivity", "proposed_action_target": "WAIT_MORE", "proposed_enter_now_binary": 0, "proposal_confidence": 0.64, "proposal_reason": "xau selective"},
            {"market_family": "XAUUSD", "preview_row_id": "xau-9", "adapter_mode": "xau_initial_entry_selective_adapter", "recommended_bias_action": "bias_initial_entry_selectivity", "proposed_action_target": "WAIT_MORE", "proposed_enter_now_binary": 0, "proposal_confidence": 0.64, "proposal_reason": "xau selective"},
        ]
    }
    adapter_payload = {
        "rows": [
            {"market_family": "BTCUSD", "surface_name": "initial_entry_surface", "adapter_mode": "btc_observe_relief_adapter", "recommended_bias_action": "bias_neutral", "objective_key": "entry_forward_ev", "current_focus": "btc"},
            {"market_family": "NAS100", "surface_name": "initial_entry_surface", "adapter_mode": "nas_conflict_observe_adapter", "recommended_bias_action": "bias_release_wait", "objective_key": "entry_forward_ev", "current_focus": "nas"},
            {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "adapter_mode": "xau_initial_entry_selective_adapter", "recommended_bias_action": "bias_initial_entry_selectivity", "objective_key": "entry_forward_ev", "current_focus": "xau"},
        ]
    }

    apply_frame, resolved_dataset, apply_summary = build_initial_entry_label_resolution_apply(
        initial_entry_dataset=initial_entry,
        initial_entry_label_resolution_draft_payload=draft_payload,
    )

    assert apply_summary["applied_row_count"] == 5
    nas_applied = resolved_dataset.loc[resolved_dataset["preview_row_id"] == "nas-9"].iloc[0]
    xau_applied = resolved_dataset.loc[resolved_dataset["preview_row_id"] == "xau-7"].iloc[0]
    assert nas_applied["action_target"] == "ENTER_NOW"
    assert nas_applied["enter_now_binary"] == 1
    assert xau_applied["action_target"] == "WAIT_MORE"
    assert xau_applied["enter_now_binary"] == 0
    assert xau_applied["adapter_mode"] == "xau_initial_entry_selective_adapter"
    assert xau_applied["recommended_bias_action"] == "bias_initial_entry_selectivity"

    eval_frame, _ = build_symbol_surface_preview_evaluation(
        initial_entry_dataset=resolved_dataset,
        follow_through_dataset=pd.DataFrame(),
        continuation_hold_dataset=pd.DataFrame(),
        protective_exit_dataset=pd.DataFrame(),
        failure_label_harvest_payload={"rows": []},
        distribution_promotion_gate_payload={"rows": []},
        market_adapter_layer_payload=adapter_payload,
    )
    gate_frame, summary = build_bounded_rollout_candidate_gate({"rows": eval_frame.to_dict(orient="records")})

    nas_eval = eval_frame.loc[(eval_frame["market_family"] == "NAS100") & (eval_frame["surface_name"] == "initial_entry_surface")].iloc[0]
    xau_eval = eval_frame.loc[(eval_frame["market_family"] == "XAUUSD") & (eval_frame["surface_name"] == "initial_entry_surface")].iloc[0]
    nas_gate = gate_frame.loc[(gate_frame["market_family"] == "NAS100") & (gate_frame["surface_name"] == "initial_entry_surface")].iloc[0]
    xau_gate = gate_frame.loc[(gate_frame["market_family"] == "XAUUSD") & (gate_frame["surface_name"] == "initial_entry_surface")].iloc[0]

    assert nas_eval["readiness_state"] == "preview_eval_ready"
    assert xau_eval["readiness_state"] == "preview_eval_ready"
    assert nas_gate["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE"
    assert xau_gate["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE"
    assert summary["review_canary_count"] == 3
