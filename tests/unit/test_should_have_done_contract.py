from backend.services.should_have_done_contract import (
    SHOULD_HAVE_DONE_CONTRACT_VERSION,
    build_should_have_done_contract_v1,
)


def test_build_should_have_done_contract_v1_exposes_r3_fields():
    contract = build_should_have_done_contract_v1()

    assert contract["contract_version"] == SHOULD_HAVE_DONE_CONTRACT_VERSION
    assert contract["status"] == "READY"
    fields = {row["field"]: row for row in contract["fields"]}
    assert "expected_direction" in fields
    assert "expected_continuation" in fields
    assert "expected_phase_v1" in fields
    assert "expected_surface" in fields
    assert "annotation_confidence_v1" in fields
    assert "candidate_source_v1" in fields
    assert contract["execution_rules"]["execution_influence_allowed"] is False
