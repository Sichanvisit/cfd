from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.r0_row_interpretation import (
    build_r0_row_interpretation_v1,
    resolve_r0_probe_state,
    resolve_r0_reason_triplet,
)
from backend.services.entry_wait_context_bias_bundle import compact_entry_wait_bias_bundle_v1
from backend.services.entry_wait_context_contract import compact_entry_wait_context_v1
from backend.services.entry_wait_state_policy_contract import compact_entry_wait_state_policy_input_v1
from backend.services.exit_manage_context_contract import compact_exit_manage_context_v1
from backend.services.exit_wait_state_surface_contract import compact_exit_wait_state_surface_v1
from backend.services.exit_wait_taxonomy_contract import compact_exit_wait_taxonomy_v1


ENTRY_DECISION_DETAIL_SCHEMA_VERSION = "entry_decision_detail_v1"
RUNTIME_STATUS_DETAIL_SCHEMA_VERSION = "runtime_status_detail_v1"
ENTRY_DECISION_DETAIL_ROTATION_POLICY_VERSION = "entry_decision_detail_rotation_v1"
ENTRY_DECISION_DETAIL_ROTATED_MARKER = "rotate"
ENTRY_TRACE_REQUIRED_FIELDS = (
    "position_snapshot_v2",
    "response_vector_v2",
    "state_vector_v2",
    "evidence_vector_v1",
    "belief_state_v1",
    "barrier_state_v1",
    "forecast_features_v1",
    "transition_forecast_v1",
    "trade_management_forecast_v1",
    "observe_confirm_v1",
)

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool) -> bool:
    text = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    return text not in {"", "0", "false", "no", "off"}


DEFAULT_ENTRY_DECISION_DETAIL_ROTATE_MAX_BYTES = int(
    os.getenv("ENTRY_DECISION_DETAIL_ROTATE_MAX_BYTES", str(256 * 1024 * 1024))
)
DEFAULT_ENTRY_DECISION_DETAIL_ROTATE_DAILY = _env_flag("ENTRY_DECISION_DETAIL_ROTATE_DAILY", True)
DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_DAYS = int(os.getenv("ENTRY_DECISION_DETAIL_RETENTION_DAYS", "14"))
DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_COUNT = int(os.getenv("ENTRY_DECISION_DETAIL_RETENTION_COUNT", "14"))

# Raw payloads, contracts, migration traces, and comments move to detail storage.
ENTRY_DECISION_DETAIL_ONLY_COLUMNS = {
    "prediction_bundle",
    "prs_canonical_position_effective_field",
    "prs_canonical_response_effective_field",
    "prs_canonical_state_effective_field",
    "prs_canonical_evidence_effective_field",
    "prs_canonical_belief_effective_field",
    "prs_canonical_barrier_effective_field",
    "prs_canonical_forecast_effective_field",
    "energy_migration_contract_field",
    "energy_scope_contract_field",
    "runtime_alignment_scope_contract_field",
    "energy_compatibility_runtime_field",
    "energy_logging_replay_contract_field",
    "energy_snapshot",
    "energy_logging_replay_contract_v1",
    "energy_migration_dual_write_v1",
    "energy_migration_guard_v1",
    "energy_scope_contract_v1",
    "runtime_alignment_scope_contract_v1",
    "observe_confirm_input_contract_v2",
    "observe_confirm_migration_dual_write_v1",
    "observe_confirm_output_contract_v2",
    "observe_confirm_scope_contract_v1",
    "consumer_input_contract_v1",
    "consumer_migration_freeze_v1",
    "consumer_migration_guard_v1",
    "consumer_logging_contract_v1",
    "consumer_test_contract_v1",
    "consumer_freeze_handoff_v1",
    "layer_mode_contract_v1",
    "layer_mode_layer_inventory_v1",
    "layer_mode_default_policy_v1",
    "layer_mode_dual_write_contract_v1",
    "layer_mode_influence_semantics_v1",
    "layer_mode_application_contract_v1",
    "layer_mode_identity_guard_contract_v1",
    "layer_mode_policy_overlay_output_contract_v1",
    "layer_mode_logging_replay_contract_v1",
    "layer_mode_test_contract_v1",
    "layer_mode_freeze_handoff_v1",
    "setup_detector_responsibility_contract_v1",
    "setup_mapping_contract_v1",
    "entry_guard_contract_v1",
    "entry_service_responsibility_contract_v1",
    "exit_handoff_contract_v1",
    "re_entry_contract_v1",
    "consumer_scope_contract_v1",
    "consumer_layer_mode_integration_v1",
    "consumer_input_contract_version",
    "consumer_migration_contract_version",
    "consumer_used_compatibility_fallback_v1",
    "consumer_policy_input_field",
    "consumer_policy_contract_version",
    "consumer_policy_identity_preserved",
    "layer_mode_scope_contract_v1",
    "layer_mode_effective_trace_v1",
    "layer_mode_influence_trace_v1",
    "layer_mode_application_trace_v1",
    "layer_mode_identity_guard_trace_v1",
    "layer_mode_policy_v1",
    "layer_mode_logging_replay_v1",
    "forecast_calibration_contract_v1",
    "outcome_labeler_scope_contract_v1",
    "position_snapshot_effective_v1",
    "response_raw_snapshot_v1",
    "response_vector_effective_v1",
    "state_raw_snapshot_v1",
    "state_vector_effective_v1",
    "evidence_vector_effective_v1",
    "belief_state_effective_v1",
    "barrier_state_effective_v1",
    "forecast_effective_policy_v1",
    "shadow_state_v1",
    "shadow_action_v1",
    "shadow_reason_v1",
    "shadow_buy_force_v1",
    "shadow_sell_force_v1",
    "shadow_net_force_v1",
    "last_order_comment",
}


def resolve_runtime_status_detail_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.detail{path.suffix}")


def resolve_entry_decision_detail_path(path: Path) -> Path:
    return path.with_suffix(".detail.jsonl")


def resolve_entry_decision_rotated_detail_path(path: Path, *, timestamp: str) -> Path:
    detail_path = resolve_entry_decision_detail_path(path)
    return detail_path.with_name(
        f"{detail_path.stem}.{ENTRY_DECISION_DETAIL_ROTATED_MARKER}_{timestamp}{detail_path.suffix}"
    )


def resolve_entry_decision_rotated_detail_glob(path: Path) -> str:
    detail_path = resolve_entry_decision_detail_path(path)
    return f"{detail_path.stem}.{ENTRY_DECISION_DETAIL_ROTATED_MARKER}_*{detail_path.suffix}"


def rotate_entry_decision_detail_if_needed(
    path: Path,
    *,
    now: datetime | None = None,
    max_bytes: int | None = None,
    roll_daily: bool | None = None,
) -> dict[str, Any]:
    detail_path = resolve_entry_decision_detail_path(path)
    current_now = now or datetime.now()
    max_bytes = int(max_bytes or DEFAULT_ENTRY_DECISION_DETAIL_ROTATE_MAX_BYTES)
    roll_daily = DEFAULT_ENTRY_DECISION_DETAIL_ROTATE_DAILY if roll_daily is None else bool(roll_daily)
    result: dict[str, Any] = {
        "contract_version": ENTRY_DECISION_DETAIL_ROTATION_POLICY_VERSION,
        "detail_path": str(detail_path),
        "rotated": False,
        "reasons": [],
        "max_bytes": int(max_bytes),
        "roll_daily": bool(roll_daily),
        "rotated_path": "",
        "source_size_bytes": 0,
        "source_modified_at": "",
        "error": "",
    }
    if not detail_path.exists():
        return result

    try:
        stat = detail_path.stat()
        source_size_bytes = int(stat.st_size)
        result["source_size_bytes"] = source_size_bytes
        if source_size_bytes <= 0:
            return result
        modified_at = datetime.fromtimestamp(stat.st_mtime)
        result["source_modified_at"] = modified_at.isoformat(timespec="seconds")
        reasons: list[str] = []
        if source_size_bytes >= int(max_bytes):
            reasons.append("size_limit")
        if bool(roll_daily) and modified_at.date() < current_now.date():
            reasons.append("day_boundary")
        if not reasons:
            return result

        timestamp = current_now.strftime("%Y%m%d_%H%M%S_%f")
        rotated_path = resolve_entry_decision_rotated_detail_path(path, timestamp=timestamp)
        rotated_path.parent.mkdir(parents=True, exist_ok=True)
        detail_path.replace(rotated_path)
        result["rotated"] = True
        result["reasons"] = list(reasons)
        result["rotated_path"] = str(rotated_path)
        result["rotated_size_bytes"] = int(rotated_path.stat().st_size)
        result["rotation_mode"] = "rename_shard"
        return result
    except PermissionError as exc:
        logger.debug("entry decision detail rotation deferred: %s", str(exc))
        result["error"] = str(exc)
        return result
    except Exception as exc:
        logger.exception("entry decision detail rotation failed")
        result["error"] = str(exc)
        return result


def _is_simple_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_simple_sequence(value: Any) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    return len(value) <= 12 and all(_is_simple_scalar(item) for item in value)


def _is_simple_value(value: Any) -> bool:
    return _is_simple_scalar(value) or _is_simple_sequence(value)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return {}


def _compact_scalar_mapping(
    value: Any,
    *,
    nested_keys: Mapping[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    nested_keys = dict(nested_keys or {})

    for key, item in payload.items():
        if key in nested_keys:
            continue
        if _is_simple_value(item):
            compact[str(key)] = item

    for parent_key, child_keys in nested_keys.items():
        nested = _coerce_mapping(payload.get(parent_key))
        nested_compact = {
            str(child_key): nested.get(child_key)
            for child_key in child_keys
            if nested.get(child_key) not in ("", None) and _is_simple_value(nested.get(child_key))
        }
        if nested_compact:
            compact[str(parent_key)] = nested_compact

    return compact


def _compact_position_snapshot(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}

    zones = _compact_scalar_mapping(payload.get("zones"))
    if zones:
        compact["zones"] = zones

    interpretation = _compact_scalar_mapping(payload.get("interpretation"))
    if interpretation:
        compact["interpretation"] = interpretation

    energy = _compact_scalar_mapping(payload.get("energy"))
    if energy:
        compact["energy"] = energy

    vector = _compact_scalar_mapping(payload.get("vector"))
    if vector:
        compact["vector"] = vector

    return compact


def _compact_forecast_payload(value: Any, *, metadata_keys: tuple[str, ...]) -> dict[str, Any]:
    return _compact_scalar_mapping(value, nested_keys={"metadata": metadata_keys})


def _compact_observe_confirm(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in (
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
    ):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item

    metadata = _coerce_mapping(payload.get("metadata"))
    metadata_compact: dict[str, Any] = {}
    for key in ("blocked_reason", "effective_action", "guard_result"):
        item = metadata.get(key)
        if _is_simple_value(item):
            metadata_compact[key] = item
    winning_evidence = metadata.get("winning_evidence")
    if _is_simple_sequence(winning_evidence):
        metadata_compact["winning_evidence"] = list(winning_evidence)
    if metadata_compact:
        compact["metadata"] = metadata_compact
    return compact


def _to_simple_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _infer_direction_from_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip().lower()
        if not text:
            continue
        if "buy" in text or "lower_rebound" in text or "lower_hold" in text or "mid_reclaim" in text:
            return "BUY"
        if "sell" in text or "upper_reject" in text or "upper_break_fail" in text or "mid_lose" in text:
            return "SELL"
    return ""


def _infer_direction_from_zone(*values: Any) -> str:
    for value in values:
        zone = str(value or "").strip().upper()
        if zone in {"LOWER", "LOWER_EDGE", "BELOW", "BREAKDOWN"}:
            return "BUY"
        if zone in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}:
            return "SELL"
    return ""


def _resolve_observe_identity(payload: Mapping[str, Any] | None) -> tuple[str, str]:
    source = _coerce_mapping(payload)
    observe_v2 = _coerce_mapping(source.get("observe_confirm_v2"))
    observe_v1 = _coerce_mapping(source.get("observe_confirm_v1"))
    observe_v2_meta = _coerce_mapping(observe_v2.get("metadata"))
    observe_v1_meta = _coerce_mapping(observe_v1.get("metadata"))
    probe_candidate = _coerce_mapping(source.get("probe_candidate_v1"))
    edge_pair_law = _coerce_mapping(source.get("edge_pair_law_v1"))

    action = _pick_text(
        source.get("observe_action"),
        observe_v2.get("action"),
        observe_v1.get("action"),
    ).upper()
    side = _pick_text(
        source.get("observe_side"),
        observe_v2.get("side"),
        observe_v1.get("side"),
    ).upper()
    if not side and action in {"BUY", "SELL"}:
        side = action

    inferred_side = (
        side
        or _pick_text(
            probe_candidate.get("probe_direction"),
            edge_pair_law.get("winner_side"),
        ).upper()
        or _infer_direction_from_text(
            source.get("observe_reason"),
            observe_v2.get("reason"),
            observe_v1.get("reason"),
            source.get("blocked_by"),
            observe_v2_meta.get("blocked_guard"),
            observe_v2_meta.get("blocked_reason"),
            observe_v1_meta.get("blocked_guard"),
            observe_v1_meta.get("blocked_reason"),
            source.get("quick_trace_reason"),
        )
        or _infer_direction_from_zone(source.get("box_state"), source.get("bb_state"))
    )
    inferred_action = action or ("WAIT" if inferred_side and _pick_text(source.get("observe_reason"), observe_v2.get("reason"), observe_v1.get("reason")) else "")
    return inferred_action, inferred_side


def build_probe_quick_trace_fields(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _coerce_mapping(payload)
    candidate = _coerce_mapping(source.get("probe_candidate_v1"))
    plan = _coerce_mapping(source.get("entry_probe_plan_v1"))
    candidate_temperament = _coerce_mapping(candidate.get("symbol_probe_temperament_v1"))
    plan_temperament = _coerce_mapping(plan.get("symbol_probe_temperament_v1"))

    observe_reason = str(source.get("observe_reason", "") or "").strip()
    blocked_by = str(source.get("blocked_by", "") or "").strip()
    action_none_reason = str(source.get("action_none_reason", "") or "").strip()

    candidate_active = bool(candidate.get("active", False))
    plan_active = bool(plan.get("active", False))
    plan_ready = bool(plan.get("ready_for_entry", False))

    candidate_scene = str(
        candidate_temperament.get("scene_id", "")
        or candidate.get("symbol_scene_relief", "")
        or ""
    ).strip()
    plan_scene = str(
        plan.get("symbol_scene_relief", "")
        or plan_temperament.get("scene_id", "")
        or candidate_scene
    ).strip()
    probe_pair_gap = _to_simple_float(plan.get("pair_gap"))
    if probe_pair_gap is None:
        probe_pair_gap = _to_simple_float(candidate.get("pair_gap"))
    candidate_support = _to_simple_float(candidate.get("candidate_support"))
    if candidate_support is None:
        candidate_support = _to_simple_float(plan.get("candidate_support"))
    candidate_bias = str(candidate_temperament.get("promotion_bias", "") or "").strip()
    plan_bias = str(plan_temperament.get("promotion_bias", "") or candidate_bias or "").strip()
    temperament_source = str(
        plan_temperament.get("source_map_id", "")
        or candidate_temperament.get("source_map_id", "")
        or ""
    ).strip()
    temperament_note = str(
        plan_temperament.get("note", "")
        or candidate_temperament.get("note", "")
        or ""
    ).strip()
    symbol_edge_execution = _coerce_mapping(source.get("symbol_edge_execution_overrides_v1"))
    edge_execution_scene = str(symbol_edge_execution.get("scene_id", "") or "").strip()

    quick_state = ""
    if plan_ready:
        quick_state = "PROBE_READY"
    elif plan_active:
        quick_state = "PROBE_WAIT"
    elif candidate_active and blocked_by:
        quick_state = "PROBE_CANDIDATE_BLOCKED"
    elif blocked_by:
        quick_state = "BLOCKED"
    elif candidate_active:
        quick_state = "PROBE_CANDIDATE"
    elif observe_reason:
        quick_state = "OBSERVE"

    quick_reason = ""
    for item in (
        str(plan.get("reason", "") or "").strip(),
        blocked_by,
        action_none_reason,
        observe_reason,
        candidate_scene,
    ):
        if item:
            quick_reason = item
            break

    quick: dict[str, Any] = {
        "probe_candidate_active": candidate_active,
        "probe_direction": str(
            candidate.get("probe_direction", "")
            or candidate.get("intended_action", "")
            or ""
        ).strip(),
        "probe_scene_id": candidate_scene or plan_scene,
        "probe_plan_active": plan_active,
        "probe_plan_ready": plan_ready,
        "probe_plan_reason": str(plan.get("reason", "") or "").strip(),
        "probe_plan_scene": plan_scene,
        "probe_promotion_bias": plan_bias or candidate_bias,
        "probe_temperament_source": temperament_source,
        "probe_entry_style": str(
            plan_temperament.get("entry_style_hint", "")
            or candidate_temperament.get("entry_style_hint", "")
            or ""
        ).strip(),
        "probe_temperament_note": temperament_note,
        "edge_execution_scene_id": edge_execution_scene,
        "quick_trace_state": quick_state,
        "quick_trace_reason": quick_reason,
    }
    if candidate_support is not None:
        quick["probe_candidate_support"] = candidate_support
    if probe_pair_gap is not None:
        quick["probe_pair_gap"] = probe_pair_gap
    return quick


def _compact_energy_helper(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in (
        "selected_side",
        "action_readiness",
        "continuation_support",
        "reversal_support",
        "suppression_pressure",
        "forecast_support",
        "net_utility",
    ):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item

    confidence_hint = _compact_scalar_mapping(payload.get("confidence_adjustment_hint"))
    if confidence_hint:
        compact["confidence_adjustment_hint"] = confidence_hint

    soft_block_hint = _compact_scalar_mapping(payload.get("soft_block_hint"))
    if soft_block_hint:
        compact["soft_block_hint"] = soft_block_hint

    metadata = _coerce_mapping(payload.get("metadata"))
    utility_hints = _compact_scalar_mapping(_coerce_mapping(metadata.get("utility_hints")))
    if utility_hints:
        compact["metadata"] = {"utility_hints": utility_hints}

    return compact


def compact_trace_mapping(value: Any) -> dict[str, Any]:
    return _compact_scalar_mapping(
        value,
        nested_keys={
            "symbol_probe_temperament_v1": (
                "scene_id",
                "promotion_bias",
                "entry_style_hint",
                "source_map_id",
                "note",
            ),
            "symbol_edge_execution_overrides_v1": (
                "scene_id",
                "prefer_hold_to_opposite_edge",
                "reason",
                "source_map_id",
            ),
        },
    )


def compact_energy_usage_trace(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in ("contract_version", "component", "usage_source", "usage_mode"):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item
    if "live_gate_applied" in payload:
        compact["live_gate_applied"] = bool(payload.get("live_gate_applied", False))
    consumed_fields = [
        str(item).strip()
        for item in (payload.get("consumed_fields", []) or [])
        if str(item).strip()
    ]
    if consumed_fields:
        compact["consumed_fields"] = consumed_fields
    branch_records_raw = payload.get("branch_records", [])
    branch_records: list[dict[str, Any]] = []
    if isinstance(branch_records_raw, list):
        for record in branch_records_raw:
            if not isinstance(record, dict):
                continue
            branch = str(record.get("branch", "") or "").strip()
            reason = str(record.get("reason", "") or "").strip()
            compact_record: dict[str, Any] = {}
            if branch:
                compact_record["branch"] = branch
            if reason:
                compact_record["reason"] = reason
            consumed = [
                str(item).strip()
                for item in (record.get("consumed_fields", []) or [])
                if str(item).strip()
            ]
            if consumed:
                compact_record["consumed_fields"] = consumed
            if compact_record:
                branch_records.append(compact_record)
    if branch_records:
        compact["branch_records"] = branch_records
    return compact


def _compact_wait_context_surface(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    if not payload:
        return {}
    bias = _coerce_mapping(payload.get("bias"))
    policy = _coerce_mapping(payload.get("policy"))
    if "bundle" in bias or "entry_wait_state_policy_input_v1" in policy:
        compact = dict(payload)
        compact["bias"] = dict(bias)
        compact["policy"] = dict(policy)
        if "bundle" in bias:
            compact["bias"]["bundle"] = _compact_wait_bias_bundle_surface(bias.get("bundle"))
        if "entry_wait_state_policy_input_v1" in policy:
            compact["policy"]["entry_wait_state_policy_input_v1"] = _compact_wait_state_policy_input_surface(
                policy.get("entry_wait_state_policy_input_v1")
            )
        return compact
    return compact_entry_wait_context_v1(payload)


def _compact_wait_bias_bundle_surface(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    if not payload:
        return {}
    if "active_release_sources" in payload or "active_wait_lock_sources" in payload:
        threshold_adjustment = _coerce_mapping(payload.get("threshold_adjustment"))
        return {
            "contract_version": str(payload.get("contract_version", "entry_wait_bias_bundle_v1") or ""),
            "active_release_sources": [
                str(item).strip()
                for item in (payload.get("active_release_sources", []) or [])
                if str(item).strip()
            ],
            "active_wait_lock_sources": [
                str(item).strip()
                for item in (payload.get("active_wait_lock_sources", []) or [])
                if str(item).strip()
            ],
            "release_bias_count": _to_int(payload.get("release_bias_count", 0), 0),
            "wait_lock_bias_count": _to_int(payload.get("wait_lock_bias_count", 0), 0),
            "threshold_adjustment": {
                "base_soft_threshold": _to_float(threshold_adjustment.get("base_soft_threshold", 0.0), 0.0),
                "base_hard_threshold": _to_float(threshold_adjustment.get("base_hard_threshold", 0.0), 0.0),
                "effective_soft_threshold": _to_float(
                    threshold_adjustment.get("effective_soft_threshold", 0.0),
                    0.0,
                ),
                "effective_hard_threshold": _to_float(
                    threshold_adjustment.get("effective_hard_threshold", 0.0),
                    0.0,
                ),
                "combined_soft_multiplier": _to_float(
                    threshold_adjustment.get("combined_soft_multiplier", 1.0),
                    1.0,
                ),
                "combined_hard_multiplier": _to_float(
                    threshold_adjustment.get("combined_hard_multiplier", 1.0),
                    1.0,
                ),
            },
        }
    return compact_entry_wait_bias_bundle_v1(payload)


def _compact_wait_state_policy_input_surface(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    if not payload:
        return {}
    if "bias_bundle" in payload or "reason_split_v1" in payload:
        identity = _coerce_mapping(payload.get("identity"))
        market = _coerce_mapping(payload.get("market"))
        setup = _coerce_mapping(payload.get("setup"))
        scores = _coerce_mapping(payload.get("scores"))
        thresholds = _coerce_mapping(payload.get("thresholds"))
        helper_hints = _coerce_mapping(payload.get("helper_hints"))
        special_scenes = _coerce_mapping(payload.get("special_scenes"))
        bias_bundle = _coerce_mapping(payload.get("bias_bundle"))
        return {
            "contract_version": str(payload.get("contract_version", "entry_wait_state_policy_input_v1") or ""),
            "identity": dict(identity),
            "reason_split_v1": dict(_coerce_mapping(payload.get("reason_split_v1"))),
            "market": dict(market),
            "setup": dict(setup),
            "scores": dict(scores),
            "thresholds": dict(thresholds),
            "helper_hints": {
                **dict(helper_hints),
                "soft_block_active": _to_boolish(helper_hints.get("soft_block_active", False)),
                "policy_hard_block_active": _to_boolish(helper_hints.get("policy_hard_block_active", False)),
                "policy_suppressed": _to_boolish(helper_hints.get("policy_suppressed", False)),
            },
            "special_scenes": {
                **dict(special_scenes),
                "probe_active": _to_boolish(special_scenes.get("probe_active", False)),
                "probe_ready_for_entry": _to_boolish(special_scenes.get("probe_ready_for_entry", False)),
                "xau_second_support_probe_relief": _to_boolish(
                    special_scenes.get("xau_second_support_probe_relief", False)
                ),
                "btc_lower_strong_score_soft_wait_candidate": _to_boolish(
                    special_scenes.get("btc_lower_strong_score_soft_wait_candidate", False)
                ),
            },
            "bias_bundle": {
                **dict(bias_bundle),
                "release_bias_count": _to_int(bias_bundle.get("release_bias_count", 0), 0),
                "wait_lock_bias_count": _to_int(bias_bundle.get("wait_lock_bias_count", 0), 0),
            },
        }
    return compact_entry_wait_state_policy_input_v1(payload)


def _compact_exit_manage_context_surface(value: Any) -> dict[str, Any]:
    compact = compact_exit_manage_context_v1(value)
    return compact if compact else {}


def _compact_exit_wait_taxonomy_surface(value: Any) -> dict[str, Any]:
    compact = compact_exit_wait_taxonomy_v1(value)
    return compact if compact else {}


def _compact_exit_wait_state_surface(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    if not payload:
        return {}
    if "state" in payload and "scoring" in payload and "policy" in payload:
        compact = compact_exit_wait_state_surface_v1(payload)
        return compact if compact else {}
    metadata = _coerce_mapping(payload.get("metadata"))
    nested = _coerce_mapping(metadata.get("exit_wait_state_surface_v1"))
    if nested:
        compact = compact_exit_wait_state_surface_v1(nested)
        return compact if compact else {}
    return {}


def _resolve_wait_surface_from_context(
    wait_context: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = _coerce_mapping(wait_context)
    bias = _coerce_mapping(context.get("bias"))
    policy = _coerce_mapping(context.get("policy"))
    return (
        context,
        _coerce_mapping(bias.get("bundle")),
        _coerce_mapping(policy.get("entry_wait_state_policy_input_v1")),
    )


def _wait_threshold_shift_summary(
    *,
    wait_bias_bundle: Mapping[str, Any] | None,
    wait_policy_input: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bundle = _coerce_mapping(wait_bias_bundle)
    threshold_adjustment = _coerce_mapping(bundle.get("threshold_adjustment"))
    policy_input = _coerce_mapping(wait_policy_input)
    thresholds = _coerce_mapping(policy_input.get("thresholds"))

    base_soft = _to_float(
        threshold_adjustment.get("base_soft_threshold", thresholds.get("base_soft_threshold", 0.0)),
        0.0,
    )
    base_hard = _to_float(
        threshold_adjustment.get("base_hard_threshold", thresholds.get("base_hard_threshold", 0.0)),
        0.0,
    )
    effective_soft = _to_float(
        threshold_adjustment.get("effective_soft_threshold", thresholds.get("effective_soft_threshold", 0.0)),
        0.0,
    )
    effective_hard = _to_float(
        threshold_adjustment.get("effective_hard_threshold", thresholds.get("effective_hard_threshold", 0.0)),
        0.0,
    )
    return {
        "base_soft_threshold": float(base_soft),
        "base_hard_threshold": float(base_hard),
        "effective_soft_threshold": float(effective_soft),
        "effective_hard_threshold": float(effective_hard),
        "soft_threshold_shift": round(float(effective_soft - base_soft), 6),
        "hard_threshold_shift": round(float(effective_hard - base_hard), 6),
    }


def compact_entry_decision_context(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in (
        "symbol",
        "phase",
        "market_mode",
        "direction_policy",
        "box_state",
        "bb_state",
        "liquidity_state",
        "regime_name",
        "regime_zone",
        "volatility_state",
    ):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item

    raw_scores = _compact_scalar_mapping(payload.get("raw_scores"))
    if raw_scores:
        compact["raw_scores"] = raw_scores

    thresholds = _compact_scalar_mapping(payload.get("thresholds"))
    if thresholds:
        compact["thresholds"] = thresholds

    metadata = _coerce_mapping(payload.get("metadata"))
    metadata_compact: dict[str, Any] = {}
    for key in (
        "core_pass",
        "core_reason",
        "core_allowed_action",
        "entry_stage",
        "decision_mode",
        "preflight_reason",
    ):
        item = metadata.get(key)
        if _is_simple_value(item):
            metadata_compact[key] = item

    for trace_key in (
        "forecast_assist_v1",
        "entry_default_side_gate_v1",
        "entry_probe_plan_v1",
        "edge_pair_law_v1",
        "probe_candidate_v1",
    ):
        trace_payload = compact_trace_mapping(metadata.get(trace_key))
        if trace_payload:
            metadata_compact[trace_key] = trace_payload

    observe_v2 = _compact_observe_confirm(metadata.get("observe_confirm_v2"))
    if observe_v2:
        metadata_compact["observe_confirm_v2"] = observe_v2

    energy_helper = _compact_energy_helper(metadata.get("energy_helper_v2"))
    if energy_helper:
        metadata_compact["energy_helper_v2"] = energy_helper

    forecast_effective = _compact_scalar_mapping(metadata.get("forecast_effective_policy_v1"))
    if forecast_effective:
        metadata_compact["forecast_effective_policy_v1"] = forecast_effective

    if metadata_compact:
        compact["metadata"] = metadata_compact

    return compact


def compact_entry_decision_result(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in (
        "phase",
        "symbol",
        "action",
        "outcome",
        "blocked_by",
        "reason",
        "decision_rule_version",
        "wait_state",
        "exit_profile",
    ):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item

    selected_setup = _compact_scalar_mapping(payload.get("selected_setup"))
    if selected_setup:
        compact["selected_setup"] = selected_setup

    metrics = _compact_scalar_mapping(payload.get("metrics"))
    if metrics:
        compact["metrics"] = metrics

    predictions = _coerce_mapping(payload.get("predictions"))
    predictions_compact: dict[str, Any] = {}
    for branch in ("entry", "wait", "exit", "reverse"):
        branch_payload = _compact_scalar_mapping(predictions.get(branch))
        if branch_payload:
            predictions_compact[branch] = branch_payload
    if predictions_compact:
        compact["predictions"] = predictions_compact

    return compact


def _dump_compact_json(value: dict[str, Any]) -> str:
    if not value:
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _compact_current_entry_context(value: Any) -> dict[str, Any]:
    payload = _coerce_mapping(value)
    compact: dict[str, Any] = {}
    for key in (
        "symbol",
        "phase",
        "market_mode",
        "direction_policy",
        "box_state",
        "bb_state",
        "liquidity_state",
        "regime_name",
        "regime_zone",
        "volatility_state",
    ):
        item = payload.get(key)
        if _is_simple_value(item):
            compact[key] = item

    metadata = _coerce_mapping(payload.get("metadata"))
    metadata_compact: dict[str, Any] = {}
    for key in ("preflight_allowed_action_raw", "preflight_approach_mode", "core_allowed_action"):
        item = metadata.get(key)
        if _is_simple_value(item):
            metadata_compact[key] = item

    state_raw = _compact_scalar_mapping(metadata.get("state_raw_snapshot_v1"))
    if state_raw:
        metadata_compact["state_raw_snapshot_v1"] = state_raw

    forecast_gap = _compact_scalar_mapping(metadata.get("forecast_gap_metrics_v1"))
    if forecast_gap:
        metadata_compact["forecast_gap_metrics_v1"] = forecast_gap

    observe_v1 = _compact_observe_confirm(metadata.get("observe_confirm_v1"))
    if observe_v1:
        metadata_compact["observe_confirm_v1"] = observe_v1

    observe_v2 = _compact_observe_confirm(metadata.get("observe_confirm_v2"))
    if observe_v2:
        metadata_compact["observe_confirm_v2"] = observe_v2

    if metadata_compact:
        compact["metadata"] = metadata_compact

    return compact


def compact_runtime_signal_row(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    compact: dict[str, Any] = {}
    nested_fields = {
        "current_entry_context_v1",
        "position_snapshot_v2",
        "position_vector_v2",
        "position_zones_v2",
        "position_interpretation_v2",
        "position_energy_v2",
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
        "observe_confirm_v1",
        "observe_confirm_v2",
        "observe_confirm_migration_dual_write_v1",
        "observe_confirm_input_contract_v2",
        "observe_confirm_output_contract_v2",
        "observe_confirm_scope_contract_v1",
        "semantic_foundation_contract_v1",
        "forecast_calibration_contract_v1",
        "outcome_labeler_scope_contract_v1",
        "prs_log_contract_v2",
        "entry_decision_context_v1",
        "entry_decision_result_v1",
        "entry_prediction_v1",
        "consumer_check_state_v1",
        "exit_decision_context_v1",
        "exit_decision_result_v1",
        "exit_prediction_v1",
        "exit_recovery_prediction_v1",
        "exit_utility_v1",
        "exit_wait_state_v1",
        "exit_wait_taxonomy_v1",
        "exit_manage_context_v1",
        "energy_helper_v2",
        "entry_wait_context_v1",
        "entry_wait_bias_bundle_v1",
        "entry_wait_state_policy_input_v1",
    }

    for key, value in payload.items():
        if key in nested_fields:
            continue
        if _is_simple_value(value):
            compact[str(key)] = value

    observe_identity_action, observe_identity_side = _resolve_observe_identity(payload)
    if observe_identity_action and not compact.get("observe_action"):
        compact["observe_action"] = observe_identity_action
    if observe_identity_side and not compact.get("observe_side"):
        compact["observe_side"] = observe_identity_side

    position_snapshot = _compact_position_snapshot(payload.get("position_snapshot_v2"))
    if position_snapshot:
        compact["position_snapshot_v2"] = position_snapshot
        compact["position_zones_v2"] = dict(position_snapshot.get("zones", {}) or {})
        compact["position_interpretation_v2"] = dict(position_snapshot.get("interpretation", {}) or {})
        compact["position_energy_v2"] = dict(position_snapshot.get("energy", {}) or {})
        compact["position_vector_v2"] = dict(position_snapshot.get("vector", {}) or {})

    current_entry_context = _compact_current_entry_context(payload.get("current_entry_context_v1"))
    if current_entry_context:
        compact["current_entry_context_v1"] = current_entry_context

    response_vector = _compact_scalar_mapping(payload.get("response_vector_v2"))
    if response_vector:
        compact["response_vector_v2"] = response_vector

    state_vector = _compact_scalar_mapping(payload.get("state_vector_v2"))
    if state_vector:
        compact["state_vector_v2"] = state_vector

    evidence_vector = _compact_scalar_mapping(payload.get("evidence_vector_v1"))
    if evidence_vector:
        compact["evidence_vector_v1"] = evidence_vector

    belief_state = _compact_scalar_mapping(payload.get("belief_state_v1"))
    if belief_state:
        compact["belief_state_v1"] = belief_state

    barrier_state = _compact_scalar_mapping(payload.get("barrier_state_v1"))
    if barrier_state:
        compact["barrier_state_v1"] = barrier_state

    forecast_features = _compact_scalar_mapping(payload.get("forecast_features_v1"))
    if forecast_features:
        compact["forecast_features_v1"] = forecast_features

    transition_forecast = _compact_forecast_payload(
        payload.get("transition_forecast_v1"),
        metadata_keys=("mapper_version", "side_separation", "confirm_fake_gap", "reversal_continuation_gap"),
    )
    if transition_forecast:
        compact["transition_forecast_v1"] = transition_forecast

    trade_management_forecast = _compact_forecast_payload(
        payload.get("trade_management_forecast_v1"),
        metadata_keys=("mapper_version", "continue_fail_gap", "recover_reentry_gap"),
    )
    if trade_management_forecast:
        compact["trade_management_forecast_v1"] = trade_management_forecast

    forecast_gap_metrics = _compact_scalar_mapping(payload.get("forecast_gap_metrics_v1"))
    if forecast_gap_metrics:
        compact["forecast_gap_metrics_v1"] = forecast_gap_metrics

    observe_confirm_v1 = _compact_observe_confirm(payload.get("observe_confirm_v1"))
    if observe_confirm_v1:
        compact["observe_confirm_v1"] = observe_confirm_v1

    raw_observe_metadata = _coerce_mapping(_coerce_mapping(payload.get("observe_confirm_v2")).get("metadata"))
    observe_confirm_v2 = _compact_observe_confirm(payload.get("observe_confirm_v2"))
    if observe_confirm_v2:
        compact["observe_confirm_v2"] = observe_confirm_v2
        if not compact.get("observe_action"):
            compact["observe_action"] = str(observe_confirm_v2.get("action", "") or "")
        if not compact.get("observe_side"):
            compact["observe_side"] = str(observe_confirm_v2.get("side", "") or "")
        if not compact.get("observe_reason"):
            compact["observe_reason"] = str(observe_confirm_v2.get("reason", "") or "")
        if not compact.get("blocked_by"):
            compact["blocked_by"] = str(
                raw_observe_metadata.get("blocked_guard", "")
                or raw_observe_metadata.get("blocked_reason", "")
                or ""
            )
        for trace_key in ("probe_candidate_v1", "edge_pair_law_v1"):
            if trace_key not in payload:
                trace_payload = compact_trace_mapping(raw_observe_metadata.get(trace_key))
                if trace_payload and trace_key not in compact:
                    compact[trace_key] = trace_payload

    if observe_identity_action and not compact.get("observe_action"):
        compact["observe_action"] = observe_identity_action
    if observe_identity_side and not compact.get("observe_side"):
        compact["observe_side"] = observe_identity_side

    energy_helper = _compact_energy_helper(payload.get("energy_helper_v2"))
    if energy_helper:
        compact["energy_helper_v2"] = energy_helper

    entry_decision_context = compact_entry_decision_context(payload.get("entry_decision_context_v1"))
    if entry_decision_context:
        compact["entry_decision_context_v1"] = entry_decision_context

    entry_decision_result = compact_entry_decision_result(payload.get("entry_decision_result_v1"))
    if entry_decision_result:
        compact["entry_decision_result_v1"] = entry_decision_result
        if not compact.get("blocked_by"):
            compact["blocked_by"] = str(entry_decision_result.get("blocked_by", "") or "")
        result_metrics = _coerce_mapping(entry_decision_result.get("metrics"))
        if not compact.get("action_none_reason"):
            compact["action_none_reason"] = str(result_metrics.get("action_none_reason", "") or "")
        if not compact.get("observe_reason"):
            compact["observe_reason"] = str(result_metrics.get("observe_reason", "") or "")

    for trace_key in (
        "forecast_assist_v1",
        "entry_default_side_gate_v1",
        "entry_probe_plan_v1",
        "edge_pair_law_v1",
        "probe_candidate_v1",
        "consumer_check_state_v1",
    ):
        trace_payload = compact_trace_mapping(payload.get(trace_key))
        if trace_payload:
            compact[trace_key] = trace_payload

    wait_context = _compact_wait_context_surface(payload.get("entry_wait_context_v1"))
    wait_bias_bundle = _compact_wait_bias_bundle_surface(payload.get("entry_wait_bias_bundle_v1"))
    wait_policy_input = _compact_wait_state_policy_input_surface(payload.get("entry_wait_state_policy_input_v1"))
    if wait_context and (not wait_bias_bundle or not wait_policy_input):
        _, context_wait_bias_bundle, context_wait_policy_input = _resolve_wait_surface_from_context(
            wait_context
        )
        if not wait_bias_bundle:
            wait_bias_bundle = _compact_wait_bias_bundle_surface(context_wait_bias_bundle)
        if not wait_policy_input:
            wait_policy_input = _compact_wait_state_policy_input_surface(context_wait_policy_input)
    if wait_context:
        compact["entry_wait_context_v1"] = wait_context
    if wait_bias_bundle:
        compact["entry_wait_bias_bundle_v1"] = wait_bias_bundle
    if wait_policy_input:
        compact["entry_wait_state_policy_input_v1"] = wait_policy_input

    exit_manage_context = _compact_exit_manage_context_surface(payload.get("exit_manage_context_v1"))
    if exit_manage_context:
        compact["exit_manage_context_v1"] = exit_manage_context

    exit_wait_state_surface = _compact_exit_wait_state_surface(
        payload.get("exit_wait_state_surface_v1") or payload.get("exit_wait_state_v1")
    )
    if exit_wait_state_surface:
        compact["exit_wait_state_surface_v1"] = exit_wait_state_surface
        exit_wait_surface_state = _coerce_mapping(exit_wait_state_surface.get("state"))
        exit_wait_surface_scoring = _coerce_mapping(exit_wait_state_surface.get("scoring"))
        exit_wait_surface_policy = _coerce_mapping(exit_wait_state_surface.get("policy"))
        compact["exit_wait_base_state"] = str(exit_wait_surface_state.get("base_state", "") or "")
        compact["exit_wait_base_reason"] = str(exit_wait_surface_state.get("base_reason", "") or "")
        compact["exit_wait_rewrite_applied"] = bool(
            exit_wait_surface_state.get("rewrite_applied", False)
        )
        compact["exit_wait_rewrite_rule"] = str(exit_wait_surface_state.get("rewrite_rule", "") or "")
        compact["exit_wait_score"] = _to_float(exit_wait_surface_scoring.get("score", 0.0), 0.0)
        compact["exit_wait_penalty"] = _to_float(exit_wait_surface_scoring.get("penalty", 0.0), 0.0)
        compact["exit_wait_recovery_policy_id"] = str(
            exit_wait_surface_policy.get("recovery_policy_id", "") or ""
        )

    exit_wait_taxonomy = _compact_exit_wait_taxonomy_surface(payload.get("exit_wait_taxonomy_v1"))
    if exit_wait_taxonomy:
        compact["exit_wait_taxonomy_v1"] = exit_wait_taxonomy
        exit_taxonomy_state = _coerce_mapping(exit_wait_taxonomy.get("state"))
        exit_taxonomy_decision = _coerce_mapping(exit_wait_taxonomy.get("decision"))
        exit_taxonomy_bridge = _coerce_mapping(exit_wait_taxonomy.get("bridge"))
        compact["exit_wait_state_family"] = str(exit_taxonomy_state.get("state_family", "") or "")
        compact["exit_wait_hold_class"] = str(exit_taxonomy_state.get("hold_class", "") or "")
        compact["exit_wait_decision_family"] = str(
            exit_taxonomy_decision.get("decision_family", "") or ""
        )
        compact["exit_wait_bridge_status"] = str(exit_taxonomy_bridge.get("bridge_status", "") or "")

    if wait_bias_bundle:
        compact["wait_bias_release_sources"] = list(wait_bias_bundle.get("active_release_sources", []) or [])
        compact["wait_bias_wait_lock_sources"] = list(wait_bias_bundle.get("active_wait_lock_sources", []) or [])
    if wait_policy_input:
        compact["wait_required_side"] = str(
            _coerce_mapping(wait_policy_input.get("identity")).get("required_side", "") or ""
        )
    if wait_context:
        wait_policy = _coerce_mapping(wait_context.get("policy"))
        wait_probe = _coerce_mapping(wait_context.get("observe_probe"))
        compact["wait_policy_state"] = str(wait_policy.get("state", "") or "")
        compact["wait_policy_reason"] = str(wait_policy.get("reason", "") or "")
        compact["wait_probe_scene_id"] = str(wait_probe.get("probe_scene_id", "") or "")
        compact["wait_probe_ready_for_entry"] = bool(wait_probe.get("probe_ready_for_entry", False))
        compact["wait_xau_second_support_probe_relief"] = bool(
            wait_probe.get("xau_second_support_probe_relief", False)
        )
    threshold_shift = _wait_threshold_shift_summary(
        wait_bias_bundle=wait_bias_bundle,
        wait_policy_input=wait_policy_input,
    )
    if threshold_shift:
        compact["wait_threshold_shift_summary"] = threshold_shift

    quick_trace_source = dict(payload or {})
    if "observe_reason" not in quick_trace_source:
        quick_trace_source["observe_reason"] = compact.get("observe_reason", "")
    if "blocked_by" not in quick_trace_source:
        quick_trace_source["blocked_by"] = compact.get("blocked_by", "")
    if "action_none_reason" not in quick_trace_source:
        quick_trace_source["action_none_reason"] = compact.get("action_none_reason", "")
    for trace_key in ("probe_candidate_v1", "edge_pair_law_v1"):
        if trace_key not in quick_trace_source:
            raw_trace_payload = raw_observe_metadata.get(trace_key)
            if isinstance(raw_trace_payload, Mapping):
                quick_trace_source[trace_key] = dict(raw_trace_payload)
    if "entry_probe_plan_v1" not in quick_trace_source and "entry_probe_plan_v1" in compact:
        quick_trace_source["entry_probe_plan_v1"] = compact.get("entry_probe_plan_v1")
    quick_trace_fields = build_probe_quick_trace_fields(quick_trace_source)
    compact.update(quick_trace_fields)
    quick_trace_source.update(quick_trace_fields)
    r0_interpretation = build_r0_row_interpretation_v1(quick_trace_source)
    if r0_interpretation:
        compact["r0_non_action_family"] = str(r0_interpretation.get("non_action_family", "") or "")
        compact["r0_semantic_runtime_state"] = str(
            r0_interpretation.get("semantic_runtime_state", "") or ""
        )
        compact["r0_row_interpretation_v1"] = r0_interpretation

    if not compact.get("timestamp"):
        time_value = payload.get("time")
        if isinstance(time_value, (int, float)) and float(time_value) > 0:
            compact["timestamp"] = datetime.fromtimestamp(float(time_value)).isoformat()
        else:
            generated_ts = payload.get("runtime_snapshot_generated_ts")
            if isinstance(generated_ts, (int, float)) and float(generated_ts) > 0:
                compact["timestamp"] = datetime.fromtimestamp(float(generated_ts)).isoformat()

    return compact


def build_entry_decision_hot_payload(
    payload: Mapping[str, Any] | None,
    *,
    detail_row_key: str,
) -> dict[str, Any]:
    full_payload = dict(payload or {})
    hot_payload = {
        str(key): value
        for key, value in full_payload.items()
        if str(key) not in ENTRY_DECISION_DETAIL_ONLY_COLUMNS
    }
    hot_payload["position_snapshot_v2"] = _dump_compact_json(_compact_position_snapshot(full_payload.get("position_snapshot_v2")))
    hot_payload["response_vector_v2"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("response_vector_v2")))
    hot_payload["state_vector_v2"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("state_vector_v2")))
    hot_payload["evidence_vector_v1"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("evidence_vector_v1")))
    hot_payload["belief_state_v1"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("belief_state_v1")))
    hot_payload["barrier_state_v1"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("barrier_state_v1")))
    hot_payload["forecast_features_v1"] = _dump_compact_json(_compact_scalar_mapping(full_payload.get("forecast_features_v1")))
    hot_payload["transition_forecast_v1"] = _dump_compact_json(
        _compact_forecast_payload(
            full_payload.get("transition_forecast_v1"),
            metadata_keys=("mapper_version", "side_separation", "confirm_fake_gap", "reversal_continuation_gap"),
        )
    )
    hot_payload["trade_management_forecast_v1"] = _dump_compact_json(
        _compact_forecast_payload(
            full_payload.get("trade_management_forecast_v1"),
            metadata_keys=("mapper_version", "continue_fail_gap", "recover_reentry_gap"),
        )
    )
    hot_payload["forecast_gap_metrics_v1"] = _dump_compact_json(
        _compact_scalar_mapping(full_payload.get("forecast_gap_metrics_v1"))
    )
    hot_payload["observe_confirm_v1"] = _dump_compact_json(_compact_observe_confirm(full_payload.get("observe_confirm_v1")))
    hot_payload["observe_confirm_v2"] = _dump_compact_json(_compact_observe_confirm(full_payload.get("observe_confirm_v2")))
    hot_payload["energy_helper_v2"] = _dump_compact_json(_compact_energy_helper(full_payload.get("energy_helper_v2")))
    hot_payload["entry_decision_context_v1"] = _dump_compact_json(
        compact_entry_decision_context(full_payload.get("entry_decision_context_v1"))
    )
    hot_payload["entry_decision_result_v1"] = _dump_compact_json(
        compact_entry_decision_result(full_payload.get("entry_decision_result_v1"))
    )
    hot_payload["forecast_assist_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("forecast_assist_v1"))
    )
    hot_payload["entry_default_side_gate_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("entry_default_side_gate_v1"))
    )
    hot_payload["entry_probe_plan_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("entry_probe_plan_v1"))
    )
    hot_payload["edge_pair_law_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("edge_pair_law_v1"))
    )
    hot_payload["probe_candidate_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("probe_candidate_v1"))
    )
    hot_payload["p7_guarded_size_overlay_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("p7_guarded_size_overlay_v1"))
    )
    hot_payload["consumer_check_state_v1"] = _dump_compact_json(
        compact_trace_mapping(full_payload.get("consumer_check_state_v1"))
    )
    compact_wait_context = _compact_wait_context_surface(full_payload.get("entry_wait_context_v1"))
    _, context_wait_bias_bundle, context_wait_policy_input = _resolve_wait_surface_from_context(compact_wait_context)
    hot_payload["entry_wait_context_v1"] = _dump_compact_json(compact_wait_context)
    hot_payload["entry_wait_bias_bundle_v1"] = _dump_compact_json(
        _compact_wait_bias_bundle_surface(
            full_payload.get("entry_wait_bias_bundle_v1") or context_wait_bias_bundle
        )
    )
    hot_payload["entry_wait_state_policy_input_v1"] = _dump_compact_json(
        _compact_wait_state_policy_input_surface(
            full_payload.get("entry_wait_state_policy_input_v1") or context_wait_policy_input
        )
    )
    hot_payload["entry_wait_energy_usage_trace_v1"] = _dump_compact_json(
        compact_energy_usage_trace(full_payload.get("entry_wait_energy_usage_trace_v1"))
    )
    hot_payload["entry_wait_decision_energy_usage_trace_v1"] = _dump_compact_json(
        compact_energy_usage_trace(full_payload.get("entry_wait_decision_energy_usage_trace_v1"))
    )
    observe_identity_action, observe_identity_side = _resolve_observe_identity(full_payload)
    if observe_identity_action and not _pick_text(hot_payload.get("observe_action")):
        hot_payload["observe_action"] = observe_identity_action
    if observe_identity_side and not _pick_text(hot_payload.get("observe_side")):
        hot_payload["observe_side"] = observe_identity_side
    if observe_identity_side and not _pick_text(hot_payload.get("core_intended_direction")):
        hot_payload["core_intended_direction"] = observe_identity_side
    if observe_identity_side and not _pick_text(hot_payload.get("core_intended_action_source")):
        hot_payload["core_intended_action_source"] = "observe_identity_side"
    quick_trace_source = dict(full_payload or {})
    if "observe_reason" not in quick_trace_source:
        quick_trace_source["observe_reason"] = hot_payload.get("observe_reason", "")
    if "blocked_by" not in quick_trace_source:
        quick_trace_source["blocked_by"] = hot_payload.get("blocked_by", "")
    if "action_none_reason" not in quick_trace_source:
        quick_trace_source["action_none_reason"] = hot_payload.get("action_none_reason", "")
    quick_trace_fields = build_probe_quick_trace_fields(quick_trace_source)
    hot_payload.update(quick_trace_fields)
    quick_trace_source.update(quick_trace_fields)
    r0_interpretation = build_r0_row_interpretation_v1(quick_trace_source)
    hot_payload["r0_non_action_family"] = str(r0_interpretation.get("non_action_family", "") or "")
    hot_payload["r0_semantic_runtime_state"] = str(
        r0_interpretation.get("semantic_runtime_state", "") or ""
    )
    hot_payload["r0_row_interpretation_v1"] = _dump_compact_json(r0_interpretation)
    hot_payload["detail_schema_version"] = ENTRY_DECISION_DETAIL_SCHEMA_VERSION
    hot_payload["detail_row_key"] = str(detail_row_key or "")
    return hot_payload


def build_entry_decision_detail_record(
    payload: Mapping[str, Any] | None,
    *,
    row_key: str,
) -> dict[str, Any]:
    return {
        "record_type": ENTRY_DECISION_DETAIL_SCHEMA_VERSION,
        "schema_version": ENTRY_DECISION_DETAIL_SCHEMA_VERSION,
        "row_key": str(row_key or ""),
        "payload": dict(payload or {}),
    }


def _to_timestamp(value: Any) -> float | str | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)


def _to_epoch(value: Any) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _has_meaningful_anchor_value(value: Any) -> bool:
    if value in ("", None):
        return False
    if isinstance(value, (int, float)):
        return float(value) > 0.0
    text = str(value).strip()
    if not text:
        return False
    try:
        return float(text) > 0.0
    except (TypeError, ValueError):
        return True


def _resolve_anchor_time(row: Mapping[str, Any] | None) -> tuple[str, float | str | None]:
    if not isinstance(row, Mapping):
        return "", None
    signal_bar_ts = _to_timestamp(row.get("signal_bar_ts"))
    if _has_meaningful_anchor_value(signal_bar_ts):
        return "signal_bar_ts", signal_bar_ts
    time_value = _to_timestamp(row.get("time"))
    if _has_meaningful_anchor_value(time_value):
        return "time", time_value
    return "", None


def _ticket_from_trade_link_key(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    for part in text.split("|"):
        if not part.startswith("ticket="):
            continue
        ticket_text = part.split("=", 1)[1].strip()
        return _to_int(ticket_text, 0)
    return 0


def _position_key(row: Mapping[str, Any] | None) -> int:
    if not isinstance(row, Mapping):
        return 0
    for field in ("ticket", "position_id"):
        value = _to_int(row.get(field), 0)
        if value > 0:
            return value
    trade_link_ticket = _ticket_from_trade_link_key(row.get("trade_link_key"))
    if trade_link_ticket > 0:
        return trade_link_ticket
    return 0


def _pick_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _sanitize_key_component(value: Any) -> str:
    text = _pick_text(value)
    if not text:
        return ""
    return " ".join(text.replace("|", "/").replace("\r", " ").replace("\n", " ").split())


def _to_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _decision_metrics(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    decision_result = _coerce_mapping(row.get("entry_decision_result_v1"))
    return _coerce_mapping(decision_result.get("metrics"))


def _decision_observe_reason(row: Mapping[str, Any] | None) -> str:
    return _sanitize_key_component(resolve_r0_reason_triplet(row).get("observe_reason", ""))


def _decision_blocked_by(row: Mapping[str, Any] | None) -> str:
    return _sanitize_key_component(resolve_r0_reason_triplet(row).get("blocked_by", ""))


def _decision_action_none_reason(row: Mapping[str, Any] | None) -> str:
    return _sanitize_key_component(resolve_r0_reason_triplet(row).get("action_none_reason", ""))


def _decision_probe_state(row: Mapping[str, Any] | None) -> str:
    return _sanitize_key_component(resolve_r0_probe_state(row))


def _needs_sparse_decision_suffix(row: Mapping[str, Any] | None) -> bool:
    if not isinstance(row, Mapping):
        return False
    if _position_key(row) > 0:
        return False
    outcome = _pick_text(row.get("outcome"), row.get("result")).lower()
    if outcome in {"entered", "open", "filled", "submitted", "executed"}:
        return False
    if (
        _pick_text(row.get("action"))
        and _pick_text(row.get("setup_id"))
        and not _decision_observe_reason(row)
        and not _decision_blocked_by(row)
        and not _decision_action_none_reason(row)
        and not _decision_probe_state(row)
        and not outcome
    ):
        return False
    return True


def _decision_time_identity(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    generated = _to_timestamp(row.get("decision_generated_ts"))
    if generated is not None:
        return _sanitize_key_component(generated)
    time_value = _to_timestamp(row.get("time"))
    if time_value is not None:
        return _sanitize_key_component(time_value)
    return ""


def resolve_entry_decision_row_key(decision_row: Mapping[str, Any] | None) -> str:
    row = dict(decision_row or {})
    anchor_field, anchor_value = _resolve_anchor_time(row)
    base_key = (
        "replay_dataset_row_v1"
        f"|symbol={str(row.get('symbol', '') or '')}"
        f"|anchor_field={anchor_field}"
        f"|anchor_value={anchor_value}"
        f"|action={str(row.get('action', '') or '')}"
        f"|setup_id={str(row.get('setup_id', '') or '')}"
        f"|ticket={_position_key(row)}"
    )
    if not _needs_sparse_decision_suffix(row):
        return base_key

    suffix_parts: list[str] = []
    decision_time = _decision_time_identity(row)
    if decision_time:
        suffix_parts.append(f"|decision_time={decision_time}")
    observe_reason = _decision_observe_reason(row)
    if observe_reason:
        suffix_parts.append(f"|observe_reason={observe_reason}")
    probe_state = _decision_probe_state(row)
    if probe_state:
        suffix_parts.append(f"|probe_state={probe_state}")
    blocked_by = _decision_blocked_by(row)
    if blocked_by:
        suffix_parts.append(f"|blocked_by={blocked_by}")
    action_none_reason = _decision_action_none_reason(row)
    if action_none_reason:
        suffix_parts.append(f"|action_none_reason={action_none_reason}")
    return base_key + "".join(suffix_parts)


def resolve_runtime_signal_row_key(signal_row: Mapping[str, Any] | None) -> str:
    row = dict(signal_row or {})
    anchor_field, anchor_value = _resolve_anchor_time(row)
    return (
        "runtime_signal_row_v1"
        f"|symbol={str(row.get('symbol', '') or '')}"
        f"|anchor_field={anchor_field}"
        f"|anchor_value={anchor_value}"
        f"|hint={str(row.get('next_action_hint', '') or '')}"
    )


def is_generic_runtime_signal_row_key(value: Any) -> bool:
    text = str(value or "").strip()
    if not text.startswith("runtime_signal_row_v1|"):
        return False
    marker = "|anchor_value="
    if marker not in text:
        return True
    anchor_part = text.split(marker, 1)[1].split("|", 1)[0].strip()
    if not anchor_part:
        return True
    try:
        return float(anchor_part) <= 0.0
    except (TypeError, ValueError):
        return False


def resolve_trade_link_key(trade_row: Mapping[str, Any] | None) -> str:
    row = dict(trade_row or {})
    return (
        "trade_link_v1"
        f"|ticket={_position_key(row)}"
        f"|symbol={str(row.get('symbol', '') or '')}"
        f"|direction={str(row.get('direction', row.get('action', '')) or '')}"
        f"|open_ts={_to_int(row.get('open_ts'), 0)}"
    )


def json_payload_size_bytes(value: Any) -> int:
    if value in ("", None):
        return 0
    try:
        if isinstance(value, bytes):
            return len(value)
        if isinstance(value, str):
            return len(value.encode("utf-8"))
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
    except Exception:
        try:
            return len(str(value).encode("utf-8", errors="ignore"))
        except Exception:
            return 0


def _is_present_payload(value: Any) -> bool:
    if value in ("", None):
        return False
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {"{}", "[]", "null", "None"}:
            return False
        parsed = _coerce_mapping(text)
        if parsed:
            return True
        return bool(text)
    return True


def summarize_trace_quality(
    payload: Mapping[str, Any] | None,
    *,
    decision_ts: float | None = None,
    runtime_snapshot_ts: float | None = None,
) -> dict[str, Any]:
    row = dict(payload or {})
    feature_present = sum(1 for field in ENTRY_TRACE_REQUIRED_FIELDS if _is_present_payload(row.get(field)))
    missing_feature_count = max(0, len(ENTRY_TRACE_REQUIRED_FIELDS) - feature_present)
    data_completeness_ratio = round(float(feature_present) / float(len(ENTRY_TRACE_REQUIRED_FIELDS)), 6)

    decision_epoch = decision_ts
    if decision_epoch is None:
        decision_epoch = _to_epoch(row.get("time"))
    signal_epoch = _to_epoch(row.get("signal_bar_ts"))
    runtime_epoch = runtime_snapshot_ts
    if runtime_epoch is None:
        runtime_epoch = _to_epoch(row.get("runtime_snapshot_generated_ts"))

    signal_age_sec = 0.0
    bar_age_sec = 0.0
    if decision_epoch is not None and signal_epoch is not None and decision_epoch >= signal_epoch:
        signal_age_sec = round(float(decision_epoch - signal_epoch), 3)
        bar_age_sec = round(float(decision_epoch - signal_epoch), 3)

    decision_latency_ms = 0
    if decision_epoch is not None and runtime_epoch is not None and decision_epoch >= runtime_epoch:
        decision_latency_ms = int(round((float(decision_epoch) - float(runtime_epoch)) * 1000.0))

    used_fallback_count = 0
    observe_input_field = str(row.get("consumer_input_observe_confirm_field", "") or "").strip()
    compatibility_flag = str(row.get("consumer_used_compatibility_fallback_v1", "") or "").strip().lower()
    energy_guard = _coerce_mapping(row.get("energy_migration_guard_v1"))
    if observe_input_field == "observe_confirm_v1":
        used_fallback_count += 1
    if compatibility_flag in {"true", "1", "yes"}:
        used_fallback_count += 1
    if bool(energy_guard.get("used_compatibility_bridge")) or bool(energy_guard.get("compatibility_bridge_rebuild_active")):
        used_fallback_count += 1

    if observe_input_field == "observe_confirm_v1":
        compatibility_mode = "observe_confirm_v1_fallback"
    elif used_fallback_count > 0:
        compatibility_mode = "hybrid"
    else:
        compatibility_mode = "native_v2"

    return {
        "signal_age_sec": float(signal_age_sec),
        "bar_age_sec": float(bar_age_sec),
        "decision_latency_ms": int(max(0, decision_latency_ms)),
        "missing_feature_count": int(missing_feature_count),
        "data_completeness_ratio": float(data_completeness_ratio),
        "used_fallback_count": int(used_fallback_count),
        "compatibility_mode": str(compatibility_mode),
    }
