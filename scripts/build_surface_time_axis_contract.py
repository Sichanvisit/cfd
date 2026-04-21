"""Build latest surface time-axis contract artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.surface_time_axis_contract import (  # noqa: E402
    build_surface_time_axis_contract,
    render_surface_time_axis_contract_markdown,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _default_check_color_label_formalization_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "check_color_label_formalization_latest.csv"


def _default_surface_objective_spec_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_objective_spec_latest.csv"


def _default_manual_wait_teacher_annotations_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_breakout_manual_overlap_seed_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "breakout_manual_overlap_seed_draft_latest.csv"


def _default_breakout_manual_overlap_seed_review_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "breakout_manual_overlap_seed_review_entries.csv"


def _default_manual_current_rich_seed_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_draft_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_time_axis_contract_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_time_axis_contract_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_time_axis_contract_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-color-label-formalization-path", default=str(_default_check_color_label_formalization_path()))
    parser.add_argument("--surface-objective-spec-path", default=str(_default_surface_objective_spec_path()))
    parser.add_argument("--manual-wait-teacher-annotations-path", default=str(_default_manual_wait_teacher_annotations_path()))
    parser.add_argument("--breakout-manual-overlap-seed-draft-path", default=str(_default_breakout_manual_overlap_seed_draft_path()))
    parser.add_argument(
        "--breakout-manual-overlap-seed-review-entries-path",
        default=str(_default_breakout_manual_overlap_seed_review_entries_path()),
    )
    parser.add_argument("--manual-current-rich-seed-draft-path", default=str(_default_manual_current_rich_seed_draft_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_surface_time_axis_contract(
        _load_csv(args.check_color_label_formalization_path),
        _load_csv(args.surface_objective_spec_path),
        _load_csv(args.manual_wait_teacher_annotations_path),
        _load_csv(args.breakout_manual_overlap_seed_draft_path),
        _load_csv(args.breakout_manual_overlap_seed_review_entries_path),
        _load_csv(args.manual_current_rich_seed_draft_path),
    )
    markdown = render_surface_time_axis_contract_markdown(summary, frame)

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
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
