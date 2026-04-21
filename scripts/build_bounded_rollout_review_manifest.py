"""Build latest bounded rollout review manifest artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.bounded_rollout_review_manifest import (  # noqa: E402
    build_bounded_rollout_review_manifest,
    render_bounded_rollout_review_manifest_markdown,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def _load_csv_with_fallback(primary_path: str | Path, fallback_path: str | Path) -> pd.DataFrame:
    frame = _load_csv(primary_path)
    if not frame.empty:
        return frame
    return _load_csv(fallback_path)


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _default_dataset_dir() -> Path:
    return ROOT / "data" / "datasets" / "multi_surface_preview"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-gate-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_candidate_gate_latest.json"))
    parser.add_argument("--preview-evaluation-path", default=str(_default_shadow_auto_dir() / "symbol_surface_preview_evaluation_latest.json"))
    parser.add_argument("--initial-entry-path", default=str(_default_dataset_dir() / "initial_entry_dataset_resolved.csv"))
    parser.add_argument("--initial-entry-fallback-path", default=str(_default_dataset_dir() / "initial_entry_dataset.csv"))
    parser.add_argument("--csv-output-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_review_manifest_latest.csv"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_review_manifest_latest.json"))
    parser.add_argument("--md-output-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_review_manifest_latest.md"))
    args = parser.parse_args()

    frame, summary = build_bounded_rollout_review_manifest(
        bounded_rollout_candidate_gate_payload=_load_json(args.candidate_gate_path),
        symbol_surface_preview_evaluation_payload=_load_json(args.preview_evaluation_path),
        initial_entry_dataset=_load_csv_with_fallback(args.initial_entry_path, args.initial_entry_fallback_path),
    )
    markdown = render_bounded_rollout_review_manifest_markdown(summary, frame)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
