import csv
import json

from backend.services.entry_wait_quality_replay_bridge import (
    build_entry_wait_quality_replay_report,
    resolve_default_future_bar_path,
    write_entry_wait_quality_replay_report,
)


def _write_csv(path, rows):
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_entry_wait_quality_replay_bridge_dedupes_and_links_next_entry_and_trade():
    entry_rows = [
        {
            "time": "2026-04-03T10:00:00+09:00",
            "signal_bar_ts": "1000",
            "symbol": "NAS100",
            "action": "",
            "observe_side": "BUY",
            "outcome": "wait",
            "entry_wait_selected": "1",
            "entry_wait_decision": "wait_soft_helper_block",
            "entry_wait_state": "CENTER",
            "observe_reason": "middle_sr_anchor_required_observe",
            "blocked_by": "middle_sr_anchor_guard",
        },
        {
            "time": "2026-04-03T10:00:03+09:00",
            "signal_bar_ts": "1000",
            "symbol": "NAS100",
            "action": "",
            "observe_side": "BUY",
            "outcome": "wait",
            "entry_wait_selected": "1",
            "entry_wait_decision": "wait_soft_helper_block",
            "entry_wait_state": "CENTER",
            "observe_reason": "middle_sr_anchor_required_observe",
            "blocked_by": "middle_sr_anchor_guard",
        },
        {
            "time": "2026-04-03T10:05:00+09:00",
            "signal_bar_ts": "1900",
            "symbol": "NAS100",
            "action": "BUY",
            "observe_side": "BUY",
            "outcome": "entered",
            "trade_link_key": "trade_link_v1|ticket=1|symbol=NAS100|direction=BUY|open_ts=1300",
            "decision_row_key": "replay_dataset_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1900|action=BUY|ticket=1",
        },
    ]
    closed_rows = [
        {
            "ticket": "1",
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": "1300",
            "open_price": "99.76",
            "profit": "1.5",
            "trade_link_key": "trade_link_v1|ticket=1|symbol=NAS100|direction=BUY|open_ts=1300",
            "decision_row_key": "replay_dataset_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1900|action=BUY|ticket=1",
        }
    ]
    future_rows = [
        {"symbol": "NAS100", "time": "1100", "open": "100.0", "high": "100.05", "low": "99.72", "close": "99.80"},
        {"symbol": "NAS100", "time": "1200", "open": "99.80", "high": "100.20", "low": "99.78", "close": "100.12"},
    ]

    report = build_entry_wait_quality_replay_report(
        entry_decision_rows=entry_rows,
        closed_trade_rows=closed_rows,
        future_bar_rows=future_rows,
        dedupe=True,
    )

    assert report["coverage"]["raw_wait_candidate_count"] == 2
    assert report["coverage"]["bridged_row_count"] == 1
    assert report["summary"]["label_counts"]["better_entry_after_wait"] == 1
    first = report["rows"][0]
    assert first["bridge_flags"]["has_future_bars"] is True
    assert first["bridge_flags"]["has_next_entry_row"] is True
    assert first["bridge_flags"]["has_next_closed_trade_row"] is True
    assert first["bridge_flags"]["has_next_entry_price"] is True
    assert first["anchor_price_source"] == "future_bars_first_open"
    assert first["next_entry_price_source"] == "closed_trade_open_price"
    assert first["audit_result"]["quality_label"] == "better_entry_after_wait"


def test_entry_wait_quality_replay_report_marks_stale_future_bar_alignment():
    report = build_entry_wait_quality_replay_report(
        entry_decision_rows=[
            {
                "time": "2026-04-03T10:00:00+09:00",
                "signal_bar_ts": "2000",
                "symbol": "BTCUSD",
                "action": "",
                "observe_side": "BUY",
                "outcome": "wait",
                "entry_wait_selected": "1",
                "entry_wait_decision": "wait_soft_helper_block",
                "entry_wait_state": "CENTER",
            }
        ],
        future_bar_rows=[
            {"symbol": "BTCUSD", "time": "1000", "open": "100.0", "high": "100.1", "low": "99.9", "close": "100.0"}
        ],
    )

    assert report["coverage"]["future_bar_alignment"]["status"] == "stale_before_waits"
    assert report["coverage"]["future_bar_alignment"]["wait_rows_with_future"] == 0


def test_resolve_default_future_bar_path_prefers_newest_companion(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    market_bars_dir = project_root / "data" / "market_bars"
    trades_dir = project_root / "data" / "trades"
    market_bars_dir.mkdir(parents=True, exist_ok=True)
    trades_dir.mkdir(parents=True, exist_ok=True)
    entry_path = trades_dir / "entry_decisions.csv"
    entry_path.write_text("time,symbol\n", encoding="utf-8")
    older = market_bars_dir / "future_bars_entry_decisions_m15.csv"
    newer = market_bars_dir / "future_bars_entry_decisions_m30.csv"
    older.write_text("symbol,time,open,high,low,close\n", encoding="utf-8")
    newer.write_text("symbol,time,open,high,low,close\n", encoding="utf-8")
    older.touch()
    newer.touch()
    monkeypatch.setattr(
        "backend.services.entry_wait_quality_replay_bridge._project_root",
        lambda: project_root,
    )

    resolved = resolve_default_future_bar_path(entry_path)

    assert resolved == newer.resolve()


def test_write_entry_wait_quality_replay_report_writes_json_and_markdown(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    closed_path = tmp_path / "trade_closed_history.csv"
    future_path = tmp_path / "future_bars.csv"
    output_path = tmp_path / "entry_wait_quality_replay_latest.json"
    markdown_path = tmp_path / "entry_wait_quality_replay_latest.md"

    _write_csv(
        entry_path,
        [
            {
                "time": "2026-04-03T10:00:00+09:00",
                "signal_bar_ts": "1000",
                "symbol": "BTCUSD",
                "action": "",
                "observe_side": "BUY",
                "outcome": "wait",
                "entry_wait_selected": "1",
                "entry_wait_decision": "wait_policy_suppressed",
                "entry_wait_state": "POLICY_SUPPRESSED",
                "observe_reason": "observe_default",
                "blocked_by": "layer_mode_confirm_suppressed",
            }
        ],
    )
    _write_csv(closed_path, [])
    _write_csv(
        future_path,
        [
            {"symbol": "BTCUSD", "time": "1100", "open": "100.0", "high": "100.01", "low": "99.55", "close": "99.60"},
            {"symbol": "BTCUSD", "time": "1200", "open": "99.60", "high": "99.70", "low": "99.40", "close": "99.50"},
        ],
    )

    report = write_entry_wait_quality_replay_report(
        entry_decision_path=entry_path,
        closed_trade_path=closed_path,
        future_bar_path=future_path,
        output_path=output_path,
        markdown_output_path=markdown_path,
    )

    saved_report = json.loads(output_path.read_text(encoding="utf-8"))
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report["summary"]["label_counts"]["avoided_loss_by_wait"] == 1
    assert saved_report["coverage"]["bridged_row_count"] == 1
    assert "Entry Wait Quality Replay Report" in saved_markdown
    assert "avoided_loss_by_wait: 1" in saved_markdown
