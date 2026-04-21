from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.apply_executor import ApplyExecutor
from backend.services.teacher_pattern_active_candidate_runtime import (
    build_default_active_candidate_state,
    normalize_state25_teacher_weight_overrides,
    render_state25_teacher_weight_override_lines_ko,
)


STATE25_WEIGHT_PATCH_APPLY_HANDLERS_CONTRACT_VERSION = (
    "state25_weight_patch_apply_handlers_v0"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_active_candidate_state_path() -> Path:
    return _repo_root() / "models" / "teacher_pattern_state25_candidates" / "active_candidate_state.json"


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    for raw in value:
        text = _to_text(raw)
        if text:
            rows.append(text)
    return rows


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _render_markdown(payload: Mapping[str, Any] | None) -> str:
    row = _mapping(payload)
    lines = [
        "# State25 Weight Patch Apply",
        "",
        f"- apply_state: `{_to_text(row.get('apply_state'))}`",
        f"- candidate_id: `{_to_text(row.get('candidate_id'))}`",
        f"- binding_mode: `{_to_text(row.get('binding_mode'))}`",
        f"- symbol_scope: `{', '.join(_as_str_list(row.get('symbol_scope')) or ['*'])}`",
        f"- entry_stage_scope: `{', '.join(_as_str_list(row.get('entry_stage_scope')) or ['*'])}`",
        "",
        "## Weight Overrides",
        "",
    ]
    override_lines = list(row.get("teacher_weight_override_display_ko", []) or [])
    if override_lines:
        lines.extend(override_lines)
    else:
        lines.append("- 변경 없음")
    return "\n".join(lines) + "\n"


class State25WeightPatchApplyHandlerSet:
    def __init__(
        self,
        *,
        active_candidate_state_path: str | Path | None = None,
        shadow_auto_dir: str | Path | None = None,
    ) -> None:
        self._active_candidate_state_path = (
            Path(active_candidate_state_path)
            if active_candidate_state_path is not None
            else _default_active_candidate_state_path()
        )
        self._shadow_auto_dir = (
            Path(shadow_auto_dir)
            if shadow_auto_dir is not None
            else _default_shadow_auto_dir()
        )

    def register_into(self, apply_executor: ApplyExecutor) -> None:
        apply_executor.register_handler(
            "STATE25_WEIGHT_PATCH_REVIEW",
            self.handle_weight_patch_review,
        )

    def handle_weight_patch_review(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        event_payload = _mapping(approval_event_payload)
        review = _mapping(review_payload)
        existing_state = build_default_active_candidate_state()
        existing_state.update(_load_json(self._active_candidate_state_path))
        existing_patch = _mapping(existing_state.get("desired_runtime_patch"))

        proposed_patch = _mapping(review.get("weight_patch"))
        proposed_overrides = normalize_state25_teacher_weight_overrides(
            proposed_patch.get("state25_teacher_weight_overrides")
            or review.get("state25_teacher_weight_overrides")
        )
        merged_overrides = normalize_state25_teacher_weight_overrides(
            {
                **_mapping(existing_patch.get("state25_teacher_weight_overrides")),
                **proposed_overrides,
            }
        )

        symbol_scope = _as_str_list(
            proposed_patch.get("state25_execution_symbol_allowlist")
            or review.get("state25_execution_symbol_allowlist")
            or existing_patch.get("state25_execution_symbol_allowlist")
        )
        entry_stage_scope = _as_str_list(
            proposed_patch.get("state25_execution_entry_stage_allowlist")
            or review.get("state25_execution_entry_stage_allowlist")
            or existing_patch.get("state25_execution_entry_stage_allowlist")
        )
        binding_mode = _to_text(
            proposed_patch.get("state25_execution_bind_mode"),
            _to_text(existing_patch.get("state25_execution_bind_mode"), "log_only"),
        )
        bounded_live_enabled = bool(
            binding_mode in {"bounded_live", "canary"}
            or _as_bool(proposed_patch.get("state25_weight_bounded_live_enabled"), False)
        )
        rollout_phase = "bounded_live" if bounded_live_enabled else "log_only"
        apply_state = (
            "STATE25_WEIGHT_PATCH_BOUNDED_LIVE_ACTIVE"
            if bounded_live_enabled
            else "STATE25_WEIGHT_PATCH_LOG_ONLY_ACTIVE"
        )
        last_event = (
            "apply_state25_weight_patch_bounded_live"
            if bounded_live_enabled
            else "apply_state25_weight_patch_log_only"
        )
        candidate_id = _to_text(
            review.get("candidate_id"),
            _to_text(existing_state.get("active_candidate_id"), "state25_weight_patch"),
        )
        applied_at = _to_text(now_ts, _now_iso())
        state_payload = {
            **existing_state,
            "active_candidate_id": candidate_id,
            "active_policy_source": "state25_candidate",
            "current_rollout_phase": rollout_phase,
            "current_binding_mode": binding_mode or "log_only",
            "activated_at": applied_at,
            "last_event": last_event,
            "desired_runtime_patch": {
                **existing_patch,
                "apply_now": True,
                "state25_execution_bind_mode": binding_mode or "log_only",
                "state25_execution_symbol_allowlist": symbol_scope,
                "state25_execution_entry_stage_allowlist": entry_stage_scope,
                "state25_weight_log_only_enabled": not bounded_live_enabled,
                "state25_weight_bounded_live_enabled": bool(bounded_live_enabled),
                "state25_teacher_weight_overrides": merged_overrides,
            },
        }
        _write_json(self._active_candidate_state_path, state_payload)

        artifact = {
            "contract_version": STATE25_WEIGHT_PATCH_APPLY_HANDLERS_CONTRACT_VERSION,
            "generated_at": applied_at,
            "apply_state": apply_state,
            "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
            "candidate_id": candidate_id,
            "binding_mode": binding_mode or "log_only",
            "rollout_phase": rollout_phase,
            "symbol_scope": symbol_scope,
            "entry_stage_scope": entry_stage_scope,
            "teacher_weight_overrides": merged_overrides,
            "teacher_weight_override_display_ko": render_state25_teacher_weight_override_lines_ko(
                merged_overrides,
                baseline_overrides=_mapping(existing_patch.get("state25_teacher_weight_overrides")),
            ),
            "approval_id": _to_text(event_payload.get("approval_id")),
            "scope_key": _to_text(event_payload.get("scope_key"), _to_text(_mapping(group).get("scope_key"))),
            "active_candidate_state_path": str(self._active_candidate_state_path),
        }
        json_path = self._shadow_auto_dir / "checkpoint_state25_weight_patch_apply_latest.json"
        md_path = self._shadow_auto_dir / "checkpoint_state25_weight_patch_apply_latest.md"
        _write_json(json_path, artifact)
        _write_text(md_path, _render_markdown(artifact))
        return {
            "summary": {
                "contract_version": STATE25_WEIGHT_PATCH_APPLY_HANDLERS_CONTRACT_VERSION,
                "generated_at": applied_at,
                "apply_state": apply_state,
                "recommended_next_action": (
                    "collect_state25_bounded_live_weight_patch_evidence"
                    if bounded_live_enabled
                    else "collect_state25_log_only_weight_patch_evidence"
                ),
                "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
                "candidate_id": candidate_id,
            },
            "artifact_paths": {
                "active_candidate_state_path": str(self._active_candidate_state_path),
                "apply_report_path": str(json_path),
                "apply_markdown_path": str(md_path),
            },
            "apply_report": artifact,
            "active_candidate_state": state_payload,
        }


def register_default_state25_weight_patch_apply_handlers(
    apply_executor: ApplyExecutor,
    *,
    active_candidate_state_path: str | Path | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> State25WeightPatchApplyHandlerSet:
    handler_set = State25WeightPatchApplyHandlerSet(
        active_candidate_state_path=active_candidate_state_path,
        shadow_auto_dir=shadow_auto_dir,
    )
    handler_set.register_into(apply_executor)
    return handler_set
