"""Build SA4c shadow threshold sweep outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_edge_metrics import (  # noqa: E402
    load_demo_frame,
    load_feature_rows_frame,
    load_manual_truth_frame,
)
from backend.services.shadow_auto_threshold_sweep import (  # noqa: E402
    build_shadow_auto_threshold_sweep,
    render_shadow_auto_threshold_sweep_markdown,
)


def _default_demo_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_runtime_activation_demo_latest.csv"


def _default_feature_rows_path() -> Path:
    return ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy" / "bridge_proxy_feature_rows.parquet"


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_threshold_sweep_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_threshold_sweep_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_threshold_sweep_latest.md"


def _parse_float_list(raw: str | None) -> Sequence[float] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    values: list[float] = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        values.append(float(token))
    return tuple(values) if values else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-path", default=str(_default_demo_path()))
    parser.add_argument("--feature-rows-path", default=str(_default_feature_rows_path()))
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--threshold-values", default="")
    parser.add_argument("--exit-threshold-values", default="")
    args = parser.parse_args()

    demo = load_demo_frame(args.demo_path)
    feature_rows = load_feature_rows_frame(args.feature_rows_path)
    manual_truth = load_manual_truth_frame(args.manual_path)
    frame, summary = build_shadow_auto_threshold_sweep(
        demo,
        feature_rows=feature_rows,
        manual_truth=manual_truth,
        threshold_values=_parse_float_list(args.threshold_values),
        exit_threshold_values=_parse_float_list(args.exit_threshold_values),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output_path.write_text(render_shadow_auto_threshold_sweep_markdown(summary, frame), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
