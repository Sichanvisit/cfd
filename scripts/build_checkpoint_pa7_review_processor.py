from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.path_checkpoint_pa7_review_processor import (
    build_checkpoint_pa7_review_processor,
    default_checkpoint_pa7_review_processor_path,
)


def main() -> None:
    repo_root = REPO_ROOT
    resolved_path = repo_root / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"
    output_path = default_checkpoint_pa7_review_processor_path()

    frame = pd.read_csv(resolved_path) if resolved_path.exists() else pd.DataFrame()
    payload = build_checkpoint_pa7_review_processor(frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output_path": str(output_path),
                **payload.get("summary", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
