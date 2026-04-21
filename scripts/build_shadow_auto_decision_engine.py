"""Build SA6 auto decision / bounded apply recommendation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_decision_engine import (  # noqa: E402
    build_shadow_auto_decision_engine,
    render_shadow_auto_decision_engine_markdown,
)


def _default_correction_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_correction_loop_latest.csv"


def _default_preview_bundle_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_preview_bundle_latest.json"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_auto_decision_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_auto_decision_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_auto_decision_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--correction-path", default=str(_default_correction_path()))
    parser.add_argument("--preview-bundle-path", default=str(_default_preview_bundle_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    correction_path = Path(args.correction_path)
    correction = pd.read_csv(correction_path, encoding="utf-8-sig", low_memory=False) if correction_path.exists() else pd.DataFrame()
    preview_payload = {}
    preview_path = Path(args.preview_bundle_path)
    if preview_path.exists():
        try:
            preview_payload = json.loads(preview_path.read_text(encoding="utf-8"))
        except Exception:
            preview_payload = {}
    preview_summary = preview_payload.get("summary", {}) if isinstance(preview_payload, dict) else {}
    frame, summary = build_shadow_auto_decision_engine(
        correction,
        preview_bundle_ready=bool(preview_summary.get("bundle_ready", False)),
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
    md_output_path.write_text(
        render_shadow_auto_decision_engine_markdown(summary, frame),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
