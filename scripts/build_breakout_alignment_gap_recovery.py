"""Build breakout alignment-gap recovery queue and optional backfill scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.breakout_alignment_gap_recovery import write_breakout_alignment_gap_recovery_report
from backend.services.breakout_backfill_runner_scaffold import write_breakout_backfill_runner_scaffold


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default=None)
    parser.add_argument("--queue-csv-output", default=None)
    parser.add_argument("--queue-json-output", default=None)
    parser.add_argument("--queue-markdown-output", default=None)
    parser.add_argument("--build-scaffold", action="store_true", default=False)
    parser.add_argument("--scaffold-analysis-root", default=None)
    parser.add_argument("--scaffold-bundle-root", default=None)
    parser.add_argument("--manual-path", default=None)
    parser.add_argument("--supplemental-manual-path", default=None)
    parser.add_argument("--trades-root", default=None)
    parser.add_argument("--closed-trades-path", default=None)
    args = parser.parse_args()

    payload = write_breakout_alignment_gap_recovery_report(
        alignment_csv_path=args.alignment,
        csv_output_path=args.queue_csv_output,
        json_output_path=args.queue_json_output,
        markdown_output_path=args.queue_markdown_output,
    )

    if args.build_scaffold:
        queue_csv_path = Path(payload["csv_output_path"])
        analysis_root = Path(args.scaffold_analysis_root) if args.scaffold_analysis_root else queue_csv_path.parent
        bundle_root = Path(args.scaffold_bundle_root) if args.scaffold_bundle_root else queue_csv_path.parents[2] / "backfill" / "breakout_event_alignment_gaps"
        scaffold_payload = write_breakout_backfill_runner_scaffold(
            queue_path=queue_csv_path,
            secondary_queue_path=analysis_root / "_empty_secondary_queue.csv",
            manual_path=args.manual_path or Path("data/manual_annotations/manual_wait_teacher_annotations.csv"),
            supplemental_manual_path=args.supplemental_manual_path or Path("data/manual_annotations/breakout_manual_overlap_seed_review_entries.csv"),
            trades_root=args.trades_root or Path("data/trades"),
            closed_trades_path=args.closed_trades_path or Path("data/trades/trade_closed_history.csv"),
            bundle_root=bundle_root,
            csv_output_path=analysis_root / "breakout_alignment_gap_backfill_runner_scaffold_latest.csv",
            json_output_path=analysis_root / "breakout_alignment_gap_backfill_runner_scaffold_latest.json",
            md_output_path=analysis_root / "breakout_alignment_gap_backfill_runner_scaffold_latest.md",
        )
        payload["scaffold_summary"] = scaffold_payload.get("summary", {})
        payload["scaffold_csv_path"] = str(analysis_root / "breakout_alignment_gap_backfill_runner_scaffold_latest.csv")

    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))
    if "scaffold_summary" in payload:
        print(json.dumps(payload.get("scaffold_summary", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
