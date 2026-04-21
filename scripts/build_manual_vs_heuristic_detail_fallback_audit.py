"""Build a recoverability audit for legacy detail JSONL fallback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_detail_fallback_audit import (  # noqa: E402
    build_manual_vs_heuristic_detail_fallback_audit,
    load_matched_cases,
    render_manual_vs_heuristic_detail_fallback_audit_markdown,
)


def _default_matched_cases_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_matched_cases_latest.csv"


def _default_trades_dir() -> Path:
    return ROOT / "data" / "trades"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_detail_fallback_audit_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_detail_fallback_audit_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_detail_fallback_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matched-cases-path", default=str(_default_matched_cases_path()))
    parser.add_argument("--trades-dir", default=str(_default_trades_dir()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--max-gap-minutes", type=int, default=180)
    args = parser.parse_args()

    matched_cases = load_matched_cases(args.matched_cases_path)
    frame, summary = build_manual_vs_heuristic_detail_fallback_audit(
        matched_cases,
        trades_dir=args.trades_dir,
        max_gap_minutes=int(args.max_gap_minutes),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output_path.write_text(render_manual_vs_heuristic_detail_fallback_audit_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
