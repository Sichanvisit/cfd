from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p2_expectancy_attribution_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_CLOSED_TRADES_PATH = ROOT / "data" / "trades" / "trade_closed_history.csv"


@dataclass
class ClosedTradeRecord:
    symbol: str
    direction: str
    setup_bucket: str
    setup_key: str
    regime_key: str
    entry_stage: str
    exit_policy_stage: str
    exit_policy_profile: str
    decision_winner: str
    decision_reason: str
    exit_wait_state: str
    pnl: float
    hold_seconds: float | None


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


def _after_since(row: dict[str, Any], since_dt: datetime | None) -> bool:
    if since_dt is None:
        return True
    for key in ("close_time", "open_time"):
        dt_value = _parse_dt(row.get(key))
        if dt_value is not None:
            return dt_value >= since_dt
    for key in ("close_ts", "open_ts"):
        numeric = _coerce_float(row.get(key))
        if numeric is not None:
            try:
                return datetime.fromtimestamp(numeric) >= since_dt
            except Exception:
                continue
    return False


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _safe_div(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator, 4)


def _top_label(counter: Counter[str]) -> str:
    for label, _count in counter.most_common():
        if label:
            return label
    return ""


def _resolve_setup_bucket(row: dict[str, Any]) -> str:
    setup_id = _coerce_text(row.get("entry_setup_id"))
    if setup_id == "snapshot_restored_auto":
        return "snapshot_restored_auto"
    if setup_id:
        return "explicit_setup"
    return "legacy_without_setup"


def _resolve_setup_key(row: dict[str, Any]) -> str:
    setup_id = _coerce_text(row.get("entry_setup_id"))
    if setup_id:
        return setup_id
    direction = _normalize_side(row.get("direction"))
    entry_stage = _coerce_text(row.get("entry_stage")) or "unknown_stage"
    return f"legacy_trade_without_setup_id::{direction}::{entry_stage}"


def _resolve_regime_key(row: dict[str, Any]) -> str:
    return _coerce_text(row.get("regime_at_entry")) or "UNKNOWN_REGIME"


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


def _resolve_pnl(row: dict[str, Any]) -> float:
    net_after_cost = _coerce_float(row.get("net_pnl_after_cost"))
    if net_after_cost is not None:
        return net_after_cost
    return _coerce_float(row.get("profit")) or 0.0


def _build_closed_trade_records(
    rows: Iterable[dict[str, Any]],
    *,
    symbol_filter: str,
) -> list[ClosedTradeRecord]:
    records: list[ClosedTradeRecord] = []
    for row in rows:
        symbol = _normalize_symbol(row.get("symbol"))
        if not symbol:
            continue
        if symbol_filter and symbol != symbol_filter:
            continue
        records.append(
            ClosedTradeRecord(
                symbol=symbol,
                direction=_normalize_side(row.get("direction")),
                setup_bucket=_resolve_setup_bucket(row),
                setup_key=_resolve_setup_key(row),
                regime_key=_resolve_regime_key(row),
                entry_stage=_coerce_text(row.get("entry_stage")) or "unknown",
                exit_policy_stage=_coerce_text(row.get("exit_policy_stage")) or "unknown",
                exit_policy_profile=_coerce_text(row.get("exit_policy_profile")) or "unknown",
                decision_winner=_coerce_text(row.get("decision_winner")),
                decision_reason=_coerce_text(row.get("decision_reason")),
                exit_wait_state=_coerce_text(row.get("exit_wait_state")),
                pnl=_resolve_pnl(row),
                hold_seconds=_compute_hold_seconds(row),
            )
        )
    return records


def _build_group_summary(records: list[ClosedTradeRecord], *, key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}

    def _ensure_group(key: tuple[str, ...]) -> dict[str, Any]:
        if key not in grouped:
            group = {field: value for field, value in zip(key_fields, key)}
            group.update(
                {
                    "closed_trade_count": 0,
                    "attribution_ready_count": 0,
                    "nonzero_pnl_count": 0,
                    "net_pnl_sum": 0.0,
                    "win_count": 0,
                    "loss_count": 0,
                    "flat_count": 0,
                    "gross_profit_sum": 0.0,
                    "gross_loss_abs_sum": 0.0,
                    "hold_seconds_total": 0.0,
                    "hold_seconds_count": 0,
                    "forced_exit_count": 0,
                    "reverse_count": 0,
                    "recovery_count": 0,
                    "_decision_winner": Counter(),
                    "_decision_reason": Counter(),
                    "_exit_wait_state": Counter(),
                }
            )
            grouped[key] = group
        return grouped[key]

    for record in records:
        key = tuple(getattr(record, field) for field in key_fields)
        group = _ensure_group(key)
        group["closed_trade_count"] += 1
        group["net_pnl_sum"] += record.pnl
        if record.pnl != 0:
            group["nonzero_pnl_count"] += 1
        if record.pnl > 0:
            group["win_count"] += 1
            group["gross_profit_sum"] += record.pnl
        elif record.pnl < 0:
            group["loss_count"] += 1
            group["gross_loss_abs_sum"] += abs(record.pnl)
        else:
            group["flat_count"] += 1
        if record.hold_seconds is not None:
            group["hold_seconds_total"] += record.hold_seconds
            group["hold_seconds_count"] += 1
        if record.decision_winner:
            group["_decision_winner"][record.decision_winner] += 1
        if record.decision_reason:
            group["_decision_reason"][record.decision_reason] += 1
        if record.exit_wait_state:
            group["_exit_wait_state"][record.exit_wait_state] += 1
        if record.decision_winner or record.decision_reason or record.exit_wait_state:
            group["attribution_ready_count"] += 1
        if record.decision_winner in {"cut_now", "exit_now"}:
            group["forced_exit_count"] += 1
        if record.decision_winner in {"reverse_now", "reverse"}:
            group["reverse_count"] += 1
        if record.decision_winner in {"wait_be", "wait_exit", "wait_tp1"}:
            group["recovery_count"] += 1

    rows: list[dict[str, Any]] = []
    for key, group in grouped.items():
        count = int(group["closed_trade_count"])
        win_count = int(group["win_count"])
        loss_count = int(group["loss_count"])
        gross_profit_sum = float(group["gross_profit_sum"])
        gross_loss_abs_sum = float(group["gross_loss_abs_sum"])
        avg_win = _safe_div(gross_profit_sum, win_count) if win_count else 0.0
        avg_loss = _safe_div(-gross_loss_abs_sum, loss_count) if loss_count else 0.0
        row = {field: value for field, value in zip(key_fields, key)}
        row.update(
            {
                "closed_trade_count": count,
                "attribution_ready_count": int(group["attribution_ready_count"]),
                "attribution_ready_ratio": _safe_ratio(group["attribution_ready_count"], count),
                "nonzero_pnl_count": int(group["nonzero_pnl_count"]),
                "nonzero_pnl_ratio": _safe_ratio(group["nonzero_pnl_count"], count),
                "net_pnl_sum": round(float(group["net_pnl_sum"]), 4),
                "avg_pnl": _safe_div(float(group["net_pnl_sum"]), count),
                "win_count": win_count,
                "loss_count": loss_count,
                "flat_count": int(group["flat_count"]),
                "win_rate": _safe_ratio(win_count, count),
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": _safe_div(gross_profit_sum, gross_loss_abs_sum) if gross_loss_abs_sum else 0.0,
                "avg_hold_seconds": _safe_div(float(group["hold_seconds_total"]), float(group["hold_seconds_count"])) if group["hold_seconds_count"] else 0.0,
                "forced_exit_count": int(group["forced_exit_count"]),
                "forced_exit_ratio": _safe_ratio(group["forced_exit_count"], count),
                "reverse_count": int(group["reverse_count"]),
                "reverse_ratio": _safe_ratio(group["reverse_count"], count),
                "recovery_count": int(group["recovery_count"]),
                "recovery_ratio": _safe_ratio(group["recovery_count"], count),
                "top_decision_winner": _top_label(group["_decision_winner"]),
                "top_decision_reason": _top_label(group["_decision_reason"]),
                "top_exit_wait_state": _top_label(group["_exit_wait_state"]),
            }
        )
        rows.append(row)

    return sorted(
        rows,
        key=lambda row: (-int(row["closed_trade_count"]), float(row["avg_pnl"]), *(row.get(field, "") for field in key_fields)),
    )


def _build_negative_expectancy_clusters(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    for row in summary_rows:
        count = int(row["closed_trade_count"])
        avg_pnl = float(row["avg_pnl"])
        nonzero_pnl_count = int(row["nonzero_pnl_count"])
        nonzero_pnl_ratio = float(row["nonzero_pnl_ratio"])
        if count >= 20 and nonzero_pnl_count == 0:
            clusters.append(
                {
                    "cluster_type": "zero_pnl_information_gap_cluster",
                    "severity": "medium",
                    "setup_bucket": row.get("setup_bucket", ""),
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "count": count,
                    "score": float(count),
                    "reason": "closed trades are present but pnl is zero across the whole bucket, so expectancy is not economically readable yet",
                }
            )
        if count >= 5 and nonzero_pnl_count >= 5 and nonzero_pnl_ratio >= 0.2 and avg_pnl < 0:
            clusters.append(
                {
                    "cluster_type": "negative_expectancy_cluster",
                    "severity": "high" if avg_pnl <= -1.0 else "medium",
                    "setup_bucket": row.get("setup_bucket", ""),
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "count": count,
                    "score": abs(avg_pnl) * count,
                    "reason": "average pnl is negative across a meaningful number of closed trades",
                }
            )
        if count >= 5 and nonzero_pnl_count >= 5 and nonzero_pnl_ratio >= 0.2 and avg_pnl < 0 and float(row["forced_exit_ratio"]) >= 0.5:
            clusters.append(
                {
                    "cluster_type": "forced_exit_drag_cluster",
                    "severity": "high",
                    "setup_bucket": row.get("setup_bucket", ""),
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "count": int(row["forced_exit_count"]),
                    "score": abs(avg_pnl) * max(1, int(row["forced_exit_count"])),
                    "reason": "negative expectancy is concentrated around forced exit winners",
                }
            )
        if count >= 5 and nonzero_pnl_count >= 5 and nonzero_pnl_ratio >= 0.2 and avg_pnl < 0 and float(row["reverse_ratio"]) >= 0.1:
            clusters.append(
                {
                    "cluster_type": "reverse_drag_cluster",
                    "severity": "medium",
                    "setup_bucket": row.get("setup_bucket", ""),
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "count": int(row["reverse_count"]),
                    "score": abs(avg_pnl) * max(1, int(row["reverse_count"])),
                    "reason": "negative expectancy is repeatedly paired with reverse decisions",
                }
            )
        if row.get("setup_bucket") == "legacy_without_setup" and count >= 5 and nonzero_pnl_count >= 5 and nonzero_pnl_ratio >= 0.2 and avg_pnl < 0:
            clusters.append(
                {
                    "cluster_type": "legacy_bucket_blind_cluster",
                    "severity": "medium",
                    "setup_bucket": row.get("setup_bucket", ""),
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "count": count,
                    "score": abs(avg_pnl) * count,
                    "reason": "negative expectancy is visible in a legacy bucket without explicit setup identity",
                }
            )
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        clusters,
        key=lambda item: (
            severity_order.get(item["severity"], 9),
            -float(item["score"]),
            -int(item["count"]),
            item["symbol"],
            item["setup_key"],
        ),
    )


def _build_positive_strengths(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strengths: list[dict[str, Any]] = []
    for row in summary_rows:
        if int(row["closed_trade_count"]) >= 5 and int(row["nonzero_pnl_count"]) >= 5 and float(row["nonzero_pnl_ratio"]) >= 0.2 and float(row["avg_pnl"]) > 0:
            strengths.append(
                {
                    "symbol": row.get("symbol", ""),
                    "setup_key": row.get("setup_key", ""),
                    "regime_key": row.get("regime_key", ""),
                    "setup_bucket": row.get("setup_bucket", ""),
                    "score": float(row["avg_pnl"]) * int(row["closed_trade_count"]),
                    "reason": "positive expectancy across repeated closed trades",
                }
            )
    return sorted(strengths, key=lambda item: (-item["score"], item["symbol"], item["setup_key"]))[:5]


def _build_cluster_type_summary(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        key = cluster["cluster_type"]
        bucket = grouped.setdefault(
            key,
            {
                "cluster_type": key,
                "count": 0,
                "high_severity_count": 0,
                "top_family_key": "",
                "top_score": -1.0,
            },
        )
        bucket["count"] += 1
        if cluster["severity"] == "high":
            bucket["high_severity_count"] += 1
        score = float(cluster.get("score", cluster.get("count", 0)))
        if score > bucket["top_score"]:
            bucket["top_score"] = score
            bucket["top_family_key"] = f"{cluster.get('symbol', '')} / {cluster.get('setup_key', '')} / {cluster.get('regime_key', '')}"
    rows = list(grouped.values())
    for row in rows:
        row.pop("top_score", None)
    return sorted(rows, key=lambda item: (-item["high_severity_count"], -item["count"], item["cluster_type"]))


def _pick_review_queue(clusters: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for cluster in clusters:
        key = (cluster.get("symbol", ""), cluster.get("setup_key", ""), cluster.get("regime_key", ""))
        if key in seen:
            continue
        selected.append(cluster)
        seen.add(key)
        if len(selected) >= limit:
            break
    return selected


def _build_attribution_readiness_summary(records: list[ClosedTradeRecord]) -> dict[str, Any]:
    total = len(records)
    explicit_setup_rows = sum(record.setup_bucket == "explicit_setup" for record in records)
    legacy_rows = sum(record.setup_bucket == "legacy_without_setup" for record in records)
    snapshot_rows = sum(record.setup_bucket == "snapshot_restored_auto" for record in records)
    decision_winner_ready = sum(bool(record.decision_winner) for record in records)
    decision_reason_ready = sum(bool(record.decision_reason) for record in records)
    exit_wait_state_ready = sum(bool(record.exit_wait_state) for record in records)
    fully_attributed = sum(bool(record.decision_winner and record.decision_reason and record.exit_wait_state) for record in records)
    nonzero_pnl_rows = sum(record.pnl != 0 for record in records)
    return {
        "closed_trade_rows": total,
        "explicit_setup_rows": explicit_setup_rows,
        "legacy_without_setup_rows": legacy_rows,
        "snapshot_restored_auto_rows": snapshot_rows,
        "decision_winner_ready_rows": decision_winner_ready,
        "decision_reason_ready_rows": decision_reason_ready,
        "exit_wait_state_ready_rows": exit_wait_state_ready,
        "fully_attributed_rows": fully_attributed,
        "fully_attributed_ratio": _safe_ratio(fully_attributed, total),
        "nonzero_pnl_rows": nonzero_pnl_rows,
        "nonzero_pnl_ratio": _safe_ratio(nonzero_pnl_rows, total),
    }


def _to_summary_csv_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "setup_bucket",
        "symbol",
        "setup_key",
        "regime_key",
        "closed_trade_count",
        "attribution_ready_count",
        "attribution_ready_ratio",
        "nonzero_pnl_count",
        "nonzero_pnl_ratio",
        "net_pnl_sum",
        "avg_pnl",
        "win_count",
        "loss_count",
        "flat_count",
        "win_rate",
        "avg_win",
        "avg_loss",
        "profit_factor",
        "avg_hold_seconds",
        "forced_exit_count",
        "forced_exit_ratio",
        "reverse_count",
        "reverse_ratio",
        "recovery_count",
        "recovery_ratio",
        "top_decision_winner",
        "top_decision_reason",
        "top_exit_wait_state",
    ]
    return [{key: row.get(key, "") for key in keys} for row in summary_rows]


def build_profitability_operations_p2_expectancy_attribution_report(
    *,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    since_dt = _parse_dt(since)
    symbol_filter = _normalize_symbol(symbol_filter)

    rows = _tail(_read_csv(closed_trades_path), tail)
    rows = [row for row in rows if _after_since(row, since_dt)]
    records = _build_closed_trade_records(rows, symbol_filter=symbol_filter)

    overall_summary = _build_group_summary(records, key_fields=tuple())[0] if records else {
        "closed_trade_count": 0,
        "attribution_ready_count": 0,
        "attribution_ready_ratio": 0.0,
        "nonzero_pnl_count": 0,
        "nonzero_pnl_ratio": 0.0,
        "net_pnl_sum": 0.0,
        "avg_pnl": 0.0,
        "win_count": 0,
        "loss_count": 0,
        "flat_count": 0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "profit_factor": 0.0,
        "avg_hold_seconds": 0.0,
        "forced_exit_count": 0,
        "forced_exit_ratio": 0.0,
        "reverse_count": 0,
        "reverse_ratio": 0.0,
        "recovery_count": 0,
        "recovery_ratio": 0.0,
        "top_decision_winner": "",
        "top_decision_reason": "",
        "top_exit_wait_state": "",
    }
    readiness_summary = _build_attribution_readiness_summary(records)
    bucket_summary = _build_group_summary(records, key_fields=("setup_bucket",))
    symbol_summary = _build_group_summary(records, key_fields=("symbol",))
    direction_summary = _build_group_summary(records, key_fields=("direction",))
    setup_summary = _build_group_summary(records, key_fields=("setup_bucket", "setup_key"))
    regime_summary = _build_group_summary(records, key_fields=("regime_key",))
    symbol_regime_summary = _build_group_summary(records, key_fields=("symbol", "regime_key"))
    bucket_regime_summary = _build_group_summary(records, key_fields=("setup_bucket", "regime_key"))
    symbol_setup_summary = _build_group_summary(records, key_fields=("symbol", "setup_bucket", "setup_key"))
    setup_regime_summary = _build_group_summary(records, key_fields=("setup_bucket", "setup_key", "regime_key"))
    symbol_setup_regime_summary = _build_group_summary(
        records,
        key_fields=("symbol", "setup_bucket", "setup_key", "regime_key"),
    )
    decision_winner_summary = _build_group_summary(records, key_fields=("decision_winner",))
    decision_reason_summary = _build_group_summary(records, key_fields=("decision_reason",))
    exit_wait_state_summary = _build_group_summary(records, key_fields=("exit_wait_state",))
    entry_stage_summary = _build_group_summary(records, key_fields=("entry_stage",))
    exit_stage_summary = _build_group_summary(records, key_fields=("exit_policy_stage",))
    exit_profile_summary = _build_group_summary(records, key_fields=("exit_policy_profile",))

    negative_clusters = _build_negative_expectancy_clusters(symbol_setup_regime_summary)
    cluster_type_summary = _build_cluster_type_summary(negative_clusters)
    positive_strengths = _build_positive_strengths(symbol_setup_regime_summary)
    review_queue = _pick_review_queue(negative_clusters, limit=3)
    quick_read = {
        "top_negative_concerns": [
            f"{cluster['symbol']} / {cluster['setup_key']} / {cluster['regime_key']} | {cluster['cluster_type']} | {cluster['reason']}"
            for cluster in review_queue
        ],
        "top_positive_strengths": [
            f"{row['symbol']} / {row['setup_key']} / {row['regime_key']} | {row['reason']}"
            for row in positive_strengths[:3]
        ],
        "next_review_queue": [
            f"{cluster['symbol']} / {cluster['setup_key']} / {cluster['regime_key']}"
            for cluster in review_queue
        ],
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "tail": tail,
            "since": _coerce_text(since),
            "symbol_filter": symbol_filter,
            "closed_trades_path": str(closed_trades_path),
            "bucket_rule": "explicit_setup vs legacy_without_setup vs snapshot_restored_auto",
        },
        "overall_expectancy_summary": overall_summary,
        "attribution_readiness_summary": readiness_summary,
        "bucket_expectancy_summary": bucket_summary,
        "symbol_expectancy_summary": symbol_summary,
        "direction_expectancy_summary": direction_summary,
        "setup_expectancy_summary": setup_summary,
        "regime_expectancy_summary": regime_summary,
        "symbol_regime_expectancy_summary": symbol_regime_summary,
        "bucket_regime_expectancy_summary": bucket_regime_summary,
        "symbol_setup_expectancy_summary": symbol_setup_summary,
        "setup_regime_expectancy_summary": setup_regime_summary,
        "symbol_setup_regime_expectancy_summary": symbol_setup_regime_summary,
        "decision_winner_attribution_summary": decision_winner_summary,
        "decision_reason_attribution_summary": decision_reason_summary,
        "exit_wait_state_attribution_summary": exit_wait_state_summary,
        "entry_stage_attribution_summary": entry_stage_summary,
        "exit_stage_attribution_summary": exit_stage_summary,
        "exit_profile_attribution_summary": exit_profile_summary,
        "negative_expectancy_clusters": negative_clusters,
        "negative_expectancy_cluster_type_summary": cluster_type_summary,
        "quick_read_summary": quick_read,
    }


def write_profitability_operations_p2_expectancy_attribution_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p2_expectancy_attribution_report(
        closed_trades_path=closed_trades_path,
        tail=tail,
        since=since,
        symbol_filter=symbol_filter,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p2_expectancy_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p2_expectancy_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p2_expectancy_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = _to_summary_csv_rows(report["setup_regime_expectancy_summary"])
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "setup_bucket",
        "symbol",
        "setup_key",
        "regime_key",
        "closed_trade_count",
        "attribution_ready_count",
        "attribution_ready_ratio",
        "nonzero_pnl_count",
        "nonzero_pnl_ratio",
        "net_pnl_sum",
        "avg_pnl",
        "win_count",
        "loss_count",
        "flat_count",
        "win_rate",
        "avg_win",
        "avg_loss",
        "profit_factor",
        "avg_hold_seconds",
        "forced_exit_count",
        "forced_exit_ratio",
        "reverse_count",
        "reverse_ratio",
        "recovery_count",
        "recovery_ratio",
        "top_decision_winner",
        "top_decision_reason",
        "top_exit_wait_state",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    markdown_lines = [
        "# Profitability / Operations P2 Expectancy / Attribution",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `closed_trade_rows`: `{report['overall_expectancy_summary']['closed_trade_count']}`",
        f"- `net_pnl_sum`: `{report['overall_expectancy_summary']['net_pnl_sum']}`",
        f"- `avg_pnl`: `{report['overall_expectancy_summary']['avg_pnl']}`",
        f"- `fully_attributed_ratio`: `{report['attribution_readiness_summary']['fully_attributed_ratio']}`",
        "",
        "## Top Negative Concerns",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_negative_concerns"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Positive Strengths"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_positive_strengths"] or ["(none)"])])
    markdown_lines.extend(["", "## Next Review Queue"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["next_review_queue"] or ["(none)"])])
    markdown_lines.extend(["", "## Negative Expectancy Clusters"])
    if report["negative_expectancy_clusters"]:
        for cluster in report["negative_expectancy_clusters"][:10]:
            markdown_lines.append(
                f"- `{cluster['cluster_type']}` | `{cluster['severity']}` | {cluster['symbol']} / {cluster['setup_key']} / {cluster['regime_key']} | {cluster['reason']}"
            )
    else:
        markdown_lines.append("- (none)")
    markdown_lines.extend(["", "## Cluster Type Summary"])
    if report["negative_expectancy_cluster_type_summary"]:
        for row in report["negative_expectancy_cluster_type_summary"][:10]:
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
        "negative_cluster_count": len(report["negative_expectancy_clusters"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tail", type=int, default=5000)
    parser.add_argument("--since", type=str, default="")
    parser.add_argument("--symbol", type=str, default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p2_expectancy_attribution_report(
        output_dir=args.output_dir,
        closed_trades_path=DEFAULT_CLOSED_TRADES_PATH,
        tail=args.tail,
        since=args.since,
        symbol_filter=args.symbol,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
