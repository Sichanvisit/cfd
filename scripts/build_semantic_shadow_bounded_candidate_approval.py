"""Build bounded candidate approval workflow output for semantic shadow staging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.semantic_shadow_bounded_candidate_approval import (  # noqa: E402
    build_semantic_shadow_bounded_candidate_approval,
    render_semantic_shadow_bounded_candidate_approval_markdown,
)


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


def _load_entries(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(path, low_memory=False)


def _default_stage_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_stage_latest.json"


def _default_approval_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "semantic_shadow_bounded_candidate_approval_entries.csv"


def _default_approved_model_dir() -> Path:
    return ROOT / "models" / "semantic_v1_bounded_approved_pending_activation"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_approval_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_approval_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_approval_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-json-path", default=str(_default_stage_json_path()))
    parser.add_argument("--approval-entries-path", default=str(_default_approval_entries_path()))
    parser.add_argument("--approved-model-dir", default=str(_default_approved_model_dir()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    stage_frame = _rows_from_json(Path(args.stage_json_path))
    approval_entries = _load_entries(Path(args.approval_entries_path))
    frame, summary = build_semantic_shadow_bounded_candidate_approval(
        stage_frame,
        approval_entries,
        approved_model_dir=args.approved_model_dir,
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
    md_output_path.write_text(
        render_semantic_shadow_bounded_candidate_approval_markdown(summary, frame),
        encoding="utf-8",
    )
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
