import json
from pathlib import Path

import pandas as pd

from backend.services.semantic_shadow_bounded_candidate_stage import (
    build_semantic_shadow_bounded_candidate_stage,
)


def test_build_semantic_shadow_bounded_candidate_stage_blocks_when_not_ready(tmp_path: Path) -> None:
    readiness = pd.DataFrame(
        [
            {
                "preview_model_dir": str(tmp_path / "preview"),
                "candidate_stage_dir": str(tmp_path / "stage"),
                "activation_ready_flag": False,
                "recommended_next_action": "keep_preview_only",
            }
        ]
    )
    bounded_gate = pd.DataFrame([{"gate_decision": "BLOCK_PREVIEW_DECISION"}])

    frame, summary = build_semantic_shadow_bounded_candidate_stage(
        readiness,
        preview_bundle_summary={"bundle_ready": True},
        bounded_gate=bounded_gate,
    )

    row = frame.iloc[0]
    assert row["stage_status"] == "blocked_before_stage"
    assert bool(row["approval_required"]) is False
    assert summary["approval_required_count"] == 0


def test_build_semantic_shadow_bounded_candidate_stage_copies_bundle_and_writes_packet(tmp_path: Path) -> None:
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    (preview_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    (preview_dir / "metrics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    stage_dir = tmp_path / "stage"
    readiness = pd.DataFrame(
        [
            {
                "preview_model_dir": str(preview_dir),
                "candidate_stage_dir": str(stage_dir),
                "activation_ready_flag": True,
            }
        ]
    )
    bounded_gate = pd.DataFrame([{"gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE"}])
    first_non_hold = pd.DataFrame(
        [
            {
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "decision": "APPLY_CANDIDATE",
            }
        ]
    )
    execution_eval = pd.DataFrame(
        [
            {
                "value_diff": 0.118,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
            }
        ]
    )

    frame, _summary = build_semantic_shadow_bounded_candidate_stage(
        readiness,
        preview_bundle_summary={"bundle_ready": True},
        bounded_gate=bounded_gate,
        first_non_hold=first_non_hold,
        execution_evaluation=execution_eval,
    )

    row = frame.iloc[0]
    assert row["stage_status"] == "candidate_runtime_staged"
    assert bool(row["approval_required"]) is True
    assert int(row["staged_file_count"]) == 2
    assert (stage_dir / "timing_model.joblib").exists()
    assert Path(str(row["candidate_manifest_path"])).exists()
    assert Path(str(row["approval_packet_path"])).exists()
