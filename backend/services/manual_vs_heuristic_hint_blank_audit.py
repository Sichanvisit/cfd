"""Audit why matched manual-vs-heuristic cases still have blank heuristic hints."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


MATCHED_CASE_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "heuristic_source_file",
    "heuristic_source_kind",
    "heuristic_match_gap_minutes",
    "heuristic_barrier_main_label",
    "heuristic_wait_family",
    "heuristic_forecast_family",
    "heuristic_belief_family",
    "heuristic_barrier_reason_summary",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _is_present(value: object) -> bool:
    return bool(_to_text(value, ""))


def load_manual_vs_heuristic_comparison(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(csv_path, encoding=encoding, low_memory=False)
        except Exception:
            continue
    return pd.read_csv(csv_path, low_memory=False)


def _source_inventory_for_entry_decisions(trades_dir: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(trades_dir)
    inventories: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("entry_decisions*.csv")):
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        except Exception:
            try:
                frame = pd.read_csv(path, encoding="cp949", low_memory=False)
            except Exception:
                continue
        inventories[path.name] = {
            "row_count": int(len(frame)),
            "barrier_label_column_present": "barrier_candidate_supporting_label" in frame.columns,
            "barrier_family_column_present": "barrier_candidate_recommended_family" in frame.columns,
            "forecast_column_present": "forecast_decision_hint" in frame.columns,
            "belief_column_present": "belief_candidate_recommended_family" in frame.columns,
        }
    return inventories


def build_manual_vs_heuristic_hint_blank_audit(
    comparison: pd.DataFrame,
    *,
    trades_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if comparison.empty:
        return pd.DataFrame(columns=MATCHED_CASE_COLUMNS), {
            "matched_case_count": 0,
            "root_cause_counts": {},
        }

    matched = comparison[
        comparison["review_comment"].fillna("").astype(str).str.contains("match_reason=matched", na=False)
    ].copy()
    for column in MATCHED_CASE_COLUMNS:
        if column not in matched.columns:
            matched[column] = ""
    matched = matched[MATCHED_CASE_COLUMNS].copy()

    inventories = _source_inventory_for_entry_decisions(trades_dir)
    barrier_root_causes: Counter[str] = Counter()
    wait_root_causes: Counter[str] = Counter()
    forecast_root_causes: Counter[str] = Counter()
    belief_root_causes: Counter[str] = Counter()

    source_case_counts: Counter[str] = Counter()
    source_kind_counts: Counter[str] = Counter()

    for _, row in matched.iterrows():
        source_file = _to_text(row.get("heuristic_source_file", ""), "")
        source_case_counts[source_file or "(unknown)"] += 1
        source_kind_counts[_to_text(row.get("heuristic_source_kind", ""), "(unknown)") or "(unknown)"] += 1
        inventory = inventories.get(source_file, {})

        barrier_present = _is_present(row.get("heuristic_barrier_main_label", "")) or _is_present(
            row.get("heuristic_barrier_reason_summary", "")
        )
        wait_present = _is_present(row.get("heuristic_wait_family", ""))
        forecast_present = _is_present(row.get("heuristic_forecast_family", ""))
        belief_present = _is_present(row.get("heuristic_belief_family", ""))

        if barrier_present:
            barrier_root_causes["barrier_hint_present"] += 1
        elif not inventory.get("barrier_label_column_present", False) and not inventory.get(
            "barrier_family_column_present", False
        ):
            barrier_root_causes["source_schema_missing_barrier_fields"] += 1
        else:
            barrier_root_causes["barrier_fields_blank_in_logged_row"] += 1

        if wait_present:
            wait_root_causes["wait_hint_present"] += 1
        elif not inventory.get("barrier_label_column_present", False) and not inventory.get(
            "barrier_family_column_present", False
        ):
            wait_root_causes["wait_derivation_blocked_by_missing_barrier_fields"] += 1
        else:
            wait_root_causes["wait_derivation_missing_from_logged_row"] += 1

        if forecast_present:
            forecast_root_causes["forecast_hint_present"] += 1
        elif not inventory.get("forecast_column_present", False):
            forecast_root_causes["source_schema_missing_forecast_field"] += 1
        else:
            forecast_root_causes["forecast_field_blank_in_logged_row"] += 1

        if belief_present:
            belief_root_causes["belief_hint_present"] += 1
        elif not inventory.get("belief_column_present", False):
            belief_root_causes["source_schema_missing_belief_field"] += 1
        else:
            belief_root_causes["belief_field_blank_in_logged_row"] += 1

    summary = {
        "matched_case_count": int(len(matched)),
        "symbol_counts": matched["symbol"].fillna("").astype(str).value_counts().to_dict(),
        "manual_label_counts": matched["manual_wait_teacher_label"].fillna("").astype(str).value_counts().to_dict(),
        "source_case_counts": dict(source_case_counts),
        "source_kind_counts": dict(source_kind_counts),
        "barrier_root_cause_counts": dict(barrier_root_causes),
        "wait_root_cause_counts": dict(wait_root_causes),
        "forecast_root_cause_counts": dict(forecast_root_causes),
        "belief_root_cause_counts": dict(belief_root_causes),
        "source_inventory": inventories,
    }
    return matched, summary


def render_manual_vs_heuristic_hint_blank_audit_markdown(summary: dict[str, Any]) -> str:
    def _fmt(counter_key: str) -> str:
        data = dict(summary.get(counter_key, {}) or {})
        return ", ".join(f"{key}={value}" for key, value in sorted(data.items(), key=lambda item: (-item[1], item[0]))) or "none"

    lines = [
        "# Manual vs Heuristic Hint Blank Audit v0",
        "",
        f"- matched cases: `{summary.get('matched_case_count', 0)}`",
        f"- symbols: `{summary.get('symbol_counts', {})}`",
        f"- manual labels: `{summary.get('manual_label_counts', {})}`",
        f"- source files: `{summary.get('source_case_counts', {})}`",
        f"- source kinds: `{summary.get('source_kind_counts', {})}`",
        f"- barrier root causes: `{_fmt('barrier_root_cause_counts')}`",
        f"- wait root causes: `{_fmt('wait_root_cause_counts')}`",
        f"- forecast root causes: `{_fmt('forecast_root_cause_counts')}`",
        f"- belief root causes: `{_fmt('belief_root_cause_counts')}`",
        "",
        "## Why This Matters",
        "",
        "- This audit distinguishes time coverage from hint coverage.",
        "- If rows are matched in time but the source schema never logged barrier or forecast fields, the next fix is history-source widening or fallback reconstruction, not bias tuning.",
        "- If fields exist in schema but are blank in matched rows, the next fix is runtime surfacing or row assembly quality.",
        "",
        "## Source Inventory",
        "",
    ]
    inventories = dict(summary.get("source_inventory", {}) or {})
    for source_file, inventory in sorted(inventories.items()):
        lines.append(
            f"- `{source_file}` | rows=`{inventory.get('row_count', 0)}` | "
            f"barrier_label_col=`{inventory.get('barrier_label_column_present', False)}` | "
            f"barrier_family_col=`{inventory.get('barrier_family_column_present', False)}` | "
            f"forecast_col=`{inventory.get('forecast_column_present', False)}` | "
            f"belief_col=`{inventory.get('belief_column_present', False)}`"
        )
    return "\n".join(lines) + "\n"


def render_manual_vs_heuristic_hint_blank_audit_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2)
