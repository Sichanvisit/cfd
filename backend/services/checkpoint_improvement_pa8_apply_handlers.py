from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.apply_executor import ApplyExecutor
from backend.services.checkpoint_improvement_pa8_closeout_runtime import (
    refresh_checkpoint_improvement_pa8_closeout_runtime,
)
from backend.services.checkpoint_improvement_pa9_handoff_runtime import (
    refresh_checkpoint_improvement_pa9_handoff_runtime,
)
from backend.services.path_checkpoint_pa8_action_canary_activation_apply import (
    build_checkpoint_pa8_nas100_action_only_canary_activation_apply,
)
from backend.services.path_checkpoint_pa8_action_symbol_review import default_checkpoint_dataset_resolved_path
from backend.services.path_checkpoint_pa8_canary_refresh import (
    build_checkpoint_pa8_canary_refresh_board,
    load_checkpoint_pa8_canary_refresh_resolved_dataset,
    write_checkpoint_pa8_canary_refresh_outputs,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    _build_activation_apply,
    render_checkpoint_pa8_symbol_action_canary_markdown,
)


CHECKPOINT_IMPROVEMENT_PA8_APPLY_HANDLERS_CONTRACT_VERSION = (
    "checkpoint_improvement_pa8_apply_handlers_v0"
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


class CheckpointImprovementPa8ApplyHandlerSet:
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
        apply_executor.register_handler("CANARY_ACTIVATION_REVIEW", self.handle_activation_review)
        apply_executor.register_handler("CANARY_ROLLBACK_REVIEW", self.handle_rollback_review)
        apply_executor.register_handler("CANARY_CLOSEOUT_REVIEW", self.handle_closeout_review)

    def handle_activation_review(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        symbol = self._resolve_symbol(group=group, review_payload=review_payload)
        activation_review = self._load_json(self._artifact_path(symbol, "action_only_canary_activation_review"))
        activation_packet = self._load_json(self._artifact_path(symbol, "action_only_canary_activation_packet"))
        if symbol == "NAS100":
            activation_apply = build_checkpoint_pa8_nas100_action_only_canary_activation_apply(
                activation_review_payload=activation_review,
                activation_packet_payload=activation_packet,
                approval_decision="APPROVE",
                approval_actor="telegram_bridge_apply_executor",
                approval_reason="approved_canary_activation_review",
            )
        else:
            activation_apply = _build_activation_apply(
                activation_review,
                activation_packet,
                approval_decision="APPROVE",
            )
            activation_apply_summary = _mapping(activation_apply.get("summary"))
            activation_apply_summary["approval_actor"] = "telegram_bridge_apply_executor"
            activation_apply_summary["approval_reason"] = "approved_canary_activation_review"
            activation_apply["summary"] = activation_apply_summary
        self._write_activation_state(symbol=symbol, activation_apply=activation_apply)
        self._refresh_canary_outputs()
        pa9_runtime = self._refresh_pa9_handoff_runtime()
        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA8_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "apply_state": _to_text(_mapping(activation_apply.get("summary")).get("activation_apply_state")),
                "recommended_next_action": "start_first_canary_window_observation",
                "symbol": symbol,
                "review_type": "CANARY_ACTIVATION_REVIEW",
            },
            "artifact_paths": {
                "activation_apply": str(self._artifact_path(symbol, "action_only_canary_activation_apply")),
                "active_state": str(self._artifact_path(symbol, "action_only_canary_active_state")),
                **_mapping(pa9_runtime.get("artifact_paths")),
            },
            "activation_apply": activation_apply,
            "pa9_handoff_runtime": pa9_runtime,
        }

    def handle_rollback_review(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        symbol = self._resolve_symbol(group=group, review_payload=review_payload)
        activation_apply = self._load_json(self._artifact_path(symbol, "action_only_canary_activation_apply"))
        updated = self._deactivate_activation_apply(
            activation_apply=activation_apply,
            approval_state="MANUAL_ROLLBACK_APPROVED",
            activation_apply_state="ROLLED_BACK_ACTION_ONLY_CANARY",
            recommended_next_action="return_to_baseline_action_behavior",
            applied_at=_to_text(now_ts, _now_iso()),
        )
        self._write_activation_state(symbol=symbol, activation_apply=updated)
        self._refresh_canary_outputs()
        pa9_runtime = self._refresh_pa9_handoff_runtime()
        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA8_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "apply_state": "ROLLED_BACK_ACTION_ONLY_CANARY",
                "recommended_next_action": "return_to_baseline_action_behavior",
                "symbol": symbol,
                "review_type": "CANARY_ROLLBACK_REVIEW",
            },
            "artifact_paths": {
                "activation_apply": str(self._artifact_path(symbol, "action_only_canary_activation_apply")),
                "active_state": str(self._artifact_path(symbol, "action_only_canary_active_state")),
                **_mapping(pa9_runtime.get("artifact_paths")),
            },
            "activation_apply": updated,
            "pa9_handoff_runtime": pa9_runtime,
        }

    def handle_closeout_review(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        symbol = self._resolve_symbol(group=group, review_payload=review_payload)
        closeout_decision = self._load_json(self._artifact_path(symbol, "action_only_canary_closeout_decision"))
        closeout_runtime = self._refresh_pa8_closeout_runtime()
        self._assert_closeout_ready(
            symbol=symbol,
            closeout_decision=closeout_decision,
            closeout_runtime=closeout_runtime,
        )
        activation_apply = self._load_json(self._artifact_path(symbol, "action_only_canary_activation_apply"))
        updated = self._deactivate_activation_apply(
            activation_apply=activation_apply,
            approval_state="MANUAL_CLOSEOUT_APPROVED",
            activation_apply_state="PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
            recommended_next_action="prepare_pa9_action_baseline_handoff_packet",
            applied_at=_to_text(now_ts, _now_iso()),
        )
        self._write_activation_state(symbol=symbol, activation_apply=updated)
        self._refresh_canary_outputs()
        closeout_runtime = self._refresh_pa8_closeout_runtime()
        pa9_runtime = self._refresh_pa9_handoff_runtime()
        closeout_apply = self._build_closeout_apply_artifact(
            symbol=symbol,
            closeout_decision=closeout_decision,
            closeout_runtime=closeout_runtime,
            now_ts=_to_text(now_ts, _now_iso()),
        )
        self._write_closeout_apply_artifact(symbol=symbol, payload=closeout_apply)
        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA8_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
                "symbol": symbol,
                "review_type": "CANARY_CLOSEOUT_REVIEW",
            },
            "artifact_paths": {
                "activation_apply": str(self._artifact_path(symbol, "action_only_canary_activation_apply")),
                "active_state": str(self._artifact_path(symbol, "action_only_canary_active_state")),
                "closeout_apply": str(self._artifact_path(symbol, "action_only_canary_closeout_apply")),
                **_mapping(closeout_runtime.get("artifact_paths")),
                **_mapping(pa9_runtime.get("artifact_paths")),
            },
            "activation_apply": updated,
            "closeout_apply": closeout_apply,
            "pa8_closeout_runtime": closeout_runtime,
            "pa9_handoff_runtime": pa9_runtime,
        }

    def _resolve_symbol(
        self,
        *,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
    ) -> str:
        symbol = _to_text(_mapping(group).get("symbol"), _to_text(_mapping(review_payload).get("symbol"))).upper()
        if not symbol:
            raise ValueError("symbol_required_for_pa8_apply_handler")
        return symbol

    def _artifact_path(self, symbol: str, artifact_name: str, *, markdown: bool = False) -> Path:
        suffix = ".md" if markdown else ".json"
        return self._shadow_auto_dir / f"checkpoint_pa8_{str(symbol).lower()}_{artifact_name}_latest{suffix}"

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

    def _write_closeout_apply_artifact(self, *, symbol: str, payload: Mapping[str, Any]) -> None:
        json_path = self._artifact_path(symbol, "action_only_canary_closeout_apply")
        markdown_path = self._artifact_path(symbol, "action_only_canary_closeout_apply", markdown=True)
        _write_json(json_path, payload)
        lines = ["# PA8 Action-Only Canary Closeout Apply", ""]
        summary = _mapping(payload.get("summary"))
        for key in (
            "symbol",
            "apply_state",
            "closeout_state_before_apply",
            "review_state",
            "apply_packet_state",
            "live_observation_ready",
            "observed_window_row_count",
            "sample_floor",
            "active_trigger_count",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{summary.get(key)}`")
        lines.append("")
        _write_text(markdown_path, "\n".join(lines).rstrip() + "\n")

    def _build_closeout_apply_artifact(
        self,
        *,
        symbol: str,
        closeout_decision: Mapping[str, Any] | None,
        closeout_runtime: Mapping[str, Any] | None,
        now_ts: str,
    ) -> dict[str, Any]:
        closeout_summary = _mapping(_mapping(closeout_decision).get("summary"))
        review_summary = _mapping(_mapping(closeout_runtime).get("review_packet", {}).get("summary"))
        apply_summary = _mapping(_mapping(closeout_runtime).get("apply_packet", {}).get("summary"))
        return {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_PA8_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": now_ts,
                "symbol": symbol,
                "review_type": "CANARY_CLOSEOUT_REVIEW",
                "apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                "closeout_state_before_apply": _to_text(closeout_summary.get("closeout_state")),
                "review_state": _to_text(review_summary.get("review_state")),
                "apply_packet_state": _to_text(apply_summary.get("apply_state")),
                "live_observation_ready": _to_bool(closeout_summary.get("live_observation_ready")),
                "observed_window_row_count": _to_text(closeout_summary.get("observed_window_row_count")),
                "sample_floor": _to_text(closeout_summary.get("sample_floor")),
                "active_trigger_count": _to_text(closeout_summary.get("active_trigger_count")),
                "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
            }
        }

    def _deactivate_activation_apply(
        self,
        *,
        activation_apply: Mapping[str, Any] | None,
        approval_state: str,
        activation_apply_state: str,
        recommended_next_action: str,
        applied_at: str,
    ) -> dict[str, Any]:
        payload = _mapping(activation_apply)
        summary = _mapping(payload.get("summary"))
        active_state = _mapping(payload.get("active_state"))
        summary["approval_decision"] = "APPROVE"
        summary["approval_state"] = approval_state
        summary["activation_apply_state"] = activation_apply_state
        summary["active"] = False
        summary["recommended_next_action"] = recommended_next_action
        summary["generated_at"] = applied_at
        payload["summary"] = summary

        active_state["approval_state"] = approval_state
        active_state["activation_apply_state"] = activation_apply_state
        active_state["active"] = False
        active_state["window_status"] = "WINDOW_NOT_ACTIVE"
        active_state["deactivated_at"] = applied_at
        payload["active_state"] = active_state
        return payload

    def _load_resolved_dataset(self) -> pd.DataFrame:
        return load_checkpoint_pa8_canary_refresh_resolved_dataset(self._resolved_dataset_path)

    def _refresh_canary_outputs(self) -> None:
        payload = build_checkpoint_pa8_canary_refresh_board(self._load_resolved_dataset())
        write_checkpoint_pa8_canary_refresh_outputs(payload)

    def _refresh_pa8_closeout_runtime(self) -> dict[str, Any]:
        return refresh_checkpoint_improvement_pa8_closeout_runtime()

    def _refresh_pa9_handoff_runtime(self) -> dict[str, Any]:
        return refresh_checkpoint_improvement_pa9_handoff_runtime()

    def _assert_closeout_ready(
        self,
        *,
        symbol: str,
        closeout_decision: Mapping[str, Any] | None,
        closeout_runtime: Mapping[str, Any] | None,
    ) -> None:
        closeout_summary = _mapping(_mapping(closeout_decision).get("summary"))
        closeout_state = _to_text(closeout_summary.get("closeout_state")).upper()
        if closeout_state != "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW":
            raise ValueError(f"pa8_closeout_not_ready::{closeout_state or 'UNKNOWN'}")
        if not _to_bool(closeout_summary.get("live_observation_ready")):
            raise ValueError("pa8_closeout_live_window_not_ready")
        observed_window_row_count = int(_to_text(closeout_summary.get("observed_window_row_count"), "0") or "0")
        sample_floor = int(_to_text(closeout_summary.get("sample_floor"), "0") or "0")
        if observed_window_row_count < sample_floor:
            raise ValueError("pa8_closeout_sample_floor_not_met")
        active_trigger_count = int(_to_text(closeout_summary.get("active_trigger_count"), "0") or "0")
        if active_trigger_count > 0:
            raise ValueError("pa8_closeout_trigger_guard_active")
        review_packet = _mapping(_mapping(closeout_runtime).get("review_packet"))
        apply_packet = _mapping(_mapping(closeout_runtime).get("apply_packet"))
        review_summary = _mapping(review_packet.get("summary"))
        apply_summary = _mapping(apply_packet.get("summary"))
        if not _to_bool(review_summary.get("review_ready")):
            raise ValueError(
                f"pa8_closeout_review_packet_not_ready::{_to_text(review_summary.get('review_state'), 'UNKNOWN')}"
            )
        if not _to_bool(apply_summary.get("allow_apply")):
            raise ValueError(
                f"pa8_closeout_apply_packet_not_ready::{_to_text(apply_summary.get('apply_state'), 'UNKNOWN')}"
            )
        rows = list(review_packet.get("rows", []) or [])
        matching = next(
            (
                _mapping(row)
                for row in rows
                if _to_text(_mapping(row).get("symbol")).upper() == symbol
            ),
            {},
        )
        if not _to_bool(matching.get("closeout_review_candidate")):
            raise ValueError(f"pa8_closeout_symbol_not_review_candidate::{symbol}")


def register_default_pa8_apply_handlers(
    apply_executor: ApplyExecutor,
    *,
    shadow_auto_dir: str | Path | None = None,
    resolved_dataset_path: str | Path | None = None,
) -> CheckpointImprovementPa8ApplyHandlerSet:
    handler_set = CheckpointImprovementPa8ApplyHandlerSet(
        shadow_auto_dir=shadow_auto_dir,
        resolved_dataset_path=resolved_dataset_path,
    )
    handler_set.register_into(apply_executor)
    return handler_set
