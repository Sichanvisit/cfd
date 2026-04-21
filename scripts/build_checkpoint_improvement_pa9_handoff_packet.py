from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.checkpoint_improvement_pa9_handoff_packet import (  # noqa: E402
    build_checkpoint_improvement_pa9_handoff_packet,
    default_checkpoint_improvement_pa9_handoff_packet_json_path,
    default_checkpoint_improvement_pa9_handoff_packet_markdown_path,
    write_checkpoint_improvement_pa9_handoff_packet_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-output-path",
        default=str(default_checkpoint_improvement_pa9_handoff_packet_json_path()),
    )
    parser.add_argument(
        "--markdown-output-path",
        default=str(default_checkpoint_improvement_pa9_handoff_packet_markdown_path()),
    )
    args = parser.parse_args(argv)

    payload = build_checkpoint_improvement_pa9_handoff_packet()
    write_checkpoint_improvement_pa9_handoff_packet_outputs(
        payload,
        json_output_path=args.json_output_path,
        markdown_output_path=args.markdown_output_path,
    )
    print(
        json.dumps(
            {
                "json_output_path": str(Path(args.json_output_path)),
                "markdown_output_path": str(Path(args.markdown_output_path)),
                **dict(payload.get("summary", {}) or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
