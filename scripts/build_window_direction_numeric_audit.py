"""Build window-direction numeric audit outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.window_direction_numeric_audit import (  # noqa: E402
    generate_and_write_window_direction_numeric_audit,
)


def _default_detail_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.detail.jsonl"


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _load_json_payload(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"invalid JSON window spec: {exc}") from exc


def _coerce_window_specs(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("windows", "window_specs", "specs"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, dict)]
        return [dict(payload)]
    return []


def _load_window_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if args.window_specs_path:
        specs.extend(
            _coerce_window_specs(
                _load_json_payload(Path(args.window_specs_path).read_text(encoding="utf-8"))
            )
        )
    if args.window_specs_json:
        specs.extend(_coerce_window_specs(_load_json_payload(args.window_specs_json)))
    if args.symbol and args.start and args.end:
        specs.append(
            {
                "window_id": args.window_id or str(args.symbol).lower(),
                "symbol": args.symbol,
                "label": args.label,
                "expected_direction": args.expected_direction,
                "start": args.start,
                "end": args.end,
            }
        )
    return specs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detail-path", default=str(_default_detail_path()))
    parser.add_argument("--window-specs-path", default="")
    parser.add_argument("--window-specs-json", default="")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--window-id", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--expected-direction", default="UP", choices=["UP", "DOWN"])
    parser.add_argument("--shadow-auto-dir", default=str(_default_shadow_auto_dir()))
    parser.add_argument("--output-stem", default="window_direction_numeric_audit_latest")
    args = parser.parse_args(argv)

    result = generate_and_write_window_direction_numeric_audit(
        args.detail_path,
        _load_window_specs(args),
        shadow_auto_dir=args.shadow_auto_dir,
        output_stem=args.output_stem,
    )
    report = dict(result.get("report", {}) or {})
    summary = {
        "artifact_paths": result.get("artifact_paths", {}),
        "window_count": int(report.get("window_count", 0) or 0),
        "windows": [
            {
                "window_id": row.get("window_id", ""),
                "symbol": row.get("symbol", ""),
                "row_count": int(row.get("row_count", 0) or 0),
                "calibration_state": (
                    dict(row.get("candidate_threshold_hints_v1", {}) or {}).get("calibration_state", "")
                ),
            }
            for row in list(report.get("windows", []) or [])
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
