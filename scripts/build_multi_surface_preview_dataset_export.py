"""Build latest multi-surface preview dataset export artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.multi_surface_preview_dataset_export import (  # noqa: E402
    write_multi_surface_preview_dataset_export,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _default_check_color_path() -> Path:
    return _default_shadow_auto_dir() / "check_color_label_formalization_latest.json"


def _default_surface_time_axis_path() -> Path:
    return _default_shadow_auto_dir() / "surface_time_axis_contract_latest.json"


def _default_failure_label_path() -> Path:
    return _default_shadow_auto_dir() / "failure_label_harvest_latest.json"


def _default_market_adapter_path() -> Path:
    return _default_shadow_auto_dir() / "market_adapter_layer_latest.json"


def _default_csv_output_path() -> Path:
    return _default_shadow_auto_dir() / "multi_surface_preview_dataset_export_latest.csv"


def _default_json_output_path() -> Path:
    return _default_shadow_auto_dir() / "multi_surface_preview_dataset_export_latest.json"


def _default_md_output_path() -> Path:
    return _default_shadow_auto_dir() / "multi_surface_preview_dataset_export_latest.md"


def _default_dataset_dir() -> Path:
    return ROOT / "data" / "datasets" / "multi_surface_preview"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-color-path", default=str(_default_check_color_path()))
    parser.add_argument("--surface-time-axis-path", default=str(_default_surface_time_axis_path()))
    parser.add_argument("--failure-label-path", default=str(_default_failure_label_path()))
    parser.add_argument("--market-adapter-path", default=str(_default_market_adapter_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--dataset-dir", default=str(_default_dataset_dir()))
    args = parser.parse_args()

    result = write_multi_surface_preview_dataset_export(
        check_color_payload=_load_json(args.check_color_path),
        surface_time_axis_payload=_load_json(args.surface_time_axis_path),
        failure_label_payload=_load_json(args.failure_label_path),
        market_adapter_layer_payload=_load_json(args.market_adapter_path),
        analysis_csv_path=args.csv_output_path,
        analysis_json_path=args.json_output_path,
        analysis_md_path=args.md_output_path,
        dataset_dir=args.dataset_dir,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
