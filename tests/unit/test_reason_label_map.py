from backend.services.reason_label_map import (
    normalize_runtime_confidence_label,
    normalize_runtime_reason,
    normalize_runtime_scene_gate,
    normalize_runtime_scene_label,
    normalize_runtime_transition_hint,
)


def test_normalize_runtime_reason_translates_known_tokens():
    assert normalize_runtime_reason("Flow: lower rebound confirm (+19점)") == "흐름: 하단 반등 확인 (lower rebound confirm)"


def test_normalize_runtime_scene_label_translates_exact_scene():
    assert normalize_runtime_scene_label("breakout_retest_hold") == "돌파 후 재시험 유지 (breakout_retest_hold)"


def test_normalize_runtime_scene_gate_translates_gate_label():
    assert normalize_runtime_scene_gate("caution") == "주의"


def test_normalize_runtime_confidence_label_supports_band_and_numeric():
    assert normalize_runtime_confidence_label(band="high") == "높음"
    assert normalize_runtime_confidence_label(confidence=0.52) == "보통"


def test_normalize_runtime_transition_hint_translates_known_transition():
    assert normalize_runtime_transition_hint("plus_to_minus_protect") == "플러스→마이너스 전환 보호"
