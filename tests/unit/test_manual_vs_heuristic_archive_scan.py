import json

from backend.services.manual_vs_heuristic_archive_scan import (
    build_manual_vs_heuristic_archive_scan,
)


def test_archive_scan_counts_rotate_and_legacy_archives(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    (trades_dir / "entry_decisions.csv").write_text(
        "time,signal_bar_ts,symbol,barrier_state_v1,belief_state_v1,forecast_assist_v1,entry_wait_decision\n"
        "2026-04-06T14:23:50,1775453030.0,NAS100,{},{},{},wait\n",
        encoding="utf-8-sig",
    )
    detail_payload = {
        "time": "2026-04-02T21:09:54+09:00",
        "signal_bar_ts": 1775362500.0,
        "symbol": "NAS100",
        "barrier_state_v1": json.dumps({"buy_barrier": 0.2}),
        "belief_state_v1": json.dumps({"buy_belief": 0.4}),
        "forecast_assist_v1": json.dumps({"decision_hint": "OBSERVE_FAVOR"}),
        "entry_wait_decision": "wait",
    }
    (trades_dir / "entry_decisions.detail.rotate_20260402_213906_695331.jsonl").write_text(
        json.dumps({"record_type": "entry_decision_detail_v1", "schema_version": "v1", "payload": detail_payload})
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_manual_vs_heuristic_archive_scan(trades_dir)

    assert len(frame) == 2
    assert summary["archive_kind_counts"]["current_csv"] == 1
    assert summary["archive_kind_counts"]["rotate_detail"] == 1
