"""Build latest failure-label harvest artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.failure_label_harvest import (  # noqa: E402
    build_failure_label_harvest,
    render_failure_label_harvest_markdown,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _load_json(path: str | Path) -> dict[str, object]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_check_color_label_formalization_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "check_color_label_formalization_latest.csv"


def _default_surface_time_axis_contract_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_time_axis_contract_latest.csv"


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_market_family_entry_audit_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_entry_audit_latest.json"


def _default_market_family_exit_audit_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_exit_audit_latest.json"


def _default_exit_surface_observation_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "exit_surface_observation_latest.json"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "failure_label_harvest_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "failure_label_harvest_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "failure_label_harvest_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-color-label-formalization-path", default=str(_default_check_color_label_formalization_path()))
    parser.add_argument("--surface-time-axis-contract-path", default=str(_default_surface_time_axis_contract_path()))
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--market-family-entry-audit-path", default=str(_default_market_family_entry_audit_path()))
    parser.add_argument("--market-family-exit-audit-path", default=str(_default_market_family_exit_audit_path()))
    parser.add_argument("--exit-surface-observation-path", default=str(_default_exit_surface_observation_path()))
    parser.add_argument("--recent-entry-limit", type=int, default=240)
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_failure_label_harvest(
        _load_csv(args.check_color_label_formalization_path),
        _load_csv(args.surface_time_axis_contract_path),
        _load_csv(args.entry_decisions_path),
        _load_json(args.market_family_entry_audit_path),
        _load_json(args.market_family_exit_audit_path),
        _load_json(args.exit_surface_observation_path),
        recent_entry_limit=max(1, int(args.recent_entry_limit)),
    )
    markdown = render_failure_label_harvest_markdown(summary, frame)

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
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
