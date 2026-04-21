"""Pattern coverage map for the manual truth corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


MANUAL_TRUTH_CORPUS_COVERAGE_VERSION = "manual_truth_corpus_coverage_v0"

MANUAL_TRUTH_CORPUS_COVERAGE_COLUMNS = [
    "coverage_key",
    "symbol",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "canonical_case_count",
    "canonical_reviewed_case_count",
    "assistant_inferred_case_count",
    "current_rich_draft_case_count",
    "current_rich_review_needed_count",
    "total_case_count",
    "source_diversity_count",
    "latest_canonical_anchor_time",
    "latest_current_rich_draft_anchor_time",
    "coverage_density_score",
    "coverage_class",
    "pattern_coverage_value",
    "review_pressure_class",
    "recommended_next_action",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _parse_local_timestamp(value: object) -> pd.Timestamp | pd.NaT:
    text = _to_text(value, "")
    if not text:
        return pd.NaT
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "+" not in text and "T" in text:
        text = f"{text}+09:00"
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return pd.NaT
    if getattr(parsed, "tzinfo", None) is None:
        return parsed.tz_localize("Asia/Seoul")
    return parsed


def _source_bucket(annotation_source: object) -> str:
    source = _to_text(annotation_source, "").lower()
    if source == "chart_annotated":
        return "canonical_chart_reviewed"
    if source == "assistant_chart_inferred":
        return "assistant_inferred_canonical"
    if source == "assistant_current_rich_seed":
        return "current_rich_draft"
    return source or "unknown"


def _coverage_class(total_case_count: int, reviewed_case_count: int, draft_case_count: int) -> str:
    if total_case_count >= 12 and reviewed_case_count >= 4:
        return "dense"
    if total_case_count >= 6 and reviewed_case_count >= 2:
        return "usable"
    if total_case_count >= 3 or draft_case_count > 0:
        return "thin"
    return "missing"


def _pattern_coverage_value(family: str, reviewed_case_count: int, total_case_count: int) -> str:
    family_key = _to_text(family, "").lower()
    if family_key in {"timing_improvement", "failed_wait"} and total_case_count < 10:
        return "high"
    if family_key in {"protective_exit", "reversal_escape"} and reviewed_case_count < 2:
        return "high"
    if total_case_count < 5:
        return "medium"
    return "low"


def _review_pressure_class(draft_case_count: int, review_needed_count: int, coverage_class: str) -> str:
    if review_needed_count >= 3:
        return "high"
    if draft_case_count > 0 and coverage_class in {"thin", "missing"}:
        return "high"
    if draft_case_count > 0:
        return "medium"
    return "low"


def _recommended_next_action(coverage_class: str, pattern_value: str, review_pressure: str) -> str:
    if review_pressure == "high":
        return "review_current_rich_then_promote"
    if coverage_class in {"missing", "thin"} and pattern_value == "high":
        return "collect_more_family_truth"
    if coverage_class in {"missing", "thin"}:
        return "collect_more_pattern_truth"
    return "monitor_coverage"


def build_manual_truth_corpus_coverage(
    canonical: pd.DataFrame,
    current_rich_draft: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    canonical_frame = normalize_manual_wait_teacher_annotation_df(
        canonical if canonical is not None else pd.DataFrame()
    )
    draft_frame = normalize_manual_wait_teacher_annotation_df(
        current_rich_draft if current_rich_draft is not None else pd.DataFrame()
    )

    canonical_frame["symbol"] = canonical_frame["symbol"].fillna("").astype(str).str.upper()
    canonical_frame["manual_wait_teacher_family"] = (
        canonical_frame["manual_wait_teacher_family"].fillna("").astype(str).str.lower()
    )
    canonical_frame["manual_wait_teacher_subtype"] = (
        canonical_frame["manual_wait_teacher_subtype"].fillna("").astype(str).str.lower()
    )
    canonical_frame["anchor_time_parsed"] = canonical_frame["anchor_time"].apply(_parse_local_timestamp)
    canonical_frame["source_bucket"] = canonical_frame["annotation_source"].apply(_source_bucket)

    draft_frame["symbol"] = draft_frame["symbol"].fillna("").astype(str).str.upper()
    draft_frame["manual_wait_teacher_family"] = (
        draft_frame["manual_wait_teacher_family"].fillna("").astype(str).str.lower()
    )
    draft_frame["manual_wait_teacher_subtype"] = (
        draft_frame["manual_wait_teacher_subtype"].fillna("").astype(str).str.lower()
    )
    draft_frame["anchor_time_parsed"] = draft_frame["anchor_time"].apply(_parse_local_timestamp)
    draft_frame["source_bucket"] = draft_frame["annotation_source"].apply(_source_bucket)

    keys = sorted(
        {
            (
                _to_text(row.get("symbol", ""), "").upper(),
                _to_text(row.get("manual_wait_teacher_family", ""), "").lower(),
                _to_text(row.get("manual_wait_teacher_subtype", ""), "").lower(),
            )
            for _, row in pd.concat([canonical_frame, draft_frame], ignore_index=True).iterrows()
            if _to_text(row.get("symbol", ""), "") and _to_text(row.get("manual_wait_teacher_family", ""), "")
        }
    )

    rows: list[dict[str, Any]] = []
    for symbol, family, subtype in keys:
        canonical_bucket = canonical_frame[
            canonical_frame["symbol"].eq(symbol)
            & canonical_frame["manual_wait_teacher_family"].eq(family)
            & canonical_frame["manual_wait_teacher_subtype"].eq(subtype)
        ].copy()
        draft_bucket = draft_frame[
            draft_frame["symbol"].eq(symbol)
            & draft_frame["manual_wait_teacher_family"].eq(family)
            & draft_frame["manual_wait_teacher_subtype"].eq(subtype)
        ].copy()

        canonical_case_count = int(len(canonical_bucket))
        canonical_reviewed_case_count = int(
            canonical_bucket["source_bucket"].fillna("").astype(str).eq("canonical_chart_reviewed").sum()
        )
        assistant_inferred_case_count = int(
            canonical_bucket["source_bucket"].fillna("").astype(str).eq("assistant_inferred_canonical").sum()
        )
        current_rich_draft_case_count = int(len(draft_bucket))
        current_rich_review_needed_count = int(
            draft_bucket["review_status"]
            .fillna("")
            .astype(str)
            .str.lower()
            .isin(["needs_manual_recheck", "review_needed", "pending"])
            .sum()
        )
        total_case_count = canonical_case_count + current_rich_draft_case_count
        source_diversity_count = int(
            pd.concat(
                [
                    canonical_bucket["source_bucket"].fillna("").astype(str),
                    draft_bucket["source_bucket"].fillna("").astype(str),
                ],
                ignore_index=True,
            ).replace("", pd.NA).dropna().nunique()
        )
        latest_canonical_anchor_time = (
            canonical_bucket["anchor_time_parsed"].dropna().max().isoformat()
            if not canonical_bucket["anchor_time_parsed"].dropna().empty
            else ""
        )
        latest_current_rich_draft_anchor_time = (
            draft_bucket["anchor_time_parsed"].dropna().max().isoformat()
            if not draft_bucket["anchor_time_parsed"].dropna().empty
            else ""
        )
        coverage_density_score = (
            canonical_reviewed_case_count * 2
            + assistant_inferred_case_count
            + current_rich_draft_case_count
            + source_diversity_count
        )
        coverage_class = _coverage_class(
            total_case_count=total_case_count,
            reviewed_case_count=canonical_reviewed_case_count,
            draft_case_count=current_rich_draft_case_count,
        )
        pattern_coverage_value = _pattern_coverage_value(
            family=family,
            reviewed_case_count=canonical_reviewed_case_count,
            total_case_count=total_case_count,
        )
        review_pressure_class = _review_pressure_class(
            draft_case_count=current_rich_draft_case_count,
            review_needed_count=current_rich_review_needed_count,
            coverage_class=coverage_class,
        )
        recommended_next_action = _recommended_next_action(
            coverage_class=coverage_class,
            pattern_value=pattern_coverage_value,
            review_pressure=review_pressure_class,
        )
        rows.append(
            {
                "coverage_key": f"{symbol}|{family}|{subtype or 'none'}",
                "symbol": symbol,
                "manual_wait_teacher_family": family,
                "manual_wait_teacher_subtype": subtype,
                "canonical_case_count": canonical_case_count,
                "canonical_reviewed_case_count": canonical_reviewed_case_count,
                "assistant_inferred_case_count": assistant_inferred_case_count,
                "current_rich_draft_case_count": current_rich_draft_case_count,
                "current_rich_review_needed_count": current_rich_review_needed_count,
                "total_case_count": total_case_count,
                "source_diversity_count": source_diversity_count,
                "latest_canonical_anchor_time": latest_canonical_anchor_time,
                "latest_current_rich_draft_anchor_time": latest_current_rich_draft_anchor_time,
                "coverage_density_score": coverage_density_score,
                "coverage_class": coverage_class,
                "pattern_coverage_value": pattern_coverage_value,
                "review_pressure_class": review_pressure_class,
                "recommended_next_action": recommended_next_action,
            }
        )

    coverage = pd.DataFrame(rows)
    if not coverage.empty:
        coverage["action_rank"] = coverage["recommended_next_action"].map(
            {
                "review_current_rich_then_promote": 0,
                "collect_more_family_truth": 1,
                "collect_more_pattern_truth": 2,
                "monitor_coverage": 3,
            }
        ).fillna(4)
        coverage = coverage.sort_values(
            by=["action_rank", "pattern_coverage_value", "coverage_density_score", "symbol", "manual_wait_teacher_family"],
            ascending=[True, True, True, True, True],
            kind="stable",
        ).drop(columns=["action_rank"]).reset_index(drop=True)

    for column in MANUAL_TRUTH_CORPUS_COVERAGE_COLUMNS:
        if column not in coverage.columns:
            coverage[column] = ""
    coverage = coverage[MANUAL_TRUTH_CORPUS_COVERAGE_COLUMNS].copy()

    summary = {
        "coverage_version": MANUAL_TRUTH_CORPUS_COVERAGE_VERSION,
        "coverage_row_count": int(len(coverage)),
        "coverage_class_counts": coverage["coverage_class"].value_counts(dropna=False).to_dict()
        if not coverage.empty
        else {},
        "pattern_coverage_value_counts": coverage["pattern_coverage_value"].value_counts(dropna=False).to_dict()
        if not coverage.empty
        else {},
        "recommended_next_action_counts": coverage["recommended_next_action"].value_counts(dropna=False).to_dict()
        if not coverage.empty
        else {},
    }
    return coverage, summary


def render_manual_truth_corpus_coverage_markdown(
    summary: Mapping[str, Any],
    coverage: pd.DataFrame,
) -> str:
    lines = [
        "# Manual Truth Corpus Coverage Map v0",
        "",
        f"- rows: `{summary.get('coverage_row_count', 0)}`",
        f"- coverage classes: `{summary.get('coverage_class_counts', {})}`",
        f"- pattern values: `{summary.get('pattern_coverage_value_counts', {})}`",
        f"- recommended actions: `{summary.get('recommended_next_action_counts', {})}`",
        "",
        "## Coverage Preview",
    ]
    preview = coverage.head(12)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("manual_wait_teacher_family", "")),
                        _to_text(row.get("manual_wait_teacher_subtype", "")),
                        f"canon={_to_text(row.get('canonical_case_count', '0'))}",
                        f"draft={_to_text(row.get('current_rich_draft_case_count', '0'))}",
                        _to_text(row.get("coverage_class", "")),
                        _to_text(row.get("review_pressure_class", "")),
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
