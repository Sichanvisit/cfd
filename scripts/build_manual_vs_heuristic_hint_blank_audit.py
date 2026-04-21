"""Build an audit for blank heuristic hints in time-matched manual-vs-heuristic cases."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_hint_blank_audit import (  # noqa: E402
    build_manual_vs_heuristic_hint_blank_audit,
    load_manual_vs_heuristic_comparison,
    render_manual_vs_heuristic_hint_blank_audit_json,
    render_manual_vs_heuristic_hint_blank_audit_markdown,
)


def _default_comparison_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_comparison_latest.csv"


def _default_trades_dir() -> Path:
    return ROOT / "data" / "trades"


def _default_matched_csv_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_matched_cases_latest.csv"


def _default_json_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_hint_blank_audit_latest.json"


def _default_md_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_hint_blank_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-path", default=str(_default_comparison_path()))
    parser.add_argument("--trades-dir", default=str(_default_trades_dir()))
    parser.add_argument("--matched-csv-output-path", default=str(_default_matched_csv_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_path()))
    args = parser.parse_args()

    comparison = load_manual_vs_heuristic_comparison(args.comparison_path)
    matched, summary = build_manual_vs_heuristic_hint_blank_audit(
        comparison,
        trades_dir=args.trades_dir,
    )

    matched_csv_output_path = Path(args.matched_csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    matched_csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    matched.to_csv(matched_csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(render_manual_vs_heuristic_hint_blank_audit_json(summary), encoding="utf-8")
    md_output_path.write_text(render_manual_vs_heuristic_hint_blank_audit_markdown(summary), encoding="utf-8")
    print(render_manual_vs_heuristic_hint_blank_audit_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
