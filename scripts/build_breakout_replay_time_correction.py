"""Build breakout replay/manual time-correction draft for strict-alignment misses."""

from __future__ import annotations

import argparse
import json

from backend.services.breakout_replay_time_correction import write_breakout_replay_time_correction_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default=None)
    parser.add_argument("--scaffold", default=None)
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--markdown-output", default=None)
    parser.add_argument("--coarse-tolerance-seconds", type=int, default=1800)
    parser.add_argument("--review-tolerance-seconds", type=int, default=7200)
    args = parser.parse_args()

    payload = write_breakout_replay_time_correction_report(
        alignment_csv_path=args.alignment,
        scaffold_csv_path=args.scaffold,
        csv_output_path=args.csv_output,
        json_output_path=args.json_output,
        markdown_output_path=args.markdown_output,
        coarse_tolerance_seconds=args.coarse_tolerance_seconds,
        review_tolerance_seconds=args.review_tolerance_seconds,
    )
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
