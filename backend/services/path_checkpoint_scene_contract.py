"""Shared scene-axis contract for path-aware checkpoint runtime rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PATH_CHECKPOINT_SCENE_CONTRACT_VERSION = "path_checkpoint_scene_contract_v1"
PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY = "UNRESOLVED"
PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL = "unresolved"
PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED = "unknown"
PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT = "unknown"
PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER = "unresolved"
PATH_CHECKPOINT_SCENE_COARSE_FAMILIES = (
    "ENTRY_INITIATION",
    "CONTINUATION",
    "POSITION_MANAGEMENT",
    "DEFENSIVE_EXIT",
    "NO_TRADE",
)
PATH_CHECKPOINT_SCENE_CONFIDENCE_BANDS = ("high", "medium", "low")
PATH_CHECKPOINT_SCENE_ACTION_BIAS_STRENGTHS = ("none", "soft", "medium", "hard")
PATH_CHECKPOINT_SCENE_MATURITY_LEVELS = ("provisional", "probable", "confirmed")
PATH_CHECKPOINT_SCENE_ALIGNMENT_STATES = ("aligned", "upgrade", "downgrade", "conflict")
PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS = ("none", "entry_block", "all_block")
PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS = [
    "runtime_scene_coarse_family",
    "runtime_scene_fine_label",
    "runtime_scene_gate_label",
    "runtime_scene_modifier_json",
    "runtime_scene_confidence",
    "runtime_scene_confidence_band",
    "runtime_scene_action_bias_strength",
    "runtime_scene_source",
    "runtime_scene_maturity",
    "runtime_scene_transition_from",
    "runtime_scene_transition_bars",
    "runtime_scene_transition_speed",
    "runtime_scene_family_alignment",
    "runtime_scene_gate_block_level",
    "hindsight_scene_fine_label",
    "hindsight_scene_quality_tier",
]
PATH_CHECKPOINT_SCENE_DEFAULT_PAYLOAD = {
    "runtime_scene_coarse_family": PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY,
    "runtime_scene_fine_label": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "runtime_scene_gate_label": "none",
    "runtime_scene_modifier_json": "{}",
    "runtime_scene_confidence": 0.0,
    "runtime_scene_confidence_band": "low",
    "runtime_scene_action_bias_strength": "none",
    "runtime_scene_source": "schema_only",
    "runtime_scene_maturity": "provisional",
    "runtime_scene_transition_from": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "runtime_scene_transition_bars": 0,
    "runtime_scene_transition_speed": PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED,
    "runtime_scene_family_alignment": PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT,
    "runtime_scene_gate_block_level": "none",
    "hindsight_scene_fine_label": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "hindsight_scene_quality_tier": PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER,
}


def build_default_scene_runtime_payload(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(PATH_CHECKPOINT_SCENE_DEFAULT_PAYLOAD)
    if not overrides:
        return payload
    for key in PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS:
        if key not in overrides:
            continue
        value = overrides[key]
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        payload[key] = value
    return payload
