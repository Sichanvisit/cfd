from pathlib import Path

from backend.services import improvement_board_field_policy as board_policy


def test_board_field_policy_exposes_canonical_sections_and_fields() -> None:
    payload = board_policy.build_improvement_board_field_baseline()

    assert "summary" in payload["section_names"]
    assert "readiness_state" in payload["section_names"]
    assert "blocking_reason" in payload["summary_fields"]
    assert "pa8_closeout_readiness_status" in payload["readiness_fields"]
    assert "pa8_closeout_focus_status" in payload["summary_fields"]
    assert "pa8_closeout_focus_next_required_action" in payload["readiness_fields"]
    assert "first_symbol_closeout_handoff_status" in payload["summary_fields"]
    assert "first_symbol_closeout_handoff_stage" in payload["readiness_fields"]
    assert "pa8_closeout_review_state" in payload["summary_fields"]
    assert "pa8_closeout_apply_state" in payload["readiness_fields"]
    assert "pa7_narrow_review_status" in payload["summary_fields"]
    assert "pa7_narrow_review_primary_group_key" in payload["readiness_fields"]
    assert "historical_cost_confidence_level" in payload["readiness_fields"]


def test_board_field_policy_derives_readiness_statuses_and_confidence() -> None:
    assert (
        board_policy.derive_pa8_closeout_readiness_status(
            phase="RUNNING",
            active_symbol_count=3,
            live_window_ready_count=1,
        )
        == "PENDING_EVIDENCE"
    )
    assert (
        board_policy.derive_pa9_handoff_readiness_status(
            pa9_handoff_state="HOLD_PENDING_PA8_LIVE_WINDOW",
            pa9_review_state="HOLD_PENDING_PA8_LIVE_WINDOW",
            pa9_apply_state="HOLD_PENDING_PA8_LIVE_WINDOW",
        )
        == "PENDING_EVIDENCE"
    )
    assert (
        board_policy.derive_pa9_handoff_readiness_status(
            pa9_handoff_state="ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
            pa9_review_state="ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
            pa9_apply_state="ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
        )
        == "APPLIED"
    )
    assert board_policy.normalize_confidence_level("limited") == "LIMITED"


def test_board_field_policy_writes_snapshot(tmp_path: Path) -> None:
    json_path = tmp_path / "improvement_board_field_baseline_latest.json"
    markdown_path = tmp_path / "improvement_board_field_baseline_latest.md"

    result = board_policy.write_improvement_board_field_baseline_snapshot(
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result["contract_version"] == board_policy.IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION
    assert json_path.exists()
    assert markdown_path.exists()
    assert "readiness_state" in json_path.read_text(encoding="utf-8")
    assert "## Readiness Fields" in markdown_path.read_text(encoding="utf-8")
