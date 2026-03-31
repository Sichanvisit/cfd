from __future__ import annotations

import json
from pathlib import Path

from scripts.preflight_24h_report import build_report


def test_preflight_report_skips_bad_decision_rows(tmp_path: Path):
    decisions_csv = tmp_path / "entry_decisions.csv"
    closed_csv = tmp_path / "trade_closed_history.csv"
    out_dir = tmp_path / "reports"

    decisions_csv.write_text(
        "\n".join(
            [
                "time,symbol,action,outcome,blocked_by,preflight_regime,preflight_liquidity,preflight_allowed_action,preflight_approach_mode",
                "2026-03-06T10:00:00,NAS100,BUY,entered,,RANGE,OK,BOTH,MIX",
                "2026-03-06T10:01:00,NAS100,SELL,skipped,core_not_passed,RANGE,OK,SELL_ONLY,MIX,EXTRA",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    closed_csv.write_text(
        "\n".join(
            [
                "symbol,direction,open_time,close_ts,profit,status",
                "NAS100,BUY,2026-03-06 10:00:00,2026-03-06 10:10:00,1.5,CLOSED",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    json_path, md_path = build_report(
        decisions_csv=decisions_csv,
        closed_csv=closed_csv,
        out_dir=out_dir,
        hours=24,
        match_tolerance_sec=600,
    )

    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert int(payload["rows_decisions"]) == 1
    assert payload["blocked_by_top10"][0]["blocked_key"] == "entered_or_not_blocked"
