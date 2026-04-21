"""
Build the patch-draft template output from the bias sandbox report.

Usage:
  python scripts/build_manual_vs_heuristic_patch_draft.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_patch_draft import (  # noqa: E402
    build_manual_vs_heuristic_patch_draft,
    load_frame,
    render_manual_vs_heuristic_patch_draft_markdown,
)


def _default_sandbox_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_bias_sandbox_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_patch_draft_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_patch_draft_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_patch_draft_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox-path", default=str(_default_sandbox_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    sandbox_path = Path(args.sandbox_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    sandbox = load_frame(sandbox_path)
    draft, summary = build_manual_vs_heuristic_patch_draft(sandbox)

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    draft.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": draft.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_vs_heuristic_patch_draft_markdown(summary, draft),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "sandbox_path": str(sandbox_path),
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
