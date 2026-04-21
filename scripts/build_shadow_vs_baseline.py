"""
Build the shadow-vs-baseline storage layer from current decision logs.

Usage:
  python scripts/build_shadow_vs_baseline.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_baseline_compare import (  # noqa: E402
    build_shadow_auto_baseline_compare,
    load_entry_decision_history,
    load_shadow_auto_compare_frame,
    render_shadow_auto_baseline_compare_markdown,
)


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_entry_history_dir() -> Path:
    return ROOT / "data" / "trades"


def _default_comparison_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_candidates_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_candidates_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_vs_baseline_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_vs_baseline_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_vs_baseline_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--entry-history-dir", default=str(_default_entry_history_dir()))
    parser.add_argument("--include-legacy", action="store_true", default=True)
    parser.add_argument("--no-include-legacy", dest="include_legacy", action="store_false")
    parser.add_argument("--comparison-path", default=str(_default_comparison_path()))
    parser.add_argument("--candidates-path", default=str(_default_candidates_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--manual-threshold-minutes", type=float, default=120.0)
    args = parser.parse_args()

    entry_decisions_path = Path(args.entry_decisions_path)
    entry_history_dir = Path(args.entry_history_dir)
    comparison_path = Path(args.comparison_path)
    candidates_path = Path(args.candidates_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    if entry_history_dir.exists():
        entry_decisions = load_entry_decision_history(entry_history_dir, include_legacy=bool(args.include_legacy))
    else:
        entry_decisions = load_shadow_auto_compare_frame(entry_decisions_path)
    comparison = load_shadow_auto_compare_frame(comparison_path)
    candidates = load_shadow_auto_compare_frame(candidates_path)
    compare_df, summary = build_shadow_auto_baseline_compare(
        entry_decisions,
        comparison=comparison,
        shadow_candidates=candidates,
        max_rows=int(args.max_rows),
        manual_match_threshold_minutes=max(1.0, float(args.manual_threshold_minutes)),
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    compare_df.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": compare_df.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_shadow_auto_baseline_compare_markdown(summary, compare_df),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "entry_decisions_path": str(entry_decisions_path),
                "entry_history_dir": str(entry_history_dir),
                "include_legacy": bool(args.include_legacy),
                "comparison_path": str(comparison_path),
                "candidates_path": str(candidates_path),
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
