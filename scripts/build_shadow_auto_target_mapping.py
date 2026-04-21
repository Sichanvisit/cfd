"""Build SA4d shadow target mapping redesign outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_target_mapping import (  # noqa: E402
    build_shadow_auto_target_mapping,
    load_shadow_training_corpus_context_frame,
    render_shadow_auto_target_mapping_markdown,
)


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_target_mapping_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_target_mapping_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_target_mapping_latest.md"


def _default_training_corpus_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--training-corpus-path", default=str(_default_training_corpus_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    manual_path = Path(args.manual_path)
    training_corpus_path = Path(args.training_corpus_path)
    manual_df = pd.read_csv(manual_path, encoding="utf-8-sig", low_memory=False) if manual_path.exists() else pd.DataFrame()
    training_df = load_shadow_training_corpus_context_frame(training_corpus_path)
    frame, summary = build_shadow_auto_target_mapping(manual_df, training_df)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output_path.write_text(render_shadow_auto_target_mapping_markdown(summary, frame), encoding="utf-8")
    print(json.dumps({"manual_path": str(manual_path), "training_corpus_path": str(training_corpus_path), "csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
