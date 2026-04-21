from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_canary_activation_apply import (  # noqa: E402
    build_checkpoint_pa8_nas100_action_only_canary_activation_apply,
    default_checkpoint_pa8_nas100_action_only_canary_activation_apply_json_path,
    default_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown_path,
    default_checkpoint_pa8_nas100_action_only_canary_active_state_path,
    render_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown,
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
    parser.add_argument(
        "--activation-review-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_nas100_action_only_canary_activation_review_latest.json"),
    )
    parser.add_argument(
        "--activation-packet-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.json"),
    )
    parser.add_argument("--approval-decision", default="APPROVE")
    parser.add_argument("--approval-actor", default="user_requested_manual_activation")
    parser.add_argument(
        "--approval-reason",
        default="explicit_user_request_to_start_pa8_nas100_action_only_canary",
    )
    parser.add_argument(
        "--json-output-path",
        default=str(default_checkpoint_pa8_nas100_action_only_canary_activation_apply_json_path()),
    )
    parser.add_argument(
        "--markdown-output-path",
        default=str(default_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown_path()),
    )
    parser.add_argument(
        "--active-state-output-path",
        default=str(default_checkpoint_pa8_nas100_action_only_canary_active_state_path()),
    )
    args = parser.parse_args(argv)

    payload = build_checkpoint_pa8_nas100_action_only_canary_activation_apply(
        activation_review_payload=_load_json(args.activation_review_path),
        activation_packet_payload=_load_json(args.activation_packet_path),
        approval_decision=args.approval_decision,
        approval_actor=args.approval_actor,
        approval_reason=args.approval_reason,
    )
    markdown = render_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown(payload)

    json_output_path = Path(args.json_output_path)
    markdown_output_path = Path(args.markdown_output_path)
    active_state_output_path = Path(args.active_state_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    active_state_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.write_text(markdown, encoding="utf-8")
    active_state_output_path.write_text(
        json.dumps(dict(payload.get("active_state", {}) or {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "json_output_path": str(json_output_path),
                "markdown_output_path": str(markdown_output_path),
                "active_state_output_path": str(active_state_output_path),
                **dict(payload.get("summary", {}) or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
