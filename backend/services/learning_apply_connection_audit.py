from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.learning_parameter_registry import (
    LEARNING_PARAMETER_REGISTRY_CONTRACT_VERSION,
    build_learning_parameter_registry,
)
from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_VERSION,
    build_learning_registry_direct_binding_plan,
)
from backend.services.teacher_pattern_active_candidate_runtime import (
    STATE25_TEACHER_WEIGHT_CATALOG,
)


LEARNING_APPLY_CONNECTION_AUDIT_CONTRACT_VERSION = "learning_apply_connection_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check(status: str, code: str, message_ko: str, **extra: Any) -> dict[str, Any]:
    payload = {"status": status, "code": code, "message_ko": message_ko}
    payload.update(extra)
    return payload


def _status_rank(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(str(status).upper(), 2)


def _overall_status(checks: list[dict[str, Any]]) -> str:
    if any(_status_rank(row.get("status")) >= 2 for row in checks):
        return "FAIL"
    if any(_status_rank(row.get("status")) == 1 for row in checks):
        return "WARN"
    return "PASS"


def build_learning_apply_connection_audit() -> dict[str, Any]:
    repo_root = _repo_root()
    registry_payload = build_learning_parameter_registry()
    registry_rows = list(registry_payload.get("rows", []) or [])
    registry_keys = {str(row.get("registry_key")) for row in registry_rows}
    direct_binding_plan = build_learning_registry_direct_binding_plan(registry_payload)
    planned_target_registry_keys = set(
        str(key) for key in list(direct_binding_plan.get("all_target_registry_keys") or [])
    )

    detector_path = repo_root / "backend" / "services" / "improvement_log_only_detector.py"
    weight_review_path = repo_root / "backend" / "services" / "state25_weight_patch_review.py"
    feedback_path = repo_root / "backend" / "services" / "trade_feedback_runtime.py"
    forecast_path = repo_root / "backend" / "services" / "forecast_state25_runtime_bridge.py"
    approval_bridge_path = repo_root / "backend" / "services" / "telegram_approval_bridge.py"
    apply_handler_path = repo_root / "backend" / "services" / "state25_weight_patch_apply_handlers.py"

    detector_source = _read_text(detector_path)
    weight_review_source = _read_text(weight_review_path)
    feedback_source = _read_text(feedback_path)
    forecast_source = _read_text(forecast_path)
    approval_bridge_source = _read_text(approval_bridge_path)
    apply_handler_source = _read_text(apply_handler_path)

    expected_state25_registry_keys = {
        f"state25_weight:{key}" for key in STATE25_TEACHER_WEIGHT_CATALOG.keys()
    }
    missing_weight_registry_keys = sorted(expected_state25_registry_keys - registry_keys)

    detector_tokens = [
        "feedback_scope_key",
        "build_manual_trade_proposal_snapshot",
        "build_state25_weight_patch_review_candidate_v1",
        "proposal_envelope",
        "hindsight_status",
        "result_type",
        "explanation_type",
    ]
    missing_detector_tokens = [
        token for token in detector_tokens if token not in detector_source
    ]

    feedback_tokens = [
        "build_detector_confusion_snapshot",
        "FAST_PROMOTION_MIN_FEEDBACK",
        "FAST_PROMOTION_MIN_POSITIVE_RATIO",
        "FAST_PROMOTION_MIN_TRADE_DAYS",
        "FAST_PROMOTION_MIN_MISREAD_CONFIDENCE",
        "proposal_envelope",
    ]
    missing_feedback_tokens = [
        token for token in feedback_tokens if token not in feedback_source
    ]

    approval_tokens = [
        "ensure_improvement_proposal_envelope",
        "STATE25_WEIGHT_PATCH_REVIEW",
        "ApplyExecutor",
        "proposal_envelope",
    ]
    missing_approval_tokens = [
        token for token in approval_tokens if token not in approval_bridge_source
    ]

    apply_tokens = [
        "STATE25_WEIGHT_PATCH_REVIEW",
        "state25_teacher_weight_overrides",
        "active_candidate_state.json",
        "STATE25_WEIGHT_PATCH_LOG_ONLY_ACTIVE",
    ]
    missing_apply_tokens = [
        token for token in apply_tokens if token not in apply_handler_source
    ]

    planned_binding_missing_keys = sorted(planned_target_registry_keys - registry_keys)

    detector_direct_binding = "learning_registry_resolver" in detector_source
    weight_review_direct_binding = "learning_registry_resolver" in weight_review_source
    feedback_direct_binding = "learning_registry_resolver" in feedback_source
    forecast_direct_binding = "learning_registry_resolver" in forecast_source
    bound_runtime_service_files = [
        service_name
        for service_name, is_bound in (
            (detector_path.name, detector_direct_binding),
            (weight_review_path.name, weight_review_direct_binding),
            (feedback_path.name, feedback_direct_binding),
            (forecast_path.name, forecast_direct_binding),
        )
        if is_bound
    ]
    fully_bound_runtime = all(
        (
            detector_direct_binding,
            weight_review_direct_binding,
            feedback_direct_binding,
            forecast_direct_binding,
        )
    )

    bound_target_registry_keys: set[str] = set()
    stages = dict(direct_binding_plan.get("stages") or {})
    if detector_direct_binding:
        bound_target_registry_keys.update(
            str(key) for key in list(dict(stages.get("detector") or {}).get("target_registry_keys") or [])
        )
    if weight_review_direct_binding:
        bound_target_registry_keys.update(
            str(key) for key in list(dict(stages.get("weight_review") or {}).get("target_registry_keys") or [])
        )
    if feedback_direct_binding:
        bound_target_registry_keys.update(
            str(key) for key in list(dict(stages.get("proposal_runtime") or {}).get("target_registry_keys") or [])
        )
    if forecast_direct_binding:
        bound_target_registry_keys.update(
            str(key) for key in list(dict(stages.get("forecast_report") or {}).get("target_registry_keys") or [])
        )

    target_key_count = len(planned_target_registry_keys)
    bound_key_count = len(bound_target_registry_keys)
    unbound_key_count = max(0, target_key_count - bound_key_count)
    binding_rate_pct = round((float(bound_key_count) / float(max(1, target_key_count))) * 100.0, 1)

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "PASS" if int(registry_payload.get("row_count", 0)) > 0 else "FAIL",
            "registry_snapshot_present",
            "중앙 학습 변수 레지스트리가 생성되어 있습니다."
            if int(registry_payload.get("row_count", 0)) > 0
            else "중앙 학습 변수 레지스트리가 비어 있습니다.",
            row_count=int(registry_payload.get("row_count", 0)),
            contract_version=LEARNING_PARAMETER_REGISTRY_CONTRACT_VERSION,
        )
    )
    checks.append(
        _check(
            "PASS" if not missing_weight_registry_keys else "FAIL",
            "state25_weight_registry_coverage",
            "state25 teacher 가중치 항목이 중앙 레지스트리에 모두 등록되어 있습니다."
            if not missing_weight_registry_keys
            else "state25 teacher 가중치 항목 중 중앙 레지스트리에 빠진 항목이 있습니다.",
            missing_keys=missing_weight_registry_keys,
        )
    )
    checks.append(
        _check(
            "PASS" if not missing_detector_tokens else "FAIL",
            "detector_to_propose_connection",
            "detector가 feedback/proposal/state25 preview/hindsight 축과 연결되어 있습니다."
            if not missing_detector_tokens
            else "detector에서 feedback/proposal/hindsight 연결 토큰 일부가 누락되어 있습니다.",
            missing_tokens=missing_detector_tokens,
        )
    )
    checks.append(
        _check(
            "PASS" if not missing_feedback_tokens else "FAIL",
            "feedback_promotion_connection",
            "feedback confusion, fast promotion, proposal envelope 연결이 확인됩니다."
            if not missing_feedback_tokens
            else "feedback promotion 연결 토큰 일부가 누락되어 있습니다.",
            missing_tokens=missing_feedback_tokens,
        )
    )
    checks.append(
        _check(
            "PASS" if not missing_approval_tokens else "FAIL",
            "review_bridge_connection",
            "approval bridge가 proposal envelope와 apply executor에 연결되어 있습니다."
            if not missing_approval_tokens
            else "approval bridge 연결 토큰 일부가 누락되어 있습니다.",
            missing_tokens=missing_approval_tokens,
        )
    )
    checks.append(
        _check(
            "PASS" if not missing_apply_tokens else "FAIL",
            "state25_apply_connection",
            "state25 weight patch review가 active candidate state 반영으로 이어집니다."
            if not missing_apply_tokens
            else "state25 apply handler 연결 토큰 일부가 누락되어 있습니다.",
            missing_tokens=missing_apply_tokens,
        )
    )
    checks.append(
        _check(
            "PASS" if not planned_binding_missing_keys else "FAIL",
            "planned_binding_registry_coverage",
            "직접 바인딩 계획에 포함된 key가 중앙 레지스트리에 모두 존재합니다."
            if not planned_binding_missing_keys
            else "직접 바인딩 계획 key 중 중앙 레지스트리에 빠진 항목이 있습니다.",
            missing_keys=planned_binding_missing_keys,
            binding_version=LEARNING_REGISTRY_BINDING_VERSION,
        )
    )
    checks.append(
        _check(
            "PASS" if fully_bound_runtime else "WARN",
            "registry_direct_runtime_binding",
            "중앙 레지스트리 직접 바인딩이 detector/weight review/feedback/forecast 전 구간에 연결되어 있습니다."
            if fully_bound_runtime
            else "중앙 레지스트리 직접 바인딩은 일부 runtime 서비스에만 연결되어 있으며, 남은 구간은 단계적으로 수렴 중입니다.",
            bound_service_files=bound_runtime_service_files,
        )
    )

    overall = _overall_status(checks)
    return {
        "contract_version": LEARNING_APPLY_CONNECTION_AUDIT_CONTRACT_VERSION,
        "registry_contract_version": LEARNING_PARAMETER_REGISTRY_CONTRACT_VERSION,
        "overall_status": overall,
        "checks": checks,
        "summary": {
            "registry_row_count": int(registry_payload.get("row_count", 0)),
            "state25_weight_count": len(STATE25_TEACHER_WEIGHT_CATALOG),
            "direct_registry_binding_count": len(bound_runtime_service_files),
            "binding_progress": {
                "binding_version": LEARNING_REGISTRY_BINDING_VERSION,
                "total_registry_keys": len(registry_keys),
                "direct_binding_target_key_count": target_key_count,
                "bound_target_key_count": bound_key_count,
                "unbound_target_key_count": unbound_key_count,
                "binding_rate_pct": binding_rate_pct,
                "detector_direct_binding": detector_direct_binding,
                "weight_review_direct_binding": weight_review_direct_binding,
                "feedback_direct_binding": feedback_direct_binding,
                "forecast_direct_binding": forecast_direct_binding,
            },
        },
        "artifact_paths": {
            "registry_json_path": str(_shadow_auto_dir() / "learning_parameter_registry_latest.json"),
            "registry_markdown_path": str(_shadow_auto_dir() / "learning_parameter_registry_latest.md"),
        },
        "direct_binding_plan": direct_binding_plan,
    }


def default_learning_apply_connection_audit_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "learning_apply_connection_audit_latest.json",
        directory / "learning_apply_connection_audit_latest.md",
    )


def render_learning_apply_connection_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Learning Apply Connection Audit",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        f"- overall_status: `{payload.get('overall_status', '-')}`",
        "",
        "## Summary",
    ]
    for key, value in dict(payload.get("summary", {}) or {}).items():
        if key == "binding_progress" and isinstance(value, dict):
            lines.append(f"- `{key}`:")
            for sub_key, sub_value in value.items():
                lines.append(f"  - `{sub_key}`: `{sub_value}`")
            continue
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Checks"])
    for row in list(payload.get("checks", []) or []):
        lines.append(
            f"- `{row.get('code', '-')}` | `{row.get('status', '-')}` | {row.get('message_ko', '-')}"
        )
        if row.get("missing_tokens"):
            lines.append(f"  missing_tokens: `{row.get('missing_tokens')}`")
        if row.get("missing_keys"):
            lines.append(f"  missing_keys: `{row.get('missing_keys')}`")
        if row.get("bound_service_files"):
            lines.append(f"  bound_service_files: `{row.get('bound_service_files')}`")
    plan = dict(payload.get("direct_binding_plan") or {})
    if plan:
        lines.extend(["", "## Direct Binding Plan"])
        for stage_key, stage_payload in dict(plan.get("stages", {}) or {}).items():
            stage_map = dict(stage_payload or {})
            lines.append(
                f"- `{stage_key}` | categories=`{stage_map.get('category_keys', [])}` | "
                f"target_key_count=`{stage_map.get('target_key_count', 0)}`"
            )
    return "\n".join(lines)


def write_learning_apply_connection_audit_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_learning_apply_connection_audit()
    default_json_path, default_markdown_path = default_learning_apply_connection_audit_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    resolved_markdown_path.write_text(render_learning_apply_connection_audit_markdown(payload), encoding="utf-8")
    return {
        "contract_version": payload["contract_version"],
        "overall_status": payload["overall_status"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
