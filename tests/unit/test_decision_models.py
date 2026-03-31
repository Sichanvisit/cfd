import json
from types import SimpleNamespace

from backend.domain.decision_models import DecisionContext, DecisionResult, ExitProfile, WaitState
from backend.services.consumer_contract import CONSUMER_LAYER_MODE_INTEGRATION_V1
from backend.services.layer_mode_contract import (
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
)
from backend.services.entry_service import EntryService
from backend.services.exit_service import ExitService


class _DummyRuntime:
    def __init__(self):
        self.latest_signal_by_symbol = {}


class _DummyTradeLogger:
    pass


def test_decision_context_to_dict_roundtrip_shape():
    ctx = DecisionContext(
        symbol="NAS100",
        phase="entry",
        market_mode="RANGE",
        direction_policy="BOTH",
        raw_scores={"buy": 120, "sell": 80},
        thresholds={"entry": 45},
        metadata={"source": "unit"},
    )
    payload = ctx.to_dict()
    assert payload["symbol"] == "NAS100"
    assert payload["market_mode"] == "RANGE"
    assert payload["raw_scores"]["buy"] == 120


def test_entry_service_append_log_stores_dto_snapshots(monkeypatch):
    runtime = _DummyRuntime()
    svc = EntryService(runtime, _DummyTradeLogger())
    captured = {}
    monkeypatch.setattr(
        svc.decision_recorder,
        "append_entry_decision_log",
        lambda _row: captured.setdefault("row", dict(_row)),
    )

    svc._append_entry_decision_log(
        {
            "symbol": "NAS100",
            "action": "BUY",
            "outcome": "entered",
            "blocked_by": "",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "preflight_regime": "RANGE",
            "preflight_allowed_action": "BOTH",
            "preflight_liquidity": "OK",
            "macro_regime": "RANGE",
            "macro_zone": "LOWER",
            "volatility_state": "normal",
            "setup_id": "range_lower_reversal_buy",
            "setup_side": "BUY",
            "setup_status": "matched",
            "setup_trigger_state": "READY",
            "setup_score": 0.9,
            "setup_entry_quality": 0.9,
            "setup_reason": "range_lower_reversal",
            "entry_score_raw": 120.0,
            "contra_score_raw": 80.0,
            "effective_entry_threshold": 45.0,
            "base_entry_threshold": 45.0,
            "position_snapshot_v2": json.dumps(
                {"interpretation": {"primary_label": "ALIGNED_LOWER_WEAK"}, "energy": {"position_conflict_score": 0.0}}
            ),
            "response_raw_snapshot_v1": json.dumps({"bb20_lower_hold": 1.0, "box_lower_bounce": 0.8}),
            "response_vector_v2": json.dumps({"lower_hold_up": 1.0, "mid_reclaim_up": 0.3}),
            "state_raw_snapshot_v1": json.dumps({"market_mode": "RANGE", "s_conflict": 0.2}),
            "state_vector_v2": json.dumps({"range_reversal_gain": 1.18, "conflict_damp": 0.87}),
            "evidence_vector_v1": json.dumps({"buy_reversal_evidence": 0.84, "buy_total_evidence": 0.84}),
            "belief_state_v1": json.dumps({"buy_belief": 0.55, "buy_persistence": 0.4, "belief_spread": 0.55}),
            "barrier_state_v1": json.dumps({"buy_barrier": 0.10, "middle_chop_barrier": 0.05}),
            "forecast_features_v1": json.dumps(
                {
                    "position_primary_label": "ALIGNED_LOWER_WEAK",
                    "evidence_vector_v1": {"buy_total_evidence": 0.84},
                    "metadata": {
                        "signal_timeframe": "15M",
                        "signal_bar_ts": 1773149400,
                        "transition_horizon_bars": 3,
                        "management_horizon_bars": 6,
                    },
                }
            ),
            "transition_forecast_v1": json.dumps({"p_buy_confirm": 0.71, "forecast_contract": "transition_forecast_v1"}),
            "trade_management_forecast_v1": json.dumps({"p_continue_favor": 0.66, "forecast_contract": "trade_management_forecast_v1"}),
            "forecast_gap_metrics_v1": json.dumps(
                {
                    "transition_side_separation": 0.24,
                    "transition_confirm_fake_gap": 0.18,
                    "transition_reversal_continuation_gap": 0.29,
                    "management_continue_fail_gap": 0.33,
                    "management_recover_reentry_gap": 0.14,
                }
            ),
            "forecast_calibration_contract_v1": json.dumps({"contract_version": "forecast_calibration_v1", "live_action_gate_changed": False}),
            "outcome_labeler_scope_contract_v1": json.dumps(
                {
                    "contract_version": "outcome_labeler_scope_v1",
                    "offline_only": True,
                    "transition_label_rules_v1": {
                        "labels": {
                            "buy_confirm_success_label": {"forecast_probability_field": "p_buy_confirm"},
                            "continuation_success_label": {
                                "positive_rule": "continuation forecast is followed by meaningful same-direction extension within horizon while break or hold structure remains intact."
                            },
                        }
                    },
                    "management_label_rules_v1": {
                        "project_tp1_definition": {
                            "fallback_status_if_unobservable": "NO_EXIT_CONTEXT",
                        },
                        "labels": {
                            "continue_favor_label": {"forecast_probability_field": "p_continue_favor"},
                            "reach_tp1_label": {"tp1_definition_ref": "project_tp1_definition_v1"},
                        },
                    },
                    "ambiguity_and_censoring_rules_v1": {
                        "mandatory_statuses": [
                            "INSUFFICIENT_FUTURE_BARS",
                            "NO_EXIT_CONTEXT",
                            "NO_POSITION_CONTEXT",
                            "AMBIGUOUS",
                            "CENSORED",
                        ],
                        "status_precedence": [
                            "INVALID",
                            "NO_POSITION_CONTEXT",
                            "CENSORED",
                            "INSUFFICIENT_FUTURE_BARS",
                            "NO_EXIT_CONTEXT",
                            "AMBIGUOUS",
                            "VALID",
                        ],
                    },
                }
            ),
            "prs_canonical_state_field": "state_vector_v2",
            "prs_canonical_evidence_field": "evidence_vector_v1",
            "prs_canonical_belief_field": "belief_state_v1",
            "prs_canonical_barrier_field": "barrier_state_v1",
            "prs_canonical_forecast_features_field": "forecast_features_v1",
            "prs_canonical_transition_forecast_field": "transition_forecast_v1",
            "prs_canonical_trade_management_forecast_field": "trade_management_forecast_v1",
            "prs_canonical_forecast_gap_metrics_field": "forecast_gap_metrics_v1",
            "transition_side_separation": 0.24,
            "transition_confirm_fake_gap": 0.18,
            "transition_reversal_continuation_gap": 0.29,
            "management_continue_fail_gap": 0.33,
            "management_recover_reentry_gap": 0.14,
            "core_reason": "core_pass",
            "wait_score": 3.0,
            "wait_conflict": 2.0,
            "wait_noise": 1.0,
            "wait_penalty": 1.5,
            "prediction_bundle": json.dumps({"entry": {"p_win": 0.64}, "wait": {"p_better_entry_if_wait": 0.28}}),
        }
    )

    row = runtime.latest_signal_by_symbol["NAS100"]
    assert row["entry_decision_context_v1"]["market_mode"] == "RANGE"
    assert row["entry_decision_context_v1"]["metadata"]["position_snapshot_v2"]["interpretation"]["primary_label"] == "ALIGNED_LOWER_WEAK"
    assert row["entry_decision_context_v1"]["metadata"]["response_raw_snapshot_v1"]["bb20_lower_hold"] == 1.0
    assert row["entry_decision_context_v1"]["metadata"]["response_vector_v2"]["lower_hold_up"] == 1.0
    assert row["entry_decision_context_v1"]["metadata"]["state_raw_snapshot_v1"]["market_mode"] == "RANGE"
    assert row["entry_decision_context_v1"]["metadata"]["state_vector_v2"]["range_reversal_gain"] == 1.18
    assert row["entry_decision_context_v1"]["metadata"]["evidence_vector_v1"]["buy_reversal_evidence"] == 0.84
    assert row["entry_decision_context_v1"]["metadata"]["belief_state_v1"]["buy_belief"] == 0.55
    assert row["entry_decision_context_v1"]["metadata"]["barrier_state_v1"]["buy_barrier"] == 0.10
    assert row["entry_decision_context_v1"]["metadata"]["forecast_features_v1"]["position_primary_label"] == "ALIGNED_LOWER_WEAK"
    assert row["entry_decision_context_v1"]["metadata"]["transition_forecast_v1"]["p_buy_confirm"] == 0.71
    assert row["entry_decision_context_v1"]["metadata"]["trade_management_forecast_v1"]["p_continue_favor"] == 0.66
    assert row["entry_decision_context_v1"]["metadata"]["forecast_gap_metrics_v1"]["transition_side_separation"] == 0.24
    assert row["entry_decision_context_v1"]["metadata"]["forecast_calibration_contract_v1"]["contract_version"] == "forecast_calibration_v1"
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["contract_version"] == "outcome_labeler_scope_v1"
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["buy_confirm_success_label"]["forecast_probability_field"] == "p_buy_confirm"
    assert "same-direction extension" in row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["continuation_success_label"]["positive_rule"]
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["continue_favor_label"]["forecast_probability_field"] == "p_continue_favor"
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["reach_tp1_label"]["tp1_definition_ref"] == "project_tp1_definition_v1"
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["ambiguity_and_censoring_rules_v1"]["mandatory_statuses"][0] == "INSUFFICIENT_FUTURE_BARS"
    assert row["entry_decision_context_v1"]["metadata"]["outcome_labeler_scope_contract_v1"]["ambiguity_and_censoring_rules_v1"]["status_precedence"][-1] == "VALID"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_input_contract_field"] == "consumer_input_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_input_contract_v1"]["contract_version"] == "consumer_input_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_input_contract_v1"]["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_migration_freeze_field"] == "consumer_migration_freeze_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_migration_freeze_v1"]["contract_version"] == "consumer_migration_freeze_v1"
    assert row["entry_decision_context_v1"]["metadata"]["setup_detector_responsibility_contract_field"] == "setup_detector_responsibility_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["setup_detector_responsibility_contract_v1"]["contract_version"] == "setup_detector_responsibility_v1"
    assert row["entry_decision_context_v1"]["metadata"]["setup_detector_responsibility_contract_v1"]["scope"] == "setup_naming_only"
    assert row["entry_decision_context_v1"]["metadata"]["setup_mapping_contract_field"] == "setup_mapping_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["setup_mapping_contract_v1"]["contract_version"] == "setup_mapping_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["setup_mapping_contract_v1"]["canonical_mapping"][0]["archetype_id"] == "upper_reject_sell"
    assert row["entry_decision_context_v1"]["metadata"]["entry_guard_contract_field"] == "entry_guard_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["entry_guard_contract_v1"]["contract_version"] == "entry_guard_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["entry_guard_contract_v1"]["reason_registry"][0]["reason"] == "observe_confirm_missing"
    assert row["entry_decision_context_v1"]["metadata"]["entry_service_responsibility_contract_field"] == "entry_service_responsibility_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["entry_service_responsibility_contract_v1"]["contract_version"] == "entry_service_responsibility_v1"
    assert row["entry_decision_context_v1"]["metadata"]["entry_service_responsibility_contract_v1"]["scope"] == "execution_guard_only"
    assert row["entry_decision_context_v1"]["metadata"]["entry_service_responsibility_contract_v1"]["entry_guard_contract_v1"]["contract_version"] == "entry_guard_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["exit_handoff_contract_field"] == "exit_handoff_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["exit_handoff_contract_v1"]["contract_version"] == "exit_handoff_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["re_entry_contract_field"] == "re_entry_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["re_entry_contract_v1"]["contract_version"] == "re_entry_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["re_entry_contract_v1"]["required_current_state"]["same_archetype_confirm_required"] is True
    assert row["entry_decision_context_v1"]["metadata"]["consumer_logging_contract_field"] == "consumer_logging_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_logging_contract_v1"]["contract_version"] == "consumer_logging_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_test_contract_field"] == "consumer_test_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_test_contract_v1"]["contract_version"] == "consumer_test_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_freeze_handoff_field"] == "consumer_freeze_handoff_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_freeze_handoff_v1"]["contract_version"] == "consumer_freeze_handoff_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_contract_field"] == "layer_mode_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_contract_v1"]["contract_version"] == "layer_mode_contract_v1"
    assert [item["mode"] for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_contract_v1"]["canonical_modes"]] == ["shadow", "assist", "enforce"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_layer_inventory_field"] == "layer_mode_layer_inventory_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_layer_inventory_v1"]["contract_version"] == "layer_mode_layer_inventory_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_layer_inventory_v1"]["layer_order"] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_default_policy_field"] == "layer_mode_default_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_default_policy_v1"]["contract_version"] == "layer_mode_default_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_default_policy_v1"]["policy_rows"][2]["target_mode_sequence"] == ["assist", "enforce"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_dual_write_contract_field"] == "layer_mode_dual_write_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_dual_write_contract_v1"]["contract_version"] == "layer_mode_dual_write_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_influence_semantics_field"] == "layer_mode_influence_semantics_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_influence_semantics_v1"]["contract_version"] == "layer_mode_influence_semantics_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_application_contract_field"] == "layer_mode_application_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_application_contract_v1"]["contract_version"] == "layer_mode_application_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_contract_field"] == "layer_mode_identity_guard_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_overlay_output_contract_field"] == "layer_mode_policy_overlay_output_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_contract_field"] == "layer_mode_logging_replay_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_test_contract_field"] == "layer_mode_test_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_test_contract_v1"]["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_freeze_handoff_field"] == "layer_mode_freeze_handoff_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_freeze_handoff_v1"]["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_field"] == "layer_mode_scope_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["contract_version"] == "layer_mode_scope_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["layer_inventory_v1"]["contract_version"] == "layer_mode_layer_inventory_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["default_mode_policy_v1"]["contract_version"] == "layer_mode_default_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["dual_write_contract_v1"]["contract_version"] == "layer_mode_dual_write_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["influence_semantics_v1"]["contract_version"] == "layer_mode_influence_semantics_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["application_contract_v1"]["contract_version"] == "layer_mode_application_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["test_contract_v1"]["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["freeze_handoff_v1"]["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["compute_disable_allowed"] is False
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["policy_overlay_output_field"] == "layer_mode_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_scope_contract_v1"]["raw_output_policy"]["logging_replay_field"] == "layer_mode_logging_replay_v1"
    assert row["entry_decision_context_v1"]["metadata"]["position_snapshot_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["position_snapshot_v2"]
    assert row["entry_decision_context_v1"]["metadata"]["response_vector_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["response_vector_v2"]
    assert row["entry_decision_context_v1"]["metadata"]["state_vector_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["state_vector_v2"]
    assert row["entry_decision_context_v1"]["metadata"]["evidence_vector_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["evidence_vector_v1"]
    assert row["entry_decision_context_v1"]["metadata"]["belief_state_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["belief_state_v1"]
    assert row["entry_decision_context_v1"]["metadata"]["barrier_state_effective_v1"] == row["entry_decision_context_v1"]["metadata"]["barrier_state_v1"]
    assert row["entry_decision_context_v1"]["metadata"]["forecast_effective_policy_v1"]["policy_overlay_applied"] is True
    assert row["entry_decision_context_v1"]["metadata"]["forecast_effective_policy_v1"]["utility_overlay_applied"] is True
    assert row["entry_decision_context_v1"]["metadata"]["forecast_effective_policy_v1"]["current_effective_mode"] == "assist"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_effective_trace_field"] == "layer_mode_effective_trace_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_effective_trace_v1"]["layers"][0]["current_effective_mode"] == "enforce"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_influence_trace_field"] == "layer_mode_influence_trace_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_influence_trace_v1"]["layers"][0]["current_effective_mode"] == "enforce"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_application_trace_field"] == "layer_mode_application_trace_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_application_trace_v1"]["layers"][0]["application_state"] == "enforce_active"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_trace_v1"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_output_field"] == "layer_mode_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_v1"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_field"] == "layer_mode_logging_replay_v1"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_v1"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert next(
        item for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_influence_trace_v1"]["layers"] if item["layer"] == "Forecast"
    )["active_effects"] == ["confidence_modulation", "priority_boost", "reason_annotation"]
    assert next(
        item for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_application_trace_v1"]["layers"] if item["layer"] == "State"
    )["application_state"] == "assist_active"
    assert next(
        item for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_trace_v1"]["layers"] if item["layer"] == "Forecast"
    )["protected_fields"] == ["archetype_id", "side"]
    assert next(
        item for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_identity_guard_trace_v1"]["layers"] if item["layer"] == "Forecast"
    )["forbidden_adjustments"] == ["archetype_rewrite", "side_rewrite", "setup_rename", "execution_veto"]
    assert next(
        item for item in row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_v1"]["effective_influences"] if item["layer"] == "State"
    )["active_effects"] == ["confidence_modulation", "reason_annotation", "soft_warning"]
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_policy_v1"]["suppressed_reasons"] == []
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_v1"]["final_consumer_action"]["consumer_effective_action"] == "BUY"
    assert row["entry_decision_context_v1"]["metadata"]["layer_mode_logging_replay_v1"]["final_consumer_action"]["consumer_guard_result"] == "PASS"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_input_observe_confirm_field"] == "observe_confirm_v2"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_input_contract_version"] == "consumer_input_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_migration_contract_version"] == "consumer_migration_freeze_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_policy_input_field"] == "layer_mode_policy_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_policy_contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["consumer_policy_identity_preserved"] is True
    assert row["entry_decision_context_v1"]["metadata"]["consumer_guard_result"] == "PASS"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_effective_action"] == "BUY"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["contract_version"] == "consumer_scope_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["canonical_input_field"] == "observe_confirm_v2"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["layer_mode_integration_v1"]["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["setup_mapping_contract_v1"]["contract_version"] == "setup_mapping_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["entry_guard_contract_v1"]["contract_version"] == "entry_guard_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["exit_handoff_contract_v1"]["contract_version"] == "exit_handoff_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["re_entry_contract_v1"]["contract_version"] == "re_entry_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["migration_freeze_v1"]["contract_version"] == "consumer_migration_freeze_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["consumer_logging_contract_v1"]["contract_version"] == "consumer_logging_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["consumer_test_contract_v1"]["contract_version"] == "consumer_test_contract_v1"
    assert row["entry_decision_context_v1"]["metadata"]["consumer_scope_contract_v1"]["consumer_freeze_handoff_v1"]["contract_version"] == "consumer_freeze_handoff_v1"
    assert row["entry_decision_context_v1"]["metadata"]["forecast_features_v1"]["metadata"]["signal_timeframe"] == "15M"
    assert row["entry_decision_context_v1"]["metadata"]["forecast_features_v1"]["metadata"]["signal_bar_ts"] == 1773149400
    assert row["entry_decision_context_v1"]["metadata"]["forecast_features_v1"]["metadata"]["transition_horizon_bars"] == 3
    assert row["entry_decision_context_v1"]["metadata"]["forecast_features_v1"]["metadata"]["management_horizon_bars"] == 6
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_position_effective_field"] == "position_snapshot_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_response_effective_field"] == "response_vector_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_state_effective_field"] == "state_vector_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_state_field"] == "state_vector_v2"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_evidence_effective_field"] == "evidence_vector_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_evidence_field"] == "evidence_vector_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_belief_effective_field"] == "belief_state_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_belief_field"] == "belief_state_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_barrier_effective_field"] == "barrier_state_effective_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_barrier_field"] == "barrier_state_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_forecast_features_field"] == "forecast_features_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_transition_forecast_field"] == "transition_forecast_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_trade_management_forecast_field"] == "trade_management_forecast_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert row["entry_decision_context_v1"]["metadata"]["prs_canonical_forecast_effective_field"] == "forecast_effective_policy_v1"
    assert row["entry_decision_result_v1"]["wait_state"]["state"] == "CONFLICT"
    assert row["entry_decision_result_v1"]["selected_setup"]["setup_id"] == "range_lower_reversal_buy"
    assert row["entry_decision_result_v1"]["predictions"]["entry"]["p_win"] == 0.64
    assert captured["row"]["signal_timeframe"] == "15M"
    assert captured["row"]["signal_bar_ts"] == 1773149400


def test_exit_service_snapshot_stores_dto_snapshots():
    runtime = _DummyRuntime()
    svc = ExitService(runtime, _DummyTradeLogger())

    svc._snapshot_exit_evaluation(
        symbol="XAUUSD",
        trade_ctx={
            "box_state": "UPPER",
            "preflight_liquidity": "OK",
            "entry_setup_id": "range_upper_reversal_sell",
            "management_profile_id": "reversal_profile",
            "invalidation_id": "upper_break_reclaim",
            "exit_profile": "tight_protect",
        },
        stage_inputs={"regime_now": "TREND", "regime_at_entry": "RANGE", "profit": 0.5},
        chosen_stage="lock",
        policy_stage="mid",
        exec_profile="neutral",
        confirm_needed=3,
        exit_signal_score=155,
        score_gap=20,
        adverse_risk=True,
        tf_confirm=True,
        detail={"route_txt": "unit-route", "exit_threshold": 60, "reverse_signal_threshold": 110},
    )

    row = runtime.latest_signal_by_symbol["XAUUSD"]
    assert row["exit_manage_context_v1"]["contract_version"] == "exit_manage_context_v1"
    assert row["exit_manage_context_v1"]["posture"]["lifecycle_exit_profile"] == "tight_protect"
    assert row["exit_wait_taxonomy_v1"]["contract_version"] == "exit_wait_taxonomy_v1"
    assert row["exit_decision_context_v1"]["market_mode"] == "TREND"
    assert row["exit_decision_result_v1"]["exit_profile"]["policy_stage"] == "mid"
    assert row["exit_decision_result_v1"]["exit_profile"]["profile_id"] == "tight_protect"
    assert row["exit_decision_context_v1"]["metadata"]["management_profile_id"] == "reversal_profile"
    assert row["exit_decision_context_v1"]["metadata"]["invalidation_id"] == "upper_break_reclaim"
    assert row["exit_decision_context_v1"]["metadata"]["exit_handoff_contract_v1"]["contract_version"] == "exit_handoff_contract_v1"
    assert row["exit_decision_context_v1"]["metadata"]["consumer_freeze_handoff_v1"]["contract_version"] == "consumer_freeze_handoff_v1"
    assert row["exit_decision_result_v1"]["exit_profile"]["metadata"]["management_profile_id"] == "reversal_profile"
    assert row["exit_decision_result_v1"]["exit_profile"]["metadata"]["invalidation_id"] == "upper_break_reclaim"
    assert row["exit_decision_result_v1"]["exit_profile"]["metadata"]["exit_handoff_v1"]["handoff_source"] == "canonical_entry_handoff"
    assert (
        row["exit_decision_result_v1"]["exit_profile"]["metadata"]["exit_manage_context_v1"]["posture"]["lifecycle_exit_profile"]
        == "tight_protect"
    )
    assert row["exit_wait_state_v1"]["metadata"]["exit_manage_context_v1"]["handoff"]["management_profile_id"] == "reversal_profile"
    assert row["exit_wait_state_v1"]["metadata"]["exit_wait_taxonomy_v1"]["state"]["state_family"] == "neutral"
    assert row["exit_wait_state_family"] == "neutral"
    assert row["exit_wait_decision_family"] in {"hold_continue", "wait_exit", "exit_now", "reverse_now", "neutral"}
    assert row["exit_wait_state_v1"]["state"] == "NONE"
    assert row["exit_prediction_v1"]["exit"]["p_giveback"] > 0.0
    assert row["exit_utility_v1"]["winner"] in {"exit_now", "hold", "reverse", "wait_exit"}
    assert "utility_exit_now" in row["exit_decision_result_v1"]["metrics"]
