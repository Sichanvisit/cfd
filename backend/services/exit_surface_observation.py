"""Observation helpers for protective-exit vs continuation-hold surface states."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
OPEN_TRADES_PATH = ROOT_DIR / "data" / "trades" / "trade_history.csv"
CLOSED_TRADES_PATH = ROOT_DIR / "data" / "trades" / "trade_closed_history.csv"
ANALYSIS_DIR = ROOT_DIR / "data" / "analysis" / "shadow_auto"
CSV_OUTPUT_PATH = ANALYSIS_DIR / "exit_surface_observation_latest.csv"
JSON_OUTPUT_PATH = ANALYSIS_DIR / "exit_surface_observation_latest.json"
MD_OUTPUT_PATH = ANALYSIS_DIR / "exit_surface_observation_latest.md"


def _load_recent_csv(path: Path, recent_limit: int) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(path, dtype=str)
    if df.empty:
        return df
    return df.tail(max(1, int(recent_limit))).copy()


def _normalize_surface_state(raw_state: object, raw_reason: object) -> str:
    state = str(raw_state or "").strip().upper()
    if state in {"PARTIAL_REDUCE", "HOLD_RUNNER", "EXIT_PROTECT", "LOCK_PROFIT"}:
        return state
    alias = {
        "PARTIAL_THEN_RUNNER_HOLD": "PARTIAL_REDUCE",
        "RUNNER_LOCK_ONLY": "HOLD_RUNNER",
        "RUNNER_CONTINUE": "HOLD_RUNNER",
        "PROTECT_EXIT": "EXIT_PROTECT",
        "ADVERSE_RECHECK_PROTECT": "EXIT_PROTECT",
        "EMERGENCY_STOP": "EXIT_PROTECT",
        "RECOVERY_EXIT": "EXIT_PROTECT",
        "ADVERSE_STOP": "EXIT_PROTECT",
        "TIME_STOP": "EXIT_PROTECT",
        "LOCK_EXIT": "LOCK_PROFIT",
        "TARGET_EXIT": "LOCK_PROFIT",
        "ADVERSE_RECHECK_LOCK": "LOCK_PROFIT",
    }
    if state in alias:
        return alias[state]
    reason = str(raw_reason or "").strip().lower()
    if reason in {"protect exit", "recovery exit", "emergency stop", "adverse stop", "time stop"}:
        return "EXIT_PROTECT"
    if reason in {"lock exit", "target"}:
        return "LOCK_PROFIT"
    return ""


def _normalize_surface_family(raw_family: object, state: str) -> str:
    if state in {"PARTIAL_REDUCE", "HOLD_RUNNER"}:
        return "continuation_hold_surface"
    if state in {"EXIT_PROTECT", "LOCK_PROFIT"}:
        return "protective_exit_surface"
    family = str(raw_family or "").strip()
    if family:
        return family
    return ""


def build_exit_surface_observation_v1(
    *,
    open_trades_path: Path | None = None,
    closed_trades_path: Path | None = None,
    recent_limit: int = 120,
) -> dict[str, object]:
    open_path = Path(open_trades_path or OPEN_TRADES_PATH)
    closed_path = Path(closed_trades_path or CLOSED_TRADES_PATH)

    rows: list[dict[str, object]] = []
    for source, path in (("open", open_path), ("closed", closed_path)):
        df = _load_recent_csv(path, recent_limit)
        if df.empty:
            continue
        for row in df.to_dict(orient="records"):
            surface_state = _normalize_surface_state(
                row.get("exit_wait_decision_family", ""),
                row.get("exit_reason", ""),
            )
            surface_family = _normalize_surface_family(
                row.get("exit_policy_stage", ""),
                surface_state,
            )
            rows.append(
                {
                    "row_source": source,
                    "ticket": str(row.get("ticket", "") or ""),
                    "symbol": str(row.get("symbol", "") or "").upper(),
                    "status": str(row.get("status", "") or ""),
                    "open_time": str(row.get("open_time", "") or ""),
                    "close_time": str(row.get("close_time", "") or ""),
                    "exit_reason": str(row.get("exit_reason", "") or ""),
                    "policy_scope": str(row.get("policy_scope", "") or ""),
                    "exit_policy_stage": str(row.get("exit_policy_stage", "") or ""),
                    "exit_wait_decision_family": str(row.get("exit_wait_decision_family", "") or ""),
                    "exit_wait_bridge_status": str(row.get("exit_wait_bridge_status", "") or ""),
                    "surface_family": surface_family,
                    "surface_state": surface_state,
                }
            )

    out_df = pd.DataFrame(rows)
    if out_df.empty:
        return {
            "contract_version": "exit_surface_observation_v1",
            "status": "no_recent_trade_rows",
            "row_count": 0,
            "runner_preservation_total_count": 0,
            "runner_preservation_live_count": 0,
            "protective_surface_total_count": 0,
            "surface_state_counts": {},
            "surface_family_counts": {},
            "recent_runner_rows": [],
        }

    state_counts = {
        str(key): int(value)
        for key, value in out_df["surface_state"].fillna("").astype(str).value_counts(dropna=False).to_dict().items()
        if str(key)
    }
    family_counts = {
        str(key): int(value)
        for key, value in out_df["surface_family"].fillna("").astype(str).value_counts(dropna=False).to_dict().items()
        if str(key)
    }
    runner_mask = out_df["surface_state"].isin(["PARTIAL_REDUCE", "HOLD_RUNNER"])
    protective_mask = out_df["surface_state"].isin(["EXIT_PROTECT", "LOCK_PROFIT"])
    recent_runner_rows = (
        out_df.loc[runner_mask]
        .tail(5)
        .fillna("")
        .to_dict(orient="records")
    )

    runner_total = int(runner_mask.sum())
    runner_live = int((runner_mask & (out_df["row_source"] == "open")).sum())
    protective_total = int(protective_mask.sum())

    return {
        "contract_version": "exit_surface_observation_v1",
        "status": "runner_preservation_observed" if runner_total > 0 else "await_live_runner_preservation",
        "row_count": int(len(out_df)),
        "runner_preservation_total_count": runner_total,
        "runner_preservation_live_count": runner_live,
        "protective_surface_total_count": protective_total,
        "surface_state_counts": state_counts,
        "surface_family_counts": family_counts,
        "recent_runner_rows": recent_runner_rows,
        "table": out_df,
    }


def write_exit_surface_observation_v1(payload: dict[str, object]) -> dict[str, Path]:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_df = payload.get("table")
    if isinstance(out_df, pd.DataFrame):
        out_df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    json_payload = {k: v for k, v in payload.items() if k != "table"}
    JSON_OUTPUT_PATH.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Exit Surface Observation",
        "",
        f"- status: `{json_payload.get('status', '')}`",
        f"- row_count: `{json_payload.get('row_count', 0)}`",
        f"- runner_preservation_total_count: `{json_payload.get('runner_preservation_total_count', 0)}`",
        f"- runner_preservation_live_count: `{json_payload.get('runner_preservation_live_count', 0)}`",
        f"- protective_surface_total_count: `{json_payload.get('protective_surface_total_count', 0)}`",
        f"- surface_state_counts: `{json.dumps(json_payload.get('surface_state_counts', {}), ensure_ascii=False)}`",
        f"- surface_family_counts: `{json.dumps(json_payload.get('surface_family_counts', {}), ensure_ascii=False)}`",
    ]
    MD_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "csv_path": CSV_OUTPUT_PATH,
        "json_path": JSON_OUTPUT_PATH,
        "md_path": MD_OUTPUT_PATH,
    }
