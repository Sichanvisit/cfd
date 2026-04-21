from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_action_review_checklist_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_action_review_checklist_latest.json"
    )


def default_checkpoint_pa8_action_review_checklist_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_action_review_checklist_latest.md"
    )


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _format_metric(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _symbol_goal(row: Mapping[str, Any]) -> str:
    blockers = set(row.get("review_blockers", []) or [])
    symbol = _to_text(row.get("symbol")).upper()
    if "hold_precision_below_symbol_floor" in blockers:
        return f"Confirm whether the HOLD boundary for {symbol} is actually correct against hindsight outcomes."
    if "runtime_proxy_match_rate_below_symbol_floor" in blockers:
        return f"Confirm whether runtime proxy mismatch can be reduced for {symbol} without changing scene bias."
    if "partial_then_hold_quality_below_symbol_floor" in blockers:
        return f"Confirm whether the PARTIAL_THEN_HOLD boundary for {symbol} can be stabilized."
    if "full_exit_precision_below_symbol_floor" in blockers:
        return f"Confirm whether the FULL_EXIT guard for {symbol} is safe enough for action-only canary review."
    if "resolved_row_count_below_symbol_floor" in blockers or "live_runner_source_row_count_below_symbol_floor" in blockers:
        return f"Treat {symbol} as support-review only until more resolved and live-runner rows are collected."
    return f"Confirm whether {symbol} is ready for an action-only canary review."


def _symbol_pass_criteria(row: Mapping[str, Any]) -> list[str]:
    blockers = set(row.get("review_blockers", []) or [])
    criteria: list[str] = []
    if "hold_precision_below_symbol_floor" in blockers:
        criteria.append(
            "Raise hold_precision to at least 0.80, or explain with review evidence why the remaining gap is isolated to a narrow family."
        )
    if "runtime_proxy_match_rate_below_symbol_floor" in blockers:
        criteria.append(
            "Raise runtime_proxy_match_rate to at least 0.90, or show that the remaining mismatch is confined to a narrow family."
        )
    if "partial_then_hold_quality_below_symbol_floor" in blockers:
        criteria.append(
            "Raise partial_then_hold_quality to at least 0.95, or show in review evidence that the trim boundary is intentionally narrow."
        )
    if "full_exit_precision_below_symbol_floor" in blockers:
        criteria.append(
            "Raise full_exit_precision to at least 0.99, or confirm that no new false full-exit clusters are appearing."
        )
    if "resolved_row_count_below_symbol_floor" in blockers:
        criteria.append("Collect at least 500 resolved rows for the symbol.")
    if "live_runner_source_row_count_below_symbol_floor" in blockers:
        criteria.append("Collect at least 100 live-runner rows for the symbol.")
    if not criteria:
        criteria.append("The symbol can be reviewed directly for action-only canary readiness.")
    return criteria


def _symbol_check_items(row: Mapping[str, Any]) -> list[str]:
    review_focuses = list(row.get("review_focuses", []) or [])
    checks = [
        "Confirm that the latest metrics still match the packet blockers.",
        "Confirm that the highest manual-exception families match the listed review focuses.",
    ]
    for focus in review_focuses[:4]:
        checks.append(f"Inspect rows for `{focus}` first.")
    checks.append("Keep scene bias out of this review and judge only the action baseline.")
    return checks


def _symbol_decision_options(row: Mapping[str, Any]) -> list[str]:
    state = _to_text(row.get("review_state"))
    if state == "CANARY_CANDIDATE":
        return [
            "Promote to action-only canary review.",
            "Wait for a few more rows before canary promotion.",
        ]
    if state == "PRIMARY_REVIEW":
        return [
            "Open a patch or review task for the current blocker.",
            "If the blocker looks isolated and explained, keep it as a provisional canary candidate.",
        ]
    return [
        "Keep the symbol in support-review only.",
        "Continue observation until more rows accumulate.",
    ]


def build_checkpoint_pa8_action_review_checklist(
    *,
    pa8_action_review_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    packet = _mapping(pa8_action_review_packet_payload)
    summary = _mapping(packet.get("summary"))
    symbol_rows = packet.get("symbol_rows")
    if not isinstance(symbol_rows, list):
        symbol_rows = []

    checklist_rows: list[dict[str, Any]] = []
    for order, row in enumerate(symbol_rows, start=1):
        if not isinstance(row, Mapping):
            continue
        row_map = dict(row)
        checklist_rows.append(
            {
                "review_order": order,
                "symbol": _to_text(row_map.get("symbol")).upper(),
                "review_state": _to_text(row_map.get("review_state")),
                "goal": _symbol_goal(row_map),
                "current_metrics": {
                    "resolved_row_count": _to_int(row_map.get("resolved_row_count")),
                    "live_runner_source_row_count": _to_int(row_map.get("live_runner_source_row_count")),
                    "runtime_proxy_match_rate": round(_to_float(row_map.get("runtime_proxy_match_rate")), 6),
                    "hold_precision": round(_to_float(row_map.get("hold_precision")), 6),
                    "partial_then_hold_quality": round(_to_float(row_map.get("partial_then_hold_quality")), 6),
                    "full_exit_precision": round(_to_float(row_map.get("full_exit_precision")), 6),
                },
                "blockers": list(row_map.get("review_blockers", []) or []),
                "pass_criteria": _symbol_pass_criteria(row_map),
                "check_items": _symbol_check_items(row_map),
                "decision_options": _symbol_decision_options(row_map),
                "review_focuses": list(row_map.get("review_focuses", []) or []),
            }
        )

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_review_checklist_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "overall_review_state": _to_text(summary.get("overall_review_state")),
            "pa8_review_state": _to_text(summary.get("pa8_review_state")),
            "scene_bias_review_state": _to_text(summary.get("scene_bias_review_state")),
            "review_order": list(summary.get("review_order", []) or []),
            "primary_review_symbols": list(summary.get("primary_review_symbols", []) or []),
            "support_review_symbols": list(summary.get("support_review_symbols", []) or []),
            "recommended_next_action": _to_text(summary.get("recommended_next_action")),
            "scene_bias_note": _to_text(summary.get("scene_bias_separation_note")),
        },
        "checklist_rows": checklist_rows,
    }


def render_checkpoint_pa8_action_review_checklist_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = body.get("checklist_rows")
    if not isinstance(rows, list):
        rows = []

    lines: list[str] = []
    lines.append("# PA8 Action-Only Review Checklist")
    lines.append("")
    lines.append(f"- overall_review_state: `{_to_text(summary.get('overall_review_state'))}`")
    lines.append(f"- pa8_review_state: `{_to_text(summary.get('pa8_review_state'))}`")
    lines.append(f"- scene_bias_review_state: `{_to_text(summary.get('scene_bias_review_state'))}`")
    lines.append(f"- review_order: `{', '.join(summary.get('review_order', []) or [])}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append(f"- scene_bias_note: `{_to_text(summary.get('scene_bias_note'))}`")
    lines.append("")

    for row in rows:
        if not isinstance(row, Mapping):
            continue
        metrics = _mapping(row.get("current_metrics"))
        lines.append(f"## {row.get('review_order')}. {_to_text(row.get('symbol')).upper()}")
        lines.append("")
        lines.append(f"- review_state: `{_to_text(row.get('review_state'))}`")
        lines.append(f"- goal: {_to_text(row.get('goal'))}")
        lines.append("- current_metrics:")
        lines.append(f"  - resolved_row_count: `{_to_int(metrics.get('resolved_row_count'))}`")
        lines.append(f"  - live_runner_source_row_count: `{_to_int(metrics.get('live_runner_source_row_count'))}`")
        lines.append(f"  - runtime_proxy_match_rate: `{_format_metric(_to_float(metrics.get('runtime_proxy_match_rate')))}`")
        lines.append(f"  - hold_precision: `{_format_metric(_to_float(metrics.get('hold_precision')))}`")
        lines.append(
            f"  - partial_then_hold_quality: `{_format_metric(_to_float(metrics.get('partial_then_hold_quality')))}`"
        )
        lines.append(f"  - full_exit_precision: `{_format_metric(_to_float(metrics.get('full_exit_precision')))}`")
        lines.append("- blockers:")
        for blocker in list(row.get("blockers", []) or []):
            lines.append(f"  - `{_to_text(blocker)}`")
        lines.append("- pass_criteria:")
        for item in list(row.get("pass_criteria", []) or []):
            lines.append(f"  - {item}")
        lines.append("- check_items:")
        for item in list(row.get("check_items", []) or []):
            lines.append(f"  - [ ] {item}")
        lines.append("- decision_options:")
        for item in list(row.get("decision_options", []) or []):
            lines.append(f"  - {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
