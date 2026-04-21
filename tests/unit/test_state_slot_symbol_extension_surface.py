import json

from backend.services.state_slot_symbol_extension_surface import (
    attach_state_slot_symbol_extension_surface_fields_v1,
    build_state_slot_symbol_extension_surface_contract_v1,
    generate_and_write_state_slot_symbol_extension_surface_summary_v1,
)


def test_state_slot_symbol_extension_surface_contract_exposes_common_fields():
    contract = build_state_slot_symbol_extension_surface_contract_v1()

    assert contract["contract_version"] == "state_slot_symbol_extension_surface_contract_v1"
    assert "common_state_slot_core_v1" in contract["row_level_fields_v1"]
    assert contract["dominance_protection_v1"]["symbol_extension_can_change_dominant_side"] is False


def test_attach_state_slot_symbol_extension_surface_fields_maps_nas_and_btc():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "symbol_state_strength_profile_family_v1": "UP_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "BREAKOUT_HELD",
            "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
            "symbol_state_strength_profile_match_v1": "MATCH",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STRONG",
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
        },
        "BTCUSD": {
            "symbol": "BTCUSD",
            "symbol_state_strength_profile_family_v1": "UP_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "LOWER_RECOVERY_REBOUND",
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "consumer_check_reason": "lower_rebound_probe_observe",
            "breakout_hold_quality_v1": "WEAK",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
        },
    }

    enriched = attach_state_slot_symbol_extension_surface_fields_v1(rows)

    nas = enriched["NAS100"]
    btc = enriched["BTCUSD"]

    assert nas["state_slot_symbol_extension_state_v1"] == "NAS_STAGE_EXTENSION"
    assert nas["common_state_slot_core_v1"] == "BULL_CONTINUATION_ACCEPTANCE"
    assert nas["common_vocabulary_compatibility_v1"] == "COMPATIBLE"

    assert btc["state_slot_symbol_extension_state_v1"] == "BTC_RECOVERY_DRIFT_EXTENSION"
    assert btc["common_state_slot_core_v1"] == "BULL_RECOVERY_INITIATION"
    assert btc["common_vocabulary_compatibility_v1"] == "REVIEW_PENDING"


def test_attach_state_slot_symbol_extension_surface_overrides_nas_pending_review_when_bullish_continuation_is_strong():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "symbol_state_strength_profile_family_v1": "DOWN_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "PENDING_REVIEW",
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "dominance_shadow_dominant_side_v1": "BULL",
            "htf_alignment_state": "WITH_HTF",
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "breakout_candidate_direction": "UP",
            "breakout_candidate_action_target": "PROBE_BREAKOUT",
            "breakout_hold_quality_v1": "WEAK",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "consumer_check_reason": "outer_band_reversal_support_required_observe",
        }
    }

    enriched = attach_state_slot_symbol_extension_surface_fields_v1(rows)
    nas = enriched["NAS100"]

    assert nas["common_state_polarity_slot_v1"] == "BULL"
    assert nas["common_state_intent_slot_v1"] == "CONTINUATION"
    assert nas["common_state_slot_core_v1"] == "BULL_CONTINUATION_INITIATION"


def test_attach_state_slot_symbol_extension_surface_overrides_nas_pending_review_from_buy_watch_overlay():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "symbol_state_strength_profile_family_v1": "DOWN_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "PENDING_REVIEW",
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "dominance_shadow_dominant_side_v1": "BULL",
            "htf_alignment_state": "WITH_HTF",
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "breakout_candidate_direction": "NONE",
            "breakout_candidate_action_target": "WAIT_MORE",
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_score": 0.84,
            "chart_event_kind_hint": "BUY_WATCH",
            "breakout_hold_quality_v1": "WEAK",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "consumer_check_reason": "outer_band_reversal_support_required_observe",
        }
    }

    enriched = attach_state_slot_symbol_extension_surface_fields_v1(rows)
    nas = enriched["NAS100"]

    assert nas["common_state_polarity_slot_v1"] == "BULL"
    assert nas["common_state_intent_slot_v1"] == "CONTINUATION"
    assert nas["common_state_slot_core_v1"] == "BULL_CONTINUATION_INITIATION"


def test_attach_state_slot_symbol_extension_surface_promotes_btc_lower_rebound_to_bull_recovery_before_breakdown_holds():
    rows = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "symbol_state_strength_profile_family_v1": "DOWN_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "LOWER_RECOVERY_REBOUND",
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "dominance_shadow_dominant_side_v1": "BULL",
            "consumer_check_side": "BUY",
            "consumer_check_reason": "lower_rebound_confirm",
            "previous_box_break_state": "INSIDE",
            "previous_box_relation": "INSIDE",
            "breakout_hold_quality_v1": "WEAK",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
        }
    }

    enriched = attach_state_slot_symbol_extension_surface_fields_v1(rows)
    btc = enriched["BTCUSD"]

    assert btc["common_state_polarity_slot_v1"] == "BULL"
    assert btc["common_state_intent_slot_v1"] == "RECOVERY"
    assert btc["common_state_slot_core_v1"] == "BULL_RECOVERY_INITIATION"


def test_attach_state_slot_symbol_extension_surface_softens_boundary_ambiguity_when_directional_context_is_consistent():
    rows = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "symbol_state_strength_profile_family_v1": "DOWN_CONTINUATION",
            "symbol_state_strength_profile_subtype_v1": "UPPER_DRIFT_FADE",
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "consumer_check_side": "SELL",
            "chart_event_kind_hint": "SELL_WAIT",
            "previous_box_break_state": "BREAKDOWN_HELD",
            "previous_box_relation": "BELOW",
            "breakout_hold_quality_v1": "WEAK",
            "box_state": "BELOW",
            "bb_state": "BREAKDOWN",
        }
    }

    enriched = attach_state_slot_symbol_extension_surface_fields_v1(rows)
    btc = enriched["BTCUSD"]

    assert btc["common_state_ambiguity_level_v1"] == "MEDIUM"


def test_generate_and_write_state_slot_symbol_extension_surface_summary_writes_artifacts(tmp_path):
    report = generate_and_write_state_slot_symbol_extension_surface_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "xau_readonly_surface_profile_v1": {"contract_version": "xau_readonly_surface_contract_v1", "applicable_v1": True},
                "xau_polarity_slot_v1": "BEAR",
                "xau_intent_slot_v1": "REJECTION",
                "xau_continuation_stage_v1": "ACCEPTANCE",
                "xau_rejection_type_v1": "REVERSAL_REJECTION",
                "xau_texture_slot_v1": "CLEAN",
                "xau_location_context_v1": "POST_BREAKOUT",
                "xau_tempo_profile_v1": "PERSISTING",
                "xau_ambiguity_level_v1": "LOW",
                "xau_state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
                "xau_state_slot_modifier_bundle_v1": ["CLEAN", "POST_BREAKOUT", "PERSISTING", "AMBIGUITY_LOW"],
            },
            "NAS100": {
                "symbol": "NAS100",
                "symbol_state_strength_profile_family_v1": "UP_CONTINUATION",
                "symbol_state_strength_profile_subtype_v1": "BREAKOUT_HELD",
                "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
                "symbol_state_strength_profile_match_v1": "MATCH",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "breakout_hold_quality_v1": "STABLE",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
            },
            "BTCUSD": {
                "symbol": "BTCUSD",
                "symbol_state_strength_profile_family_v1": "UP_CONTINUATION",
                "symbol_state_strength_profile_subtype_v1": "LOWER_RECOVERY_REBOUND",
                "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
                "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "consumer_check_reason": "lower_rebound_probe_observe",
                "breakout_hold_quality_v1": "WEAK",
                "box_state": "BELOW",
                "bb_state": "LOWER_EDGE",
            },
        },
        state_slot_commonization_judge_report={
            "slot_catalog_v1": [
                {
                    "state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
                    "commonization_verdict_v1": "COMMON_WITH_SYMBOL_THRESHOLD",
                    "threshold_specificity_required_v1": True,
                }
            ]
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_slot_symbol_extension_surface_latest.json"
    md_path = tmp_path / "state_slot_symbol_extension_surface_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 3
    assert report["artifact_paths"]["json_path"] == str(json_path)
