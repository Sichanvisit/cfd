from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from backend.trading.engine.offline.replay_dataset_builder import write_replay_dataset_batch  # noqa: E402
from fetch_mt5_future_bars import fetch_mt5_future_bars  # noqa: E402
from ml.semantic_v1.shadow_compare import DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE  # noqa: E402


DEFAULT_COMPARE_ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis" / "semantic_v1"
COMPARE_SOURCE_MANIFEST_VERSION = "shadow_compare_production_compare_source_v1"


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _cleanup_compare_output_dir(path: Path) -> list[str]:
    removed: list[str] = []
    if not path.exists():
        return removed
    for item in sorted(path.glob("*.jsonl")):
        if not item.is_file():
            continue
        item.unlink()
        removed.append(item.name)
    return removed


def _write_compare_source_manifest(
    *,
    summary: dict[str, object],
    analysis_dir: Path,
    output_dir: Path,
    removed_files: list[str],
) -> dict[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {
        "manifest_type": COMPARE_SOURCE_MANIFEST_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_role": "production_compare_source",
        "replay_source_dir": str(output_dir),
        "dataset_path": str(summary.get("dataset_path", "") or ""),
        "rows_written": int(summary.get("rows_written", 0) or 0),
        "entry_decision_path": str(summary.get("entry_decision_path", "") or ""),
        "closed_trade_path": str(summary.get("closed_trade_path", "") or ""),
        "future_bar_path": str(summary.get("future_bar_path", "") or ""),
        "future_bar_resolution": str(summary.get("future_bar_resolution", "") or ""),
        "replay_build_manifest_path": str(summary.get("replay_build_manifest_path", "") or ""),
        "label_quality_manifest_path": str(summary.get("label_quality_manifest_path", "") or ""),
        "key_integrity_manifest_path": str(summary.get("key_integrity_manifest_path", "") or ""),
        "validation_report_path": str(summary.get("validation_report_path", "") or ""),
        "removed_previous_files": list(removed_files),
    }
    analysis_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = analysis_dir / f"shadow_compare_production_source_manifest_{timestamp}.json"
    latest_path = analysis_dir / "shadow_compare_production_source_manifest_latest.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    manifest_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    return {
        "manifest_path": str(manifest_path),
        "latest_manifest_path": str(latest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the dedicated production replay source used by semantic shadow compare."
    )
    parser.add_argument(
        "--entry-decisions",
        default="data/trades/entry_decisions.csv",
        help="Path to entry_decisions.csv",
    )
    parser.add_argument(
        "--closed-trades",
        default="data/trades/trade_closed_history.csv",
        help="Path to trade_closed_history.csv",
    )
    parser.add_argument(
        "--future-bars",
        default="",
        help="Optional OHLC future bar CSV path with symbol,time,open,high,low,close columns.",
    )
    parser.add_argument(
        "--fetch-mt5-future-bars",
        action="store_true",
        help="Fetch future OHLC bars from MT5 first and feed the generated CSV into replay building.",
    )
    parser.add_argument(
        "--future-bars-output",
        default="",
        help="Output CSV path for MT5-fetched future bars.",
    )
    parser.add_argument(
        "--future-bars-timeframe",
        default="M15",
        help="MT5 timeframe used when --fetch-mt5-future-bars is enabled.",
    )
    parser.add_argument(
        "--future-bars-lookback-bars",
        type=int,
        default=1,
        help="Bars to fetch before the earliest anchor when MT5 backfill is enabled.",
    )
    parser.add_argument(
        "--future-bars-lookahead-bars",
        type=int,
        default=8,
        help="Bars to fetch after the latest anchor when MT5 backfill is enabled.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE.relative_to(PROJECT_ROOT)),
        help="Dedicated production compare replay directory.",
    )
    parser.add_argument(
        "--analysis-dir",
        default=str(DEFAULT_COMPARE_ANALYSIS_DIR.relative_to(PROJECT_ROOT)),
        help="Directory for compare-source manifests and replay manifests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of decision rows to process.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Optional symbol filter. Repeat for multiple symbols.",
    )
    parser.add_argument(
        "--entered-only",
        action="store_true",
        help="Only include decision rows where outcome == entered.",
    )
    parser.add_argument(
        "--keep-history",
        action="store_true",
        help="Keep existing replay JSONL files in the dedicated compare directory.",
    )
    args = parser.parse_args()

    output_dir = _resolve_path(args.output_dir, DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE)
    analysis_dir = _resolve_path(args.analysis_dir, DEFAULT_COMPARE_ANALYSIS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    removed_files = [] if bool(args.keep_history) else _cleanup_compare_output_dir(output_dir)

    future_bar_path = (args.future_bars or None)
    future_bar_fetch_summary = None
    if bool(args.fetch_mt5_future_bars):
        future_bar_fetch_summary = fetch_mt5_future_bars(
            entry_decisions=args.entry_decisions,
            output_path=(args.future_bars_output or future_bar_path),
            timeframe=str(args.future_bars_timeframe or "M15"),
            lookback_bars=int(args.future_bars_lookback_bars),
            lookahead_bars=int(args.future_bars_lookahead_bars),
            symbols=list(args.symbol or []),
        )
        future_bar_path = str(future_bar_fetch_summary.get("output_path", "") or future_bar_path or "")

    summary = write_replay_dataset_batch(
        entry_decision_path=args.entry_decisions,
        closed_trade_path=args.closed_trades,
        future_bar_path=future_bar_path,
        output_dir=output_dir,
        analysis_dir=analysis_dir,
        limit=args.limit,
        symbols=args.symbol,
        entered_only=args.entered_only,
        emit_validation_report=True,
    )
    if future_bar_fetch_summary is not None:
        summary["future_bar_fetch_summary"] = future_bar_fetch_summary

    manifest_paths = _write_compare_source_manifest(
        summary=summary,
        analysis_dir=analysis_dir,
        output_dir=output_dir,
        removed_files=removed_files,
    )
    summary["compare_source_dir"] = str(output_dir)
    summary["removed_previous_files"] = removed_files
    summary.update(manifest_paths)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
