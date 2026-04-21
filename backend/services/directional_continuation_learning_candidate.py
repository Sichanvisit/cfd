from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.services.semantic_baseline_no_action_cluster_candidate import (
    build_semantic_baseline_no_action_cluster_candidates,
)


DIRECTIONAL_CONTINUATION_LEARNING_CANDIDATE_VERSION = (
    "directional_continuation_learning_candidate_v1"
)

DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY = (
    "misread:directional_up_continuation_conflict"
)

DIRECTIONAL_CONTINUATION_DOWN_REGISTRY_KEY = (
    "misread:directional_down_continuation_conflict"
)

_SEMANTIC_CONTINUATION_PATTERN_CODE = "continuation_gap"

_MARKET_FAMILY_UP_OBSERVE_REASONS: dict[str, str] = {
    "upper_break_fail_confirm": "상단 돌파 유지",
    "upper_reclaim_strength_confirm": "상단 재회복 유지",
}

_MARKET_FAMILY_DOWN_OBSERVE_REASONS: dict[str, str] = {
    "upper_reject_confirm": "상단 거부 후 하락",
    "upper_reject_mixed_confirm": "상단 거부 혼조 후 하락",
    "upper_reject_probe_observe": "상단 거부 탐색",
    "upper_edge_observe": "상단 가장자리 약세",
    "btc_midline_sell_watch": "중단 저항 하락 감시",
    "conflict_box_upper_bb20_lower_lower_dominant_observe": "상단 충돌 후 하락 우세",
    "conflict_box_lower_bb20_upper_lower_dominant_observe": "하단 우세 충돌 관찰",
}

_SOURCE_PRIORITY = {
    "wrong_side_conflict_harvest": 0,
    "semantic_baseline_no_action_cluster": 1,
    "market_family_entry_audit": 2,
}


def _shadow_auto_dir() -> Path:
    return Path("data") / "analysis" / "shadow_auto"


def default_wrong_side_conflict_harvest_json_path() -> Path:
    return _shadow_auto_dir() / "wrong_side_conflict_harvest_latest.json"


def default_market_family_entry_audit_json_path() -> Path:
    return _shadow_auto_dir() / "market_family_entry_audit_latest.json"


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


def _json_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    text = _text(value)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _unique_text_list(values: list[object] | tuple[object, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = _text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _direction_from_continuation_label(value: object) -> str:
    label = _text(value).lower()
    if label == "missed_up_continuation":
        return "UP"
    if label == "missed_down_continuation":
        return "DOWN"
    return ""


def _direction_summary_ko(symbol: str, direction: str) -> str:
    if direction == "UP":
        return f"{symbol} 상승 지속 누락 가능성 관찰"
    if direction == "DOWN":
        return f"{symbol} 하락 지속 누락 가능성 관찰"
    return f"{symbol} 방향 지속 누락 가능성 관찰"


def _direction_hint_ko(direction: str) -> str:
    if direction == "UP":
        return "계속 올라가는 형태를 반대로 읽었을 가능성"
    if direction == "DOWN":
        return "계속 내려가는 형태를 반대로 읽었을 가능성"
    return "방향 지속 형태를 반대로 읽었을 가능성"


def _direction_observe_hint_line(direction: str) -> str:
    if direction == "UP":
        return "- 추세 힌트: 계속 올라갈 가능성 누락 관찰"
    if direction == "DOWN":
        return "- 추세 힌트: 계속 내려갈 가능성 누락 관찰"
    return "- 추세 힌트: 방향 지속 누락 관찰"


def _direction_pattern_label_ko(direction: str) -> str:
    if direction == "UP":
        return "상승 지속 누락"
    if direction == "DOWN":
        return "하락 지속 누락"
    return "방향 지속 누락"


def _direction_pattern_code(direction: str) -> str:
    if direction == "UP":
        return "continuation_gap_up"
    if direction == "DOWN":
        return "continuation_gap_down"
    return "continuation_gap_unknown"


def _direction_registry_key(direction: str) -> str:
    if direction == "UP":
        return DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY
    if direction == "DOWN":
        return DIRECTIONAL_CONTINUATION_DOWN_REGISTRY_KEY
    return ""


def _cluster_priority_score(
    *,
    repeat_count: int,
    symbol_share: float,
    global_share: float,
    bias_gap: float = 0.0,
) -> float:
    score = 0.0
    score += min(50.0, float(repeat_count) * 6.0)
    score += min(25.0, float(symbol_share) * 35.0)
    score += min(15.0, float(global_share) * 25.0)
    score += min(10.0, float(bias_gap) * 10.0)
    return round(score, 1)


def _cluster_confidence(
    *,
    repeat_count: int,
    symbol_share: float,
    global_share: float,
    bias_gap: float = 0.0,
) -> float:
    confidence = 0.35
    confidence += min(0.22, float(repeat_count) / 20.0)
    confidence += min(0.20, float(symbol_share) * 0.30)
    confidence += min(0.10, float(global_share) * 0.20)
    confidence += min(0.10, float(bias_gap) * 0.12)
    return round(min(confidence, 0.95), 2)


def _source_label_ko(source_kind: str) -> str:
    mapping = {
        "semantic_baseline_no_action_cluster": "semantic observe cluster",
        "wrong_side_conflict_harvest": "wrong-side conflict",
        "market_family_entry_audit": "market-family observe",
    }
    return _text(mapping.get(source_kind), source_kind or "-")


def _build_semantic_continuation_rows(
    semantic_cluster_candidates: list[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    source_rows = [
        _mapping(row)
        for row in list(
            semantic_cluster_candidates
            if semantic_cluster_candidates is not None
            else build_semantic_baseline_no_action_cluster_candidates()
        )
    ]
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        if _text(row.get("cluster_pattern_code")) != _SEMANTIC_CONTINUATION_PATTERN_CODE:
            continue
        symbol = _text(row.get("symbol")).upper() or "ALL"
        repeat_count = _to_int(row.get("cluster_count"))
        direction = "UP"
        rows.append(
            {
                "contract_version": DIRECTIONAL_CONTINUATION_LEARNING_CANDIDATE_VERSION,
                "candidate_key": f"semantic::{_text(row.get('candidate_key'))}",
                "source_kind": "semantic_baseline_no_action_cluster",
                "symbol": symbol,
                "continuation_direction": direction,
                "summary_ko": _text(row.get("summary_ko"), _direction_summary_ko(symbol, direction)),
                "why_now_ko": _text(row.get("why_now_ko")),
                "recommended_action_ko": _text(row.get("recommended_action_ko")),
                "evidence_lines_ko": list(row.get("evidence_lines_ko") or []),
                "repeat_count": repeat_count,
                "symbol_share": _to_float(row.get("cluster_symbol_share"), 0.0),
                "global_share": _to_float(row.get("cluster_share"), 0.0),
                "priority_score": _to_float(row.get("priority_score"), 0.0),
                "misread_confidence": _to_float(row.get("misread_confidence"), 0.0),
                "registry_key": _text(row.get("registry_key"), _direction_registry_key(direction)),
                "extra_evidence_registry_keys": _unique_text_list(
                    list(row.get("extra_evidence_registry_keys") or [])
                    + [_direction_registry_key(direction)]
                ),
                "pattern_code": _direction_pattern_code(direction),
                "pattern_label_ko": _direction_pattern_label_ko(direction),
                "primary_failure_label": "",
                "continuation_failure_label": "missed_up_continuation",
                "context_failure_label": "",
                "bridge_surface_family": "",
                "bridge_surface_state": "",
                "dominant_observe_reason": _text(row.get("observe_reason")),
                "source_kind_list": ["semantic_baseline_no_action_cluster"],
                "source_labels_ko": [_source_label_ko("semantic_baseline_no_action_cluster")],
            }
        )
    return rows


def _build_wrong_side_continuation_rows(
    wrong_side_conflict_payload: Mapping[str, Any] | None,
    *,
    minimum_repeat_count: int,
    minimum_symbol_share: float,
) -> list[dict[str, Any]]:
    payload = _mapping(wrong_side_conflict_payload) or _load_json(
        default_wrong_side_conflict_harvest_json_path()
    )
    source_rows = [_mapping(row) for row in list(payload.get("rows") or [])]
    filtered_rows = [
        row
        for row in source_rows
        if _direction_from_continuation_label(row.get("continuation_failure_label"))
    ]
    if not filtered_rows:
        return []

    symbol_totals: dict[str, int] = {}
    for row in filtered_rows:
        symbol = _text(row.get("symbol")).upper() or "ALL"
        symbol_totals[symbol] = symbol_totals.get(symbol, 0) + 1

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in filtered_rows:
        symbol = _text(row.get("symbol")).upper() or "ALL"
        continuation_label = _text(row.get("continuation_failure_label"))
        context_label = _text(row.get("context_failure_label"))
        primary_label = _text(row.get("primary_failure_label"))
        key = (symbol, continuation_label, context_label, primary_label)
        bucket = grouped.setdefault(
            key,
            {
                "symbol": symbol,
                "continuation_failure_label": continuation_label,
                "context_failure_label": context_label,
                "primary_failure_label": primary_label,
                "count": 0,
                "bias_gap_sum": 0.0,
                "bridge_surface_family_counts": {},
                "bridge_surface_state_counts": {},
            },
        )
        bucket["count"] += 1
        bucket["bias_gap_sum"] += _to_float(row.get("bias_gap"), 0.0)
        family = _text(row.get("bridge_surface_family"))
        state = _text(row.get("bridge_surface_state"))
        if family:
            bucket["bridge_surface_family_counts"][family] = (
                _to_int(bucket["bridge_surface_family_counts"].get(family), 0) + 1
            )
        if state:
            bucket["bridge_surface_state_counts"][state] = (
                _to_int(bucket["bridge_surface_state_counts"].get(state), 0) + 1
            )

    total_count = max(1, len(filtered_rows))
    rows: list[dict[str, Any]] = []
    for bucket in grouped.values():
        count = int(bucket["count"])
        symbol = _text(bucket.get("symbol")).upper() or "ALL"
        symbol_total = max(1, symbol_totals.get(symbol, 0))
        symbol_share = float(count) / float(symbol_total)
        global_share = float(count) / float(total_count)
        if count < int(minimum_repeat_count) and symbol_share < float(minimum_symbol_share):
            continue

        direction = _direction_from_continuation_label(bucket.get("continuation_failure_label"))
        avg_bias_gap = float(bucket["bias_gap_sum"]) / float(max(1, count))
        top_family = ""
        if bucket["bridge_surface_family_counts"]:
            top_family = sorted(
                bucket["bridge_surface_family_counts"].items(),
                key=lambda item: (-_to_int(item[1]), item[0]),
            )[0][0]
        top_state = ""
        if bucket["bridge_surface_state_counts"]:
            top_state = sorted(
                bucket["bridge_surface_state_counts"].items(),
                key=lambda item: (-_to_int(item[1]), item[0]),
            )[0][0]

        rows.append(
            {
                "contract_version": DIRECTIONAL_CONTINUATION_LEARNING_CANDIDATE_VERSION,
                "candidate_key": (
                    f"wrong_side::{symbol}::{_text(bucket.get('continuation_failure_label'))}"
                    f"::{_text(bucket.get('context_failure_label'))}"
                ),
                "source_kind": "wrong_side_conflict_harvest",
                "symbol": symbol,
                "continuation_direction": direction,
                "summary_ko": _direction_summary_ko(symbol, direction),
                "why_now_ko": (
                    f"최근 {symbol} wrong-side continuation conflict {symbol_total}건 중 "
                    f"{count}건({symbol_share * 100.0:.1f}%)이 "
                    f"`{_text(bucket.get('primary_failure_label'))}` / "
                    f"`{_text(bucket.get('context_failure_label'))}`로 반복돼, "
                    f"{_direction_hint_ko(direction)}."
                ),
                "recommended_action_ko": (
                    "자동 관찰을 누적하고 detector/propose에서 반복성을 확인한 뒤 "
                    "bounded live review 후보로 천천히 승격합니다."
                ),
                "evidence_lines_ko": [
                    _direction_observe_hint_line(direction),
                    f"- symbol_conflict_share: {symbol_share * 100.0:.1f}%",
                    f"- global_conflict_share: {global_share * 100.0:.1f}%",
                    f"- primary_failure_label: {_text(bucket.get('primary_failure_label'))}",
                    f"- context_failure_label: {_text(bucket.get('context_failure_label'))}",
                    f"- bridge_surface_family: {top_family or '-'}",
                    f"- bridge_surface_state: {top_state or '-'}",
                ],
                "repeat_count": count,
                "symbol_share": round(symbol_share, 4),
                "global_share": round(global_share, 4),
                "priority_score": _cluster_priority_score(
                    repeat_count=count,
                    symbol_share=symbol_share,
                    global_share=global_share,
                    bias_gap=avg_bias_gap,
                ),
                "misread_confidence": _cluster_confidence(
                    repeat_count=count,
                    symbol_share=symbol_share,
                    global_share=global_share,
                    bias_gap=avg_bias_gap,
                ),
                "registry_key": _direction_registry_key(direction),
                "extra_evidence_registry_keys": [_direction_registry_key(direction)],
                "pattern_code": _direction_pattern_code(direction),
                "pattern_label_ko": _direction_pattern_label_ko(direction),
                "primary_failure_label": _text(bucket.get("primary_failure_label")),
                "continuation_failure_label": _text(bucket.get("continuation_failure_label")),
                "context_failure_label": _text(bucket.get("context_failure_label")),
                "bridge_surface_family": top_family,
                "bridge_surface_state": top_state,
                "dominant_observe_reason": "",
                "source_kind_list": ["wrong_side_conflict_harvest"],
                "source_labels_ko": [_source_label_ko("wrong_side_conflict_harvest")],
            }
        )
    return rows


def _build_market_family_entry_rows(
    market_family_entry_payload: Mapping[str, Any] | None,
    *,
    minimum_repeat_count: int,
    minimum_symbol_share: float,
) -> list[dict[str, Any]]:
    payload = _mapping(market_family_entry_payload) or _load_json(
        default_market_family_entry_audit_json_path()
    )
    summary = _mapping(payload.get("summary"))
    observe_reason_counts = {
        _text(symbol).upper(): _json_mapping(reason_map)
        for symbol, reason_map in _json_mapping(summary.get("symbol_observe_reason_counts")).items()
    }
    symbol_row_counts = {
        _text(symbol).upper(): _to_int(count)
        for symbol, count in _json_mapping(summary.get("symbol_row_counts")).items()
    }
    total_rows = max(1, sum(max(0, value) for value in symbol_row_counts.values()))

    rows: list[dict[str, Any]] = []
    for symbol, reason_map in observe_reason_counts.items():
        symbol_total = max(1, symbol_row_counts.get(symbol, 0))
        for observe_reason, count_value in reason_map.items():
            count = _to_int(count_value)
            if count <= 0:
                continue

            direction = ""
            pattern_hint = ""
            if observe_reason in _MARKET_FAMILY_UP_OBSERVE_REASONS:
                direction = "UP"
                pattern_hint = _MARKET_FAMILY_UP_OBSERVE_REASONS[observe_reason]
            elif observe_reason in _MARKET_FAMILY_DOWN_OBSERVE_REASONS:
                direction = "DOWN"
                pattern_hint = _MARKET_FAMILY_DOWN_OBSERVE_REASONS[observe_reason]
            if not direction:
                continue

            symbol_share = float(count) / float(symbol_total)
            global_share = float(count) / float(total_rows)
            if count < int(minimum_repeat_count) and symbol_share < float(minimum_symbol_share):
                continue

            rows.append(
                {
                    "contract_version": DIRECTIONAL_CONTINUATION_LEARNING_CANDIDATE_VERSION,
                    "candidate_key": f"market_family::{symbol}::{direction}::{observe_reason}",
                    "source_kind": "market_family_entry_audit",
                    "symbol": symbol,
                    "continuation_direction": direction,
                    "summary_ko": _direction_summary_ko(symbol, direction),
                    "why_now_ko": (
                        f"최근 {symbol} market-family observe {symbol_total}건 중 "
                        f"{count}건({symbol_share * 100.0:.1f}%)이 `{observe_reason}`로 반복돼, "
                        f"{pattern_hint} 장면을 {('상승' if direction == 'UP' else '하락')} 지속으로 읽을 필요가 있습니다."
                    ),
                    "recommended_action_ko": (
                        "자동 관찰을 누적하고 같은 방향 지속 장면이 반복되면 "
                        "bounded live review 후보로 승격합니다."
                    ),
                    "evidence_lines_ko": [
                        _direction_observe_hint_line(direction),
                        f"- market_family_observe_reason: {observe_reason}",
                        f"- symbol_observe_share: {symbol_share * 100.0:.1f}%",
                        f"- global_observe_share: {global_share * 100.0:.1f}%",
                    ],
                    "repeat_count": count,
                    "symbol_share": round(symbol_share, 4),
                    "global_share": round(global_share, 4),
                    "priority_score": _cluster_priority_score(
                        repeat_count=count,
                        symbol_share=symbol_share,
                        global_share=global_share,
                    ),
                    "misread_confidence": _cluster_confidence(
                        repeat_count=count,
                        symbol_share=symbol_share,
                        global_share=global_share,
                    ),
                    "registry_key": _direction_registry_key(direction),
                    "extra_evidence_registry_keys": [_direction_registry_key(direction)],
                    "pattern_code": _direction_pattern_code(direction),
                    "pattern_label_ko": _direction_pattern_label_ko(direction),
                    "primary_failure_label": "",
                    "continuation_failure_label": (
                        "missed_up_continuation" if direction == "UP" else "missed_down_continuation"
                    ),
                    "context_failure_label": "",
                    "bridge_surface_family": "",
                    "bridge_surface_state": "",
                    "dominant_observe_reason": observe_reason,
                    "source_kind_list": ["market_family_entry_audit"],
                    "source_labels_ko": [_source_label_ko("market_family_entry_audit")],
                }
            )
    return rows


def _merge_directional_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    ordered = sorted(
        rows,
        key=lambda row: (
            _SOURCE_PRIORITY.get(_text(row.get("source_kind")), 99),
            -_to_float(row.get("priority_score"), 0.0),
            -_to_int(row.get("repeat_count"), 0),
            _text(row.get("symbol")).lower(),
        ),
    )
    for row in ordered:
        row_map = dict(row)
        key = (
            _text(row_map.get("symbol")).upper() or "ALL",
            _text(row_map.get("continuation_direction")),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = row_map
            continue

        existing["source_kind_list"] = _unique_text_list(
            list(existing.get("source_kind_list") or [])
            + list(row_map.get("source_kind_list") or [row_map.get("source_kind")])
        )
        existing["source_labels_ko"] = _unique_text_list(
            list(existing.get("source_labels_ko") or [])
            + list(row_map.get("source_labels_ko") or [_source_label_ko(_text(row_map.get("source_kind")))])
        )
        existing["extra_evidence_registry_keys"] = _unique_text_list(
            list(existing.get("extra_evidence_registry_keys") or [])
            + list(row_map.get("extra_evidence_registry_keys") or [])
        )
        existing["evidence_lines_ko"] = _unique_text_list(
            list(existing.get("evidence_lines_ko") or [])
            + list(row_map.get("evidence_lines_ko") or [])
        )[:8]
        existing["repeat_count"] = max(
            _to_int(existing.get("repeat_count"), 0),
            _to_int(row_map.get("repeat_count"), 0),
        )
        existing["symbol_share"] = max(
            _to_float(existing.get("symbol_share"), 0.0),
            _to_float(row_map.get("symbol_share"), 0.0),
        )
        existing["global_share"] = max(
            _to_float(existing.get("global_share"), 0.0),
            _to_float(row_map.get("global_share"), 0.0),
        )
        existing["priority_score"] = max(
            _to_float(existing.get("priority_score"), 0.0),
            _to_float(row_map.get("priority_score"), 0.0),
        )
        existing["misread_confidence"] = max(
            _to_float(existing.get("misread_confidence"), 0.0),
            _to_float(row_map.get("misread_confidence"), 0.0),
        )
        existing["source_kind"] = (
            _text(existing.get("source_kind"))
            if _SOURCE_PRIORITY.get(_text(existing.get("source_kind")), 99)
            <= _SOURCE_PRIORITY.get(_text(row_map.get("source_kind")), 99)
            else _text(row_map.get("source_kind"))
        )
        if not _text(existing.get("why_now_ko")):
            existing["why_now_ko"] = _text(row_map.get("why_now_ko"))
        elif _text(row_map.get("why_now_ko")) and _text(row_map.get("why_now_ko")) not in _text(existing.get("why_now_ko")):
            existing["why_now_ko"] = f"{_text(existing.get('why_now_ko'))} / {_text(row_map.get('why_now_ko'))}"
        if not _text(existing.get("recommended_action_ko")):
            existing["recommended_action_ko"] = _text(row_map.get("recommended_action_ko"))
        for field in (
            "primary_failure_label",
            "continuation_failure_label",
            "context_failure_label",
            "bridge_surface_family",
            "bridge_surface_state",
            "dominant_observe_reason",
        ):
            if not _text(existing.get(field)) and _text(row_map.get(field)):
                existing[field] = _text(row_map.get(field))

    return sorted(
        merged.values(),
        key=lambda row: (
            -_to_float(_mapping(row).get("priority_score"), 0.0),
            -_to_int(_mapping(row).get("repeat_count"), 0),
            _text(_mapping(row).get("summary_ko")).lower(),
        ),
    )


def build_directional_continuation_learning_candidates(
    *,
    semantic_cluster_candidates: list[Mapping[str, Any]] | None = None,
    wrong_side_conflict_payload: Mapping[str, Any] | None = None,
    market_family_entry_payload: Mapping[str, Any] | None = None,
    minimum_repeat_count: int = 2,
    minimum_symbol_share: float = 0.35,
    minimum_market_family_repeat_count: int = 3,
    minimum_market_family_symbol_share: float = 0.12,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_build_semantic_continuation_rows(semantic_cluster_candidates))
    rows.extend(
        _build_wrong_side_continuation_rows(
            wrong_side_conflict_payload,
            minimum_repeat_count=minimum_repeat_count,
            minimum_symbol_share=minimum_symbol_share,
        )
    )
    rows.extend(
        _build_market_family_entry_rows(
            market_family_entry_payload,
            minimum_repeat_count=minimum_market_family_repeat_count,
            minimum_symbol_share=minimum_market_family_symbol_share,
        )
    )
    return _merge_directional_rows(rows)
