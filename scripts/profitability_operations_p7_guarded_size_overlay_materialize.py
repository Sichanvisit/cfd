from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p7_guarded_size_overlay_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_P7_COUNTERFACTUAL_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p7_counterfactual_latest.json"


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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_profitability_operations_p7_guarded_size_overlay_materialization(
    *,
    p7_counterfactual_path: Path = DEFAULT_P7_COUNTERFACTUAL_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    p7_payload = _read_json(p7_counterfactual_path)
    proposal_rows = p7_payload.get("guarded_application_queue", []) or []

    by_symbol: dict[str, dict[str, Any]] = {}
    for row in proposal_rows:
        row_local = dict(row or {})
        if _coerce_text(row_local.get("proposal_type")) != "size_overlay_guarded_apply":
            continue
        if _coerce_text(row_local.get("recommendation_state")) != "guarded_apply_candidate":
            continue
        symbol = _coerce_text(row_local.get("symbol")).upper()
        if not symbol:
            continue
        candidate = {
            "symbol": symbol,
            "scene_key": _coerce_text(row_local.get("scene_key")) or symbol,
            "setup_key": _coerce_text(row_local.get("setup_key")),
            "regime_key": _coerce_text(row_local.get("regime_key")),
            "health_state": _coerce_text(row_local.get("health_state")),
            "size_action": _coerce_text(row_local.get("size_action")),
            "target_multiplier": round(_coerce_float(row_local.get("size_multiplier"), 1.0), 4),
            "coverage_state": _coerce_text(row_local.get("coverage_state")),
            "top_alert_type": _coerce_text(row_local.get("top_alert_type")),
            "candidate_type": _coerce_text(row_local.get("candidate_type")),
            "evidence_count": int(_coerce_float(row_local.get("evidence_count"), 0.0)),
            "priority_score": round(_coerce_float(row_local.get("priority_score"), 0.0), 4),
            "gate_reason": _coerce_text(row_local.get("gate_reason")),
            "recommendation_state": _coerce_text(row_local.get("recommendation_state")),
            "max_change_suggestion": _coerce_text(row_local.get("max_change_suggestion")),
            "rationale": _coerce_text(row_local.get("rationale")),
            "proposal_source": "P7",
        }
        previous = by_symbol.get(symbol)
        if previous and float(previous.get("priority_score", 0.0)) >= float(candidate["priority_score"]):
            continue
        by_symbol[symbol] = candidate

    candidates = sorted(
        by_symbol.values(),
        key=lambda item: (-float(item.get("priority_score", 0.0)), item.get("symbol", "")),
    )

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "p7_counterfactual_path": str(p7_counterfactual_path),
            "p7_report_version": _coerce_text(p7_payload.get("report_version")),
        },
        "overall_summary": {
            "candidate_count": len(candidates),
            "symbol_count": len(candidates),
            "source_guarded_apply_count": len(proposal_rows),
            "top_symbol": candidates[0]["symbol"] if candidates else "",
        },
        "guarded_size_overlay_candidates": candidates,
        "guarded_size_overlay_by_symbol": {row["symbol"]: row for row in candidates},
        "quick_read_summary": {
            "top_symbols": [row["symbol"] for row in candidates[:5]],
            "top_actions": [
                {
                    "symbol": row["symbol"],
                    "target_multiplier": row["target_multiplier"],
                    "size_action": row["size_action"],
                }
                for row in candidates[:5]
            ],
        },
    }


def write_profitability_operations_p7_guarded_size_overlay_materialization(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    p7_counterfactual_path: Path = DEFAULT_P7_COUNTERFACTUAL_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    payload = build_profitability_operations_p7_guarded_size_overlay_materialization(
        p7_counterfactual_path=p7_counterfactual_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p7_guarded_size_overlay_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p7_guarded_size_overlay_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p7_guarded_size_overlay_latest.md"

    latest_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = list(payload["guarded_size_overlay_candidates"][0].keys()) if payload["guarded_size_overlay_candidates"] else [
        "symbol",
        "target_multiplier",
        "size_action",
        "health_state",
        "gate_reason",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(payload["guarded_size_overlay_candidates"])

    summary = payload["overall_summary"]
    markdown_lines = [
        "# Profitability / Operations P7 Guarded Size Overlay",
        "",
        f"- `report_version`: `{payload['report_version']}`",
        f"- `generated_at`: `{payload['generated_at']}`",
        f"- `candidate_count`: `{summary['candidate_count']}`",
        f"- `symbol_count`: `{summary['symbol_count']}`",
        "",
        "## Top Overlay Candidates",
    ]
    if payload["guarded_size_overlay_candidates"]:
        for row in payload["guarded_size_overlay_candidates"][:5]:
            markdown_lines.append(
                f"- `{row['symbol']}` -> `{row['target_multiplier']}` ({row['size_action']}, {row['health_state']})"
            )
    else:
        markdown_lines.append("- (none)")
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "candidate_count": summary["candidate_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--p7-counterfactual-path", type=Path, default=DEFAULT_P7_COUNTERFACTUAL_PATH)
    args = parser.parse_args()

    result = write_profitability_operations_p7_guarded_size_overlay_materialization(
        output_dir=args.output_dir,
        p7_counterfactual_path=args.p7_counterfactual_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
