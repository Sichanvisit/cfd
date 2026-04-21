"""Build latest generic bounded symbol-surface activation contract artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.bounded_symbol_surface_activation_contract import (  # noqa: E402
    build_bounded_symbol_surface_activation_contract,
    render_bounded_symbol_surface_activation_contract_markdown,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signoff-packet-path", default=str(_default_shadow_auto_dir() / "symbol_surface_canary_signoff_packet_latest.json"))
    parser.add_argument("--csv-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.csv"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.json"))
    parser.add_argument("--md-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.md"))
    args = parser.parse_args()

    frame, summary = build_bounded_symbol_surface_activation_contract(
        symbol_surface_canary_signoff_packet_payload=_load_json(args.signoff_packet_path),
    )
    markdown = render_bounded_symbol_surface_activation_contract_markdown(summary, frame)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
