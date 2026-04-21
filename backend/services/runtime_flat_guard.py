from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import URLError
from urllib.request import urlopen


RUNTIME_FLAT_GUARD_CONTRACT_VERSION = "runtime_flat_guard_v0"


def default_runtime_status_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "runtime_status.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _parse_iso(value: object) -> datetime | None:
    text = _to_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _load_runtime_status_payload(path: str | Path) -> tuple[dict[str, Any], str]:
    file_path = Path(path)
    if not file_path.exists():
        return {}, "runtime_status_missing"
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, f"runtime_status_parse_failed::{exc.__class__.__name__}"
    if not isinstance(payload, dict):
        return {}, "runtime_status_not_mapping"
    return payload, ""


def _runtime_status_age_seconds(
    *,
    runtime_status_path: str | Path,
    runtime_status_payload: Mapping[str, Any],
    now_dt: datetime,
) -> int | None:
    updated_at = _parse_iso(runtime_status_payload.get("updated_at"))
    if updated_at is not None:
        return max(0, int((now_dt - updated_at).total_seconds()))
    file_path = Path(runtime_status_path)
    if not file_path.exists():
        return None
    return max(0, int(now_dt.timestamp() - file_path.stat().st_mtime))


def _runtime_open_count(runtime_status_payload: Mapping[str, Any]) -> tuple[int | None, str]:
    latest_signal_by_symbol = _mapping(runtime_status_payload.get("latest_signal_by_symbol"))
    if latest_signal_by_symbol:
        total = 0
        for signal in latest_signal_by_symbol.values():
            total += _to_int(_mapping(signal).get("my_position_count"))
        return total, ""
    runtime_recycle = _mapping(runtime_status_payload.get("runtime_recycle"))
    if runtime_recycle:
        return _to_int(runtime_recycle.get("last_open_positions_count")), ""
    return None, "runtime_open_count_missing"


def load_api_open_count(api_url: str, timeout_sec: int = 4) -> tuple[int | None, str]:
    try:
        with urlopen(api_url, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        return None, f"api_summary_unavailable::{exc.__class__.__name__}"
    except Exception as exc:
        return None, f"api_summary_unavailable::{exc.__class__.__name__}"
    summary = _mapping(_mapping(payload).get("summary"))
    if not summary:
        return None, "api_summary_missing"
    return _to_int(summary.get("open_count")), ""


def build_runtime_flat_guard(
    *,
    runtime_status_path: str | Path | None = None,
    api_url: str = "http://127.0.0.1:8010/trades/summary",
    max_status_age_sec: int = 180,
    now_ts: object | None = None,
    api_open_loader: Callable[[str], tuple[int | None, str]] | None = None,
) -> dict[str, Any]:
    status_path = Path(runtime_status_path or default_runtime_status_path())
    run_at = _to_text(now_ts, _now_iso())
    now_dt = _parse_iso(run_at) or datetime.now().astimezone()

    runtime_status_payload, runtime_reason = _load_runtime_status_payload(status_path)
    status_open_count, runtime_open_reason = _runtime_open_count(runtime_status_payload)
    if not runtime_reason:
        runtime_reason = runtime_open_reason

    status_age_sec = _runtime_status_age_seconds(
        runtime_status_path=status_path,
        runtime_status_payload=runtime_status_payload,
        now_dt=now_dt,
    )

    api_loader = api_open_loader or (lambda url: load_api_open_count(url))
    api_open_count, api_reason = api_loader(api_url)

    candidates: list[int] = []
    sources: list[str] = []
    if status_open_count is not None and status_age_sec is not None and status_age_sec <= int(max_status_age_sec):
        candidates.append(int(status_open_count))
        sources.append("runtime_status")
    if api_open_count is not None:
        candidates.append(int(api_open_count))
        sources.append("api_summary")

    if not candidates:
        trigger_state = "GUARD_BLOCKED"
        guard_passed = False
        open_count = None
        recommended_next_action = "inspect_runtime_status_or_api_health_before_restart"
    else:
        open_count = max(candidates)
        if open_count > 0:
            trigger_state = "GUARD_BLOCKED"
            guard_passed = False
            recommended_next_action = "wait_until_open_positions_are_flat_before_restart"
        else:
            trigger_state = "GUARD_OK"
            guard_passed = True
            recommended_next_action = "restart_core_can_continue"

    return {
        "summary": {
            "contract_version": RUNTIME_FLAT_GUARD_CONTRACT_VERSION,
            "generated_at": run_at,
            "trigger_state": trigger_state,
            "guard_passed": guard_passed,
            "recommended_next_action": recommended_next_action,
            "runtime_status_path": str(status_path),
            "api_url": api_url,
            "open_count": open_count,
            "status_open_count": status_open_count,
            "status_age_sec": status_age_sec,
            "api_open_count": api_open_count,
            "guard_sources": sources,
            "runtime_reason": runtime_reason,
            "api_reason": api_reason,
        },
        "runtime_status": runtime_status_payload,
    }
