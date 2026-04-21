from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_pa9_handoff_apply_packet import (
    build_checkpoint_improvement_pa9_handoff_apply_packet,
    default_checkpoint_improvement_pa9_handoff_apply_packet_json_path,
    default_checkpoint_improvement_pa9_handoff_apply_packet_markdown_path,
    write_checkpoint_improvement_pa9_handoff_apply_packet_outputs,
)
from backend.services.checkpoint_improvement_pa9_handoff_packet import (
    build_checkpoint_improvement_pa9_handoff_packet,
    default_checkpoint_improvement_pa9_handoff_packet_json_path,
    default_checkpoint_improvement_pa9_handoff_packet_markdown_path,
    write_checkpoint_improvement_pa9_handoff_packet_outputs,
)
from backend.services.checkpoint_improvement_pa9_handoff_review_packet import (
    build_checkpoint_improvement_pa9_handoff_review_packet,
    default_checkpoint_improvement_pa9_handoff_review_packet_json_path,
    default_checkpoint_improvement_pa9_handoff_review_packet_markdown_path,
    write_checkpoint_improvement_pa9_handoff_review_packet_outputs,
)


CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_RUNTIME_CONTRACT_VERSION = (
    "checkpoint_improvement_pa9_action_baseline_handoff_runtime_v0"
)


def default_checkpoint_improvement_pa9_handoff_runtime_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_runtime_latest.json"
    )


def default_checkpoint_improvement_pa9_handoff_runtime_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_runtime_latest.md"
    )


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def render_checkpoint_improvement_pa9_handoff_runtime_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    lines: list[str] = []
    lines.append("# PA9 Action Baseline Handoff Runtime")
    lines.append("")
    for key in (
        "trigger_state",
        "recommended_next_action",
        "handoff_state",
        "review_state",
        "apply_state",
        "prepared_symbol_count",
        "review_candidate_symbol_count",
        "apply_candidate_symbol_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def refresh_checkpoint_improvement_pa9_handoff_runtime(
    *,
    runtime_json_output_path: str | Path | None = None,
    runtime_markdown_output_path: str | Path | None = None,
    handoff_json_output_path: str | Path | None = None,
    handoff_markdown_output_path: str | Path | None = None,
    review_json_output_path: str | Path | None = None,
    review_markdown_output_path: str | Path | None = None,
    apply_json_output_path: str | Path | None = None,
    apply_markdown_output_path: str | Path | None = None,
) -> dict[str, Any]:
    handoff_payload = build_checkpoint_improvement_pa9_handoff_packet()
    write_checkpoint_improvement_pa9_handoff_packet_outputs(
        handoff_payload,
        json_output_path=handoff_json_output_path,
        markdown_output_path=handoff_markdown_output_path,
    )

    review_payload = build_checkpoint_improvement_pa9_handoff_review_packet(
        handoff_payload=handoff_payload,
    )
    write_checkpoint_improvement_pa9_handoff_review_packet_outputs(
        review_payload,
        json_output_path=review_json_output_path,
        markdown_output_path=review_markdown_output_path,
    )

    apply_payload = build_checkpoint_improvement_pa9_handoff_apply_packet(
        review_payload=review_payload,
    )
    write_checkpoint_improvement_pa9_handoff_apply_packet_outputs(
        apply_payload,
        json_output_path=apply_json_output_path,
        markdown_output_path=apply_markdown_output_path,
    )

    handoff_summary = _mapping(handoff_payload.get("summary"))
    review_summary = _mapping(review_payload.get("summary"))
    apply_summary = _mapping(apply_payload.get("summary"))
    payload = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_RUNTIME_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "trigger_state": "PA9_HANDOFF_RUNTIME_REFRESHED",
            "recommended_next_action": _to_text(
                apply_summary.get("recommended_next_action")
                or review_summary.get("recommended_next_action")
                or handoff_summary.get("recommended_next_action")
            ),
            "handoff_state": _to_text(handoff_summary.get("handoff_state")),
            "review_state": _to_text(review_summary.get("review_state")),
            "apply_state": _to_text(apply_summary.get("apply_state")),
            "prepared_symbol_count": handoff_summary.get("prepared_symbol_count"),
            "review_candidate_symbol_count": review_summary.get("review_candidate_symbol_count"),
            "apply_candidate_symbol_count": apply_summary.get("apply_candidate_symbol_count"),
        },
        "artifact_paths": {
            "handoff_packet": str(
                Path(handoff_json_output_path or default_checkpoint_improvement_pa9_handoff_packet_json_path())
            ),
            "handoff_markdown": str(
                Path(
                    handoff_markdown_output_path
                    or default_checkpoint_improvement_pa9_handoff_packet_markdown_path()
                )
            ),
            "review_packet": str(
                Path(review_json_output_path or default_checkpoint_improvement_pa9_handoff_review_packet_json_path())
            ),
            "review_markdown": str(
                Path(
                    review_markdown_output_path
                    or default_checkpoint_improvement_pa9_handoff_review_packet_markdown_path()
                )
            ),
            "apply_packet": str(
                Path(apply_json_output_path or default_checkpoint_improvement_pa9_handoff_apply_packet_json_path())
            ),
            "apply_markdown": str(
                Path(
                    apply_markdown_output_path
                    or default_checkpoint_improvement_pa9_handoff_apply_packet_markdown_path()
                )
            ),
        },
        "handoff_packet": handoff_payload,
        "review_packet": review_payload,
        "apply_packet": apply_payload,
    }
    _write_json(runtime_json_output_path or default_checkpoint_improvement_pa9_handoff_runtime_json_path(), payload)
    _write_text(
        runtime_markdown_output_path or default_checkpoint_improvement_pa9_handoff_runtime_markdown_path(),
        render_checkpoint_improvement_pa9_handoff_runtime_markdown(payload),
    )
    return payload
