from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_FORENSIC_TABLE_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b3_forensic_table_latest.json"
)
OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
REPORT_VERSION = "r0_b4_family_clustering_v1"


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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _classify_forensic_family(row: dict[str, Any]) -> tuple[str, str, str]:
    linkage_quality = _coerce_text(row.get("linkage_quality"))
    alignment = _coerce_text(row.get("entry_row_alignment_label"))
    stage = _coerce_text(row.get("consumer_check_stage")).upper()
    blocked_by = _coerce_text(row.get("blocked_by"))
    observe_reason = _coerce_text(row.get("observe_reason")).lower()
    suspicious_runtime = bool(row.get("suspicious_exact_runtime_linkage", False))
    decision_gap = _safe_float(row.get("decision_entry_gap_sec"), 0.0)
    resolved_pnl = _safe_float(row.get("resolved_pnl"), 0.0)
    hold_seconds = _safe_float(row.get("hold_seconds"), 0.0)

    if linkage_quality == "coverage_gap":
        return (
            "decision_log_coverage_gap",
            "B1/B2 sample은 있지만 대응 decision row coverage가 부족하다",
            "high",
        )
    if suspicious_runtime or linkage_quality == "suspicious_exact_runtime_linkage":
        return (
            "runtime_linkage_integrity_gap",
            "generic runtime snapshot key 또는 과도한 decision-entry gap 때문에 exact linkage 신뢰도가 낮다",
            "high",
        )
    if alignment == "unknown":
        return (
            "consumer_stage_misalignment",
            "row alignment를 판단할 최소 entry/consumer 정보가 부족하다",
            "medium",
        )
    if alignment == "row_action_conflict":
        return (
            "consumer_stage_misalignment",
            "row action과 실제 trade direction이 어긋난다",
            "high",
        )
    if alignment == "row_non_entry_outcome":
        return (
            "consumer_stage_misalignment",
            "decision row outcome이 entry를 지지하지 않는다",
            "high",
        )
    if alignment == "row_says_not_ready":
        if stage == "BLOCKED":
            return (
                "consumer_stage_misalignment",
                "consumer stage가 BLOCKED인데 실제 adverse trade sample과 연결된다",
                "high",
            )
        if stage == "PROBE":
            return (
                "probe_promoted_too_early",
                "probe 단계 또는 probe-ready 미만인데 trade가 열린 듯 보인다",
                "high",
            )
        if blocked_by:
            return (
                "guard_leak",
                "blocked_by가 존재하는데도 trade sample과 연결된다",
                "high",
            )
        if "confirm" in observe_reason:
            return (
                "confirm_quality_too_weak",
                "confirm 계열 문맥이지만 ready/entry 정렬이 약하다",
                "medium",
            )
        return (
            "consumer_stage_misalignment",
            "row가 not-ready인데 consumer/entry 정렬이 분명하지 않다",
            "medium",
        )
    if alignment == "row_borderline_probe":
        return (
            "probe_promoted_too_early",
            "probe 경계 구간에서 entry가 너무 빨리 열린 후보로 보인다",
            "medium",
        )
    if alignment == "row_supports_entry" and resolved_pnl < 0.0 and hold_seconds <= 180.0:
        return (
            "exit_not_entry_issue",
            "entry row는 지지되지만 짧은 보유 손실이라 exit timing 쪽 검토가 필요하다",
            "medium",
        )
    if "confirm" in observe_reason and decision_gap > 60.0:
        return (
            "confirm_quality_too_weak",
            "confirm 계열 문맥이지만 timing gap이 커서 실제 confirm 품질이 의심된다",
            "low",
        )
    return (
        "unclassified",
        "현재 규칙으로는 명확한 반복 family로 묶이지 않는다",
        "low",
    )


def _family_context_key(row: dict[str, Any], family: str) -> str:
    parts = [
        family,
        f"stage={_coerce_text(row.get('consumer_check_stage')).upper() or '-'}",
        f"blocked={_coerce_text(row.get('blocked_by')) or '-'}",
        f"observe={_coerce_text(row.get('observe_reason')) or '-'}",
        f"setup={_coerce_text(row.get('setup_id')) or '-'}",
    ]
    return "|".join(parts)


def build_actual_entry_forensic_family_report(
    *,
    forensic_table_report_path: Path = DEFAULT_FORENSIC_TABLE_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    forensic_table_report = _load_json(forensic_table_report_path)
    forensic_rows = list(forensic_table_report.get("forensic_rows", []) or [])

    classified_rows: list[dict[str, Any]] = []
    rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    family_counts: Counter[str] = Counter()

    for row in forensic_rows:
        family, family_reason, family_confidence = _classify_forensic_family(row)
        context_key = _family_context_key(row, family)
        classified = {
            **row,
            "forensic_family": family,
            "forensic_family_reason": family_reason,
            "forensic_family_confidence": family_confidence,
            "forensic_family_context_key": context_key,
        }
        classified_rows.append(classified)
        rows_by_family[family].append(classified)
        family_counts[family] += 1

    family_groups: list[dict[str, Any]] = []
    for family, rows in sorted(rows_by_family.items(), key=lambda item: (-len(item[1]), item[0])):
        sorted_rows = sorted(
            rows,
            key=lambda row: (
                -_safe_float(row.get("priority_score"), 0.0),
                _safe_float(row.get("resolved_pnl"), 0.0),
                int(_safe_float(row.get("sample_rank"), 0)),
            ),
        )
        representative = sorted_rows[0]
        family_groups.append(
            {
                "family": family,
                "count": int(len(rows)),
                "confidence_levels": dict(Counter(_coerce_text(row.get("forensic_family_confidence")) for row in rows).most_common()),
                "linkage_quality_counts": dict(
                    Counter(_coerce_text(row.get("linkage_quality")) for row in rows).most_common()
                ),
                "alignment_counts": dict(
                    Counter(_coerce_text(row.get("entry_row_alignment_label")) for row in rows).most_common()
                ),
                "top_symbols": dict(Counter(_coerce_text(row.get("symbol")) for row in rows).most_common(5)),
                "top_setups": dict(Counter(_coerce_text(row.get("setup_id")) for row in rows).most_common(5)),
                "top_blocked_by": dict(Counter(_coerce_text(row.get("blocked_by")) for row in rows).most_common(5)),
                "top_stages": dict(Counter(_coerce_text(row.get("consumer_check_stage")) for row in rows).most_common(5)),
                "top_observe_reasons": dict(Counter(_coerce_text(row.get("observe_reason")) for row in rows).most_common(5)),
                "context_counts": dict(
                    Counter(_coerce_text(row.get("forensic_family_context_key")) for row in rows).most_common(5)
                ),
                "representative_sample_rank": int(_safe_float(representative.get("sample_rank"), 0)),
                "representative_ticket": int(_safe_float(representative.get("ticket"), 0)),
                "representative_symbol": _coerce_text(representative.get("symbol")),
                "representative_setup_id": _coerce_text(representative.get("setup_id")),
                "representative_reason": _coerce_text(representative.get("forensic_family_reason")),
                "sample_ranks": [int(_safe_float(row.get("sample_rank"), 0)) for row in sorted_rows],
            }
        )

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "forensic_table_report_path": str(forensic_table_report_path),
        "summary": {
            "row_count": int(len(classified_rows)),
            "family_count": int(len(family_groups)),
            "repeat_families": int(sum(1 for group in family_groups if int(group["count"]) >= 2)),
        },
        "family_counts": dict(family_counts.most_common()),
        "family_groups": family_groups,
        "classified_rows": classified_rows,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("summary", {}) or {})
    lines = [
        "# R0-B4 Family Clustering",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- family_count: `{summary.get('family_count', 0)}`",
        f"- repeat_families: `{summary.get('repeat_families', 0)}`",
        "",
        "## Family Counts",
    ]
    family_counts = dict(report.get("family_counts", {}) or {})
    if family_counts:
        for key, value in family_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Family Groups"])
    for group in list(report.get("family_groups", []) or [])[:12]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"family={group.get('family', '')}",
                    f"count={group.get('count', 0)}",
                    f"rep_rank={group.get('representative_sample_rank', 0)}",
                    f"rep_ticket={group.get('representative_ticket', 0)}",
                    f"rep_symbol={group.get('representative_symbol', '')}",
                    f"rep_setup={group.get('representative_setup_id', '')}",
                    f"reason={group.get('representative_reason', '')}",
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_actual_entry_forensic_family_report(
    *,
    forensic_table_report_path: Path = DEFAULT_FORENSIC_TABLE_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_actual_entry_forensic_family_report(
        forensic_table_report_path=forensic_table_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "r0_b4_family_clustering_latest.json"
    latest_csv = output_dir / "r0_b4_family_clustering_latest.csv"
    latest_md = output_dir / "r0_b4_family_clustering_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report.get("classified_rows", []) or []).to_csv(latest_csv, index=False, encoding="utf-8-sig")
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forensic-table-report", type=str, default=str(DEFAULT_FORENSIC_TABLE_REPORT))
    parser.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    args = parser.parse_args(argv)
    result = write_actual_entry_forensic_family_report(
        forensic_table_report_path=Path(args.forensic_table_report),
        output_dir=Path(args.output_dir),
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
                "family_count": summary.get("family_count", 0),
                "repeat_families": summary.get("repeat_families", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
