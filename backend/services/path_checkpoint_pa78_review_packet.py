from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa78_review_packet_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa78_review_packet_latest.json"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def build_checkpoint_pa78_review_packet(
    *,
    action_eval_payload: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any] | None,
    live_runner_watch_payload: Mapping[str, Any] | None,
    pa7_review_processor_payload: Mapping[str, Any] | None,
    scene_disagreement_payload: Mapping[str, Any] | None,
    scene_bias_preview_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    action_eval = _mapping(action_eval_payload)
    action_eval_summary = _mapping(action_eval.get("summary"))
    observation = _mapping(observation_payload)
    observation_summary = _mapping(observation.get("summary"))
    live_runner_watch = _mapping(live_runner_watch_payload)
    live_runner_summary = _mapping(live_runner_watch.get("summary"))
    pa7_review_processor = _mapping(pa7_review_processor_payload)
    pa7_review_processor_summary = _mapping(pa7_review_processor.get("summary"))
    scene_disagreement = _mapping(scene_disagreement_payload)
    scene_disagreement_summary = _mapping(scene_disagreement.get("summary"))
    scene_bias_preview = _mapping(scene_bias_preview_payload)
    scene_bias_preview_summary = _mapping(scene_bias_preview.get("summary"))

    resolved_row_count = _to_int(action_eval_summary.get("resolved_row_count"))
    live_runner_source_row_count = _to_int(live_runner_summary.get("live_runner_source_row_count"))
    runtime_proxy_match_rate = _to_float(action_eval_summary.get("runtime_proxy_match_rate"))
    hold_precision = _to_float(action_eval_summary.get("hold_precision"))
    partial_then_hold_quality = _to_float(action_eval_summary.get("partial_then_hold_quality"))
    full_exit_precision = _to_float(action_eval_summary.get("full_exit_precision"))
    manual_exception_count = _to_int(action_eval_summary.get("manual_exception_count"))
    high_conf_scene_disagreement_count = _to_int(scene_disagreement_summary.get("high_conf_scene_disagreement_count"))
    scene_expected_action_alignment_rate = _to_float(
        scene_disagreement_summary.get("expected_action_alignment_rate")
    )
    preview_improved_row_count = _to_int(scene_bias_preview_summary.get("improved_row_count"))
    preview_worsened_row_count = _to_int(scene_bias_preview_summary.get("worsened_row_count"))
    preview_changed_row_count = _to_int(scene_bias_preview_summary.get("preview_changed_row_count"))
    preview_match_rate = _to_float(scene_bias_preview_summary.get("preview_hindsight_match_rate"))
    baseline_preview_match_rate = _to_float(scene_bias_preview_summary.get("baseline_hindsight_match_rate"))
    pa7_disposition_counts = dict(pa7_review_processor_summary.get("review_disposition_counts", {}) or {})
    pa7_processed_group_count = _to_int(pa7_review_processor_summary.get("processed_group_count"))

    pa7_unresolved_review_group_count = sum(
        _to_int(pa7_disposition_counts.get(key))
        for key in (
            "policy_mismatch_review",
            "baseline_hydration_gap",
            "mixed_backfill_value_scale_review",
            "mixed_wait_boundary_review",
            "mixed_review",
        )
    )
    pa7_resolved_review_group_count = sum(
        _to_int(pa7_disposition_counts.get(key))
        for key in (
            "resolved_by_current_policy",
            "hydration_gap_resolved_by_current_policy",
            "hydration_gap_confirmed_cluster",
            "confidence_only_confirmed",
        )
    )

    pa7_data_ready = bool(
        resolved_row_count >= 4000
        and live_runner_source_row_count >= 100
        and hold_precision >= 0.84
        and full_exit_precision >= 0.99
    )

    action_baseline_review_ready = bool(
        pa7_data_ready
        and pa7_processed_group_count > 0
        and pa7_unresolved_review_group_count == 0
        and runtime_proxy_match_rate >= 0.92
        and hold_precision >= 0.84
        and partial_then_hold_quality >= 0.95
        and full_exit_precision >= 0.99
    )

    trend_exhaustion_preview_positive = bool(
        preview_changed_row_count > 0
        and preview_improved_row_count > 0
        and preview_worsened_row_count == 0
        and preview_match_rate >= baseline_preview_match_rate
    )

    scene_bias_review_ready = bool(
        action_baseline_review_ready
        and trend_exhaustion_preview_positive
        and high_conf_scene_disagreement_count <= 500
        and scene_expected_action_alignment_rate >= 0.95
    )

    if not pa7_data_ready:
        pa7_state = "HOLD_REVIEW_PACKET"
    elif pa7_unresolved_review_group_count > 0:
        pa7_state = "READY_FOR_REVIEW"
    else:
        pa7_state = "REVIEW_PACKET_PROCESSED"

    if action_baseline_review_ready:
        pa8_state = "READY_FOR_ACTION_BASELINE_REVIEW"
    else:
        pa8_state = "HOLD_ACTION_BASELINE_ALIGNMENT"

    if scene_bias_review_ready:
        scene_bias_state = "READY_FOR_SCENE_BOUNDED_ADOPTION_REVIEW"
    elif action_baseline_review_ready and trend_exhaustion_preview_positive:
        scene_bias_state = "HOLD_PREVIEW_ONLY_SCENE_BIAS"
    else:
        scene_bias_state = "HOLD_SCENE_ALIGNMENT"

    blockers: list[str] = []
    if resolved_row_count < 4000:
        blockers.append("resolved_row_count_below_review_floor")
    if live_runner_source_row_count < 100:
        blockers.append("live_runner_source_row_count_too_low")
    if pa7_unresolved_review_group_count > 0:
        blockers.append("pa7_unresolved_review_groups_remain")
    if runtime_proxy_match_rate < 0.92:
        blockers.append("runtime_proxy_match_rate_below_action_review_floor")
    if hold_precision < 0.84:
        blockers.append("hold_precision_below_action_review_floor")
    if partial_then_hold_quality < 0.95:
        blockers.append("partial_then_hold_quality_below_action_review_floor")
    if full_exit_precision < 0.99:
        blockers.append("full_exit_precision_below_action_review_floor")
    if not trend_exhaustion_preview_positive:
        blockers.append("trend_exhaustion_scene_bias_not_preview_positive")
    if high_conf_scene_disagreement_count > 500:
        blockers.append("scene_high_conf_disagreement_still_high_for_pa8")
    if scene_expected_action_alignment_rate < 0.95:
        blockers.append("scene_expected_action_alignment_below_pa8_floor")
    if action_baseline_review_ready and trend_exhaustion_preview_positive and not scene_bias_review_ready:
        blockers.append("trend_exhaustion_scene_bias_preview_only")

    if not pa7_data_ready:
        recommended_next_action = "keep_collecting_checkpoint_rows_before_pa7_review"
    elif pa7_unresolved_review_group_count > 0:
        recommended_next_action = "work_through_pa7_review_groups_before_pa8"
    elif action_baseline_review_ready and scene_bias_review_ready:
        recommended_next_action = "prepare_pa8_action_and_scene_bounded_adoption_review"
    elif action_baseline_review_ready:
        recommended_next_action = "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only"
    else:
        recommended_next_action = "stabilize_action_baseline_review_packet"

    return {
        "summary": {
            "contract_version": "checkpoint_pa78_review_packet_v2",
            "generated_at": datetime.now().astimezone().isoformat(),
            "resolved_row_count": resolved_row_count,
            "position_side_row_count": _to_int(observation_summary.get("position_side_row_count")),
            "live_runner_source_row_count": live_runner_source_row_count,
            "recent_live_runner_source_row_count": _to_int(live_runner_summary.get("recent_live_runner_source_row_count")),
            "runtime_proxy_match_rate": round(runtime_proxy_match_rate, 6),
            "hold_precision": round(hold_precision, 6),
            "partial_then_hold_quality": round(partial_then_hold_quality, 6),
            "full_exit_precision": round(full_exit_precision, 6),
            "manual_exception_count": manual_exception_count,
            "high_conf_scene_disagreement_count": high_conf_scene_disagreement_count,
            "scene_expected_action_alignment_rate": round(scene_expected_action_alignment_rate, 6),
            "trend_exhaustion_preview_changed_row_count": preview_changed_row_count,
            "trend_exhaustion_preview_improved_row_count": preview_improved_row_count,
            "trend_exhaustion_preview_worsened_row_count": preview_worsened_row_count,
            "trend_exhaustion_preview_match_rate": round(preview_match_rate, 6),
            "trend_exhaustion_preview_positive": trend_exhaustion_preview_positive,
            "pa7_processed_group_count": pa7_processed_group_count,
            "pa7_unresolved_review_group_count": pa7_unresolved_review_group_count,
            "pa7_resolved_review_group_count": pa7_resolved_review_group_count,
            "pa7_review_state": pa7_state,
            "pa8_review_state": pa8_state,
            "scene_bias_review_state": scene_bias_state,
            "action_baseline_review_ready": action_baseline_review_ready,
            "scene_bias_review_ready": scene_bias_review_ready,
            "blockers": blockers,
            "recommended_next_action": recommended_next_action,
        },
        "review_axes": {
            "action_eval": {
                "resolved_row_count": resolved_row_count,
                "runtime_proxy_match_rate": round(runtime_proxy_match_rate, 6),
                "hold_precision": round(hold_precision, 6),
                "partial_then_hold_quality": round(partial_then_hold_quality, 6),
                "full_exit_precision": round(full_exit_precision, 6),
                "manual_exception_count": manual_exception_count,
                "hindsight_label_counts": dict(action_eval_summary.get("hindsight_label_counts", {}) or {}),
            },
            "pa7_review_processor": {
                "processed_group_count": pa7_processed_group_count,
                "unresolved_review_group_count": pa7_unresolved_review_group_count,
                "resolved_review_group_count": pa7_resolved_review_group_count,
                "review_disposition_counts": pa7_disposition_counts,
                "recommended_next_action": _to_text(pa7_review_processor_summary.get("recommended_next_action")),
            },
            "position_side_observation": {
                "position_side_row_count": _to_int(observation_summary.get("position_side_row_count")),
                "open_profit_row_count": _to_int(observation_summary.get("open_profit_row_count")),
                "open_loss_row_count": _to_int(observation_summary.get("open_loss_row_count")),
                "runner_secured_row_count": _to_int(observation_summary.get("runner_secured_row_count")),
                "live_runner_source_row_count": live_runner_source_row_count,
                "source_counts": dict(observation_summary.get("source_counts", {}) or {}),
                "family_counts": dict(observation_summary.get("family_counts", {}) or {}),
            },
            "scene_disagreement": {
                "high_conf_scene_disagreement_count": high_conf_scene_disagreement_count,
                "scene_expected_action_alignment_rate": round(scene_expected_action_alignment_rate, 6),
                "candidate_selected_label_counts": dict(
                    scene_disagreement_summary.get("candidate_selected_label_counts", {}) or {}
                ),
            },
            "scene_bias_preview": {
                "preview_changed_row_count": preview_changed_row_count,
                "improved_row_count": preview_improved_row_count,
                "worsened_row_count": preview_worsened_row_count,
                "baseline_hindsight_match_rate": round(baseline_preview_match_rate, 6),
                "preview_hindsight_match_rate": round(preview_match_rate, 6),
                "recommended_next_action": _to_text(scene_bias_preview_summary.get("recommended_next_action")),
            },
        },
    }
