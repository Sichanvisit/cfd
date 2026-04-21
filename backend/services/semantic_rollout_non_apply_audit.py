from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SEMANTIC_ROLLOUT_NON_APPLY_AUDIT_CONTRACT_VERSION = "semantic_rollout_non_apply_audit_v1"

PROMOTION_REASON_LABELS_KO = {
    "rollout_disabled": "semantic rollout이 아직 disabled 상태임",
    "shadow_runtime_unavailable": "shadow runtime이 active 상태가 아님",
    "baseline_no_action_dominant": "baseline 자체가 no-action이 많아 semantic 후보가 생기지 않음",
    "semantic_unavailable_dominant": "semantic feature/trace가 충분히 붙지 않아 후보가 생기지 않음",
    "symbol_not_in_allowlist_dominant": "symbol allowlist 제한으로 rollout 후보가 막힘",
    "no_eligible_rows": "최근 row는 있지만 eligible row가 0건임",
    "no_counterfactual_apply_cases": "counterfactual 상에서도 threshold/partial-live 적용 사례가 없음",
    "promotion_not_blocked": "promotion 관점 blocker는 크지 않음",
}

ACTIVATION_REASON_LABELS_KO = {
    "approval_pending": "bounded candidate 승인 전 상태임",
    "runtime_not_idle_pending_activation": "승인된 candidate는 있으나 runtime이 idle이 아니어서 activation을 미룸",
    "approved_bundle_missing": "승인된 bundle이 없어 activation을 진행할 수 없음",
    "activation_not_started": "activation이 아직 시작되지 않음",
    "activation_completed": "candidate activation은 완료됨",
}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_semantic_rollout_non_apply_audit_json_path() -> Path:
    return _shadow_auto_dir() / "semantic_rollout_non_apply_audit_latest.json"


def default_semantic_rollout_non_apply_audit_markdown_path() -> Path:
    return _shadow_auto_dir() / "semantic_rollout_non_apply_audit_latest.md"


def _default_artifact_path(name: str) -> Path:
    return _shadow_auto_dir() / name


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _first_row(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    body = _mapping(payload)
    rows = list(body.get("rows", []) or [])
    return _mapping(rows[0]) if rows else {}


def _json_mapping(value: object) -> dict[str, int]:
    if isinstance(value, Mapping):
        return {str(key): _to_int(val) for key, val in value.items()}
    text = _text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    if not isinstance(parsed, Mapping):
        return {}
    return {str(key): _to_int(val) for key, val in parsed.items()}


def _dominant_reason(reason_counts: Mapping[str, int]) -> str:
    if not reason_counts:
        return ""
    return sorted(
        ((str(key), _to_int(value)) for key, value in reason_counts.items()),
        key=lambda item: (-item[1], item[0]),
    )[0][0]


def _promotion_reason_code(observation_row: Mapping[str, Any]) -> str:
    rollout_mode = _text(observation_row.get("rollout_mode")).lower()
    shadow_loaded = _to_bool(observation_row.get("shadow_loaded"))
    shadow_runtime_state = _text(observation_row.get("shadow_runtime_state")).lower()
    recent_row_count = _to_int(observation_row.get("recent_row_count"))
    threshold_eligible = _to_int(observation_row.get("recent_threshold_eligible_count"))
    partial_eligible = _to_int(observation_row.get("recent_partial_live_eligible_count"))
    threshold_would_apply = _to_int(observation_row.get("recent_threshold_would_apply_count"))
    partial_would_apply = _to_int(observation_row.get("recent_partial_live_would_apply_count"))
    fallback_reason_counts = _json_mapping(observation_row.get("recent_fallback_reason_counts"))
    dominant_fallback = _dominant_reason(fallback_reason_counts)

    if rollout_mode == "disabled":
        return "rollout_disabled"
    if not shadow_loaded or shadow_runtime_state != "active":
        return "shadow_runtime_unavailable"
    if recent_row_count > 0 and threshold_eligible <= 0 and partial_eligible <= 0:
        if dominant_fallback == "baseline_no_action":
            return "baseline_no_action_dominant"
        if dominant_fallback == "semantic_unavailable":
            return "semantic_unavailable_dominant"
        if dominant_fallback == "symbol_not_in_allowlist":
            return "symbol_not_in_allowlist_dominant"
        return "no_eligible_rows"
    if recent_row_count > 0 and threshold_would_apply <= 0 and partial_would_apply <= 0:
        return "no_counterfactual_apply_cases"
    return "promotion_not_blocked"


def _activation_reason_code(approval_row: Mapping[str, Any], activation_row: Mapping[str, Any]) -> str:
    approval_status = _text(approval_row.get("approval_status"))
    activation_status = _text(activation_row.get("activation_status"))
    if approval_status != "approved_pending_activation":
        return "approval_pending"
    if activation_status == "blocked_runtime_not_idle":
        return "runtime_not_idle_pending_activation"
    if activation_status == "approved_bundle_missing":
        return "approved_bundle_missing"
    if activation_status.startswith("activated_candidate_runtime"):
        return "activation_completed"
    return "activation_not_started"


def build_semantic_rollout_non_apply_audit(
    *,
    observation_payload: Mapping[str, Any] | None = None,
    observation_json_path: str | Path | None = None,
    readiness_payload: Mapping[str, Any] | None = None,
    readiness_json_path: str | Path | None = None,
    stage_payload: Mapping[str, Any] | None = None,
    stage_json_path: str | Path | None = None,
    approval_payload: Mapping[str, Any] | None = None,
    approval_json_path: str | Path | None = None,
    activation_payload: Mapping[str, Any] | None = None,
    activation_json_path: str | Path | None = None,
) -> dict[str, Any]:
    observation = (
        _mapping(observation_payload)
        if observation_payload is not None
        else _load_json(
            observation_json_path
            or _default_artifact_path("semantic_live_rollout_observation_latest.json")
        )
    )
    readiness = (
        _mapping(readiness_payload)
        if readiness_payload is not None
        else _load_json(
            readiness_json_path
            or _default_artifact_path("semantic_shadow_active_runtime_readiness_latest.json")
        )
    )
    stage = (
        _mapping(stage_payload)
        if stage_payload is not None
        else _load_json(
            stage_json_path
            or _default_artifact_path("semantic_shadow_bounded_candidate_stage_latest.json")
        )
    )
    approval = (
        _mapping(approval_payload)
        if approval_payload is not None
        else _load_json(
            approval_json_path
            or _default_artifact_path("semantic_shadow_bounded_candidate_approval_latest.json")
        )
    )
    activation = (
        _mapping(activation_payload)
        if activation_payload is not None
        else _load_json(
            activation_json_path
            or _default_artifact_path("semantic_shadow_active_runtime_activation_latest.json")
        )
    )

    observation_row = _first_row(observation)
    readiness_row = _first_row(readiness)
    stage_row = _first_row(stage)
    approval_row = _first_row(approval)
    activation_row = _first_row(activation)

    fallback_reason_counts = _json_mapping(observation_row.get("recent_fallback_reason_counts"))
    dominant_fallback_reason = _dominant_reason(fallback_reason_counts)
    promotion_reason_code = _promotion_reason_code(observation_row)
    activation_reason_code = _activation_reason_code(approval_row, activation_row)

    rows = [
        {
            "lane": "promotion_counterfactual",
            "lane_label_ko": "semantic promotion 관찰 lane",
            "state": _text(observation_row.get("rollout_promotion_readiness")),
            "blocking": promotion_reason_code != "promotion_not_blocked",
            "non_apply_reason_code": promotion_reason_code,
            "non_apply_reason_ko": PROMOTION_REASON_LABELS_KO.get(promotion_reason_code, promotion_reason_code),
            "recommended_next_action": _text(observation_row.get("recommended_next_action")),
            "recent_row_count": _to_int(observation_row.get("recent_row_count")),
            "recent_shadow_available_count": _to_int(observation_row.get("recent_shadow_available_count")),
            "recent_threshold_eligible_count": _to_int(observation_row.get("recent_threshold_eligible_count")),
            "recent_partial_live_eligible_count": _to_int(observation_row.get("recent_partial_live_eligible_count")),
            "dominant_fallback_reason": dominant_fallback_reason,
            "fallback_reason_counts": fallback_reason_counts,
        },
        {
            "lane": "runtime_readiness",
            "lane_label_ko": "semantic runtime readiness lane",
            "state": _text(readiness_row.get("active_runtime_state")),
            "blocking": not _to_bool(readiness_row.get("activation_ready_flag")),
            "non_apply_reason_code": _text(readiness_row.get("activation_block_reason")) or "none",
            "non_apply_reason_ko": _text(readiness_row.get("activation_block_reason")) or "candidate stage 준비 자체는 완료됨",
            "recommended_next_action": _text(readiness_row.get("recommended_next_action")),
            "bounded_gate_decision": _text(readiness_row.get("bounded_gate_decision")),
            "activation_ready_flag": _to_bool(readiness_row.get("activation_ready_flag")),
        },
        {
            "lane": "candidate_stage",
            "lane_label_ko": "bounded candidate stage lane",
            "state": _text(stage_row.get("stage_status")),
            "blocking": _text(stage_row.get("stage_status")) != "candidate_runtime_staged",
            "non_apply_reason_code": _text(stage_row.get("stage_status")) or "stage_unknown",
            "non_apply_reason_ko": "bounded candidate가 아직 stage에 못 올라감"
            if _text(stage_row.get("stage_status")) != "candidate_runtime_staged"
            else "bounded candidate stage는 이미 완료됨",
            "recommended_next_action": _text(stage_row.get("recommended_next_action")),
            "approval_required": _to_bool(stage_row.get("approval_required")),
            "staged_file_count": _to_int(stage_row.get("staged_file_count")),
        },
        {
            "lane": "approval",
            "lane_label_ko": "bounded candidate approval lane",
            "state": _text(approval_row.get("approval_status")),
            "blocking": _text(approval_row.get("approval_status")) != "approved_pending_activation",
            "non_apply_reason_code": _text(approval_row.get("approval_status")) or "approval_unknown",
            "non_apply_reason_ko": "사람 승인 대기 또는 승인 미완료"
            if _text(approval_row.get("approval_status")) != "approved_pending_activation"
            else "승인은 완료됐고 activation 대기 상태임",
            "recommended_next_action": _text(approval_row.get("recommended_next_action")),
            "approval_decision": _text(approval_row.get("approval_decision")),
        },
        {
            "lane": "runtime_activation",
            "lane_label_ko": "approved candidate activation lane",
            "state": _text(activation_row.get("activation_status")),
            "blocking": activation_reason_code != "activation_completed",
            "non_apply_reason_code": activation_reason_code,
            "non_apply_reason_ko": ACTIVATION_REASON_LABELS_KO.get(activation_reason_code, activation_reason_code),
            "recommended_next_action": _text(activation_row.get("recommended_next_action")),
            "runtime_idle_flag": _to_bool(activation_row.get("runtime_idle_flag")),
            "open_positions_count": _to_int(activation_row.get("open_positions_count")),
        },
    ]

    recommended_next_action = _text(_mapping(rows[-1]).get("recommended_next_action"))
    if activation_reason_code == "runtime_not_idle_pending_activation":
        recommended_next_action = "wait_for_runtime_idle_then_retry_activation"
    elif promotion_reason_code != "promotion_not_blocked":
        recommended_next_action = _text(observation_row.get("recommended_next_action"))

    return {
        "summary": {
            "contract_version": SEMANTIC_ROLLOUT_NON_APPLY_AUDIT_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "promotion_lane_state": _text(observation_row.get("rollout_promotion_readiness")),
            "promotion_non_apply_reason_code": promotion_reason_code,
            "promotion_non_apply_reason_ko": PROMOTION_REASON_LABELS_KO.get(promotion_reason_code, promotion_reason_code),
            "activation_lane_state": _text(activation_row.get("activation_status")),
            "activation_non_apply_reason_code": activation_reason_code,
            "activation_non_apply_reason_ko": ACTIVATION_REASON_LABELS_KO.get(activation_reason_code, activation_reason_code),
            "dominant_recent_fallback_reason": dominant_fallback_reason,
            "recent_row_count": _to_int(observation_row.get("recent_row_count")),
            "recent_shadow_available_count": _to_int(observation_row.get("recent_shadow_available_count")),
            "recent_threshold_eligible_count": _to_int(observation_row.get("recent_threshold_eligible_count")),
            "recent_partial_live_eligible_count": _to_int(observation_row.get("recent_partial_live_eligible_count")),
            "blocking_lane_count": sum(1 for row in rows if bool(row.get("blocking"))),
            "recommended_next_action": recommended_next_action,
        },
        "rows": rows,
    }


def render_semantic_rollout_non_apply_audit_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines = [
        "# Semantic Rollout Non-Apply Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- promotion_non_apply_reason: `{_text(summary.get('promotion_non_apply_reason_ko'))}`",
        f"- activation_non_apply_reason: `{_text(summary.get('activation_non_apply_reason_ko'))}`",
        f"- dominant_recent_fallback_reason: `{_text(summary.get('dominant_recent_fallback_reason'))}`",
        f"- recent_row_count: `{_to_int(summary.get('recent_row_count'))}`",
        f"- recent_shadow_available_count: `{_to_int(summary.get('recent_shadow_available_count'))}`",
        f"- recent_threshold_eligible_count: `{_to_int(summary.get('recent_threshold_eligible_count'))}`",
        f"- recent_partial_live_eligible_count: `{_to_int(summary.get('recent_partial_live_eligible_count'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
        "## Lanes",
        "",
    ]
    for raw_row in rows:
        row = _mapping(raw_row)
        lines.extend(
            [
                f"### {_text(row.get('lane_label_ko'), '-')}",
                "",
                f"- state: `{_text(row.get('state'))}`",
                f"- blocking: `{bool(row.get('blocking'))}`",
                f"- non_apply_reason: `{_text(row.get('non_apply_reason_ko'))}`",
                f"- recommended_next_action: `{_text(row.get('recommended_next_action'))}`",
            ]
        )
        if _text(row.get("lane")) == "promotion_counterfactual":
            lines.extend(
                [
                    f"- recent_row_count: `{_to_int(row.get('recent_row_count'))}`",
                    f"- recent_shadow_available_count: `{_to_int(row.get('recent_shadow_available_count'))}`",
                    f"- dominant_fallback_reason: `{_text(row.get('dominant_fallback_reason'))}`",
                    f"- fallback_reason_counts: `{json.dumps(_mapping(row.get('fallback_reason_counts')), ensure_ascii=False, sort_keys=True)}`",
                ]
            )
        if _text(row.get("lane")) == "runtime_activation":
            lines.extend(
                [
                    f"- runtime_idle_flag: `{_to_bool(row.get('runtime_idle_flag'))}`",
                    f"- open_positions_count: `{_to_int(row.get('open_positions_count'))}`",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_semantic_rollout_non_apply_audit_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    _write_json(
        json_output_path or default_semantic_rollout_non_apply_audit_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_semantic_rollout_non_apply_audit_markdown_path(),
        render_semantic_rollout_non_apply_audit_markdown(payload),
    )
