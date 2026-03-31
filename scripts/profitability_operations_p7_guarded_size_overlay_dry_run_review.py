from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p7_guarded_size_overlay_dry_run_review_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_ENTRY_DECISIONS_PATH = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OVERLAY_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p7_guarded_size_overlay_latest.json"

P7_REQUIRED_COLUMNS = (
    "p7_guarded_size_overlay_v1",
    "p7_size_overlay_mode",
    "p7_size_overlay_gate_reason",
    "p7_size_overlay_matched",
)


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any, default: float = 0.0) -> float:
    text = _coerce_text(value)
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _coerce_int(value: Any, default: int = 0) -> int:
    text = _coerce_text(value)
    if not text:
        return int(default)
    try:
        return int(float(text))
    except Exception:
        return int(default)


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if not path.exists():
        return [], []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                return list(reader.fieldnames or []), rows
        except Exception:
            continue
    return [], []


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _tail(rows: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    if size <= 0 or len(rows) <= size:
        return rows
    return rows[-size:]


def _parse_overlay_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _coerce_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def build_profitability_operations_p7_guarded_size_overlay_dry_run_review(
    *,
    entry_decisions_path: Path = DEFAULT_ENTRY_DECISIONS_PATH,
    overlay_path: Path = DEFAULT_OVERLAY_PATH,
    tail: int = 5000,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    columns, rows = _read_csv_rows(entry_decisions_path)
    rows = _tail(rows, tail)
    overlay_payload = _read_json(overlay_path)
    overlay_candidates = overlay_payload.get("guarded_size_overlay_candidates", []) or []

    schema_present = all(column in columns for column in P7_REQUIRED_COLUMNS)
    p7_rows: list[dict[str, Any]] = []
    symbol_grouped: dict[str, dict[str, Any]] = {}
    mode_counter: Counter[str] = Counter()
    gate_counter: Counter[str] = Counter()
    symbol_gate_counter: dict[str, Counter[str]] = {}

    for row in rows:
        overlay_row = _parse_overlay_payload(row.get("p7_guarded_size_overlay_v1"))
        mode = _coerce_text(row.get("p7_size_overlay_mode") or overlay_row.get("mode"))
        matched = bool(_coerce_int(row.get("p7_size_overlay_matched"), 0) or overlay_row.get("matched"))
        gate_reason = _coerce_text(row.get("p7_size_overlay_gate_reason") or overlay_row.get("gate_reason"))
        symbol = _coerce_text(row.get("symbol")).upper()
        if not symbol:
            continue
        if not overlay_row and not mode and not gate_reason and not matched:
            continue

        p7_rows.append(row)
        mode_counter[mode or "unknown"] += 1
        gate_counter[gate_reason or "unknown"] += 1
        symbol_gate_counter.setdefault(symbol, Counter())[gate_reason or "unknown"] += 1

        bucket = symbol_grouped.setdefault(
            symbol,
            {
                "symbol": symbol,
                "row_count": 0,
                "matched_count": 0,
                "apply_allowed_count": 0,
                "applied_count": 0,
                "gate_reason_counter": Counter(),
                "mode_counter": Counter(),
                "target_multiplier_sum": 0.0,
                "effective_multiplier_sum": 0.0,
            },
        )
        bucket["row_count"] += 1
        bucket["matched_count"] += int(1 if matched else 0)
        bucket["apply_allowed_count"] += int(
            1 if (_coerce_int(row.get("p7_size_overlay_apply_allowed"), 0) or overlay_row.get("apply_allowed")) else 0
        )
        bucket["applied_count"] += int(
            1 if (_coerce_int(row.get("p7_size_overlay_applied"), 0) or overlay_row.get("applied")) else 0
        )
        bucket["gate_reason_counter"][gate_reason or "unknown"] += 1
        bucket["mode_counter"][mode or "unknown"] += 1
        bucket["target_multiplier_sum"] += _coerce_float(
            row.get("p7_size_overlay_target_multiplier") or overlay_row.get("target_multiplier"),
            0.0,
        )
        bucket["effective_multiplier_sum"] += _coerce_float(
            row.get("p7_size_overlay_effective_multiplier") or overlay_row.get("effective_multiplier"),
            0.0,
        )

    symbol_rows: list[dict[str, Any]] = []
    for symbol, bucket in sorted(symbol_grouped.items()):
        row_count = max(1, int(bucket["row_count"]))
        symbol_rows.append(
            {
                "symbol": symbol,
                "row_count": int(bucket["row_count"]),
                "matched_count": int(bucket["matched_count"]),
                "matched_ratio": round(float(bucket["matched_count"]) / row_count, 4),
                "apply_allowed_count": int(bucket["apply_allowed_count"]),
                "applied_count": int(bucket["applied_count"]),
                "top_mode": bucket["mode_counter"].most_common(1)[0][0] if bucket["mode_counter"] else "",
                "top_gate_reason": (
                    bucket["gate_reason_counter"].most_common(1)[0][0] if bucket["gate_reason_counter"] else ""
                ),
                "avg_target_multiplier": round(float(bucket["target_multiplier_sum"]) / row_count, 4),
                "avg_effective_multiplier": round(float(bucket["effective_multiplier_sum"]) / row_count, 4),
            }
        )

    if not schema_present:
        review_state = "pre_p7_schema_header"
        recommended_next_step = "restart_runtime_and_wait_for_new_entry_rows"
    elif not p7_rows:
        review_state = "waiting_for_first_dry_run_rows"
        recommended_next_step = "wait_for_new_entry_rows_after_restart"
    else:
        review_state = "dry_run_rows_accumulating"
        recommended_next_step = "review_btc_only_apply_gate_when_rows_are_sufficient"

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "entry_decisions_path": str(entry_decisions_path),
            "overlay_path": str(overlay_path),
            "tail": int(tail),
        },
        "overall_summary": {
            "entry_decision_row_count": len(rows),
            "p7_schema_present": bool(schema_present),
            "p7_trace_row_count": len(p7_rows),
            "overlay_candidate_count": len(overlay_candidates),
            "symbol_trace_count": len(symbol_rows),
            "review_state": review_state,
            "recommended_next_step": recommended_next_step,
        },
        "mode_summary": [
            {"mode": mode, "count": count}
            for mode, count in mode_counter.most_common()
        ],
        "gate_reason_summary": [
            {"gate_reason": gate_reason, "count": count}
            for gate_reason, count in gate_counter.most_common()
        ],
        "symbol_dry_run_summary": symbol_rows,
        "quick_read_summary": {
            "top_symbols": [row["symbol"] for row in symbol_rows[:5]],
            "top_gate_reasons": [
                {"gate_reason": gate_reason, "count": count}
                for gate_reason, count in gate_counter.most_common(5)
            ],
            "overlay_candidates": [
                {
                    "symbol": _coerce_text(row.get("symbol")),
                    "target_multiplier": _coerce_float(row.get("target_multiplier")),
                    "size_action": _coerce_text(row.get("size_action")),
                }
                for row in overlay_candidates[:5]
            ],
        },
    }


def write_profitability_operations_p7_guarded_size_overlay_dry_run_review(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    entry_decisions_path: Path = DEFAULT_ENTRY_DECISIONS_PATH,
    overlay_path: Path = DEFAULT_OVERLAY_PATH,
    tail: int = 5000,
    now: datetime | None = None,
) -> dict[str, Any]:
    payload = build_profitability_operations_p7_guarded_size_overlay_dry_run_review(
        entry_decisions_path=entry_decisions_path,
        overlay_path=overlay_path,
        tail=tail,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p7_guarded_size_overlay_dry_run_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p7_guarded_size_overlay_dry_run_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p7_guarded_size_overlay_dry_run_latest.md"

    latest_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = list(payload["symbol_dry_run_summary"][0].keys()) if payload["symbol_dry_run_summary"] else [
        "symbol",
        "row_count",
        "matched_count",
        "top_gate_reason",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(payload["symbol_dry_run_summary"])

    summary = payload["overall_summary"]
    lines = [
        "# Profitability / Operations P7 Guarded Size Overlay Dry-Run Review",
        "",
        f"- `report_version`: `{payload['report_version']}`",
        f"- `generated_at`: `{payload['generated_at']}`",
        f"- `entry_decision_row_count`: `{summary['entry_decision_row_count']}`",
        f"- `p7_schema_present`: `{summary['p7_schema_present']}`",
        f"- `p7_trace_row_count`: `{summary['p7_trace_row_count']}`",
        f"- `review_state`: `{summary['review_state']}`",
        f"- `recommended_next_step`: `{summary['recommended_next_step']}`",
        "",
        "## Top Symbols",
    ]
    if payload["symbol_dry_run_summary"]:
        for row in payload["symbol_dry_run_summary"][:5]:
            lines.append(
                f"- `{row['symbol']}` rows={row['row_count']} matched={row['matched_count']} gate={row['top_gate_reason']}"
            )
    else:
        lines.append("- (none)")
    latest_markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "p7_trace_row_count": summary["p7_trace_row_count"],
        "review_state": summary["review_state"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--entry-decisions-path", type=Path, default=DEFAULT_ENTRY_DECISIONS_PATH)
    parser.add_argument("--overlay-path", type=Path, default=DEFAULT_OVERLAY_PATH)
    parser.add_argument("--tail", type=int, default=5000)
    args = parser.parse_args()

    result = write_profitability_operations_p7_guarded_size_overlay_dry_run_review(
        output_dir=args.output_dir,
        entry_decisions_path=args.entry_decisions_path,
        overlay_path=args.overlay_path,
        tail=args.tail,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
