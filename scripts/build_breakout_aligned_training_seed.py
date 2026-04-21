"""Build canonical breakout training seed rows from replay-aligned cases."""

from __future__ import annotations

import argparse
import json

from backend.services.breakout_aligned_training_seed import write_breakout_aligned_training_seed_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default=None)
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--markdown-output", default=None)
    args = parser.parse_args()

    payload = write_breakout_aligned_training_seed_report(
        alignment_csv_path=args.alignment,
        csv_output_path=args.csv_output,
        json_output_path=args.json_output,
        markdown_output_path=args.markdown_output,
    )
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
