"""Build latest continuation-hold and protective-exit augmentation draft artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.hold_exit_augmentation_draft import (  # noqa: E402
    build_hold_exit_augmentation_draft,
    render_hold_exit_augmentation_draft_markdown,
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
    parser.add_argument("--failure-harvest-path", default=str(_default_shadow_auto_dir() / "failure_label_harvest_latest.json"))
    parser.add_argument("--continuation-hold-path", default=str(_default_dataset_dir() / "continuation_hold_dataset.csv"))
    parser.add_argument("--protective-exit-path", default=str(_default_dataset_dir() / "protective_exit_dataset.csv"))
    parser.add_argument("--csv-output-path", default=str(_default_shadow_auto_dir() / "hold_exit_augmentation_draft_latest.csv"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "hold_exit_augmentation_draft_latest.json"))
    parser.add_argument("--md-output-path", default=str(_default_shadow_auto_dir() / "hold_exit_augmentation_draft_latest.md"))
    args = parser.parse_args()

    frame, summary = build_hold_exit_augmentation_draft(
        failure_label_harvest_payload=_load_json(args.failure_harvest_path),
        continuation_hold_dataset=_load_csv(args.continuation_hold_path),
        protective_exit_dataset=_load_csv(args.protective_exit_path),
    )
    markdown = render_hold_exit_augmentation_draft_markdown(summary, frame)

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
