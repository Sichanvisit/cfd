from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.p0_decision_trace import build_p0_decision_trace_v1


REPORT_VERSION = "profitability_operations_p1_lifecycle_correlation_v2"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_DECISIONS_PATH = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_DECISION_DETAIL_PATH = ROOT / "data" / "trades" / "entry_decisions.detail.jsonl"
DEFAULT_OPEN_TRADES_PATH = ROOT / "data" / "trades" / "trade_history.csv"
DEFAULT_CLOSED_TRADES_PATH = ROOT / "data" / "trades" / "trade_closed_history.csv"


@dataclass
class DecisionRecord:
    symbol: str
    setup_key: str
    regime_key: str
    side_key: str
    coverage_state: str
    outcome: str
    blocked_by: str
    action_none_reason: str
    observe_reason: str
    owner_relation: str
    consumer_check_stage: str


@dataclass
class TradeRecord:
    symbol: str
    setup_key: str
    regime_key: str
    side_key: str
    status: str
    direction: str
    profit_value: float
    hold_seconds: float | None
    decision_winner: str
    decision_reason: str
    exit_wait_state: str


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _tail(rows: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    if size <= 0 or len(rows) <= size:
        return rows
    return rows[-size:]


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_symbol(value: Any) -> str:
    return _coerce_text(value).upper()


def _normalize_side(value: Any) -> str:
    text = _coerce_text(value).upper()
    if text in {"BUY", "SELL"}:
        return text
    if text in {"NONE", "WAIT", "BLOCKED", "OBSERVE"}:
        return "NONE"
    return text or "UNKNOWN"


def _coerce_float(value: Any) -> float | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = _coerce_text(value)
        if text:
            return text
    return ""


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _top_label(counter: Counter[str]) -> str:
    for label, _count in counter.most_common():
        if label:
            return label
    return ""


def _top_count(counter: Counter[str]) -> int:
    if not counter:
        return 0
    return counter.most_common(1)[0][1]


def _after_since(row: dict[str, Any], since_dt: datetime | None) -> bool:
    if since_dt is None:
        return True
    for key in ("time", "timestamp", "created_at", "open_time", "close_time"):
        dt_value = _parse_dt(row.get(key))
        if dt_value is not None:
            return dt_value >= since_dt
    for key in ("signal_bar_ts", "open_ts", "close_ts"):
        timestamp_value = _coerce_float(row.get(key))
        if timestamp_value is not None:
            try:
                return datetime.fromtimestamp(timestamp_value) >= since_dt
            except Exception:
                continue
    return False


def _resolve_decision_trace(row: dict[str, Any]) -> dict[str, Any]:
    trace_text = _coerce_text(row.get("p0_decision_trace_v1"))
    if trace_text:
        try:
            trace = json.loads(trace_text)
            if isinstance(trace, dict):
                return trace
        except Exception:
            pass
    return build_p0_decision_trace_v1(row)


def _resolve_decision_setup_key(row: dict[str, Any]) -> str:
    return _first_nonempty(
        row.get("setup_id"),
        row.get("consumer_setup_id"),
        row.get("consumer_archetype_id"),
        row.get("observe_reason"),
        "unknown",
    )


def _resolve_decision_regime_key(row: dict[str, Any]) -> str:
    return _first_nonempty(
        row.get("preflight_regime"),
        row.get("market_mode"),
        row.get("box_state"),
        "unknown",
    )


def _resolve_decision_side_key(row: dict[str, Any]) -> str:
    direct = _normalize_side(
        _first_nonempty(
            row.get("setup_side"),
            row.get("consumer_check_side"),
            row.get("observe_side"),
            row.get("action"),
            row.get("consumer_effective_action"),
        )
    )
    if direct not in {"UNKNOWN", "NONE"}:
        return direct
    setup_hint = _first_nonempty(
        row.get("setup_id"),
        row.get("consumer_setup_id"),
        row.get("consumer_archetype_id"),
        row.get("observe_reason"),
    ).lower()
    if setup_hint.endswith("_buy") or "_buy_" in setup_hint or "buy" in setup_hint:
        return "BUY"
    if setup_hint.endswith("_sell") or "_sell_" in setup_hint or "sell" in setup_hint:
        return "SELL"
    return direct


def _resolve_trade_setup_key(row: dict[str, Any]) -> str:
    explicit_setup = _coerce_text(row.get("entry_setup_id"))
    if explicit_setup:
        return explicit_setup
    direction = _coerce_text(row.get("direction")).upper() or "UNKNOWN"
    entry_stage = _coerce_text(row.get("entry_stage")) or "unknown_stage"
    return f"legacy_trade_without_setup_id::{direction}::{entry_stage}"


def _resolve_trade_regime_key(row: dict[str, Any]) -> str:
    return _first_nonempty(
        row.get("regime_at_entry"),
        row.get("policy_scope"),
        "unknown",
    )


def _resolve_trade_side_key(row: dict[str, Any]) -> str:
    return _normalize_side(row.get("direction"))


def _compute_hold_seconds(row: dict[str, Any]) -> float | None:
    open_ts = _coerce_float(row.get("open_ts"))
    close_ts = _coerce_float(row.get("close_ts"))
    if open_ts is not None and close_ts is not None:
        return max(0.0, close_ts - open_ts)
    open_dt = _parse_dt(row.get("open_time"))
    close_dt = _parse_dt(row.get("close_time"))
    if open_dt is not None and close_dt is not None:
        return max(0.0, (close_dt - open_dt).total_seconds())
    return None


def _build_decision_records(
    rows: Iterable[dict[str, Any]],
    *,
    symbol_filter: str,
) -> list[DecisionRecord]:
    records: list[DecisionRecord] = []
    for row in rows:
        symbol = _normalize_symbol(row.get("symbol"))
        if not symbol:
            continue
        if symbol_filter and symbol != symbol_filter:
            continue
        trace = _resolve_decision_trace(row)
        records.append(
            DecisionRecord(
                symbol=symbol,
                setup_key=_resolve_decision_setup_key(row),
                regime_key=_resolve_decision_regime_key(row),
                side_key=_resolve_decision_side_key(row),
                coverage_state=_coerce_text(trace.get("coverage_state")) or "unknown",
                outcome=_coerce_text(row.get("outcome")) or "unknown",
                blocked_by=_coerce_text(row.get("blocked_by")),
                action_none_reason=_coerce_text(row.get("action_none_reason")),
                observe_reason=_coerce_text(row.get("observe_reason")),
                owner_relation=_coerce_text(trace.get("decision_owner_relation")) or "unknown",
                consumer_check_stage=_coerce_text(row.get("consumer_check_stage")) or "unknown",
            )
        )
    return records


def _build_trade_records(
    rows: Iterable[dict[str, Any]],
    *,
    symbol_filter: str,
    status: str,
) -> list[TradeRecord]:
    records: list[TradeRecord] = []
    for row in rows:
        symbol = _normalize_symbol(row.get("symbol"))
        if not symbol:
            continue
        if symbol_filter and symbol != symbol_filter:
            continue
        net_after_cost = _coerce_float(row.get("net_pnl_after_cost"))
        records.append(
            TradeRecord(
                symbol=symbol,
                setup_key=_resolve_trade_setup_key(row),
                regime_key=_resolve_trade_regime_key(row),
                side_key=_resolve_trade_side_key(row),
                status=status,
                direction=_coerce_text(row.get("direction")).upper(),
                profit_value=net_after_cost if net_after_cost is not None else (_coerce_float(row.get("profit")) or 0.0),
                hold_seconds=_compute_hold_seconds(row),
                decision_winner=_coerce_text(row.get("decision_winner")),
                decision_reason=_coerce_text(row.get("decision_reason")),
                exit_wait_state=_coerce_text(row.get("exit_wait_state")),
            )
        )
    return records


def _build_group_summary(
    decision_records: list[DecisionRecord],
    open_trade_records: list[TradeRecord],
    closed_trade_records: list[TradeRecord],
    *,
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}

    def _ensure_group(key: tuple[str, ...]) -> dict[str, Any]:
        if key not in grouped:
            group = {field: value for field, value in zip(key_fields, key)}
            group.update(
                {
                    "decision_rows": 0,
                    "entered_count": 0,
                    "wait_count": 0,
                    "skipped_count": 0,
                    "blocked_count": 0,
                    "in_scope_decision_rows": 0,
                    "outside_coverage_decision_rows": 0,
                    "unknown_coverage_decision_rows": 0,
                    "open_trade_count": 0,
                    "closed_trade_count": 0,
                    "profitable_closed_count": 0,
                    "losing_closed_count": 0,
                    "fast_adverse_close_count": 0,
                    "closed_hold_seconds_total": 0.0,
                    "closed_hold_seconds_count": 0,
                    "_blocked_by": Counter(),
                    "_action_none_reason": Counter(),
                    "_observe_reason": Counter(),
                    "_owner_relation": Counter(),
                    "_decision_winner": Counter(),
                    "_decision_reason": Counter(),
                    "_exit_wait_state": Counter(),
                }
            )
            grouped[key] = group
        return grouped[key]

    for record in decision_records:
        key = tuple(getattr(record, field) for field in key_fields)
        group = _ensure_group(key)
        group["decision_rows"] += 1
        if record.outcome == "entered":
            group["entered_count"] += 1
        elif record.outcome == "wait":
            group["wait_count"] += 1
        elif record.outcome == "skipped":
            group["skipped_count"] += 1
        if record.blocked_by or record.consumer_check_stage == "BLOCKED":
            group["blocked_count"] += 1
        if record.coverage_state == "in_scope_runtime":
            group["in_scope_decision_rows"] += 1
        elif record.coverage_state == "outside_coverage":
            group["outside_coverage_decision_rows"] += 1
        else:
            group["unknown_coverage_decision_rows"] += 1
        if record.blocked_by:
            group["_blocked_by"][record.blocked_by] += 1
        if record.action_none_reason:
            group["_action_none_reason"][record.action_none_reason] += 1
        if record.observe_reason:
            group["_observe_reason"][record.observe_reason] += 1
        if record.owner_relation:
            group["_owner_relation"][record.owner_relation] += 1

    for record in open_trade_records:
        key = tuple(getattr(record, field) for field in key_fields)
        group = _ensure_group(key)
        group["open_trade_count"] += 1

    for record in closed_trade_records:
        key = tuple(getattr(record, field) for field in key_fields)
        group = _ensure_group(key)
        group["closed_trade_count"] += 1
        if record.profit_value > 0:
            group["profitable_closed_count"] += 1
        elif record.profit_value < 0:
            group["losing_closed_count"] += 1
            if record.hold_seconds is not None and record.hold_seconds <= 180.0:
                group["fast_adverse_close_count"] += 1
        if record.hold_seconds is not None:
            group["closed_hold_seconds_total"] += record.hold_seconds
            group["closed_hold_seconds_count"] += 1
        if record.decision_winner:
            group["_decision_winner"][record.decision_winner] += 1
        if record.decision_reason:
            group["_decision_reason"][record.decision_reason] += 1
        if record.exit_wait_state:
            group["_exit_wait_state"][record.exit_wait_state] += 1

    rows: list[dict[str, Any]] = []
    for key, group in grouped.items():
        decision_rows = int(group["decision_rows"])
        closed_trade_count = int(group["closed_trade_count"])
        losing_closed_count = int(group["losing_closed_count"])
        row = {field: value for field, value in zip(key_fields, key)}
        row.update(
            {
                "decision_rows": decision_rows,
                "entered_count": int(group["entered_count"]),
                "wait_count": int(group["wait_count"]),
                "skipped_count": int(group["skipped_count"]),
                "blocked_count": int(group["blocked_count"]),
                "in_scope_decision_rows": int(group["in_scope_decision_rows"]),
                "outside_coverage_decision_rows": int(group["outside_coverage_decision_rows"]),
                "unknown_coverage_decision_rows": int(group["unknown_coverage_decision_rows"]),
                "wait_ratio": _safe_ratio(group["wait_count"], decision_rows),
                "skip_ratio": _safe_ratio(group["skipped_count"], decision_rows),
                "outside_coverage_ratio": _safe_ratio(group["outside_coverage_decision_rows"], decision_rows),
                "open_trade_count": int(group["open_trade_count"]),
                "closed_trade_count": closed_trade_count,
                "profitable_closed_count": int(group["profitable_closed_count"]),
                "losing_closed_count": losing_closed_count,
                "fast_adverse_close_count": int(group["fast_adverse_close_count"]),
                "fast_adverse_close_ratio": _safe_ratio(group["fast_adverse_close_count"], losing_closed_count),
                "avg_closed_hold_seconds": round(
                    group["closed_hold_seconds_total"] / group["closed_hold_seconds_count"], 2
                ) if group["closed_hold_seconds_count"] else 0.0,
                "top_blocked_by": _top_label(group["_blocked_by"]),
                "top_action_none_reason": _top_label(group["_action_none_reason"]),
                "top_observe_reason": _top_label(group["_observe_reason"]),
                "top_owner_relation": _top_label(group["_owner_relation"]),
                "top_decision_winner": _top_label(group["_decision_winner"]),
                "top_decision_reason": _top_label(group["_decision_reason"]),
                "top_exit_wait_state": _top_label(group["_exit_wait_state"]),
                "top_blocked_by_count": _top_count(group["_blocked_by"]),
                "top_decision_winner_count": _top_count(group["_decision_winner"]),
                "top_decision_winner_ratio": _safe_ratio(_top_count(group["_decision_winner"]), closed_trade_count),
                "forced_exit_winner_count": int(group["_decision_winner"].get("cut_now", 0) + group["_decision_winner"].get("exit_now", 0)),
                "reverse_winner_count": int(group["_decision_winner"].get("reverse_now", 0) + group["_decision_winner"].get("reverse", 0)),
            }
        )
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            -int(row.get("decision_rows", 0)),
            -int(row.get("closed_trade_count", 0)),
            *(row.get(name, "") for name in key_fields),
        ),
    )


def _build_suspicious_clusters(family_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    for row in family_summary:
        family_root = " / ".join(
            value for value in [row.get("symbol", ""), row.get("setup_key", ""), row.get("regime_key", "")] if value
        )
        family_key = " / ".join(
            value for value in [row.get("symbol", ""), row.get("setup_key", ""), row.get("regime_key", ""), row.get("side_key", "")]
            if value
        )
        if row["outside_coverage_decision_rows"] >= 3 and row["outside_coverage_ratio"] >= 0.5:
            clusters.append(
                {
                    "cluster_type": "coverage_blind_spot_cluster",
                    "severity": "high",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["outside_coverage_decision_rows"],
                    "score": row["outside_coverage_decision_rows"] * (1.0 + row["outside_coverage_ratio"]),
                    "reason": "decision lifecycle for this family is still materially outside active decision coverage",
                }
            )
        if row["decision_rows"] >= 5 and row["skip_ratio"] >= 0.7:
            clusters.append(
                {
                    "cluster_type": "skip_heavy_cluster",
                    "severity": "medium",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["skipped_count"],
                    "score": row["skipped_count"] * (1.0 + row["skip_ratio"]),
                    "reason": "decision flow is heavily skipping or blocking instead of opening",
                }
            )
        if row["decision_rows"] >= 5 and _safe_ratio(row["blocked_count"], row["decision_rows"]) >= 0.7 and row["top_blocked_by"]:
            clusters.append(
                {
                    "cluster_type": "blocked_pressure_cluster",
                    "severity": "medium",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["blocked_count"],
                    "score": row["blocked_count"] * _safe_ratio(row["blocked_count"], row["decision_rows"]),
                    "reason": f"blocked lifecycle is concentrated around `{row['top_blocked_by']}`",
                }
            )
        if row["decision_rows"] >= 5 and row["wait_ratio"] >= 0.7:
            clusters.append(
                {
                    "cluster_type": "wait_heavy_cluster",
                    "severity": "medium",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["wait_count"],
                    "score": row["wait_count"] * (1.0 + row["wait_ratio"]),
                    "reason": "decision flow is dominated by wait outcomes",
                }
            )
        if row["wait_count"] >= 3 and row["closed_trade_count"] >= 2 and row["forced_exit_winner_count"] >= 2:
            clusters.append(
                {
                    "cluster_type": "wait_to_forced_exit_cluster",
                    "severity": "high",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["wait_count"],
                    "score": row["wait_count"] + row["forced_exit_winner_count"],
                    "reason": "wait-heavy decision flow is closing mostly through forced exit families",
                }
            )
        if row["closed_trade_count"] >= 2 and row["fast_adverse_close_ratio"] >= 0.5:
            clusters.append(
                {
                    "cluster_type": "fast_adverse_close_cluster",
                    "severity": "high",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["fast_adverse_close_count"],
                    "score": row["fast_adverse_close_count"] * (1.0 + row["fast_adverse_close_ratio"]),
                    "reason": "closed trades are quickly turning into losses after entry",
                }
            )
        if row["closed_trade_count"] >= 3 and row["top_decision_winner"] == "cut_now" and row["top_decision_winner_ratio"] >= 0.5:
            clusters.append(
                {
                    "cluster_type": "cut_now_concentration_cluster",
                    "severity": "medium",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["top_decision_winner_count"],
                    "score": row["top_decision_winner_count"] * row["top_decision_winner_ratio"],
                    "reason": "exit lifecycle is concentrated around cut_now decisions",
                }
            )
        if row["closed_trade_count"] >= 2 and row["reverse_winner_count"] >= 1:
            clusters.append(
                {
                    "cluster_type": "reverse_now_cluster",
                    "severity": "medium",
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "side_key": row.get("side_key", ""),
                    "family_root_key": family_root,
                    "family_key": family_key,
                    "count": row["reverse_winner_count"],
                    "score": row["reverse_winner_count"] * max(0.34, _safe_ratio(row["reverse_winner_count"], row["closed_trade_count"])),
                    "reason": "exit lifecycle is repeatedly flipping into reverse decisions",
                }
            )
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        clusters,
        key=lambda item: (
            severity_order.get(item["severity"], 9),
            -float(item.get("score", item["count"])),
            -int(item["count"]),
            item["family_key"],
        ),
    )


def _build_strengths(family_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strengths: list[dict[str, Any]] = []
    for row in family_summary:
        family_key = " / ".join(value for value in [row.get("symbol", ""), row.get("setup_key", ""), row.get("regime_key", ""), row.get("side_key", "")] if value)
        if row["closed_trade_count"] >= 3 and row["profitable_closed_count"] > row["losing_closed_count"]:
            strengths.append(
                {
                    "family_key": family_key,
                    "reason": "profitable closed trades are outweighing losing closed trades",
                    "score": row["profitable_closed_count"] - row["losing_closed_count"],
                }
            )
        elif row["decision_rows"] >= 5 and row["in_scope_decision_rows"] >= row["outside_coverage_decision_rows"]:
            strengths.append(
                {
                    "family_key": family_key,
                    "reason": "decision lifecycle is mostly inside active coverage",
                    "score": row["in_scope_decision_rows"],
                }
            )
    return sorted(strengths, key=lambda item: (-item["score"], item["family_key"]))[:5]


def _build_cluster_type_summary(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        key = cluster["cluster_type"]
        bucket = grouped.setdefault(key, {"cluster_type": key, "count": 0, "high_severity_count": 0, "top_family_key": "", "top_score": -1.0})
        bucket["count"] += 1
        if cluster["severity"] == "high":
            bucket["high_severity_count"] += 1
        score = float(cluster.get("score", cluster.get("count", 0)))
        if score > bucket["top_score"]:
            bucket["top_score"] = score
            bucket["top_family_key"] = cluster["family_key"]
    rows = list(grouped.values())
    for row in rows:
        row.pop("top_score", None)
    return sorted(rows, key=lambda item: (-item["high_severity_count"], -item["count"], item["cluster_type"]))


def _pick_review_queue(clusters: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_roots: set[tuple[str, str, str]] = set()
    for cluster in clusters:
        dedupe_key = (
            cluster["cluster_type"],
            cluster.get("symbol", ""),
            cluster.get("setup_key", ""),
        )
        if dedupe_key in seen_roots:
            continue
        selected.append(cluster)
        seen_roots.add(dedupe_key)
        if len(selected) >= limit:
            break
    return selected


def _to_family_csv_rows(family_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "symbol",
        "setup_key",
        "regime_key",
        "decision_rows",
        "entered_count",
        "wait_count",
        "skipped_count",
        "blocked_count",
        "in_scope_decision_rows",
        "outside_coverage_decision_rows",
        "unknown_coverage_decision_rows",
        "wait_ratio",
        "skip_ratio",
        "outside_coverage_ratio",
        "open_trade_count",
        "closed_trade_count",
        "profitable_closed_count",
        "losing_closed_count",
        "fast_adverse_close_count",
        "fast_adverse_close_ratio",
        "avg_closed_hold_seconds",
        "top_blocked_by",
        "top_action_none_reason",
        "top_observe_reason",
        "top_owner_relation",
        "top_decision_winner",
        "top_decision_reason",
        "top_exit_wait_state",
        "side_key",
    ]
    return [{key: row.get(key, "") for key in keys} for row in family_summary]


def build_profitability_operations_p1_lifecycle_correlation_report(
    *,
    decisions_path: Path = DEFAULT_DECISIONS_PATH,
    decision_detail_path: Path = DEFAULT_DECISION_DETAIL_PATH,
    open_trades_path: Path = DEFAULT_OPEN_TRADES_PATH,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    since_dt = _parse_dt(since)
    symbol_filter = _normalize_symbol(symbol_filter)

    decision_rows = _tail(_read_csv(decisions_path), tail)
    open_trade_rows = _read_csv(open_trades_path)
    closed_trade_rows = _tail(_read_csv(closed_trades_path), tail)

    decision_rows = [row for row in decision_rows if _after_since(row, since_dt)]
    open_trade_rows = [row for row in open_trade_rows if _after_since(row, since_dt)]
    closed_trade_rows = [row for row in closed_trade_rows if _after_since(row, since_dt)]

    decision_records = _build_decision_records(decision_rows, symbol_filter=symbol_filter)
    open_trade_records = _build_trade_records(open_trade_rows, symbol_filter=symbol_filter, status="OPEN")
    closed_trade_records = _build_trade_records(closed_trade_rows, symbol_filter=symbol_filter, status="CLOSED")

    family_summary = _build_group_summary(
        decision_records,
        open_trade_records,
        closed_trade_records,
        key_fields=("symbol", "setup_key", "regime_key", "side_key"),
    )
    symbol_summary = _build_group_summary(decision_records, open_trade_records, closed_trade_records, key_fields=("symbol",))
    setup_summary = _build_group_summary(decision_records, open_trade_records, closed_trade_records, key_fields=("setup_key",))
    regime_summary = _build_group_summary(decision_records, open_trade_records, closed_trade_records, key_fields=("regime_key",))
    side_summary = _build_group_summary(decision_records, open_trade_records, closed_trade_records, key_fields=("side_key",))
    symbol_setup_summary = _build_group_summary(
        decision_records,
        open_trade_records,
        closed_trade_records,
        key_fields=("symbol", "setup_key"),
    )
    symbol_regime_summary = _build_group_summary(
        decision_records,
        open_trade_records,
        closed_trade_records,
        key_fields=("symbol", "regime_key"),
    )

    coverage_counter = Counter(record.coverage_state for record in decision_records)
    suspicious_clusters = _build_suspicious_clusters(family_summary)
    cluster_type_summary = _build_cluster_type_summary(suspicious_clusters)
    strengths = _build_strengths(family_summary)
    review_queue = _pick_review_queue(suspicious_clusters, limit=3)

    overall_summary = {
        "decision_rows": len(decision_records),
        "open_trade_rows": len(open_trade_records),
        "closed_trade_rows": len(closed_trade_records),
        "entered_count": sum(record.outcome == "entered" for record in decision_records),
        "wait_count": sum(record.outcome == "wait" for record in decision_records),
        "skipped_count": sum(record.outcome == "skipped" for record in decision_records),
        "blocked_count": sum(bool(record.blocked_by) or record.consumer_check_stage == "BLOCKED" for record in decision_records),
        "profitable_closed_count": sum(record.profit_value > 0 for record in closed_trade_records),
        "losing_closed_count": sum(record.profit_value < 0 for record in closed_trade_records),
        "fast_adverse_close_count": sum(record.profit_value < 0 and record.hold_seconds is not None and record.hold_seconds <= 180.0 for record in closed_trade_records),
    }
    coverage_summary = {
        "coverage_in_scope": coverage_counter.get("in_scope_runtime", 0),
        "outside_coverage": coverage_counter.get("outside_coverage", 0),
        "unknown_coverage": coverage_counter.get("unknown", 0),
        "outside_coverage_ratio": _safe_ratio(coverage_counter.get("outside_coverage", 0), len(decision_records)),
    }
    quick_read_summary = {
        "top_concerns": [f"{cluster['family_key']} | {cluster['cluster_type']} | {cluster['reason']}" for cluster in review_queue],
        "top_strengths": [f"{strength['family_key']} | {strength['reason']}" for strength in strengths[:3]],
        "next_review_queue": [cluster["family_key"] for cluster in review_queue],
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "tail": tail,
            "since": _coerce_text(since),
            "symbol_filter": symbol_filter,
            "decisions_path": str(decisions_path),
            "decision_detail_path": str(decision_detail_path),
            "decision_detail_available": decision_detail_path.exists(),
            "open_trades_path": str(open_trades_path),
            "closed_trades_path": str(closed_trades_path),
            "coverage_split_rule": "decision rows are separated by p0 coverage state before lifecycle interpretation",
        },
        "overall_summary": overall_summary,
        "coverage_summary": coverage_summary,
        "symbol_summary": symbol_summary,
        "setup_summary": setup_summary,
        "regime_summary": regime_summary,
        "side_summary": side_summary,
        "symbol_setup_summary": symbol_setup_summary,
        "symbol_regime_summary": symbol_regime_summary,
        "lifecycle_family_summary": family_summary,
        "suspicious_clusters": suspicious_clusters,
        "suspicious_cluster_type_summary": cluster_type_summary,
        "quick_read_summary": quick_read_summary,
    }


def write_profitability_operations_p1_lifecycle_correlation_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    decisions_path: Path = DEFAULT_DECISIONS_PATH,
    decision_detail_path: Path = DEFAULT_DECISION_DETAIL_PATH,
    open_trades_path: Path = DEFAULT_OPEN_TRADES_PATH,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p1_lifecycle_correlation_report(
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        tail=tail,
        since=since,
        symbol_filter=symbol_filter,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p1_lifecycle_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p1_lifecycle_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p1_lifecycle_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = _to_family_csv_rows(report["lifecycle_family_summary"])
    fieldnames = list(csv_rows[0].keys()) if csv_rows else list(_to_family_csv_rows([{}])[0].keys())
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    markdown_lines = [
        "# Profitability / Operations P1 Lifecycle Correlation",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `decision_rows`: `{report['overall_summary']['decision_rows']}`",
        f"- `closed_trade_rows`: `{report['overall_summary']['closed_trade_rows']}`",
        f"- `coverage_in_scope`: `{report['coverage_summary']['coverage_in_scope']}`",
        f"- `outside_coverage`: `{report['coverage_summary']['outside_coverage']}`",
        "",
        "## Top Concerns",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_concerns"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Strengths"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_strengths"] or ["(none)"])])
    markdown_lines.extend(["", "## Next Review Queue"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["next_review_queue"] or ["(none)"])])
    markdown_lines.extend(["", "## Suspicious Clusters"])
    if report["suspicious_clusters"]:
        for cluster in report["suspicious_clusters"][:10]:
            markdown_lines.append(f"- `{cluster['cluster_type']}` | `{cluster['severity']}` | {cluster['family_key']} | {cluster['reason']}")
    else:
        markdown_lines.append("- (none)")
    markdown_lines.extend(["", "## Cluster Type Summary"])
    if report["suspicious_cluster_type_summary"]:
        for row in report["suspicious_cluster_type_summary"][:10]:
            markdown_lines.append(
                f"- `{row['cluster_type']}` | count={row['count']} | high={row['high_severity_count']} | top={row['top_family_key']}"
            )
    else:
        markdown_lines.append("- (none)")
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "family_row_count": len(csv_rows),
        "suspicious_cluster_count": len(report["suspicious_clusters"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tail", type=int, default=5000)
    parser.add_argument("--since", type=str, default="")
    parser.add_argument("--symbol", type=str, default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p1_lifecycle_correlation_report(
        output_dir=args.output_dir,
        tail=args.tail,
        since=args.since,
        symbol_filter=args.symbol,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
