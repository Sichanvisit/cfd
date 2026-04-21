from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_review_checklist import (  # noqa: E402
    default_checkpoint_pa8_action_review_checklist_json_path,
)
from backend.services.path_checkpoint_pa8_action_symbol_review import (  # noqa: E402
    build_checkpoint_pa8_action_symbol_review,
    default_checkpoint_dataset_resolved_path,
    default_checkpoint_pa8_action_symbol_review_json_path,
    default_checkpoint_pa8_action_symbol_review_markdown_path,
    load_checkpoint_dataset_resolved_rows,
    render_checkpoint_pa8_action_symbol_review_markdown,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--pa8-checklist-path", default=str(default_checkpoint_pa8_action_review_checklist_json_path()))
    parser.add_argument("--resolved-dataset-path", default=str(default_checkpoint_dataset_resolved_path()))
    parser.add_argument("--json-output-path")
    parser.add_argument("--markdown-output-path")
    args = parser.parse_args(argv)

    symbol = str(args.symbol).upper()
    json_output_path = Path(args.json_output_path) if args.json_output_path else default_checkpoint_pa8_action_symbol_review_json_path(symbol)
    markdown_output_path = (
        Path(args.markdown_output_path)
        if args.markdown_output_path
        else default_checkpoint_pa8_action_symbol_review_markdown_path(symbol)
    )

    payload = build_checkpoint_pa8_action_symbol_review(
        symbol=symbol,
        pa8_action_review_checklist_payload=_load_json(args.pa8_checklist_path),
        resolved_rows=load_checkpoint_dataset_resolved_rows(args.resolved_dataset_path),
    )
    markdown = render_checkpoint_pa8_action_symbol_review_markdown(payload)

    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "symbol": symbol,
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
