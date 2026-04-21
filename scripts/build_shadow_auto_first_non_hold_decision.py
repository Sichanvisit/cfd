"""Build SA6a first non-HOLD decision outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_first_non_hold_decision import (  # noqa: E402
    build_shadow_auto_first_non_hold_decision,
    render_shadow_auto_first_non_hold_markdown,
)


def _default_run_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_divergence_run_latest.json"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_non_hold_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_non_hold_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_first_non_hold_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json-path", default=str(_default_run_json_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    run_json_path = Path(args.run_json_path)
    payload = {}
    if run_json_path.exists():
        try:
            payload = json.loads(run_json_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    summary_in = payload.get("summary", {}) if isinstance(payload, dict) else {}
    frame, summary = build_shadow_auto_first_non_hold_decision(summary_in)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output_path.write_text(render_shadow_auto_first_non_hold_markdown(summary, frame), encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
