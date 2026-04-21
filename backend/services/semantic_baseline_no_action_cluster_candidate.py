from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.services.semantic_baseline_no_action_sample_audit import (
    default_semantic_baseline_no_action_sample_audit_json_path,
)


SEMANTIC_BASELINE_NO_ACTION_CLUSTER_CANDIDATE_VERSION = (
    "semantic_baseline_no_action_cluster_candidate_v1"
)

SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY = (
    "misread:semantic_baseline_no_action_cluster"
)

SEMANTIC_CONTINUATION_GAP_PRIMARY_REGISTRY_KEY = (
    "misread:semantic_continuation_gap_cluster"
)

_CONTINUATION_GAP_OBSERVE_REASONS = {
    "upper_break_fail_confirm",
    "upper_reclaim_strength_confirm",
}


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_cluster_key(cluster_key: str) -> dict[str, str]:
    parts = [part.strip() for part in cluster_key.split("|")]
    while len(parts) < 4:
        parts.append("")
    return {
        "symbol": _text(parts[0]).upper(),
        "observe_reason": _text(parts[1]),
        "blocked_by": _text(parts[2]),
        "action_none_reason": _text(parts[3]),
    }


def _cluster_priority_score(
    *,
    cluster_count: int,
    share: float,
    symbol_share: float,
    unavailable_share: float,
) -> float:
    score = 0.0
    score += min(50.0, float(cluster_count) * 2.0)
    score += min(35.0, max(share, symbol_share) * 50.0)
    score += min(15.0, unavailable_share * 15.0)
    return round(score, 1)


def _cluster_confidence(
    *,
    cluster_count: int,
    share: float,
    symbol_share: float,
    unavailable_share: float,
) -> float:
    confidence = 0.35
    confidence += min(0.20, float(cluster_count) / 50.0)
    confidence += min(0.25, max(share, symbol_share) * 0.35)
    confidence += min(0.10, unavailable_share * 0.10)
    return round(min(confidence, 0.92), 2)


def _build_cluster_interpretation(
    *,
    symbol: str,
    observe_reason: str,
    blocked_by: str,
    action_none_reason: str,
    baseline_no_action_count: int,
    symbol_baseline_count: int,
    cluster_count: int,
    cluster_share: float,
    symbol_share: float,
) -> dict[str, Any]:
    if observe_reason in _CONTINUATION_GAP_OBSERVE_REASONS:
        return {
            "summary_ko": f"{symbol} 상승 지속 누락 가능성 관찰",
            "why_now_ko": (
                f"최근 {symbol} baseline_no_action {symbol_baseline_count}건 중 "
                f"{cluster_count}건({symbol_share * 100.0:.1f}%)이 "
                f"`{observe_reason}` / `{blocked_by}` / `{action_none_reason}` 군집으로 반복돼, "
                "계속 올라갈 수 있는 장면이 observe/blocked로만 흘렀을 가능성이 있습니다."
            ),
            "recommended_action_ko": (
                "상승 지속 가능성을 바로 live 완화로 넘기지 말고, detector/propose에서 자동 관찰을 누적한 뒤 "
                "feedback이 쌓이면 bounded review 후보로 올립니다."
            ),
            "pattern_code": "continuation_gap",
            "pattern_label_ko": "상승 지속 누락",
            "primary_registry_key_override": SEMANTIC_CONTINUATION_GAP_PRIMARY_REGISTRY_KEY,
            "extra_evidence_registry_keys": [
                SEMANTIC_CONTINUATION_GAP_PRIMARY_REGISTRY_KEY,
                SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
            ],
            "evidence_lines_ko": [
                "- 추세 힌트: 계속 올라갈 가능성 누락 관찰",
                f"- symbol_cluster_share: {symbol_share * 100.0:.1f}%",
                f"- global_cluster_share: {cluster_share * 100.0:.1f}%",
                f"- baseline_no_action_total: {baseline_no_action_count}",
            ],
        }

    return {
        "summary_ko": f"{symbol} baseline no-action observe cluster 관찰",
        "why_now_ko": (
            f"최근 baseline_no_action {baseline_no_action_count}건 중 {cluster_count}건({cluster_share * 100.0:.1f}%)이 "
            f"`{observe_reason}` / `{blocked_by}` / `{action_none_reason}` 군집으로 반복됩니다."
        ),
        "recommended_action_ko": (
            "semantic threshold를 바로 완화하지 말고, detector feedback과 bounded proposal 후보로 먼저 관찰합니다."
        ),
        "pattern_code": "generic_observe_cluster",
        "pattern_label_ko": "baseline no-action 군집",
        "primary_registry_key_override": SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
        "extra_evidence_registry_keys": [SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY],
        "evidence_lines_ko": [
            f"- symbol_cluster_share: {symbol_share * 100.0:.1f}%",
            f"- global_cluster_share: {cluster_share * 100.0:.1f}%",
            f"- baseline_no_action_total: {baseline_no_action_count}",
        ],
    }


def build_semantic_baseline_no_action_cluster_candidates(
    *,
    sample_audit_payload: Mapping[str, Any] | None = None,
    minimum_cluster_count: int = 5,
    minimum_cluster_share: float = 0.25,
    minimum_symbol_cluster_share: float = 0.40,
) -> list[dict[str, Any]]:
    payload = _mapping(sample_audit_payload) or _load_json(
        default_semantic_baseline_no_action_sample_audit_json_path()
    )
    summary = _mapping(payload.get("summary"))
    cluster_counts = {
        _text(key): _to_int(value)
        for key, value in _mapping(summary.get("cluster_counts")).items()
        if _text(key) and _to_int(value) > 0
    }
    baseline_no_action_count = max(1, _to_int(summary.get("baseline_no_action_count"), 0))
    symbol_counts = {
        _text(key).upper(): _to_int(value)
        for key, value in _mapping(summary.get("symbol_counts")).items()
        if _text(key)
    }
    quality_counts = {
        _text(key): _to_int(value)
        for key, value in _mapping(summary.get("semantic_shadow_trace_quality_counts")).items()
        if _text(key)
    }
    unavailable_count = sum(
        count for key, count in quality_counts.items() if key.lower() in {"unavailable", "missing", "degraded"}
    )
    unavailable_share = float(unavailable_count) / float(max(1, baseline_no_action_count))

    rows: list[dict[str, Any]] = []
    for cluster_key, cluster_count in sorted(cluster_counts.items(), key=lambda item: (-item[1], item[0])):
        cluster_share = float(cluster_count) / float(max(1, baseline_no_action_count))
        parsed = _parse_cluster_key(cluster_key)
        symbol = _text(parsed.get("symbol")).upper() or "ALL"
        symbol_baseline_count = max(1, _to_int(symbol_counts.get(symbol), 0) or baseline_no_action_count)
        symbol_share = float(cluster_count) / float(max(1, symbol_baseline_count))
        if cluster_count < int(minimum_cluster_count):
            continue
        if cluster_share < float(minimum_cluster_share) and symbol_share < float(minimum_symbol_cluster_share):
            continue

        priority_score = _cluster_priority_score(
            cluster_count=cluster_count,
            share=cluster_share,
            symbol_share=symbol_share,
            unavailable_share=unavailable_share,
        )
        misread_confidence = _cluster_confidence(
            cluster_count=cluster_count,
            share=cluster_share,
            symbol_share=symbol_share,
            unavailable_share=unavailable_share,
        )
        observe_reason = _text(parsed.get("observe_reason"))
        blocked_by = _text(parsed.get("blocked_by"))
        action_none_reason = _text(parsed.get("action_none_reason"))
        interpretation = _build_cluster_interpretation(
            symbol=symbol,
            observe_reason=observe_reason,
            blocked_by=blocked_by,
            action_none_reason=action_none_reason,
            baseline_no_action_count=baseline_no_action_count,
            symbol_baseline_count=symbol_baseline_count,
            cluster_count=cluster_count,
            cluster_share=cluster_share,
            symbol_share=symbol_share,
        )
        primary_registry_key = _text(
            interpretation.get("primary_registry_key_override"),
            SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
        )
        rows.append(
            {
                "contract_version": SEMANTIC_BASELINE_NO_ACTION_CLUSTER_CANDIDATE_VERSION,
                "candidate_key": cluster_key,
                "symbol": symbol,
                "observe_reason": observe_reason,
                "blocked_by": blocked_by,
                "action_none_reason": action_none_reason,
                "baseline_no_action_count": baseline_no_action_count,
                "symbol_baseline_count": symbol_baseline_count,
                "cluster_count": cluster_count,
                "cluster_share": round(cluster_share, 4),
                "cluster_symbol_share": round(symbol_share, 4),
                "semantic_shadow_trace_quality": "unavailable",
                "semantic_shadow_unavailable_share": round(unavailable_share, 4),
                "summary_ko": _text(interpretation.get("summary_ko")),
                "why_now_ko": _text(interpretation.get("why_now_ko")),
                "recommended_action_ko": _text(interpretation.get("recommended_action_ko")),
                "cluster_pattern_code": _text(interpretation.get("pattern_code")),
                "cluster_pattern_label_ko": _text(interpretation.get("pattern_label_ko")),
                "evidence_lines_ko": [
                    *list(interpretation.get("evidence_lines_ko") or []),
                    f"- observe_reason: {observe_reason or '-'}",
                    f"- blocked_by: {blocked_by or '-'}",
                    f"- action_none_reason: {action_none_reason or '-'}",
                    f"- cluster_count: {cluster_count}",
                    "- semantic_shadow_trace_quality: unavailable",
                ],
                "registry_key": primary_registry_key,
                "extra_evidence_registry_keys": list(
                    interpretation.get("extra_evidence_registry_keys")
                    or [SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY]
                ),
                "primary_registry_key_override": primary_registry_key,
                "result_type": "result_unresolved",
                "explanation_type": "explanation_gap",
                "misread_confidence": misread_confidence,
                "priority_score": priority_score,
                "detector_binding_mode": "derived",
            }
        )

    return rows
