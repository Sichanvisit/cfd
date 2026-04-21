from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_review_packet import (  # noqa: E402
    build_checkpoint_pa8_action_review_packet,
    default_checkpoint_pa8_action_review_packet_path,
)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pa78-review-packet-path", default=str(_default_shadow_auto_dir() / "checkpoint_pa78_review_packet_latest.json"))
    parser.add_argument("--action-eval-path", default=str(_default_shadow_auto_dir() / "checkpoint_action_eval_latest.json"))
    parser.add_argument("--management-snapshot-path", default=str(_default_shadow_auto_dir() / "checkpoint_management_action_snapshot_latest.json"))
    parser.add_argument("--observation-path", default=str(_default_shadow_auto_dir() / "checkpoint_position_side_observation_latest.json"))
    parser.add_argument("--live-runner-watch-path", default=str(_default_shadow_auto_dir() / "checkpoint_live_runner_watch_latest.json"))
    parser.add_argument("--json-output-path", default=str(default_checkpoint_pa8_action_review_packet_path()))
    args = parser.parse_args(argv)

    payload = build_checkpoint_pa8_action_review_packet(
        pa78_review_packet_payload=_load_json(args.pa78_review_packet_path),
        action_eval_payload=_load_json(args.action_eval_path),
        management_action_snapshot_payload=_load_json(args.management_snapshot_path),
        observation_payload=_load_json(args.observation_path),
        live_runner_watch_payload=_load_json(args.live_runner_watch_path),
    )
    output_path = Path(args.json_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"json_output_path": str(output_path), **dict(payload.get("summary", {}) or {})}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
