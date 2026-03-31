from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_FAMILY_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b4_family_clustering_latest.json"
)
OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
REPORT_VERSION = "r0_b5_action_candidates_v1"

ENTRY_SERVICE = str(ROOT / "backend" / "services" / "entry_service.py")
ENTRY_TRY_OPEN = str(ROOT / "backend" / "services" / "entry_try_open_entry.py")
CONSUMER_CHECK_STATE = str(ROOT / "backend" / "services" / "consumer_check_state.py")
STORAGE_COMPACTION = str(ROOT / "backend" / "services" / "storage_compaction.py")
ENTRY_ENGINES = str(ROOT / "backend" / "services" / "entry_engines.py")
EXIT_SERVICE = str(ROOT / "backend" / "services" / "exit_service.py")


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        text = _coerce_text(value)
        if not text:
            return int(default)
        return int(float(text))
    except Exception:
        return int(default)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 9)


def _template_for_family(family: str) -> dict[str, Any]:
    templates: dict[str, dict[str, Any]] = {
        "runtime_linkage_integrity_gap": {
            "priority": "critical",
            "candidate_kind": "infrastructure_integrity",
            "suspected_issue_code": "runtime_snapshot_key_reuse",
            "suspected_issue": "generic runtime_snapshot_key가 재사용되며 exact linkage를 과신하게 만든다",
            "suspected_owners": [STORAGE_COMPACTION, ENTRY_ENGINES],
            "next_action": "runtime_snapshot_key 생성/보존 규칙을 점검하고 generic anchor_value=0.0 exact 매칭은 downgrade 또는 manual-review 대상으로 강등한다",
        },
        "decision_log_coverage_gap": {
            "priority": "critical",
            "candidate_kind": "observability_retention",
            "suspected_issue_code": "decision_log_retention_gap",
            "suspected_issue": "closed trade는 남았지만 대응 decision row coverage가 비어 forensic join이 끊긴다",
            "suspected_owners": [ENTRY_ENGINES, STORAGE_COMPACTION],
            "next_action": "active/legacy entry_decisions retention과 rollover coverage를 점검하고 최근 adverse sample window를 잇는 보존 기준을 강화한다",
        },
        "consumer_stage_misalignment": {
            "priority": "high",
            "candidate_kind": "entry_consumer_contract",
            "suspected_issue_code": "consumer_entry_contract_drift",
            "suspected_issue": "consumer_check_stage 또는 entry_ready 판단과 실제 trade open 사실이 어긋난다",
            "suspected_owners": [CONSUMER_CHECK_STATE, ENTRY_SERVICE],
            "next_action": "consumer stage와 entry gate의 불변조건을 비교하고 BLOCKED/OBSERVE row가 open path로 이어지는지 audit logging을 추가한다",
        },
        "guard_leak": {
            "priority": "high",
            "candidate_kind": "entry_guard_enforcement",
            "suspected_issue_code": "blocked_by_enforcement_gap",
            "suspected_issue": "blocked_by가 존재하는 row가 실제 adverse trade와 연결되며 guard enforcement 누수가 의심된다",
            "suspected_owners": [ENTRY_SERVICE, ENTRY_TRY_OPEN],
            "next_action": "blocked_by와 consumer block 결과가 실제 open path에서 hard-stop으로 적용되는지 검증하고 누수 경로를 차단한다",
        },
        "probe_promoted_too_early": {
            "priority": "high",
            "candidate_kind": "promotion_gate",
            "suspected_issue_code": "probe_to_ready_promotion_too_permissive",
            "suspected_issue": "probe 단계에서 confirm/ready 승격 또는 open 허용이 너무 이르게 일어난다",
            "suspected_owners": [ENTRY_SERVICE, ENTRY_TRY_OPEN],
            "next_action": "probe_plan_ready, consumer stage, quick trace를 함께 보는 승격 불변조건을 강화하고 probe 상태 open을 줄인다",
        },
        "confirm_quality_too_weak": {
            "priority": "high",
            "candidate_kind": "confirm_quality",
            "suspected_issue_code": "confirm_quality_threshold_weak",
            "suspected_issue": "confirm 계열 문맥이지만 실제 persistence나 quality가 약해 false-ready가 발생한다",
            "suspected_owners": [ENTRY_SERVICE, CONSUMER_CHECK_STATE],
            "next_action": "confirm 계열 observe_reason의 quality threshold와 consumer display/entry readiness 경계를 재점검한다",
        },
        "exit_not_entry_issue": {
            "priority": "medium",
            "candidate_kind": "exit_timing",
            "suspected_issue_code": "exit_management_too_tight",
            "suspected_issue": "entry row는 지지되지만 짧은 손실 청산 패턴이라 exit management가 더 큰 문제일 수 있다",
            "suspected_owners": [EXIT_SERVICE, ENTRY_TRY_OPEN],
            "next_action": "entry는 유지하되 early cut / immediate protection / hold profile의 과민 반응 여부를 분리 분석한다",
        },
        "unclassified": {
            "priority": "low",
            "candidate_kind": "manual_review",
            "suspected_issue_code": "manual_bucket_review",
            "suspected_issue": "현재 규칙으로는 명확한 반복 family로 묶이지 않는다",
            "suspected_owners": [ENTRY_SERVICE],
            "next_action": "sample 수를 더 모으거나 family 규칙을 보강한다",
        },
    }
    return dict(templates.get(family, templates["unclassified"]))


def build_actual_entry_forensic_action_report(
    *,
    family_report_path: Path = DEFAULT_FAMILY_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    family_report = _load_json(family_report_path)
    family_groups = list(family_report.get("family_groups", []) or [])

    action_candidates: list[dict[str, Any]] = []
    for group in family_groups:
        family = _coerce_text(group.get("family"))
        template = _template_for_family(family)
        count = _safe_int(group.get("count"))
        top_blocked_by = dict(group.get("top_blocked_by", {}) or {})
        top_stages = dict(group.get("top_stages", {}) or {})
        top_observe_reasons = dict(group.get("top_observe_reasons", {}) or {})
        context_counts = dict(group.get("context_counts", {}) or {})
        priority = _coerce_text(template.get("priority"))
        candidate = {
            "rank": 0,
            "family": family,
            "priority": priority,
            "candidate_kind": _coerce_text(template.get("candidate_kind")),
            "suspected_issue_code": _coerce_text(template.get("suspected_issue_code")),
            "suspected_issue": _coerce_text(template.get("suspected_issue")),
            "suspected_owners": list(template.get("suspected_owners", []) or []),
            "suspected_owners_text": " | ".join(list(template.get("suspected_owners", []) or [])),
            "next_action": _coerce_text(template.get("next_action")),
            "evidence_count": count,
            "representative_sample_rank": _safe_int(group.get("representative_sample_rank")),
            "representative_ticket": _safe_int(group.get("representative_ticket")),
            "representative_symbol": _coerce_text(group.get("representative_symbol")),
            "representative_setup_id": _coerce_text(group.get("representative_setup_id")),
            "representative_reason": _coerce_text(group.get("representative_reason")),
            "top_blocked_by": top_blocked_by,
            "top_stages": top_stages,
            "top_observe_reasons": top_observe_reasons,
            "context_counts": context_counts,
            "sample_ranks": list(group.get("sample_ranks", []) or []),
            "rationale": (
                f"family={family}, count={count}, "
                f"top_stage={next(iter(top_stages.keys()), '-')}, "
                f"top_blocked_by={next(iter(top_blocked_by.keys()), '-')}, "
                f"top_observe_reason={next(iter(top_observe_reasons.keys()), '-')}"
            ),
        }
        action_candidates.append(candidate)

    action_candidates.sort(
        key=lambda item: (
            _priority_rank(_coerce_text(item.get("priority"))),
            -_safe_int(item.get("evidence_count")),
            _coerce_text(item.get("family")),
        )
    )
    for rank, candidate in enumerate(action_candidates, start=1):
        candidate["rank"] = rank

    summary = {
        "candidate_count": int(len(action_candidates)),
        "critical_candidates": int(sum(1 for row in action_candidates if row["priority"] == "critical")),
        "high_candidates": int(sum(1 for row in action_candidates if row["priority"] == "high")),
        "medium_candidates": int(sum(1 for row in action_candidates if row["priority"] == "medium")),
        "low_candidates": int(sum(1 for row in action_candidates if row["priority"] == "low")),
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "family_report_path": str(family_report_path),
        "summary": summary,
        "action_candidates": action_candidates,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("summary", {}) or {})
    lines = [
        "# R0-B5 Action Candidates",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- critical_candidates: `{summary.get('critical_candidates', 0)}`",
        f"- high_candidates: `{summary.get('high_candidates', 0)}`",
        "",
        "| rank | family | priority | suspected owner | suspected issue | next action | evidence_count |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in list(report.get("action_candidates", []) or []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("rank", 0)),
                    _coerce_text(row.get("family")),
                    _coerce_text(row.get("priority")),
                    _coerce_text(row.get("suspected_owners_text")),
                    _coerce_text(row.get("suspected_issue")),
                    _coerce_text(row.get("next_action")),
                    str(_safe_int(row.get("evidence_count"))),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_actual_entry_forensic_action_report(
    *,
    family_report_path: Path = DEFAULT_FAMILY_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_actual_entry_forensic_action_report(
        family_report_path=family_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "r0_b5_action_candidates_latest.json"
    latest_csv = output_dir / "r0_b5_action_candidates_latest.csv"
    latest_md = output_dir / "r0_b5_action_candidates_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report.get("action_candidates", []) or []).to_csv(latest_csv, index=False, encoding="utf-8-sig")
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family-report", type=str, default=str(DEFAULT_FAMILY_REPORT))
    parser.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    args = parser.parse_args(argv)
    result = write_actual_entry_forensic_action_report(
        family_report_path=Path(args.family_report),
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
                "candidate_count": summary.get("candidate_count", 0),
                "critical_candidates": summary.get("critical_candidates", 0),
                "high_candidates": summary.get("high_candidates", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
