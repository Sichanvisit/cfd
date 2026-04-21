"""
Build the unified manual calibration approval log.

Usage:
  python scripts/build_manual_calibration_approval_log.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_calibration_approval_log import (  # noqa: E402
    build_manual_calibration_approval_log,
    load_frame,
    render_manual_calibration_approval_log_markdown,
)


def _default_trace_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_entries.csv"


def _default_correction_runs_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_correction_runs_latest.csv"


def _default_post_promotion_audit_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_post_promotion_audit_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_calibration_approval_log.csv"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_calibration_approval_log_latest.md"


def _default_shadow_bounded_candidate_approval_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_approval_latest.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-entries-path", default=str(_default_trace_entries_path()))
    parser.add_argument("--correction-runs-path", default=str(_default_correction_runs_path()))
    parser.add_argument("--post-promotion-audit-path", default=str(_default_post_promotion_audit_path()))
    parser.add_argument("--shadow-bounded-candidate-approval-path", default=str(_default_shadow_bounded_candidate_approval_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    trace_entries_path = Path(args.trace_entries_path)
    correction_runs_path = Path(args.correction_runs_path)
    post_promotion_audit_path = Path(args.post_promotion_audit_path)
    shadow_bounded_candidate_approval_path = Path(args.shadow_bounded_candidate_approval_path)
    csv_output_path = Path(args.csv_output_path)
    md_output_path = Path(args.md_output_path)

    trace_entries = load_frame(trace_entries_path)
    correction_runs = load_frame(correction_runs_path)
    post_promotion_audit = load_frame(post_promotion_audit_path)
    shadow_bounded_candidate_approval = load_frame(shadow_bounded_candidate_approval_path)

    approval_log, summary = build_manual_calibration_approval_log(
        trace_entries,
        correction_runs,
        post_promotion_audit,
        shadow_bounded_candidate_approval,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    approval_log.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    md_output_path.write_text(
        render_manual_calibration_approval_log_markdown(summary, approval_log),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "trace_entries_path": str(trace_entries_path),
                "correction_runs_path": str(correction_runs_path),
                "post_promotion_audit_path": str(post_promotion_audit_path),
                "shadow_bounded_candidate_approval_path": str(shadow_bounded_candidate_approval_path),
                "csv_output_path": str(csv_output_path),
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
