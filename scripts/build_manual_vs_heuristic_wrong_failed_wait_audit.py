"""
Build a focused audit for wrong_failed_wait_interpretation cases.

Usage:
  python scripts/build_manual_vs_heuristic_wrong_failed_wait_audit.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_wrong_failed_wait_audit import (  # noqa: E402
    build_wrong_failed_wait_audit,
    load_frame,
    render_wrong_failed_wait_audit_markdown,
)


def _default_comparison_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_fallback_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_global_detail_fallback_audit_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_wrong_failed_wait_audit_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_wrong_failed_wait_audit_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_wrong_failed_wait_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-path", default=str(_default_comparison_path()))
    parser.add_argument("--fallback-path", default=str(_default_fallback_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    comparison = load_frame(Path(args.comparison_path))
    fallback = load_frame(Path(args.fallback_path))
    audit, summary = build_wrong_failed_wait_audit(comparison, fallback)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    audit.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": audit.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(render_wrong_failed_wait_audit_markdown(summary, audit), encoding="utf-8")

    print(
        json.dumps(
            {
                "comparison_path": str(Path(args.comparison_path)),
                "fallback_path": str(Path(args.fallback_path)),
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
