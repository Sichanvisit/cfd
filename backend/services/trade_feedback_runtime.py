from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.improvement_proposal_policy import build_improvement_proposal_envelope
from backend.services.improvement_detector_feedback_runtime import (
    DETECTOR_FEEDBACK_CONFIRMED,
    DETECTOR_FEEDBACK_MISSED,
    DETECTOR_NARROWING_KEEP,
    DETECTOR_NARROWING_PROMOTE,
    build_detector_confusion_snapshot,
    detector_narrowing_label_ko,
)
from backend.services.improvement_status_policy import (
    PROPOSAL_STAGE_REPORT_READY,
    READINESS_STATUS_PENDING_EVIDENCE,
    READINESS_STATUS_READY_FOR_REVIEW,
)
from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    LEARNING_REGISTRY_BINDING_MODE_FALLBACK,
    build_learning_registry_binding_fields,
    build_learning_registry_relation,
)
from backend.services.telegram_pnl_digest_formatter import (
    _format_reason_display,
    _pick_trade_unit_column,
    _prepare_closed_frame,
    _safe_numeric_series,
)
from backend.services.semantic_baseline_no_action_cluster_candidate import (
    build_semantic_baseline_no_action_cluster_candidates,
)
from backend.services.directional_continuation_learning_candidate import (
    build_directional_continuation_learning_candidates,
)
from backend.services.semantic_baseline_no_action_gate_review_candidate import (
    build_semantic_baseline_no_action_gate_review_candidates,
)


TRADE_FEEDBACK_RUNTIME_CONTRACT_VERSION = "trade_feedback_runtime_v1"
DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT = 50
MANUAL_PROPOSE_COMMAND = "/propose"

FAST_PROMOTION_MIN_FEEDBACK = 5
FAST_PROMOTION_MIN_POSITIVE_RATIO = 0.70
FAST_PROMOTION_MIN_TRADE_DAYS = 3
FAST_PROMOTION_MIN_MISREAD_CONFIDENCE = 0.65

PROMOTION_REGISTRY_KEY_HINDSIGHT_STATUS = "promotion:hindsight_status"
PROMOTION_REGISTRY_KEY_MIN_FEEDBACK = "promotion:fast_promotion_min_feedback"
PROMOTION_REGISTRY_KEY_MIN_POSITIVE_RATIO = "promotion:fast_promotion_min_positive_ratio"
PROMOTION_REGISTRY_KEY_MIN_TRADE_DAYS = "promotion:fast_promotion_min_trade_days"
PROMOTION_REGISTRY_KEY_MIN_MISREAD_CONFIDENCE = "promotion:fast_promotion_min_misread_confidence"
PROMOTION_POLICY_TARGET_REGISTRY_KEYS = [
    PROMOTION_REGISTRY_KEY_HINDSIGHT_STATUS,
    PROMOTION_REGISTRY_KEY_MIN_FEEDBACK,
    PROMOTION_REGISTRY_KEY_MIN_POSITIVE_RATIO,
    PROMOTION_REGISTRY_KEY_MIN_TRADE_DAYS,
    PROMOTION_REGISTRY_KEY_MIN_MISREAD_CONFIDENCE,
]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _parse_iso_datetime(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _first_nonempty_text(series: pd.Series) -> str:
    for value in series.tolist():
        text = _text(value)
        if text:
            return text
    return ""


def _fmt_money(value: float) -> str:
    return f"{value:+.2f} USD"


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _normalize_manual_propose_text_line(text: object) -> str:
    normalized = _text(text)
    replacements = {
        "state25 context bridge weight review ?\uaefe\ub09b:": "state25 context bridge weight review \ud6c4\ubcf4:",
        "state25 context bridge weight review ?\u88a1\u05d8\uae76:": "state25 context bridge weight review \ud6c4\ubcf4:",
        "state25 context bridge threshold review ?\uaefe\ub09b:": "state25 context bridge threshold review \ud6c4\ubcf4:",
        "state25 context bridge threshold review ?\u88a1\u05d8\uae76:": "state25 context bridge threshold review \ud6c4\ubcf4:",
        "feedback-aware ?\uacf7\uafd1 \u5bc3\u20ac??": "feedback-aware \uc6b0\uc120 \uac80\ud1a0:",
        "semantic observe cluster ?\uaefe\ub09b:": "semantic observe cluster \ud6c4\ubcf4:",
        "semantic gate review ?\uaefe\ub09b:": "semantic gate review \ud6c4\ubcf4:",
        "continuation 諛⑺뼢 ?숈뒿 ?꾨낫:": "continuation 방향 학습 후보:",
        "\uc81a\ubab4\uc838 ?\u2466\uafd9:": "\ubb38\uc81c \ud328\ud134:",
        "?\uc4d3\ucef7?\u20ac \uad00\ufffd?": "\uc2dc\uac04\ub300 \uad00\ucc30:",
        "?\uc12d\ub8e5 ?\uc492\uc548 \u907a\uafe9\uafd8 | \ufe64\ucad3\ub834 \ufffd\ub35b\uc6a9 \uc5e9\uacf4\uc625": "\uc218\ub3d9 \uc81c\uc548 \ubd84\uc11d | \ucd5c\uadfc \ub9c8\uac10 \uac70\ub798",
        "   - \ufe4d\uceab: ": "   - \ub9e5\ub77d: ",
        "   - \u7b4c\ub760\uc0b4\ubd75: ": "   - \ub9e5\ub77d: ",
        "   - ?\uc4d6\ube9e: ": "   - \uc81c\uc548: ",
        "   - ??\ubf6f\ud9a7: ": "   - \uc81c\uc548: ",
        "   - ?\ubba8\ub5d2: ": "   - \ud310\ub2e8: ",
        "   - \ufe4d\uceab/?\uc774\uc36d: ": "   - \ub9e5\ub77d/\uc0ac\ud6c4: ",
        "   - 異⑸룎: ": "   - 충돌: ",
        "   - 洹쇨굅: ": "   - 근거: ",
        "   - ?댁쑀: ": "   - 이유: ",
        "   - ?쒖븞: ": "   - 제안: ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _build_manual_propose_inbox_summary_ko(
    *,
    analyzed_count: int,
    surfaced_issue_count: int,
    feedback_promotion_count: int,
    semantic_cluster_count: int,
    semantic_gate_review_count: int,
    state25_weight_review_count: int,
    state25_threshold_review_count: int,
) -> str:
    if (
        surfaced_issue_count
        or feedback_promotion_count
        or semantic_cluster_count
        or semantic_gate_review_count
        or state25_weight_review_count
        or state25_threshold_review_count
    ):
        return (
            f"[자동 분석 보고] 최근 {analyzed_count}건 기준 문제 패턴 {surfaced_issue_count}건 / "
            f"feedback-aware {feedback_promotion_count}건 / semantic cluster {semantic_cluster_count}건 / "
            f"semantic gate {semantic_gate_review_count}건 / state25 weight {state25_weight_review_count}건 / "
            f"state25 threshold {state25_threshold_review_count}건 / 보고서 topic 확인"
        )
    return f"[자동 분석 보고] 최근 {analyzed_count}건 기준 아직 크게 surface된 문제 패턴은 없고, 계속 분석하며 자동 반영 후보를 누적합니다."

def _build_manual_propose_inbox_summary_ko_v2(
    *,
    analyzed_count: int,
    surfaced_issue_count: int,
    feedback_promotion_count: int,
    directional_continuation_count: int,
    semantic_cluster_count: int,
    semantic_gate_review_count: int,
    state25_weight_review_count: int,
    state25_threshold_review_count: int,
) -> str:
    if (
        surfaced_issue_count
        or feedback_promotion_count
        or directional_continuation_count
        or semantic_cluster_count
        or semantic_gate_review_count
        or state25_weight_review_count
        or state25_threshold_review_count
    ):
        return (
            f"[자동 분석 보고] 최근 {analyzed_count}건 기준 문제 패턴 {surfaced_issue_count}건 / "
            f"feedback-aware {feedback_promotion_count}건 / continuation {directional_continuation_count}건 / "
            f"semantic cluster {semantic_cluster_count}건 / semantic gate {semantic_gate_review_count}건 / "
            f"state25 weight {state25_weight_review_count}건 / state25 threshold {state25_threshold_review_count}건 / 보고서 topic 확인"
        )
    return (
        f"[자동 분석 보고] 최근 {analyzed_count}건 기준 아직 크게 surface된 문제 패턴은 없고, "
        "계속 분석하고 자동 반영 후보를 누적합니다."
    )


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_trade_feedback_snapshot_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "trade_feedback_manual_propose_latest.json",
        directory / "trade_feedback_manual_propose_latest.md",
    )


def _default_improvement_log_only_detector_snapshot_path() -> Path:
    return _shadow_auto_dir() / "improvement_log_only_detector_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _aggregate_trade_units_for_feedback(
    closed_frame: pd.DataFrame | None,
    *,
    timezone: Any,
) -> pd.DataFrame:
    prepared = _prepare_closed_frame(closed_frame, timezone=timezone)
    if prepared.empty:
        return prepared

    working = prepared.copy()
    for column_name in ("peak_profit_at_exit", "post_exit_mfe"):
        if column_name not in working.columns:
            working[column_name] = 0.0
        working[column_name] = _safe_numeric_series(working, column_name)

    unit_column = _pick_trade_unit_column(working)
    if unit_column:
        unit_series = working[unit_column].fillna("").astype(str).str.strip()
        working["_trade_unit_id"] = unit_series.where(
            unit_series != "",
            working.index.map(lambda idx: f"row:{idx}"),
        )
    else:
        working["_trade_unit_id"] = working.index.map(lambda idx: f"row:{idx}")

    aggregated = (
        working.groupby("_trade_unit_id", as_index=False)
        .agg(
            close_dt=("close_dt", "max"),
            symbol=("symbol", _first_nonempty_text),
            entry_reason=("entry_reason", _first_nonempty_text),
            exit_reason=("exit_reason", _first_nonempty_text),
            realized_pnl=("realized_pnl", "sum"),
            gross_pnl=("gross_pnl", "sum"),
            cost_total=("cost_total", "sum"),
            lot=("lot", "sum"),
            peak_profit_at_exit=("peak_profit_at_exit", "max"),
            post_exit_mfe=("post_exit_mfe", "max"),
        )
        .sort_values("close_dt")
        .reset_index(drop=True)
    )
    aggregated["close_hour"] = aggregated["close_dt"].map(lambda value: int(getattr(value, "hour", 0)))
    return aggregated
def _loss_streak_stats(series: pd.Series) -> tuple[int, int]:
    max_streak = 0
    current = 0
    trailing = 0
    values = list(pd.to_numeric(series, errors="coerce").fillna(0.0).tolist())
    for value in values:
        if float(value) < 0.0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    for value in reversed(values):
        if float(value) < 0.0:
            trailing += 1
        else:
            break
    return max_streak, trailing


def _capture_ratio_average(series_pnl: pd.Series, series_peak: pd.Series) -> float | None:
    ratios: list[float] = []
    pnl_values = pd.to_numeric(series_pnl, errors="coerce").fillna(0.0).tolist()
    peak_values = pd.to_numeric(series_peak, errors="coerce").fillna(0.0).tolist()
    for pnl_value, peak_value in zip(pnl_values, peak_values, strict=False):
        peak = float(peak_value)
        if peak <= 0.0:
            continue
        realized = max(0.0, float(pnl_value))
        ratios.append(max(0.0, min(realized / peak, 1.5)))
    if not ratios:
        return None
    return float(sum(ratios) / len(ratios))


def _hour_bucket_label(hour: int) -> str:
    if hour < 6:
        return "야간(00~06시)"
    if hour < 12:
        return "오전(06~12시)"
    if hour < 18:
        return "오후(12~18시)"
    return "야간(18~24시)"
def _problem_level_for_group(
    *,
    count: int,
    win_rate: float,
    trailing_loss_streak: int,
    capture_ratio_avg: float | None,
) -> tuple[int, str]:
    if trailing_loss_streak >= 3:
        return 1, "같은 패턴에서 최근 3연속 손실이 발생했습니다."
    if count >= 5 and win_rate < 0.30:
        return 1, "표본 5건 이상 기준 승률이 30% 미만입니다."
    if count >= 5 and capture_ratio_avg is not None and capture_ratio_avg < 0.25:
        return 1, "MFE 대비 실현 수익 포착률이 25% 미만입니다."

    if trailing_loss_streak >= 2:
        return 2, "같은 패턴에서 최근 2연속 손실이 발생했습니다."
    if count >= 5 and win_rate < 0.45:
        return 2, "표본 5건 이상 기준 승률이 45% 미만입니다."
    if count >= 5 and capture_ratio_avg is not None and capture_ratio_avg < 0.40:
        return 2, "MFE 대비 실현 수익 포착률이 40% 미만입니다."

    if count < 5:
        return 3, "표본이 아직 적어 관찰 단계입니다."
    return 0, ""
def _recommendation_for_issue(*, level: int, capture_ratio_avg: float | None) -> str:
    if level == 1 and capture_ratio_avg is not None and capture_ratio_avg < 0.25:
        return "해당 패턴은 진입 자체보다 partial/청산 타이밍 조정 후보로 먼저 보는 것이 좋습니다."
    if level == 1:
        return "해당 패턴은 진입 기준 강화 또는 WAIT 우선 전환 후보로 검토하는 편이 안전합니다."
    if level == 2 and capture_ratio_avg is not None and capture_ratio_avg < 0.40:
        return "해당 패턴은 진입 여부보다 수익 포착 규칙 보강 여부를 먼저 보는 편이 좋습니다."
    if level == 2:
        return "해당 패턴은 관찰을 이어가고 반복되면 weight/scene 제안 후보로 올리는 것이 좋습니다."
    return "아직 관찰 단계이므로 당장 patch보다 로그 누적이 우선입니다."
def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_registry_key_list(values: list[object] | tuple[object, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        key = _text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _detector_label_ko(detector_key: object) -> str:
    mapping = {
        "scene_aware_detector": "scene 장면 detector",
        "candle_weight_detector": "candle weight detector",
        "reverse_pattern_detector": "reverse pattern detector",
    }
    normalized = _text(detector_key).strip().lower()
    return _text(mapping.get(normalized), normalized or "-")


def _feedback_issue_evidence_registry_keys(issue: Mapping[str, Any] | None) -> list[str]:
    issue_map = _mapping(issue)
    return _normalize_registry_key_list(
        [
            *list(issue_map.get("evidence_registry_keys") or []),
            issue_map.get("registry_key"),
        ]
    )


def _feedback_issue_target_registry_keys(issue: Mapping[str, Any] | None) -> list[str]:
    issue_map = _mapping(issue)
    return _normalize_registry_key_list(list(issue_map.get("target_registry_keys") or []))


def _feedback_promotion_target_registry_keys() -> list[str]:
    return list(PROMOTION_POLICY_TARGET_REGISTRY_KEYS)


def _feedback_promotion_binding_mode(
    *,
    evidence_registry_keys: list[str],
    target_registry_keys: list[str],
) -> str:
    if target_registry_keys and len(target_registry_keys) == 1 and len(evidence_registry_keys) <= 1:
        return LEARNING_REGISTRY_BINDING_MODE_EXACT
    if target_registry_keys or evidence_registry_keys:
        return LEARNING_REGISTRY_BINDING_MODE_DERIVED
    return LEARNING_REGISTRY_BINDING_MODE_FALLBACK


def _feedback_promotion_registry_key(
    *,
    target_registry_keys: list[str],
) -> str:
    if PROMOTION_REGISTRY_KEY_HINDSIGHT_STATUS in target_registry_keys:
        return PROMOTION_REGISTRY_KEY_HINDSIGHT_STATUS
    return _text(target_registry_keys[0]) if target_registry_keys else ""


_CONTEXT_BRIDGE_FIELDS = (
    "context_bundle_summary_ko",
    "context_conflict_state",
    "context_conflict_flags",
    "context_conflict_intensity",
    "context_conflict_score",
    "context_conflict_label_ko",
    "late_chase_risk_state",
    "late_chase_reason",
    "late_chase_confidence",
    "late_chase_trigger_count",
    "htf_alignment_state",
    "htf_alignment_detail",
    "htf_against_severity",
    "previous_box_break_state",
    "previous_box_relation",
    "previous_box_lifecycle",
    "previous_box_confidence",
)


def _build_issue_context_summary_ko(issue: Mapping[str, Any] | None) -> str:
    issue_map = _mapping(issue)
    context_summary = _text(issue_map.get("context_bundle_summary_ko"))
    if not context_summary:
        context_summary = _text(issue_map.get("context_conflict_label_ko"))
    hindsight_status_ko = _text(issue_map.get("hindsight_status_ko"))
    if not hindsight_status_ko:
        hindsight_status = _text(issue_map.get("hindsight_status"))
        hindsight_status_ko = _feedback_hindsight_label_ko(hindsight_status) if hindsight_status else ""
    if context_summary and hindsight_status_ko:
        return f"{context_summary} / 사후: {hindsight_status_ko}"
    if context_summary:
        return context_summary
    if hindsight_status_ko:
        return f"사후: {hindsight_status_ko}"
    return ""


def _extract_issue_context_bridge(issue: Mapping[str, Any] | None) -> dict[str, Any]:
    issue_map = _mapping(issue)
    payload: dict[str, Any] = {
        field: issue_map.get(field)
        for field in _CONTEXT_BRIDGE_FIELDS
        if field in issue_map
    }
    payload["proposal_context_summary_ko"] = _build_issue_context_summary_ko(issue_map)
    return payload


def _attach_feedback_promotion_registry_binding(
    row: Mapping[str, Any],
    *,
    latest_issue: Mapping[str, Any] | None,
) -> dict[str, Any]:
    row_map = dict(_mapping(row))
    latest_issue_map = _mapping(latest_issue)
    evidence_registry_keys = _feedback_issue_evidence_registry_keys(latest_issue_map)
    target_registry_keys = _feedback_promotion_target_registry_keys()
    downstream_target_registry_keys = _feedback_issue_target_registry_keys(latest_issue_map)
    binding_mode = _feedback_promotion_binding_mode(
        evidence_registry_keys=evidence_registry_keys,
        target_registry_keys=target_registry_keys,
    )
    registry_key = _feedback_promotion_registry_key(target_registry_keys=target_registry_keys)
    binding_fields = build_learning_registry_binding_fields(
        registry_key,
        binding_mode=binding_mode,
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=evidence_registry_keys,
        target_registry_keys=target_registry_keys,
        binding_mode=binding_mode,
    )
    downstream_relation = build_learning_registry_relation(
        target_registry_keys=downstream_target_registry_keys,
        binding_mode=(
            LEARNING_REGISTRY_BINDING_MODE_EXACT
            if len(downstream_target_registry_keys) == 1
            else LEARNING_REGISTRY_BINDING_MODE_DERIVED
        ),
    )
    row_map.update(binding_fields)
    row_map.update(
        {
            "registry_binding_ready": bool(binding_fields.get("registry_found")) and bool(relation.get("binding_ready")),
            "evidence_registry_keys": relation.get("evidence_registry_keys", []),
            "target_registry_keys": relation.get("target_registry_keys", []),
            "evidence_bindings": relation.get("evidence_bindings", []),
            "target_bindings": relation.get("target_bindings", []),
            "detector_registry_key": _text(latest_issue_map.get("registry_key")),
            "detector_registry_label_ko": _text(latest_issue_map.get("registry_label_ko")),
            "detector_registry_binding_mode": _text(latest_issue_map.get("registry_binding_mode")),
            "downstream_target_registry_keys": downstream_relation.get("target_registry_keys", []),
            "downstream_target_bindings": downstream_relation.get("target_bindings", []),
        }
    )
    row_map.update(_extract_issue_context_bridge(latest_issue_map))
    return row_map


def _summarize_feedback_registry_binding(
    feedback_promotion_rows: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    rows = [_mapping(row) for row in list(feedback_promotion_rows or []) if _mapping(row)]
    state25_context_bridge_threshold_review_candidates: list[Any] = []
    if state25_context_bridge_threshold_review_candidates:
        inbox_summary_ko = (
            f"[?섎룞 ?쒖븞 遺꾩꽍] 理쒓렐 {analyzed_count}嫄?湲곗? 臾몄젣 ?⑦꽩 {len(surfaced_issues)}嫄?/ "
            f"feedback-aware {len(feedback_promotion_rows)}嫄?/ semantic cluster {len(semantic_cluster_candidates)}嫄?/ "
            f"semantic gate {len(semantic_gate_review_candidates)}嫄?/ state25 weight {len(state25_context_bridge_weight_review_candidates)}嫄?/ "
            f"state25 threshold {len(state25_context_bridge_threshold_review_candidates)}嫄?/ 蹂닿퀬??topic ?뺤씤"
        )

    return {
        "feedback_registry_keys": _normalize_registry_key_list([row.get("registry_key") for row in rows]),
        "feedback_evidence_registry_keys": _normalize_registry_key_list(
            [key for row in rows for key in list(row.get("evidence_registry_keys") or [])]
        ),
        "feedback_target_registry_keys": _normalize_registry_key_list(
            [key for row in rows for key in list(row.get("target_registry_keys") or [])]
        ),
        "feedback_downstream_target_registry_keys": _normalize_registry_key_list(
            [key for row in rows for key in list(row.get("downstream_target_registry_keys") or [])]
        ),
        "feedback_registry_binding_ready_count": sum(
            1 for row in rows if bool(row.get("registry_binding_ready"))
        ),
    }
def _feedback_promotion_priority_key(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    row_map = _mapping(row)
    if bool(row_map.get("fast_promotion_eligible")):
        return (
            -1,
            -int(_to_float(row_map.get("confirmed_count"), 0.0) + _to_float(row_map.get("missed_count"), 0.0)),
            -int(_to_float(row_map.get("total_feedback"), 0.0)),
            _text(row_map.get("summary_ko")).lower(),
        )
    decision = _text(row_map.get("narrowing_decision")).upper()
    rank_map = {
        DETECTOR_NARROWING_PROMOTE: 0,
        DETECTOR_NARROWING_KEEP: 1,
    }
    positive_count = int(_to_float(row_map.get("confirmed_count"), 0.0) + _to_float(row_map.get("missed_count"), 0.0))
    total_feedback = int(_to_float(row_map.get("total_feedback"), 0.0))
    return (
        rank_map.get(decision, 9),
        -positive_count,
        -total_feedback,
        _text(row_map.get("summary_ko")).lower(),
    )


def _attach_semantic_cluster_registry_binding(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(_mapping(row))
    registry_key = _text(row_map.get("registry_key"))
    binding_mode = LEARNING_REGISTRY_BINDING_MODE_EXACT if registry_key else LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    row_map.update(
        build_learning_registry_binding_fields(
            registry_key,
            binding_mode=binding_mode,
        )
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=[registry_key] if registry_key else [],
        binding_mode=binding_mode,
    )
    row_map["evidence_registry_keys"] = list(relation.get("evidence_registry_keys") or [])
    row_map["target_registry_keys"] = list(relation.get("target_registry_keys") or [])
    row_map["evidence_bindings"] = list(relation.get("evidence_bindings") or [])
    row_map["target_bindings"] = list(relation.get("target_bindings") or [])
    row_map["registry_binding_ready"] = bool(relation.get("binding_ready"))
    return row_map


def _attach_directional_continuation_registry_binding(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(_mapping(row))
    registry_key = _text(row_map.get("registry_key"))
    binding_mode = LEARNING_REGISTRY_BINDING_MODE_EXACT if registry_key else LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    row_map.update(
        build_learning_registry_binding_fields(
            registry_key,
            binding_mode=binding_mode,
        )
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=list(row_map.get("extra_evidence_registry_keys") or ([registry_key] if registry_key else [])),
        binding_mode=binding_mode,
    )
    row_map["evidence_registry_keys"] = list(relation.get("evidence_registry_keys") or [])
    row_map["target_registry_keys"] = list(relation.get("target_registry_keys") or [])
    row_map["evidence_bindings"] = list(relation.get("evidence_bindings") or [])
    row_map["target_bindings"] = list(relation.get("target_bindings") or [])
    row_map["registry_binding_ready"] = bool(relation.get("binding_ready"))
    return row_map


def _attach_semantic_gate_review_registry_binding(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(_mapping(row))
    registry_key = _text(row_map.get("registry_key"))
    binding_mode = LEARNING_REGISTRY_BINDING_MODE_EXACT if registry_key else LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    row_map.update(
        build_learning_registry_binding_fields(
            registry_key,
            binding_mode=binding_mode,
        )
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=list(row_map.get("extra_evidence_registry_keys") or []),
        binding_mode=binding_mode,
    )
    row_map["evidence_registry_keys"] = list(relation.get("evidence_registry_keys") or [])
    row_map["target_registry_keys"] = list(relation.get("target_registry_keys") or [])
    row_map["evidence_bindings"] = list(relation.get("evidence_bindings") or [])
    row_map["target_bindings"] = list(relation.get("target_bindings") or [])
    row_map["registry_binding_ready"] = bool(relation.get("binding_ready"))
    return row_map


def _semantic_cluster_priority_key(row: Mapping[str, Any]) -> tuple[float, int, str]:
    row_map = _mapping(row)
    return (
        -_to_float(row_map.get("priority_score"), 0.0),
        -_to_int(row_map.get("cluster_count"), 0),
        _text(row_map.get("summary_ko")).lower(),
    )


def _directional_continuation_priority_key(row: Mapping[str, Any]) -> tuple[float, int, str]:
    row_map = _mapping(row)
    return (
        -_to_float(row_map.get("priority_score"), 0.0),
        -_to_int(row_map.get("repeat_count"), 0),
        _text(row_map.get("summary_ko")).lower(),
    )


def _pick_directional_continuation_report_rows(
    rows: list[Mapping[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    normalized = [dict(_mapping(row)) for row in rows]
    if limit <= 0 or not normalized:
        return []

    ordered = sorted(normalized, key=_directional_continuation_priority_key)
    selected: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for direction in ("UP", "DOWN"):
        direction_rows = [
            row
            for row in ordered
            if _text(row.get("continuation_direction")).upper() == direction
        ]
        if not direction_rows:
            continue
        row = direction_rows[0]
        key = (
            _text(row.get("symbol")).upper(),
            _text(row.get("continuation_direction")).upper(),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        selected.append(row)
        if len(selected) >= limit:
            return selected[:limit]

    for row in ordered:
        key = (
            _text(row.get("symbol")).upper(),
            _text(row.get("continuation_direction")).upper(),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _semantic_gate_review_priority_key(row: Mapping[str, Any]) -> tuple[float, int, str]:
    row_map = _mapping(row)
    return (
        -_to_float(row_map.get("priority_score"), 0.0),
        -_to_int(row_map.get("gate_count"), 0),
        _text(row_map.get("summary_ko")).lower(),
    )


def _state25_context_bridge_weight_review_priority_key(
    row: Mapping[str, Any],
) -> tuple[int, int, int, float, str]:
    row_map = _mapping(row)
    return (
        1 if bool(row_map.get("bridge_guard_active")) else 0,
        -_to_int(row_map.get("bridge_weight_effective_count"), 0),
        -_to_int(row_map.get("bridge_weight_requested_count"), 0),
        -_to_float(row_map.get("bridge_context_bias_confidence"), 0.0),
        _text(row_map.get("summary_ko")).lower(),
    )


def _build_state25_context_bridge_weight_review_candidates(
    detector_latest_issue_refs: list[Mapping[str, Any]] | None,
    *,
    detector_snapshot_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_issue in _state25_context_bridge_candidate_source_rows(
        detector_latest_issue_refs,
        preview_field_name="weight_patch_preview",
        detector_snapshot_payload=detector_snapshot_payload,
    ):
        issue_map = _mapping(raw_issue)
        preview = _mapping(issue_map.get("weight_patch_preview"))
        if _text(preview.get("review_type")).upper() != "STATE25_WEIGHT_PATCH_REVIEW":
            continue
        if _text(preview.get("bridge_source_lane")) != "STATE25_CONTEXT_BRIDGE_WEIGHT_ONLY_LOG_ONLY":
            continue
        row = dict(preview)
        row["source_feedback_ref"] = _text(issue_map.get("feedback_ref"))
        row["source_detector_key"] = _text(issue_map.get("detector_key"))
        row["source_detector_label_ko"] = _text(issue_map.get("detector_label_ko"))
        row["source_symbol"] = _text(issue_map.get("symbol")).upper()
        row["source_summary_ko"] = _text(issue_map.get("summary_ko"))
        row["proposal_context_summary_ko"] = (
            _build_issue_context_summary_ko(issue_map)
            or _text(preview.get("bridge_context_summary_ko"))
        )
        row["bridge_guard_active"] = bool(preview.get("bridge_guard_modes"))
        rows.append(row)
    rows.sort(key=_state25_context_bridge_weight_review_priority_key)
    return rows


def _state25_context_bridge_threshold_review_priority_key(
    row: Mapping[str, Any],
) -> tuple[int, float, float, str]:
    row_map = _mapping(row)
    return (
        0 if bool(row_map.get("bridge_threshold_changed_decision")) else 1,
        -_to_float(row_map.get("bridge_threshold_effective_points"), 0.0),
        -_to_float(row_map.get("bridge_threshold_requested_points"), 0.0),
        _text(row_map.get("summary_ko")).lower(),
    )


def _build_state25_context_bridge_threshold_review_candidates(
    detector_latest_issue_refs: list[Mapping[str, Any]] | None,
    *,
    detector_snapshot_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_issue in _state25_context_bridge_candidate_source_rows(
        detector_latest_issue_refs,
        preview_field_name="threshold_patch_preview",
        detector_snapshot_payload=detector_snapshot_payload,
    ):
        issue_map = _mapping(raw_issue)
        preview = _mapping(issue_map.get("threshold_patch_preview"))
        if _text(preview.get("review_type")).upper() != "STATE25_THRESHOLD_PATCH_REVIEW":
            continue
        if _text(preview.get("bridge_source_lane")) != "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY":
            continue
        row = dict(preview)
        row["source_feedback_ref"] = _text(issue_map.get("feedback_ref"))
        row["source_detector_key"] = _text(issue_map.get("detector_key"))
        row["source_detector_label_ko"] = _text(issue_map.get("detector_label_ko"))
        row["source_symbol"] = _text(issue_map.get("symbol")).upper()
        row["source_summary_ko"] = _text(issue_map.get("summary_ko"))
        row["proposal_context_summary_ko"] = (
            _build_issue_context_summary_ko(issue_map)
            or _text(preview.get("bridge_context_summary_ko"))
        )
        row["bridge_guard_active"] = bool(preview.get("bridge_guard_modes"))
        rows.append(row)
    rows.sort(key=_state25_context_bridge_threshold_review_priority_key)
    return rows


def _iter_detector_snapshot_issue_rows(
    detector_snapshot_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    payload = _mapping(detector_snapshot_payload)
    rows: list[dict[str, Any]] = []
    for section_key in (
        "scene_aware_detector",
        "candle_weight_detector",
        "reverse_pattern_detector",
    ):
        section = _mapping(payload.get(section_key))
        for field_name in ("surfaced_rows", "cooldown_suppressed_rows"):
            for raw_row in list(section.get(field_name) or []):
                row = _mapping(raw_row)
                if row:
                    rows.append(row)
    return rows


def _state25_context_bridge_source_key(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    return (
        _text(row_map.get("feedback_scope_key"))
        or _text(row_map.get("feedback_ref"))
        or f"{_text(row_map.get('symbol')).upper()}::{_text(row_map.get('summary_ko')).lower()}"
    )


def _state25_context_bridge_candidate_source_rows(
    detector_latest_issue_refs: list[Mapping[str, Any]] | None,
    *,
    preview_field_name: str,
    detector_snapshot_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    merged_by_scope: dict[str, dict[str, Any]] = {}
    needs_snapshot_fallback = detector_snapshot_payload is not None

    for raw_issue in list(detector_latest_issue_refs or []):
        issue = _mapping(raw_issue)
        scope_key = _state25_context_bridge_source_key(issue)
        if not scope_key:
            continue
        if not _mapping(issue.get(preview_field_name)):
            needs_snapshot_fallback = True
        merged_by_scope[scope_key] = dict(issue)

    if not needs_snapshot_fallback:
        return list(merged_by_scope.values())

    snapshot_payload = _mapping(detector_snapshot_payload)
    if not snapshot_payload:
        snapshot_payload = _load_json(_default_improvement_log_only_detector_snapshot_path())

    for row in _iter_detector_snapshot_issue_rows(snapshot_payload):
        scope_key = _state25_context_bridge_source_key(row)
        if not scope_key:
            continue
        existing = _mapping(merged_by_scope.get(scope_key))
        merged = dict(row)
        if existing:
            merged.update(existing)
            if "weight_patch_preview" not in existing and row.get("weight_patch_preview") is not None:
                merged["weight_patch_preview"] = row.get("weight_patch_preview")
            if "threshold_patch_preview" not in existing and row.get("threshold_patch_preview") is not None:
                merged["threshold_patch_preview"] = row.get("threshold_patch_preview")
        merged_by_scope[scope_key] = merged

    return list(merged_by_scope.values())


def _feedback_trade_day_count(
    detector_feedback_entries: list[Mapping[str, Any]] | None,
    *,
    feedback_scope_key: object,
) -> int:
    scope_key = _text(feedback_scope_key)
    days: set[str] = set()
    for raw_entry in list(detector_feedback_entries or []):
        entry = _mapping(raw_entry)
        if _text(entry.get("feedback_scope_key")) != scope_key:
            continue
        dt = _parse_iso_datetime(entry.get("feedback_at"))
        if dt is None:
            continue
        days.add(dt.date().isoformat())
    return len(days)


def _feedback_hindsight_label_ko(value: object) -> str:
    mapping = {
        "confirmed_misread": "사후 확정 오판",
        "false_alarm": "사후 오경보",
        "partial_misread": "사후 타이밍 불일치",
        "unresolved": "사후 미확정",
    }
    normalized = _text(value).strip().lower()
    return _text(mapping.get(normalized), normalized or "-")


def _build_feedback_aware_promotion_rows(
    detector_feedback_entries: list[Mapping[str, Any]] | None,
    detector_latest_issue_refs: list[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    confusion_payload = build_detector_confusion_snapshot(
        detector_feedback_entries,
        detector_latest_issue_refs,
    )
    latest_issue_by_scope = {
        _text(_mapping(row).get("feedback_scope_key")): _mapping(row)
        for row in list(detector_latest_issue_refs or [])
        if _text(_mapping(row).get("feedback_scope_key"))
    }
    rows: list[dict[str, Any]] = []
    for raw_row in list(confusion_payload.get("scope_rows") or []):
        row = _mapping(raw_row)
        decision = _text(row.get("narrowing_decision")).upper()
        if decision not in {DETECTOR_NARROWING_KEEP, DETECTOR_NARROWING_PROMOTE}:
            continue
        confirmed_count = int(_to_float(row.get("confirmed_count"), 0.0))
        missed_count = int(_to_float(row.get("missed_count"), 0.0))
        positive_count = confirmed_count + missed_count
        if positive_count <= 0:
            continue
        total_feedback = int(_to_float(row.get("total_feedback"), 0.0))
        feedback_scope_key = _text(row.get("feedback_scope_key"))
        latest_issue = _mapping(latest_issue_by_scope.get(feedback_scope_key))
        hindsight_status = _text(latest_issue.get("hindsight_status"))
        hindsight_status_ko = _text(latest_issue.get("hindsight_status_ko"))
        misread_confidence = _to_float(latest_issue.get("misread_confidence"), 0.0)
        trade_day_count = _feedback_trade_day_count(
            detector_feedback_entries,
            feedback_scope_key=feedback_scope_key,
        )
        positive_ratio = float(positive_count) / float(max(1, total_feedback))
        fast_promotion_eligible = bool(
            hindsight_status == "confirmed_misread"
            and total_feedback >= FAST_PROMOTION_MIN_FEEDBACK
            and positive_ratio >= FAST_PROMOTION_MIN_POSITIVE_RATIO
            and trade_day_count >= FAST_PROMOTION_MIN_TRADE_DAYS
            and misread_confidence >= FAST_PROMOTION_MIN_MISREAD_CONFIDENCE
        )
        detector_label_ko = _detector_label_ko(row.get("detector_key"))
        summary_ko = _text(row.get("summary_ko"))
        symbol = _text(row.get("symbol")).upper() or "ALL"
        fast_promotion_reason_ko = ""
        if fast_promotion_eligible:
            fast_promotion_reason_ko = (
                f"{hindsight_status_ko or _feedback_hindsight_label_ko(hindsight_status)} 비율이 높고 "
                f"피드백 {total_feedback}건이 {trade_day_count}거래일에 걸쳐 누적되어 "
                "빠른 승격 대상으로 올립니다."
            )
            promotion_summary_ko = (
                f"{detector_label_ko}에서 사후 확정 오판 반복이 확인되어 "
                "proposal 빠른 승격 후보로 우선 검토합니다."
            )
        elif decision == DETECTOR_NARROWING_PROMOTE:
            promotion_summary_ko = (
                f"{detector_label_ko}에서 반복 긍정 피드백이 쌓여 proposal 우선 검토 대상으로 승격했습니다."
            )
        else:
            promotion_summary_ko = (
                f"{detector_label_ko}에서 긍정 피드백이 누적돼 proposal 검토 우선순위를 올려볼 가치가 있습니다."
            )
        hindsight_display_ko = hindsight_status_ko or _feedback_hindsight_label_ko(hindsight_status)
        fast_badge = " | 빠른 승격" if fast_promotion_eligible else ""
        report_line_ko = (
            f"{symbol} | {summary_ko} | {_text(row.get('narrowing_label_ko'))} | "
            f"맞았음 {confirmed_count} / 놓쳤음 {missed_count} / 과민 {int(_to_float(row.get('oversensitive_count'), 0.0))} | "
            f"{hindsight_display_ko}{fast_badge}"
        )
        row_payload = {
            "feedback_scope_key": feedback_scope_key,
            "detector_key": _text(row.get("detector_key")),
            "detector_label_ko": detector_label_ko,
            "symbol": symbol,
            "summary_ko": summary_ko,
            "narrowing_decision": decision,
            "narrowing_label_ko": detector_narrowing_label_ko(decision),
            "total_feedback": total_feedback,
            "confirmed_count": confirmed_count,
            "missed_count": missed_count,
            "oversensitive_count": int(_to_float(row.get("oversensitive_count"), 0.0)),
            "positive_ratio": positive_ratio,
            "feedback_trade_day_count": trade_day_count,
            "hindsight_status": hindsight_status,
            "hindsight_status_ko": hindsight_display_ko,
            "misread_confidence": misread_confidence,
            "fast_promotion_eligible": fast_promotion_eligible,
            "fast_promotion_reason_ko": fast_promotion_reason_ko,
            "promotion_priority_summary_ko": promotion_summary_ko,
            "report_line_ko": report_line_ko,
        }
        rows.append(
            _attach_feedback_promotion_registry_binding(
                row_payload,
                latest_issue=latest_issue,
            )
        )
    rows.sort(key=_feedback_promotion_priority_key)
    return rows


def _dominant_symbol_for_group(group: pd.DataFrame) -> str:
    if group.empty or "symbol" not in group.columns:
        return ""
    values = group["symbol"].fillna("").astype(str).str.upper().str.strip()
    values = values[values != ""]
    if values.empty:
        return ""
    mode = values.mode()
    if not mode.empty:
        return _text(mode.iloc[0]).upper()
    return _text(values.iloc[0]).upper()


def _issue_matches_feedback_promotion(issue: Mapping[str, Any], promotion: Mapping[str, Any]) -> bool:
    issue_map = _mapping(issue)
    promotion_map = _mapping(promotion)
    promotion_symbol = _text(promotion_map.get("symbol")).upper()
    issue_symbol = _text(issue_map.get("dominant_symbol") or issue_map.get("symbol")).upper()
    if promotion_symbol not in {"", "ALL", "UNKNOWN"} and issue_symbol and promotion_symbol != issue_symbol:
        return False

    issue_reason = _text(issue_map.get("entry_reason")).lower()
    issue_reason_ko = _text(issue_map.get("entry_reason_ko")).lower()
    promotion_summary = _text(promotion_map.get("summary_ko")).lower()
    detector_key = _text(promotion_map.get("detector_key")).lower()

    if issue_reason and issue_reason in promotion_summary:
        return True
    if issue_reason_ko and issue_reason_ko in promotion_summary:
        return True
    if detector_key in {"scene_aware_detector", "reverse_pattern_detector"}:
        return bool(issue_symbol and promotion_symbol in {"", "ALL", "UNKNOWN", issue_symbol})
    return False


def _apply_feedback_aware_priority(
    issues: list[dict[str, Any]],
    feedback_promotion_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prioritized: list[dict[str, Any]] = []
    for raw_issue in issues:
        issue = dict(raw_issue)
        matches = [row for row in feedback_promotion_rows if _issue_matches_feedback_promotion(issue, row)]
        matches.sort(key=_feedback_promotion_priority_key)
        issue["feedback_priority_score"] = 0
        issue["feedback_priority_summary_ko"] = ""
        issue["feedback_priority_matches"] = matches[:2]
        issue["feedback_priority_registry_key"] = ""
        issue["feedback_priority_registry_label_ko"] = ""
        issue["feedback_priority_binding_mode"] = ""
        issue["feedback_priority_evidence_registry_keys"] = []
        issue["feedback_priority_target_registry_keys"] = []
        issue["feedback_priority_context_summary_ko"] = ""
        issue["feedback_priority_hindsight_status_ko"] = ""
        issue["feedback_priority_context_conflict_state"] = ""
        if matches:
            top_match = matches[0]
            decision = _text(top_match.get("narrowing_decision")).upper()
            if bool(top_match.get("fast_promotion_eligible")):
                issue["feedback_priority_score"] = 3
            else:
                issue["feedback_priority_score"] = 2 if decision == DETECTOR_NARROWING_PROMOTE else 1
            issue["feedback_priority_summary_ko"] = _text(top_match.get("promotion_priority_summary_ko"))
            issue["feedback_priority_registry_key"] = _text(top_match.get("registry_key"))
            issue["feedback_priority_registry_label_ko"] = _text(top_match.get("registry_label_ko"))
            issue["feedback_priority_binding_mode"] = _text(top_match.get("registry_binding_mode"))
            issue["feedback_priority_evidence_registry_keys"] = list(top_match.get("evidence_registry_keys") or [])
            issue["feedback_priority_target_registry_keys"] = list(top_match.get("target_registry_keys") or [])
            issue["feedback_priority_context_summary_ko"] = _text(top_match.get("proposal_context_summary_ko"))
            issue["feedback_priority_hindsight_status_ko"] = _text(top_match.get("hindsight_status_ko"))
            issue["feedback_priority_context_conflict_state"] = _text(top_match.get("context_conflict_state"))
        prioritized.append(issue)

    prioritized.sort(
        key=lambda row: (
            int(row.get("level", 9)),
            -int(row.get("feedback_priority_score", 0)),
            -int(row.get("trailing_loss_streak", 0)),
            float(row.get("win_rate", 1.0)),
            float(row.get("net_pnl", 0.0)),
        )
    )
    return prioritized


def build_manual_trade_proposal_snapshot(
    closed_frame: pd.DataFrame | None,
    *,
    recent_trade_limit: int = DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT,
    timezone: Any,
    now_ts: str = "",
    detector_feedback_entries: list[Mapping[str, Any]] | None = None,
    detector_latest_issue_refs: list[Mapping[str, Any]] | None = None,
    detector_snapshot_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trade_units = _aggregate_trade_units_for_feedback(closed_frame, timezone=timezone)
    if not trade_units.empty:
        trade_units = (
            trade_units.sort_values("close_dt")
            .tail(max(1, int(recent_trade_limit)))
            .reset_index(drop=True)
        )

    analyzed_count = int(len(trade_units))
    overall_net = float(_safe_numeric_series(trade_units, "realized_pnl").sum()) if analyzed_count else 0.0
    overall_win_rate = (
        float((_safe_numeric_series(trade_units, "realized_pnl") > 0.0).sum()) / float(analyzed_count)
        if analyzed_count
        else 0.0
    )
    overall_capture = (
        _capture_ratio_average(
            trade_units.get("realized_pnl", pd.Series(dtype=float)),
            trade_units.get("peak_profit_at_exit", pd.Series(dtype=float)),
        )
        if analyzed_count
        else None
    )

    feedback_promotion_rows = _build_feedback_aware_promotion_rows(
        detector_feedback_entries,
        detector_latest_issue_refs,
    )
    feedback_binding_summary = _summarize_feedback_registry_binding(feedback_promotion_rows)
    feedback_context_summaries = _normalize_registry_key_list(
        [_text(row.get("proposal_context_summary_ko")) for row in feedback_promotion_rows]
    )
    feedback_hindsight_labels = _normalize_registry_key_list(
        [_text(row.get("hindsight_status_ko")) for row in feedback_promotion_rows]
    )
    raw_semantic_cluster_candidates = build_semantic_baseline_no_action_cluster_candidates()
    directional_continuation_candidates = [
        _attach_directional_continuation_registry_binding(row)
        for row in build_directional_continuation_learning_candidates(
            semantic_cluster_candidates=raw_semantic_cluster_candidates,
        )
    ]
    directional_continuation_candidates.sort(key=_directional_continuation_priority_key)
    semantic_cluster_candidates = [
        _attach_semantic_cluster_registry_binding(row)
        for row in raw_semantic_cluster_candidates
        if _text(_mapping(row).get("cluster_pattern_code")) != "continuation_gap"
    ]
    semantic_cluster_candidates.sort(key=_semantic_cluster_priority_key)
    semantic_gate_review_candidates = [
        _attach_semantic_gate_review_registry_binding(row)
        for row in build_semantic_baseline_no_action_gate_review_candidates()
    ]
    semantic_gate_review_candidates.sort(key=_semantic_gate_review_priority_key)
    state25_context_bridge_weight_review_candidates = (
        _build_state25_context_bridge_weight_review_candidates(
            detector_latest_issue_refs,
            detector_snapshot_payload=detector_snapshot_payload,
        )
    )
    state25_context_bridge_threshold_review_candidates = (
        _build_state25_context_bridge_threshold_review_candidates(
            detector_latest_issue_refs,
            detector_snapshot_payload=detector_snapshot_payload,
        )
    )

    issues: list[dict[str, Any]] = []
    if analyzed_count:
        for entry_reason, group in trade_units.groupby("entry_reason", dropna=False):
            normalized_reason = _text(entry_reason)
            if not normalized_reason:
                continue
            count = int(len(group))
            net_pnl = float(_safe_numeric_series(group, "realized_pnl").sum())
            win_rate = (
                float((_safe_numeric_series(group, "realized_pnl") > 0.0).sum()) / float(count)
                if count
                else 0.0
            )
            max_loss_streak, trailing_loss_streak = _loss_streak_stats(group["realized_pnl"])
            capture_ratio_avg = _capture_ratio_average(
                group["realized_pnl"],
                group["peak_profit_at_exit"],
            )
            level, level_reason = _problem_level_for_group(
                count=count,
                win_rate=win_rate,
                trailing_loss_streak=trailing_loss_streak,
                capture_ratio_avg=capture_ratio_avg,
            )
            if level <= 0:
                continue
            issues.append(
                {
                    "level": level,
                    "entry_reason": normalized_reason,
                    "entry_reason_ko": _format_reason_display(normalized_reason, reason_kind="entry"),
                    "dominant_symbol": _dominant_symbol_for_group(group),
                    "trade_count": count,
                    "net_pnl": net_pnl,
                    "win_rate": win_rate,
                    "max_loss_streak": max_loss_streak,
                    "trailing_loss_streak": trailing_loss_streak,
                    "capture_ratio_avg": capture_ratio_avg,
                    "level_reason_ko": level_reason,
                    "recommended_action_ko": _recommendation_for_issue(
                        level=level,
                        capture_ratio_avg=capture_ratio_avg,
                    ),
                }
            )

    issues = _apply_feedback_aware_priority(issues, feedback_promotion_rows)

    time_observations: list[str] = []
    if analyzed_count >= 6:
        for close_hour, group in trade_units.groupby("close_hour", dropna=False):
            count = int(len(group))
            if count < 3:
                continue
            win_rate = float((_safe_numeric_series(group, "realized_pnl") > 0.0).sum()) / float(count)
            if win_rate <= max(0.0, overall_win_rate - 0.15):
                time_observations.append(
                    f"- {_hour_bucket_label(int(close_hour))}: 승률 {_fmt_pct(win_rate)}로 전체 대비 {abs((overall_win_rate - win_rate) * 100.0):.1f}%p 낮습니다."
                )

    level1_count = sum(1 for row in issues if int(row.get("level", 0)) == 1)
    level2_count = sum(1 for row in issues if int(row.get("level", 0)) == 2)
    surfaced_issues = [row for row in issues if int(row.get("level", 0)) <= 2][:3]
    fast_promotion_rows = [
        row for row in feedback_promotion_rows if bool(row.get("fast_promotion_eligible"))
    ]
    bridge_review_report_lines: list[str] = []
    report_lines_ko = bridge_review_report_lines


    if state25_context_bridge_weight_review_candidates:
        bridge_review_report_lines.append("")
        report_lines_ko.append("state25 context bridge weight review 후보:")
        for index, row in enumerate(state25_context_bridge_weight_review_candidates[:3], start=1):
            report_lines_ko.append(
                f"{index}. {_text(row.get('summary_ko'))} | requested {_to_int(row.get('bridge_weight_requested_count'))}건 | effective {_to_int(row.get('bridge_weight_effective_count'))}건 | suppressed {_to_int(row.get('bridge_weight_suppressed_count'))}건"
            )
            if _text(row.get("proposal_context_summary_ko")):
                report_lines_ko.append(f"   - 맥락: {_text(row.get('proposal_context_summary_ko'))}")
            if _text(row.get("bridge_context_bias_side")):
                report_lines_ko.append(
                    f"   - bridge bias: {_text(row.get('bridge_context_bias_side'))} ({_to_float(row.get('bridge_context_bias_confidence')):.2f})"
                )
            if list(row.get("bridge_guard_modes") or []):
                report_lines_ko.append(
                    f"   - guard: {', '.join(list(row.get('bridge_guard_modes') or []))}"
                )
            if list(row.get("bridge_failure_modes") or []):
                report_lines_ko.append(
                    f"   - failure: {', '.join(list(row.get('bridge_failure_modes') or []))}"
                )
            report_lines_ko.append(f"   - 제안: {_text(row.get('recommended_action_ko'))}")

    if state25_context_bridge_threshold_review_candidates:
        bridge_review_report_lines.append("")
        report_lines_ko.append("state25 context bridge threshold review 후보:")
        for index, row in enumerate(state25_context_bridge_threshold_review_candidates[:3], start=1):
            report_lines_ko.append(
                f"{index}. {_text(row.get('summary_ko'))} | requested +{_to_float(row.get('bridge_threshold_requested_points'), 0.0):.2f}pt | effective +{_to_float(row.get('bridge_threshold_effective_points'), 0.0):.2f}pt"
            )
            if _text(row.get("proposal_context_summary_ko")):
                report_lines_ko.append(f"   - 맥락: {_text(row.get('proposal_context_summary_ko'))}")
            if list(row.get("bridge_threshold_reason_keys") or []):
                report_lines_ko.append(
                    f"   - reason: {', '.join(list(row.get('bridge_threshold_reason_keys') or []))}"
                )
            if _text(row.get("bridge_without_bridge_decision")) or _text(row.get("bridge_with_bridge_decision")):
                report_lines_ko.append(
                    f"   - decision: {_text(row.get('bridge_without_bridge_decision'), '-')} -> {_text(row.get('bridge_with_bridge_decision'), '-')}"
                )
            if list(row.get("bridge_guard_modes") or []):
                report_lines_ko.append(
                    f"   - guard: {', '.join(list(row.get('bridge_guard_modes') or []))}"
                )
            if list(row.get("bridge_failure_modes") or []):
                report_lines_ko.append(
                    f"   - failure: {', '.join(list(row.get('bridge_failure_modes') or []))}"
                )
            report_lines_ko.append(f"   - 제안: {_text(row.get('recommended_action_ko'))}")

    if surfaced_issues:
        summary_ko = f"최근 {analyzed_count}건 기준 문제 패턴 {len(surfaced_issues)}건이 surface되었습니다."
        why_now_ko = surfaced_issues[0]["level_reason_ko"]
        if _text(surfaced_issues[0].get("feedback_priority_context_summary_ko")):
            why_now_ko = f"{why_now_ko} / {_text(surfaced_issues[0].get('feedback_priority_context_summary_ko'))}"
        recommended_action_ko = "문제 패턴은 바로 완화하지 말고 bounded proposal 후보로 먼저 review topic에서 검토합니다."
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif fast_promotion_rows:
        summary_ko = f"최근 {analyzed_count}건 기준 fast promotion 후보 {len(fast_promotion_rows)}건이 surface되었습니다."
        why_now_ko = _text(fast_promotion_rows[0].get("promotion_priority_summary_ko"))
        if _text(fast_promotion_rows[0].get("proposal_context_summary_ko")):
            why_now_ko = f"{why_now_ko} / {_text(fast_promotion_rows[0].get('proposal_context_summary_ko'))}"
        recommended_action_ko = "반복 detector scope는 review backlog로 우선 올리고 bounded proposal로 먼저 검토합니다."
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif feedback_promotion_rows:
        summary_ko = f"최근 {analyzed_count}건 기준 feedback-aware 우선 검토 {len(feedback_promotion_rows)}건이 surface되었습니다."
        why_now_ko = feedback_promotion_rows[0]["promotion_priority_summary_ko"]
        if _text(feedback_promotion_rows[0].get("proposal_context_summary_ko")):
            why_now_ko = f"{why_now_ko} / {_text(feedback_promotion_rows[0].get('proposal_context_summary_ko'))}"
        recommended_action_ko = "detector feedback가 누적된 scope를 review backlog에 올리고 bounded proposal 후보로 이어서 검토합니다."
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif directional_continuation_candidates:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 continuation 방향 학습 후보 "
            f"{len(directional_continuation_candidates)}건이 surface되었습니다."
        )
        why_now_ko = _text(directional_continuation_candidates[0].get("why_now_ko"))
        recommended_action_ko = (
            "상승 지속 누락과 하락 지속 누락을 같은 continuation 학습 축으로 누적하고, "
            "반복되면 bounded live review 후보로 승격합니다."
        )
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif semantic_cluster_candidates:
        summary_ko = f"최근 {analyzed_count}건 기준 semantic observe cluster 후보 {len(semantic_cluster_candidates)}건이 surface되었습니다."
        why_now_ko = _text(semantic_cluster_candidates[0].get("why_now_ko"))
        recommended_action_ko = "semantic baseline no-action 군집은 detector/feedback/proposal 루프로 먼저 관찰하고, threshold나 allowlist 완화는 review backlog에서 따로 검토합니다."
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif semantic_gate_review_candidates:
        summary_ko = f"최근 {analyzed_count}건 기준 semantic gate review 후보 {len(semantic_gate_review_candidates)}건이 surface되었습니다."
        why_now_ko = _text(semantic_gate_review_candidates[0].get("why_now_ko"))
        recommended_action_ko = "semantic gate review 후보는 review backlog에 먼저 올리고, threshold나 guard 조정은 bounded review 이후에 검토합니다."
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif state25_context_bridge_weight_review_candidates:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 state25 context bridge weight review 후보 "
            f"{len(state25_context_bridge_weight_review_candidates)}건을 계속 분석 중입니다."
        )
        why_now_ko = _text(
            state25_context_bridge_weight_review_candidates[0].get("evidence_summary_ko")
        )
        recommended_action_ko = (
            "계속 분석하고 자동 반영 후보를 누적합니다."
        )
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    elif state25_context_bridge_threshold_review_candidates:
        summary_ko = (
            f"state25 context bridge threshold review 후보 {len(state25_context_bridge_threshold_review_candidates)}건을 "
            f"최근 {analyzed_count}건 기준으로 계속 분석 중입니다."
        )
        why_now_ko = _text(
            state25_context_bridge_threshold_review_candidates[0].get("evidence_summary_ko")
        )
        recommended_action_ko = (
            "계속 분석하고 자동 반영 후보를 누적합니다."
        )
        readiness_status = READINESS_STATUS_READY_FOR_REVIEW
    else:
        summary_ko = f"최근 {analyzed_count}건 기준 자동 분석을 계속 진행 중입니다."
        why_now_ko = "아직 바로 크게 올릴 review 후보는 적지만 detector와 semantic 흐름을 계속 추적하고 있습니다."
        recommended_action_ko = "계속 분석하고 자동 반영 후보를 누적합니다."
        readiness_status = READINESS_STATUS_PENDING_EVIDENCE

    if feedback_promotion_rows and surfaced_issues:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 문제 패턴 {len(surfaced_issues)}건 / feedback-aware 우선 검토 {len(feedback_promotion_rows)}건이 surface되었습니다."
        )
    elif fast_promotion_rows:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 fast promotion 후보 {len(fast_promotion_rows)}건 / feedback-aware 우선 검토 {len(feedback_promotion_rows)}건이 surface되었습니다."
        )
    elif directional_continuation_candidates and not surfaced_issues and not feedback_promotion_rows:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 continuation 방향 학습 후보 {len(directional_continuation_candidates)}건이 surface되었습니다."
        )
    elif semantic_cluster_candidates and not surfaced_issues and not feedback_promotion_rows:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 semantic observe cluster 후보 {len(semantic_cluster_candidates)}건이 surface되었습니다."
        )
    elif semantic_gate_review_candidates and not surfaced_issues and not feedback_promotion_rows:
        summary_ko = (
            f"최근 {analyzed_count}건 기준 semantic gate review 후보 {len(semantic_gate_review_candidates)}건이 surface되었습니다."
        )

    if state25_context_bridge_weight_review_candidates and not surfaced_issues and not feedback_promotion_rows and not directional_continuation_candidates and not semantic_cluster_candidates and not semantic_gate_review_candidates:
        summary_ko = (
            f"state25 context bridge weight review 후보 {len(state25_context_bridge_weight_review_candidates)}건이 "
            f"최근 {analyzed_count}건 기준으로 surface되었습니다."
        )

    if state25_context_bridge_threshold_review_candidates and not surfaced_issues and not feedback_promotion_rows and not directional_continuation_candidates and not semantic_cluster_candidates and not semantic_gate_review_candidates and not state25_context_bridge_weight_review_candidates:
        summary_ko = (
            f"state25 context bridge threshold review 후보 {len(state25_context_bridge_threshold_review_candidates)}건이 "
            f"최근 {analyzed_count}건 기준으로 surface되었습니다."
        )

    proposal_envelope = build_improvement_proposal_envelope(
        proposal_type="MANUAL_TRADE_PATTERN_REVIEW",
        scope_key=f"MANUAL_PROPOSE::recent_closed::{max(1, int(recent_trade_limit))}",
        trace_id=_text(now_ts, _now_iso()),
        proposal_stage=PROPOSAL_STAGE_REPORT_READY,
        readiness_status=readiness_status,
        summary_ko=summary_ko,
        why_now_ko=why_now_ko,
        recommended_action_ko=recommended_action_ko,
        confidence_level=(
            "MEDIUM"
            if (
                surfaced_issues
                or feedback_promotion_rows
                or directional_continuation_candidates
                or semantic_cluster_candidates
                or semantic_gate_review_candidates
                or state25_context_bridge_weight_review_candidates
                or state25_context_bridge_threshold_review_candidates
            )
            else "LOW"
        ),
        expected_effect_ko="반복 detector scope, semantic observe cluster, semantic gate review 후보를 같은 bounded proposal 언어로 surface해 review 우선순위를 더 쉽게 읽도록 돕습니다.",
        scope_note_ko=f"recent_closed_trade_limit={max(1, int(recent_trade_limit))}",
        evidence_snapshot={
            "analyzed_trade_count": analyzed_count,
            "level1_count": level1_count,
            "level2_count": level2_count,
            "feedback_promotion_count": len(feedback_promotion_rows),
            "fast_promotion_count": len(fast_promotion_rows),
            "feedback_context_summaries": feedback_context_summaries,
            "feedback_hindsight_labels": feedback_hindsight_labels,
            "directional_continuation_candidate_count": len(
                directional_continuation_candidates
            ),
            "directional_continuation_registry_keys": [
                _text(row.get("registry_key"))
                for row in directional_continuation_candidates
                if _text(row.get("registry_key"))
            ],
            "semantic_cluster_candidate_count": len(semantic_cluster_candidates),
            "semantic_gate_review_candidate_count": len(semantic_gate_review_candidates),
            "state25_context_bridge_weight_review_count": len(
                state25_context_bridge_weight_review_candidates
            ),
            "state25_context_bridge_weight_review_registry_keys": [
                _text(row.get("registry_key"))
                for row in state25_context_bridge_weight_review_candidates
                if _text(row.get("registry_key"))
            ],
            "state25_context_bridge_weight_review_target_registry_keys": _normalize_registry_key_list(
                [
                    key
                    for row in state25_context_bridge_weight_review_candidates
                    for key in list(row.get("target_registry_keys") or [])
                ]
            ),
            "state25_context_bridge_threshold_review_count": len(
                state25_context_bridge_threshold_review_candidates
            ),
            "state25_context_bridge_threshold_review_registry_keys": [
                _text(row.get("registry_key"))
                for row in state25_context_bridge_threshold_review_candidates
                if _text(row.get("registry_key"))
            ],
            "state25_context_bridge_threshold_review_target_registry_keys": _normalize_registry_key_list(
                [
                    key
                    for row in state25_context_bridge_threshold_review_candidates
                    for key in list(row.get("target_registry_keys") or [])
                ]
            ),
            "semantic_cluster_registry_keys": [
                _text(row.get("registry_key"))
                for row in semantic_cluster_candidates
                if _text(row.get("registry_key"))
            ],
            "semantic_gate_review_registry_keys": [
                _text(row.get("registry_key"))
                for row in semantic_gate_review_candidates
                if _text(row.get("registry_key"))
            ],
            **feedback_binding_summary,
        },
    )



    proposal_envelope["summary_ko"] = _normalize_manual_propose_text_line(
        proposal_envelope.get("summary_ko")
    )
    proposal_envelope["why_now_ko"] = _normalize_manual_propose_text_line(
        proposal_envelope.get("why_now_ko")
    )
    proposal_envelope["recommended_action_ko"] = _normalize_manual_propose_text_line(
        proposal_envelope.get("recommended_action_ko")
    )

    report_lines_ko = [
        f"기준: 최근 {analyzed_count}건 마감 거래",
        f"전체 손익 {_fmt_money(overall_net)} / 전체 승률 {_fmt_pct(overall_win_rate)}",
    ]
    report_lines_ko.extend(bridge_review_report_lines)
    if overall_capture is not None:
        report_lines_ko.append(f"평균 MFE 회수율 {_fmt_pct(overall_capture)}")

    if feedback_promotion_rows:
        report_lines_ko.append("")
        report_lines_ko.append("feedback-aware 우선 검토:")
        for index, row in enumerate(feedback_promotion_rows[:3], start=1):
            report_lines_ko.append(f"{index}. {row['report_line_ko']}")
            report_lines_ko.append(f"   - 이유: {_text(row.get('promotion_priority_summary_ko'))}")
            if _text(row.get("proposal_context_summary_ko")):
                report_lines_ko.append(f"   - 맥락/사후: {_text(row.get('proposal_context_summary_ko'))}")
            if _text(row.get("fast_promotion_reason_ko")):
                report_lines_ko.append(f"   - 빠른 승격 근거: {_text(row.get('fast_promotion_reason_ko'))}")

    if directional_continuation_candidates:
        report_lines_ko.append("")
        report_lines_ko.append("continuation 방향 학습 후보:")
        for index, row in enumerate(
            _pick_directional_continuation_report_rows(directional_continuation_candidates, limit=5),
            start=1,
        ):
            report_lines_ko.append(
                f"{index}. {_text(row.get('summary_ko'))} | 반복 {_to_int(row.get('repeat_count'))}건 | 비중 {_fmt_pct(_to_float(row.get('global_share')))}"
            )
            source_labels = [
                _text(label)
                for label in list(row.get("source_labels_ko") or [])
                if _text(label)
            ]
            if source_labels:
                report_lines_ko.append(f"   - 원천: {' / '.join(source_labels)}")
            source_kind = _text(row.get("source_kind"))
            if source_kind == "wrong_side_conflict_harvest":
                report_lines_ko.append(
                    f"   - 충돌: {_text(row.get('primary_failure_label'))} / {_text(row.get('context_failure_label'))}"
                )
            else:
                report_lines_ko.append(
                    f"   - 근거: {_text(row.get('continuation_failure_label')) or '-'} / {_text(row.get('pattern_label_ko'))}"
                )
            report_lines_ko.append(f"   - 이유: {_text(row.get('why_now_ko'))}")
            report_lines_ko.append(f"   - 제안: {_text(row.get('recommended_action_ko'))}")

    if semantic_cluster_candidates:
        report_lines_ko.append("")
        report_lines_ko.append("semantic observe cluster 후보:")
        for index, row in enumerate(semantic_cluster_candidates[:3], start=1):
            report_lines_ko.append(
                f"{index}. {_text(row.get('summary_ko'))} | 반복 {_to_int(row.get('cluster_count'))}건 | 비중 {_fmt_pct(_to_float(row.get('cluster_share')))}"
            )
            report_lines_ko.append(
                f"   - 군집: {_text(row.get('observe_reason'))} / {_text(row.get('blocked_by'))} / {_text(row.get('action_none_reason'))}"
            )
            report_lines_ko.append(f"   - 제안: {_text(row.get('recommended_action_ko'))}")

    if semantic_gate_review_candidates:
        report_lines_ko.append("")
        report_lines_ko.append("semantic gate review 후보:")
        for index, row in enumerate(semantic_gate_review_candidates[:3], start=1):
            report_lines_ko.append(
                f"{index}. {_text(row.get('candidate_label_ko'))} | 반복 {_to_int(row.get('gate_count'))}건 | 비중 {_fmt_pct(_to_float(row.get('gate_share')))}"
            )
            report_lines_ko.append(
                f"   - gate: {_text(row.get('dimension'))} / {_text(row.get('dimension_value'))}"
            )
            report_lines_ko.append(f"   - 제안: {_text(row.get('recommended_action_ko'))}")

    if surfaced_issues:
        report_lines_ko.append("")
        report_lines_ko.append("문제 패턴:")
        for index, issue in enumerate(surfaced_issues, start=1):
            report_lines_ko.append(
                f"{index}. {issue['entry_reason_ko']} | 표본 {issue['trade_count']}건 | 승률 {_fmt_pct(issue['win_rate'])} | 손익 {_fmt_money(issue['net_pnl'])}"
            )
            report_lines_ko.append(f"   - 판단: {issue['level_reason_ko']}")
            if issue.get("capture_ratio_avg") is not None:
                report_lines_ko.append(f"   - MFE 회수율 {_fmt_pct(float(issue['capture_ratio_avg']))}")
            if _text(issue.get("feedback_priority_summary_ko")):
                report_lines_ko.append(f"   - feedback-aware: {_text(issue.get('feedback_priority_summary_ko'))}")
            if _text(issue.get("feedback_priority_context_summary_ko")):
                report_lines_ko.append(f"   - 맥락/사후: {_text(issue.get('feedback_priority_context_summary_ko'))}")
            report_lines_ko.append(f"   - 제안: {issue['recommended_action_ko']}")
    else:
        report_lines_ko.extend(["", "문제 패턴:", "- 아직 surface된 문제 패턴이 없습니다."])

    if time_observations:
        report_lines_ko.append("")
        report_lines_ko.append("시간대 관찰:")
        report_lines_ko.extend(time_observations[:2])

    report_lines_ko = [
        _normalize_manual_propose_text_line(line)
        for line in report_lines_ko
    ]

    inbox_summary_ko = _build_manual_propose_inbox_summary_ko_v2(
        analyzed_count=analyzed_count,
        surfaced_issue_count=len(surfaced_issues),
        feedback_promotion_count=len(feedback_promotion_rows),
        directional_continuation_count=len(directional_continuation_candidates),
        semantic_cluster_count=len(semantic_cluster_candidates),
        semantic_gate_review_count=len(semantic_gate_review_candidates),
        state25_weight_review_count=len(state25_context_bridge_weight_review_candidates),
        state25_threshold_review_count=len(state25_context_bridge_threshold_review_candidates),
    )

    return {
        "contract_version": TRADE_FEEDBACK_RUNTIME_CONTRACT_VERSION,
        "generated_at": _text(now_ts, _now_iso()),
        "recent_trade_limit": max(1, int(recent_trade_limit)),
        "analyzed_trade_count": analyzed_count,
        "overall_net_pnl": overall_net,
        "overall_win_rate": overall_win_rate,
        "overall_capture_ratio": overall_capture,
        "level1_count": level1_count,
        "level2_count": level2_count,
        "feedback_promotion_count": len(feedback_promotion_rows),
        "fast_promotion_count": len(fast_promotion_rows),
        "feedback_context_summaries": feedback_context_summaries,
        "feedback_hindsight_labels": feedback_hindsight_labels,
        "directional_continuation_candidate_count": len(directional_continuation_candidates),
        "semantic_cluster_candidate_count": len(semantic_cluster_candidates),
        "semantic_gate_review_candidate_count": len(semantic_gate_review_candidates),
        "state25_context_bridge_weight_review_count": len(
            state25_context_bridge_weight_review_candidates
        ),
        "state25_context_bridge_threshold_review_count": len(
            state25_context_bridge_threshold_review_candidates
        ),
        "feedback_registry_binding_summary": feedback_binding_summary,
        "feedback_promotion_rows": feedback_promotion_rows,
        "directional_continuation_candidates": directional_continuation_candidates,
        "semantic_cluster_candidates": semantic_cluster_candidates,
        "semantic_gate_review_candidates": semantic_gate_review_candidates,
        "state25_context_bridge_weight_review_candidates": state25_context_bridge_weight_review_candidates,
        "state25_context_bridge_threshold_review_candidates": state25_context_bridge_threshold_review_candidates,
        "problem_patterns": issues,
        "surfaced_problem_patterns": surfaced_issues,
        "time_observations": time_observations,
        "proposal_envelope": proposal_envelope,
        "report_title_ko": "자동 분석 보고 | 최근 마감 거래",
        "report_lines_ko": report_lines_ko,
        "inbox_summary_ko": inbox_summary_ko,
    }

def build_pnl_lesson_comment_lines(
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    timezone: Any,
) -> list[str]:
    trade_units = _aggregate_trade_units_for_feedback(closed_frame, timezone=timezone)
    scoped = trade_units[(trade_units["close_dt"] >= start) & (trade_units["close_dt"] < end)].copy() if not trade_units.empty else pd.DataFrame()

    if scoped.empty:
        return ["━━ 오늘의 교훈 ━━", "✅ 특이사항 없음"]

    lesson_lines: list[str] = ["━━ 오늘의 교훈 ━━"]
    capture_ratio = _capture_ratio_average(scoped["realized_pnl"], scoped["peak_profit_at_exit"])
    if capture_ratio is not None and float((_safe_numeric_series(scoped, "peak_profit_at_exit") > 0.0).sum()) >= 2 and capture_ratio < 0.50:
        lesson_lines.append(f"⚠️ MFE 대비 수익 포착이 약합니다. 평균 포착률 {_fmt_pct(capture_ratio)}")

    for entry_reason, group in scoped.groupby("entry_reason", dropna=False):
        normalized_reason = _text(entry_reason)
        if not normalized_reason:
            continue
        max_loss_streak, trailing_loss_streak = _loss_streak_stats(group["realized_pnl"])
        effective_streak = max(max_loss_streak, trailing_loss_streak)
        if effective_streak >= 2:
            lesson_lines.append(
                f"⚠️ {_format_reason_display(normalized_reason, reason_kind='entry')} 패턴에서 최대 {effective_streak}연속 손실이 있습니다."
            )
            break

    overall_win_rate = float((_safe_numeric_series(scoped, "realized_pnl") > 0.0).sum()) / float(len(scoped))
    for close_hour, group in scoped.groupby("close_hour", dropna=False):
        if int(len(group)) < 3:
            continue
        bucket_win_rate = float((_safe_numeric_series(group, "realized_pnl") > 0.0).sum()) / float(len(group))
        if bucket_win_rate <= max(0.0, overall_win_rate - 0.20):
            lesson_lines.append(
                f"⚠️ {_hour_bucket_label(int(close_hour))} 승률이 {_fmt_pct(bucket_win_rate)}로 전체 대비 낮습니다."
            )
            break

    if len(lesson_lines) == 1:
        lesson_lines.append("✅ 특이사항 없음")
    return lesson_lines
def render_manual_trade_proposal_markdown(payload: dict[str, Any]) -> str:
    envelope = dict(payload.get("proposal_envelope") or {})
    lines = [
        "# Manual Trade Proposal Snapshot",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        f"- generated_at: `{payload.get('generated_at', '-')}`",
        f"- recent_trade_limit: `{payload.get('recent_trade_limit', '-')}`",
        f"- analyzed_trade_count: `{payload.get('analyzed_trade_count', '-')}`",
        f"- proposal_id: `{envelope.get('proposal_id', '-')}`",
        f"- readiness_status: `{envelope.get('readiness_status', '-')}`",
        "",
        "## Summary",
        f"- {envelope.get('summary_ko', '-')}",
        f"- {envelope.get('why_now_ko', '-')}",
        "",
        "## Report Lines",
    ]
    for row in payload.get("report_lines_ko", []):
        lines.append(f"- {row}")
    return "\n".join(lines)


def write_manual_trade_proposal_snapshot(
    payload: dict[str, Any],
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    default_json_path, default_markdown_path = default_trade_feedback_snapshot_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    resolved_markdown_path.write_text(render_manual_trade_proposal_markdown(payload), encoding="utf-8")
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
