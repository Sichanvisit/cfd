"""
Build the manual-vs-heuristic comparison report from manual answer-key episodes.

Usage:
  python scripts/build_manual_vs_heuristic_comparison_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_comparison import (  # noqa: E402
    build_manual_vs_heuristic_comparison_report,
    load_global_detail_fallback_frame,
    load_entry_decision_heuristic_frame,
    load_manual_wait_teacher_annotations,
    render_manual_vs_heuristic_markdown,
)


def _default_annotations_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_heuristic_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.md"


def _default_global_detail_fallback_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_global_detail_fallback_audit_latest.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations-path", default=str(_default_annotations_path()))
    parser.add_argument("--heuristic-path", default=str(_default_heuristic_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--global-detail-fallback-path", default=str(_default_global_detail_fallback_path()))
    parser.add_argument("--max-gap-minutes", type=int, default=180)
    parser.add_argument("--review-owner", default="codex")
    args = parser.parse_args()

    annotations_path = Path(args.annotations_path)
    heuristic_path = Path(args.heuristic_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    global_detail_fallback_path = Path(args.global_detail_fallback_path)

    annotations = load_manual_wait_teacher_annotations(annotations_path)
    heuristic_frame = load_entry_decision_heuristic_frame(heuristic_path)
    global_detail_fallback_frame = load_global_detail_fallback_frame(global_detail_fallback_path)
    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic_frame,
        global_detail_fallback_frame=global_detail_fallback_frame,
        max_gap_minutes=int(args.max_gap_minutes),
        review_owner=str(args.review_owner),
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    report.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": report.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(render_manual_vs_heuristic_markdown(summary), encoding="utf-8")

    print(
        json.dumps(
            {
                "annotations_path": str(annotations_path),
                "heuristic_path": str(heuristic_path),
                "global_detail_fallback_path": str(global_detail_fallback_path),
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
