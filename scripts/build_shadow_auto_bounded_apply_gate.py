"""Build the bounded live-apply gate over preview shadow candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_bounded_apply_gate import (  # noqa: E402
    build_shadow_auto_bounded_apply_gate,
    render_shadow_auto_bounded_apply_gate_markdown,
)


def _default_non_hold_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_non_hold_latest.json"


def _default_manual_reference_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_manual_reference_audit_latest.json"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_bounded_apply_gate_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_bounded_apply_gate_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_bounded_apply_gate_latest.md"


def _rows_from_json(path: Path) -> pd.DataFrame:
    payload = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-non-hold-json-path", default=str(_default_non_hold_json_path()))
    parser.add_argument("--manual-reference-json-path", default=str(_default_manual_reference_json_path()))
    parser.add_argument("--required-manual-reference-row-count", type=int, default=5)
    parser.add_argument("--required-value-diff-proxy", type=float, default=0.01)
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_shadow_auto_bounded_apply_gate(
        _rows_from_json(Path(args.first_non_hold_json_path)),
        _rows_from_json(Path(args.manual_reference_json_path)),
        required_manual_reference_row_count=int(args.required_manual_reference_row_count),
        required_value_diff_proxy=float(args.required_value_diff_proxy),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(render_shadow_auto_bounded_apply_gate_markdown(summary, frame), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
