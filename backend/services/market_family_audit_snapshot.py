"""Market-family entry/exit audit snapshots for NAS/BTC/XAU."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


MARKET_FAMILY_ENTRY_AUDIT_CONTRACT_VERSION = "market_family_entry_audit_v1"
MARKET_FAMILY_EXIT_AUDIT_CONTRACT_VERSION = "market_family_exit_audit_v1"
DEFAULT_MARKET_FAMILY_SYMBOLS = ("NAS100", "BTCUSD", "XAUUSD")

MARKET_FAMILY_ENTRY_AUDIT_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "symbol",
    "row_count",
    "metric_group",
    "metric_value",
    "count",
    "share",
    "recommended_focus",
]

MARKET_FAMILY_EXIT_AUDIT_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "symbol",
    "row_count",
    "auto_row_count",
    "metric_group",
    "metric_value",
    "count",
    "share",
    "avg_profit",
    "median_profit",
    "avg_hold_minutes",
    "recommended_focus",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _series_counts(values: pd.Series, *, blank_label: str | None = None) -> dict[str, int]:
    series = values.fillna("").astype(str).str.strip()
    if blank_label is None:
        series = series.replace("", pd.NA).dropna()
    else:
        series = series.replace("", blank_label)
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _stable_join(values: Iterable[str]) -> str:
    seen: list[str] = []
    for raw in values:
        text = _to_text(raw)
        if not text or text in seen:
            continue
        seen.append(text)
    return ",".join(seen)


def _append_metric_rows(
    rows: list[dict[str, Any]],
    *,
    base_payload: Mapping[str, Any],
    metric_group: str,
    counts: Mapping[str, int],
    denominator: int,
) -> None:
    total = max(1, int(denominator))
    for metric_value, count in counts.items():
        rows.append(
            {
                **dict(base_payload),
                "metric_group": _to_text(metric_group),
                "metric_value": _to_text(metric_value),
                "count": int(count),
                "share": round(float(count) / float(total), 6),
            }
        )


def _symbol_focus_entry(
    symbol: str,
    blocked_counts: Mapping[str, int],
    none_counts: Mapping[str, int],
    observe_counts: Mapping[str, int],
) -> str:
    top_blocked = next(iter(blocked_counts.keys()), "")
    top_none = next(iter(none_counts.keys()), "")
    top_observe = next(iter(observe_counts.keys()), "")
    symbol_key = _to_text(symbol).lower()
    if symbol == "XAUUSD" and top_blocked == "outer_band_guard":
        return "inspect_xau_outer_band_follow_through_bridge"
    if symbol == "BTCUSD" and (
        top_blocked == "middle_sr_anchor_guard" or top_observe == "middle_sr_anchor_required_observe"
    ):
        return "inspect_btc_middle_anchor_probe_relief"
    if symbol == "NAS100" and top_none == "observe_state_wait":
        return "inspect_nas_conflict_observe_decomposition"
    if top_none == "probe_not_promoted":
        return f"inspect_{symbol_key}_probe_promotion_gap"
    if top_none == "observe_state_wait":
        return f"inspect_{symbol_key}_observe_no_action_gap"
    if top_blocked and top_blocked != "BLANK":
        return f"inspect_{symbol_key}_{top_blocked}"
    return f"inspect_{symbol_key}_market_family_wait_gap"


def _hold_minutes(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    open_dt = pd.to_datetime(frame.get("open_time"), errors="coerce")
    close_dt = pd.to_datetime(frame.get("close_time"), errors="coerce")
    minutes = (close_dt - open_dt).dt.total_seconds().div(60.0)
    if minutes.isna().all():
        open_ts = pd.to_numeric(frame.get("open_ts"), errors="coerce")
        close_ts = pd.to_numeric(frame.get("close_ts"), errors="coerce")
        minutes = (close_ts - open_ts).div(60.0)
    return minutes.where(minutes >= 0)


def _symbol_focus_exit(symbol: str, auto_exit_counts: Mapping[str, int], auto_row_count: int) -> str:
    symbol_key = _to_text(symbol).lower()
    if auto_row_count <= 0:
        return f"collect_more_{symbol_key}_auto_exit_rows"
    runner_like = 0
    protect_like = 0
    for reason, count in auto_exit_counts.items():
        reason_lower = _to_text(reason).lower()
        if "lock exit" in reason_lower or "profit_giveback" in reason_lower or reason.startswith("Target"):
            runner_like += int(count)
        if "protect exit" in reason_lower or "hard_guard=adverse" in reason_lower:
            protect_like += int(count)
    if runner_like >= max(1, int(round(auto_row_count * 0.1))):
        return f"inspect_{symbol_key}_runner_preservation"
    if protect_like >= max(1, int(round(auto_row_count * 0.2))):
        return f"inspect_{symbol_key}_protective_exit_overfire"
    return f"inspect_{symbol_key}_exit_surface_split"


def build_market_family_entry_audit(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = DEFAULT_MARKET_FAMILY_SYMBOLS,
    recent_limit: int = 240,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    semantic_live_config = dict(runtime.get("semantic_live_config", {}) or {})
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    symbol_order = [str(symbol) for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": MARKET_FAMILY_ENTRY_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "symbols": _stable_join(symbol_order),
        "symbol_row_counts": "{}",
        "symbol_outcome_counts": "{}",
        "symbol_blocked_by_counts": "{}",
        "symbol_action_none_reason_counts": "{}",
        "symbol_observe_reason_counts": "{}",
        "symbol_focus_map": "{}",
        "recommended_next_action": "collect_more_market_family_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=MARKET_FAMILY_ENTRY_AUDIT_COLUMNS), summary

    decisions = frame.copy()
    for column in ("time", "symbol", "outcome", "blocked_by", "action_none_reason", "observe_reason", "core_reason"):
        if column not in decisions.columns:
            decisions[column] = ""
    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].fillna("").astype(str).isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=MARKET_FAMILY_ENTRY_AUDIT_COLUMNS), summary

    rows: list[dict[str, Any]] = []
    symbol_row_counts: dict[str, int] = {}
    symbol_outcome_counts: dict[str, dict[str, int]] = {}
    symbol_blocked_counts: dict[str, dict[str, int]] = {}
    symbol_none_counts: dict[str, dict[str, int]] = {}
    symbol_observe_counts: dict[str, dict[str, int]] = {}
    symbol_focus_map: dict[str, str] = {}

    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"].fillna("").astype(str) == symbol].copy()
        row_count = int(len(symbol_frame))
        symbol_row_counts[symbol] = row_count
        if row_count <= 0:
            symbol_focus_map[symbol] = f"collect_more_{symbol.lower()}_rows"
            continue

        outcome_counts = _series_counts(symbol_frame["outcome"], blank_label="BLANK")
        blocked_counts = _series_counts(symbol_frame["blocked_by"], blank_label="BLANK")
        none_counts = _series_counts(symbol_frame["action_none_reason"])
        observe_counts = _series_counts(symbol_frame["observe_reason"])
        core_counts = _series_counts(symbol_frame["core_reason"])
        focus = _symbol_focus_entry(symbol, blocked_counts, none_counts, observe_counts)

        symbol_outcome_counts[symbol] = outcome_counts
        symbol_blocked_counts[symbol] = blocked_counts
        symbol_none_counts[symbol] = none_counts
        symbol_observe_counts[symbol] = observe_counts
        symbol_focus_map[symbol] = focus

        base_payload = {
            "observation_event_id": f"{MARKET_FAMILY_ENTRY_AUDIT_CONTRACT_VERSION}:{generated_at}:{symbol}",
            "generated_at": generated_at,
            "runtime_updated_at": _to_text(runtime.get("updated_at")),
            "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
            "symbol": symbol,
            "row_count": row_count,
            "recommended_focus": focus,
        }
        _append_metric_rows(rows, base_payload=base_payload, metric_group="outcome", counts=outcome_counts, denominator=row_count)
        _append_metric_rows(rows, base_payload=base_payload, metric_group="blocked_by", counts=blocked_counts, denominator=row_count)
        _append_metric_rows(rows, base_payload=base_payload, metric_group="action_none_reason", counts=none_counts, denominator=row_count)
        _append_metric_rows(rows, base_payload=base_payload, metric_group="observe_reason", counts=observe_counts, denominator=row_count)
        _append_metric_rows(rows, base_payload=base_payload, metric_group="core_reason", counts=core_counts, denominator=row_count)

    summary["symbol_row_counts"] = _json_counts(symbol_row_counts)
    summary["symbol_outcome_counts"] = json.dumps(symbol_outcome_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_blocked_by_counts"] = json.dumps(symbol_blocked_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_action_none_reason_counts"] = json.dumps(symbol_none_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_observe_reason_counts"] = json.dumps(symbol_observe_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_focus_map"] = json.dumps(symbol_focus_map, ensure_ascii=False, sort_keys=True)
    summary["recommended_next_action"] = _stable_join(symbol_focus_map.get(symbol, "") for symbol in symbol_order)

    return pd.DataFrame(rows, columns=MARKET_FAMILY_ENTRY_AUDIT_COLUMNS), summary


def build_market_family_exit_audit(
    runtime_status: Mapping[str, Any] | None,
    closed_trade_history: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = DEFAULT_MARKET_FAMILY_SYMBOLS,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = closed_trade_history.copy() if closed_trade_history is not None and not closed_trade_history.empty else pd.DataFrame()
    symbol_order = [str(symbol) for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": MARKET_FAMILY_EXIT_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "symbols": _stable_join(symbol_order),
        "symbol_row_counts": "{}",
        "symbol_auto_row_counts": "{}",
        "symbol_exit_reason_counts": "{}",
        "symbol_auto_exit_reason_counts": "{}",
        "symbol_focus_map": "{}",
        "recommended_next_action": "collect_more_market_family_exit_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=MARKET_FAMILY_EXIT_AUDIT_COLUMNS), summary

    trades = frame.copy()
    for column in ("close_time", "symbol", "entry_reason", "exit_reason", "status", "profit", "open_time", "open_ts", "close_ts"):
        if column not in trades.columns:
            trades[column] = ""
    trades["__close_sort"] = pd.to_datetime(trades["close_time"], errors="coerce")
    trades = trades.sort_values("__close_sort", ascending=False).drop(columns="__close_sort")
    recent = trades.head(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].fillna("").astype(str).isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=MARKET_FAMILY_EXIT_AUDIT_COLUMNS), summary

    rows: list[dict[str, Any]] = []
    symbol_row_counts: dict[str, int] = {}
    symbol_auto_row_counts: dict[str, int] = {}
    symbol_exit_reason_counts: dict[str, dict[str, int]] = {}
    symbol_auto_exit_reason_counts: dict[str, dict[str, int]] = {}
    symbol_focus_map: dict[str, str] = {}

    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"].fillna("").astype(str) == symbol].copy()
        row_count = int(len(symbol_frame))
        symbol_row_counts[symbol] = row_count
        if row_count <= 0:
            symbol_focus_map[symbol] = f"collect_more_{symbol.lower()}_exit_rows"
            continue

        symbol_frame["exit_reason_prefix"] = symbol_frame["exit_reason"].fillna("").astype(str).str.split("|").str[0].str.strip()
        auto_mask = symbol_frame["entry_reason"].fillna("").astype(str).str.startswith("[AUTO]")
        auto_frame = symbol_frame.loc[auto_mask].copy()
        auto_row_count = int(len(auto_frame))
        symbol_auto_row_counts[symbol] = auto_row_count

        exit_reason_counts = _series_counts(symbol_frame["exit_reason_prefix"], blank_label="BLANK")
        auto_exit_reason_counts = _series_counts(auto_frame["exit_reason_prefix"], blank_label="BLANK")
        status_counts = _series_counts(symbol_frame["status"], blank_label="BLANK")
        hold_minutes = _hold_minutes(symbol_frame)
        profit_values = pd.to_numeric(symbol_frame["profit"], errors="coerce")
        avg_profit = round(float(profit_values.dropna().mean()), 6) if profit_values.notna().any() else 0.0
        median_profit = round(float(profit_values.dropna().median()), 6) if profit_values.notna().any() else 0.0
        avg_hold_minutes = round(float(hold_minutes.dropna().mean()), 6) if hold_minutes.notna().any() else 0.0
        focus = _symbol_focus_exit(symbol, auto_exit_reason_counts, auto_row_count)

        symbol_exit_reason_counts[symbol] = exit_reason_counts
        symbol_auto_exit_reason_counts[symbol] = auto_exit_reason_counts
        symbol_focus_map[symbol] = focus

        base_payload = {
            "observation_event_id": f"{MARKET_FAMILY_EXIT_AUDIT_CONTRACT_VERSION}:{generated_at}:{symbol}",
            "generated_at": generated_at,
            "runtime_updated_at": _to_text(runtime.get("updated_at")),
            "symbol": symbol,
            "row_count": row_count,
            "auto_row_count": auto_row_count,
            "avg_profit": avg_profit,
            "median_profit": median_profit,
            "avg_hold_minutes": avg_hold_minutes,
            "recommended_focus": focus,
        }
        _append_metric_rows(rows, base_payload=base_payload, metric_group="exit_reason", counts=exit_reason_counts, denominator=row_count)
        if auto_row_count > 0:
            _append_metric_rows(rows, base_payload=base_payload, metric_group="auto_exit_reason", counts=auto_exit_reason_counts, denominator=auto_row_count)
        _append_metric_rows(rows, base_payload=base_payload, metric_group="status", counts=status_counts, denominator=row_count)

    summary["symbol_row_counts"] = _json_counts(symbol_row_counts)
    summary["symbol_auto_row_counts"] = _json_counts(symbol_auto_row_counts)
    summary["symbol_exit_reason_counts"] = json.dumps(symbol_exit_reason_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_auto_exit_reason_counts"] = json.dumps(symbol_auto_exit_reason_counts, ensure_ascii=False, sort_keys=True)
    summary["symbol_focus_map"] = json.dumps(symbol_focus_map, ensure_ascii=False, sort_keys=True)
    summary["recommended_next_action"] = _stable_join(symbol_focus_map.get(symbol, "") for symbol in symbol_order)

    return pd.DataFrame(rows, columns=MARKET_FAMILY_EXIT_AUDIT_COLUMNS), summary


def render_market_family_entry_audit_markdown(summary: Mapping[str, Any], frame: pd.DataFrame | None) -> str:
    row = dict(summary or {})
    lines = [
        "# Market-Family Entry Audit Snapshot",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(row.get('rollout_mode'), 'disabled')}`",
        f"- recent_row_count: `{int(_to_float(row.get('recent_row_count'), 0.0))}`",
        f"- market_family_row_count: `{int(_to_float(row.get('market_family_row_count'), 0.0))}`",
        f"- symbols: `{_to_text(row.get('symbols'))}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
        "",
        "## Symbol Focus Map",
        "",
        f"- symbol_focus_map: `{_to_text(row.get('symbol_focus_map'), '{}')}`",
    ]
    if frame is None or frame.empty:
        lines.extend(["", "_No market-family entry rows found._"])
        return "\n".join(lines) + "\n"

    for symbol in DEFAULT_MARKET_FAMILY_SYMBOLS:
        symbol_frame = frame.loc[frame["symbol"] == symbol].copy()
        if symbol_frame.empty:
            continue
        first = symbol_frame.iloc[0].to_dict()
        lines.extend(
            [
                "",
                f"## {symbol}",
                "",
                f"- row_count: `{int(_to_float(first.get('row_count'), 0.0))}`",
                f"- recommended_focus: `{_to_text(first.get('recommended_focus'))}`",
            ]
        )
        for metric_group in ("outcome", "blocked_by", "action_none_reason", "observe_reason"):
            group_frame = symbol_frame.loc[symbol_frame["metric_group"] == metric_group].copy()
            if group_frame.empty:
                continue
            counts = {
                _to_text(metric_row["metric_value"]): int(_to_float(metric_row["count"], 0.0))
                for _, metric_row in group_frame.iterrows()
            }
            lines.append(f"- {metric_group}: `{json.dumps(counts, ensure_ascii=False, sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def render_market_family_exit_audit_markdown(summary: Mapping[str, Any], frame: pd.DataFrame | None) -> str:
    row = dict(summary or {})
    lines = [
        "# Market-Family Exit Audit Snapshot",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- recent_row_count: `{int(_to_float(row.get('recent_row_count'), 0.0))}`",
        f"- market_family_row_count: `{int(_to_float(row.get('market_family_row_count'), 0.0))}`",
        f"- symbols: `{_to_text(row.get('symbols'))}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
        "",
        "## Symbol Focus Map",
        "",
        f"- symbol_focus_map: `{_to_text(row.get('symbol_focus_map'), '{}')}`",
    ]
    if frame is None or frame.empty:
        lines.extend(["", "_No market-family exit rows found._"])
        return "\n".join(lines) + "\n"

    for symbol in DEFAULT_MARKET_FAMILY_SYMBOLS:
        symbol_frame = frame.loc[frame["symbol"] == symbol].copy()
        if symbol_frame.empty:
            continue
        first = symbol_frame.iloc[0].to_dict()
        lines.extend(
            [
                "",
                f"## {symbol}",
                "",
                f"- row_count: `{int(_to_float(first.get('row_count'), 0.0))}`",
                f"- auto_row_count: `{int(_to_float(first.get('auto_row_count'), 0.0))}`",
                f"- avg_profit: `{round(_to_float(first.get('avg_profit'), 0.0), 6)}`",
                f"- median_profit: `{round(_to_float(first.get('median_profit'), 0.0), 6)}`",
                f"- avg_hold_minutes: `{round(_to_float(first.get('avg_hold_minutes'), 0.0), 6)}`",
                f"- recommended_focus: `{_to_text(first.get('recommended_focus'))}`",
            ]
        )
        for metric_group in ("exit_reason", "auto_exit_reason", "status"):
            group_frame = symbol_frame.loc[symbol_frame["metric_group"] == metric_group].copy()
            if group_frame.empty:
                continue
            counts = {
                _to_text(metric_row["metric_value"]): int(_to_float(metric_row["count"], 0.0))
                for _, metric_row in group_frame.iterrows()
            }
            lines.append(f"- {metric_group}: `{json.dumps(counts, ensure_ascii=False, sort_keys=True)}`")
    return "\n".join(lines) + "\n"
