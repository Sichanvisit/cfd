from ml.semantic_v1.contracts import (
    MODEL_TARGET_FAMILIES,
    MODEL_OWNER_FIELDS,
    RULE_OWNER_FIELDS,
    SEMANTIC_FEATURE_CONTRACT,
    SEMANTIC_TARGET_CONTRACT,
    rule_owner_vs_model_owner_table,
)
from ml.semantic_v1.feature_packs import (
    ALL_CONTRACT_COLUMNS,
    SEMANTIC_INPUT_COLUMNS,
    SEMANTIC_INPUT_PACKS,
    SUPPORT_PACKS,
)


def test_semantic_feature_contract_has_expected_pack_layout():
    assert [pack.key for pack in SEMANTIC_INPUT_PACKS] == [
        "position_pack",
        "response_pack",
        "state_pack",
        "evidence_pack",
        "forecast_summary_pack",
    ]
    assert [pack.key for pack in SUPPORT_PACKS] == ["trace_quality_pack"]
    assert len(SEMANTIC_INPUT_COLUMNS) > 0
    assert len(ALL_CONTRACT_COLUMNS) >= len(SEMANTIC_INPUT_COLUMNS)
    assert SEMANTIC_FEATURE_CONTRACT["version"] == "semantic_feature_contract_v1"


def test_semantic_target_contract_and_owner_table_are_fixed():
    assert [target.key for target in MODEL_TARGET_FAMILIES] == [
        "timing_now_vs_wait",
        "entry_quality",
        "exit_management",
    ]
    assert SEMANTIC_TARGET_CONTRACT["version"] == "semantic_target_contract_v1"
    assert RULE_OWNER_FIELDS == (
        "side",
        "entry_setup_id",
        "management_profile_id",
        "invalidation_id",
        "hard_guard",
        "kill_switch",
    )
    assert "timing_now_vs_wait" in MODEL_OWNER_FIELDS
    assert any(row["field"] == "side" and row["domain"] == "rule_owner" for row in rule_owner_vs_model_owner_table)
    assert any(
        row["field"] == "bounded_threshold_adjustment" and row["domain"] == "model_owner"
        for row in rule_owner_vs_model_owner_table
    )

