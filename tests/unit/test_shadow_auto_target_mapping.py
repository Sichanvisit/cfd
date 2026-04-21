import pandas as pd

from backend.services.shadow_auto_target_mapping import build_shadow_auto_target_mapping


def test_build_shadow_auto_target_mapping_includes_manual_and_bridge_rows():
    manual_df = pd.DataFrame(
        [
            {
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "manual_wait_teacher_family": "protective_exit",
            },
            {
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
            },
        ]
    )

    training_corpus_df = pd.DataFrame(
        [
            {
                "entry_wait_quality_label": "insufficient_evidence",
                "learning_total_label": "positive",
                "signed_exit_score": 90.0,
                "wait_bias_hint": "wait",
                "forecast_decision_hint": "BALANCED",
            },
            {
                "entry_wait_quality_label": "insufficient_evidence",
                "learning_total_label": "neutral",
                "signed_exit_score": 50.0,
                "wait_bias_hint": "wait",
                "forecast_decision_hint": "BALANCED",
            },
            {
                "entry_wait_quality_label": "insufficient_evidence",
                "learning_total_label": "negative",
                "signed_exit_score": -300.0,
                "wait_bias_hint": "wait",
                "forecast_decision_hint": "BALANCED",
            },
        ]
    )

    frame, summary = build_shadow_auto_target_mapping(manual_df, training_corpus_df)

    assert len(frame) >= 4
    manual_row = frame.loc[frame["source_label"].eq("good_wait_protective_exit")].iloc[0]
    bridge_row = frame.loc[
        (frame["mapping_namespace"].eq("bridge_entry_wait_quality_label"))
        & (frame["source_label"].eq("insufficient_evidence"))
    ].iloc[0]
    assert manual_row["target_action_class"] == "exit_protect"
    assert bridge_row["target_action_class"] == "wait_more"
    assert bridge_row["target_action_variant"] == "wait_better_entry"
    assert int(bridge_row["current_count"]) == 3
    assert summary["namespace_counts"]["manual_wait_teacher_label"] >= 1
