from __future__ import annotations

from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    build_learning_registry_binding_fields,
    build_learning_registry_direct_binding_plan,
    build_learning_registry_relation,
    resolve_learning_registry_row,
)


def test_learning_registry_resolver_returns_expected_binding_fields() -> None:
    row = resolve_learning_registry_row("misread:box_relative_position")
    assert row["label_ko"] == "박스 상대 위치"

    binding = build_learning_registry_binding_fields(
        "misread:box_relative_position",
        binding_mode=LEARNING_REGISTRY_BINDING_MODE_EXACT,
    )
    assert binding["registry_key"] == "misread:box_relative_position"
    assert binding["registry_label_ko"] == "박스 상대 위치"
    assert binding["registry_category"] == "misread_observation"
    assert binding["registry_binding_mode"] == LEARNING_REGISTRY_BINDING_MODE_EXACT
    assert binding["registry_found"] is True


def test_learning_registry_relation_deduplicates_and_marks_ready() -> None:
    relation = build_learning_registry_relation(
        evidence_registry_keys=[
            "misread:box_relative_position",
            "misread:box_relative_position",
            "misread:upper_wick_ratio",
        ],
        target_registry_keys=[
            "state25_weight:upper_wick_weight",
        ],
        binding_mode=LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    )

    assert relation["binding_ready"] is True
    assert relation["registry_binding_mode"] == LEARNING_REGISTRY_BINDING_MODE_DERIVED
    assert relation["evidence_registry_keys"] == [
        "misread:box_relative_position",
        "misread:upper_wick_ratio",
    ]
    assert relation["target_registry_keys"] == [
        "state25_weight:upper_wick_weight",
    ]


def test_learning_registry_direct_binding_plan_exposes_stage_targets() -> None:
    plan = build_learning_registry_direct_binding_plan()

    assert plan["binding_version"] == "learning_registry_binding_v1"
    assert int(plan["all_target_key_count"]) > 0
    assert int(plan["stages"]["detector"]["target_key_count"]) > 0
    assert "misread:box_relative_position" in plan["stages"]["detector"]["target_registry_keys"]
    assert "state25_weight:upper_wick_weight" in plan["stages"]["weight_review"]["target_registry_keys"]
