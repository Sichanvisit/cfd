from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p6_metacognition_health_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_P3_ANOMALY_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p3_anomaly_latest.json"
DEFAULT_P4_COMPARE_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p4_compare_latest.json"
DEFAULT_P5_CASEBOOK_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p5_casebook_latest.json"


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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _health_state(score: float, *, critical_count: int, high_count: int, alert_delta: int) -> str:
    if critical_count > 0 or score < 35.0:
        return "stressed"
    if score < 60.0 or high_count > 0 or alert_delta > 0:
        return "watch"
    return "healthy"


def _size_action(multiplier: float) -> str:
    if multiplier <= 0.45:
        return "hard_reduce"
    if multiplier <= 0.7:
        return "reduce"
    if multiplier <= 0.95:
        return "hold_small"
    if multiplier <= 1.05:
        return "normal"
    return "allow_expand"


def _symbol_context_from_casebook(casebook_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    def ensure(symbol: str) -> dict[str, Any]:
        return grouped.setdefault(
            symbol,
            {
                "symbol": symbol,
                "worst_scene_count": 0,
                "strength_scene_count": 0,
                "information_gap_scene_count": 0,
                "worst_score_sum": 0.0,
                "strength_score_sum": 0.0,
                "_candidate_type": Counter(),
                "_setup_key": Counter(),
            },
        )

    for row in casebook_payload.get("worst_scene_candidates", []):
        symbol = _coerce_text(row.get("symbol"))
        if not symbol:
            continue
        ctx = ensure(symbol)
        ctx["worst_scene_count"] += 1
        ctx["worst_score_sum"] += _coerce_float(row.get("worst_score"))
        if bool(row.get("information_gap_flag")):
            ctx["information_gap_scene_count"] += 1
        ctx["_candidate_type"][_coerce_text(row.get("candidate_type"))] += 1
        ctx["_setup_key"][_coerce_text(row.get("setup_key"))] += 1

    for row in casebook_payload.get("strength_scene_candidates", []):
        symbol = _coerce_text(row.get("symbol"))
        if not symbol:
            continue
        ctx = ensure(symbol)
        ctx["strength_scene_count"] += 1
        ctx["strength_score_sum"] += _coerce_float(row.get("strength_score"))
        ctx["_setup_key"][_coerce_text(row.get("setup_key"))] += 1

    return grouped


def _archetype_context_from_casebook(casebook_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    def ensure(setup_key: str) -> dict[str, Any]:
        return grouped.setdefault(
            setup_key,
            {
                "setup_key": setup_key,
                "caution_scene_count": 0,
                "strength_scene_count": 0,
                "information_gap_scene_count": 0,
                "worst_score_sum": 0.0,
                "strength_score_sum": 0.0,
                "_candidate_type": Counter(),
                "_symbol": Counter(),
            },
        )

    for row in casebook_payload.get("worst_scene_candidates", []):
        setup_key = _coerce_text(row.get("setup_key"))
        if not setup_key:
            continue
        ctx = ensure(setup_key)
        ctx["caution_scene_count"] += 1
        ctx["worst_score_sum"] += _coerce_float(row.get("worst_score"))
        if bool(row.get("information_gap_flag")):
            ctx["information_gap_scene_count"] += 1
        ctx["_candidate_type"][_coerce_text(row.get("candidate_type"))] += 1
        ctx["_symbol"][_coerce_text(row.get("symbol"))] += 1

    for row in casebook_payload.get("strength_scene_candidates", []):
        setup_key = _coerce_text(row.get("setup_key"))
        if not setup_key:
            continue
        ctx = ensure(setup_key)
        ctx["strength_scene_count"] += 1
        ctx["strength_score_sum"] += _coerce_float(row.get("strength_score"))
        ctx["_symbol"][_coerce_text(row.get("symbol"))] += 1

    return grouped


def _build_symbol_health_summary(
    p3_payload: dict[str, Any],
    p4_payload: dict[str, Any],
    casebook_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    p3_symbol_rows = {
        _coerce_text(row.get("symbol")): row
        for row in p3_payload.get("symbol_alert_summary", [])
        if _coerce_text(row.get("symbol"))
    }
    p4_symbol_rows = {
        _coerce_text(row.get("symbol")): row
        for row in p4_payload.get("symbol_alert_deltas", [])
        if _coerce_text(row.get("symbol"))
    }
    casebook_ctx = _symbol_context_from_casebook(casebook_payload)

    rows: list[dict[str, Any]] = []
    symbols = sorted(set(p3_symbol_rows) | set(p4_symbol_rows) | set(casebook_ctx))
    for symbol in symbols:
        p3_row = p3_symbol_rows.get(symbol, {})
        p4_row = p4_symbol_rows.get(symbol, {})
        ctx = casebook_ctx.get(symbol, {})
        critical_count = _coerce_int(p3_row.get("critical_count"))
        high_count = _coerce_int(p3_row.get("high_count"))
        medium_count = _coerce_int(p3_row.get("medium_count"))
        active_alert_count = _coerce_int(p3_row.get("active_alert_count"))
        active_alert_delta = _coerce_int(p4_row.get("active_alert_delta"))
        worst_scene_count = _coerce_int(ctx.get("worst_scene_count"))
        strength_scene_count = _coerce_int(ctx.get("strength_scene_count"))
        info_gap_scene_count = _coerce_int(ctx.get("information_gap_scene_count"))

        score = 100.0
        score -= critical_count * 25.0
        score -= high_count * 4.5
        score -= medium_count * 1.0
        score -= max(0, active_alert_delta) * 4.0
        score -= worst_scene_count * 5.0
        score -= info_gap_scene_count * 4.0
        score += strength_scene_count * 6.0
        score += max(0, -active_alert_delta) * 2.0
        score = round(_clamp(score, 0.0, 100.0), 2)

        multiplier = 1.0
        multiplier -= 0.35 if critical_count > 0 else 0.0
        multiplier -= 0.02 * min(8, high_count)
        multiplier -= 0.008 * min(12, medium_count)
        multiplier -= 0.05 * min(4, max(0, active_alert_delta))
        multiplier -= 0.03 * min(4, worst_scene_count)
        multiplier -= 0.03 * min(3, info_gap_scene_count)
        multiplier += 0.04 * min(2, strength_scene_count)
        multiplier += 0.02 * min(2, max(0, -active_alert_delta))
        multiplier = round(_clamp(multiplier, 0.25, 1.10), 2)

        top_candidate_type = ctx.get("_candidate_type", Counter()).most_common(1)[0][0] if ctx.get("_candidate_type") else ""
        top_setup_key = ctx.get("_setup_key", Counter()).most_common(1)[0][0] if ctx.get("_setup_key") else ""
        health_state = _health_state(score, critical_count=critical_count, high_count=high_count, alert_delta=active_alert_delta)

        rows.append(
            {
                "symbol": symbol,
                "health_score": score,
                "health_state": health_state,
                "active_alert_count": active_alert_count,
                "critical_count": critical_count,
                "high_count": high_count,
                "medium_count": medium_count,
                "active_alert_delta": active_alert_delta,
                "worst_scene_count": worst_scene_count,
                "strength_scene_count": strength_scene_count,
                "information_gap_scene_count": info_gap_scene_count,
                "top_alert_type": _coerce_text(p3_row.get("top_alert_type")),
                "top_candidate_type": top_candidate_type,
                "top_setup_key": top_setup_key,
                "size_multiplier": multiplier,
                "size_action": _size_action(multiplier),
            }
        )

    return sorted(
        rows,
        key=lambda row: (_coerce_text(row["health_state"]), row["health_score"], row["symbol"]),
    )


def _build_archetype_health_summary(casebook_payload: dict[str, Any]) -> list[dict[str, Any]]:
    ctx_map = _archetype_context_from_casebook(casebook_payload)
    rows: list[dict[str, Any]] = []
    for setup_key, ctx in ctx_map.items():
        caution_count = _coerce_int(ctx.get("caution_scene_count"))
        strength_count = _coerce_int(ctx.get("strength_scene_count"))
        info_gap_count = _coerce_int(ctx.get("information_gap_scene_count"))
        score = 50.0 + strength_count * 10.0 - caution_count * 10.0 - info_gap_count * 5.0
        score = round(_clamp(score, 0.0, 100.0), 2)
        state = "healthy" if score >= 60.0 else "watch" if score >= 35.0 else "stressed"
        rows.append(
            {
                "setup_key": setup_key,
                "health_score": score,
                "health_state": state,
                "caution_scene_count": caution_count,
                "strength_scene_count": strength_count,
                "information_gap_scene_count": info_gap_count,
                "top_candidate_type": ctx["_candidate_type"].most_common(1)[0][0] if ctx.get("_candidate_type") else "",
                "top_symbol": ctx["_symbol"].most_common(1)[0][0] if ctx.get("_symbol") else "",
            }
        )
    return sorted(rows, key=lambda row: (row["health_score"], row["setup_key"]))


def _build_drift_signal_summary(p4_payload: dict[str, Any], symbol_health_rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall_delta = p4_payload.get("overall_delta_summary", {})
    worsening_alert_types = [
        row for row in p4_payload.get("p3_alert_type_deltas", [])
        if _coerce_float(row.get("delta")) > 0
    ]
    worsening_symbols = [
        row for row in p4_payload.get("symbol_alert_deltas", [])
        if _coerce_int(row.get("active_alert_delta")) > 0
    ]
    improving_symbols = [
        row for row in p4_payload.get("symbol_alert_deltas", [])
        if _coerce_int(row.get("active_alert_delta")) < 0
    ]

    active_alert_delta = _coerce_int(overall_delta.get("active_alert_delta"))
    if active_alert_delta > 5 or any(_coerce_int(row.get("critical_delta")) > 0 for row in p4_payload.get("symbol_alert_deltas", [])):
        overall_state = "worsening"
    elif active_alert_delta < -5:
        overall_state = "improving"
    else:
        overall_state = "mixed"

    stressed_symbols = [row["symbol"] for row in symbol_health_rows if _coerce_text(row.get("health_state")) == "stressed"]
    return {
        "overall_drift_state": overall_state,
        "active_alert_delta": active_alert_delta,
        "top_worsening_alert_types": [
            {
                "alert_type": _coerce_text(row.get("alert_type")),
                "delta": _coerce_float(row.get("delta")),
            }
            for row in worsening_alert_types[:5]
        ],
        "top_worsening_symbols": [
            {
                "symbol": _coerce_text(row.get("symbol")),
                "active_alert_delta": _coerce_int(row.get("active_alert_delta")),
            }
            for row in worsening_symbols[:5]
        ],
        "top_improving_symbols": [
            {
                "symbol": _coerce_text(row.get("symbol")),
                "active_alert_delta": _coerce_int(row.get("active_alert_delta")),
            }
            for row in improving_symbols[:5]
        ],
        "stressed_symbol_count": len(stressed_symbols),
        "stressed_symbols": stressed_symbols[:5],
    }


def _build_sizing_overlay_recommendations(symbol_health_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "symbol": row["symbol"],
                "health_state": row["health_state"],
                "size_multiplier": row["size_multiplier"],
                "size_action": row["size_action"],
                "top_alert_type": row["top_alert_type"],
                "top_candidate_type": row["top_candidate_type"],
                "rationale": (
                    f"alerts={row['active_alert_count']}, high={row['high_count']}, critical={row['critical_count']}, "
                    f"alert_delta={row['active_alert_delta']}, worst_scenes={row['worst_scene_count']}, strengths={row['strength_scene_count']}"
                ),
            }
            for row in symbol_health_rows
        ],
        key=lambda row: (row["size_multiplier"], row["symbol"]),
    )


def build_profitability_operations_p6_metacognition_health_report(
    *,
    p3_anomaly_path: Path = DEFAULT_P3_ANOMALY_PATH,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    p5_casebook_path: Path = DEFAULT_P5_CASEBOOK_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    p3_payload = _read_json(p3_anomaly_path)
    p4_payload = _read_json(p4_compare_path)
    p5_payload = _read_json(p5_casebook_path)

    symbol_health_rows = _build_symbol_health_summary(p3_payload, p4_payload, p5_payload)
    archetype_health_rows = _build_archetype_health_summary(p5_payload)
    drift_summary = _build_drift_signal_summary(p4_payload, symbol_health_rows)
    sizing_rows = _build_sizing_overlay_recommendations(symbol_health_rows)

    state_counter: Counter[str] = Counter(_coerce_text(row.get("health_state")) for row in symbol_health_rows)
    candidate_type_counter: Counter[str] = Counter(
        _coerce_text(row.get("candidate_type"))
        for row in p5_payload.get("tuning_candidate_queue", [])
        if _coerce_text(row.get("candidate_type"))
    )
    overall_size_multiplier = round(
        sum(_coerce_float(row.get("size_multiplier")) for row in sizing_rows) / len(sizing_rows), 3
    ) if sizing_rows else 1.0

    review_queue = [row["symbol"] for row in sizing_rows[:3]] + drift_summary.get("stressed_symbols", [])
    review_queue = list(dict.fromkeys([item for item in review_queue if item]))

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "p3_anomaly_path": str(p3_anomaly_path),
            "p4_compare_path": str(p4_compare_path),
            "p5_casebook_path": str(p5_casebook_path),
        },
        "overall_health_summary": {
            "symbol_count": len(symbol_health_rows),
            "healthy_symbol_count": state_counter.get("healthy", 0),
            "watch_symbol_count": state_counter.get("watch", 0),
            "stressed_symbol_count": state_counter.get("stressed", 0),
            "overall_drift_state": drift_summary.get("overall_drift_state", ""),
            "global_size_multiplier": overall_size_multiplier,
            "top_candidate_type": candidate_type_counter.most_common(1)[0][0] if candidate_type_counter else "",
        },
        "symbol_health_summary": symbol_health_rows,
        "archetype_health_summary": archetype_health_rows,
        "drift_signal_summary": drift_summary,
        "sizing_overlay_recommendations": sizing_rows,
        "operator_review_queue": review_queue,
        "quick_read_summary": {
            "top_stressed_symbols": [row["symbol"] for row in symbol_health_rows if row["health_state"] == "stressed"][:3],
            "top_reduce_symbols": [row["symbol"] for row in sizing_rows if row["size_action"] in {"hard_reduce", "reduce"}][:3],
            "top_expand_symbols": [row["symbol"] for row in sizing_rows if row["size_action"] == "allow_expand"][:3],
            "top_drift_signals": drift_summary.get("top_worsening_alert_types", [])[:3],
        },
    }


def write_profitability_operations_p6_metacognition_health_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    p3_anomaly_path: Path = DEFAULT_P3_ANOMALY_PATH,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    p5_casebook_path: Path = DEFAULT_P5_CASEBOOK_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p6_metacognition_health_report(
        p3_anomaly_path=p3_anomaly_path,
        p4_compare_path=p4_compare_path,
        p5_casebook_path=p5_casebook_path,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p6_health_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p6_health_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p6_health_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = report["sizing_overlay_recommendations"]
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "symbol", "health_state", "size_multiplier", "size_action", "top_alert_type", "top_candidate_type", "rationale",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    overall = report["overall_health_summary"]
    markdown_lines = [
        "# Profitability / Operations P6 Meta-Cognition / Health / Drift / Sizing",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `overall_drift_state`: `{overall['overall_drift_state']}`",
        f"- `global_size_multiplier`: `{overall['global_size_multiplier']}`",
        f"- `healthy_symbol_count`: `{overall['healthy_symbol_count']}`",
        f"- `watch_symbol_count`: `{overall['watch_symbol_count']}`",
        f"- `stressed_symbol_count`: `{overall['stressed_symbol_count']}`",
        "",
        "## Top Stressed Symbols",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_stressed_symbols"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Reduce Symbols"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_reduce_symbols"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Expand Symbols"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_expand_symbols"] or ["(none)"])])
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "symbol_count": overall["symbol_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p6_metacognition_health_report(output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
