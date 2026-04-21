"""Build active runtime activation status for an approved bounded semantic shadow candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.semantic_shadow_active_runtime_activation import (  # noqa: E402
    build_semantic_shadow_active_runtime_activation,
    render_semantic_shadow_active_runtime_activation_markdown,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _rows_from_json(path: Path) -> pd.DataFrame:
    payload = _load_json(path)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return pd.DataFrame(rows)


def _default_approval_json_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_bounded_candidate_approval_latest.json"


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_active_model_dir() -> Path:
    return ROOT / "models" / "semantic_v1"


def _default_backup_root_dir() -> Path:
    return ROOT / "models" / "backups"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_activation_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_activation_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_active_runtime_activation_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval-json-path", default=str(_default_approval_json_path()))
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--active-model-dir", default=str(_default_active_model_dir()))
    parser.add_argument("--backup-root-dir", default=str(_default_backup_root_dir()))
    parser.add_argument("--force-activate", action="store_true")
    parser.add_argument("--override-reason", default="")
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    approval_frame = _rows_from_json(Path(args.approval_json_path))
    runtime_status = _load_json(Path(args.runtime_status_path))
    frame, summary = build_semantic_shadow_active_runtime_activation(
        approval_frame,
        runtime_status=runtime_status,
        active_model_dir=args.active_model_dir,
        backup_root_dir=args.backup_root_dir,
        force_activate=bool(args.force_activate),
        override_reason=args.override_reason,
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
        render_semantic_shadow_active_runtime_activation_markdown(summary, frame),
        encoding="utf-8",
    )
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
