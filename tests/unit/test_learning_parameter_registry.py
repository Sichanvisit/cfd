from __future__ import annotations

from backend.services.learning_parameter_registry import (
    build_learning_parameter_registry,
    render_learning_parameter_registry_markdown,
)


def _row_by_key(payload: dict, registry_key: str) -> dict:
    for row in payload.get("rows", []):
        if str(row.get("registry_key")) == registry_key:
            return dict(row)
    raise AssertionError(f"registry row not found: {registry_key}")


def test_learning_parameter_registry_contains_core_categories() -> None:
    payload = build_learning_parameter_registry()

    assert payload["contract_version"] == "learning_parameter_registry_v1"
    assert int(payload["row_count"]) >= 40

    category_keys = {str(category["category_key"]) for category in payload.get("categories", [])}
    assert "translation_source" in category_keys
    assert "state25_teacher_weight" in category_keys
    assert "forecast_runtime" in category_keys
    assert "misread_observation" in category_keys
    assert "detector_policy" in category_keys
    assert "feedback_promotion_policy" in category_keys


def test_learning_parameter_registry_contains_expected_rows() -> None:
    payload = build_learning_parameter_registry()

    weight_row = _row_by_key(payload, "state25_weight:upper_wick_weight")
    assert weight_row["label_ko"] == "윗꼬리 반응 비중"
    assert weight_row["variable_kind"] == "weight"

    forecast_row = _row_by_key(payload, "forecast:false_break_score")
    assert forecast_row["label_ko"] == "가짜 돌파 경계 점수"
    assert "false break" in forecast_row["description_ko"]

    misread_row = _row_by_key(payload, "misread:box_relative_position")
    assert misread_row["label_ko"] == "박스 상대 위치"
    assert misread_row["variable_kind"] == "evidence"

    conflict_row = _row_by_key(payload, "misread:context_conflict_state")
    assert conflict_row["variable_kind"] == "evidence"

    htf_row = _row_by_key(payload, "misread:htf_alignment_state")
    assert htf_row["variable_kind"] == "evidence"

    continuation_row = _row_by_key(payload, "misread:semantic_continuation_gap_cluster")
    assert continuation_row["variable_kind"] == "evidence"
    assert "semantic" in continuation_row["label_ko"].lower()

    up_direction_row = _row_by_key(payload, "misread:directional_up_continuation_conflict")
    assert up_direction_row["variable_kind"] == "evidence"

    down_direction_row = _row_by_key(payload, "misread:directional_down_continuation_conflict")
    assert down_direction_row["variable_kind"] == "evidence"

    threshold_row = _row_by_key(payload, "state25_threshold:entry_harden_delta_points")
    assert threshold_row["variable_kind"] == "threshold_delta"
    assert threshold_row["category_key"] == "state25_threshold_policy"

    promotion_row = _row_by_key(payload, "promotion:fast_promotion_min_trade_days")
    assert promotion_row["label_ko"] == "빠른 승격 최소 거래일 분산"


def test_learning_parameter_registry_markdown_renders_labels() -> None:
    payload = build_learning_parameter_registry()
    markdown = render_learning_parameter_registry_markdown(payload)

    assert "# Learning Parameter Registry" in markdown
    assert "## forecast 보조 판단 축 (`forecast_runtime`)" in markdown
    assert "`misread:composite_structure_mismatch` | 구조 복합 불일치" in markdown
