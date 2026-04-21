import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_mf17_rollout_pending_diagnostic.py"
spec = importlib.util.spec_from_file_location("build_mf17_rollout_pending_diagnostic", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_mf17_rollout_pending_diagnostic_reports_preview_blocker(tmp_path: Path) -> None:
    preview_path = tmp_path / "preview.json"
    preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "market_family": "BTCUSD",
                        "surface_name": "initial_entry_surface",
                        "readiness_state": "needs_label_resolution",
                        "recommended_action": "resolve_probe_and_wait_labels",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "market_family": "BTCUSD",
                        "surface_name": "initial_entry_surface",
                        "rollout_candidate_state": "HOLD_NOT_READY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    activation_contract_path = tmp_path / "activation_contract.json"
    activation_contract_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "market_family": "BTCUSD",
                        "surface_name": "initial_entry_surface",
                        "contract_status": "PENDING_MANUAL_SIGNOFF",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    activation_apply_path = tmp_path / "activation_apply.json"
    activation_apply_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "market_family": "BTCUSD",
                        "surface_name": "initial_entry_surface",
                        "activation_state": "HOLD_MANUAL_SIGNOFF",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "diagnostic.json"

    rc = module.main(
        [
            "--preview-evaluation-path",
            str(preview_path),
            "--candidate-gate-path",
            str(candidate_path),
            "--activation-contract-path",
            str(activation_contract_path),
            "--activation-apply-path",
            str(activation_apply_path),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["pending_stage"] == "preview"
    assert payload["rows"][0]["top_blocker"] == "preview_not_ready::needs_label_resolution"
    assert payload["rows"][0]["recommended_next_action"] == "resolve_probe_and_wait_labels"
