"""Rank mismatch families from the manual-vs-heuristic comparison surface."""

from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_FAMILY_RANKING_VERSION = "manual_vs_heuristic_family_ranking_v0"

MANUAL_VS_HEURISTIC_FAMILY_RANKING_COLUMNS = [
    "family_id",
    "miss_type",
    "primary_correction_target",
    "manual_wait_teacher_family",
    "heuristic_wait_family",
    "heuristic_barrier_main_label",
    "case_count",
    "symbol_counts",
    "correction_worthy_case_count",
    "candidate_correction_case_count",
    "freeze_worthy_case_count",
    "hold_for_more_truth_case_count",
    "ready_case_count",
    "avg_frequency_score",
    "avg_severity_score",
    "avg_correction_priority_score",
    "avg_freeze_risk_score",
    "avg_evidence_quality_score",
    "avg_current_rich_reproducibility_score",
    "avg_correction_cost_score",
    "priority_score_total",
    "priority_score_frequency",
    "priority_score_severity",
    "priority_score_evidence",
    "priority_score_reproducibility",
    "priority_score_correction_cost",
    "priority_score_freeze_risk_penalty",
    "top_manual_truth_sources",
    "top_heuristic_sources",
    "top_episode_ids",
    "family_disposition",
    "correction_priority_tier",
    "recommended_next_action",
    "ranking_reason_summary",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(str(value).strip())
    except Exception:
        return float(default)


def load_manual_vs_heuristic_comparison_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _family_disposition(
    *,
    case_count: int,
    correction_worthy_case_count: int,
    freeze_worthy_case_count: int,
    hold_for_more_truth_case_count: int,
    ready_case_count: int,
) -> str:
    if correction_worthy_case_count > 0 and ready_case_count > 0:
        return "correction_candidate"
    if freeze_worthy_case_count >= max(1, ceil(case_count / 2)):
        return "freeze_candidate"
    if hold_for_more_truth_case_count > 0:
        return "collect_more_truth"
    return "casebook_only"


def _priority_tier(
    *,
    family_disposition: str,
    case_count: int,
    avg_priority_score: float,
    candidate_correction_case_count: int,
) -> str:
    if family_disposition == "correction_candidate":
        if case_count >= 2 and avg_priority_score >= 11.0:
            return "P1"
        if avg_priority_score >= 10.0:
            return "P2"
        return "P3"
    if candidate_correction_case_count > 0 and family_disposition != "freeze_candidate":
        return "P3"
    return "hold"


def _recommended_next_action(family_disposition: str, priority_tier: str) -> str:
    if family_disposition == "correction_candidate":
        if priority_tier in {"P1", "P2"}:
            return "edit_rule_now"
        return "review_as_next_family_candidate"
    if family_disposition == "collect_more_truth":
        return "collect_current_rich_truth"
    if family_disposition == "freeze_candidate":
        return "freeze_and_monitor"
    return "keep_as_casebook_only"


def _ranking_reason_summary(
    *,
    family_disposition: str,
    priority_tier: str,
    ready_case_count: int,
    hold_for_more_truth_case_count: int,
    freeze_worthy_case_count: int,
    avg_evidence_quality_score: float,
    avg_reproducibility_score: float,
) -> str:
    if family_disposition == "correction_candidate":
        return (
            f"{priority_tier.lower()}_candidate::ready={ready_case_count}"
            f"::evidence={avg_evidence_quality_score}"
            f"::repro={avg_reproducibility_score}"
        )
    if family_disposition == "collect_more_truth":
        return (
            f"collect_more_truth::hold_cases={hold_for_more_truth_case_count}"
            f"::evidence={avg_evidence_quality_score}"
            f"::repro={avg_reproducibility_score}"
        )
    if family_disposition == "freeze_candidate":
        return (
            f"freeze_candidate::freeze_cases={freeze_worthy_case_count}"
            f"::evidence={avg_evidence_quality_score}"
        )
    return "casebook_only::insufficient_priority_signal"


def build_manual_vs_heuristic_family_ranking(
    comparison: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = comparison.copy() if comparison is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_FAMILY_RANKING_COLUMNS)
        summary = {
            "family_ranking_version": MANUAL_VS_HEURISTIC_FAMILY_RANKING_VERSION,
            "family_count": 0,
            "disposition_counts": {},
            "priority_tier_counts": {},
            "recommended_next_action_counts": {},
            "next_target_family_id": "",
        }
        return empty, summary

    mismatch_like = source[
        source["miss_type"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    if mismatch_like.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_FAMILY_RANKING_COLUMNS)
        summary = {
            "family_ranking_version": MANUAL_VS_HEURISTIC_FAMILY_RANKING_VERSION,
            "family_count": 0,
            "disposition_counts": {},
            "priority_tier_counts": {},
            "recommended_next_action_counts": {},
            "next_target_family_id": "",
        }
        return empty, summary

    group_columns = [
        "miss_type",
        "primary_correction_target",
        "manual_wait_teacher_family",
        "heuristic_wait_family",
        "heuristic_barrier_main_label",
    ]

    rows: list[dict[str, Any]] = []
    for keys, group in mismatch_like.groupby(group_columns, dropna=False, sort=False):
        miss_type, correction_target, manual_family, heuristic_family, heuristic_label = [
            _to_text(value, "none") for value in keys
        ]
        case_count = int(len(group))
        correction_worthy_case_count = int(
            group["correction_worthiness_class"].fillna("").astype(str).eq("correction_worthy").sum()
        )
        candidate_correction_case_count = int(
            group["correction_worthiness_class"]
            .fillna("")
            .astype(str)
            .isin(["correction_worthy", "candidate_correction"])
            .sum()
        )
        freeze_worthy_case_count = int(
            group["freeze_worthiness_class"].fillna("").astype(str).eq("freeze_worthy").sum()
        )
        hold_for_more_truth_case_count = int(
            group["rule_change_readiness"]
            .fillna("")
            .astype(str)
            .isin(["needs_more_recent_truth", "needs_manual_recheck", "insufficient_evidence"])
            .sum()
        )
        ready_case_count = int(
            group["rule_change_readiness"].fillna("").astype(str).eq("ready").sum()
        )
        avg_frequency_score = round(
            group["frequency_score"].apply(_to_float).mean(),
            3,
        )
        avg_severity_score = round(
            group["severity_score"].apply(_to_float).mean(),
            3,
        )
        avg_priority_score = round(
            group["correction_priority_score"].apply(_to_float).mean(),
            3,
        )
        avg_freeze_risk_score = round(
            group["freeze_risk_score"].apply(_to_float).mean(),
            3,
        )
        avg_evidence_quality_score = round(
            group["evidence_quality_score"].apply(_to_float).mean(),
            3,
        )
        avg_reproducibility_score = round(
            group["current_rich_reproducibility_score"].apply(_to_float).mean(),
            3,
        )
        avg_cost_score = round(
            group["correction_cost_score"].apply(_to_float).mean(),
            3,
        )
        priority_score_total = round(
            avg_frequency_score
            + avg_severity_score
            + avg_evidence_quality_score
            + avg_reproducibility_score
            + avg_cost_score
            - avg_freeze_risk_score,
            3,
        )
        family_disposition = _family_disposition(
            case_count=case_count,
            correction_worthy_case_count=correction_worthy_case_count,
            freeze_worthy_case_count=freeze_worthy_case_count,
            hold_for_more_truth_case_count=hold_for_more_truth_case_count,
            ready_case_count=ready_case_count,
        )
        priority_tier = _priority_tier(
            family_disposition=family_disposition,
            case_count=case_count,
            avg_priority_score=avg_priority_score,
            candidate_correction_case_count=candidate_correction_case_count,
        )
        recommended_next_action = _recommended_next_action(family_disposition, priority_tier)
        ranking_reason_summary = _ranking_reason_summary(
            family_disposition=family_disposition,
            priority_tier=priority_tier,
            ready_case_count=ready_case_count,
            hold_for_more_truth_case_count=hold_for_more_truth_case_count,
            freeze_worthy_case_count=freeze_worthy_case_count,
            avg_evidence_quality_score=avg_evidence_quality_score,
            avg_reproducibility_score=avg_reproducibility_score,
        )
        sorted_group = group.sort_values(
            by=["correction_priority_score", "mismatch_severity", "episode_id"],
            ascending=[False, False, True],
            kind="stable",
        )
        family_id = "|".join(
            [
                miss_type or "none",
                correction_target or "none",
                manual_family or "manual_none",
                heuristic_family or "heuristic_none",
                heuristic_label or "label_none",
            ]
        )
        rows.append(
            {
                "family_id": family_id,
                "miss_type": miss_type,
                "primary_correction_target": correction_target,
                "manual_wait_teacher_family": manual_family,
                "heuristic_wait_family": heuristic_family,
                "heuristic_barrier_main_label": heuristic_label,
                "case_count": case_count,
                "symbol_counts": group["symbol"].value_counts(dropna=False).to_dict(),
                "correction_worthy_case_count": correction_worthy_case_count,
                "candidate_correction_case_count": candidate_correction_case_count,
                "freeze_worthy_case_count": freeze_worthy_case_count,
                "hold_for_more_truth_case_count": hold_for_more_truth_case_count,
                "ready_case_count": ready_case_count,
                "avg_frequency_score": avg_frequency_score,
                "avg_severity_score": avg_severity_score,
                "avg_correction_priority_score": avg_priority_score,
                "avg_freeze_risk_score": avg_freeze_risk_score,
                "avg_evidence_quality_score": avg_evidence_quality_score,
                "avg_current_rich_reproducibility_score": avg_reproducibility_score,
                "avg_correction_cost_score": avg_cost_score,
                "priority_score_total": priority_score_total,
                "priority_score_frequency": avg_frequency_score,
                "priority_score_severity": avg_severity_score,
                "priority_score_evidence": avg_evidence_quality_score,
                "priority_score_reproducibility": avg_reproducibility_score,
                "priority_score_correction_cost": avg_cost_score,
                "priority_score_freeze_risk_penalty": avg_freeze_risk_score,
                "top_manual_truth_sources": (
                    group["manual_truth_source_bucket"].fillna("").astype(str).value_counts(dropna=False).head(3).to_dict()
                ),
                "top_heuristic_sources": (
                    group["heuristic_source_kind"].fillna("").astype(str).value_counts(dropna=False).head(3).to_dict()
                ),
                "top_episode_ids": sorted_group["episode_id"].fillna("").astype(str).head(5).tolist(),
                "family_disposition": family_disposition,
                "correction_priority_tier": priority_tier,
                "recommended_next_action": recommended_next_action,
                "ranking_reason_summary": ranking_reason_summary,
            }
        )

    ranking = pd.DataFrame(rows)
    if not ranking.empty:
        ranking["priority_rank"] = ranking["correction_priority_tier"].map(
            {"P1": 0, "P2": 1, "P3": 2, "hold": 3}
        ).fillna(4)
        ranking = ranking.sort_values(
            by=["priority_rank", "priority_score_total", "avg_correction_priority_score", "case_count", "family_id"],
            ascending=[True, False, False, False, True],
            kind="stable",
        ).copy()
        ranking = ranking.drop(columns=["priority_rank"])

    for column in MANUAL_VS_HEURISTIC_FAMILY_RANKING_COLUMNS:
        if column not in ranking.columns:
            ranking[column] = ""
    ranking = ranking[MANUAL_VS_HEURISTIC_FAMILY_RANKING_COLUMNS].copy()

    candidate_target = ranking[
        ranking["correction_priority_tier"].fillna("").astype(str).isin(["P1", "P2", "P3"])
    ]
    summary = {
        "family_ranking_version": MANUAL_VS_HEURISTIC_FAMILY_RANKING_VERSION,
        "family_count": int(len(ranking)),
        "disposition_counts": ranking["family_disposition"].value_counts(dropna=False).to_dict(),
        "priority_tier_counts": ranking["correction_priority_tier"].value_counts(dropna=False).to_dict(),
        "recommended_next_action_counts": ranking["recommended_next_action"].value_counts(dropna=False).to_dict(),
        "next_target_family_id": (
            _to_text(candidate_target.iloc[0]["family_id"], "") if not candidate_target.empty else ""
        ),
    }
    return ranking, summary


def render_manual_vs_heuristic_family_ranking_markdown(
    summary: Mapping[str, Any],
    ranking: pd.DataFrame,
) -> str:
    lines = [
        "# Manual vs Heuristic Next-Family Ranking v0",
        "",
        f"- families: `{summary.get('family_count', 0)}`",
        f"- disposition counts: `{summary.get('disposition_counts', {})}`",
        f"- priority tiers: `{summary.get('priority_tier_counts', {})}`",
        f"- recommended actions: `{summary.get('recommended_next_action_counts', {})}`",
        f"- next target family: `{summary.get('next_target_family_id', '')}`",
        "",
        "## Ranked Families",
    ]
    preview = ranking.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("correction_priority_tier", "")),
                        _to_text(row.get("family_disposition", "")),
                        _to_text(row.get("miss_type", "")),
                        f"cases={_to_text(row.get('case_count', '0'))}",
                        f"manual={_to_text(row.get('manual_wait_teacher_family', ''))}",
                        f"heuristic={_to_text(row.get('heuristic_barrier_main_label', ''))}/{_to_text(row.get('heuristic_wait_family', ''))}",
                        f"score_total={_to_text(row.get('priority_score_total', '0'))}",
                        (
                            "components="
                            f"f{_to_text(row.get('priority_score_frequency', '0'))}/"
                            f"s{_to_text(row.get('priority_score_severity', '0'))}/"
                            f"e{_to_text(row.get('priority_score_evidence', '0'))}/"
                            f"r{_to_text(row.get('priority_score_reproducibility', '0'))}/"
                            f"c{_to_text(row.get('priority_score_correction_cost', '0'))}/"
                            f"pen{_to_text(row.get('priority_score_freeze_risk_penalty', '0'))}"
                        ),
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
