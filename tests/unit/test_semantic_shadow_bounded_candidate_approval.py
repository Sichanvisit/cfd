import json
from pathlib import Path

import pandas as pd

from backend.services.semantic_shadow_bounded_candidate_approval import (
    build_semantic_shadow_bounded_candidate_approval,
)


def test_bounded_candidate_approval_is_pending_without_entries(tmp_path: Path) -> None:
    stage_dir = tmp_path / "candidate_stage"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    stage_frame = pd.DataFrame(
        [
            {
                "stage_event_id": "semantic_shadow_stage::0001",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "stage_status": "candidate_runtime_staged",
                "approval_required": True,
                "preview_decision": "APPLY_CANDIDATE",
                "gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                "value_diff": 0.118,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
                "candidate_stage_dir": str(stage_dir),
            }
        ]
    )

    frame, summary = build_semantic_shadow_bounded_candidate_approval(
        stage_frame,
        pd.DataFrame(),
        approved_model_dir=tmp_path / "approved",
    )

    row = frame.iloc[0]
    assert row["approval_status"] == "pending_human_review"
    assert row["recommended_next_action"] == "fill_shadow_bounded_candidate_approval_entry"
    assert summary["approval_status_counts"]["pending_human_review"] == 1


def test_bounded_candidate_approval_copies_stage_when_approved(tmp_path: Path) -> None:
    stage_dir = tmp_path / "candidate_stage"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    (stage_dir / "metrics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    approved_dir = tmp_path / "approved_pending"
    stage_frame = pd.DataFrame(
        [
            {
                "stage_event_id": "semantic_shadow_stage::0001",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "stage_status": "candidate_runtime_staged",
                "approval_required": True,
                "preview_decision": "APPLY_CANDIDATE",
                "gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                "value_diff": 0.118,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
                "candidate_stage_dir": str(stage_dir),
            }
        ]
    )
    entries = pd.DataFrame(
        [
            {
                "stage_event_id": "semantic_shadow_stage::0001",
                "decision": "APPROVE",
                "decision_by": "codex",
                "decision_at": "2026-04-08T19:00:00+09:00",
                "reason_summary": "manual_review::bounded_candidate_looks_safe",
            }
        ]
    )

    frame, _summary = build_semantic_shadow_bounded_candidate_approval(
        stage_frame,
        entries,
        approved_model_dir=approved_dir,
    )

    row = frame.iloc[0]
    assert row["approval_status"] == "approved_pending_activation"
    assert int(row["approved_file_count"]) == 2
    assert (approved_dir / "timing_model.joblib").exists()
    assert Path(str(row["activation_manifest_path"])).exists()
