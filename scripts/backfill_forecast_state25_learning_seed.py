"""
Apply forecast-state25 enrichment to trade_closed_history.csv.

Usage:
  python scripts/backfill_forecast_state25_learning_seed.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.forecast_state25_seed_enrichment import (  # noqa: E402
    apply_forecast_state25_seed_enrichment,
    build_forecast_state25_seed_enrichment_plan,
    load_forecast_state25_outcome_bridge_report,
)
from backend.services.teacher_pattern_backfill import (  # noqa: E402
    read_closed_history_for_backfill,
    write_closed_history_backfill,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_replay_report_path() -> Path:
    return ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closed-history-path", default=str(_default_closed_history_path()))
    parser.add_argument("--replay-report-path", default=str(_default_replay_report_path()))
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    closed_history_path = Path(args.closed_history_path)
    replay_report_path = Path(args.replay_report_path)

    frame = read_closed_history_for_backfill(closed_history_path)
    replay_report = load_forecast_state25_outcome_bridge_report(replay_report_path)

    if args.dry_run:
        report = build_forecast_state25_seed_enrichment_plan(
            frame,
            replay_report=replay_report,
            overwrite_existing=bool(args.overwrite_existing),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    updated_frame, report = apply_forecast_state25_seed_enrichment(
        frame,
        replay_report=replay_report,
        overwrite_existing=bool(args.overwrite_existing),
    )
    backup_path = write_closed_history_backfill(
        closed_history_path,
        updated_frame,
        backup=True,
        backup_suffix="forecast_state25_enrichment",
    )
    report["closed_history_path"] = str(closed_history_path)
    report["replay_report_path"] = str(replay_report_path)
    report["backup_path"] = str(backup_path) if backup_path is not None else ""
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
