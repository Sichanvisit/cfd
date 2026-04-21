from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_pa8_action_symbol_review_json_path(symbol: str) -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / f"checkpoint_pa8_action_review_{symbol.lower()}_latest.json"
    )


def default_checkpoint_pa8_action_symbol_review_markdown_path(symbol: str) -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / f"checkpoint_pa8_action_review_{symbol.lower()}_latest.md"
    )


def default_checkpoint_dataset_resolved_path() -> Path:
    return _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _format_metric(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_checkpoint_dataset_resolved_rows(path: str | Path | None = None) -> list[dict[str, str]]:
    file_path = Path(path) if path else default_checkpoint_dataset_resolved_path()
    if not file_path.exists():
        return []
    with file_path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _pick_symbol_row(pa8_action_review_checklist_payload: Mapping[str, Any], symbol: str) -> dict[str, Any]:
    target = symbol.upper()
    for row in pa8_action_review_checklist_payload.get("checklist_rows", []) or []:
        if isinstance(row, Mapping) and _to_text(row.get("symbol")).upper() == target:
            return dict(row)
    return {}


def _mismatch_rows(resolved_rows: Iterable[Mapping[str, Any]], symbol: str) -> list[dict[str, Any]]:
    target = symbol.upper()
    rows: list[dict[str, Any]] = []
    for row in resolved_rows:
        row_map = dict(row)
        if _to_text(row_map.get("symbol")).upper() != target:
            continue
        action = _to_text(row_map.get("management_action_label"))
        hindsight = _to_text(row_map.get("hindsight_best_management_action_label"))
        if not action or not hindsight or action == hindsight:
            continue
        rows.append(row_map)
    return rows


def _cluster_key(row: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        _to_text(row.get("surface_name")),
        _to_text(row.get("checkpoint_type")),
        _to_text(row.get("checkpoint_rule_family_hint")),
        _to_text(row.get("management_action_label")),
        _to_text(row.get("hindsight_best_management_action_label")),
    )


def _summarize_cluster(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sample = rows[0] if rows else {}
    current_profit_values = [_to_float(row.get("current_profit")) for row in rows]
    hold_values = [_to_float(row.get("runtime_hold_quality_score")) for row in rows]
    partial_values = [_to_float(row.get("runtime_partial_exit_ev")) for row in rows]
    continuation_values = [_to_float(row.get("runtime_continuation_odds")) for row in rows]
    reversal_values = [_to_float(row.get("runtime_reversal_odds")) for row in rows]
    reason_counts = Counter(_to_text(row.get("management_action_reason")) for row in rows)
    source_counts = Counter(_to_text(row.get("source")) for row in rows)
    return {
        "surface_name": _to_text(sample.get("surface_name")),
        "checkpoint_type": _to_text(sample.get("checkpoint_type")),
        "checkpoint_rule_family_hint": _to_text(sample.get("checkpoint_rule_family_hint")),
        "management_action_label": _to_text(sample.get("management_action_label")),
        "hindsight_best_management_action_label": _to_text(sample.get("hindsight_best_management_action_label")),
        "row_count": len(rows),
        "avg_current_profit": round(sum(current_profit_values) / len(current_profit_values), 6) if current_profit_values else 0.0,
        "avg_runtime_hold_quality_score": round(sum(hold_values) / len(hold_values), 6) if hold_values else 0.0,
        "avg_runtime_partial_exit_ev": round(sum(partial_values) / len(partial_values), 6) if partial_values else 0.0,
        "avg_runtime_continuation_odds": round(sum(continuation_values) / len(continuation_values), 6)
        if continuation_values
        else 0.0,
        "avg_runtime_reversal_odds": round(sum(reversal_values) / len(reversal_values), 6) if reversal_values else 0.0,
        "top_management_reason": reason_counts.most_common(1)[0][0] if reason_counts else "",
        "top_source": source_counts.most_common(1)[0][0] if source_counts else "",
        "sample_checkpoint_ids": [row.get("checkpoint_id", "") for row in rows[:5]],
    }


def _manual_exception_summary(resolved_rows: Iterable[Mapping[str, Any]], symbol: str) -> list[dict[str, Any]]:
    target = symbol.upper()
    counter: Counter[tuple[str, str, str]] = Counter()
    for row in resolved_rows:
        row_map = dict(row)
        if _to_text(row_map.get("symbol")).upper() != target:
            continue
        if _to_text(row_map.get("hindsight_quality_tier")).lower() != "manual_exception":
            continue
        counter[
            (
                _to_text(row_map.get("surface_name")),
                _to_text(row_map.get("checkpoint_type")),
                _to_text(row_map.get("checkpoint_rule_family_hint")),
            )
        ] += 1
    return [
        {
            "surface_name": surface,
            "checkpoint_type": checkpoint_type,
            "checkpoint_rule_family_hint": family,
            "row_count": count,
        }
        for (surface, checkpoint_type, family), count in counter.most_common(8)
    ]


def _position_side_summary(resolved_rows: Iterable[Mapping[str, Any]], symbol: str) -> dict[str, int]:
    target = symbol.upper()
    counter: Counter[str] = Counter()
    for row in resolved_rows:
        row_map = dict(row)
        if _to_text(row_map.get("symbol")).upper() == target:
            counter[_to_text(row_map.get("position_side"), "UNKNOWN")] += 1
    return dict(counter)


def _review_conclusion(symbol: str, top_cluster: Mapping[str, Any]) -> tuple[str, str]:
    family = _to_text(top_cluster.get("checkpoint_rule_family_hint"))
    action = _to_text(top_cluster.get("management_action_label"))
    hindsight = _to_text(top_cluster.get("hindsight_best_management_action_label"))
    checkpoint_type = _to_text(top_cluster.get("checkpoint_type"))
    surface_name = _to_text(top_cluster.get("surface_name"))
    if family == "profit_hold_bias" and action == "HOLD" and hindsight == "PARTIAL_THEN_HOLD":
        return (
            "narrow_hold_boundary_candidate_identified",
            f"{symbol.upper()} hold-precision blocker is concentrated in {checkpoint_type} + profit_hold_bias, where HOLD should likely preview as PARTIAL_THEN_HOLD.",
        )
    if (
        surface_name == "protective_exit_surface"
        and checkpoint_type == "RECLAIM_CHECK"
        and family in {"active_open_loss", "open_loss_protective"}
        and action == "PARTIAL_EXIT"
        and hindsight == "WAIT"
    ):
        return (
            "narrow_wait_boundary_candidate_identified",
            f"{symbol.upper()} protective reclaim loss blocker is concentrated in {checkpoint_type} + {family}, where PARTIAL_EXIT should likely preview as WAIT.",
        )
    return (
        "review_completed_no_single_family_dominance",
        f"{symbol.upper()} review does not collapse to a single patch family yet.",
    )


def build_checkpoint_pa8_action_symbol_review(
    *,
    symbol: str,
    pa8_action_review_checklist_payload: Mapping[str, Any] | None,
    resolved_rows: Iterable[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    target = symbol.upper()
    checklist_payload = _mapping(pa8_action_review_checklist_payload)
    checklist_row = _pick_symbol_row(checklist_payload, target)
    rows = [dict(row) for row in resolved_rows or []]
    mismatches = _mismatch_rows(rows, target)

    cluster_map: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in mismatches:
        cluster_map.setdefault(_cluster_key(row), []).append(row)
    cluster_rows = [_summarize_cluster(group_rows) for _, group_rows in sorted(cluster_map.items(), key=lambda item: len(item[1]), reverse=True)]
    top_cluster = cluster_rows[0] if cluster_rows else {}
    review_result, review_summary = _review_conclusion(target, top_cluster)

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_symbol_review_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": target,
            "review_state": _to_text(checklist_row.get("review_state")),
            "goal": _to_text(checklist_row.get("goal")),
            "review_result": review_result,
            "review_summary": review_summary,
            "mismatch_row_count": len(mismatches),
            "top_mismatch_cluster_row_count": int(top_cluster.get("row_count") or 0),
        },
        "checklist_context": checklist_row,
        "top_mismatch_clusters": cluster_rows[:8],
        "manual_exception_top_groups": _manual_exception_summary(rows, target),
        "position_side_counts": _position_side_summary(rows, target),
    }


def render_checkpoint_pa8_action_symbol_review_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    checklist_context = _mapping(body.get("checklist_context"))
    top_clusters = body.get("top_mismatch_clusters")
    if not isinstance(top_clusters, list):
        top_clusters = []
    manual_exception_groups = body.get("manual_exception_top_groups")
    if not isinstance(manual_exception_groups, list):
        manual_exception_groups = []
    position_side_counts = _mapping(body.get("position_side_counts"))

    symbol = _to_text(summary.get("symbol")).upper()
    lines: list[str] = []
    lines.append(f"# PA8 {symbol} Action Review")
    lines.append("")
    lines.append(f"- review_state: `{_to_text(summary.get('review_state'))}`")
    lines.append(f"- goal: {_to_text(summary.get('goal'))}")
    lines.append(f"- review_result: `{_to_text(summary.get('review_result'))}`")
    lines.append(f"- mismatch_row_count: `{summary.get('mismatch_row_count')}`")
    lines.append(f"- top_mismatch_cluster_row_count: `{summary.get('top_mismatch_cluster_row_count')}`")
    lines.append(f"- review_summary: {_to_text(summary.get('review_summary'))}")
    lines.append("")
    lines.append("## Checklist Context")
    lines.append("")
    lines.append("- blockers:")
    for blocker in list(checklist_context.get("blockers", []) or []):
        lines.append(f"  - `{_to_text(blocker)}`")
    lines.append("- pass_criteria:")
    for item in list(checklist_context.get("pass_criteria", []) or []):
        lines.append(f"  - {item}")
    lines.append("- review_focuses:")
    for item in list(checklist_context.get("review_focuses", []) or []):
        lines.append(f"  - `{_to_text(item)}`")
    lines.append("")
    lines.append("## Top Mismatch Clusters")
    lines.append("")
    for index, cluster in enumerate(top_clusters, start=1):
        if not isinstance(cluster, Mapping):
            continue
        lines.append(f"### {index}. {_to_text(cluster.get('checkpoint_rule_family_hint'))}")
        lines.append("")
        lines.append(f"- surface_name: `{_to_text(cluster.get('surface_name'))}`")
        lines.append(f"- checkpoint_type: `{_to_text(cluster.get('checkpoint_type'))}`")
        lines.append(
            f"- action_path: `{_to_text(cluster.get('management_action_label'))} -> {_to_text(cluster.get('hindsight_best_management_action_label'))}`"
        )
        lines.append(f"- row_count: `{cluster.get('row_count')}`")
        lines.append(f"- avg_current_profit: `{_format_metric(_to_float(cluster.get('avg_current_profit')))}`")
        lines.append(
            f"- avg_runtime_hold_quality_score: `{_format_metric(_to_float(cluster.get('avg_runtime_hold_quality_score')))}`"
        )
        lines.append(
            f"- avg_runtime_partial_exit_ev: `{_format_metric(_to_float(cluster.get('avg_runtime_partial_exit_ev')))}`"
        )
        lines.append(
            f"- avg_runtime_continuation_odds: `{_format_metric(_to_float(cluster.get('avg_runtime_continuation_odds')))}`"
        )
        lines.append(
            f"- avg_runtime_reversal_odds: `{_format_metric(_to_float(cluster.get('avg_runtime_reversal_odds')))}`"
        )
        lines.append(f"- top_management_reason: `{_to_text(cluster.get('top_management_reason'))}`")
        lines.append(f"- top_source: `{_to_text(cluster.get('top_source'))}`")
        lines.append("- sample_checkpoint_ids:")
        for checkpoint_id in list(cluster.get("sample_checkpoint_ids", []) or []):
            lines.append(f"  - `{_to_text(checkpoint_id)}`")
        lines.append("")
    lines.append("## Manual Exception Top Groups")
    lines.append("")
    for group in manual_exception_groups:
        if not isinstance(group, Mapping):
            continue
        lines.append(
            f"- `{_to_text(group.get('surface_name'))} | {_to_text(group.get('checkpoint_type'))} | {_to_text(group.get('checkpoint_rule_family_hint'))}`: `{group.get('row_count')}`"
        )
    lines.append("")
    lines.append("## Position Side Counts")
    lines.append("")
    for side, count in position_side_counts.items():
        lines.append(f"- `{_to_text(side)}`: `{count}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"
