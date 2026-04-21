"""Apply follow-through negative expansion drafts into an augmented dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.follow_through_negative_expansion_apply import (  # noqa: E402
    build_follow_through_negative_expansion_apply,
    render_follow_through_negative_expansion_apply_markdown,
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


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _default_dataset_dir() -> Path:
    return ROOT / "data" / "datasets" / "multi_surface_preview"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--follow-through-path", default=str(_default_dataset_dir() / "follow_through_dataset.csv"))
    parser.add_argument("--draft-path", default=str(_default_shadow_auto_dir() / "follow_through_negative_expansion_draft_latest.json"))
    parser.add_argument("--csv-output-path", default=str(_default_shadow_auto_dir() / "follow_through_negative_expansion_apply_latest.csv"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "follow_through_negative_expansion_apply_latest.json"))
    parser.add_argument("--md-output-path", default=str(_default_shadow_auto_dir() / "follow_through_negative_expansion_apply_latest.md"))
    parser.add_argument("--augmented-dataset-output-path", default=str(_default_dataset_dir() / "follow_through_dataset_augmented.csv"))
    args = parser.parse_args()

    frame, augmented_dataset, summary = build_follow_through_negative_expansion_apply(
        follow_through_dataset=_load_csv(args.follow_through_path),
        follow_through_negative_expansion_draft_payload=_load_json(args.draft_path),
    )
    markdown = render_follow_through_negative_expansion_apply_markdown(summary, frame)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    augmented_dataset_output_path = Path(args.augmented_dataset_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    augmented_dataset_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    augmented_dataset.to_csv(augmented_dataset_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records"), "augmented_dataset_path": str(augmented_dataset_output_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")

    print(json.dumps({"csv_output_path": str(csv_output_path), "json_output_path": str(json_output_path), "md_output_path": str(md_output_path), "augmented_dataset_output_path": str(augmented_dataset_output_path), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
