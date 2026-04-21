"""Build latest wrong-side conflict replay harness artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.wrong_side_conflict_replay_harness import (  # noqa: E402
    build_wrong_side_conflict_replay_harness,
    render_wrong_side_conflict_replay_harness_markdown,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return (
        ROOT / "data" / "analysis" / "shadow_auto" / "wrong_side_conflict_replay_harness_latest.csv"
    )


def _default_json_output_path() -> Path:
    return (
        ROOT / "data" / "analysis" / "shadow_auto" / "wrong_side_conflict_replay_harness_latest.json"
    )


def _default_md_output_path() -> Path:
    return (
        ROOT / "data" / "analysis" / "shadow_auto" / "wrong_side_conflict_replay_harness_latest.md"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--recent-limit", type=int, default=1200)
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_wrong_side_conflict_replay_harness(
        _load_csv(args.entry_decisions_path),
        recent_limit=max(1, int(args.recent_limit)),
    )
    markdown = render_wrong_side_conflict_replay_harness_markdown(summary, frame)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
