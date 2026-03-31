from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p5_optimization_casebook_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_P2_EXPECTANCY_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p2_expectancy_latest.json"
DEFAULT_P3_ANOMALY_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p3_anomaly_latest.json"
DEFAULT_P4_COMPARE_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p4_compare_latest.json"


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


def _scene_key(symbol: str, setup_key: str, regime_key: str) -> str:
    return f"{symbol} / {setup_key} / {regime_key}"


def _build_scene_alert_map(active_alerts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for alert in active_alerts:
        key = _scene_key(
            _coerce_text(alert.get("symbol")),
            _coerce_text(alert.get("setup_key")),
            _coerce_text(alert.get("regime_key")),
        )
        group = grouped.setdefault(
            key,
            {
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

    for group in grouped.values():
        group["top_alert_type"] = group["_alert_type"].most_common(1)[0][0] if group["_alert_type"] else ""
        group["max_severity"] = "critical" if group["critical_count"] else "high" if group["high_count"] else "medium" if group["medium_count"] else "low"
    return grouped


def _build_symbol_delta_map(symbol_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_coerce_text(row.get("symbol")): row for row in symbol_rows}


def _build_alert_delta_map(alert_rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        _coerce_text(row.get("alert_type")): _coerce_float(row.get("delta"))
        for row in alert_rows
        if _coerce_text(row.get("alert_type"))
    }


def _resolve_candidate_type(scene: dict[str, Any]) -> str:
    top_alert_type = _coerce_text(scene.get("top_alert_type"))
    setup_bucket = _coerce_text(scene.get("setup_bucket"))
    info_gap = bool(scene.get("information_gap_flag"))
    if top_alert_type in {"fast_adverse_close_alert", "cut_now_concentration_alert", "reverse_now_alert"}:
        return "entry_exit_timing_review"
    if top_alert_type in {"blocked_pressure_alert", "skip_heavy_alert", "wait_heavy_alert"}:
        return "consumer_gate_pressure_review"
    if info_gap and setup_bucket == "legacy_without_setup":
        return "legacy_bucket_identity_restore"
    if info_gap:
        return "pnl_lineage_attribution_audit"
    if setup_bucket == "legacy_without_setup":
        return "legacy_bucket_identity_restore"
    return "scene_casebook_review"


def _build_scene_rows(
    p2_payload: dict[str, Any],
    p3_payload: dict[str, Any],
    p4_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    expectancy_rows = p2_payload.get("symbol_setup_regime_expectancy_summary", [])
    scene_alert_map = _build_scene_alert_map(p3_payload.get("active_alerts", []))
    symbol_delta_map = _build_symbol_delta_map(p4_payload.get("symbol_alert_deltas", []))
    alert_delta_map = _build_alert_delta_map(p4_payload.get("p3_alert_type_deltas", []))

    rows: list[dict[str, Any]] = []
    for row in expectancy_rows:
        symbol = _coerce_text(row.get("symbol"))
        setup_key = _coerce_text(row.get("setup_key"))
        regime_key = _coerce_text(row.get("regime_key"))
        key = _scene_key(symbol, setup_key, regime_key)
        alert_info = scene_alert_map.get(key, {})
        symbol_delta = symbol_delta_map.get(symbol, {})
        top_alert_type = _coerce_text(alert_info.get("top_alert_type"))
        top_alert_delta = _coerce_float(alert_delta_map.get(top_alert_type))
        avg_pnl = _coerce_float(row.get("avg_pnl"))
        count = _coerce_int(row.get("closed_trade_count"))
        nonzero_pnl_ratio = _coerce_float(row.get("nonzero_pnl_ratio"))
        profit_factor = _coerce_float(row.get("profit_factor"))
        information_gap_flag = top_alert_type == "zero_pnl_information_gap_alert" or (count >= 20 and nonzero_pnl_ratio == 0.0)

        negative_drag_score = max(0.0, -avg_pnl) * count * 20.0
        information_gap_score = (count * 0.5) if information_gap_flag else 0.0
        alert_pressure_score = (
            _coerce_int(alert_info.get("critical_count")) * 100.0
            + _coerce_int(alert_info.get("high_count")) * 40.0
            + _coerce_int(alert_info.get("medium_count")) * 15.0
        )
        symbol_delta_score = max(0.0, _coerce_float(symbol_delta.get("active_alert_delta"))) * 10.0
        worst_score = round(negative_drag_score + information_gap_score + alert_pressure_score + symbol_delta_score, 4)
        strength_score = round(
            max(0.0, avg_pnl) * count * 20.0
            + max(0.0, profit_factor - 1.0) * 50.0
            + max(0.0, nonzero_pnl_ratio) * 20.0
            - _coerce_int(alert_info.get("high_count")) * 20.0
            - _coerce_int(alert_info.get("critical_count")) * 40.0
            + max(0.0, -_coerce_float(symbol_delta.get("active_alert_delta"))) * 5.0,
            4,
        )

        scene_row = {
            "symbol": symbol,
            "setup_bucket": _coerce_text(row.get("setup_bucket")),
            "setup_key": setup_key,
            "regime_key": regime_key,
            "scene_key": key,
            "closed_trade_count": count,
            "avg_pnl": avg_pnl,
            "profit_factor": profit_factor,
            "nonzero_pnl_ratio": nonzero_pnl_ratio,
            "active_alert_count": _coerce_int(alert_info.get("active_alert_count")),
            "critical_count": _coerce_int(alert_info.get("critical_count")),
            "high_count": _coerce_int(alert_info.get("high_count")),
            "medium_count": _coerce_int(alert_info.get("medium_count")),
            "top_alert_type": top_alert_type,
            "top_alert_delta": top_alert_delta,
            "symbol_active_alert_delta": _coerce_int(symbol_delta.get("active_alert_delta")),
            "information_gap_flag": information_gap_flag,
            "worst_score": worst_score,
            "strength_score": strength_score,
        }
        scene_row["candidate_type"] = _resolve_candidate_type(scene_row)
        rows.append(scene_row)
    return rows


def _build_worst_scene_candidates(scene_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in scene_rows
        if row["closed_trade_count"] >= 20
        and (row["avg_pnl"] < 0 or row["information_gap_flag"] or row["active_alert_count"] > 0)
        and row["worst_score"] > 0
    ]
    return sorted(
        rows,
        key=lambda row: (-_coerce_float(row["worst_score"]), row["symbol"], row["setup_key"], row["regime_key"]),
    )[:15]


def _build_strength_scene_candidates(scene_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in scene_rows
        if row["closed_trade_count"] >= 20
        and row["avg_pnl"] > 0
        and row["nonzero_pnl_ratio"] >= 0.05
        and row["critical_count"] == 0
        and row["strength_score"] > 0
    ]
    return sorted(
        rows,
        key=lambda row: (-_coerce_float(row["strength_score"]), row["symbol"], row["setup_key"], row["regime_key"]),
    )[:10]


def _build_caution_setup_summary(worst_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in worst_rows:
        setup_key = _coerce_text(row.get("setup_key"))
        group = grouped.setdefault(
            setup_key,
            {
                "setup_key": setup_key,
                "scene_count": 0,
                "worst_score_sum": 0.0,
                "_candidate_type": Counter(),
            },
        )
        group["scene_count"] += 1
        group["worst_score_sum"] += _coerce_float(row.get("worst_score"))
        group["_candidate_type"][_coerce_text(row.get("candidate_type"))] += 1

    rows: list[dict[str, Any]] = []
    for group in grouped.values():
        rows.append(
            {
                "setup_key": group["setup_key"],
                "scene_count": group["scene_count"],
                "worst_score_sum": round(group["worst_score_sum"], 4),
                "top_candidate_type": group["_candidate_type"].most_common(1)[0][0] if group["_candidate_type"] else "",
            }
        )
    return sorted(rows, key=lambda row: (-_coerce_float(row["worst_score_sum"]), row["setup_key"]))


def _build_tuning_candidate_queue(worst_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in worst_rows[:10]:
        queue.append(
            {
                "candidate_type": _coerce_text(row.get("candidate_type")),
                "priority_score": round(_coerce_float(row.get("worst_score")), 4),
                "symbol": _coerce_text(row.get("symbol")),
                "setup_key": _coerce_text(row.get("setup_key")),
                "regime_key": _coerce_text(row.get("regime_key")),
                "reason": (
                    f"avg_pnl={_coerce_float(row.get('avg_pnl'))}, "
                    f"alerts={_coerce_int(row.get('active_alert_count'))}, "
                    f"top_alert={_coerce_text(row.get('top_alert_type'))}, "
                    f"symbol_active_alert_delta={_coerce_int(row.get('symbol_active_alert_delta'))}"
                ),
            }
        )
    return queue


def build_profitability_operations_p5_optimization_casebook_report(
    *,
    p2_expectancy_path: Path = DEFAULT_P2_EXPECTANCY_PATH,
    p3_anomaly_path: Path = DEFAULT_P3_ANOMALY_PATH,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    p2_payload = _read_json(p2_expectancy_path)
    p3_payload = _read_json(p3_anomaly_path)
    p4_payload = _read_json(p4_compare_path)

    scene_rows = _build_scene_rows(p2_payload, p3_payload, p4_payload)
    worst_rows = _build_worst_scene_candidates(scene_rows)
    strength_rows = _build_strength_scene_candidates(scene_rows)
    caution_setup_summary = _build_caution_setup_summary(worst_rows)
    tuning_queue = _build_tuning_candidate_queue(worst_rows)
    review_queue = [row["scene_key"] for row in worst_rows[:5]] + [row["scene_key"] for row in strength_rows[:3]]

    candidate_type_counter: Counter[str] = Counter(_coerce_text(row.get("candidate_type")) for row in tuning_queue)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "p2_expectancy_path": str(p2_expectancy_path),
            "p3_anomaly_path": str(p3_anomaly_path),
            "p4_compare_path": str(p4_compare_path),
        },
        "overall_casebook_summary": {
            "scene_row_count": len(scene_rows),
            "worst_scene_count": len(worst_rows),
            "strength_scene_count": len(strength_rows),
            "tuning_candidate_count": len(tuning_queue),
        },
        "worst_scene_candidates": worst_rows,
        "strength_scene_candidates": strength_rows,
        "caution_setup_summary": caution_setup_summary,
        "tuning_candidate_queue": tuning_queue,
        "casebook_review_queue": review_queue,
        "quick_read_summary": {
            "top_caution_scenes": [row["scene_key"] for row in worst_rows[:3]],
            "top_strength_scenes": [row["scene_key"] for row in strength_rows[:3]],
            "top_candidate_types": [
                {"candidate_type": key, "count": value}
                for key, value in candidate_type_counter.most_common()
            ],
        },
    }


def write_profitability_operations_p5_optimization_casebook_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    p2_expectancy_path: Path = DEFAULT_P2_EXPECTANCY_PATH,
    p3_anomaly_path: Path = DEFAULT_P3_ANOMALY_PATH,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p5_optimization_casebook_report(
        p2_expectancy_path=p2_expectancy_path,
        p3_anomaly_path=p3_anomaly_path,
        p4_compare_path=p4_compare_path,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p5_casebook_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p5_casebook_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p5_casebook_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows: list[dict[str, Any]] = []
    for row in report["worst_scene_candidates"]:
        csv_row = dict(row)
        csv_row["candidate_group"] = "worst_scene"
        csv_rows.append(csv_row)
    for row in report["strength_scene_candidates"]:
        csv_row = dict(row)
        csv_row["candidate_group"] = "strength_scene"
        csv_rows.append(csv_row)
    for row in report["tuning_candidate_queue"]:
        csv_row = dict(row)
        csv_row["candidate_group"] = "tuning_candidate"
        csv_rows.append(csv_row)

    fieldnames: list[str] = []
    for row in csv_rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["candidate_group", "symbol", "setup_key", "regime_key"]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    markdown_lines = [
        "# Profitability / Operations P5 Optimization / Casebook",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `worst_scene_count`: `{report['overall_casebook_summary']['worst_scene_count']}`",
        f"- `strength_scene_count`: `{report['overall_casebook_summary']['strength_scene_count']}`",
        f"- `tuning_candidate_count`: `{report['overall_casebook_summary']['tuning_candidate_count']}`",
        "",
        "## Top Caution Scenes",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_caution_scenes"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Strength Scenes"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_strength_scenes"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Candidate Types"])
    for row in report["quick_read_summary"]["top_candidate_types"][:10]:
        markdown_lines.append(f"- `{row['candidate_type']}` | count={row['count']}")
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "tuning_candidate_count": report["overall_casebook_summary"]["tuning_candidate_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p5_optimization_casebook_report(output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
