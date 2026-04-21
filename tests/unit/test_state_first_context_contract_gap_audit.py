import json
from pathlib import Path

from backend.services.state_first_context_contract_gap_audit import (
    build_state_first_context_contract_gap_audit,
    write_state_first_context_contract_gap_audit,
)


def test_build_state_first_context_contract_gap_audit_classifies_fields():
    runtime_status = {
        "updated_at": "2026-04-13T22:40:00+09:00",
        "latest_signal_by_symbol": {
            "NAS100": {
                "trend_1h_direction": "UPTREND",
                "active_action_conflict_detected": True,
                "box_state": "ABOVE",
            },
            "BTCUSD": {
                "box_state": "INSIDE",
            },
        },
    }
    field_catalog = [
        {
            "context_group": "HTF",
            "state_layer": "raw",
            "target_field": "trend_1h_direction",
            "direct_runtime_fields": ["trend_1h_direction"],
            "related_proxy_fields": ["mtf_ma_big_map_v1"],
            "source_refs": [{"file": "stub_htf.py", "tokens": ["TIMEFRAME_H1"]}],
            "recommended_next_action": "promote_via_ST1_htf_cache",
            "notes_ko": "htf raw",
        },
        {
            "context_group": "CONFLICT",
            "state_layer": "interpreted",
            "target_field": "context_conflict_state",
            "direct_runtime_fields": ["context_conflict_state"],
            "related_proxy_fields": ["active_action_conflict_detected"],
            "source_refs": [],
            "recommended_next_action": "build_in_ST3_context_state_builder",
            "notes_ko": "conflict",
        },
        {
            "context_group": "SHARE",
            "state_layer": "raw",
            "target_field": "cluster_share_symbol",
            "direct_runtime_fields": ["cluster_share_symbol"],
            "related_proxy_fields": [],
            "source_refs": [{"file": "stub_share.py", "tokens": ["cluster_symbol_share"]}],
            "recommended_next_action": "promote_via_ST6_share_state",
            "notes_ko": "share",
        },
        {
            "context_group": "META",
            "state_layer": "meta",
            "target_field": "context_state_version",
            "direct_runtime_fields": ["context_state_version"],
            "related_proxy_fields": [],
            "source_refs": [],
            "recommended_next_action": "add_meta_in_ST3_context_state_builder",
            "notes_ko": "meta",
        },
    ]
    source_map = {
        "stub_htf.py": "TIMEFRAME_H1 copy_rates_from_pos",
        "stub_share.py": "cluster_symbol_share semantic cluster",
    }

    payload = build_state_first_context_contract_gap_audit(
        runtime_status,
        source_text_by_relpath=source_map,
        field_catalog=field_catalog,
    )
    rows = {row["target_field"]: row for row in payload["field_rows"]}

    assert rows["trend_1h_direction"]["audit_state"] == "DIRECT_PRESENT"
    assert rows["trend_1h_direction"]["proxy_evidence_level"] == "DIRECT_FIELD"

    assert rows["context_conflict_state"]["audit_state"] == "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
    assert rows["context_conflict_state"]["proxy_evidence_level"] == "RUNTIME_RELATED_PROXY"

    assert rows["cluster_share_symbol"]["audit_state"] == "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
    assert rows["cluster_share_symbol"]["proxy_evidence_level"] == "SOURCE_TOKEN_ONLY"

    assert rows["context_state_version"]["audit_state"] == "NOT_COMPUTED_YET"
    assert payload["summary"]["direct_present_count"] == 1
    assert payload["summary"]["already_computed_but_not_promoted_count"] == 2
    assert payload["summary"]["not_computed_yet_count"] == 1
    assert payload["summary"]["recommended_next_step"] == "start_ST3_context_state_builder"


def test_write_state_first_context_contract_gap_audit_writes_outputs(tmp_path: Path):
    runtime_status = {
        "updated_at": "2026-04-13T22:40:00+09:00",
        "latest_signal_by_symbol": {
            "NAS100": {
                "box_state": "ABOVE",
            }
        },
    }
    field_catalog = [
        {
            "context_group": "PREVIOUS_BOX",
            "state_layer": "raw",
            "target_field": "previous_box_high",
            "direct_runtime_fields": ["previous_box_high"],
            "related_proxy_fields": ["box_state"],
            "source_refs": [],
            "recommended_next_action": "promote_via_ST2_previous_box_calculator",
            "notes_ko": "prev box",
        }
    ]

    json_path = tmp_path / "audit.json"
    md_path = tmp_path / "audit.md"
    payload = write_state_first_context_contract_gap_audit(
        runtime_status,
        json_path=json_path,
        markdown_path=md_path,
        field_catalog=field_catalog,
        source_text_by_relpath={},
    )

    assert payload["summary"]["already_computed_but_not_promoted_count"] == 1
    assert json_path.exists()
    assert md_path.exists()

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert loaded["summary"]["recommended_next_step"] == "start_ST2_previous_box_calculator"
    assert "ST0 Current State Audit" in markdown
    assert "previous_box_high" in markdown
