import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_build_checkpoint_pa7_review_processor_script_writes_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dataset_dir = repo_root / "data" / "datasets" / "path_checkpoint"
    analysis_dir = repo_root / "data" / "analysis" / "shadow_auto"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    resolved_path = dataset_dir / "checkpoint_dataset_resolved.csv"
    original_resolved = resolved_path.read_text(encoding="utf-8") if resolved_path.exists() else None
    output_path = analysis_dir / "checkpoint_pa7_review_processor_latest.json"
    original_output = output_path.read_text(encoding="utf-8") if output_path.exists() else None

    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:00:00+09:00",
                "symbol": "NAS100",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.43,
                "runtime_partial_exit_ev": 0.37,
                "runtime_full_exit_risk": 0.56,
                "current_profit": -0.6,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            }
        ]
    ).to_csv(resolved_path, index=False)

    try:
        completed = subprocess.run(
            [sys.executable, str(repo_root / "scripts" / "build_checkpoint_pa7_review_processor.py")],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["summary"]["processed_group_count"] == 1
        assert payload["group_rows"][0]["review_disposition"] == "policy_mismatch_review"
        stdout_payload = json.loads(completed.stdout)
        assert stdout_payload["recommended_next_action"] == "review_policy_mismatch_groups_first"
    finally:
        if original_resolved is None:
            resolved_path.unlink(missing_ok=True)
        else:
            resolved_path.write_text(original_resolved, encoding="utf-8")
        if original_output is None:
            output_path.unlink(missing_ok=True)
        else:
            output_path.write_text(original_output, encoding="utf-8")
