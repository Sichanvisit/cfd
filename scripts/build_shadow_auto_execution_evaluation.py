"""Build execution-level evaluation for preview shadow runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_execution_evaluation import (  # noqa: E402
    build_shadow_auto_execution_evaluation,
    render_shadow_auto_execution_evaluation_markdown,
)


def _default_demo_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_runtime_activation_demo_latest.csv"


def _default_candidate_run_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_divergence_run_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_execution_evaluation_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_execution_evaluation_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_execution_evaluation_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-path", default=str(_default_demo_path()))
    parser.add_argument("--candidate-run-path", default=str(_default_candidate_run_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    demo_path = Path(args.demo_path)
    demo = pd.read_csv(demo_path, encoding="utf-8-sig", low_memory=False) if demo_path.exists() else pd.DataFrame()
    candidate_run_path = Path(args.candidate_run_path)
    candidate_rows = (
        pd.read_csv(candidate_run_path, encoding="utf-8-sig", low_memory=False)
        if candidate_run_path.exists()
        else pd.DataFrame()
    )
    evaluation, summary = build_shadow_auto_execution_evaluation(demo, candidate_rows=candidate_rows)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": evaluation.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_shadow_auto_execution_evaluation_markdown(summary, evaluation),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
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
