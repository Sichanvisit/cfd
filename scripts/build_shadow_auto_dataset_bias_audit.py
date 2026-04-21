"""Build SA4e shadow dataset bias audit outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_dataset_bias_audit import (  # noqa: E402
    build_shadow_auto_dataset_bias_audit,
    render_shadow_auto_dataset_bias_audit_markdown,
)
from backend.services.shadow_auto_edge_metrics import load_feature_rows_frame, load_manual_truth_frame  # noqa: E402


def _default_feature_rows_path() -> Path:
    return ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy" / "bridge_proxy_feature_rows.parquet"


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_dataset_bias_audit_latest.csv"


def _default_rebalanced_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_rebalanced_training_corpus_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_dataset_bias_audit_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_dataset_bias_audit_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-rows-path", default=str(_default_feature_rows_path()))
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--rebalanced-output-path", default=str(_default_rebalanced_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    feature_rows = load_feature_rows_frame(args.feature_rows_path)
    manual_truth = load_manual_truth_frame(args.manual_path)
    audit, rebalanced, summary = build_shadow_auto_dataset_bias_audit(
        feature_rows,
        manual_truth=manual_truth,
    )

    csv_output_path = Path(args.csv_output_path)
    rebalanced_output_path = Path(args.rebalanced_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    rebalanced.to_csv(rebalanced_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {"summary": summary, "audit_rows": audit.to_dict(orient="records"), "rebalanced_rows": rebalanced.to_dict(orient="records")},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(render_shadow_auto_dataset_bias_audit_markdown(summary, audit, rebalanced), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), "rebalanced_output_path": str(rebalanced_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
