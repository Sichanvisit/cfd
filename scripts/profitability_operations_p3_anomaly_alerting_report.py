from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p3_anomaly_alerting_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_P1_LIFECYCLE_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p1_lifecycle_latest.json"
DEFAULT_P2_EXPECTANCY_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p2_expectancy_latest.json"
DEFAULT_P2_ZERO_PNL_AUDIT_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p2_zero_pnl_gap_audit_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any) -> float:
    text = _coerce_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _coerce_int(value: Any) -> int:
    text = _coerce_text(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _severity_rank(severity: str) -> int:
    mapping = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    return mapping.get(_coerce_text(severity).lower(), 0)


def _severity_label(rank: int) -> str:
    reverse = {3: "critical", 2: "high", 1: "medium", 0: "low"}
    return reverse.get(rank, "low")


def _normalize_side_from_setup_key(setup_key: str) -> str:
    text = _coerce_text(setup_key).lower()
    if not text:
        return "UNKNOWN"
    if "::buy::" in text or text.endswith("_buy") or "_buy_" in text or "buy" in text:
        return "BUY"
    if "::sell::" in text or text.endswith("_sell") or "_sell_" in text or "sell" in text:
        return "SELL"
    return "UNKNOWN"


def _normalize_p1_severity(cluster_type: str, source_severity: str, count: int, score: float) -> str:
    rank = _severity_rank(source_severity)
    if cluster_type == "fast_adverse_close_cluster" and (count >= 50 or score >= 100.0):
        rank = max(rank, 3)
    elif cluster_type == "cut_now_concentration_cluster" and count >= 50:
        rank = max(rank, 2)
    elif cluster_type == "blocked_pressure_cluster" and count >= 200:
        rank = max(rank, 2)
    elif cluster_type == "coverage_blind_spot_cluster" and count >= 20:
        rank = max(rank, 2)
    elif cluster_type == "wait_heavy_cluster" and count >= 100:
        rank = max(rank, 1)
    elif cluster_type == "reverse_now_cluster" and score >= 5.0:
        rank = max(rank, 1)
    return _severity_label(rank)


def _normalize_p2_severity(cluster_type: str, source_severity: str, count: int, score: float) -> str:
    rank = _severity_rank(source_severity)
    if cluster_type == "negative_expectancy_cluster" and (count >= 100 or score >= 40.0):
        rank = max(rank, 2)
    elif cluster_type == "forced_exit_drag_cluster" and (count >= 25 or score >= 20.0):
        rank = max(rank, 2)
    elif cluster_type == "reverse_drag_cluster" and (count >= 20 or score >= 5.0):
        rank = max(rank, 1)
    elif cluster_type == "legacy_bucket_blind_cluster" and count >= 50:
        rank = max(rank, 2)
    return _severity_label(rank)


def _normalize_zero_pnl_severity(zero_pnl_row_count: int, avg_abs_profit: float, profit_abs_sum: float) -> str:
    if zero_pnl_row_count >= 200 and (avg_abs_profit >= 5.0 or profit_abs_sum >= 500.0):
        return "high"
    if zero_pnl_row_count >= 100 or profit_abs_sum >= 200.0:
        return "medium"
    return "low"


def _recommended_action_for_alert(alert_type: str, *, setup_bucket: str = "") -> str:
    mapping = {
        "fast_adverse_close_alert": "review entry timing and guard strictness before open",
        "blocked_pressure_alert": "review repeated blocking guard concentration and whether it is too restrictive",
        "wait_heavy_alert": "review whether wait state is over-concentrated without conversion",
        "cut_now_concentration_alert": "review whether exit pressure is too quickly collapsing into cut_now",
        "reverse_now_alert": "review reverse decision recurrence and timing quality",
        "coverage_blind_spot_alert": "review whether lifecycle concern is dominated by coverage limitation",
        "negative_expectancy_alert": "review expectancy drag bucket before further tuning",
        "forced_exit_drag_alert": "review forced-exit concentration and whether management profile is too tight",
        "reverse_drag_alert": "review reverse-driven drag and whether reversal management is too reactive",
        "legacy_bucket_blind_alert": "review legacy bucket attribution and explicit setup restoration priority",
        "zero_pnl_information_gap_alert": "review pnl field lineage and attribution quality before treating this as true zero expectancy",
    }
    action = mapping.get(alert_type, "review source bucket")
    if alert_type == "zero_pnl_information_gap_alert" and setup_bucket == "legacy_without_setup":
        return "review legacy attribution gap and pnl field lineage before expectancy interpretation"
    return action


def _build_alerts_from_p1(p1_payload: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for cluster in p1_payload.get("suspicious_clusters", []):
        cluster_type = _coerce_text(cluster.get("cluster_type"))
        count = _coerce_int(cluster.get("count"))
        score = _coerce_float(cluster.get("score"))
        severity = _normalize_p1_severity(cluster_type, _coerce_text(cluster.get("severity")), count, score)
        if _severity_rank(severity) <= 0:
            continue
        alert_type = cluster_type.replace("_cluster", "_alert")
        alerts.append(
            {
                "alert_type": alert_type,
                "severity": severity,
                "source_track": "P1",
                "source_kind": "lifecycle",
                "source_cluster_type": cluster_type,
                "symbol": _coerce_text(cluster.get("symbol")),
                "setup_key": _coerce_text(cluster.get("setup_key")),
                "regime_key": _coerce_text(cluster.get("regime_key")),
                "side_key": _coerce_text(cluster.get("side_key")) or _normalize_side_from_setup_key(cluster.get("setup_key")),
                "setup_bucket": "",
                "count": count,
                "score": round(score, 4),
                "reason": _coerce_text(cluster.get("reason")),
                "evidence_hint": _coerce_text(cluster.get("family_key")) or _coerce_text(cluster.get("family_root_key")),
                "recommended_action": _recommended_action_for_alert(alert_type),
            }
        )
    return alerts


def _build_alerts_from_p2(p2_payload: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for cluster in p2_payload.get("negative_expectancy_clusters", []):
        cluster_type = _coerce_text(cluster.get("cluster_type"))
        if cluster_type == "zero_pnl_information_gap_cluster":
            continue
        count = _coerce_int(cluster.get("count"))
        score = _coerce_float(cluster.get("score"))
        severity = _normalize_p2_severity(cluster_type, _coerce_text(cluster.get("severity")), count, score)
        if _severity_rank(severity) <= 0:
            continue
        alert_type = cluster_type.replace("_cluster", "_alert")
        setup_key = _coerce_text(cluster.get("setup_key"))
        setup_bucket = _coerce_text(cluster.get("setup_bucket"))
        alerts.append(
            {
                "alert_type": alert_type,
                "severity": severity,
                "source_track": "P2",
                "source_kind": "expectancy",
                "source_cluster_type": cluster_type,
                "symbol": _coerce_text(cluster.get("symbol")),
                "setup_key": setup_key,
                "regime_key": _coerce_text(cluster.get("regime_key")),
                "side_key": _normalize_side_from_setup_key(setup_key),
                "setup_bucket": setup_bucket,
                "count": count,
                "score": round(score, 4),
                "reason": _coerce_text(cluster.get("reason")),
                "evidence_hint": f"{_coerce_text(cluster.get('symbol'))} / {setup_key} / {_coerce_text(cluster.get('regime_key'))}",
                "recommended_action": _recommended_action_for_alert(alert_type, setup_bucket=setup_bucket),
            }
        )
    return alerts


def _build_alerts_from_zero_pnl_audit(zero_payload: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for row in zero_payload.get("suspicious_zero_pnl_buckets", []):
        count = _coerce_int(row.get("zero_pnl_row_count"))
        avg_abs_profit = _coerce_float(row.get("avg_abs_profit"))
        profit_abs_sum = _coerce_float(row.get("profit_abs_sum"))
        severity = _normalize_zero_pnl_severity(count, avg_abs_profit, profit_abs_sum)
        if _severity_rank(severity) <= 0:
            continue
        setup_key = _coerce_text(row.get("setup_key"))
        setup_bucket = _coerce_text(row.get("setup_bucket"))
        pattern = _coerce_text(row.get("pattern"))
        alerts.append(
            {
                "alert_type": "zero_pnl_information_gap_alert",
                "severity": severity,
                "source_track": "P2-support",
                "source_kind": "zero_pnl_gap_audit",
                "source_cluster_type": pattern,
                "symbol": _coerce_text(row.get("symbol")),
                "setup_key": setup_key,
                "regime_key": _coerce_text(row.get("regime_key")),
                "side_key": _normalize_side_from_setup_key(setup_key),
                "setup_bucket": setup_bucket,
                "count": count,
                "score": round(profit_abs_sum, 4),
                "reason": (
                    f"{pattern} is dominating the zero-pnl bucket while avg_abs_profit={avg_abs_profit}, "
                    "so economic interpretation is likely hidden by pnl field mismatch or attribution gap"
                ),
                "evidence_hint": (
                    f"missing_setup_ratio={_coerce_float(row.get('missing_setup_ratio'))}, "
                    f"missing_regime_ratio={_coerce_float(row.get('missing_regime_ratio'))}, "
                    f"missing_decision_winner_ratio={_coerce_float(row.get('missing_decision_winner_ratio'))}"
                ),
                "recommended_action": _recommended_action_for_alert("zero_pnl_information_gap_alert", setup_bucket=setup_bucket),
            }
        )
    return alerts


def _sort_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        alerts,
        key=lambda row: (
            -_severity_rank(_coerce_text(row.get("severity"))),
            -_coerce_float(row.get("score")),
            -_coerce_int(row.get("count")),
            _coerce_text(row.get("symbol")),
            _coerce_text(row.get("setup_key")),
        ),
    )


def _build_symbol_summary(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        symbol = _coerce_text(alert.get("symbol")) or "UNKNOWN"
        group = grouped.setdefault(
            symbol,
            {
                "symbol": symbol,
                "active_alert_count": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "score_sum": 0.0,
                "_alert_type": Counter(),
            },
        )
        group["active_alert_count"] += 1
        group["score_sum"] += _coerce_float(alert.get("score"))
        severity = _coerce_text(alert.get("severity"))
        if severity == "critical":
            group["critical_count"] += 1
        elif severity == "high":
            group["high_count"] += 1
        elif severity == "medium":
            group["medium_count"] += 1
        group["_alert_type"][_coerce_text(alert.get("alert_type"))] += 1

    rows: list[dict[str, Any]] = []
    for group in grouped.values():
        rows.append(
            {
                "symbol": group["symbol"],
                "active_alert_count": int(group["active_alert_count"]),
                "critical_count": int(group["critical_count"]),
                "high_count": int(group["high_count"]),
                "medium_count": int(group["medium_count"]),
                "score_sum": round(float(group["score_sum"]), 4),
                "top_alert_type": group["_alert_type"].most_common(1)[0][0] if group["_alert_type"] else "",
            }
        )
    return sorted(
        rows,
        key=lambda row: (-int(row["critical_count"]), -int(row["high_count"]), -float(row["score_sum"]), row["symbol"]),
    )


def _dedupe_review_queue(alerts: list[dict[str, Any]], limit: int = 8) -> list[str]:
    queue: list[str] = []
    seen: set[str] = set()
    for alert in alerts:
        item = f"{_coerce_text(alert.get('symbol'))} / {_coerce_text(alert.get('setup_key'))} / {_coerce_text(alert.get('regime_key'))}"
        if item in seen:
            continue
        seen.add(item)
        queue.append(item)
        if len(queue) >= limit:
            break
    return queue


def build_profitability_operations_p3_anomaly_alerting_report(
    *,
    p1_lifecycle_path: Path = DEFAULT_P1_LIFECYCLE_PATH,
    p2_expectancy_path: Path = DEFAULT_P2_EXPECTANCY_PATH,
    p2_zero_pnl_audit_path: Path = DEFAULT_P2_ZERO_PNL_AUDIT_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    p1_payload = _read_json(p1_lifecycle_path)
    p2_payload = _read_json(p2_expectancy_path)
    zero_payload = _read_json(p2_zero_pnl_audit_path)

    alerts = _sort_alerts(
        _build_alerts_from_p1(p1_payload)
        + _build_alerts_from_p2(p2_payload)
        + _build_alerts_from_zero_pnl_audit(zero_payload)
    )

    severity_counter: Counter[str] = Counter()
    alert_type_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    for alert in alerts:
        severity_counter[_coerce_text(alert.get("severity"))] += 1
        alert_type_counter[_coerce_text(alert.get("alert_type"))] += 1
        source_counter[_coerce_text(alert.get("source_kind"))] += 1

    symbol_summary = _build_symbol_summary(alerts)
    review_queue = _dedupe_review_queue(alerts)
    top_alerts = [
        f"{_coerce_text(row.get('severity')).upper()} | {_coerce_text(row.get('symbol'))} / {_coerce_text(row.get('setup_key'))} / {_coerce_text(row.get('regime_key'))} | {_coerce_text(row.get('alert_type'))}"
        for row in alerts[:5]
    ]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "p1_lifecycle_path": str(p1_lifecycle_path),
            "p2_expectancy_path": str(p2_expectancy_path),
            "p2_zero_pnl_audit_path": str(p2_zero_pnl_audit_path),
            "p1_report_version": _coerce_text(p1_payload.get("report_version")),
            "p2_report_version": _coerce_text(p2_payload.get("report_version")),
            "p2_zero_pnl_audit_report_version": _coerce_text(zero_payload.get("report_version")),
        },
        "overall_alert_summary": {
            "active_alert_count": len(alerts),
            "critical_count": severity_counter.get("critical", 0),
            "high_count": severity_counter.get("high", 0),
            "medium_count": severity_counter.get("medium", 0),
            "alert_type_count": len(alert_type_counter),
        },
        "source_summary": [{"source_kind": key, "count": value} for key, value in source_counter.most_common()],
        "severity_summary": [{"severity": key, "count": value} for key, value in severity_counter.most_common()],
        "alert_type_summary": [{"alert_type": key, "count": value} for key, value in alert_type_counter.most_common()],
        "symbol_alert_summary": symbol_summary,
        "active_alerts": alerts,
        "operator_review_queue": review_queue,
        "quick_read_summary": {
            "top_alerts": top_alerts,
            "next_review_queue": review_queue[:5],
        },
    }


def write_profitability_operations_p3_anomaly_alerting_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    p1_lifecycle_path: Path = DEFAULT_P1_LIFECYCLE_PATH,
    p2_expectancy_path: Path = DEFAULT_P2_EXPECTANCY_PATH,
    p2_zero_pnl_audit_path: Path = DEFAULT_P2_ZERO_PNL_AUDIT_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p3_anomaly_alerting_report(
        p1_lifecycle_path=p1_lifecycle_path,
        p2_expectancy_path=p2_expectancy_path,
        p2_zero_pnl_audit_path=p2_zero_pnl_audit_path,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p3_anomaly_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p3_anomaly_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p3_anomaly_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = report["active_alerts"]
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "alert_type", "severity", "source_track", "source_kind", "source_cluster_type", "symbol",
        "setup_key", "regime_key", "side_key", "setup_bucket", "count", "score", "reason",
        "evidence_hint", "recommended_action",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    markdown_lines = [
        "# Profitability / Operations P3 Anomaly / Alerting",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `active_alert_count`: `{report['overall_alert_summary']['active_alert_count']}`",
        f"- `critical_count`: `{report['overall_alert_summary']['critical_count']}`",
        f"- `high_count`: `{report['overall_alert_summary']['high_count']}`",
        f"- `medium_count`: `{report['overall_alert_summary']['medium_count']}`",
        "",
        "## Top Alerts",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_alerts"] or ["(none)"])])
    markdown_lines.extend(["", "## Review Queue"])
    markdown_lines.extend([f"- {item}" for item in (report["operator_review_queue"] or ["(none)"])])
    markdown_lines.extend(["", "## Alert Type Summary"])
    for row in report["alert_type_summary"][:10]:
        markdown_lines.append(f"- `{row['alert_type']}` | count={row['count']}")
    markdown_lines.extend(["", "## Symbol Summary"])
    for row in report["symbol_alert_summary"][:10]:
        markdown_lines.append(
            f"- `{row['symbol']}` | active={row['active_alert_count']} | critical={row['critical_count']} | high={row['high_count']} | top={row['top_alert_type']}"
        )
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "active_alert_count": report["overall_alert_summary"]["active_alert_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p3_anomaly_alerting_report(output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
