import json
from pathlib import Path

import pandas as pd

from backend.services.semantic_shadow_active_runtime_activation import (
    build_semantic_shadow_active_runtime_activation,
)


def test_active_runtime_activation_blocks_when_runtime_not_idle(tmp_path: Path) -> None:
    approved_dir = tmp_path / "approved_pending"
    approved_dir.mkdir(parents=True, exist_ok=True)
    (approved_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    approval_frame = pd.DataFrame(
        [
            {
                "approval_status": "approved_pending_activation",
                "approval_decision": "APPROVE",
                "decision_by": "codex",
                "decision_at": "2026-04-08T19:00:00+09:00",
                "approved_model_dir": str(approved_dir),
            }
        ]
    )
    runtime_status = {
        "updated_at": "2026-04-08T19:01:00+09:00",
        "semantic_live_config": {"mode": "disabled"},
        "runtime_recycle": {"last_open_positions_count": 2},
    }

    frame, summary = build_semantic_shadow_active_runtime_activation(
        approval_frame,
        runtime_status=runtime_status,
        active_model_dir=tmp_path / "semantic_v1",
        backup_root_dir=tmp_path / "backups",
    )

    row = frame.iloc[0]
    assert row["activation_status"] == "blocked_runtime_not_idle"
    assert bool(row["runtime_idle_flag"]) is False
    assert int(row["activated_file_count"]) == 0
    assert summary["activation_status_counts"]["blocked_runtime_not_idle"] == 1


def test_active_runtime_activation_copies_bundle_when_idle(tmp_path: Path) -> None:
    approved_dir = tmp_path / "approved_pending"
    approved_dir.mkdir(parents=True, exist_ok=True)
    (approved_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    (approved_dir / "metrics.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    active_dir = tmp_path / "semantic_v1"
    approval_frame = pd.DataFrame(
        [
            {
                "approval_status": "approved_pending_activation",
                "approval_decision": "APPROVE",
                "decision_by": "codex",
                "decision_at": "2026-04-08T19:00:00+09:00",
                "approved_model_dir": str(approved_dir),
            }
        ]
    )
    runtime_status = {
        "updated_at": "2026-04-08T19:01:00+09:00",
        "semantic_live_config": {"mode": "disabled"},
        "runtime_recycle": {"last_open_positions_count": 0},
    }

    frame, _summary = build_semantic_shadow_active_runtime_activation(
        approval_frame,
        runtime_status=runtime_status,
        active_model_dir=active_dir,
        backup_root_dir=tmp_path / "backups",
    )

    row = frame.iloc[0]
    assert row["activation_status"] == "activated_candidate_runtime"
    assert int(row["activated_file_count"]) == 2
    assert (active_dir / "timing_model.joblib").exists()
    assert Path(str(row["activation_manifest_path"])).exists()


def test_active_runtime_activation_can_force_activate_when_not_idle(tmp_path: Path) -> None:
    approved_dir = tmp_path / "approved_pending"
    approved_dir.mkdir(parents=True, exist_ok=True)
    (approved_dir / "timing_model.joblib").write_text("timing", encoding="utf-8")
    active_dir = tmp_path / "semantic_v1"
    approval_frame = pd.DataFrame(
        [
            {
                "approval_status": "approved_pending_activation",
                "approval_decision": "APPROVE",
                "decision_by": "codex",
                "decision_at": "2026-04-08T19:00:00+09:00",
                "approved_model_dir": str(approved_dir),
            }
        ]
    )
    runtime_status = {
        "updated_at": "2026-04-08T19:01:00+09:00",
        "semantic_live_config": {"mode": "disabled"},
        "runtime_recycle": {"last_open_positions_count": 2},
    }

    frame, _summary = build_semantic_shadow_active_runtime_activation(
        approval_frame,
        runtime_status=runtime_status,
        active_model_dir=active_dir,
        backup_root_dir=tmp_path / "backups",
        force_activate=True,
        override_reason="manual_override::ignore_manual_positions_for_activation_demo",
    )

    row = frame.iloc[0]
    assert row["activation_status"] == "activated_candidate_runtime_forced"
    assert bool(row["force_activate"]) is True
    assert row["override_reason"] == "manual_override::ignore_manual_positions_for_activation_demo"
    assert (active_dir / "timing_model.joblib").exists()
