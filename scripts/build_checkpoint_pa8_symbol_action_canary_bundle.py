from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_action_symbol_review import (  # noqa: E402
    default_checkpoint_dataset_resolved_path,
    default_checkpoint_pa8_action_symbol_review_json_path,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (  # noqa: E402
    build_checkpoint_pa8_symbol_action_canary_bundle,
    default_checkpoint_pa8_symbol_action_canary_artifact_path,
    render_checkpoint_pa8_symbol_action_canary_markdown,
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


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--approval-decision", default="APPROVE")
    parser.add_argument(
        "--resolved-dataset-path",
        default=str(default_checkpoint_dataset_resolved_path()),
    )
    parser.add_argument(
        "--pa8-action-review-packet-path",
        default=str(_default_shadow_auto_dir() / "checkpoint_pa8_action_review_packet_latest.json"),
    )
    parser.add_argument("--symbol-review-path")
    args = parser.parse_args(argv)

    symbol = str(args.symbol).upper()
    symbol_review_path = Path(args.symbol_review_path) if args.symbol_review_path else default_checkpoint_pa8_action_symbol_review_json_path(symbol)
    bundle = build_checkpoint_pa8_symbol_action_canary_bundle(
        resolved_dataset=_load_csv(args.resolved_dataset_path),
        pa8_action_review_packet_payload=_load_json(args.pa8_action_review_packet_path),
        symbol_review_payload=_load_json(symbol_review_path),
        symbol=symbol,
        approval_decision=str(args.approval_decision).upper(),
    )

    artifact_map = {
        "preview": "action_only_preview",
        "canary_review": "provisional_canary_review_packet",
        "execution_checklist": "action_only_canary_execution_checklist",
        "activation_packet": "action_only_canary_activation_packet",
        "activation_review": "action_only_canary_activation_review",
        "monitoring_packet": "action_only_canary_monitoring_packet",
        "rollback_packet": "action_only_canary_rollback_review_packet",
        "activation_apply": "action_only_canary_activation_apply",
        "first_window_observation": "action_only_canary_first_window_observation",
        "closeout_decision": "action_only_canary_closeout_decision",
    }
    output_paths: dict[str, str] = {}
    for key, artifact_name in artifact_map.items():
        payload = dict(bundle.get(key) or {})
        json_path = default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, artifact_name, markdown=False)
        md_path = default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, artifact_name, markdown=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_checkpoint_pa8_symbol_action_canary_markdown(key, payload), encoding="utf-8")
        output_paths[key] = str(json_path)

    activation_apply = dict(bundle.get("activation_apply") or {})
    active_state = dict(activation_apply.get("active_state") or {})
    if active_state:
        active_state_path = default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, "action_only_canary_active_state", markdown=False)
        active_state_path.parent.mkdir(parents=True, exist_ok=True)
        active_state_path.write_text(json.dumps(active_state, ensure_ascii=False, indent=2), encoding="utf-8")
        output_paths["active_state"] = str(active_state_path)

    print(
        json.dumps(
            {
                "symbol": symbol,
                "output_paths": output_paths,
                "preview_summary": dict(_load_json(output_paths["preview"]).get("summary") or {}),
                "activation_packet_summary": dict(_load_json(output_paths["activation_packet"]).get("summary") or {}),
                "activation_apply_summary": dict(_load_json(output_paths["activation_apply"]).get("summary") or {}),
                "closeout_decision_summary": dict(_load_json(output_paths["closeout_decision"]).get("summary") or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
