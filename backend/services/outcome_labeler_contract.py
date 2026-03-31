from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

OUTCOME_LABELER_TRANSITION_LABELS_V1 = (
    "buy_confirm_success_label",
    "sell_confirm_success_label",
    "false_break_label",
    "reversal_success_label",
    "continuation_success_label",
)

OUTCOME_LABELER_MANAGEMENT_LABELS_V1 = (
    "continue_favor_label",
    "fail_now_label",
    "recover_after_pullback_label",
    "reach_tp1_label",
    "opposite_edge_reach_label",
    "better_reentry_if_cut_label",
)

OUTCOME_LABELER_TRANSITION_FIELDS_V1 = OUTCOME_LABELER_TRANSITION_LABELS_V1 + (
    "label_status",
    "metadata",
)

OUTCOME_LABELER_MANAGEMENT_FIELDS_V1 = OUTCOME_LABELER_MANAGEMENT_LABELS_V1 + (
    "label_status",
    "metadata",
)

OUTCOME_LABEL_STATUS_VALUES_V1 = (
    "VALID",
    "INSUFFICIENT_FUTURE_BARS",
    "NO_POSITION_CONTEXT",
    "NO_EXIT_CONTEXT",
    "AMBIGUOUS",
    "CENSORED",
    "INVALID",
)

OUTCOME_LABEL_POLARITY_VALUES_V1 = (
    "POSITIVE",
    "NEGATIVE",
    "UNKNOWN",
)

OUTCOME_LABEL_UNKNOWN_STATUS_VALUES_V1 = (
    "INSUFFICIENT_FUTURE_BARS",
    "NO_POSITION_CONTEXT",
    "NO_EXIT_CONTEXT",
    "AMBIGUOUS",
    "CENSORED",
    "INVALID",
)

OUTCOME_LABELER_ANCHOR_REQUIRED_FIELDS_V1 = (
    "time",
    "symbol",
    "action",
    "forecast_features_v1",
    "transition_forecast_v1",
    "trade_management_forecast_v1",
    "forecast_gap_metrics_v1",
    "observe_confirm_v1",
)

OUTCOME_LABELER_OPTIONAL_ANCHOR_FIELDS_V1 = (
    "signal_timeframe",
    "signal_bar_ts",
)

OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1 = (
    "signal_bar_ts",
    "time",
)

OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1 = 3
OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1 = 6

OUTCOME_LABEL_CONTRACT_V1 = {
    "contract_version": "label_contract_v1",
    "bundle_type": "OutcomeLabelsV1",
    "transition_type": "TransitionOutcomeLabelsV1",
    "trade_management_type": "TradeManagementOutcomeLabelsV1",
    "transition_fields": list(OUTCOME_LABELER_TRANSITION_FIELDS_V1),
    "trade_management_fields": list(OUTCOME_LABELER_MANAGEMENT_FIELDS_V1),
    "label_status_values": list(OUTCOME_LABEL_STATUS_VALUES_V1),
}

OUTCOME_LABELING_PHILOSOPHY_V1 = {
    "contract_version": "outcome_labeling_philosophy_v1",
    "evaluation_question": "Was the forecast at anchor time correct about the realized future outcome within the explicit horizon?",
    "core_principles": [
        "label_scores_forecast_against_future_outcome",
        "semantic_layer_is_not_reinterpreted",
        "future_outcome_only",
        "explicit_horizon_required",
        "transition_and_management_are_labeled_separately",
        "binary_alone_is_insufficient",
    ],
    "role_separation": {
        "shared_contract": True,
        "forecast_role": "present_scenario_score",
        "outcome_labeler_role": "future_outcome_scoring",
        "roles_are_inverse": True,
    },
    "polarity_values": list(OUTCOME_LABEL_POLARITY_VALUES_V1),
    "polarity_criteria": {
        "positive": "label-specific success condition is satisfied within the explicit horizon and label_status == VALID",
        "negative": "explicit horizon is complete, label-specific success condition is not satisfied, and label_status == VALID",
        "unknown": "row is not safely scorable into positive or negative; any non-VALID label_status maps to UNKNOWN polarity",
    },
    "status_semantics": {
        "VALID": {
            "scorable": True,
            "polarity_behavior": "POSITIVE or NEGATIVE",
            "meaning": "future path is sufficient and unambiguous for scoring",
        },
        "INSUFFICIENT_FUTURE_BARS": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "future window ends before the label question can be answered",
        },
        "NO_POSITION_CONTEXT": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "the anchor row does not have enough position context to judge the label",
        },
        "NO_EXIT_CONTEXT": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "the future trade-management or exit context is missing for the label question",
        },
        "AMBIGUOUS": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "future path contains competing outcomes so the label cannot be judged uniquely",
        },
        "CENSORED": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "future path is truncated or censored by an external boundary",
        },
        "INVALID": {
            "scorable": False,
            "polarity_behavior": "UNKNOWN",
            "meaning": "anchor row or future outcome is malformed for label evaluation",
        },
    },
    "family_semantics": {
        "transition": {
            "question": "Did the predicted transition outcome occur within the transition horizon?",
            "positive_rule": "the transition event for that label occurs within horizon",
            "negative_rule": "the transition horizon completes without that event",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid",
        },
        "management": {
            "question": "Did the predicted trade-management outcome occur within the management horizon?",
            "positive_rule": "the management event for that label occurs within horizon",
            "negative_rule": "the management horizon completes without that event",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid",
        },
    },
    "documentation_path": "docs/outcome_labeler_labeling_philosophy.md",
}

OUTCOME_LABELER_TRANSITION_ANCHOR_DEFINITION_V1 = {
    "anchor_name": "transition_anchor_v1",
    "anchor_row_source": "entry_decisions.csv",
    "anchor_row_unit": "entry_decisions.csv row",
    "anchor_time_fields": list(OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1),
    "preferred_timeframe_field": "signal_timeframe",
    "forecast_field": "transition_forecast_v1",
    "future_interval": {
        "start": "first_future_bar_after_anchor",
        "end": "transition_horizon_close",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "horizon_contract_ref": "horizon_definition_v1",
    },
    "purpose": "score whether TransitionForecast was correct within the future transition window",
}

OUTCOME_LABELER_MANAGEMENT_ANCHOR_DEFINITION_V1 = {
    "anchor_name": "management_anchor_v1",
    "preferred_anchor_row_source": "entry_decisions.csv",
    "alternate_anchor_row_source": "position_open_event_row",
    "anchor_row_unit": "management decision reference row",
    "anchor_time_fields": list(OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1),
    "preferred_timeframe_field": "signal_timeframe",
    "forecast_field": "trade_management_forecast_v1",
    "future_interval": {
        "start": "anchor_time_while_position_is_live",
        "end": "management_horizon_close_or_position_close",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "position_close_capped": True,
        "horizon_contract_ref": "horizon_definition_v1",
    },
    "purpose": "score hold/fail/recover/tp1/reentry style forecasts while management context is active",
}

OUTCOME_LABELER_ANCHOR_DEFINITION_V1 = {
    "contract_version": "anchor_definition_v1",
    "shared_principles": [
        "transition_and_management_use_distinct_anchor_rules",
        "same_row_may_feed_both_families",
        "same_row_requires_family_specific_label_rules",
        "signal_bar_ts_is_preferred_when_available",
        "row_timestamp_is_fallback_anchor_time",
    ],
    "anchor_basis": {
        "source": "entry_decisions.csv",
        "row_unit": "entry_decisions.csv row",
        "required_fields": list(OUTCOME_LABELER_ANCHOR_REQUIRED_FIELDS_V1),
        "optional_fields": list(OUTCOME_LABELER_OPTIONAL_ANCHOR_FIELDS_V1),
        "timestamp_priority_fields": list(OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1),
    },
    "transition": dict(OUTCOME_LABELER_TRANSITION_ANCHOR_DEFINITION_V1),
    "management": dict(OUTCOME_LABELER_MANAGEMENT_ANCHOR_DEFINITION_V1),
    "supporting_result_sources": [
        "trade_closed_history.csv",
        "position_log",
        "exit_log",
        "closed_trade_result",
    ],
    "documentation_path": "docs/outcome_labeler_anchor_definition.md",
}

OUTCOME_LABELER_HORIZON_DEFINITION_V1 = {
    "contract_version": "horizon_definition_v1",
    "shared_principles": [
        "every_label_uses_an_explicit_future_window",
        "future_window_starts_on_bar_1_after_anchor",
        "transition_horizon_is_shorter_than_management_horizon",
        "management_horizon_is_capped_even_if_position_remains_open",
    ],
    "recommended_metadata": {
        "transition_horizon_bars": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "management_horizon_bars": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
    },
    "transition": {
        "family": "transition",
        "window": "next_1_to_3_bars",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "horizon_bars": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "evaluation_reason": "fast_confirm_or_fake_window",
        "negative_requires_full_window": True,
    },
    "management": {
        "family": "management",
        "window": "next_1_to_6_bars_or_position_close_capped",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "horizon_bars": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "position_close_boundary": "position_close_if_earlier_than_bar_6",
        "cap_rule": "cap_at_bar_6_even_if_position_remains_open",
        "evaluation_reason": "hold_cut_recover_tp1_reentry_window",
        "negative_requires_full_window": True,
    },
    "documentation_path": "docs/outcome_labeler_horizon_definition.md",
}

OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1 = {
    "contract_version": "transition_label_rules_v1",
    "family": "transition",
    "horizon_contract_ref": "horizon_definition_v1.transition",
    "label_status_contract_ref": "label_status_values",
    "shared_principles": [
        "score_realized_transition_outcome_against_transition_forecast",
        "use_future_outcome_only_within_transition_horizon",
        "effective_action_continuation_counts_as_confirm_success",
        "quick_invalidation_or_opposite_side_dominance_counts_against_confirm_or_continuation",
    ],
    "labels": {
        "buy_confirm_success_label": {
            "forecast_probability_field": "p_buy_confirm",
            "question": "Did the predicted buy-confirm path actually succeed within the transition horizon?",
            "positive_rule": "BUY_CONFIRM lifecycle appears, or equivalent buy-side action continuation holds, and the realized buy-side outcome is favorable within horizon.",
            "negative_rule": "predicted buy confirm is invalidated within horizon, flips quickly into fake behavior, or opposite-side dominance overtakes the buy path.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging buy confirm success.",
            "positive_signals": [
                "BUY_CONFIRM state is observed within horizon",
                "effective buy action continuation remains live within horizon",
                "buy-side realized outcome reaches the labeler's favorable threshold within horizon",
            ],
            "negative_signals": [
                "buy confirm setup is invalidated within horizon",
                "path rotates quickly into false-break or failed-confirm behavior",
                "sell-side or opposite-side outcome becomes dominant within horizon",
            ],
        },
        "sell_confirm_success_label": {
            "forecast_probability_field": "p_sell_confirm",
            "question": "Did the predicted sell-confirm path actually succeed within the transition horizon?",
            "positive_rule": "SELL_CONFIRM lifecycle appears, or equivalent sell-side action continuation holds, and the realized sell-side outcome is favorable within horizon.",
            "negative_rule": "predicted sell confirm is invalidated within horizon, flips quickly into fake behavior, or opposite-side dominance overtakes the sell path.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging sell confirm success.",
            "positive_signals": [
                "SELL_CONFIRM state is observed within horizon",
                "effective sell action continuation remains live within horizon",
                "sell-side realized outcome reaches the labeler's favorable threshold within horizon",
            ],
            "negative_signals": [
                "sell confirm setup is invalidated within horizon",
                "path rotates quickly into false-break or failed-confirm behavior",
                "buy-side or opposite-side outcome becomes dominant within horizon",
            ],
        },
        "false_break_label": {
            "forecast_probability_field": "p_false_break",
            "question": "Did the projected break or reclaim fail quickly enough to count as a false break within the transition horizon?",
            "positive_rule": "projected break, reclaim, or reject is quickly invalidated within horizon so continuation or confirm cannot hold and the structure returns or flips.",
            "negative_rule": "projected break or continuation remains valid through horizon without quick invalidation, structural return, or opposite takeover.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging false-break behavior.",
            "positive_signals": [
                "break, reclaim, or reject forecast is invalidated quickly within horizon",
                "continuation or confirm maintenance fails within horizon",
                "opposite signal appears or structure returns rapidly to the prior range",
            ],
            "negative_signals": [
                "break or continuation stays intact through the transition horizon",
                "no rapid invalidation or structural recovery occurs",
                "confirm path remains dominant rather than reverting",
            ],
        },
        "reversal_success_label": {
            "forecast_probability_field": "p_reversal_success",
            "question": "Did the predicted reversal lead to meaningful opposite-direction extension within the transition horizon?",
            "positive_rule": "reversal forecast is followed by meaningful opposite-direction follow-through within horizon after reclaim, reject, or edge reaction.",
            "negative_rule": "reversal forecast fails to generate meaningful opposite-direction extension within horizon and continuation, stall, or rejection of the reversal dominates instead.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging reversal success.",
            "positive_signals": [
                "middle reclaim or edge reject leads to extension in the opposite direction",
                "reversal direction keeps control for a meaningful portion of the horizon",
                "realized outcome supports the reversal side rather than the prior move",
            ],
            "negative_signals": [
                "expected opposite-direction extension never materializes",
                "prior direction resumes and dominates within horizon",
                "reversal attempt stalls or is rejected before meaningful follow-through",
            ],
        },
        "continuation_success_label": {
            "forecast_probability_field": "p_continuation_success",
            "question": "Did the predicted continuation hold and extend in the same direction within the transition horizon?",
            "positive_rule": "continuation forecast is followed by meaningful same-direction extension within horizon while break or hold structure remains intact.",
            "negative_rule": "continuation forecast loses structure, stalls, or reverses within horizon so same-direction follow-through does not hold.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging continuation success.",
            "positive_signals": [
                "same-direction extension persists within horizon",
                "break or hold structure stays valid within horizon",
                "realized outcome remains aligned with the forecast direction",
            ],
            "negative_signals": [
                "continuation structure breaks down within horizon",
                "same-direction follow-through stalls below the success threshold",
                "reversal or false-break behavior overtakes the projected continuation",
            ],
        },
    },
    "documentation_path": "docs/outcome_labeler_transition_label_rules.md",
}

OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1 = {
    "contract_version": "management_label_rules_v1",
    "family": "management",
    "horizon_contract_ref": "horizon_definition_v1.management",
    "label_status_contract_ref": "label_status_values",
    "shared_principles": [
        "score_realized_trade_management_outcome_against_trade_management_forecast",
        "hold_vs_immediate_cut_expected_value_is_part_of_scoring",
        "same_direction_mfe_vs_adverse_excursion_is_a_primary_observable",
        "position_close_can_end_the_management_horizon_early",
    ],
    "project_tp1_definition": {
        "reference_name": "project_tp1_definition_v1",
        "rule": "TP1 is reached when the project's canonical first-target event is observed within the management horizon.",
        "observable_sources": [
            "closed_trade_result.tp1_hit",
            "exit_log.close_reason == Recovery TP1",
            "profit >= Config.EXIT_RECOVERY_TP1_CLOSE_USD when recovery_tp1 path is active",
        ],
        "fallback_status_if_unobservable": "NO_EXIT_CONTEXT",
    },
    "labels": {
        "continue_favor_label": {
            "forecast_probability_field": "p_continue_favor",
            "question": "Was holding from the management anchor still favorable versus immediate cut within the management horizon?",
            "positive_rule": "holding from anchor keeps the dominant side favorable, same-direction MFE materially exceeds adverse excursion, and no rapid failure forces an early exit within horizon.",
            "negative_rule": "holding loses edge within horizon because adverse excursion dominates, rapid failure appears, or immediate cut or exit would have been better than holding.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging whether holding remained favorable.",
            "positive_signals": [
                "same-direction MFE exceeds MAE by the labeler's materiality threshold within horizon",
                "no fail-now event invalidates the hold path before meaningful extension",
                "the held path preserves the dominant direction and extends without rapid failure",
            ],
            "negative_signals": [
                "adverse excursion dominates before meaningful same-direction extension",
                "management path breaks quickly into fail-now or forced-exit behavior",
                "immediate cut or exit would have outperformed passive hold within horizon",
            ],
        },
        "fail_now_label": {
            "forecast_probability_field": "p_fail_now",
            "question": "Did the position fail quickly enough that immediate cut or exit was the better action within the management horizon?",
            "positive_rule": "the path invalidates quickly after anchor, a materially adverse move arrives before favorable follow-through, and immediate cut or exit outperforms holding within horizon.",
            "negative_rule": "no rapid failure occurs within horizon because holding remains competitive, the trade stabilizes, or recovery and continuation dominate instead.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging fail-now behavior.",
            "positive_signals": [
                "rapid adverse move appears before favorable extension",
                "hold path is invalidated quickly after anchor",
                "realized outcome shows immediate cut or exit would have been better than hold",
            ],
            "negative_signals": [
                "same-direction hold remains viable within horizon",
                "no quick invalidation or early failure appears",
                "recovery or continuation dominates over immediate cut",
            ],
        },
        "recover_after_pullback_label": {
            "forecast_probability_field": "p_recover_after_pullback",
            "question": "Did the trade recover after an initial pullback strongly enough that holding beat immediate cut within the management horizon?",
            "positive_rule": "an initial wobble, pullback, or adverse excursion occurs after anchor, but the path recovers back into the dominant direction and holding outperforms immediate cut within horizon.",
            "negative_rule": "after the initial pullback the trade does not recover meaningfully within horizon, so cut, exit, or reentry dominates the held path.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging pullback recovery.",
            "positive_signals": [
                "initial pullback or MAE occurs soon after anchor",
                "dominant-direction control returns within horizon",
                "holding through the pullback beats immediate cut on realized outcome",
            ],
            "negative_signals": [
                "pullback turns into sustained failure rather than recovery",
                "dominant-direction recovery does not regain control within horizon",
                "cut or reentry outperforms holding through the pullback",
            ],
        },
        "reach_tp1_label": {
            "forecast_probability_field": "p_reach_tp1",
            "question": "Did the realized path reach the project's canonical TP1 event within the management horizon?",
            "positive_rule": "the canonical project TP1 event is observed within horizon according to the project's TP1 definition.",
            "negative_rule": "the management horizon completes without a canonical TP1 hit, or the position closes for another outcome before TP1 is reached.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, invalid, or missing canonical TP1 observables for judging TP1 reach.",
            "tp1_definition_ref": "project_tp1_definition_v1",
            "positive_signals": [
                "closed trade result marks tp1_hit within horizon",
                "exit log records close_reason == Recovery TP1 within horizon",
                "realized profit satisfies the project's canonical TP1 threshold within horizon",
            ],
            "negative_signals": [
                "horizon closes without a TP1 hit",
                "position closes for another reason before TP1 is reached",
                "fail-now or non-TP1 management path dominates before TP1 becomes observable",
            ],
        },
        "opposite_edge_reach_label": {
            "forecast_probability_field": "p_opposite_edge_reach",
            "question": "Did the realized management path reach the opposite edge of the active range or continuation structure within the management horizon?",
            "positive_rule": "within horizon the realized path travels far enough to reach the opposite edge implied by the active range or continuation structure.",
            "negative_rule": "the opposite edge is not reached before the management horizon closes or the position closes.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging opposite-edge reach.",
            "positive_signals": [
                "range or continuation structure reaches its opposite edge within horizon",
                "wait or exit evaluation marks reached_opposite_edge == True",
                "realized travel distance satisfies the project's opposite-edge event",
            ],
            "negative_signals": [
                "path stalls before the opposite edge is reached",
                "position closes early without touching the opposite edge",
                "reversal or failure interrupts the projected edge travel",
            ],
        },
        "better_reentry_if_cut_label": {
            "forecast_probability_field": "p_better_reentry_if_cut",
            "question": "Would cutting at the anchor and re-entering later have beaten passive hold within the management horizon?",
            "positive_rule": "holding from anchor is inefficient within horizon, a later reentry point appears with better realized expectancy, and cut-plus-reentry outperforms simple hold.",
            "negative_rule": "passive hold is at least as good as cutting and re-entering later, or no materially better reentry opportunity emerges within horizon.",
            "unknown_rule": "future path is insufficient, ambiguous, censored, or invalid for judging reentry advantage.",
            "positive_signals": [
                "immediate hold underperforms a later reentry path within horizon",
                "a materially better reentry level appears after cutting",
                "cut-plus-reentry realized expectancy exceeds passive hold",
            ],
            "negative_signals": [
                "hold path remains competitive or better than cut-plus-reentry",
                "no materially better reentry point appears within horizon",
                "recovery after pullback rewards holding rather than cutting",
            ],
        },
    },
    "documentation_path": "docs/outcome_labeler_management_label_rules.md",
}

OUTCOME_LABELER_AMBIGUITY_AND_CENSORING_RULES_V1 = {
    "contract_version": "ambiguity_and_censoring_rules_v1",
    "mandatory_statuses": [
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "NO_POSITION_CONTEXT",
        "AMBIGUOUS",
        "CENSORED",
    ],
    "resolution_principles": [
        "do_not_force_binary_label_when_row_is_not_safely_scorable",
        "prefer_exclusion_over_noisy_supervision",
        "only_valid_rows_may_emit_positive_or_negative_label_value",
        "if_multiple_non_scorable_conditions_apply_use_status_precedence",
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
    "statuses": {
        "INSUFFICIENT_FUTURE_BARS": {
            "trigger": "future bars do not fully cover the required horizon and no earlier legitimate boundary closes the question",
            "examples": [
                "future bars have not accumulated through the full horizon yet",
                "horizon needs 6 bars but only 2 future bars are present",
            ],
            "label_action": "set label_value to None and exclude from binary training or calibration score sets",
        },
        "NO_EXIT_CONTEXT": {
            "trigger": "required exit, close, TP1, or closed-trade observables are missing even though the row otherwise has enough future window",
            "examples": [
                "position close log is missing",
                "TP1 label needs exit context but no canonical TP1 observable is linked",
            ],
            "label_action": "set label_value to None and exclude from binary training or calibration score sets",
        },
        "NO_POSITION_CONTEXT": {
            "trigger": "anchor row cannot be linked to the required live-position or open-position context for that label family",
            "examples": [
                "open and close events cannot be joined to the anchor row",
                "management label cannot confirm there was a live position context at anchor",
            ],
            "label_action": "set label_value to None and exclude from binary training or calibration score sets",
        },
        "AMBIGUOUS": {
            "trigger": "positive and negative interpretations both remain plausible, competing sources disagree, or no unique judgment can be made",
            "examples": [
                "positive and negative path evidence are both materially satisfied within horizon",
                "multiple candidate joins or conflicting future sources prevent a unique outcome",
            ],
            "label_action": "set label_value to None and exclude from binary training or calibration score sets",
        },
        "CENSORED": {
            "trigger": "future path is truncated by a data gap, export cutoff, session boundary, or other external interruption before safe scoring",
            "examples": [
                "future data stream is cut in the middle of the scoring window",
                "dataset ends or a continuity gap appears before the label can be judged safely",
            ],
            "label_action": "set label_value to None and exclude from binary training or calibration score sets",
        },
    },
    "family_notes": {
        "transition": [
            "INSUFFICIENT_FUTURE_BARS is the common fallback when the 1 to 3 bar transition window is incomplete",
            "AMBIGUOUS applies when confirm, fake, reversal, or continuation outcomes compete without a unique winner",
        ],
        "management": [
            "NO_EXIT_CONTEXT is common when TP1, close, or realized management outcome cannot be linked",
            "CENSORED applies when the management window is interrupted before hold, cut, recovery, or reentry can be judged safely",
        ],
    },
    "documentation_path": "docs/outcome_labeler_ambiguity_censoring_rules.md",
}

OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1 = {
    "contract_version": "outcome_signal_source_v1",
    "required_inputs": [
        {
            "source": "entry_decisions.csv",
            "path_candidates": [
                "data/trades/entry_decisions.csv",
            ],
            "role": "anchor_forecast_row",
            "required_fields": [
                "symbol",
                "action",
                "time",
                "transition_forecast_v1",
                "trade_management_forecast_v1",
            ],
            "preferred_time_fields": [
                "signal_bar_ts",
                "time",
            ],
            "supporting_bridge_fields": [
                "signal_timeframe",
                "setup_id",
                "setup_side",
            ],
        },
        {
            "source": "trade_closed_history.csv",
            "path_candidates": [
                "data/trades/trade_closed_history.csv",
                "trade_closed_history.csv",
            ],
            "role": "primary_future_outcome",
            "required_fields": [
                "ticket",
                "symbol",
                "direction",
                "open_time",
                "open_ts",
                "close_time",
                "close_ts",
                "status",
            ],
            "canonical_position_key_fields": [
                "ticket",
                "position_id",
            ],
        },
    ],
    "optional_inputs": [
        {
            "source": "runtime_snapshot_archive",
            "role": "bridge_anchor_to_position_context",
        },
        {
            "source": "position_lifecycle_log",
            "role": "bridge_anchor_to_position_context",
        },
        {
            "source": "exit_log",
            "role": "bridge_position_to_exit_context",
        },
    ],
    "required_join_keys": {
        "symbol": "required anchor and future identity key",
        "timestamp": "anchor row time fallback and future open or close time reference",
        "signal_bar_ts": "preferred anchor timestamp when available",
        "ticket_or_position_id": "preferred canonical position key for deterministic linkage",
        "setup_side_action": "setup_id, setup_side, and action stabilize same-symbol joins",
    },
    "deterministic_join_order": [
        {
            "stage": "anchor_to_position_context",
            "preferred_match": "exact ticket or position_id match when the anchor row is enriched or an optional bridge source provides it",
            "fallback_match": "same symbol plus aligned action or direction plus nearest non-negative open_ts or open_time from anchor_time",
            "supporting_fields": [
                "setup_id",
                "setup_side",
                "signal_timeframe",
            ],
            "tie_break_order": [
                "smallest_non_negative_open_time_distance_from_anchor",
                "exact_action_direction_alignment",
                "exact_setup_side_alignment_when_available",
                "latest_open_ts",
                "highest_ticket",
            ],
            "failure_statuses": {
                "no_match": "NO_POSITION_CONTEXT",
                "multiple_equal_matches": "AMBIGUOUS",
            },
        },
        {
            "stage": "position_context_to_closed_outcome",
            "preferred_match": "ticket or position_id to trade_closed_history.csv",
            "fallback_match": "same symbol, direction, and resolved open_ts or open_time when canonical ticket is absent",
            "required_future_fields": [
                "ticket",
                "symbol",
                "direction",
                "open_time",
                "open_ts",
                "close_time",
                "close_ts",
                "status",
            ],
            "tie_break_order": [
                "exact_ticket_or_position_id",
                "exact_open_ts",
                "smallest_abs_open_time_distance",
                "latest_close_ts",
            ],
            "failure_statuses": {
                "missing_closed_row": "NO_EXIT_CONTEXT",
                "multiple_equal_matches": "AMBIGUOUS",
            },
        },
    ],
    "family_specific_usage": {
        "transition": {
            "anchor_use": "entry_decisions.csv row drives transition grading",
            "future_window_ref": "horizon_definition_v1.transition",
            "primary_observables": [
                "future bars after anchor",
                "trade_closed_history.csv outcome when a position is opened or closed inside the transition window",
            ],
        },
        "management": {
            "anchor_use": "entry_decisions.csv row or resolved live position context drives management grading",
            "future_window_ref": "horizon_definition_v1.management",
            "primary_observables": [
                "trade_closed_history.csv close context",
                "optional exit or lifecycle logs when management observables need richer context",
            ],
        },
    },
    "source_hardening_guidance": [
        "prefer signal_bar_ts over row time for anchor alignment",
        "persist ticket or position_id onto entry_decisions.csv when available, without changing the live action gate",
        "if neither canonical position keys nor deterministic symbol-side-time bridges are available, exclude the row rather than forcing a join",
    ],
    "documentation_path": "docs/outcome_labeler_outcome_signal_source.md",
}

OUTCOME_LABELER_IMPLEMENTATION_V1 = {
    "contract_version": "outcome_labeler_implementation_v1",
    "engine_file": "backend/trading/engine/offline/outcome_labeler.py",
    "bundle_function": "build_outcome_labels",
    "transition_function": "label_transition_outcomes",
    "management_function": "label_management_outcomes",
    "offline_only": True,
    "live_engine_integration": False,
}

OUTCOME_LABELER_LABEL_METADATA_V1 = {
    "contract_version": "label_metadata_v1",
    "family_metadata_fields": [
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
    ],
    "per_label_reason_fields": [
        "reason_code",
        "reason_text",
        "evidence",
    ],
    "principles": [
        "metadata_must_explain_positive_negative_and_unknown_outcomes",
        "status_reason_is_required_for_non_scorable_rows",
        "matched_rows_and_source_files_must_be_traceable",
        "reason_text_and_reason_code_should_coexist",
    ],
    "documentation_path": "docs/outcome_labeler_label_metadata.md",
}

OUTCOME_LABELER_SHADOW_OUTPUT_V1 = {
    "contract_version": "shadow_label_output_v1",
    "row_type": "outcome_labels_v1",
    "required_sections": [
        "decision_context",
        "forecast_snapshot",
        "outcome_labels_v1",
        "transition_label_summary",
        "management_label_summary",
    ],
    "output_targets": {
        "analysis_dir": "data/analysis",
        "replay_dataset_intermediate": "data/datasets/replay_intermediate",
    },
    "review_goal": "make a single forecast row reviewable against later realized outcome labels",
    "future_extensions": [
        "flat_comparison_columns",
    ],
    "documentation_path": "docs/outcome_labeler_shadow_output.md",
}

OUTCOME_LABELER_DATASET_BUILDER_BRIDGE_V1 = {
    "contract_version": "dataset_builder_bridge_v1",
    "builder_file": "backend/trading/engine/offline/replay_dataset_builder.py",
    "row_type": "replay_dataset_row_v1",
    "same_row_key_required": True,
    "row_key_components": [
        "symbol",
        "anchor_time_field",
        "anchor_time_value",
        "action",
        "setup_id",
        "ticket_or_position_id",
    ],
    "required_sections": [
        "decision_row",
        "semantic_snapshots",
        "forecast_snapshots",
        "outcome_labels_v1",
    ],
    "semantic_snapshot_fields": [
        "position_snapshot_v2",
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "observe_confirm_v1",
    ],
    "forecast_snapshot_fields": [
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ],
    "output_targets": {
        "builder_input_file": "backend/trading/engine/offline/replay_dataset_builder.py",
        "replay_dataset_intermediate": "data/datasets/replay_intermediate",
    },
    "documentation_path": "docs/outcome_labeler_dataset_builder_bridge.md",
}

OUTCOME_LABELER_VALIDATION_REPORT_V1 = {
    "contract_version": "validation_report_v1",
    "report_type": "outcome_label_validation_report_v1",
    "input_row_type": "replay_dataset_row_v1",
    "required_sections": [
        "transition",
        "management",
    ],
    "required_metrics": [
        "label_counts",
        "status_counts",
        "unknown_ratio",
        "censored_ratio",
        "symbol_distribution",
        "horizon_distribution",
    ],
    "alert_thresholds": {
        "high_unknown_ratio_warn": 0.40,
        "high_unknown_ratio_fail": 0.60,
        "label_side_skew_ratio_warn": 0.90,
        "label_side_skew_ratio_fail": 0.98,
        "symbol_min_scorable_rows_warn": 3,
    },
    "output_targets": {
        "analysis_dir": "data/analysis",
    },
    "documentation_path": "docs/outcome_labeler_validation_report.md",
}

OUTCOME_LABELER_SCOPE_CONTRACT_V1 = {
    "contract_version": "outcome_labeler_scope_v1",
    "scope": "offline_forecast_scoring_only",
    "anchor_basis": {
        "source": "entry_decisions.csv",
        "row_unit": "entry_decisions.csv row",
        "required_fields": list(OUTCOME_LABELER_ANCHOR_REQUIRED_FIELDS_V1),
        "optional_fields": list(OUTCOME_LABELER_OPTIONAL_ANCHOR_FIELDS_V1),
        "timestamp_priority_fields": list(OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1),
    },
    "label_contract_v1": dict(OUTCOME_LABEL_CONTRACT_V1),
    "anchor_definition_v1": dict(OUTCOME_LABELER_ANCHOR_DEFINITION_V1),
    "horizon_definition_v1": dict(OUTCOME_LABELER_HORIZON_DEFINITION_V1),
    "transition_label_rules_v1": dict(OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1),
    "management_label_rules_v1": dict(OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1),
    "ambiguity_and_censoring_rules_v1": dict(OUTCOME_LABELER_AMBIGUITY_AND_CENSORING_RULES_V1),
    "outcome_signal_source_v1": dict(OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1),
    "outcome_labeler_v1_implementation": dict(OUTCOME_LABELER_IMPLEMENTATION_V1),
    "label_metadata_v1": dict(OUTCOME_LABELER_LABEL_METADATA_V1),
    "shadow_label_output_v1": dict(OUTCOME_LABELER_SHADOW_OUTPUT_V1),
    "dataset_builder_bridge_v1": dict(OUTCOME_LABELER_DATASET_BUILDER_BRIDGE_V1),
    "validation_report_v1": dict(OUTCOME_LABELER_VALIDATION_REPORT_V1),
    "future_source": {
        "source": "trade_closed_history.csv",
        "supporting_inputs": [
            "related_future_outcome",
        ],
    },
    "label_families": {
        "transition": list(OUTCOME_LABELER_TRANSITION_LABELS_V1),
        "management": list(OUTCOME_LABELER_MANAGEMENT_LABELS_V1),
    },
    "label_status_values": list(OUTCOME_LABEL_STATUS_VALUES_V1),
    "label_polarity_values": list(OUTCOME_LABEL_POLARITY_VALUES_V1),
    "labeling_philosophy_v1": dict(OUTCOME_LABELING_PHILOSOPHY_V1),
    "frozen_principles": [
        "offline_only",
        "live_action_gate_unchanged",
        "semantic_foundation_remains_frozen",
        "score_existing_forecasts_without_consumer_retuning",
    ],
    "completed_definitions": [
        "label_contract_v1",
        "anchor_definition_v1",
        "horizon_definition_v1",
        "transition_label_rules_v1",
        "management_label_rules_v1",
        "ambiguity_and_censoring_rules_v1",
        "outcome_signal_source_v1",
        "outcome_labeler_v1_implementation",
        "label_metadata_v1",
        "shadow_label_output_v1",
        "dataset_builder_bridge_v1",
        "validation_report_v1",
    ],
    "deferred_definitions": [],
    "allowed_changes": [
        "outcome_label_contract",
        "future_outcome_rules",
        "offline_labeler_implementation",
        "dataset_ready_outputs",
        "validation_reporting",
    ],
    "forbidden_changes": [
        "live_action_gate_change",
        "observe_confirm_rewrite",
        "consumer_retuning",
        "symbol_exceptions",
        "immediate_model_training",
        "semantic_foundation_recomposition",
    ],
    "live_action_gate_changed": False,
    "offline_only": True,
    "dataset_ready": True,
}


def normalize_outcome_label_status(status: str) -> str:
    normalized = str(status or "").strip().upper()
    if normalized in OUTCOME_LABEL_STATUS_VALUES_V1:
        return normalized
    return "INVALID"


def resolve_outcome_label_polarity(*, label_status: str, label_value: bool | None) -> str:
    normalized_status = normalize_outcome_label_status(label_status)
    if normalized_status != "VALID":
        return "UNKNOWN"
    if label_value is True:
        return "POSITIVE"
    if label_value is False:
        return "NEGATIVE"
    return "UNKNOWN"


def outcome_labeling_philosophy_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELING_PHILOSOPHY_V1["documentation_path"]


def outcome_labeling_anchor_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_ANCHOR_DEFINITION_V1["documentation_path"]


def outcome_labeling_horizon_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_HORIZON_DEFINITION_V1["documentation_path"]


def outcome_labeling_transition_rules_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1["documentation_path"]


def outcome_labeling_management_rules_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1["documentation_path"]


def outcome_labeling_ambiguity_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_AMBIGUITY_AND_CENSORING_RULES_V1["documentation_path"]


def outcome_labeling_signal_source_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1["documentation_path"]


def outcome_labeling_label_metadata_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_LABEL_METADATA_V1["documentation_path"]


def outcome_labeling_shadow_output_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_SHADOW_OUTPUT_V1["documentation_path"]


def outcome_labeling_dataset_builder_bridge_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_DATASET_BUILDER_BRIDGE_V1["documentation_path"]


def outcome_labeling_validation_report_doc_path(project_root: Path) -> Path:
    return Path(project_root) / OUTCOME_LABELER_VALIDATION_REPORT_V1["documentation_path"]


def build_outcome_signal_source_descriptor(row: Mapping[str, Any] | None) -> dict[str, Any]:
    anchor_time_field, anchor_time_value = resolve_entry_decision_anchor_time(row)
    if not isinstance(row, Mapping):
        row = {}
    return {
        "anchor_source": "entry_decisions.csv",
        "anchor_time_field": anchor_time_field,
        "anchor_time_value": anchor_time_value,
        "symbol": str(row.get("symbol", "") or ""),
        "action": str(row.get("action", "") or ""),
        "setup_id": str(row.get("setup_id", "") or ""),
        "setup_side": str(row.get("setup_side", "") or ""),
        "preferred_position_key_fields": [
            "ticket",
            "position_id",
        ],
        "future_source": "trade_closed_history.csv",
        "future_source_path_candidates": [
            "data/trades/trade_closed_history.csv",
            "trade_closed_history.csv",
        ],
        "deterministic_join_stages": [
            "anchor_to_position_context",
            "position_context_to_closed_outcome",
        ],
    }


def build_transition_horizon_descriptor() -> dict[str, Any]:
    return {
        "family": "transition",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "horizon_bars": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "window": "next_1_to_3_bars",
        "recommended_metadata_field": "transition_horizon_bars",
    }


def build_management_horizon_descriptor() -> dict[str, Any]:
    return {
        "family": "management",
        "start_bar_offset": 1,
        "end_bar_offset": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "horizon_bars": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "window": "next_1_to_6_bars_or_position_close_capped",
        "position_close_capped": True,
        "recommended_metadata_field": "management_horizon_bars",
    }


def resolve_transition_label_rule_definition(label_name: str) -> dict[str, Any]:
    if not label_name:
        return {}
    rule = (OUTCOME_LABELER_TRANSITION_LABEL_RULES_V1.get("labels", {}) or {}).get(str(label_name), {})
    return dict(rule) if isinstance(rule, Mapping) else {}


def resolve_management_label_rule_definition(label_name: str) -> dict[str, Any]:
    if not label_name:
        return {}
    rule = (OUTCOME_LABELER_MANAGEMENT_LABEL_RULES_V1.get("labels", {}) or {}).get(str(label_name), {})
    return dict(rule) if isinstance(rule, Mapping) else {}


def is_outcome_label_status_scorable(status: str) -> bool:
    return normalize_outcome_label_status(status) == "VALID"


def resolve_outcome_label_status_from_flags(
    *,
    has_position_context: bool = True,
    has_future_bars: bool = True,
    has_exit_context: bool = True,
    requires_exit_context: bool = False,
    is_ambiguous: bool = False,
    is_censored: bool = False,
    is_invalid: bool = False,
) -> str:
    precedence = (
        ("INVALID", bool(is_invalid)),
        ("NO_POSITION_CONTEXT", not bool(has_position_context)),
        ("CENSORED", bool(is_censored)),
        ("INSUFFICIENT_FUTURE_BARS", not bool(has_future_bars)),
        ("NO_EXIT_CONTEXT", bool(requires_exit_context) and not bool(has_exit_context)),
        ("AMBIGUOUS", bool(is_ambiguous)),
    )
    for status, applies in precedence:
        if applies:
            return status
    return "VALID"


def resolve_entry_decision_anchor_time(row: Mapping[str, Any] | None) -> tuple[str, Any | None]:
    if not isinstance(row, Mapping):
        return "", None
    for field in OUTCOME_LABELER_ANCHOR_TIMESTAMP_PRIORITY_FIELDS_V1:
        value = row.get(field)
        if value not in ("", None):
            return field, value
    return "", None


def build_transition_anchor_descriptor(row: Mapping[str, Any] | None) -> dict[str, Any]:
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(row)
    return {
        "family": "transition",
        "anchor_row_source": "entry_decisions.csv",
        "anchor_time_field": anchor_field,
        "anchor_time_value": anchor_value,
        "forecast_field": "transition_forecast_v1",
        "future_interval_start": "first_future_bar_after_anchor",
        "future_interval_end": "transition_horizon_close",
        "start_bar_offset": 1,
        "horizon_bars": OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        "recommended_metadata_field": "transition_horizon_bars",
    }


def build_management_anchor_descriptor(row: Mapping[str, Any] | None) -> dict[str, Any]:
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(row)
    return {
        "family": "management",
        "anchor_row_source": "entry_decisions.csv",
        "alternate_anchor_row_source": "position_open_event_row",
        "anchor_time_field": anchor_field,
        "anchor_time_value": anchor_value,
        "forecast_field": "trade_management_forecast_v1",
        "future_interval_start": "anchor_time_while_position_is_live",
        "future_interval_end": "management_horizon_close_or_position_close",
        "start_bar_offset": 1,
        "horizon_bars": OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        "position_close_capped": True,
        "recommended_metadata_field": "management_horizon_bars",
    }
