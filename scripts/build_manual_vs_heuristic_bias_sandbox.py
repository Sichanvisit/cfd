"""
Build the bias-correction sandbox loop scaffold from ranking and bias targets.

Usage:
  python scripts/build_manual_vs_heuristic_bias_sandbox.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_bias_sandbox import (  # noqa: E402
    build_manual_vs_heuristic_bias_sandbox,
    load_frame,
    render_manual_vs_heuristic_bias_sandbox_markdown,
)


def _default_ranking_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_family_ranking_latest.csv"


def _default_bias_targets_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_bias_targets_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_bias_sandbox_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_bias_sandbox_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_bias_sandbox_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking-path", default=str(_default_ranking_path()))
    parser.add_argument("--bias-targets-path", default=str(_default_bias_targets_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    ranking_path = Path(args.ranking_path)
    bias_targets_path = Path(args.bias_targets_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    ranking = load_frame(ranking_path)
    bias_targets = load_frame(bias_targets_path)
    sandbox, summary = build_manual_vs_heuristic_bias_sandbox(ranking, bias_targets)

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    sandbox.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": sandbox.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_vs_heuristic_bias_sandbox_markdown(summary, sandbox),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ranking_path": str(ranking_path),
                "bias_targets_path": str(bias_targets_path),
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
