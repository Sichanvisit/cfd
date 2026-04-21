"""Build guarded readiness output for promoting preview shadow runtime toward active usage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.semantic_shadow_active_runtime_readiness import (  # noqa: E402
    build_semantic_shadow_active_runtime_readiness,
    render_semantic_shadow_active_runtime_readiness_markdown,
)


def _default_preview_bundle_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_preview_bundle_latest.json"


def _default_bounded_gate_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_bounded_apply_gate_latest.json"


def _default_active_model_dir() -> Path:
    return ROOT / "models" / "semantic_v1"


def _default_candidate_stage_dir() -> Path:
    return ROOT / "models" / "semantic_v1_bounded_candidate"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_readiness_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_readiness_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_readiness_latest.md"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _rows_from_json(path: Path) -> pd.DataFrame:
    payload = _load_json(path)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-bundle-json-path", default=str(_default_preview_bundle_json_path()))
    parser.add_argument("--bounded-gate-json-path", default=str(_default_bounded_gate_json_path()))
    parser.add_argument("--preview-model-dir", default=str(ROOT / "models" / "semantic_v1_preview_bridge_proxy"))
    parser.add_argument("--active-model-dir", default=str(_default_active_model_dir()))
    parser.add_argument("--candidate-stage-dir", default=str(_default_candidate_stage_dir()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    preview_payload = _load_json(Path(args.preview_bundle_json_path))
    preview_summary = preview_payload.get("summary", {}) if isinstance(preview_payload, dict) else {}
    bounded_gate = _rows_from_json(Path(args.bounded_gate_json_path))

    frame, summary = build_semantic_shadow_active_runtime_readiness(
        preview_summary,
        bounded_gate,
        preview_model_dir=args.preview_model_dir,
        active_model_dir=args.active_model_dir,
        candidate_stage_dir=args.candidate_stage_dir,
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(render_semantic_shadow_active_runtime_readiness_markdown(summary, frame), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
