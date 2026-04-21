from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SYSTEM_STATE_CONTRACT_VERSION = "checkpoint_improvement_system_state_v0"
SYSTEM_PHASES = ("STARTING", "RUNNING", "DEGRADED", "EMERGENCY", "SHUTDOWN")
DEFAULT_PA8_SYMBOLS = ("BTCUSD", "XAUUSD", "NAS100")
_CYCLE_FIELD_BY_NAME = {
    "light": "light_last_run",
    "heavy": "heavy_last_run",
    "governance": "governance_last_run",
    "reconcile": "reconcile_last_run",
}
_ALLOWED_PHASE_TRANSITIONS = {
    "STARTING": {"RUNNING", "DEGRADED", "EMERGENCY", "SHUTDOWN"},
    "RUNNING": {"RUNNING", "DEGRADED", "EMERGENCY", "SHUTDOWN"},
    "DEGRADED": {"DEGRADED", "RUNNING", "EMERGENCY", "SHUTDOWN"},
    "EMERGENCY": {"EMERGENCY", "DEGRADED", "SHUTDOWN"},
    "SHUTDOWN": {"SHUTDOWN"},
}


def default_checkpoint_improvement_system_state_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_system_state_latest.json"
    )


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _normalize_timestamp(value: object, default: str = "") -> str:
    if isinstance(value, datetime):
        return value.astimezone().isoformat()
    return _to_text(value, default)


def _normalize_phase(value: object, default: str = "STARTING") -> str:
    phase = _to_text(value, default).upper()
    return phase if phase in SYSTEM_PHASES else str(default)


def _default_pa8_symbol_state() -> dict[str, Any]:
    return {
        "canary_active": False,
        "live_window_ready": False,
    }


def _normalize_pa8_symbols(
    value: object,
    *,
    default_symbols: tuple[str, ...] = DEFAULT_PA8_SYMBOLS,
) -> dict[str, dict[str, Any]]:
    base: dict[str, dict[str, Any]] = {
        symbol: _default_pa8_symbol_state()
        for symbol in default_symbols
    }
    raw = _as_mapping(value)
    for symbol, symbol_state in raw.items():
        normalized_symbol = _to_text(symbol).upper()
        if not normalized_symbol:
            continue
        state_map = _as_mapping(symbol_state)
        merged = deepcopy(base.get(normalized_symbol, _default_pa8_symbol_state()))
        merged["canary_active"] = _to_bool(state_map.get("canary_active"), merged["canary_active"])
        merged["live_window_ready"] = _to_bool(
            state_map.get("live_window_ready"),
            merged["live_window_ready"],
        )
        base[normalized_symbol] = merged
    return base


def build_default_system_state(
    *,
    phase: str = "STARTING",
    default_symbols: tuple[str, ...] = DEFAULT_PA8_SYMBOLS,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "contract_version": SYSTEM_STATE_CONTRACT_VERSION,
        "created_at": now,
        "updated_at": now,
        "phase": _normalize_phase(phase),
        "last_transition_reason": "initial_bootstrap",
        "last_row_ts": "",
        "row_count_since_boot": 0,
        "light_last_run": "",
        "heavy_last_run": "",
        "governance_last_run": "",
        "reconcile_last_run": "",
        "pa8_symbols": _normalize_pa8_symbols({}, default_symbols=default_symbols),
        "telegram_healthy": True,
        "last_error": "",
    }


class SystemStateManager:
    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        default_symbols: tuple[str, ...] = DEFAULT_PA8_SYMBOLS,
    ) -> None:
        self._state_path = Path(state_path) if state_path is not None else default_checkpoint_improvement_system_state_path()
        self._default_symbols = tuple(default_symbols)
        self._lock = threading.Lock()

    @property
    def state_path(self) -> Path:
        return self._state_path

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._load_state_unlocked())

    def transition(
        self,
        next_phase: str,
        *,
        reason: str = "",
        occurred_at: object | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._load_state_unlocked()
            current_phase = _normalize_phase(state.get("phase"))
            target_phase = _normalize_phase(next_phase, current_phase)
            allowed_targets = _ALLOWED_PHASE_TRANSITIONS.get(current_phase, {current_phase})
            if target_phase not in allowed_targets:
                raise ValueError(f"invalid_phase_transition::{current_phase}->{target_phase}")
            state["phase"] = target_phase
            state["last_transition_reason"] = _to_text(reason, state.get("last_transition_reason", ""))
            state["updated_at"] = _normalize_timestamp(occurred_at, _now_iso())
            if target_phase == "RUNNING" and not reason:
                state["last_error"] = ""
            elif target_phase in {"DEGRADED", "EMERGENCY"}:
                state["last_error"] = _to_text(reason, state.get("last_error", ""))
            self._save_state_unlocked(state)
            return deepcopy(state)

    def record_row_observation(
        self,
        *,
        last_row_ts: object,
        row_count_increment: int = 1,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._load_state_unlocked()
            state["last_row_ts"] = _normalize_timestamp(last_row_ts, state.get("last_row_ts", ""))
            state["row_count_since_boot"] = max(
                0,
                _to_int(state.get("row_count_since_boot")) + max(0, int(row_count_increment)),
            )
            state["updated_at"] = _now_iso()
            self._save_state_unlocked(state)
            return deepcopy(state)

    def mark_cycle_run(self, cycle_name: str, *, run_at: object | None = None) -> dict[str, Any]:
        cycle_key = _to_text(cycle_name).lower()
        field_name = _CYCLE_FIELD_BY_NAME.get(cycle_key)
        if not field_name:
            raise ValueError(f"unsupported_cycle::{cycle_name}")
        with self._lock:
            state = self._load_state_unlocked()
            state[field_name] = _normalize_timestamp(run_at, _now_iso())
            state["updated_at"] = _now_iso()
            self._save_state_unlocked(state)
            return deepcopy(state)

    def set_pa8_symbol_state(
        self,
        symbol: str,
        *,
        canary_active: bool | None = None,
        live_window_ready: bool | None = None,
    ) -> dict[str, Any]:
        normalized_symbol = _to_text(symbol).upper()
        if not normalized_symbol:
            raise ValueError("symbol_required")
        with self._lock:
            state = self._load_state_unlocked()
            pa8_symbols = _normalize_pa8_symbols(
                state.get("pa8_symbols"),
                default_symbols=self._default_symbols,
            )
            symbol_state = deepcopy(pa8_symbols.get(normalized_symbol, _default_pa8_symbol_state()))
            if canary_active is not None:
                symbol_state["canary_active"] = bool(canary_active)
            if live_window_ready is not None:
                symbol_state["live_window_ready"] = bool(live_window_ready)
            pa8_symbols[normalized_symbol] = symbol_state
            state["pa8_symbols"] = pa8_symbols
            state["updated_at"] = _now_iso()
            self._save_state_unlocked(state)
            return deepcopy(state)

    def set_telegram_health(
        self,
        healthy: bool,
        *,
        error: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            state = self._load_state_unlocked()
            state["telegram_healthy"] = bool(healthy)
            if error or healthy:
                state["last_error"] = _to_text(error)
            state["updated_at"] = _now_iso()
            self._save_state_unlocked(state)
            return deepcopy(state)

    def _load_state_unlocked(self) -> dict[str, Any]:
        if not self._state_path.exists():
            return build_default_system_state(default_symbols=self._default_symbols)
        try:
            parsed = json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            state = build_default_system_state(default_symbols=self._default_symbols)
            state["last_error"] = f"state_load_error::{exc.__class__.__name__}"
            return state
        return self._normalize_state(parsed)

    def _normalize_state(self, raw: object) -> dict[str, Any]:
        default = build_default_system_state(default_symbols=self._default_symbols)
        data = _as_mapping(raw)
        state = dict(data)
        state["contract_version"] = _to_text(state.get("contract_version"), default["contract_version"])
        state["created_at"] = _normalize_timestamp(state.get("created_at"), default["created_at"])
        state["updated_at"] = _normalize_timestamp(state.get("updated_at"), default["updated_at"])
        state["phase"] = _normalize_phase(state.get("phase"), default["phase"])
        state["last_transition_reason"] = _to_text(
            state.get("last_transition_reason"),
            default["last_transition_reason"],
        )
        state["last_row_ts"] = _normalize_timestamp(state.get("last_row_ts"), default["last_row_ts"])
        state["row_count_since_boot"] = _to_int(state.get("row_count_since_boot"), default["row_count_since_boot"])
        state["light_last_run"] = _normalize_timestamp(state.get("light_last_run"), default["light_last_run"])
        state["heavy_last_run"] = _normalize_timestamp(state.get("heavy_last_run"), default["heavy_last_run"])
        state["governance_last_run"] = _normalize_timestamp(
            state.get("governance_last_run"),
            default["governance_last_run"],
        )
        state["reconcile_last_run"] = _normalize_timestamp(
            state.get("reconcile_last_run"),
            default["reconcile_last_run"],
        )
        state["pa8_symbols"] = _normalize_pa8_symbols(
            state.get("pa8_symbols"),
            default_symbols=self._default_symbols,
        )
        state["telegram_healthy"] = _to_bool(state.get("telegram_healthy"), default["telegram_healthy"])
        state["last_error"] = _to_text(state.get("last_error"), default["last_error"])
        return state

    def _save_state_unlocked(self, state: Mapping[str, Any]) -> None:
        normalized = self._normalize_state(state)
        normalized["updated_at"] = _normalize_timestamp(normalized.get("updated_at"), _now_iso())
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        temp_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self._state_path)
