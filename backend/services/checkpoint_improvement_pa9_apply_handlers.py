from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.apply_executor import ApplyExecutor
from backend.services.checkpoint_improvement_pa9_handoff_runtime import (
    refresh_checkpoint_improvement_pa9_handoff_runtime,
)
from backend.services.path_checkpoint_pa8_action_symbol_review import (
    default_checkpoint_dataset_resolved_path,
)
from backend.services.path_checkpoint_pa8_canary_refresh import (
    build_checkpoint_pa8_canary_refresh_board,
    load_checkpoint_pa8_canary_refresh_resolved_dataset,
    write_checkpoint_pa8_canary_refresh_outputs,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    render_checkpoint_pa8_symbol_action_canary_markdown,
)


CHECKPOINT_IMPROVEMENT_PA9_APPLY_HANDLERS_CONTRACT_VERSION = (
    "checkpoint_improvement_pa9_apply_handlers_v0"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CheckpointImprovementPa9ApplyHandlerSet:
    def __init__(
        self,
        *,
        shadow_auto_dir: str | Path | None = None,
        resolved_dataset_path: str | Path | None = None,
    ) -> None:
        self._shadow_auto_dir = (
            Path(shadow_auto_dir)
            if shadow_auto_dir is not None
            else _repo_root() / "data" / "analysis" / "shadow_auto"
        )
        self._resolved_dataset_path = (
            Path(resolved_dataset_path)
            if resolved_dataset_path is not None
            else default_checkpoint_dataset_resolved_path()
        )

    def register_into(self, apply_executor: ApplyExecutor) -> None:
        apply_executor.register_handler(
            "PA9_ACTION_BASELINE_HANDOFF_REVIEW",
            self.handle_handoff_review,
        )

    def handle_handoff_review(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        symbol = self._resolve_symbol(group=group, review_payload=review_payload)
        runtime = refresh_checkpoint_improvement_pa9_handoff_runtime()
        self._assert_handoff_ready(symbol=symbol, runtime=runtime)

        activation_apply = self._load_json(self._artifact_path(symbol, "action_only_canary_activation_apply"))
        updated = self._mark_handoff_applied(
            activation_apply=activation_apply,
            applied_at=_to_text(now_ts, _now_iso()),
        )
        self._write_activation_state(symbol=symbol, activation_apply=updated)
        self._refresh_canary_outputs()

        handoff_apply = self._build_handoff_apply_artifact(
            symbol=symbol,
            runtime=runtime,
            now_ts=_to_text(now_ts, _now_iso()),
        )
        self._write_handoff_apply_artifact(symbol=symbol, payload=handoff_apply)
        refreshed_runtime = refresh_checkpoint_improvement_pa9_handoff_runtime()

        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA9_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                "recommended_next_action": "monitor_post_handoff_action_baseline_runtime",
                "symbol": symbol,
                "review_type": "PA9_ACTION_BASELINE_HANDOFF_REVIEW",
            },
            "artifact_paths": {
                "activation_apply": str(self._artifact_path(symbol, "action_only_canary_activation_apply")),
                "active_state": str(self._artifact_path(symbol, "action_only_canary_active_state")),
                "handoff_apply": str(self._handoff_apply_artifact_path(symbol)),
                **_mapping(refreshed_runtime.get("artifact_paths")),
            },
            "activation_apply": updated,
            "handoff_apply": handoff_apply,
            "pa9_handoff_runtime": refreshed_runtime,
        }

    def _resolve_symbol(
        self,
        *,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
    ) -> str:
        symbol = _to_text(_mapping(group).get("symbol"), _to_text(_mapping(review_payload).get("symbol"))).upper()
        if not symbol:
            raise ValueError("symbol_required_for_pa9_apply_handler")
        return symbol

    def _artifact_path(self, symbol: str, artifact_name: str, *, markdown: bool = False) -> Path:
        suffix = ".md" if markdown else ".json"
        return self._shadow_auto_dir / f"checkpoint_pa8_{str(symbol).lower()}_{artifact_name}_latest{suffix}"

    def _handoff_apply_artifact_path(self, symbol: str, *, markdown: bool = False) -> Path:
        suffix = ".md" if markdown else ".json"
        return self._shadow_auto_dir / f"checkpoint_pa9_{str(symbol).lower()}_action_baseline_handoff_apply_latest{suffix}"

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_activation_state(self, *, symbol: str, activation_apply: Mapping[str, Any]) -> None:
        payload = _mapping(activation_apply)
        activation_apply_path = self._artifact_path(symbol, "action_only_canary_activation_apply")
        activation_apply_md_path = self._artifact_path(symbol, "action_only_canary_activation_apply", markdown=True)
        active_state_path = self._artifact_path(symbol, "action_only_canary_active_state")
        _write_json(activation_apply_path, payload)
        _write_text(
            activation_apply_md_path,
            render_checkpoint_pa8_symbol_action_canary_markdown("activation_apply", payload),
        )
        active_state = _mapping(payload.get("active_state"))
        if active_state:
            _write_json(active_state_path, active_state)

    def _write_handoff_apply_artifact(self, *, symbol: str, payload: Mapping[str, Any]) -> None:
        json_path = self._handoff_apply_artifact_path(symbol)
        markdown_path = self._handoff_apply_artifact_path(symbol, markdown=True)
        _write_json(json_path, payload)
        summary = _mapping(payload.get("summary"))
        lines = ["# PA9 Action Baseline Handoff Apply", ""]
        for key in (
            "symbol",
            "apply_state",
            "review_state",
            "runtime_apply_state",
            "prepared_activation_state_before_apply",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{summary.get(key)}`")
        lines.append("")
        _write_text(markdown_path, "\n".join(lines).rstrip() + "\n")

    def _mark_handoff_applied(
        self,
        *,
        activation_apply: Mapping[str, Any] | None,
        applied_at: str,
    ) -> dict[str, Any]:
        payload = _mapping(activation_apply)
        summary = _mapping(payload.get("summary"))
        active_state = _mapping(payload.get("active_state"))
        summary["approval_decision"] = "APPROVE"
        summary["approval_state"] = "MANUAL_PA9_HANDOFF_APPROVED"
        summary["activation_apply_state"] = "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
        summary["active"] = False
        summary["recommended_next_action"] = "monitor_post_handoff_action_baseline_runtime"
        summary["generated_at"] = applied_at
        payload["summary"] = summary

        active_state["approval_state"] = "MANUAL_PA9_HANDOFF_APPROVED"
        active_state["activation_apply_state"] = "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
        active_state["active"] = False
        active_state["window_status"] = "WINDOW_NOT_ACTIVE"
        active_state["handoff_applied_at"] = applied_at
        payload["active_state"] = active_state
        return payload

    def _build_handoff_apply_artifact(
        self,
        *,
        symbol: str,
        runtime: Mapping[str, Any] | None,
        now_ts: str,
    ) -> dict[str, Any]:
        review_summary = _mapping(_mapping(runtime).get("review_packet", {}).get("summary"))
        apply_summary = _mapping(_mapping(runtime).get("apply_packet", {}).get("summary"))
        row = next(
            (
                _mapping(item)
                for item in list(_mapping(runtime).get("apply_packet", {}).get("rows", []) or [])
                if _to_text(_mapping(item).get("symbol")).upper() == symbol
            ),
            {},
        )
        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA9_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": now_ts,
                "symbol": symbol,
                "review_type": "PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                "apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                "review_state": _to_text(review_summary.get("review_state")),
                "runtime_apply_state": _to_text(apply_summary.get("apply_state")),
                "prepared_activation_state_before_apply": _to_text(row.get("activation_apply_state")),
                "recommended_next_action": "monitor_post_handoff_action_baseline_runtime",
            }
        }

    def _assert_handoff_ready(self, *, symbol: str, runtime: Mapping[str, Any] | None) -> None:
        runtime_map = _mapping(runtime)
        summary = _mapping(runtime_map.get("summary"))
        review_state = _to_text(summary.get("review_state"))
        apply_state = _to_text(summary.get("apply_state"))
        if review_state != "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW":
            raise ValueError(f"pa9_handoff_review_not_ready::{review_state or 'UNKNOWN'}")
        if apply_state != "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW":
            raise ValueError(f"pa9_handoff_apply_not_ready::{apply_state or 'UNKNOWN'}")

        review_rows = list(_mapping(runtime_map.get("review_packet")).get("rows", []) or [])
        apply_rows = list(_mapping(runtime_map.get("apply_packet")).get("rows", []) or [])
        review_row = next(
            (
                _mapping(row)
                for row in review_rows
                if _to_text(_mapping(row).get("symbol")).upper() == symbol
            ),
            {},
        )
        apply_row = next(
            (
                _mapping(row)
                for row in apply_rows
                if _to_text(_mapping(row).get("symbol")).upper() == symbol
            ),
            {},
        )
        if not _to_bool(review_row.get("handoff_review_candidate")):
            raise ValueError(f"pa9_handoff_symbol_not_review_candidate::{symbol}")
        if not _to_bool(apply_row.get("handoff_apply_candidate")):
            raise ValueError(f"pa9_handoff_symbol_not_apply_candidate::{symbol}")

    def _refresh_canary_outputs(self) -> None:
        resolved_dataset = load_checkpoint_pa8_canary_refresh_resolved_dataset(self._resolved_dataset_path)
        payload = build_checkpoint_pa8_canary_refresh_board(resolved_dataset)
        write_checkpoint_pa8_canary_refresh_outputs(payload)


def register_default_pa9_apply_handlers(
    apply_executor: ApplyExecutor,
    *,
    shadow_auto_dir: str | Path | None = None,
    resolved_dataset_path: str | Path | None = None,
) -> CheckpointImprovementPa9ApplyHandlerSet:
    handler_set = CheckpointImprovementPa9ApplyHandlerSet(
        shadow_auto_dir=shadow_auto_dir,
        resolved_dataset_path=resolved_dataset_path,
    )
    handler_set.register_into(apply_executor)
    return handler_set
