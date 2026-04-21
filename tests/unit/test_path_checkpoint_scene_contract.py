from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_ACTION_BIAS_STRENGTHS,
    PATH_CHECKPOINT_SCENE_ALIGNMENT_STATES,
    PATH_CHECKPOINT_SCENE_CONFIDENCE_BANDS,
    PATH_CHECKPOINT_SCENE_DEFAULT_PAYLOAD,
    PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS,
    PATH_CHECKPOINT_SCENE_MATURITY_LEVELS,
    PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT,
    PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER,
    build_default_scene_runtime_payload,
)


def test_build_default_scene_runtime_payload_returns_full_contract_defaults() -> None:
    payload = build_default_scene_runtime_payload()

    assert set(PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS).issubset(payload.keys())
    assert payload["runtime_scene_gate_label"] == "none"
    assert payload["runtime_scene_confidence_band"] == "low"
    assert payload["runtime_scene_action_bias_strength"] == "none"
    assert payload["runtime_scene_maturity"] == "provisional"
    assert payload["runtime_scene_gate_block_level"] == "none"
    assert payload["runtime_scene_coarse_family"] == PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY
    assert payload["runtime_scene_fine_label"] == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    assert payload["runtime_scene_transition_from"] == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    assert payload["runtime_scene_transition_speed"] == PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED
    assert payload["runtime_scene_family_alignment"] == PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT
    assert payload["hindsight_scene_quality_tier"] == PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER


def test_build_default_scene_runtime_payload_allows_known_overrides_only() -> None:
    payload = build_default_scene_runtime_payload(
        {
            "runtime_scene_fine_label": "trend_exhaustion",
            "runtime_scene_confidence_band": "high",
            "runtime_scene_action_bias_strength": "hard",
            "not_a_scene_key": "ignored",
        }
    )

    assert payload["runtime_scene_fine_label"] == "trend_exhaustion"
    assert payload["runtime_scene_confidence_band"] == "high"
    assert payload["runtime_scene_action_bias_strength"] == "hard"
    assert "not_a_scene_key" not in payload
    assert set(payload.keys()) == set(PATH_CHECKPOINT_SCENE_DEFAULT_PAYLOAD.keys())


def test_scene_contract_enums_include_scope_lock_basics() -> None:
    assert {"high", "medium", "low"} == set(PATH_CHECKPOINT_SCENE_CONFIDENCE_BANDS)
    assert {"none", "soft", "medium", "hard"} == set(PATH_CHECKPOINT_SCENE_ACTION_BIAS_STRENGTHS)
    assert {"provisional", "probable", "confirmed"} == set(PATH_CHECKPOINT_SCENE_MATURITY_LEVELS)
    assert {"aligned", "upgrade", "downgrade", "conflict"} == set(PATH_CHECKPOINT_SCENE_ALIGNMENT_STATES)
    assert {"none", "entry_block", "all_block"} == set(PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS)
