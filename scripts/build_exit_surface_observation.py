from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.exit_surface_observation import (  # noqa: E402
    build_exit_surface_observation_v1,
    write_exit_surface_observation_v1,
)


def main() -> int:
    payload = build_exit_surface_observation_v1()
    outputs = write_exit_surface_observation_v1(payload)
    print(
        json.dumps(
            {
                "outputs": {k: str(v) for k, v in outputs.items()},
                "status": payload.get("status", ""),
                "runner_preservation_total_count": payload.get("runner_preservation_total_count", 0),
                "runner_preservation_live_count": payload.get("runner_preservation_live_count", 0),
                "protective_surface_total_count": payload.get("protective_surface_total_count", 0),
                "surface_state_counts": payload.get("surface_state_counts", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
