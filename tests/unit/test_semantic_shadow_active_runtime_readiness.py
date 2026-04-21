from pathlib import Path

import pandas as pd

from backend.services.semantic_shadow_active_runtime_readiness import (
    build_semantic_shadow_active_runtime_readiness,
)


def test_active_runtime_readiness_blocks_when_bounded_gate_not_ready(tmp_path: Path) -> None:
    preview_dir = tmp_path / "preview"
    active_dir = tmp_path / "active"
    stage_dir = tmp_path / "candidate"
    preview_dir.mkdir(parents=True, exist_ok=True)

    bounded_gate = pd.DataFrame(
        [
            {
                "gate_decision": "REQUIRE_MORE_MANUAL_TRUTH",
                "live_candidate_ready_flag": False,
                "recommended_next_action": "expand_manual_truth_shadow_overlap",
            }
        ]
    )

    frame, _summary = build_semantic_shadow_active_runtime_readiness(
        {"bundle_ready": True},
        bounded_gate,
        preview_model_dir=preview_dir,
        active_model_dir=active_dir,
        candidate_stage_dir=stage_dir,
    )

    row = frame.iloc[0]
    assert row["active_runtime_state"] == "blocked_preview_only"
    assert bool(row["activation_ready_flag"]) is False
    assert not stage_dir.exists()


def test_active_runtime_readiness_stages_candidate_when_gate_allows(tmp_path: Path) -> None:
    preview_dir = tmp_path / "preview"
    active_dir = tmp_path / "active"
    stage_dir = tmp_path / "candidate"
    preview_dir.mkdir(parents=True, exist_ok=True)

    bounded_gate = pd.DataFrame(
        [
            {
                "gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                "live_candidate_ready_flag": True,
            }
        ]
    )

    frame, summary = build_semantic_shadow_active_runtime_readiness(
        {"bundle_ready": True},
        bounded_gate,
        preview_model_dir=preview_dir,
        active_model_dir=active_dir,
        candidate_stage_dir=stage_dir,
    )

    row = frame.iloc[0]
    assert row["active_runtime_state"] == "candidate_stage_ready"
    assert bool(row["activation_ready_flag"]) is True
    assert stage_dir.exists()
    assert summary["activation_ready_count"] == 1
