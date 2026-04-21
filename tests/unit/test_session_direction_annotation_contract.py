from backend.services.session_direction_annotation_contract import (
    ANNOTATION_CONFIDENCE_ENUM_V1,
    CONTINUATION_ANNOTATION_ENUM_V1,
    CONTINUATION_PHASE_V1_ENUM,
    DIRECTION_ANNOTATION_ENUM_V1,
    SESSION_DIRECTION_ANNOTATION_CONTRACT_VERSION,
    build_session_direction_annotation_contract_v1,
)


def test_build_session_direction_annotation_contract_v1_exposes_minimum_r2_schema():
    contract = build_session_direction_annotation_contract_v1()

    assert contract["contract_version"] == SESSION_DIRECTION_ANNOTATION_CONTRACT_VERSION
    assert contract["status"] == "READY"
    assert contract["session_bias_expansion_status"] == "HOLD"
    fields = {row["field"]: row for row in contract["fields"]}
    assert fields["direction_annotation"]["enum"] == list(DIRECTION_ANNOTATION_ENUM_V1)
    assert fields["continuation_annotation"]["enum"] == list(CONTINUATION_ANNOTATION_ENUM_V1)
    assert fields["continuation_phase_v1"]["enum"] == list(CONTINUATION_PHASE_V1_ENUM)
    assert fields["annotation_confidence_v1"]["enum"] == list(ANNOTATION_CONFIDENCE_ENUM_V1)
    assert contract["execution_rules"]["session_direct_buy_sell_allowed"] is False
    assert contract["execution_rules"]["state25_bias_expansion_allowed"] is False
