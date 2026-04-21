from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa7_review_queue_packet import (  # noqa: E402
    build_checkpoint_pa7_review_queue_packet,
    default_checkpoint_pa7_review_queue_packet_path,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resolved-dataset-path",
        default=str(ROOT / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"),
    )
    parser.add_argument("--top-n-groups", type=int, default=12)
    parser.add_argument("--sample-rows-per-group", type=int, default=3)
    parser.add_argument("--json-output-path", default=str(default_checkpoint_pa7_review_queue_packet_path()))
    args = parser.parse_args(argv)

    payload = build_checkpoint_pa7_review_queue_packet(
        _load_csv(args.resolved_dataset_path),
        top_n_groups=int(args.top_n_groups),
        sample_rows_per_group=int(args.sample_rows_per_group),
    )
    output_path = Path(args.json_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"json_output_path": str(output_path), **dict(payload.get("summary", {}) or {})}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
