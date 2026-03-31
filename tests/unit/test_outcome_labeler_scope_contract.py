from pathlib import Path

from backend.services.outcome_labeler_contract import (
    OUTCOME_LABELER_AMBIGUITY_AND_CENSORING_RULES_V1,
    OUTCOME_LABEL_CONTRACT_V1,
    OUTCOME_LABELER_ANCHOR_DEFINITION_V1,
    OUTCOME_LABELER_ANCHOR_REQUIRED_FIELDS_V1,
    OUTCOME_LABELER_HORIZON_DEFINITION_V1,
    OUTCOME_LABELER_DATASET_BUILDER_BRIDGE_V1,
    OUTCOME_LABELER_LABEL_METADATA_V1,
    OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1,
    OUTCOME_LABELER_MANAGEMENT_LABELS_V1,
    OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1,
    OUTCOME_LABELER_SHADOW_OUTPUT_V1,
    OUTCOME_LABELER_SCOPE_CONTRACT_V1,
    OUTCOME_LABELER_TRANSITION_LABELS_V1,
    OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1,
    OUTCOME_LABELER_VALIDATION_REPORT_V1,
    OUTCOME_LABELING_PHILOSOPHY_V1,
    OUTCOME_LABEL_POLARITY_VALUES_V1,
    OUTCOME_LABEL_STATUS_VALUES_V1,
    build_outcome_signal_source_descriptor,
    build_management_anchor_descriptor,
    build_management_horizon_descriptor,
    build_transition_anchor_descriptor,
    build_transition_horizon_descriptor,
    is_outcome_label_status_scorable,
    normalize_outcome_label_status,
    outcome_labeling_ambiguity_doc_path,
    outcome_labeling_anchor_doc_path,
    outcome_labeling_dataset_builder_bridge_doc_path,
    outcome_labeling_horizon_doc_path,
    outcome_labeling_label_metadata_doc_path,
    outcome_labeling_management_rules_doc_path,
    outcome_labeling_philosophy_doc_path,
    outcome_labeling_shadow_output_doc_path,
    outcome_labeling_signal_source_doc_path,
    outcome_labeling_transition_rules_doc_path,
    outcome_labeling_validation_report_doc_path,
    resolve_management_label_rule_definition,
    resolve_entry_decision_anchor_time,
    resolve_outcome_label_polarity,
    resolve_outcome_label_status_from_flags,
    resolve_transition_label_rule_definition,
)


def test_outcome_labeler_scope_contract_freezes_l0_boundary():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1

    assert contract["contract_version"] == "outcome_labeler_scope_v1"
    assert contract["scope"] == "offline_forecast_scoring_only"
    assert contract["offline_only"] is True
    assert contract["live_action_gate_changed"] is False
    assert contract["anchor_basis"] == {
        "source": "entry_decisions.csv",
        "row_unit": "entry_decisions.csv row",
        "required_fields": list(OUTCOME_LABELER_ANCHOR_REQUIRED_FIELDS_V1),
        "optional_fields": ["signal_timeframe", "signal_bar_ts"],
        "timestamp_priority_fields": ["signal_bar_ts", "time"],
    }
    assert contract["future_source"] == {
        "source": "trade_closed_history.csv",
        "supporting_inputs": ["related_future_outcome"],
    }


def test_outcome_labeler_scope_contract_exposes_frozen_label_vocabulary():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1

    assert contract["label_contract_v1"] == OUTCOME_LABEL_CONTRACT_V1
    assert contract["label_families"]["transition"] == list(OUTCOME_LABELER_TRANSITION_LABELS_V1)
    assert contract["label_families"]["management"] == list(OUTCOME_LABELER_MANAGEMENT_LABELS_V1)
    assert contract["label_status_values"] == list(OUTCOME_LABEL_STATUS_VALUES_V1)
    assert contract["label_polarity_values"] == list(OUTCOME_LABEL_POLARITY_VALUES_V1)
    assert "label_contract_v1" in contract["completed_definitions"]
    assert "anchor_definition_v1" in contract["completed_definitions"]
    assert "horizon_definition_v1" in contract["completed_definitions"]
    assert "transition_label_rules_v1" in contract["completed_definitions"]
    assert "management_label_rules_v1" in contract["completed_definitions"]
    assert "ambiguity_and_censoring_rules_v1" in contract["completed_definitions"]
    assert "outcome_signal_source_v1" in contract["completed_definitions"]
    assert "outcome_labeler_v1_implementation" in contract["completed_definitions"]
    assert "label_metadata_v1" in contract["completed_definitions"]
    assert "shadow_label_output_v1" in contract["completed_definitions"]
    assert "dataset_builder_bridge_v1" in contract["completed_definitions"]
    assert "validation_report_v1" in contract["completed_definitions"]
    assert contract["outcome_labeler_v1_implementation"]["engine_file"] == "backend/trading/engine/offline/outcome_labeler.py"
    assert contract["outcome_labeler_v1_implementation"]["offline_only"] is True
    assert contract["deferred_definitions"] == []
    assert "live_action_gate_change" in contract["forbidden_changes"]
    assert "semantic_foundation_recomposition" in contract["forbidden_changes"]


def test_outcome_labeler_scope_contract_embeds_labeling_philosophy():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    philosophy = contract["labeling_philosophy_v1"]

    assert philosophy["contract_version"] == "outcome_labeling_philosophy_v1"
    assert philosophy["role_separation"]["shared_contract"] is True
    assert philosophy["role_separation"]["roles_are_inverse"] is True
    assert philosophy["role_separation"]["forecast_role"] == "present_scenario_score"
    assert philosophy["role_separation"]["outcome_labeler_role"] == "future_outcome_scoring"
    assert philosophy["polarity_values"] == list(OUTCOME_LABEL_POLARITY_VALUES_V1)
    assert philosophy["status_semantics"]["VALID"]["polarity_behavior"] == "POSITIVE or NEGATIVE"
    assert philosophy["status_semantics"]["CENSORED"]["polarity_behavior"] == "UNKNOWN"
    assert philosophy["status_semantics"]["INVALID"]["scorable"] is False
    assert philosophy["family_semantics"]["transition"]["positive_rule"] == "the transition event for that label occurs within horizon"
    assert philosophy["family_semantics"]["management"]["negative_rule"] == "the management horizon completes without that event"


def test_outcome_labeler_scope_contract_embeds_anchor_definition():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    anchor_definition = contract["anchor_definition_v1"]

    assert anchor_definition == OUTCOME_LABELER_ANCHOR_DEFINITION_V1
    assert anchor_definition["transition"]["anchor_row_source"] == "entry_decisions.csv"
    assert anchor_definition["transition"]["forecast_field"] == "transition_forecast_v1"
    assert anchor_definition["management"]["preferred_anchor_row_source"] == "entry_decisions.csv"
    assert anchor_definition["management"]["alternate_anchor_row_source"] == "position_open_event_row"
    assert anchor_definition["management"]["forecast_field"] == "trade_management_forecast_v1"
    assert "trade_closed_history.csv" in anchor_definition["supporting_result_sources"]


def test_outcome_labeler_scope_contract_embeds_horizon_definition():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    horizon_definition = contract["horizon_definition_v1"]

    assert horizon_definition == OUTCOME_LABELER_HORIZON_DEFINITION_V1
    assert horizon_definition["transition"]["window"] == "next_1_to_3_bars"
    assert horizon_definition["transition"]["horizon_bars"] == 3
    assert horizon_definition["management"]["window"] == "next_1_to_6_bars_or_position_close_capped"
    assert horizon_definition["management"]["horizon_bars"] == 6
    assert horizon_definition["management"]["position_close_boundary"] == "position_close_if_earlier_than_bar_6"
    assert horizon_definition["recommended_metadata"] == {
        "transition_horizon_bars": 3,
        "management_horizon_bars": 6,
    }


def test_outcome_labeler_scope_contract_embeds_transition_label_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    transition_rules = contract["transition_label_rules_v1"]

    assert transition_rules == OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1
    assert transition_rules["family"] == "transition"
    assert transition_rules["horizon_contract_ref"] == "horizon_definition_v1.transition"
    assert transition_rules["labels"]["buy_confirm_success_label"]["forecast_probability_field"] == "p_buy_confirm"
    assert "BUY_CONFIRM lifecycle appears" in transition_rules["labels"]["buy_confirm_success_label"]["positive_rule"]
    assert transition_rules["labels"]["false_break_label"]["forecast_probability_field"] == "p_false_break"
    assert "quickly invalidated" in transition_rules["labels"]["false_break_label"]["positive_rule"]
    assert transition_rules["labels"]["reversal_success_label"]["forecast_probability_field"] == "p_reversal_success"
    assert transition_rules["labels"]["continuation_success_label"]["forecast_probability_field"] == "p_continuation_success"


def test_outcome_labeler_scope_contract_embeds_management_label_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    management_rules = contract["management_label_rules_v1"]

    assert management_rules == OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1
    assert management_rules["family"] == "management"
    assert management_rules["horizon_contract_ref"] == "horizon_definition_v1.management"
    assert management_rules["project_tp1_definition"]["reference_name"] == "project_tp1_definition_v1"
    assert "Recovery TP1" in management_rules["project_tp1_definition"]["observable_sources"][1]
    assert management_rules["labels"]["continue_favor_label"]["forecast_probability_field"] == "p_continue_favor"
    assert "same-direction MFE materially exceeds adverse excursion" in management_rules["labels"]["continue_favor_label"]["positive_rule"]
    assert management_rules["labels"]["fail_now_label"]["forecast_probability_field"] == "p_fail_now"
    assert "immediate cut or exit outperforms holding" in management_rules["labels"]["fail_now_label"]["positive_rule"]
    assert management_rules["labels"]["recover_after_pullback_label"]["forecast_probability_field"] == "p_recover_after_pullback"
    assert management_rules["labels"]["reach_tp1_label"]["tp1_definition_ref"] == "project_tp1_definition_v1"
    assert management_rules["labels"]["opposite_edge_reach_label"]["forecast_probability_field"] == "p_opposite_edge_reach"
    assert management_rules["labels"]["better_reentry_if_cut_label"]["forecast_probability_field"] == "p_better_reentry_if_cut"


def test_outcome_labeler_scope_contract_embeds_ambiguity_and_censoring_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    ambiguity_rules = contract["ambiguity_and_censoring_rules_v1"]

    assert ambiguity_rules == OUTCOME_LABELER_AMBIGUITY_AND_CENSORING_RULES_V1
    assert ambiguity_rules["mandatory_statuses"] == [
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "NO_POSITION_CONTEXT",
        "AMBIGUOUS",
        "CENSORED",
    ]
    assert ambiguity_rules["status_precedence"] == [
        "INVALID",
        "NO_POSITION_CONTEXT",
        "CENSORED",
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "AMBIGUOUS",
        "VALID",
    ]
    assert "future bars have not accumulated" in ambiguity_rules["statuses"]["INSUFFICIENT_FUTURE_BARS"]["examples"][0]
    assert "position close log is missing" in ambiguity_rules["statuses"]["NO_EXIT_CONTEXT"]["examples"][0]
    assert "open and close" in ambiguity_rules["statuses"]["NO_POSITION_CONTEXT"]["examples"][0]
    assert "positive and negative path evidence" in ambiguity_rules["statuses"]["AMBIGUOUS"]["examples"][0]
    assert "future data stream is cut" in ambiguity_rules["statuses"]["CENSORED"]["examples"][0]


def test_outcome_labeler_scope_contract_embeds_outcome_signal_source_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    signal_source = contract["outcome_signal_source_v1"]

    assert signal_source == OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1
    assert signal_source["required_inputs"][0]["source"] == "entry_decisions.csv"
    assert signal_source["required_inputs"][0]["preferred_time_fields"] == ["signal_bar_ts", "time"]
    assert signal_source["required_inputs"][1]["source"] == "trade_closed_history.csv"
    assert signal_source["required_inputs"][1]["canonical_position_key_fields"] == ["ticket", "position_id"]
    assert signal_source["required_join_keys"]["ticket_or_position_id"] == "preferred canonical position key for deterministic linkage"
    assert signal_source["deterministic_join_order"][0]["failure_statuses"]["no_match"] == "NO_POSITION_CONTEXT"
    assert signal_source["deterministic_join_order"][1]["failure_statuses"]["missing_closed_row"] == "NO_EXIT_CONTEXT"
    assert signal_source["family_specific_usage"]["management"]["future_window_ref"] == "horizon_definition_v1.management"


def test_outcome_labeler_scope_contract_embeds_label_metadata_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    label_metadata = contract["label_metadata_v1"]

    assert label_metadata == OUTCOME_LABELER_LABEL_METADATA_V1
    assert label_metadata["family_metadata_fields"] == [
        "label_contract",
        "labeler_version",
        "anchor_timestamp",
        "horizon_bars",
        "future_window_start",
        "future_window_end",
        "source_files",
        "matched_outcome_rows",
        "label_reasons",
        "label_status_reason",
    ]
    assert label_metadata["per_label_reason_fields"] == [
        "reason_code",
        "reason_text",
        "evidence",
    ]
    assert "status_reason_is_required_for_non_scorable_rows" in label_metadata["principles"]


def test_outcome_labeler_scope_contract_embeds_shadow_output_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    shadow_output = contract["shadow_label_output_v1"]

    assert shadow_output == OUTCOME_LABELER_SHADOW_OUTPUT_V1
    assert shadow_output["row_type"] == "outcome_labels_v1"
    assert shadow_output["required_sections"] == [
        "decision_context",
        "forecast_snapshot",
        "outcome_labels_v1",
        "transition_label_summary",
        "management_label_summary",
    ]
    assert shadow_output["output_targets"]["analysis_dir"] == "data/analysis"
    assert "flat_comparison_columns" in shadow_output["future_extensions"]


def test_outcome_labeler_scope_contract_embeds_dataset_builder_bridge_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    dataset_bridge = contract["dataset_builder_bridge_v1"]

    assert dataset_bridge == OUTCOME_LABELER_DATASET_BUILDER_BRIDGE_V1
    assert dataset_bridge["builder_file"] == "backend/trading/engine/offline/replay_dataset_builder.py"
    assert dataset_bridge["row_type"] == "replay_dataset_row_v1"
    assert dataset_bridge["same_row_key_required"] is True
    assert dataset_bridge["required_sections"] == [
        "decision_row",
        "semantic_snapshots",
        "forecast_snapshots",
        "outcome_labels_v1",
    ]
    assert "observe_confirm_v1" in dataset_bridge["semantic_snapshot_fields"]
    assert "trade_management_forecast_v1" in dataset_bridge["forecast_snapshot_fields"]


def test_outcome_labeler_scope_contract_embeds_validation_report_rules():
    contract = OUTCOME_LABELER_SCOPE_CONTRACT_V1
    validation_report = contract["validation_report_v1"]

    assert validation_report == OUTCOME_LABELER_VALIDATION_REPORT_V1
    assert validation_report["report_type"] == "outcome_label_validation_report_v1"
    assert validation_report["input_row_type"] == "replay_dataset_row_v1"
    assert validation_report["required_sections"] == ["transition", "management"]
    assert validation_report["required_metrics"] == [
        "label_counts",
        "status_counts",
        "unknown_ratio",
        "censored_ratio",
        "symbol_distribution",
        "horizon_distribution",
    ]
    assert validation_report["alert_thresholds"]["high_unknown_ratio_warn"] == 0.40
    assert validation_report["output_targets"]["analysis_dir"] == "data/analysis"


def test_outcome_labeler_philosophy_helpers_resolve_status_and_polarity():
    assert normalize_outcome_label_status("valid") == "VALID"
    assert normalize_outcome_label_status("censored") == "CENSORED"
    assert normalize_outcome_label_status("no_position_context") == "NO_POSITION_CONTEXT"
    assert normalize_outcome_label_status("no_exit_context") == "NO_EXIT_CONTEXT"
    assert normalize_outcome_label_status("") == "INVALID"
    assert normalize_outcome_label_status("not_a_real_status") == "INVALID"

    assert resolve_outcome_label_polarity(label_status="VALID", label_value=True) == "POSITIVE"
    assert resolve_outcome_label_polarity(label_status="VALID", label_value=False) == "NEGATIVE"
    assert resolve_outcome_label_polarity(label_status="VALID", label_value=None) == "UNKNOWN"
    assert resolve_outcome_label_polarity(label_status="NO_POSITION_CONTEXT", label_value=True) == "UNKNOWN"
    assert resolve_outcome_label_polarity(label_status="NO_EXIT_CONTEXT", label_value=False) == "UNKNOWN"
    assert resolve_outcome_label_polarity(label_status="CENSORED", label_value=True) == "UNKNOWN"
    assert resolve_outcome_label_polarity(label_status="INVALID", label_value=False) == "UNKNOWN"
    assert is_outcome_label_status_scorable("VALID") is True
    assert is_outcome_label_status_scorable("AMBIGUOUS") is False
    assert is_outcome_label_status_scorable("NO_EXIT_CONTEXT") is False

    assert resolve_outcome_label_status_from_flags(is_invalid=True) == "INVALID"
    assert resolve_outcome_label_status_from_flags(has_position_context=False) == "NO_POSITION_CONTEXT"
    assert resolve_outcome_label_status_from_flags(is_censored=True, has_future_bars=False) == "CENSORED"
    assert resolve_outcome_label_status_from_flags(has_future_bars=False) == "INSUFFICIENT_FUTURE_BARS"
    assert resolve_outcome_label_status_from_flags(requires_exit_context=True, has_exit_context=False) == "NO_EXIT_CONTEXT"
    assert resolve_outcome_label_status_from_flags(is_ambiguous=True) == "AMBIGUOUS"
    assert resolve_outcome_label_status_from_flags() == "VALID"


def test_outcome_labeler_anchor_helpers_resolve_time_priority_and_family_descriptors():
    row = {
        "time": "2026-03-10T19:03:32",
        "signal_timeframe": "15M",
        "signal_bar_ts": 1773149400,
        "symbol": "NAS100",
        "action": "SELL",
        "setup_id": "range_upper_reversal_sell",
        "setup_side": "SELL",
    }
    fallback_row = {
        "time": "2026-03-10T19:03:32",
        "signal_bar_ts": "",
    }

    assert resolve_entry_decision_anchor_time(row) == ("signal_bar_ts", 1773149400)
    assert resolve_entry_decision_anchor_time(fallback_row) == ("time", "2026-03-10T19:03:32")

    transition = build_transition_anchor_descriptor(row)
    management = build_management_anchor_descriptor(fallback_row)

    assert transition["family"] == "transition"
    assert transition["anchor_time_field"] == "signal_bar_ts"
    assert transition["forecast_field"] == "transition_forecast_v1"
    assert transition["future_interval_end"] == "transition_horizon_close"

    assert management["family"] == "management"
    assert management["anchor_time_field"] == "time"
    assert management["alternate_anchor_row_source"] == "position_open_event_row"
    assert management["future_interval_end"] == "management_horizon_close_or_position_close"
    assert management["horizon_bars"] == 6

    transition_horizon = build_transition_horizon_descriptor()
    management_horizon = build_management_horizon_descriptor()

    assert transition_horizon["window"] == "next_1_to_3_bars"
    assert transition_horizon["horizon_bars"] == 3
    assert transition_horizon["recommended_metadata_field"] == "transition_horizon_bars"
    assert management_horizon["window"] == "next_1_to_6_bars_or_position_close_capped"
    assert management_horizon["horizon_bars"] == 6
    assert management_horizon["position_close_capped"] is True
    assert management_horizon["recommended_metadata_field"] == "management_horizon_bars"

    signal_source = build_outcome_signal_source_descriptor(row)

    assert signal_source["anchor_time_field"] == "signal_bar_ts"
    assert signal_source["symbol"] == "NAS100"
    assert signal_source["action"] == "SELL"
    assert signal_source["setup_id"] == "range_upper_reversal_sell"
    assert signal_source["setup_side"] == "SELL"
    assert signal_source["preferred_position_key_fields"] == ["ticket", "position_id"]
    assert signal_source["future_source_path_candidates"] == [
        "data/trades/trade_closed_history.csv",
        "trade_closed_history.csv",
    ]

    buy_confirm_rule = resolve_transition_label_rule_definition("buy_confirm_success_label")
    continuation_rule = resolve_transition_label_rule_definition("continuation_success_label")

    assert buy_confirm_rule["forecast_probability_field"] == "p_buy_confirm"
    assert "opposite-side dominance" in buy_confirm_rule["negative_rule"]
    assert continuation_rule["forecast_probability_field"] == "p_continuation_success"
    assert "same-direction extension" in continuation_rule["positive_rule"]
    assert resolve_transition_label_rule_definition("not_a_real_label") == {}

    continue_favor_rule = resolve_management_label_rule_definition("continue_favor_label")
    reach_tp1_rule = resolve_management_label_rule_definition("reach_tp1_label")

    assert continue_favor_rule["forecast_probability_field"] == "p_continue_favor"
    assert "immediate cut or exit would have been better than holding" in continue_favor_rule["negative_rule"]
    assert reach_tp1_rule["forecast_probability_field"] == "p_reach_tp1"
    assert reach_tp1_rule["tp1_definition_ref"] == "project_tp1_definition_v1"
    assert resolve_management_label_rule_definition("not_a_real_label") == {}


def test_outcome_labeler_philosophy_document_exists():
    doc_path = outcome_labeling_philosophy_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_labeling_philosophy.md"
    assert OUTCOME_LABELING_PHILOSOPHY_V1["documentation_path"] == "docs/outcome_labeler_labeling_philosophy.md"


def test_outcome_labeler_anchor_document_exists():
    doc_path = outcome_labeling_anchor_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_anchor_definition.md"


def test_outcome_labeler_horizon_document_exists():
    doc_path = outcome_labeling_horizon_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_horizon_definition.md"


def test_outcome_labeler_transition_rules_document_exists():
    doc_path = outcome_labeling_transition_rules_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_transition_label_rules.md"


def test_outcome_labeler_management_rules_document_exists():
    doc_path = outcome_labeling_management_rules_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_management_label_rules.md"


def test_outcome_labeler_ambiguity_document_exists():
    doc_path = outcome_labeling_ambiguity_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_ambiguity_censoring_rules.md"


def test_outcome_labeler_signal_source_document_exists():
    doc_path = outcome_labeling_signal_source_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_outcome_signal_source.md"


def test_outcome_labeler_label_metadata_document_exists():
    doc_path = outcome_labeling_label_metadata_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_label_metadata.md"


def test_outcome_labeler_shadow_output_document_exists():
    doc_path = outcome_labeling_shadow_output_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_shadow_output.md"


def test_outcome_labeler_dataset_builder_bridge_document_exists():
    doc_path = outcome_labeling_dataset_builder_bridge_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_dataset_builder_bridge.md"


def test_outcome_labeler_validation_report_document_exists():
    doc_path = outcome_labeling_validation_report_doc_path(Path(__file__).resolve().parents[2])

    assert doc_path.exists()
    assert doc_path.name == "outcome_labeler_validation_report.md"
