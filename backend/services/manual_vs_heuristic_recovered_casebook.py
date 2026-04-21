"""Recovered manual-vs-heuristic casebook builder."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_VERSION = "manual_vs_heuristic_recovered_casebook_v0"

MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "anchor_side",
    "manual_wait_teacher_label",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "manual_wait_teacher_confidence",
    "heuristic_barrier_main_label",
    "heuristic_wait_family",
    "heuristic_wait_subtype",
    "heuristic_barrier_confidence_tier",
    "heuristic_barrier_reason_summary",
    "heuristic_reconstruction_mode",
    "heuristic_reconstruction_source_file",
    "manual_vs_barrier_match",
    "manual_vs_wait_family_match",
    "overall_alignment_grade",
    "miss_type",
    "mismatch_severity",
    "primary_correction_target",
    "repeated_case_signature",
    "review_comment",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def load_manual_vs_heuristic_comparison_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def build_manual_vs_heuristic_recovered_casebook(
    comparison_report: pd.DataFrame,
    *,
    reconstruction_mode: str = "global_detail_fallback",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = comparison_report.copy() if comparison_report is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS)
        summary = {
            "casebook_version": MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_VERSION,
            "reconstruction_mode": reconstruction_mode,
            "recovered_case_count": 0,
            "symbol_counts": {},
            "manual_label_counts": {},
            "barrier_label_counts": {},
            "wait_family_counts": {},
            "alignment_counts": {},
            "miss_type_counts": {},
            "primary_correction_target_counts": {},
            "reconstruction_source_counts": {},
            "top_repeated_case_signatures": {},
        }
        return empty, summary

    if "heuristic_reconstruction_mode" not in source.columns:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS)
        summary = {
            "casebook_version": MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_VERSION,
            "reconstruction_mode": reconstruction_mode,
            "recovered_case_count": 0,
            "symbol_counts": {},
            "manual_label_counts": {},
            "barrier_label_counts": {},
            "wait_family_counts": {},
            "alignment_counts": {},
            "miss_type_counts": {},
            "primary_correction_target_counts": {},
            "reconstruction_source_counts": {},
            "top_repeated_case_signatures": {},
        }
        return empty, summary

    recovered = source[
        source["heuristic_reconstruction_mode"].fillna("").astype(str) == reconstruction_mode
    ].copy()

    if recovered.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS)
        summary = {
            "casebook_version": MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_VERSION,
            "reconstruction_mode": reconstruction_mode,
            "recovered_case_count": 0,
            "symbol_counts": {},
            "manual_label_counts": {},
            "barrier_label_counts": {},
            "wait_family_counts": {},
            "alignment_counts": {},
            "miss_type_counts": {},
            "primary_correction_target_counts": {},
            "reconstruction_source_counts": {},
            "top_repeated_case_signatures": {},
        }
        return empty, summary

    recovered["mismatch_rank"] = recovered["overall_alignment_grade"].map(
        {
            "mismatch": 0,
            "partial_match": 1,
            "match": 2,
            "unknown": 3,
        }
    ).fillna(4)
    recovered["miss_type_sort"] = recovered["miss_type"].fillna("").replace("", "aligned")
    recovered["reconstruction_source_file_sort"] = recovered["heuristic_reconstruction_source_file"].fillna("")
    recovered = recovered.sort_values(
        by=[
            "mismatch_rank",
            "symbol",
            "miss_type_sort",
            "anchor_time",
            "episode_id",
        ],
        kind="stable",
    ).copy()

    for column in MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS:
        if column not in recovered.columns:
            recovered[column] = ""
    casebook = recovered[MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_COLUMNS].copy()

    repeated_signature_counts = Counter(
        _to_text(value, "aligned")
        for value in casebook["repeated_case_signature"].tolist()
        if _to_text(value, "")
    )

    summary = {
        "casebook_version": MANUAL_VS_HEURISTIC_RECOVERED_CASEBOOK_VERSION,
        "reconstruction_mode": reconstruction_mode,
        "recovered_case_count": int(len(casebook)),
        "symbol_counts": casebook["symbol"].value_counts(dropna=False).to_dict(),
        "manual_label_counts": casebook["manual_wait_teacher_label"].value_counts(dropna=False).to_dict(),
        "barrier_label_counts": casebook["heuristic_barrier_main_label"].replace("", "blank").value_counts(dropna=False).to_dict(),
        "wait_family_counts": casebook["heuristic_wait_family"].replace("", "blank").value_counts(dropna=False).to_dict(),
        "alignment_counts": casebook["overall_alignment_grade"].value_counts(dropna=False).to_dict(),
        "miss_type_counts": casebook["miss_type"].apply(lambda value: _to_text(value, "aligned")).value_counts(dropna=False).to_dict(),
        "primary_correction_target_counts": casebook["primary_correction_target"].apply(lambda value: _to_text(value, "none")).value_counts(dropna=False).to_dict(),
        "reconstruction_source_counts": casebook["heuristic_reconstruction_source_file"].value_counts(dropna=False).to_dict(),
        "top_repeated_case_signatures": dict(repeated_signature_counts.most_common(10)),
    }
    return casebook, summary


def render_manual_vs_heuristic_recovered_casebook_markdown(summary: Mapping[str, Any], casebook: pd.DataFrame) -> str:
    top_signatures = ", ".join(
        f"{key}={value}"
        for key, value in list((summary.get("top_repeated_case_signatures", {}) or {}).items())[:5]
    ) or "none"
    top_sources = ", ".join(
        f"{key}={value}"
        for key, value in list((summary.get("reconstruction_source_counts", {}) or {}).items())[:5]
    ) or "none"

    lines = [
        "# Manual vs Heuristic Recovered Casebook v0",
        "",
        f"- reconstruction mode: `{summary.get('reconstruction_mode', '')}`",
        f"- recovered cases: `{summary.get('recovered_case_count', 0)}`",
        f"- symbols: `{summary.get('symbol_counts', {})}`",
        f"- manual labels: `{summary.get('manual_label_counts', {})}`",
        f"- heuristic barrier labels: `{summary.get('barrier_label_counts', {})}`",
        f"- heuristic wait families: `{summary.get('wait_family_counts', {})}`",
        f"- alignment counts: `{summary.get('alignment_counts', {})}`",
        f"- miss types: `{summary.get('miss_type_counts', {})}`",
        f"- primary correction targets: `{summary.get('primary_correction_target_counts', {})}`",
        f"- top reconstruction sources: `{top_sources}`",
        f"- top repeated signatures: `{top_signatures}`",
        "",
        "## Representative Cases",
    ]

    preview = casebook.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("episode_id", "")),
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("manual_wait_teacher_label", "")),
                        f"heuristic={_to_text(row.get('heuristic_barrier_main_label', ''), 'blank')}/{_to_text(row.get('heuristic_wait_family', ''), 'blank')}",
                        f"align={_to_text(row.get('overall_alignment_grade', ''), 'unknown')}",
                        f"miss={_to_text(row.get('miss_type', ''), 'aligned')}",
                    ]
                )
            )

    return "\n".join(lines) + "\n"
