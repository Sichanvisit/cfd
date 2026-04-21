from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_preview import (  # noqa: E402
    build_nas100_profit_hold_bias_action_preview,
    default_checkpoint_pa8_nas100_profit_hold_bias_preview_path,
    render_nas100_profit_hold_bias_action_preview_markdown,
)

def _default_markdown_output_path() -> Path:
    return default_checkpoint_pa8_nas100_profit_hold_bias_preview_path().with_suffix(".md")


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
    parser.add_argument("--json-output-path", default=str(default_checkpoint_pa8_nas100_profit_hold_bias_preview_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    args = parser.parse_args(argv)

    frame = _load_csv(args.resolved_dataset_path)
    preview_frame, summary = build_nas100_profit_hold_bias_action_preview(frame)
    payload = {
        "summary": summary,
        "rows": list(summary.get("casebook_examples", []) or []),
    }

    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_output_path = Path(args.markdown_output_path)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_nas100_profit_hold_bias_action_preview_markdown(payload), encoding="utf-8")

    print(json.dumps({"json_output_path": str(json_output_path), "markdown_output_path": str(markdown_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
