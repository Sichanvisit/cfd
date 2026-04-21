from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.services.path_checkpoint_analysis_refresh import (
    maybe_refresh_checkpoint_analysis_chain,
)


def test_maybe_refresh_checkpoint_analysis_chain_skips_when_rows_missing(tmp_path: Path) -> None:
    payload = maybe_refresh_checkpoint_analysis_chain(
        checkpoint_rows_path=tmp_path / "missing.csv",
        state_path=tmp_path / "state.json",
        report_path=tmp_path / "report.json",
        markdown_path=tmp_path / "report.md",
    )

    assert payload["summary"]["trigger_state"] == "SKIP_CHECKPOINT_ROWS_MISSING"
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()


def test_maybe_refresh_checkpoint_analysis_chain_respects_throttle(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    rows_path.write_text("generated_at,symbol\n2026-04-11T13:00:00+09:00,BTCUSD\n", encoding="utf-8-sig")
    state_path = tmp_path / "state.json"
    refreshed_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
    state_path.write_text(
        f'{{"summary":{{"refreshed_at":"{refreshed_at}","row_count_after":1}}}}',
        encoding="utf-8",
    )

    payload = maybe_refresh_checkpoint_analysis_chain(
        checkpoint_rows_path=rows_path,
        state_path=state_path,
        report_path=tmp_path / "report.json",
        markdown_path=tmp_path / "report.md",
        lock_path=tmp_path / "refresh.lock",
        min_interval_seconds=300,
        min_new_rows=25,
        force=False,
    )

    assert payload["summary"]["trigger_state"] == "SKIP_THROTTLED"
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()


def test_maybe_refresh_checkpoint_analysis_chain_skips_when_locked(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    rows_path.write_text("generated_at,symbol\n2026-04-11T13:00:00+09:00,BTCUSD\n", encoding="utf-8-sig")
    lock_path = tmp_path / "refresh.lock"
    lock_path.write_text(datetime.now(ZoneInfo("Asia/Seoul")).isoformat(), encoding="utf-8")

    payload = maybe_refresh_checkpoint_analysis_chain(
        checkpoint_rows_path=rows_path,
        state_path=tmp_path / "state.json",
        report_path=tmp_path / "report.json",
        markdown_path=tmp_path / "report.md",
        lock_path=lock_path,
        force=True,
    )

    assert payload["summary"]["trigger_state"] == "SKIP_LOCKED"
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()
