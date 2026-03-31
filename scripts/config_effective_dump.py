from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import Config  # noqa: E402


ENV_PATH = PROJECT_ROOT / ".env"
OUT_DIR = PROJECT_ROOT / "data" / "analysis"


SECTION_PREFIXES = {
    "entry": ("ENTRY_", "ENABLE_ENTRY_", "AI_ENTRY_"),
    "wait": ("ENTRY_WAIT_", "ADVERSE_WAIT_"),
    "exit": (
        "EXIT_",
        "REVERSE_",
        "PROFIT_GIVEBACK_",
        "PLUS_TO_MINUS_",
        "ADVERSE_REVERSE_",
        "REVERSAL_",
        "MIN_HOLD_SECONDS_FOR_REVERSAL",
    ),
    "learning": (
        "LEARNING_",
        "LABEL_",
        "POLICY_",
        "REGIME_SWITCH_",
        "ENTRY_CONDITION_",
        "ENABLE_ENTRY_CONDITION_LEARNING",
    ),
    "predictor": ("AI_", "ENTRY_UTILITY_"),
}


RUNTIME_FIELDS = {
    "entry": [
        "WATCH_LIST",
        "ENTRY_THRESHOLD",
        "ENTRY_COOLDOWN",
        "AI_ENTRY_THRESHOLD",
        "AI_USE_ENTRY_FILTER",
        "AI_ENTRY_WEIGHT",
        "ENABLE_ADAPTIVE_ENTRY_ROUTING",
        "ENTRY_STAGE_AGGRESSIVE_MULT",
        "ENTRY_STAGE_BALANCED_MULT",
        "ENTRY_STAGE_CONSERVATIVE_MULT",
        "ENABLE_ENTRY_CONDITION_LEARNING",
        "ENTRY_CORE_MIN_SCORE",
        "ENABLE_ENTRY_PREFLIGHT_2H",
    ],
    "wait": [
        "ADVERSE_WAIT_MIN_SECONDS",
        "ADVERSE_WAIT_MAX_SECONDS",
        "ADVERSE_WAIT_RECOVERY_USD",
        "ADVERSE_WAIT_NO_TURN_SCORE_GAP",
        "ADVERSE_WAIT_DISABLE_ON_GIVEBACK",
        "ADVERSE_WAIT_GIVEBACK_MIN_PEAK_USD",
        "ADVERSE_WAIT_GIVEBACK_MIN_USD",
        "ADVERSE_WAIT_GIVEBACK_PROFIT_FLOOR_USD",
    ],
    "exit": [
        "EXIT_THRESHOLD",
        "PROFIT_GIVEBACK_MIN_PEAK_USD",
        "PROFIT_GIVEBACK_RETRACE_USD",
        "PLUS_TO_MINUS_MIN_RETRACE_USD",
        "REVERSE_SIGNAL_THRESHOLD",
        "REVERSAL_MIN_SCORE_GAP",
        "MIN_HOLD_SECONDS_FOR_REVERSAL",
        "ADVERSE_REVERSE_PLUS_TO_MINUS_MULT",
        "ADVERSE_REVERSE_PLUS_TO_MINUS_MIN_SCORE_GAP",
    ],
    "learning": [
        "ENABLE_ENTRY_CONDITION_LEARNING",
        "ENTRY_CONDITION_REFRESH_SEC",
        "ENTRY_CONDITION_MIN_SAMPLES",
        "ENTRY_CONDITION_WEIGHT_STRENGTH",
        "ENTRY_CONDITION_MULT_MIN",
        "ENTRY_CONDITION_MULT_MAX",
    ],
    "predictor": [
        "AI_ENTRY_THRESHOLD",
        "AI_EXIT_THRESHOLD",
        "AI_ENTRY_WEIGHT",
        "AI_EXIT_WEIGHT",
        "ENABLE_ENTRY_UTILITY_GATE",
    ],
}


SYMBOL_FIELDS = {
    "entry": {
        "entry_threshold": ("ENTRY_THRESHOLD_BY_SYMBOL", "ENTRY_THRESHOLD", "int"),
        "max_positions": ("MAX_POSITIONS_BY_SYMBOL", "MAX_POSITIONS", "int"),
    },
    "wait": {},
    "exit": {
        "exit_threshold": ("EXIT_THRESHOLD_BY_SYMBOL", "EXIT_THRESHOLD", "int"),
        "reverse_signal_threshold": (
            "REVERSE_SIGNAL_THRESHOLD_BY_SYMBOL",
            "REVERSE_SIGNAL_THRESHOLD",
            "int",
        ),
    },
    "learning": {},
    "predictor": {},
}


def read_effective_env(env_path: Path) -> tuple[dict[str, str], dict[str, list[int]]]:
    effective: dict[str, str] = {}
    positions: dict[str, list[int]] = {}
    for lineno, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        effective[key] = value.strip()
        positions.setdefault(key, []).append(lineno)
    duplicates = {key: lines for key, lines in positions.items() if len(lines) > 1}
    return effective, duplicates


def as_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [as_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): as_jsonable(v) for k, v in value.items()}
    return str(value)


def collect_runtime(section: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in RUNTIME_FIELDS.get(section, []):
        if hasattr(Config, field):
            data[field] = as_jsonable(getattr(Config, field))
    return data


def collect_symbol_values(section: str) -> dict[str, dict[str, Any]]:
    field_specs = SYMBOL_FIELDS.get(section, {})
    if not field_specs:
        return {}

    result: dict[str, dict[str, Any]] = {}
    for symbol in Config.WATCH_LIST:
        result[symbol] = {}
        for alias, (mapping_name, default_name, kind) in field_specs.items():
            mapping = getattr(Config, mapping_name, {})
            default = getattr(Config, default_name)
            if kind == "int":
                value = Config.get_symbol_int(symbol, mapping, default)
            else:
                value = Config.get_symbol_float(symbol, mapping, default)
            result[symbol][alias] = value
    return result


def collect_env_section(effective_env: dict[str, str], section: str) -> dict[str, str]:
    prefixes = SECTION_PREFIXES.get(section, ())
    result = {
        key: value
        for key, value in effective_env.items()
        if any(key.startswith(prefix) for prefix in prefixes)
    }
    return dict(sorted(result.items()))


def build_report() -> dict[str, Any]:
    effective_env, duplicates = read_effective_env(ENV_PATH)
    sections: dict[str, Any] = {}
    for name in SECTION_PREFIXES:
        sections[name] = {
            "runtime": collect_runtime(name),
            "symbols": collect_symbol_values(name),
            "env_effective": collect_env_section(effective_env, name),
        }

    watch_counter = Counter(Config.WATCH_LIST)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "env_path": str(ENV_PATH),
        "watch_list": list(Config.WATCH_LIST),
        "watch_list_duplicates": [key for key, count in watch_counter.items() if count > 1],
        "active_duplicate_env_keys": duplicates,
        "sections": sections,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"config_effective_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "report": str(out_path),
                "active_duplicate_env_keys": report["active_duplicate_env_keys"],
                "watch_list": report["watch_list"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
