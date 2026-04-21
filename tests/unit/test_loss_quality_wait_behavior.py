import pandas as pd

from backend.services.trade_csv_schema import add_signed_exit_score


def test_loss_quality_reflects_adverse_wait_recovery_vs_timeout():
    df = pd.DataFrame(
        [
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 4,
                "peak_profit_at_exit": 0.0,
                "giveback_usd": 0.0,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=recovery(0.45/0.35)",
            },
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 4,
                "peak_profit_at_exit": 0.0,
                "giveback_usd": 0.0,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=timeout(120s)",
            },
        ]
    )

    out = add_signed_exit_score(df)
    rec = out.iloc[0]
    tout = out.iloc[1]

    assert rec["loss_quality_label"] in {"good_loss", "neutral_loss"}
    assert tout["loss_quality_label"] == "bad_loss"
    assert "wait_recovery" in str(rec["loss_quality_reason"])
    assert "wait_timeout" in str(tout["loss_quality_reason"])
    assert float(rec["loss_quality_score"]) > float(tout["loss_quality_score"])
    # Loss-side signed score should be less negative for higher-quality loss handling.
    assert float(rec["signed_exit_score"]) > float(tout["signed_exit_score"])
    assert rec["wait_quality_label"] == "good_wait"
    assert tout["wait_quality_label"] == "bad_wait"
    assert float(rec["wait_quality_score"]) > float(tout["wait_quality_score"])


def test_wait_quality_marks_unnecessary_wait_when_recovery_is_marginal():
    df = pd.DataFrame(
        [
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 4,
                "peak_profit_at_exit": 0.0,
                "giveback_usd": 0.0,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=recovery(0.36/0.35)",
            },
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 2,
                "peak_profit_at_exit": 0.0,
                "giveback_usd": 0.0,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=recovery(0.55/0.35)",
            },
        ]
    )

    out = add_signed_exit_score(df)
    unnecessary = out.iloc[0]
    good = out.iloc[1]

    assert unnecessary["wait_quality_label"] == "unnecessary_wait"
    assert good["wait_quality_label"] == "good_wait"
    assert "wait_unnecessary" in str(unnecessary["loss_quality_reason"])
    assert float(unnecessary["wait_quality_score"]) < float(good["wait_quality_score"])


def test_wait_quality_relabels_short_timeout_without_green_room_as_unnecessary_wait():
    df = pd.DataFrame(
        [
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 3,
                "peak_profit_at_exit": -0.2,
                "giveback_usd": 0.9,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=timeout(18s)",
            },
            {
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 4,
                "peak_profit_at_exit": 0.3,
                "giveback_usd": 0.9,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=timeout(40s)",
            },
        ]
    )

    out = add_signed_exit_score(df)
    short_timeout = out.iloc[0]
    long_timeout = out.iloc[1]

    assert short_timeout["wait_quality_label"] == "unnecessary_wait"
    assert short_timeout["wait_quality_reason"] == "wait_timeout_short_never_green"
    assert "wait_timeout_short_never_green" in str(short_timeout["loss_quality_reason"])
    assert long_timeout["wait_quality_label"] == "bad_wait"


def test_learning_total_score_penalizes_timeout_loss_case():
    df = pd.DataFrame(
        [
            {
                "entry_score": 82,
                "contra_score_at_entry": 18,
                "exit_score": 120,
                "profit": -1.2,
                "exit_delay_ticks": 4,
                "peak_profit_at_exit": 0.0,
                "giveback_usd": 0.0,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Adverse Stop, adverse_wait=timeout(120s)",
            }
        ]
    )

    out = add_signed_exit_score(df)
    row = out.iloc[0]

    assert float(row["learning_entry_score"]) > 0.0
    assert float(row["learning_wait_score"]) < 0.0
    assert float(row["learning_exit_score"]) < 0.0
    assert float(row["learning_total_score"]) < 0.0
    assert row["learning_total_label"] == "negative"


def test_learning_total_score_rewards_profitable_defensive_exit_case():
    df = pd.DataFrame(
        [
            {
                "entry_score": 76,
                "contra_score_at_entry": 24,
                "exit_score": 110,
                "profit": 1.8,
                "net_pnl_after_cost": 1.5,
                "exit_delay_ticks": 1,
                "peak_profit_at_exit": 2.2,
                "giveback_usd": 0.4,
                "post_exit_mae": 0.0,
                "post_exit_mfe": 0.0,
                "exit_policy_stage": "short",
                "exit_reason": "Protect Exit",
            }
        ]
    )

    out = add_signed_exit_score(df)
    row = out.iloc[0]

    assert float(row["learning_entry_score"]) > 0.0
    assert float(row["learning_exit_score"]) > 0.0
    assert float(row["learning_total_score"]) > 0.0
    assert row["learning_total_label"] == "positive"
