"""Readiness report for comparing the calibrated rule forecast against future models.

This report combines:
- bucket validation status (FC8)
- current runtime/live forecast behavior (FC9)

The goal is not to approve live action gating. It is to answer whether the
current rule-based forecast is stable enough to serve as a shadow baseline for
later ML/DL comparison.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUNTIME_STATUS = PROJECT_ROOT / "data" / "runtime_status.json"
FORECAST_RULE_BASELINE_V1 = {
    "baseline_contract": "forecast_rule_baseline_v1",
    "baseline_name": "ForecastRuleV1",
    "baseline_role": "shadow_baseline",
    "score_semantics": "scenario_score",
    "calibrated_probability": False,
    "shadow_ready": True,
    "comparison_target_contract": "ForecastModelV1",
}
FORECAST_CALIBRATION_CONTRACT_V1 = {
    "contract_version": "forecast_calibration_v1",
    "scope": "forecast_calibration_only",
    "allowed_changes": [
        "forecast_score_structure",
        "separation_metrics",
        "shadow_validation_reporting",
    ],
    "forbidden_changes": [
        "semantic_foundation_recomposition",
        "symbol_exceptions",
        "consumer_retuning",
        "ml_model_activation",
        "live_action_gate_change",
    ],
    "live_action_gate_changed": False,
    "shadow_validation_ready": True,
}
BUCKET_SCRIPT_PATH = Path(__file__).with_name("forecast_bucket_validation.py")

_bucket_spec = importlib.util.spec_from_file_location("forecast_bucket_validation", BUCKET_SCRIPT_PATH)
if _bucket_spec is None or _bucket_spec.loader is None:
    raise ImportError(f"Unable to load {BUCKET_SCRIPT_PATH}")
_bucket_module = importlib.util.module_from_spec(_bucket_spec)
sys.modules[_bucket_spec.name] = _bucket_module
_bucket_spec.loader.exec_module(_bucket_module)

ENTRY_DECISIONS = _bucket_module.ENTRY_DECISIONS
OUT_DIR = _bucket_module.OUT_DIR
TRADE_CLOSED_HISTORY = _bucket_module.TRADE_CLOSED_HISTORY
_coerce_forecast_scores = _bucket_module._coerce_forecast_scores
_load_closed_history = _bucket_module._load_closed_history
_load_entry_decisions = _bucket_module._load_entry_decisions
build_bucket_validation_report = _bucket_module.build_bucket_validation_report

WAIT_CONFIRM_MAX = 0.20
CONFIRM_GAP_MIN = 0.05
RECENT_CONFIRM_ROWS = 120


def _load_runtime_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_transition_mapper_versions(runtime_status: dict[str, Any]) -> set[str]:
    versions: set[str] = set()
    for payload in ((runtime_status or {}).get("latest_signal_by_symbol", {}) or {}).values():
        if not isinstance(payload, dict):
            continue
        forecast = payload.get("transition_forecast_v1", {}) or {}
        if isinstance(forecast, dict):
            version = str((forecast.get("metadata", {}) or {}).get("mapper_version", "") or "").strip()
            if version:
                versions.add(version)
    return versions


def _parse_management_mapper_versions(runtime_status: dict[str, Any]) -> set[str]:
    versions: set[str] = set()
    for payload in ((runtime_status or {}).get("latest_signal_by_symbol", {}) or {}).values():
        if not isinstance(payload, dict):
            continue
        forecast = payload.get("trade_management_forecast_v1", {}) or {}
        if isinstance(forecast, dict):
            version = str((forecast.get("metadata", {}) or {}).get("mapper_version", "") or "").strip()
            if version:
                versions.add(version)
    return versions


def _extract_mapper_version(value: Any) -> str:
    text = str(value or "").strip()
    if not text.startswith("{"):
        return ""
    try:
        payload = json.loads(text)
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    return str((payload.get("metadata", {}) or {}).get("mapper_version", "") or "").strip()


def _filter_current_mapper_rows(entry_decisions, runtime_status: dict[str, Any]):
    if entry_decisions.empty:
        return entry_decisions.copy(), {"transition_mapper_versions": [], "management_mapper_versions": []}

    transition_versions = _parse_transition_mapper_versions(runtime_status)
    management_versions = _parse_management_mapper_versions(runtime_status)
    df = entry_decisions.copy()
    df["transition_mapper_version"] = df.get("transition_forecast_v1", "").fillna("").astype(str).apply(
        _extract_mapper_version
    )
    df["management_mapper_version"] = df.get("trade_management_forecast_v1", "").fillna("").astype(str).apply(
        _extract_mapper_version
    )

    mask = None
    if transition_versions:
        transition_mask = df["transition_mapper_version"].isin(transition_versions)
        mask = transition_mask if mask is None else (mask | transition_mask)
    if management_versions:
        management_mask = df["management_mapper_version"].isin(management_versions)
        mask = management_mask if mask is None else (mask | management_mask)
    if mask is None:
        return df, {
            "transition_mapper_versions": sorted(transition_versions),
            "management_mapper_versions": sorted(management_versions),
        }
    return (
        df[mask].copy(),
        {
            "transition_mapper_versions": sorted(transition_versions),
            "management_mapper_versions": sorted(management_versions),
        },
    )


def _build_runtime_wait_summary(runtime_status: dict[str, Any]) -> dict[str, Any]:
    latest = (runtime_status or {}).get("latest_signal_by_symbol", {}) or {}
    rows: list[dict[str, Any]] = []
    for symbol, payload in latest.items():
        if not isinstance(payload, dict):
            continue
        obs = payload.get("observe_confirm_v1", {}) or {}
        action = str(obs.get("action", "") or "").upper().strip()
        state = str(obs.get("state", "") or "").upper().strip()
        if not (action == "WAIT" or state.endswith("OBSERVE") or state.endswith("WAIT")):
            continue
        transition = payload.get("transition_forecast_v1", {}) or {}
        buy_confirm = float(transition.get("p_buy_confirm", 0.0) or 0.0)
        sell_confirm = float(transition.get("p_sell_confirm", 0.0) or 0.0)
        confirm_max = max(buy_confirm, sell_confirm)
        rows.append(
            {
                "symbol": str(symbol or "").upper(),
                "state": state,
                "confirm_max": confirm_max,
                "pass": bool(confirm_max <= WAIT_CONFIRM_MAX),
            }
        )
    wait_rows = len(rows)
    pass_rows = sum(1 for row in rows if row["pass"])
    return {
        "rows": rows,
        "wait_rows": wait_rows,
        "wait_pass_rows": pass_rows,
        "wait_pass_rate": (float(pass_rows) / float(wait_rows)) if wait_rows else None,
        "wait_confirm_threshold": WAIT_CONFIRM_MAX,
    }


def _build_recent_wait_summary(entry_decisions, runtime_status: dict[str, Any]) -> dict[str, Any]:
    if entry_decisions.empty:
        return {
            "rows": [],
            "wait_rows": 0,
            "wait_pass_rows": 0,
            "wait_pass_rate": None,
            "wait_confirm_threshold": WAIT_CONFIRM_MAX,
        }

    df = _coerce_forecast_scores(entry_decisions)
    transition_versions = _parse_transition_mapper_versions(runtime_status)
    if transition_versions:
        df["transition_mapper_version"] = (
            df.get("transition_forecast_v1", "").fillna("").astype(str).apply(_extract_mapper_version)
        )
        df = df[df["transition_mapper_version"].isin(transition_versions)].copy()
    df = df.tail(RECENT_CONFIRM_ROWS).copy()

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        obs = {}
        try:
            obs = json.loads(str(row.get("observe_confirm_v1", "") or "").strip() or "{}")
            if not isinstance(obs, dict):
                obs = {}
        except Exception:
            obs = {}
        action = str(obs.get("action", row.get("action", "")) or "").upper().strip()
        state = str(obs.get("state", "") or "").upper().strip()
        if not (action == "WAIT" or state.endswith("OBSERVE") or state.endswith("WAIT")):
            continue
        confirm_max = max(float(row.get("p_buy_confirm") or 0.0), float(row.get("p_sell_confirm") or 0.0))
        rows.append(
            {
                "time": str(row.get("time", "") or ""),
                "symbol": str(row.get("symbol", "") or "").upper(),
                "state": state,
                "confirm_max": confirm_max,
                "pass": bool(confirm_max <= WAIT_CONFIRM_MAX),
            }
        )

    total = len(rows)
    pass_rows = sum(1 for row in rows if row["pass"])
    return {
        "rows": rows,
        "wait_rows": total,
        "wait_pass_rows": pass_rows,
        "wait_pass_rate": (float(pass_rows) / float(total)) if total else None,
        "wait_confirm_threshold": WAIT_CONFIRM_MAX,
    }


def _build_recent_confirm_summary(entry_decisions, runtime_status: dict[str, Any]) -> dict[str, Any]:
    if entry_decisions.empty:
        return {
            "rows": [],
            "confirm_rows": 0,
            "confirm_gap_pass_rows": 0,
            "confirm_gap_pass_rate": None,
            "confirm_gap_threshold": CONFIRM_GAP_MIN,
        }

    df = _coerce_forecast_scores(entry_decisions)
    transition_versions = _parse_transition_mapper_versions(runtime_status)
    if transition_versions:
        df["transition_mapper_version"] = (
            df.get("transition_forecast_v1", "")
            .fillna("")
            .astype(str)
            .apply(lambda text: str((((json.loads(text) if text else {}) or {}).get("metadata", {}) or {}).get("mapper_version", "") if text.strip().startswith("{") else ""))
        )
        df = df[df["transition_mapper_version"].isin(transition_versions)].copy()

    df = df.tail(RECENT_CONFIRM_ROWS).copy()
    confirm_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        obs = {}
        try:
            obs = json.loads(str(row.get("observe_confirm_v1", "") or "").strip() or "{}")
            if not isinstance(obs, dict):
                obs = {}
        except Exception:
            obs = {}
        action = str(obs.get("action", row.get("action", "")) or "").upper().strip()
        state = str(obs.get("state", "") or "").upper().strip()
        if action not in {"BUY", "SELL"} and not state.endswith("CONFIRM"):
            continue
        if action == "BUY":
            dominant_confirm = float(row.get("p_buy_confirm") or 0.0)
        elif action == "SELL":
            dominant_confirm = float(row.get("p_sell_confirm") or 0.0)
        else:
            dominant_confirm = max(float(row.get("p_buy_confirm") or 0.0), float(row.get("p_sell_confirm") or 0.0))
        false_break = float(row.get("p_false_break") or 0.0)
        gap = dominant_confirm - false_break
        confirm_rows.append(
            {
                "time": str(row.get("time", "") or ""),
                "symbol": str(row.get("symbol", "") or "").upper(),
                "action": action,
                "state": state,
                "dominant_confirm": dominant_confirm,
                "false_break": false_break,
                "confirm_fake_gap": gap,
                "pass": bool(gap >= CONFIRM_GAP_MIN),
            }
        )

    total = len(confirm_rows)
    pass_rows = sum(1 for row in confirm_rows if row["pass"])
    return {
        "rows": confirm_rows,
        "confirm_rows": total,
        "confirm_gap_pass_rows": pass_rows,
        "confirm_gap_pass_rate": (float(pass_rows) / float(total)) if total else None,
        "confirm_gap_threshold": CONFIRM_GAP_MIN,
    }


def _transition_status(bucket_report: dict[str, Any], runtime_wait: dict[str, Any], recent_confirm: dict[str, Any]) -> str:
    transition = (bucket_report or {}).get("transition", {}) or {}
    sell_confirm = (transition.get("p_sell_confirm", {}) or {})
    wait_rate = runtime_wait.get("wait_pass_rate")
    confirm_rate = recent_confirm.get("confirm_gap_pass_rate")
    sell_monotonic = sell_confirm.get("monotonic_non_decreasing")

    if wait_rate is None or confirm_rate is None:
        return "INSUFFICIENT_LIVE_ROWS"
    if bool(sell_monotonic) and wait_rate >= 0.80 and confirm_rate >= 0.70:
        return "READY_FOR_MODEL_COMPARE"
    if wait_rate >= 0.65 and confirm_rate >= 0.55:
        return "NEAR_PASS"
    return "NEEDS_MORE_CALIBRATION"


def _management_status(bucket_report: dict[str, Any]) -> str:
    management = (bucket_report or {}).get("management", {}) or {}
    continue_rows = int(((management.get("p_continue_favor", {}) or {}).get("labeled_rows", 0)) or 0)
    fail_rows = int(((management.get("p_fail_now", {}) or {}).get("labeled_rows", 0)) or 0)
    if continue_rows <= 0 and fail_rows <= 0:
        return "PENDING_OUTCOME_LABELER"
    return "READY_FOR_MODEL_COMPARE"


def build_shadow_compare_readiness_report(
    entry_decisions,
    closed_history,
    runtime_status: dict[str, Any],
) -> dict[str, Any]:
    filtered_entry_decisions, mapper_filter = _filter_current_mapper_rows(entry_decisions, runtime_status)
    bucket_report = build_bucket_validation_report(filtered_entry_decisions, closed_history)
    current_runtime_wait = _build_runtime_wait_summary(runtime_status)
    recent_wait = _build_recent_wait_summary(filtered_entry_decisions, runtime_status)
    recent_confirm = _build_recent_confirm_summary(filtered_entry_decisions, runtime_status)

    wait_acceptance = recent_wait if recent_wait.get("wait_rows", 0) > 0 else current_runtime_wait
    transition_status = _transition_status(bucket_report, wait_acceptance, recent_confirm)
    management_status = _management_status(bucket_report)
    if transition_status == "READY_FOR_MODEL_COMPARE" and management_status == "READY_FOR_MODEL_COMPARE":
        overall_status = "READY_FOR_SHADOW_COMPARE"
    elif transition_status in {"READY_FOR_MODEL_COMPARE", "NEAR_PASS"} and management_status == "PENDING_OUTCOME_LABELER":
        overall_status = "TRANSITION_READY_MANAGEMENT_PENDING"
    else:
        overall_status = "NEEDS_MORE_CALIBRATION"

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "baseline_contract": dict(FORECAST_RULE_BASELINE_V1),
        "calibration_contract": dict(FORECAST_CALIBRATION_CONTRACT_V1),
        "sources": {
            "entry_decisions_csv": str(ENTRY_DECISIONS),
            "trade_closed_history_csv": str(TRADE_CLOSED_HISTORY),
            "runtime_status_json": str(RUNTIME_STATUS),
            "mapper_filter": mapper_filter,
        },
        "transition_readiness": {
            "bucket_validation": {
                "p_buy_confirm": (bucket_report.get("transition", {}) or {}).get("p_buy_confirm", {}),
                "p_sell_confirm": (bucket_report.get("transition", {}) or {}).get("p_sell_confirm", {}),
                "p_false_break": (bucket_report.get("transition", {}) or {}).get("p_false_break", {}),
            },
            "current_runtime_wait_acceptance": current_runtime_wait,
            "recent_wait_acceptance": recent_wait,
            "recent_confirm_acceptance": recent_confirm,
            "overall_status": transition_status,
        },
        "management_readiness": {
            "bucket_validation": {
                "p_continue_favor": (bucket_report.get("management", {}) or {}).get("p_continue_favor", {}),
                "p_fail_now": (bucket_report.get("management", {}) or {}).get("p_fail_now", {}),
            },
            "overall_status": management_status,
            "notes": [
                "management forecast still relies on resolved trade proxy labels",
                "full readiness requires OutcomeLabeler coverage",
            ],
        },
        "overall_status": overall_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-csv", default=str(ENTRY_DECISIONS))
    parser.add_argument("--closed-history-csv", default=str(TRADE_CLOSED_HISTORY))
    parser.add_argument("--runtime-json", default=str(RUNTIME_STATUS))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    entry_df = _load_entry_decisions(Path(str(args.entry_csv)))
    closed_df = _load_closed_history(Path(str(args.closed_history_csv)))
    runtime_status = _load_runtime_status(Path(str(args.runtime_json)))
    report = build_shadow_compare_readiness_report(entry_df, closed_df, runtime_status)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"forecast_shadow_compare_readiness_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
