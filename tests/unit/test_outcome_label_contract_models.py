from backend.services.outcome_labeler_contract import OUTCOME_LABEL_STATUS_VALUES_V1
from backend.trading.engine.core.models import (
    OutcomeLabelsV1,
    TradeManagementOutcomeLabelsV1,
    TransitionOutcomeLabelsV1,
)


def test_transition_outcome_labels_v1_exposes_exact_fields():
    payload = TransitionOutcomeLabelsV1().to_dict()

    assert set(payload.keys()) == {
        "buy_confirm_success_label",
        "sell_confirm_success_label",
        "false_break_label",
        "reversal_success_label",
        "continuation_success_label",
        "label_status",
        "metadata",
    }
    assert payload["label_status"] == "INVALID"


def test_trade_management_outcome_labels_v1_exposes_exact_fields():
    payload = TradeManagementOutcomeLabelsV1().to_dict()

    assert set(payload.keys()) == {
        "continue_favor_label",
        "fail_now_label",
        "recover_after_pullback_label",
        "reach_tp1_label",
        "opposite_edge_reach_label",
        "better_reentry_if_cut_label",
        "label_status",
        "metadata",
    }
    assert payload["label_status"] == "INVALID"


def test_outcome_labels_v1_bundles_transition_and_trade_management_contracts():
    bundle = OutcomeLabelsV1(
        transition=TransitionOutcomeLabelsV1(
            buy_confirm_success_label=True,
            label_status="VALID",
            metadata={"horizon": "transition_h1"},
        ),
        trade_management=TradeManagementOutcomeLabelsV1(
            continue_favor_label=False,
            label_status="NO_EXIT_CONTEXT",
            metadata={"horizon": "management_h1"},
        ),
        metadata={"anchor_row_id": "row-1"},
    )

    payload = bundle.to_dict()

    assert set(payload.keys()) == {"transition", "trade_management", "metadata"}
    assert payload["transition"]["buy_confirm_success_label"] is True
    assert payload["transition"]["label_status"] == "VALID"
    assert payload["trade_management"]["continue_favor_label"] is False
    assert payload["trade_management"]["label_status"] == "NO_EXIT_CONTEXT"
    assert payload["metadata"]["anchor_row_id"] == "row-1"


def test_outcome_label_status_vocabulary_covers_learning_and_reporting_contracts():
    assert OUTCOME_LABEL_STATUS_VALUES_V1 == (
        "VALID",
        "INSUFFICIENT_FUTURE_BARS",
        "NO_POSITION_CONTEXT",
        "NO_EXIT_CONTEXT",
        "AMBIGUOUS",
        "CENSORED",
        "INVALID",
    )
