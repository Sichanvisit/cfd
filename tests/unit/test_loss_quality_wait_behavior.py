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
