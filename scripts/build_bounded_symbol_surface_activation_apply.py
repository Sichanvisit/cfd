"""Apply bounded activation decisions after symbol-surface manual signoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.bounded_symbol_surface_activation_apply import (  # noqa: E402
    build_bounded_symbol_surface_activation_apply,
    render_bounded_symbol_surface_activation_apply_markdown,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activation-contract-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.json"))
    parser.add_argument("--manual-signoff-apply-path", default=str(_default_shadow_auto_dir() / "symbol_surface_manual_signoff_apply_latest.json"))
    parser.add_argument("--regression-watch-path", default=str(_default_shadow_auto_dir() / "entry_performance_regression_watch_latest.json"))
    parser.add_argument("--runtime-status-path", default=str(ROOT / "data" / "runtime_status.json"))
    parser.add_argument("--csv-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.csv"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.json"))
    parser.add_argument("--md-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.md"))
    parser.add_argument("--resolved-contract-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_applied.csv"))
    args = parser.parse_args()

    frame, resolved_contract, summary = build_bounded_symbol_surface_activation_apply(
        bounded_symbol_surface_activation_contract_payload=_load_json(args.activation_contract_path),
        symbol_surface_manual_signoff_apply_payload=_load_json(args.manual_signoff_apply_path),
        entry_performance_regression_watch_payload=_load_json(args.regression_watch_path),
        runtime_status=_load_json(args.runtime_status_path),
    )
    markdown = render_bounded_symbol_surface_activation_apply_markdown(summary, frame)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    resolved_contract_output_path = Path(args.resolved_contract_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    resolved_contract.to_csv(resolved_contract_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": frame.to_dict(orient="records"),
                "resolved_contract_path": str(resolved_contract_output_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")

    print(json.dumps({"csv_output_path": str(csv_output_path), "json_output_path": str(json_output_path), "md_output_path": str(md_output_path), "resolved_contract_output_path": str(resolved_contract_output_path), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
