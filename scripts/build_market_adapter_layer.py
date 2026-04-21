"""Build latest market adapter layer artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.market_adapter_layer import (  # noqa: E402
    build_market_adapter_layer,
    render_market_adapter_layer_markdown,
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


def _default_entry_audit_path() -> Path:
    return _default_shadow_auto_dir() / "market_family_entry_audit_latest.json"


def _default_exit_audit_path() -> Path:
    return _default_shadow_auto_dir() / "market_family_exit_audit_latest.json"


def _default_surface_objective_path() -> Path:
    return _default_shadow_auto_dir() / "surface_objective_spec_latest.json"


def _default_failure_label_path() -> Path:
    return _default_shadow_auto_dir() / "failure_label_harvest_latest.json"


def _default_distribution_gate_path() -> Path:
    return _default_shadow_auto_dir() / "distribution_promotion_gate_baseline_latest.json"


def _default_csv_output_path() -> Path:
    return _default_shadow_auto_dir() / "market_adapter_layer_latest.csv"


def _default_json_output_path() -> Path:
    return _default_shadow_auto_dir() / "market_adapter_layer_latest.json"


def _default_md_output_path() -> Path:
    return _default_shadow_auto_dir() / "market_adapter_layer_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-audit-path", default=str(_default_entry_audit_path()))
    parser.add_argument("--exit-audit-path", default=str(_default_exit_audit_path()))
    parser.add_argument("--surface-objective-path", default=str(_default_surface_objective_path()))
    parser.add_argument("--failure-label-path", default=str(_default_failure_label_path()))
    parser.add_argument("--distribution-gate-path", default=str(_default_distribution_gate_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_market_adapter_layer(
        _load_json(args.entry_audit_path),
        _load_json(args.exit_audit_path),
        _load_json(args.surface_objective_path),
        _load_json(args.failure_label_path),
        _load_json(args.distribution_gate_path),
    )
    markdown = render_market_adapter_layer_markdown(summary, frame)

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
                "md_output_path": str(md_output_path),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
