"""
Build the family-ranking retrospective surface.

Usage:
  python scripts/build_manual_vs_heuristic_ranking_retrospective.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_ranking_retrospective import (  # noqa: E402
    build_manual_vs_heuristic_ranking_retrospective,
    load_frame,
    render_manual_vs_heuristic_ranking_retrospective_markdown,
)


def _default_ranking_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.csv"


def _default_correction_runs_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_runs_latest.csv"


def _default_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_retrospective_entries.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_history_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_retrospective_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_retrospective_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking-path", default=str(_default_ranking_path()))
    parser.add_argument("--correction-runs-path", default=str(_default_correction_runs_path()))
    parser.add_argument("--entries-path", default=str(_default_entries_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    ranking_path = Path(args.ranking_path)
    correction_runs_path = Path(args.correction_runs_path)
    entries_path = Path(args.entries_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    ranking = load_frame(ranking_path)
    correction_runs = load_frame(correction_runs_path)
    entries = load_frame(entries_path)

    history, summary = build_manual_vs_heuristic_ranking_retrospective(
        ranking,
        correction_runs,
        retrospective_entries=entries,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    history.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": history.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_vs_heuristic_ranking_retrospective_markdown(summary, history),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ranking_path": str(ranking_path),
                "correction_runs_path": str(correction_runs_path),
                "entries_path": str(entries_path),
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
