from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_provisional_canary_review_packet_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json"
    )


def default_checkpoint_pa8_nas100_provisional_canary_review_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_provisional_canary_review_packet_latest.md"
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


def _symbol_row(payload: Mapping[str, Any] | None, symbol: str) -> dict[str, Any]:
    body = _mapping(payload)
    rows = body.get("symbol_rows")
    if not isinstance(rows, list):
        return {}
    symbol_upper = symbol.upper()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if _to_text(row.get("symbol")).upper() == symbol_upper:
            return dict(row)
    return {}


def build_checkpoint_pa8_nas100_provisional_canary_review_packet(
    *,
    pa8_action_review_packet_payload: Mapping[str, Any] | None,
    nas100_symbol_review_payload: Mapping[str, Any] | None,
    nas100_profit_hold_bias_preview_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pa8_packet = _mapping(pa8_action_review_packet_payload)
    pa8_summary = _mapping(pa8_packet.get("summary"))
    nas100_packet_row = _symbol_row(pa8_packet, "NAS100")
    symbol_review = _mapping(nas100_symbol_review_payload)
    symbol_review_summary = _mapping(symbol_review.get("summary"))
    preview = _mapping(nas100_profit_hold_bias_preview_payload)
    preview_summary = _mapping(preview.get("summary"))

    blockers: list[str] = []
    action_baseline_review_ready = bool(pa8_summary.get("action_baseline_review_ready"))
    if not action_baseline_review_ready:
        blockers.append("pa8_action_baseline_review_not_ready")
    if _to_text(pa8_summary.get("pa8_review_state")) != "READY_FOR_ACTION_BASELINE_REVIEW":
        blockers.append("pa8_review_state_not_ready")
    if _to_text(symbol_review_summary.get("review_result")) != "narrow_hold_boundary_candidate_identified":
        blockers.append("nas100_symbol_review_not_narrow_boundary_candidate")

    eligible_row_count = _to_int(preview_summary.get("eligible_row_count"))
    preview_changed_row_count = _to_int(preview_summary.get("preview_changed_row_count"))
    improved_row_count = _to_int(preview_summary.get("improved_row_count"))
    worsened_row_count = _to_int(preview_summary.get("worsened_row_count"))
    baseline_hold_precision = _to_float(preview_summary.get("baseline_hold_precision"))
    preview_hold_precision = _to_float(preview_summary.get("preview_hold_precision"))
    baseline_runtime_proxy_match_rate = _to_float(preview_summary.get("baseline_runtime_proxy_match_rate"))
    preview_runtime_proxy_match_rate = _to_float(preview_summary.get("preview_runtime_proxy_match_rate"))
    baseline_partial_then_hold_quality = _to_float(preview_summary.get("baseline_partial_then_hold_quality"))
    preview_partial_then_hold_quality = _to_float(preview_summary.get("preview_partial_then_hold_quality"))

    if eligible_row_count < 50:
        blockers.append("preview_eligible_row_count_below_floor")
    if preview_changed_row_count <= 0:
        blockers.append("preview_changed_row_count_zero")
    if worsened_row_count > 0:
        blockers.append("preview_has_worsened_rows")
    if preview_hold_precision < 0.80:
        blockers.append("preview_hold_precision_below_floor")
    if preview_runtime_proxy_match_rate <= baseline_runtime_proxy_match_rate:
        blockers.append("preview_runtime_proxy_match_rate_not_improved")
    if preview_partial_then_hold_quality + 0.000001 < baseline_partial_then_hold_quality:
        blockers.append("preview_partial_then_hold_quality_regressed")

    provisional_canary_ready = len(blockers) == 0
    canary_review_state = (
        "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW"
        if provisional_canary_ready
        else "HOLD_PREVIEW_ONLY_REVIEW"
    )
    recommended_next_action = (
        "prepare_nas100_action_only_provisional_canary_scope"
        if provisional_canary_ready
        else "keep_nas100_profit_hold_bias_preview_only"
    )

    casebook_examples = list(preview_summary.get("casebook_examples", []) or [])

    summary = {
        "contract_version": "checkpoint_pa8_action_canary_review_packet_v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "symbol": "NAS100",
        "pa8_review_state": _to_text(pa8_summary.get("pa8_review_state")),
        "scene_bias_review_state": _to_text(pa8_summary.get("scene_bias_review_state")),
        "action_baseline_review_ready": action_baseline_review_ready,
        "nas100_review_state": _to_text(nas100_packet_row.get("review_state")),
        "nas100_review_result": _to_text(symbol_review_summary.get("review_result")),
        "canary_review_state": canary_review_state,
        "provisional_canary_ready": provisional_canary_ready,
        "blockers": blockers,
        "eligible_row_count": eligible_row_count,
        "preview_changed_row_count": preview_changed_row_count,
        "improved_row_count": improved_row_count,
        "worsened_row_count": worsened_row_count,
        "baseline_hold_precision": round(baseline_hold_precision, 6),
        "preview_hold_precision": round(preview_hold_precision, 6),
        "baseline_runtime_proxy_match_rate": round(baseline_runtime_proxy_match_rate, 6),
        "preview_runtime_proxy_match_rate": round(preview_runtime_proxy_match_rate, 6),
        "baseline_partial_then_hold_quality": round(baseline_partial_then_hold_quality, 6),
        "preview_partial_then_hold_quality": round(preview_partial_then_hold_quality, 6),
        "target_metric_goal": "raise_hold_precision_to_at_least_0.80_without_scene_bias_changes",
        "recommended_next_action": recommended_next_action,
        "casebook_examples": casebook_examples[:10],
    }

    return {
        "summary": summary,
        "candidate_scope": {
            "symbol_allowlist": ["NAS100"],
            "surface_allowlist": ["continuation_hold_surface"],
            "checkpoint_type_allowlist": ["RUNNER_CHECK"],
            "family_allowlist": ["profit_hold_bias"],
            "baseline_action_allowlist": ["HOLD"],
            "preview_action": "PARTIAL_THEN_HOLD",
            "preview_reason": "nas100_profit_hold_bias_hold_to_partial_then_hold_preview",
            "change_mode": "action_only_preview_candidate",
            "scene_bias_mode": "preview_only_excluded_from_canary_scope",
        },
        "canary_guardrails": {
            "sample_floor": 50,
            "worsened_row_count_ceiling": 0,
            "hold_precision_floor": 0.80,
            "runtime_proxy_match_rate_must_improve": True,
            "partial_then_hold_quality_must_not_regress": True,
            "rollback_watch_metrics": [
                "hold_precision_drop_below_baseline",
                "preview_partial_then_hold_quality_regression",
                "new_worsened_rows_detected",
            ],
        },
        "review_context": {
            "pa8_packet_symbol_row": nas100_packet_row,
            "symbol_review_summary": symbol_review_summary,
            "preview_summary": preview_summary,
        },
    }


def render_checkpoint_pa8_nas100_provisional_canary_review_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    candidate_scope = _mapping(body.get("candidate_scope"))
    guardrails = _mapping(body.get("canary_guardrails"))
    examples = list(summary.get("casebook_examples", []) or [])

    lines: list[str] = []
    lines.append("# PA8 NAS100 Provisional Action-Only Canary Review")
    lines.append("")
    lines.append(f"- canary_review_state: `{_to_text(summary.get('canary_review_state'))}`")
    lines.append(f"- provisional_canary_ready: `{summary.get('provisional_canary_ready', False)}`")
    lines.append(f"- pa8_review_state: `{_to_text(summary.get('pa8_review_state'))}`")
    lines.append(f"- scene_bias_review_state: `{_to_text(summary.get('scene_bias_review_state'))}`")
    lines.append(f"- eligible_row_count: `{_to_int(summary.get('eligible_row_count'))}`")
    lines.append(f"- preview_changed_row_count: `{_to_int(summary.get('preview_changed_row_count'))}`")
    lines.append(f"- improved_row_count: `{_to_int(summary.get('improved_row_count'))}`")
    lines.append(f"- worsened_row_count: `{_to_int(summary.get('worsened_row_count'))}`")
    lines.append(f"- baseline_hold_precision: `{_to_float(summary.get('baseline_hold_precision'))}`")
    lines.append(f"- preview_hold_precision: `{_to_float(summary.get('preview_hold_precision'))}`")
    lines.append(
        f"- baseline_runtime_proxy_match_rate: `{_to_float(summary.get('baseline_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- preview_runtime_proxy_match_rate: `{_to_float(summary.get('preview_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- baseline_partial_then_hold_quality: `{_to_float(summary.get('baseline_partial_then_hold_quality'))}`"
    )
    lines.append(
        f"- preview_partial_then_hold_quality: `{_to_float(summary.get('preview_partial_then_hold_quality'))}`"
    )
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Candidate Scope")
    lines.append("")
    lines.append(f"- symbol_allowlist: `{json.dumps(candidate_scope.get('symbol_allowlist', []))}`")
    lines.append(f"- surface_allowlist: `{json.dumps(candidate_scope.get('surface_allowlist', []))}`")
    lines.append(
        f"- checkpoint_type_allowlist: `{json.dumps(candidate_scope.get('checkpoint_type_allowlist', []))}`"
    )
    lines.append(f"- family_allowlist: `{json.dumps(candidate_scope.get('family_allowlist', []))}`")
    lines.append(f"- baseline_action_allowlist: `{json.dumps(candidate_scope.get('baseline_action_allowlist', []))}`")
    lines.append(f"- preview_action: `{_to_text(candidate_scope.get('preview_action'))}`")
    lines.append(f"- scene_bias_mode: `{_to_text(candidate_scope.get('scene_bias_mode'))}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append(f"- sample_floor: `{_to_int(guardrails.get('sample_floor'))}`")
    lines.append(f"- worsened_row_count_ceiling: `{_to_int(guardrails.get('worsened_row_count_ceiling'))}`")
    lines.append(f"- hold_precision_floor: `{_to_float(guardrails.get('hold_precision_floor'))}`")
    lines.append(
        f"- runtime_proxy_match_rate_must_improve: `{guardrails.get('runtime_proxy_match_rate_must_improve', False)}`"
    )
    lines.append(
        f"- partial_then_hold_quality_must_not_regress: `{guardrails.get('partial_then_hold_quality_must_not_regress', False)}`"
    )
    blockers = list(summary.get("blockers", []) or [])
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{_to_text(blocker)}`")
    else:
        lines.append("- `none`")
    lines.append("")
    lines.append("## Casebook Examples")
    lines.append("")
    for index, example in enumerate(examples[:10], start=1):
        if not isinstance(example, Mapping):
            continue
        lines.append(f"### {index}. {_to_text(example.get('checkpoint_id'))}")
        lines.append("")
        lines.append(
            f"- action_path: `{_to_text(example.get('baseline_action_label'))} -> {_to_text(example.get('preview_action_label'))} -> {_to_text(example.get('hindsight_best_management_action_label'))}`"
        )
        lines.append(f"- family: `{_to_text(example.get('checkpoint_rule_family_hint'))}`")
        lines.append(f"- current_profit: `{_to_float(example.get('current_profit'))}`")
        lines.append(f"- runtime_hold_quality_score: `{_to_float(example.get('runtime_hold_quality_score'))}`")
        lines.append(f"- runtime_partial_exit_ev: `{_to_float(example.get('runtime_partial_exit_ev'))}`")
        lines.append(f"- runtime_full_exit_risk: `{_to_float(example.get('runtime_full_exit_risk'))}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
