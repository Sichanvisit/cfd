"""
Build next mismatch family ranking from the manual-vs-heuristic comparison report.

Usage:
  python scripts/build_manual_vs_heuristic_family_ranking.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_family_ranking import (  # noqa: E402
    build_manual_vs_heuristic_family_ranking,
    load_manual_vs_heuristic_comparison_frame,
    render_manual_vs_heuristic_family_ranking_markdown,
)


def _default_input_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default=str(_default_input_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    input_path = Path(args.input_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    comparison = load_manual_vs_heuristic_comparison_frame(input_path)
    ranking, summary = build_manual_vs_heuristic_family_ranking(comparison)

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    ranking.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": ranking.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_vs_heuristic_family_ranking_markdown(summary, ranking),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "input_path": str(input_path),
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
