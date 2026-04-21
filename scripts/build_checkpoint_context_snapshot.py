"""Build latest checkpoint context snapshot artifact for PA3 instrumentation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_context import (  # noqa: E402
    build_checkpoint_context_snapshot,
    default_checkpoint_rows_path,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "checkpoint_context_snapshot_latest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--recent-limit", type=int, default=400)
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    args = parser.parse_args(argv)

    snapshot, summary = build_checkpoint_context_snapshot(
        _load_json(args.runtime_status_path),
        _load_csv(args.checkpoint_rows_path),
        recent_limit=int(args.recent_limit),
    )

    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(
        json.dumps(
            {"summary": summary, "rows": snapshot.to_dict(orient="records")},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"json_output_path": str(json_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
