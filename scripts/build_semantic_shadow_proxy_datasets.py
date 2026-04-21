"""Materialize proxy semantic_v1 datasets from bridge corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.semantic_shadow_proxy_dataset_materializer import (  # noqa: E402
    DEFAULT_DATASET_DIR,
    build_semantic_shadow_proxy_datasets,
    render_semantic_shadow_proxy_dataset_markdown,
)
from ml.semantic_v1.feature_packs import SEMANTIC_INPUT_COLUMNS, TRACE_QUALITY_COLUMNS  # noqa: E402


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_proxy_datasets_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_proxy_datasets_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--corpus-path", default="")
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--rebalanced-corpus-path", default="")
    parser.set_defaults(use_rebalanced_targets=True)
    parser.add_argument("--use-rebalanced-targets", dest="use_rebalanced_targets", action="store_true")
    parser.add_argument("--disable-rebalanced-targets", dest="use_rebalanced_targets", action="store_false")
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    datasets, summary, base_frame = build_semantic_shadow_proxy_datasets(
        corpus_path=(Path(args.corpus_path) if args.corpus_path else None),
        adapter_path=(Path(args.adapter_path) if args.adapter_path else None),
        rebalanced_corpus_path=(Path(args.rebalanced_corpus_path) if args.rebalanced_corpus_path else None),
        use_rebalanced_targets=bool(args.use_rebalanced_targets),
    )
    dataset_dir.mkdir(parents=True, exist_ok=True)

    dataset_payload: dict[str, Any] = {}
    for dataset_key, frame in datasets.items():
        parquet_path = dataset_dir / f"{dataset_key}_dataset.parquet"
        frame.to_parquet(parquet_path, index=False)
        dataset_summary = {
            "dataset_key": dataset_key,
            "row_count": int(len(frame)),
            "class_balance": summary.get("dataset_class_balance", {}).get(dataset_key, {}),
            "source_generation": "bridge_proxy",
            "proxy_target_mapping_version": "semantic_shadow_proxy_targets_v2_rebalanced" if summary.get("use_rebalanced_targets") else "semantic_shadow_proxy_targets_v2",
            "feature_tier_policy": {"semantic_input_pack": "keep", "trace_quality_pack": "keep"},
            "feature_tier_summary": {
                "semantic_input_pack": {
                    "mode": "keep",
                    "candidate_count": len(SEMANTIC_INPUT_COLUMNS),
                    "retained_count": len([col for col in frame.columns if col in SEMANTIC_INPUT_COLUMNS]),
                    "dropped_count": max(0, len(SEMANTIC_INPUT_COLUMNS) - len([col for col in frame.columns if col in SEMANTIC_INPUT_COLUMNS])),
                    "observed_only_dropped_count": 0,
                },
                "trace_quality_pack": {
                    "mode": "keep",
                    "candidate_count": len(TRACE_QUALITY_COLUMNS),
                    "retained_count": len([col for col in frame.columns if col in TRACE_QUALITY_COLUMNS]),
                    "dropped_count": max(0, len(TRACE_QUALITY_COLUMNS) - len([col for col in frame.columns if col in TRACE_QUALITY_COLUMNS])),
                    "observed_only_dropped_count": 0,
                },
            },
            "dropped_feature_columns": [],
            "dropped_feature_reasons": {},
            "observed_only_dropped_feature_columns": [],
            "split_summary": getattr(frame, "attrs", {}).get("split_summary", {}),
        }
        parquet_path.with_suffix(parquet_path.suffix + ".summary.json").write_text(
            json.dumps(dataset_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        dataset_payload[dataset_key] = dataset_summary

    feature_rows_path = dataset_dir / "bridge_proxy_feature_rows.parquet"
    base_frame.to_parquet(feature_rows_path, index=False)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(
        json.dumps({"summary": summary, "datasets": dataset_payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_semantic_shadow_proxy_dataset_markdown(summary, datasets),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "dataset_dir": str(dataset_dir),
                "feature_rows_path": str(feature_rows_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
