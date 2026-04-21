"""Build latest multi-surface objective and EV proxy specs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.surface_objective_ev_spec import (  # noqa: E402
    build_surface_objective_ev_spec,
    render_surface_objective_ev_spec_markdown,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_entry_audit_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_entry_audit_latest.json"


def _default_exit_audit_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "market_family_exit_audit_latest.json"


def _default_surface_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_objective_spec_latest.csv"


def _default_surface_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_objective_spec_latest.json"


def _default_surface_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_objective_spec_latest.md"


def _default_ev_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "surface_ev_proxy_spec_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--market-family-entry-audit-path", default=str(_default_entry_audit_path()))
    parser.add_argument("--market-family-exit-audit-path", default=str(_default_exit_audit_path()))
    parser.add_argument("--surface-csv-output-path", default=str(_default_surface_csv_output_path()))
    parser.add_argument("--surface-json-output-path", default=str(_default_surface_json_output_path()))
    parser.add_argument("--surface-md-output-path", default=str(_default_surface_md_output_path()))
    parser.add_argument("--ev-json-output-path", default=str(_default_ev_json_output_path()))
    args = parser.parse_args()

    frame, summary, ev_proxy_spec = build_surface_objective_ev_spec(
        _load_json(args.runtime_status_path),
        _load_json(args.market_family_entry_audit_path),
        _load_json(args.market_family_exit_audit_path),
    )
    markdown = render_surface_objective_ev_spec_markdown(summary, ev_proxy_spec, frame)

    surface_csv_output_path = Path(args.surface_csv_output_path)
    surface_json_output_path = Path(args.surface_json_output_path)
    surface_md_output_path = Path(args.surface_md_output_path)
    ev_json_output_path = Path(args.ev_json_output_path)
    surface_csv_output_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(surface_csv_output_path, index=False, encoding="utf-8-sig")
    surface_json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    surface_md_output_path.write_text(markdown, encoding="utf-8")
    ev_json_output_path.write_text(json.dumps(ev_proxy_spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "surface_csv_output_path": str(surface_csv_output_path),
                "surface_json_output_path": str(surface_json_output_path),
                "ev_json_output_path": str(ev_json_output_path),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
