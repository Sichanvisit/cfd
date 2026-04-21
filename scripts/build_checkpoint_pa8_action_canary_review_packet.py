from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_canary_review_packet import (  # noqa: E402
    build_checkpoint_pa8_nas100_provisional_canary_review_packet,
    default_checkpoint_pa8_nas100_provisional_canary_review_markdown_path,
    default_checkpoint_pa8_nas100_provisional_canary_review_packet_path,
    render_checkpoint_pa8_nas100_provisional_canary_review_markdown,
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
        "--pa8-action-review-packet-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_action_review_packet_latest.json"),
    )
    parser.add_argument(
        "--nas100-symbol-review-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_action_review_nas100_latest.json"),
    )
    parser.add_argument(
        "--nas100-preview-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json"),
    )
    parser.add_argument(
        "--json-output-path",
        default=str(default_checkpoint_pa8_nas100_provisional_canary_review_packet_path()),
    )
    parser.add_argument(
        "--markdown-output-path",
        default=str(default_checkpoint_pa8_nas100_provisional_canary_review_markdown_path()),
    )
    args = parser.parse_args(argv)

    payload = build_checkpoint_pa8_nas100_provisional_canary_review_packet(
        pa8_action_review_packet_payload=_load_json(args.pa8_action_review_packet_path),
        nas100_symbol_review_payload=_load_json(args.nas100_symbol_review_path),
        nas100_profit_hold_bias_preview_payload=_load_json(args.nas100_preview_path),
    )
    markdown = render_checkpoint_pa8_nas100_provisional_canary_review_markdown(payload)

    json_output_path = Path(args.json_output_path)
    markdown_output_path = Path(args.markdown_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

    json_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output_path": str(json_output_path),
                "markdown_output_path": str(markdown_output_path),
                **dict(payload.get("summary", {}) or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
