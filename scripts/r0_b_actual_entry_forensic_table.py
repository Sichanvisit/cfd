from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_SAMPLE_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b1_adverse_entry_samples_latest.json"
)
DEFAULT_MATCH_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b2_decision_row_matches_latest.json"
)
OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
REPORT_VERSION = "r0_b3_forensic_table_v1"
_ENTERED_OUTCOMES = {"entered", "open", "filled", "submitted", "executed"}
_TRUE_SET = {"1", "true", "yes", "y", "on"}
_FALSE_SET = {"0", "false", "no", "n", "off"}


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        if not text:
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except Exception:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_bool(value: Any) -> bool | None:
    text = _coerce_text(value).lower()
    if not text:
        return None
    if text in _TRUE_SET:
        return True
    if text in _FALSE_SET:
        return False
    return None


def _normalize_signal_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _coerce_text(value)
    if not text:
        return []
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    return [text]


def _build_sample_index(sample_report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(rank): sample
        for rank, sample in enumerate(list(sample_report.get("top_samples", []) or []), start=1)
    }


def _decision_entry_gap_sec(match_row: dict[str, Any]) -> float | None:
    open_dt = _parse_dt(match_row.get("open_time"))
    decision_dt = _parse_dt(match_row.get("matched_time"))
    if open_dt is None or decision_dt is None:
        return None
    return round(abs((decision_dt - open_dt).total_seconds()), 3)


def _is_generic_runtime_snapshot_key(value: Any) -> bool:
    text = _coerce_text(value)
    return bool(text.startswith("runtime_signal_row_v1|") and "anchor_value=0.0" in text)


def _classify_linkage_quality(
    *,
    match_status: str,
    match_strategy: str,
    generic_runtime_snapshot_linkage: bool,
    decision_entry_gap_sec: float | None,
    within_decision_log_coverage: bool,
    suspicious_exact_gap_sec: float,
) -> tuple[str, bool, str]:
    if match_status == "unmatched_outside_coverage":
        return ("coverage_gap", False, "low")
    if match_status == "unmatched_no_candidate":
        return ("no_candidate", False, "low")
    if match_status == "fallback":
        return ("fallback_match", False, "medium")
    if match_status == "exact":
        if match_strategy == "exact_runtime_snapshot_key":
            suspicious = bool(
                generic_runtime_snapshot_linkage
                or not within_decision_log_coverage
                or (
                    decision_entry_gap_sec is not None
                    and float(decision_entry_gap_sec) > float(suspicious_exact_gap_sec)
                )
            )
            if suspicious:
                return ("suspicious_exact_runtime_linkage", True, "low")
            return ("runtime_snapshot_exact", False, "medium")
        return ("strong_exact", False, "high")
    return ("unknown", False, "low")


def _entry_row_alignment_label(match_row: dict[str, Any]) -> str:
    match_status = _coerce_text(match_row.get("match_status"))
    if match_status.startswith("unmatched"):
        return "unknown"

    blocked_by = _coerce_text(match_row.get("matched_blocked_by"))
    action_none_reason = _coerce_text(match_row.get("matched_action_none_reason"))
    stage = _coerce_text(match_row.get("matched_consumer_check_stage")).upper()
    consumer_entry_ready = _parse_bool(match_row.get("matched_consumer_check_entry_ready"))
    probe_plan_ready = _parse_bool(match_row.get("matched_probe_plan_ready"))
    matched_action = _coerce_text(match_row.get("matched_action")).upper()
    matched_outcome = _coerce_text(match_row.get("matched_outcome")).lower()
    sample_direction = _coerce_text(match_row.get("direction")).upper()

    if blocked_by or action_none_reason or consumer_entry_ready is False or stage in {"BLOCKED", "OBSERVE"}:
        return "row_says_not_ready"
    if stage == "PROBE" or probe_plan_ready is False:
        return "row_borderline_probe"
    if matched_action and sample_direction and matched_action != sample_direction:
        return "row_action_conflict"
    if matched_outcome and matched_outcome not in _ENTERED_OUTCOMES:
        return "row_non_entry_outcome"
    return "row_supports_entry"


def build_actual_entry_forensic_table_report(
    *,
    sample_report_path: Path = DEFAULT_SAMPLE_REPORT,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    suspicious_exact_gap_sec: float = 300.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sample_report = _load_json(sample_report_path)
    match_report = _load_json(match_report_path)
    sample_by_rank = _build_sample_index(sample_report)

    forensic_rows: list[dict[str, Any]] = []
    linkage_quality_counts: Counter[str] = Counter()
    alignment_counts: Counter[str] = Counter()

    for match_row in list(match_report.get("matches", []) or []):
        sample_rank = int(_safe_float(match_row.get("sample_rank"), 0))
        sample = dict(sample_by_rank.get(sample_rank, {}) or {})
        match_status = _coerce_text(match_row.get("match_status"))
        match_strategy = _coerce_text(match_row.get("match_strategy"))
        within_decision_log_coverage = bool(match_row.get("within_decision_log_coverage", False))
        decision_entry_gap_sec = _decision_entry_gap_sec(match_row)
        generic_runtime_snapshot_linkage = _is_generic_runtime_snapshot_key(
            match_row.get("matched_runtime_snapshot_key")
        )
        linkage_quality, suspicious_exact_runtime_linkage, forensic_confidence = _classify_linkage_quality(
            match_status=match_status,
            match_strategy=match_strategy,
            generic_runtime_snapshot_linkage=generic_runtime_snapshot_linkage,
            decision_entry_gap_sec=decision_entry_gap_sec,
            within_decision_log_coverage=within_decision_log_coverage,
            suspicious_exact_gap_sec=float(suspicious_exact_gap_sec),
        )
        alignment_label = _entry_row_alignment_label(match_row)
        needs_manual_review = bool(
            suspicious_exact_runtime_linkage
            or linkage_quality in {"coverage_gap", "no_candidate"}
            or alignment_label in {"row_says_not_ready", "row_borderline_probe", "row_action_conflict"}
        )

        normalized_action = _coerce_text(match_row.get("matched_action")).upper() or _coerce_text(
            match_row.get("direction")
        ).upper()
        normalized_setup_id = _coerce_text(match_row.get("matched_setup_id")) or _coerce_text(
            match_row.get("entry_setup_id")
        ) or _coerce_text(sample.get("entry_setup_id"))
        adverse_signals = _normalize_signal_list(match_row.get("sample_adverse_signals") or sample.get("adverse_signals"))
        forensic_row = {
            "sample_rank": sample_rank,
            "ticket": int(_safe_float(match_row.get("ticket"), 0)),
            "symbol": _coerce_text(match_row.get("symbol")).upper(),
            "time": _coerce_text(match_row.get("matched_time")) or _coerce_text(match_row.get("open_time")),
            "decision_time": _coerce_text(match_row.get("matched_time")),
            "entry_time": _coerce_text(match_row.get("open_time")),
            "close_time": _coerce_text(match_row.get("close_time")),
            "action": normalized_action,
            "outcome": _coerce_text(match_row.get("matched_outcome")) or "trade_closed_sample",
            "setup_id": normalized_setup_id,
            "observe_reason": _coerce_text(match_row.get("matched_observe_reason")),
            "blocked_by": _coerce_text(match_row.get("matched_blocked_by")),
            "action_none_reason": _coerce_text(match_row.get("matched_action_none_reason")),
            "quick_trace_state": _coerce_text(match_row.get("matched_quick_trace_state")),
            "quick_trace_reason": _coerce_text(match_row.get("matched_quick_trace_reason")),
            "probe_plan_ready": _coerce_text(match_row.get("matched_probe_plan_ready")),
            "probe_plan_reason": _coerce_text(match_row.get("matched_probe_plan_reason")),
            "consumer_check_stage": _coerce_text(match_row.get("matched_consumer_check_stage")),
            "consumer_check_entry_ready": _coerce_text(match_row.get("matched_consumer_check_entry_ready")),
            "r0_non_action_family": _coerce_text(match_row.get("matched_r0_non_action_family")),
            "r0_semantic_runtime_state": _coerce_text(match_row.get("matched_r0_semantic_runtime_state")),
            "decision_row_key": _coerce_text(match_row.get("matched_decision_row_key"))
            or _coerce_text(match_row.get("sample_decision_row_key"))
            or _coerce_text(sample.get("decision_row_key")),
            "runtime_snapshot_key": _coerce_text(match_row.get("matched_runtime_snapshot_key"))
            or _coerce_text(match_row.get("sample_runtime_snapshot_key"))
            or _coerce_text(sample.get("runtime_snapshot_key")),
            "trade_link_key": _coerce_text(match_row.get("matched_trade_link_key"))
            or _coerce_text(match_row.get("sample_trade_link_key"))
            or _coerce_text(sample.get("trade_link_key")),
            "replay_row_key": _coerce_text(match_row.get("matched_replay_row_key"))
            or _coerce_text(match_row.get("sample_replay_row_key"))
            or _coerce_text(sample.get("replay_row_key")),
            "match_status": match_status,
            "match_strategy": match_strategy,
            "linkage_quality": linkage_quality,
            "forensic_confidence": forensic_confidence,
            "within_decision_log_coverage": within_decision_log_coverage,
            "decision_entry_gap_sec": decision_entry_gap_sec,
            "generic_runtime_snapshot_linkage": generic_runtime_snapshot_linkage,
            "suspicious_exact_runtime_linkage": suspicious_exact_runtime_linkage,
            "needs_manual_review": needs_manual_review,
            "entry_row_alignment_label": alignment_label,
            "matched_source": _coerce_text(match_row.get("matched_source")),
            "matched_score": round(_safe_float(match_row.get("match_score")), 4),
            "matched_time_delta_sec": (
                round(_safe_float(match_row.get("time_delta_sec")), 3)
                if _coerce_text(match_row.get("time_delta_sec"))
                else None
            ),
            "resolved_pnl": round(_safe_float(match_row.get("resolved_pnl") or sample.get("resolved_pnl")), 4),
            "hold_seconds": round(_safe_float(match_row.get("hold_seconds") or sample.get("hold_seconds")), 3),
            "priority_score": round(_safe_float(match_row.get("priority_score") or sample.get("priority_score")), 4),
            "adverse_signals": adverse_signals,
            "forensic_ready": bool(match_row.get("forensic_ready", sample.get("forensic_ready", False))),
            "has_any_linkage_key": bool(sample.get("has_any_linkage_key", False)),
            "decision_winner": _coerce_text(sample.get("decision_winner")),
            "decision_reason": _coerce_text(sample.get("decision_reason")),
            "final_outcome": _coerce_text(sample.get("final_outcome")),
            "loss_quality_label": _coerce_text(sample.get("loss_quality_label")),
            "loss_quality_reason": _coerce_text(sample.get("loss_quality_reason")),
            "entry_wait_state": _coerce_text(sample.get("entry_wait_state"))
            or _coerce_text(match_row.get("matched_entry_wait_state")),
            "exit_wait_state": _coerce_text(sample.get("exit_wait_state")),
            "net_pnl_after_cost": round(_safe_float(sample.get("net_pnl_after_cost")), 4),
            "profit": round(_safe_float(sample.get("profit")), 4),
            "points": round(_safe_float(sample.get("points")), 4),
        }
        linkage_quality_counts[linkage_quality] += 1
        alignment_counts[alignment_label] += 1
        forensic_rows.append(forensic_row)

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "sample_report_path": str(sample_report_path),
        "match_report_path": str(match_report_path),
        "suspicious_exact_gap_sec": float(suspicious_exact_gap_sec),
        "summary": {
            "row_count": int(len(forensic_rows)),
            "manual_review_rows": int(sum(1 for row in forensic_rows if row["needs_manual_review"])),
            "suspicious_exact_runtime_linkage_rows": int(
                sum(1 for row in forensic_rows if row["suspicious_exact_runtime_linkage"])
            ),
            "coverage_gap_rows": int(sum(1 for row in forensic_rows if row["linkage_quality"] == "coverage_gap")),
            "strong_exact_rows": int(sum(1 for row in forensic_rows if row["linkage_quality"] == "strong_exact")),
            "fallback_rows": int(sum(1 for row in forensic_rows if row["linkage_quality"] == "fallback_match")),
        },
        "linkage_quality_counts": dict(linkage_quality_counts.most_common()),
        "entry_row_alignment_counts": dict(alignment_counts.most_common()),
        "forensic_rows": forensic_rows,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("summary", {}) or {})
    lines = [
        "# R0-B3 Forensic Table",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- manual_review_rows: `{summary.get('manual_review_rows', 0)}`",
        f"- suspicious_exact_runtime_linkage_rows: `{summary.get('suspicious_exact_runtime_linkage_rows', 0)}`",
        f"- coverage_gap_rows: `{summary.get('coverage_gap_rows', 0)}`",
        "",
        "## Linkage Quality",
    ]
    linkage_counts = dict(report.get("linkage_quality_counts", {}) or {})
    if linkage_counts:
        for key, value in linkage_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Entry Row Alignment"])
    alignment_counts = dict(report.get("entry_row_alignment_counts", {}) or {})
    if alignment_counts:
        for key, value in alignment_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Top Manual Review Rows"])
    manual_review_rows = [row for row in list(report.get("forensic_rows", []) or []) if row.get("needs_manual_review")]
    for row in manual_review_rows[:12]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"rank={row.get('sample_rank', 0)}",
                    f"ticket={row.get('ticket', 0)}",
                    f"symbol={row.get('symbol', '')}",
                    f"setup={row.get('setup_id', '')}",
                    f"quality={row.get('linkage_quality', '')}",
                    f"align={row.get('entry_row_alignment_label', '')}",
                    f"gap={row.get('decision_entry_gap_sec', '')}",
                    f"stage={row.get('consumer_check_stage', '')}",
                    f"blocked_by={row.get('blocked_by', '')}",
                    f"observe_reason={row.get('observe_reason', '')}",
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_actual_entry_forensic_table_report(
    *,
    sample_report_path: Path = DEFAULT_SAMPLE_REPORT,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    output_dir: Path = OUT_DIR,
    suspicious_exact_gap_sec: float = 300.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_actual_entry_forensic_table_report(
        sample_report_path=sample_report_path,
        match_report_path=match_report_path,
        suspicious_exact_gap_sec=suspicious_exact_gap_sec,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "r0_b3_forensic_table_latest.json"
    latest_csv = output_dir / "r0_b3_forensic_table_latest.csv"
    latest_md = output_dir / "r0_b3_forensic_table_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report.get("forensic_rows", []) or []).to_csv(latest_csv, index=False, encoding="utf-8-sig")
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-report", type=str, default=str(DEFAULT_SAMPLE_REPORT))
    parser.add_argument("--match-report", type=str, default=str(DEFAULT_MATCH_REPORT))
    parser.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    parser.add_argument("--suspicious-exact-gap-sec", type=float, default=300.0)
    args = parser.parse_args(argv)
    result = write_actual_entry_forensic_table_report(
        sample_report_path=Path(args.sample_report),
        match_report_path=Path(args.match_report),
        output_dir=Path(args.output_dir),
        suspicious_exact_gap_sec=float(args.suspicious_exact_gap_sec),
    )
    summary = dict(result["report"].get("summary", {}) or {})
    print(
        json.dumps(
            {
                "ok": True,
                "latest_json_path": result["latest_json_path"],
                "latest_csv_path": result["latest_csv_path"],
                "latest_markdown_path": result["latest_markdown_path"],
                "row_count": summary.get("row_count", 0),
                "manual_review_rows": summary.get("manual_review_rows", 0),
                "suspicious_exact_runtime_linkage_rows": summary.get(
                    "suspicious_exact_runtime_linkage_rows", 0
                ),
                "coverage_gap_rows": summary.get("coverage_gap_rows", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
