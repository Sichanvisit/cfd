"""Build shadow manual-truth overlap collection queue from divergence rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_manual_overlap_queue import (  # noqa: E402
    build_shadow_auto_manual_overlap_queue,
    render_shadow_auto_manual_overlap_queue_markdown,
)


def _default_divergence_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_divergence_run_latest.json"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_manual_overlap_queue_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_manual_overlap_queue_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_manual_overlap_queue_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--divergence-json-path", default=str(_default_divergence_json_path()))
    parser.add_argument("--window-minutes", type=int, default=30)
    parser.add_argument("--limit-per-symbol", type=int, default=4)
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    payload = {}
    divergence_json_path = Path(args.divergence_json_path)
    if divergence_json_path.exists():
        try:
            payload = json.loads(divergence_json_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    divergence_rows = pd.DataFrame(rows)
    queue, summary = build_shadow_auto_manual_overlap_queue(
        divergence_rows,
        window_minutes=int(args.window_minutes),
        limit_per_symbol=int(args.limit_per_symbol),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": queue.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(render_shadow_auto_manual_overlap_queue_markdown(summary, queue), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
