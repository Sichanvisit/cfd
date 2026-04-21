"""
Build the manual-vs-heuristic correction loop candidate and run outputs.

Usage:
  python scripts/run_manual_vs_heuristic_correction_loop.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_correction_runs import (  # noqa: E402
    build_manual_vs_heuristic_correction_candidates,
    build_manual_vs_heuristic_correction_runs,
    load_frame,
    render_manual_vs_heuristic_correction_loop_markdown,
)


def _default_ranking_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.csv"


def _default_patch_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_patch_draft_latest.csv"


def _default_comparison_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_candidates_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_candidates_latest.csv"


def _default_runs_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_runs_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_runs_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_runs_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking-path", default=str(_default_ranking_path()))
    parser.add_argument("--patch-draft-path", default=str(_default_patch_draft_path()))
    parser.add_argument("--comparison-path", default=str(_default_comparison_path()))
    parser.add_argument("--candidates-output-path", default=str(_default_candidates_output_path()))
    parser.add_argument("--runs-output-path", default=str(_default_runs_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    ranking_path = Path(args.ranking_path)
    patch_draft_path = Path(args.patch_draft_path)
    comparison_path = Path(args.comparison_path)
    candidates_output_path = Path(args.candidates_output_path)
    runs_output_path = Path(args.runs_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    ranking = load_frame(ranking_path)
    patch_draft = load_frame(patch_draft_path)
    comparison = load_frame(comparison_path)

    candidates, candidate_summary = build_manual_vs_heuristic_correction_candidates(ranking, patch_draft)
    runs, run_summary = build_manual_vs_heuristic_correction_runs(candidates, comparison)

    candidates_output_path.parent.mkdir(parents=True, exist_ok=True)
    runs_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    candidates.to_csv(candidates_output_path, index=False, encoding="utf-8-sig")
    runs.to_csv(runs_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {
                "candidate_summary": candidate_summary,
                "run_summary": run_summary,
                "candidates": candidates.to_dict(orient="records"),
                "runs": runs.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_vs_heuristic_correction_loop_markdown(
            candidate_summary,
            candidates,
            run_summary,
            runs,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ranking_path": str(ranking_path),
                "patch_draft_path": str(patch_draft_path),
                "comparison_path": str(comparison_path),
                "candidates_output_path": str(candidates_output_path),
                "runs_output_path": str(runs_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **candidate_summary,
                **{f"run_{key}": value for key, value in run_summary.items() if key != "correction_loop_version"},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
