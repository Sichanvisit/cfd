import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_build_checkpoint_backfill_value_normalization_audit_script_writes_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dataset_dir = repo_root / "data" / "datasets" / "path_checkpoint"
    analysis_dir = repo_root / "data" / "analysis" / "shadow_auto"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    resolved_path = dataset_dir / "checkpoint_dataset_resolved.csv"
    review_path = analysis_dir / "checkpoint_pa7_review_processor_latest.json"
    output_path = analysis_dir / "checkpoint_backfill_value_normalization_audit_latest.json"

    original_resolved = resolved_path.read_text(encoding="utf-8") if resolved_path.exists() else None
    original_review = review_path.read_text(encoding="utf-8") if review_path.exists() else None
    original_output = output_path.read_text(encoding="utf-8") if output_path.exists() else None

    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T15:19:12+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": -378.0,
                "giveback_ratio": 0.000026,
                "source": "closed_trade_hold_backfill",
                "checkpoint_id": "XAU_CP003",
            },
            {
                "generated_at": "2026-04-10T22:03:46+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": 3.11,
                "giveback_ratio": 0.0,
                "source": "exit_manage_runner",
                "checkpoint_id": "XAU_CP004",
            },
        ]
    ).to_csv(resolved_path, index=False)

    review_payload = {
        "group_rows": [
            {
                "group_key": (
                    "XAUUSD | continuation_hold_surface | RUNNER_CHECK | "
                    "runner_secured_continuation | runner_secured_continuation | WAIT"
                ),
                "review_disposition": "mixed_backfill_value_scale_review",
            }
        ]
    }
    review_path.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        completed = subprocess.run(
            [sys.executable, str(repo_root / "scripts" / "build_checkpoint_backfill_value_normalization_audit.py")],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["summary"]["target_group_count"] == 1
        assert payload["group_rows"][0]["audit_state"] == "source_scale_incompatibility_likely"
        stdout_payload = json.loads(completed.stdout)
        assert (
            stdout_payload["recommended_next_action"]
            == "review_backfill_source_scale_incompatibility_before_any_rule_patch"
        )
    finally:
        if original_resolved is None:
            resolved_path.unlink(missing_ok=True)
        else:
            resolved_path.write_text(original_resolved, encoding="utf-8")
        if original_review is None:
            review_path.unlink(missing_ok=True)
        else:
            review_path.write_text(original_review, encoding="utf-8")
        if original_output is None:
            output_path.unlink(missing_ok=True)
        else:
            output_path.write_text(original_output, encoding="utf-8")
