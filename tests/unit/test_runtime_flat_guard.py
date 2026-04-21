from __future__ import annotations

import json
from pathlib import Path

from backend.services.runtime_flat_guard import build_runtime_flat_guard


def _write_runtime_status(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_runtime_flat_guard_passes_when_fresh_status_and_api_are_flat(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    _write_runtime_status(
        runtime_status_path,
        {
            "updated_at": "2026-04-11T20:10:00+09:00",
            "runtime_recycle": {
                "last_open_positions_count": 0,
            },
        },
    )

    payload = build_runtime_flat_guard(
        runtime_status_path=runtime_status_path,
        now_ts="2026-04-11T20:11:00+09:00",
        api_open_loader=lambda url: (0, ""),
    )

    assert payload["summary"]["trigger_state"] == "GUARD_OK"
    assert payload["summary"]["guard_passed"] is True
    assert payload["summary"]["open_count"] == 0


def test_runtime_flat_guard_blocks_when_api_or_status_reports_open_positions(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    _write_runtime_status(
        runtime_status_path,
        {
            "updated_at": "2026-04-11T20:10:00+09:00",
            "runtime_recycle": {
                "last_open_positions_count": 0,
            },
        },
    )

    payload = build_runtime_flat_guard(
        runtime_status_path=runtime_status_path,
        now_ts="2026-04-11T20:11:00+09:00",
        api_open_loader=lambda url: (2, ""),
    )

    assert payload["summary"]["trigger_state"] == "GUARD_BLOCKED"
    assert payload["summary"]["guard_passed"] is False
    assert payload["summary"]["open_count"] == 2


def test_runtime_flat_guard_blocks_when_no_fresh_runtime_or_api_signal_exists(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    _write_runtime_status(
        runtime_status_path,
        {
            "updated_at": "2026-04-11T19:00:00+09:00",
            "runtime_recycle": {
                "last_open_positions_count": 0,
            },
        },
    )

    payload = build_runtime_flat_guard(
        runtime_status_path=runtime_status_path,
        now_ts="2026-04-11T20:11:00+09:00",
        max_status_age_sec=60,
        api_open_loader=lambda url: (None, "api_summary_unavailable"),
    )

    assert payload["summary"]["trigger_state"] == "GUARD_BLOCKED"
    assert payload["summary"]["guard_passed"] is False
    assert payload["summary"]["recommended_next_action"] == "inspect_runtime_status_or_api_health_before_restart"
