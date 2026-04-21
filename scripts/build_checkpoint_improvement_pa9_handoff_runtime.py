from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.checkpoint_improvement_pa9_handoff_runtime import (  # noqa: E402
    refresh_checkpoint_improvement_pa9_handoff_runtime,
)


def main() -> int:
    payload = refresh_checkpoint_improvement_pa9_handoff_runtime()
    print(json.dumps(_json_safe_summary(payload), ensure_ascii=False, indent=2))
    return 0


def _json_safe_summary(payload: dict[str, object]) -> dict[str, object]:
    summary = dict(payload.get("summary", {}) or {})
    artifact_paths = dict(payload.get("artifact_paths", {}) or {})
    return {
        **summary,
        **artifact_paths,
    }


if __name__ == "__main__":
    raise SystemExit(main())
