from backend.services.symbol_specific_state_strength_calibration import (
    attach_symbol_specific_state_strength_calibration_fields_v1,
    build_symbol_specific_state_strength_calibration_contract_v1,
    generate_and_write_symbol_specific_state_strength_calibration_summary_v1,
)


def test_symbol_specific_state_strength_contract_exposes_family_shape():
    contract = build_symbol_specific_state_strength_calibration_contract_v1()
    assert contract["contract_version"] == "symbol_specific_state_strength_calibration_contract_v1"
    assert "UP_CONTINUATION" in contract["profile_family_enum_v1"]
    assert "DOWN_CONTINUATION" in contract["profile_family_enum_v1"]


def test_attach_symbol_specific_state_strength_calibration_marks_nas_up_xau_up_xau_down_and_btc_pending():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "state_strength_continuation_integrity_v1": 0.97,
            "state_strength_reversal_evidence_v1": 0.04,
            "state_strength_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "breakout_hold_quality_v1": "STRONG",
            "body_drive_state_v1": "STRONG_DRIVE",
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
        },
        "XAUUSD_UP": {
            "symbol": "XAUUSD",
            "state_strength_continuation_integrity_v1": 0.79,
            "state_strength_reversal_evidence_v1": 0.18,
            "state_strength_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "few_candle_structure_bias_v1": "MIXED",
            "breakout_hold_quality_v1": "STABLE",
            "body_drive_state_v1": "WEAK_DRIVE",
            "box_state": "LOWER",
            "bb_state": "UNKNOWN",
        },
        "XAUUSD_DOWN": {
            "symbol": "XAUUSD",
            "state_strength_continuation_integrity_v1": 0.81,
            "state_strength_reversal_evidence_v1": 0.14,
            "state_strength_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "breakout_hold_quality_v1": "WEAK",
            "body_drive_state_v1": "WEAK_DRIVE",
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
        },
        "BTCUSD": {
            "symbol": "BTCUSD",
            "state_strength_continuation_integrity_v1": 0.63,
            "state_strength_reversal_evidence_v1": 0.21,
            "state_strength_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
        },
    }

    enriched = attach_symbol_specific_state_strength_calibration_fields_v1(rows)

    assert enriched["NAS100"]["symbol_state_strength_profile_family_v1"] == "UP_CONTINUATION"
    assert enriched["NAS100"]["symbol_state_strength_profile_match_v1"] == "MATCH"
    assert enriched["NAS100"]["symbol_state_strength_bias_hint_v1"] == "PREFER_CONTINUATION_WITH_FRICTION"
    assert enriched["NAS100"]["symbol_state_strength_flow_support_state_v1"] == "FLOW_CONFIRMED"

    assert enriched["XAUUSD_UP"]["symbol_state_strength_profile_family_v1"] == "UP_CONTINUATION"
    assert enriched["XAUUSD_UP"]["symbol_state_strength_profile_match_v1"] == "MATCH"
    assert enriched["XAUUSD_UP"]["symbol_state_strength_flow_support_state_v1"] in {"FLOW_CONFIRMED", "FLOW_BUILDING"}

    assert enriched["XAUUSD_DOWN"]["symbol_state_strength_profile_family_v1"] == "DOWN_CONTINUATION"
    assert enriched["XAUUSD_DOWN"]["symbol_state_strength_profile_match_v1"] == "MATCH"
    assert enriched["XAUUSD_DOWN"]["symbol_state_strength_flow_support_state_v1"] in {"FLOW_CONFIRMED", "FLOW_BUILDING"}

    assert enriched["BTCUSD"]["symbol_state_strength_profile_family_v1"] == "DOWN_CONTINUATION"
    assert enriched["BTCUSD"]["symbol_state_strength_profile_match_v1"] == "SEPARATE_PENDING"
    assert enriched["BTCUSD"]["symbol_state_strength_bias_hint_v1"] == "KEEP_SYMBOL_SEPARATE"


def test_generate_and_write_symbol_specific_state_strength_calibration_summary_writes_artifacts(tmp_path):
    report = generate_and_write_symbol_specific_state_strength_calibration_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "state_strength_continuation_integrity_v1": 0.97,
                "state_strength_reversal_evidence_v1": 0.04,
                "state_strength_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "breakout_hold_quality_v1": "STRONG",
                "body_drive_state_v1": "STRONG_DRIVE",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
            },
            "XAUUSD": {
                "symbol": "XAUUSD",
                "state_strength_continuation_integrity_v1": 0.79,
                "state_strength_reversal_evidence_v1": 0.18,
                "state_strength_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "few_candle_structure_bias_v1": "MIXED",
                "breakout_hold_quality_v1": "STABLE",
                "body_drive_state_v1": "WEAK_DRIVE",
                "box_state": "LOWER",
                "bb_state": "UNKNOWN",
            },
            "BTCUSD": {
                "symbol": "BTCUSD",
                "state_strength_continuation_integrity_v1": 0.5,
                "state_strength_reversal_evidence_v1": 0.2,
                "state_strength_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "BOUNDARY",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
            },
        },
        shadow_auto_dir=tmp_path,
    )

    assert (tmp_path / "symbol_specific_state_strength_calibration_latest.json").exists()
    assert (tmp_path / "symbol_specific_state_strength_calibration_latest.md").exists()
    assert report["summary"]["status"] == "READY"
    assert "flow_support_state_count_summary" in report["summary"]
