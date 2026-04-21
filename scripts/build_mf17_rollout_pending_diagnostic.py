"""Build a compact diagnostic for the current MF17 pending rollout chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.mf17_rollout_pending_diagnostic import (  # noqa: E402
    build_mf17_rollout_pending_diagnostic,
    default_mf17_rollout_pending_diagnostic_path,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-evaluation-path", default=str(_default_shadow_auto_dir() / "symbol_surface_preview_evaluation_latest.json"))
    parser.add_argument("--candidate-gate-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_candidate_gate_latest.json"))
    parser.add_argument("--review-manifest-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_review_manifest_latest.json"))
    parser.add_argument("--signoff-criteria-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_signoff_criteria_latest.json"))
    parser.add_argument("--signoff-packet-path", default=str(_default_shadow_auto_dir() / "symbol_surface_canary_signoff_packet_latest.json"))
    parser.add_argument("--manual-signoff-apply-path", default=str(_default_shadow_auto_dir() / "symbol_surface_manual_signoff_apply_latest.json"))
    parser.add_argument("--activation-contract-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.json"))
    parser.add_argument("--activation-apply-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.json"))
    parser.add_argument("--json-output-path", default=str(default_mf17_rollout_pending_diagnostic_path()))
    args = parser.parse_args(argv)

    rows, summary = build_mf17_rollout_pending_diagnostic(
        symbol_surface_preview_evaluation_payload=_load_json(args.preview_evaluation_path),
        bounded_rollout_candidate_gate_payload=_load_json(args.candidate_gate_path),
        bounded_rollout_review_manifest_payload=_load_json(args.review_manifest_path),
        bounded_rollout_signoff_criteria_payload=_load_json(args.signoff_criteria_path),
        symbol_surface_canary_signoff_packet_payload=_load_json(args.signoff_packet_path),
        symbol_surface_manual_signoff_apply_payload=_load_json(args.manual_signoff_apply_path),
        bounded_symbol_surface_activation_contract_payload=_load_json(args.activation_contract_path),
        bounded_symbol_surface_activation_apply_payload=_load_json(args.activation_apply_path),
    )

    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": rows.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"json_output_path": str(json_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
