"""Build latest market-family entry/exit audit snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.market_family_audit_snapshot import (  # noqa: E402
    build_market_family_entry_audit,
    build_market_family_exit_audit,
    render_market_family_entry_audit_markdown,
    render_market_family_exit_audit_markdown,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_trade_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_entry_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_entry_audit_latest.csv"


def _default_entry_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_entry_audit_latest.json"


def _default_entry_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_entry_audit_latest.md"


def _default_exit_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_exit_audit_latest.csv"


def _default_exit_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_exit_audit_latest.json"


def _default_exit_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_exit_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--trade-closed-history-path", default=str(_default_trade_closed_history_path()))
    parser.add_argument("--entry-recent-limit", type=int, default=240)
    parser.add_argument("--exit-recent-limit", type=int, default=200)
    parser.add_argument("--entry-csv-output-path", default=str(_default_entry_csv_output_path()))
    parser.add_argument("--entry-json-output-path", default=str(_default_entry_json_output_path()))
    parser.add_argument("--entry-md-output-path", default=str(_default_entry_md_output_path()))
    parser.add_argument("--exit-csv-output-path", default=str(_default_exit_csv_output_path()))
    parser.add_argument("--exit-json-output-path", default=str(_default_exit_json_output_path()))
    parser.add_argument("--exit-md-output-path", default=str(_default_exit_md_output_path()))
    args = parser.parse_args()

    runtime_status = _load_json(args.runtime_status_path)
    entry_decisions = _load_csv(args.entry_decisions_path)
    closed_trade_history = _load_csv(args.trade_closed_history_path)

    entry_frame, entry_summary = build_market_family_entry_audit(
        runtime_status,
        entry_decisions,
        recent_limit=int(args.entry_recent_limit),
    )
    exit_frame, exit_summary = build_market_family_exit_audit(
        runtime_status,
        closed_trade_history,
        recent_limit=int(args.exit_recent_limit),
    )

    entry_markdown = render_market_family_entry_audit_markdown(entry_summary, entry_frame)
    exit_markdown = render_market_family_exit_audit_markdown(exit_summary, exit_frame)

    entry_csv_output_path = Path(args.entry_csv_output_path)
    entry_json_output_path = Path(args.entry_json_output_path)
    entry_md_output_path = Path(args.entry_md_output_path)
    exit_csv_output_path = Path(args.exit_csv_output_path)
    exit_json_output_path = Path(args.exit_json_output_path)
    exit_md_output_path = Path(args.exit_md_output_path)
    entry_csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    entry_frame.to_csv(entry_csv_output_path, index=False, encoding="utf-8-sig")
    exit_frame.to_csv(exit_csv_output_path, index=False, encoding="utf-8-sig")
    entry_json_output_path.write_text(
        json.dumps({"summary": entry_summary, "rows": entry_frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    exit_json_output_path.write_text(
        json.dumps({"summary": exit_summary, "rows": exit_frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    entry_md_output_path.write_text(entry_markdown, encoding="utf-8")
    exit_md_output_path.write_text(exit_markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "entry_csv_output_path": str(entry_csv_output_path),
                "exit_csv_output_path": str(exit_csv_output_path),
                "entry_summary": entry_summary,
                "exit_summary": exit_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
