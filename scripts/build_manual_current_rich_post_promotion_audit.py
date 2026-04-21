"""
Build the current-rich post-promotion audit output.

Usage:
  python scripts/build_manual_current_rich_post_promotion_audit.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_post_promotion_audit import (  # noqa: E402
    build_manual_current_rich_post_promotion_audit,
    load_frame,
    render_manual_current_rich_post_promotion_audit_markdown,
)


def _default_trace_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_entries.csv"


def _default_canonical_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_comparison_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_audit_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_post_promotion_audit_entries.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_post_promotion_audit_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_post_promotion_audit_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_post_promotion_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-entries-path", default=str(_default_trace_entries_path()))
    parser.add_argument("--canonical-path", default=str(_default_canonical_path()))
    parser.add_argument("--comparison-path", default=str(_default_comparison_path()))
    parser.add_argument("--audit-entries-path", default=str(_default_audit_entries_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    trace_entries_path = Path(args.trace_entries_path)
    canonical_path = Path(args.canonical_path)
    comparison_path = Path(args.comparison_path)
    audit_entries_path = Path(args.audit_entries_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    trace_entries = load_frame(trace_entries_path)
    canonical = load_frame(canonical_path)
    comparison = load_frame(comparison_path)
    audit_entries = load_frame(audit_entries_path)

    audit, summary = build_manual_current_rich_post_promotion_audit(
        trace_entries,
        canonical,
        comparison,
        audit_entries=audit_entries,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    audit.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": audit.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_current_rich_post_promotion_audit_markdown(summary, audit),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "trace_entries_path": str(trace_entries_path),
                "canonical_path": str(canonical_path),
                "comparison_path": str(comparison_path),
                "audit_entries_path": str(audit_entries_path),
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
