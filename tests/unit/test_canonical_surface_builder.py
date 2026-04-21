import json

from backend.services.canonical_surface_builder import (
    CANONICAL_SURFACE_CONTRACT_VERSION,
    attach_canonical_surface_fields_v1,
    build_canonical_surface_contract_v1,
    build_canonical_surface_row_v1,
    generate_and_write_canonical_surface_summary_v1,
)


def test_build_canonical_surface_contract_v1_exposes_priority_rule():
    contract = build_canonical_surface_contract_v1()

    assert contract["contract_version"] == CANONICAL_SURFACE_CONTRACT_VERSION
    assert contract["priority_rule_v1"] == "phase>continuation>direction"
    assert "BUY_WATCH" in contract["runtime_surface_enum_v1"]
    assert "BUY_EXECUTION" in contract["execution_surface_enum_v1"]


def test_build_canonical_surface_row_v1_maps_runtime_and_execution():
    row = build_canonical_surface_row_v1(
        {
            "session_bucket_v1": "US",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "execution_diff_final_action_side": "SELL",
        }
    )

    assert row["canonical_runtime_surface_name_v1"] == "BUY_WATCH"
    assert row["canonical_execution_surface_name_v1"] == "SELL_EXECUTION"
    assert row["canonical_direction_annotation_v1"] == "UP"
    assert row["canonical_continuation_annotation_v1"] == "CONTINUING"
    assert row["canonical_phase_v1"] == "CONTINUATION"
    assert row["canonical_runtime_execution_alignment_v1"] == "DIVERGED"


def test_attach_canonical_surface_fields_v1_updates_rows():
    rows = attach_canonical_surface_fields_v1(
        {
            "BTCUSD": {
                "directional_continuation_overlay_direction": "DOWN",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_selection_state": "LOW_ALIGNMENT",
                "execution_diff_final_action_side": "SKIP",
            }
        }
    )

    row = rows["BTCUSD"]
    assert row["canonical_runtime_surface_name_v1"] == "SELL_WATCH"
    assert row["canonical_phase_v1"] == "BOUNDARY"
    assert row["canonical_runtime_execution_alignment_v1"] == "WAITING"


def test_generate_and_write_canonical_surface_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_canonical_surface_summary_v1(
        {
            "NAS100": {
                "session_bucket_v1": "EU_US_OVERLAP",
                "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
                "directional_continuation_overlay_selection_state": "UP_SELECTED",
                "execution_diff_final_action_side": "BUY",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "canonical_surface_summary_latest.json"
    md_path = tmp_path / "canonical_surface_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
    assert payload["summary"]["runtime_surface_count_summary"]["BUY_WATCH"] == 1
