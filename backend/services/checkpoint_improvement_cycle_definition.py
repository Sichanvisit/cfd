from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping


CYCLE_DEFINITION_CONTRACT_VERSION = "checkpoint_improvement_cycle_definition_v0"
SUPPORTED_CYCLE_NAMES = ("light", "heavy", "governance", "reconcile")
_LAST_RUN_FIELD_BY_CYCLE = {
    "light": "light_last_run",
    "heavy": "heavy_last_run",
    "governance": "governance_last_run",
    "reconcile": "reconcile_last_run",
}


@dataclass(frozen=True, slots=True)
class CycleDefinition:
    cycle_name: str
    min_interval_seconds: int
    preferred_interval_seconds: int
    row_delta_floor: int
    sample_floor: int = 0


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


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in ("", None):
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone()
    text = _to_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _elapsed_seconds(last_run_ts: object, now_ts: object | None = None) -> int | None:
    last_run = _normalize_dt(last_run_ts)
    if last_run is None:
        return None
    now = _normalize_dt(now_ts) or datetime.now().astimezone()
    elapsed = int((now - last_run).total_seconds())
    return max(0, elapsed)


def build_default_cycle_definitions() -> dict[str, dict[str, Any]]:
    definitions = {
        "light": CycleDefinition("light", min_interval_seconds=180, preferred_interval_seconds=300, row_delta_floor=25),
        "heavy": CycleDefinition("heavy", min_interval_seconds=900, preferred_interval_seconds=1800, row_delta_floor=100, sample_floor=100),
        "governance": CycleDefinition("governance", min_interval_seconds=60, preferred_interval_seconds=180, row_delta_floor=1),
        "reconcile": CycleDefinition("reconcile", min_interval_seconds=300, preferred_interval_seconds=600, row_delta_floor=0),
    }
    return {
        name: {
            "contract_version": CYCLE_DEFINITION_CONTRACT_VERSION,
            **asdict(definition),
        }
        for name, definition in definitions.items()
    }


def get_cycle_definition(cycle_name: str) -> dict[str, Any]:
    normalized = _to_text(cycle_name).lower()
    definitions = build_default_cycle_definitions()
    if normalized not in definitions:
        raise ValueError(f"unsupported_cycle::{cycle_name}")
    return definitions[normalized]


def active_pa8_symbol_count(system_state: Mapping[str, Any] | None) -> int:
    state = _as_mapping(system_state)
    pa8_symbols = _as_mapping(state.get("pa8_symbols"))
    active = 0
    for symbol_state in pa8_symbols.values():
        if _to_bool(_as_mapping(symbol_state).get("canary_active")):
            active += 1
    return active


def _base_decision(
    *,
    definition: Mapping[str, Any],
    cycle_name: str,
    due: bool,
    reason: str,
    row_delta: int,
    elapsed_seconds: int | None,
    sample_count: int,
    active_pa8_symbol_count_value: int,
    approval_backlog_count: int,
    apply_backlog_count: int,
) -> dict[str, Any]:
    return {
        "contract_version": CYCLE_DEFINITION_CONTRACT_VERSION,
        "cycle_name": cycle_name,
        "due": bool(due),
        "decision_reason": reason if due else "",
        "skip_reason": "" if due else reason,
        "elapsed_seconds_since_last_run": elapsed_seconds,
        "row_delta": row_delta,
        "sample_count": sample_count,
        "row_delta_floor": _to_int(definition.get("row_delta_floor")),
        "sample_floor": _to_int(definition.get("sample_floor")),
        "active_pa8_symbol_count": active_pa8_symbol_count_value,
        "approval_backlog_count": approval_backlog_count,
        "apply_backlog_count": apply_backlog_count,
    }


def evaluate_cycle_decision(
    cycle_name: str,
    *,
    system_state: Mapping[str, Any] | None,
    row_delta: int = 0,
    now_ts: object | None = None,
    cycle_running: bool = False,
    lock_held: bool = False,
    hot_path_healthy: bool = True,
    recent_sample_count: int = 0,
    approval_backlog_count: int = 0,
    apply_backlog_count: int = 0,
    reconcile_signal: bool = False,
    force_run: bool = False,
) -> dict[str, Any]:
    normalized_cycle = _to_text(cycle_name).lower()
    definition = get_cycle_definition(normalized_cycle)
    state = _as_mapping(system_state)
    last_run_field = _LAST_RUN_FIELD_BY_CYCLE[normalized_cycle]
    elapsed = _elapsed_seconds(state.get(last_run_field), now_ts)
    row_delta_value = max(0, _to_int(row_delta))
    sample_count = max(0, _to_int(recent_sample_count))
    approval_backlog = max(0, _to_int(approval_backlog_count))
    apply_backlog = max(0, _to_int(apply_backlog_count))
    active_count = active_pa8_symbol_count(state)
    min_interval = _to_int(definition.get("min_interval_seconds"))
    preferred_interval = _to_int(definition.get("preferred_interval_seconds"))
    sample_floor = _to_int(definition.get("sample_floor"))
    row_floor = _to_int(definition.get("row_delta_floor"))

    if force_run:
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=True,
            reason="force_run",
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    if cycle_running:
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=False,
            reason="cycle_already_running",
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    if normalized_cycle == "light":
        if lock_held:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="lock_held",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if row_delta_value <= 0:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="row_delta_zero",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed is None:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=True,
                reason="first_cycle_run",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed < min_interval:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="cooldown_active",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if row_delta_value >= row_floor:
            reason = "row_delta_floor_met"
            due = True
        elif elapsed >= preferred_interval:
            reason = "preferred_interval_elapsed"
            due = True
        else:
            reason = "row_delta_below_floor"
            due = False
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=due,
            reason=reason,
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    if normalized_cycle == "governance":
        if active_count <= 0 and approval_backlog <= 0:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="no_active_canary_or_backlog",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed is None:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=True,
                reason="first_cycle_run",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed < min_interval:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="cooldown_active",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if approval_backlog > 0:
            reason = "approval_backlog_present"
            due = True
        elif row_delta_value >= row_floor:
            reason = "active_canary_row_delta_present"
            due = True
        elif elapsed >= preferred_interval:
            reason = "preferred_interval_elapsed"
            due = True
        else:
            reason = "waiting_for_row_delta_or_interval"
            due = False
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=due,
            reason=reason,
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    if normalized_cycle == "heavy":
        if not hot_path_healthy:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="hot_path_unhealthy",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if sample_count < sample_floor:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="sample_floor_not_met",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed is None:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=True,
                reason="first_cycle_run",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed < min_interval:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="cooldown_active",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if row_delta_value >= row_floor:
            reason = "row_delta_and_sample_floor_met"
            due = True
        elif elapsed >= preferred_interval:
            reason = "preferred_interval_elapsed"
            due = True
        else:
            reason = "waiting_for_heavy_threshold"
            due = False
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=due,
            reason=reason,
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    if normalized_cycle == "reconcile":
        if not reconcile_signal and approval_backlog <= 0 and apply_backlog <= 0:
            if elapsed is not None and elapsed >= preferred_interval:
                return _base_decision(
                    definition=definition,
                    cycle_name=normalized_cycle,
                    due=True,
                    reason="periodic_reconcile_scan",
                    row_delta=row_delta_value,
                    elapsed_seconds=elapsed,
                    sample_count=sample_count,
                    active_pa8_symbol_count_value=active_count,
                    approval_backlog_count=approval_backlog,
                    apply_backlog_count=apply_backlog,
                )
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="no_reconcile_signal",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        if elapsed is not None and elapsed < min_interval:
            return _base_decision(
                definition=definition,
                cycle_name=normalized_cycle,
                due=False,
                reason="cooldown_active",
                row_delta=row_delta_value,
                elapsed_seconds=elapsed,
                sample_count=sample_count,
                active_pa8_symbol_count_value=active_count,
                approval_backlog_count=approval_backlog,
                apply_backlog_count=apply_backlog,
            )
        return _base_decision(
            definition=definition,
            cycle_name=normalized_cycle,
            due=True,
            reason="reconcile_signal_detected",
            row_delta=row_delta_value,
            elapsed_seconds=elapsed,
            sample_count=sample_count,
            active_pa8_symbol_count_value=active_count,
            approval_backlog_count=approval_backlog,
            apply_backlog_count=apply_backlog,
        )

    raise ValueError(f"unsupported_cycle::{cycle_name}")
