import json

from backend.services.xau_readonly_surface_contract import (
    attach_xau_readonly_surface_fields_v1,
    build_xau_readonly_surface_contract_v1,
    generate_and_write_xau_readonly_surface_summary_v1,
)


def test_xau_readonly_surface_contract_exposes_xau_row_fields():
    contract = build_xau_readonly_surface_contract_v1()

    assert contract["contract_version"] == "xau_readonly_surface_contract_v1"
    assert "xau_state_slot_core_v1" in contract["row_level_fields_v1"]
    assert contract["dominance_protection_v1"]["xau_readonly_surface_can_change_dominant_side"] is False


def test_attach_xau_readonly_surface_fields_surfaces_xau_profile():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "symbol_state_strength_best_profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
            "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
            "symbol_state_strength_profile_match_v1": "MATCH",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "consumer_check_reason": "lower_rebound_probe_observe",
            "previous_box_break_state": "BREAKOUT_HELD",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
        }
    }

    enriched = attach_xau_readonly_surface_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["xau_polarity_slot_v1"] == "BULL"
    assert row["xau_intent_slot_v1"] == "RECOVERY"
    assert row["xau_texture_slot_v1"] == "WITH_FRICTION"
    assert row["xau_pilot_window_match_v1"] == "MATCHED_ACTIVE_PROFILE"


def test_generate_and_write_xau_readonly_surface_summary_writes_artifacts(tmp_path):
    report = generate_and_write_xau_readonly_surface_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "symbol_state_strength_best_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
                "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
                "symbol_state_strength_profile_match_v1": "MATCH",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION",
                "consumer_check_reason": "upper_break_fail_confirm",
                "previous_box_break_state": "BREAKDOWN_HELD",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "xau_readonly_surface_latest.json"
    md_path = tmp_path / "xau_readonly_surface_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["xau_row_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
