import pandas as pd

from backend.services.entry_wait_quality_seed_enrichment import (
    apply_entry_wait_quality_enrichment,
    build_entry_wait_quality_enrichment_plan,
)
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df


def _closed_row(**overrides):
    row = {column: "" for column in TRADE_COLUMNS}
    row.update(
        {
            "ticket": 101,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 1775195588,
            "open_price": 24009.42,
            "profit": 0.67,
            "status": "CLOSED",
            "entry_wait_quality_label": "",
            "entry_wait_quality_score": 0.0,
            "entry_wait_quality_reason": "",
        }
    )
    row.update(overrides)
    return row


def _replay_row(*, ticket: int, open_ts: int, label: str, score: float, reason_codes=None):
    return {
        "wait_row": {
            "symbol": "NAS100",
            "time": "2026-04-03T10:35:45+09:00",
        },
        "next_closed_trade_row": {
            "ticket": str(ticket),
            "symbol": "NAS100",
            "open_ts": str(open_ts),
            "open_price": "24009.42",
            "profit": "0.67",
        },
        "audit_result": {
            "label_status": "VALID" if label != "insufficient_evidence" else "INSUFFICIENT_EVIDENCE",
            "quality_label": label,
            "quality_score": score,
            "reason_codes": list(reason_codes or []),
        },
    }


def test_entry_wait_quality_enrichment_aggregates_multiple_wait_rows_per_trade():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(ticket=101, open_ts=1775195588),
                _closed_row(ticket=202, open_ts=1775197801, open_price=24017.68, profit=-0.26),
                _closed_row(ticket=303, open_ts=1775199000, symbol="BTCUSD"),
            ],
            columns=TRADE_COLUMNS,
        )
    )
    replay_report = {
        "rows": [
            _replay_row(
                ticket=101,
                open_ts=1775195588,
                label="better_entry_after_wait",
                score=1.0,
                reason_codes=["better_reentry_price", "next_trade_non_negative"],
            ),
            _replay_row(
                ticket=101,
                open_ts=1775195588,
                label="neutral_wait",
                score=0.0,
                reason_codes=["mixed_or_small_signal"],
            ),
            _replay_row(
                ticket=202,
                open_ts=1775197801,
                label="delayed_loss_after_wait",
                score=-0.8829,
                reason_codes=["worse_reentry_price", "next_trade_negative"],
            ),
        ]
    }

    updated, report = apply_entry_wait_quality_enrichment(frame, replay_report=replay_report)

    first = updated.iloc[0]
    second = updated.iloc[1]
    third = updated.iloc[2]

    assert first["entry_wait_quality_label"] == "better_entry_after_wait"
    assert float(first["entry_wait_quality_score"]) == 1.0
    assert "linked_wait_rows=2" in first["entry_wait_quality_reason"]
    assert "label_mix=better_entry_after_wait:1,neutral_wait:1" in first["entry_wait_quality_reason"]

    assert second["entry_wait_quality_label"] == "delayed_loss_after_wait"
    assert float(second["entry_wait_quality_score"]) == -0.8829
    assert "worse_reentry_price" in second["entry_wait_quality_reason"]

    assert third["entry_wait_quality_label"] == ""
    assert float(pd.to_numeric(third["entry_wait_quality_score"], errors="coerce") or 0.0) == 0.0

    assert report["matched_trade_rows"] == 2
    assert report["updated_rows"] == 2
    assert report["label_distribution"]["better_entry_after_wait"] == 1
    assert report["label_distribution"]["delayed_loss_after_wait"] == 1


def test_entry_wait_quality_enrichment_plan_respects_existing_labels_without_overwrite():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(
                    ticket=101,
                    open_ts=1775195588,
                    entry_wait_quality_label="better_entry_after_wait",
                    entry_wait_quality_score=0.73,
                    entry_wait_quality_reason="existing",
                ),
            ],
            columns=TRADE_COLUMNS,
        )
    )
    replay_report = {
        "rows": [
            _replay_row(
                ticket=101,
                open_ts=1775195588,
                label="delayed_loss_after_wait",
                score=-0.6,
                reason_codes=["worse_reentry_price"],
            )
        ]
    }

    plan = build_entry_wait_quality_enrichment_plan(frame, replay_report=replay_report, overwrite_existing=False)
    updated, report = apply_entry_wait_quality_enrichment(frame, replay_report=replay_report, overwrite_existing=False)

    assert plan["existing_enriched_rows"] == 1
    assert plan["skipped_existing_rows"] == 1
    assert report["updated_rows"] == 0
    assert updated.iloc[0]["entry_wait_quality_label"] == "better_entry_after_wait"
