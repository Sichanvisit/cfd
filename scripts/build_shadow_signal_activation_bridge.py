"""
Build the shadow signal activation/availability bridge.

Usage:
  python scripts/build_shadow_signal_activation_bridge.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_signal_activation_bridge import (  # noqa: E402
    build_shadow_signal_activation_bridge,
    load_shadow_signal_bridge_frame,
    render_shadow_signal_activation_bridge_markdown,
)


def _default_compare_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_vs_baseline_latest.csv"


def _default_candidates_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_candidates_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_signal_activation_bridge_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_signal_activation_bridge_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_signal_activation_bridge_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare-path", default=str(_default_compare_path()))
    parser.add_argument("--candidates-path", default=str(_default_candidates_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    compare_path = Path(args.compare_path)
    candidates_path = Path(args.candidates_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    compare_df = load_shadow_signal_bridge_frame(compare_path)
    candidates_df = load_shadow_signal_bridge_frame(candidates_path)
    bridge, summary = build_shadow_signal_activation_bridge(compare_df, shadow_candidates=candidates_df)

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    bridge.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": bridge.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_shadow_signal_activation_bridge_markdown(summary, bridge),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "compare_path": str(compare_path),
                "candidates_path": str(candidates_path),
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
