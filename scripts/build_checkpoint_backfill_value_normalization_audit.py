from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.path_checkpoint_backfill_value_normalization_audit import (  # noqa: E402
    build_checkpoint_backfill_value_normalization_audit,
    default_checkpoint_backfill_value_normalization_audit_path,
)


def main() -> None:
    repo_root = REPO_ROOT
    resolved_path = repo_root / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"
    review_processor_path = repo_root / "data" / "analysis" / "shadow_auto" / "checkpoint_pa7_review_processor_latest.json"
    output_path = default_checkpoint_backfill_value_normalization_audit_path()

    frame = pd.read_csv(resolved_path, low_memory=False) if resolved_path.exists() else pd.DataFrame()
    review_payload = {}
    if review_processor_path.exists():
        review_payload = json.loads(review_processor_path.read_text(encoding="utf-8"))

    payload = build_checkpoint_backfill_value_normalization_audit(
        frame,
        review_processor_payload=review_payload,
    )
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
