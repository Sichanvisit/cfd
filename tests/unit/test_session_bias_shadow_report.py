import json

from backend.services.session_bias_shadow_report import (
    SESSION_BIAS_SHADOW_CONTRACT_VERSION,
    build_session_bias_shadow_contract_v1,
    build_session_bias_shadow_row_v1,
    generate_and_write_session_bias_shadow_report_v1,
)


def test_build_session_bias_shadow_contract_v1_is_shadow_only():
    contract = build_session_bias_shadow_contract_v1()

    assert contract["contract_version"] == SESSION_BIAS_SHADOW_CONTRACT_VERSION
    assert contract["mode"] == "shadow_only"
    assert contract["execution_change_allowed"] is False
    assert contract["state25_change_allowed"] is False


def test_build_session_bias_shadow_row_v1_raises_confidence_for_high_accuracy_directional_surface():
    row = build_session_bias_shadow_row_v1(
        {
            "timestamp": "2026-04-15T00:10:00+09:00",
            "canonical_direction_annotation_v1": "UP",
            "canonical_runtime_surface_name_v1": "BUY_WATCH",
            "canonical_runtime_execution_alignment_v1": "DIVERGED",
        },
        session_aware_annotation_accuracy_report={
            "summary": {
                "measured_count_by_session": {"US": 42},
                "direction_accuracy_by_session": {"US": 0.5849},
                "session_difference_significance": {"status": "SIGNIFICANT"},
            }
        },
    )

    assert row["session_bias_candidate_state_v1"] == "READY"
    assert row["session_bias_effect_v1"] == "RAISE_CONTINUATION_CONFIDENCE"
    assert row["session_bias_confidence_v1"] in {"MEDIUM", "HIGH"}
    assert row["would_change_surface_v1"] is True
    assert row["would_change_execution_v1"] is True
    assert row["execution_change_allowed"] is False


def test_build_session_bias_shadow_row_v1_lowers_confidence_for_low_accuracy_directional_surface():
    row = build_session_bias_shadow_row_v1(
        {
            "timestamp": "2026-04-15T16:10:00+09:00",
            "canonical_direction_annotation_v1": "DOWN",
            "canonical_runtime_surface_name_v1": "SELL_WATCH",
            "canonical_runtime_execution_alignment_v1": "MATCH",
        },
        session_aware_annotation_accuracy_report={
            "summary": {
                "measured_count_by_session": {"EU": 78},
                "direction_accuracy_by_session": {"EU": 0.3974},
                "session_difference_significance": {"status": "SIGNIFICANT"},
            }
        },
    )

    assert row["session_bias_candidate_state_v1"] == "READY"
    assert row["session_bias_effect_v1"] == "LOWER_CONTINUATION_CONFIDENCE"
    assert row["would_change_surface_v1"] is True
    assert row["would_change_execution_v1"] is False
    assert row["state25_change_allowed"] is False


def test_build_session_bias_shadow_row_v1_keeps_neutral_for_insufficient_sample():
    row = build_session_bias_shadow_row_v1(
        {
            "timestamp": "2026-04-15T08:10:00+09:00",
            "canonical_direction_annotation_v1": "UP",
            "canonical_runtime_surface_name_v1": "BUY_WATCH",
            "canonical_runtime_execution_alignment_v1": "WAITING",
        },
        session_aware_annotation_accuracy_report={
            "summary": {
                "measured_count_by_session": {"ASIA": 0},
                "direction_accuracy_by_session": {"ASIA": 0.0},
                "session_difference_significance": {"status": "SIGNIFICANT"},
            }
        },
    )

    assert row["session_bias_candidate_state_v1"] == "INSUFFICIENT_SAMPLE"
    assert row["session_bias_effect_v1"] == "KEEP_NEUTRAL"
    assert row["would_change_surface_v1"] is False
    assert row["would_change_execution_v1"] is False


def test_generate_and_write_session_bias_shadow_report_v1_writes_artifacts(tmp_path):
    report = generate_and_write_session_bias_shadow_report_v1(
        {
            "NAS100": {
                "timestamp": "2026-04-15T00:15:00+09:00",
                "canonical_direction_annotation_v1": "UP",
                "canonical_runtime_surface_name_v1": "BUY_WATCH",
                "canonical_runtime_execution_alignment_v1": "DIVERGED",
            }
        },
        session_aware_annotation_accuracy_report={
            "summary": {
                "measured_count_by_session": {"US": 42},
                "direction_accuracy_by_session": {"US": 0.5849},
                "session_difference_significance": {"status": "SIGNIFICANT"},
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "session_bias_shadow_report_latest.json"
    md_path = tmp_path / "session_bias_shadow_report_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
    assert payload["summary"]["mode"] == "shadow_only"
