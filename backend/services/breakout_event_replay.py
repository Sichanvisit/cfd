"""Replay-only breakout alignment and target builders.

Phase 0 separates replay/manual truth labels from runtime breakout detection.
This module is allowed to read manual anchors and future outcome summaries,
but its outputs must not be fed back into runtime feature builders.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.services.breakout_event_runtime import build_breakout_event_runtime_v1


BREAKOUT_MANUAL_ALIGNMENT_CONTRACT_VERSION = "breakout_manual_alignment_v1"
BREAKOUT_ACTION_TARGET_CONTRACT_VERSION = "breakout_action_target_v1"
BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_VERSION = "breakout_event_replay_scope_freeze_v1"

BREAKOUT_ACTION_TARGET_WAIT_MORE = "WAIT_MORE"
BREAKOUT_ACTION_TARGET_ENTER_NOW = "ENTER_NOW"
BREAKOUT_ACTION_TARGET_AVOID_ENTRY = "AVOID_ENTRY"
BREAKOUT_ACTION_TARGET_EXIT_PROTECT = "EXIT_PROTECT"

MANUAL_LABEL_GOOD_WAIT_BETTER_ENTRY = "good_wait_better_entry"
MANUAL_LABEL_BAD_WAIT_MISSED_MOVE = "bad_wait_missed_move"
MANUAL_LABEL_GOOD_WAIT_PROTECTIVE_EXIT = "good_wait_protective_exit"

BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_VERSION,
    "replay_role": "manual_truth_alignment_and_shadow_target_builder",
    "phase": "P0",
    "runtime_direct_use_fields": [],
    "replay_only_fields": [
        "breakout_manual_alignment_v1",
        "breakout_action_target_v1",
        "manual_wait_teacher_label",
        "manual_wait_teacher_anchor_time",
        "manual_wait_teacher_entry_time",
        "manual_wait_teacher_exit_time",
        "future_favorable_move_ratio",
        "future_adverse_move_ratio",
    ],
    "forbidden_runtime_exports": [
        "manual_wait_teacher_label",
        "future_favorable_move_ratio",
        "future_adverse_move_ratio",
        "target_source",
        "provisional_target",
    ],
    "no_leakage_rule": (
        "Replay alignment may consume manual truth and future outcomes to build "
        "analysis rows and shadow targets, but those labels must never be routed "
        "back into breakout_event_runtime_v1 or other live runtime builders."
    ),
}


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _runtime_breakout(
    decision_row: Mapping[str, Any] | None,
    breakout_event_runtime_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mapped = _as_mapping(breakout_event_runtime_v1)
    if mapped:
        return mapped
    return build_breakout_event_runtime_v1(_as_mapping(decision_row))


def build_breakout_manual_alignment_v1(
    *,
    decision_row: Mapping[str, Any] | None = None,
    breakout_event_runtime_v1: Mapping[str, Any] | None = None,
    manual_wait_teacher_row: Mapping[str, Any] | None = None,
    future_outcome_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = _as_mapping(decision_row)
    runtime_breakout = _runtime_breakout(decision, breakout_event_runtime_v1)
    manual = _as_mapping(manual_wait_teacher_row) or decision
    future = _as_mapping(future_outcome_row)

    manual_label = _to_str(
        manual.get("manual_wait_teacher_label", manual.get("manual_label", ""))
    ).lower()
    breakout_state = _to_str(runtime_breakout.get("breakout_state")).lower()
    breakout_direction = _to_str(runtime_breakout.get("breakout_direction")).upper()
    future_favorable_move_ratio = _to_float(
        future.get("future_favorable_move_ratio", future.get("favorable_move_ratio"))
    )
    future_adverse_move_ratio = _to_float(
        future.get("future_adverse_move_ratio", future.get("adverse_move_ratio"))
    )

    if not runtime_breakout.get("available", False):
        alignment_class = "runtime_missing"
        aligned = False
    elif not manual_label:
        alignment_class = "manual_missing"
        aligned = False
    elif manual_label == MANUAL_LABEL_GOOD_WAIT_BETTER_ENTRY and breakout_state in {
        "initial_breakout",
        "breakout_pullback",
        "breakout_continuation",
    }:
        alignment_class = "aligned_breakout_entry"
        aligned = True
    elif manual_label == MANUAL_LABEL_BAD_WAIT_MISSED_MOVE and breakout_state in {
        "initial_breakout",
        "breakout_pullback",
        "breakout_continuation",
    }:
        alignment_class = "missed_breakout"
        aligned = True
    elif manual_label == MANUAL_LABEL_GOOD_WAIT_PROTECTIVE_EXIT and breakout_state == "breakout_continuation":
        alignment_class = "protective_exit_alignment"
        aligned = True
    else:
        alignment_class = "label_state_mismatch"
        aligned = False

    reason_tokens = [
        alignment_class,
        manual_label,
        breakout_state,
        breakout_direction.lower() if breakout_direction else "",
    ]
    return {
        "contract_version": BREAKOUT_MANUAL_ALIGNMENT_CONTRACT_VERSION,
        "scope_freeze_contract_version": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_VERSION,
        "available": bool(runtime_breakout.get("available", False)),
        "aligned": bool(aligned),
        "alignment_class": alignment_class,
        "manual_label_present": bool(manual_label),
        "manual_wait_teacher_label": manual_label,
        "manual_wait_teacher_anchor_time": _to_str(manual.get("manual_wait_teacher_anchor_time")),
        "manual_wait_teacher_entry_time": _to_str(manual.get("manual_wait_teacher_entry_time")),
        "manual_wait_teacher_exit_time": _to_str(manual.get("manual_wait_teacher_exit_time")),
        "breakout_state": breakout_state,
        "breakout_direction": breakout_direction,
        "breakout_confidence": _to_float(runtime_breakout.get("breakout_confidence")),
        "breakout_failure_risk": _to_float(runtime_breakout.get("breakout_failure_risk")),
        "future_favorable_move_ratio": round(float(future_favorable_move_ratio), 6),
        "future_adverse_move_ratio": round(float(future_adverse_move_ratio), 6),
        "reason_summary": "|".join(token for token in reason_tokens if token),
    }


def build_breakout_action_target_v1(
    breakout_manual_alignment_v1: Mapping[str, Any] | None,
    *,
    allow_provisional: bool = True,
) -> dict[str, Any]:
    alignment = _as_mapping(breakout_manual_alignment_v1)
    if not alignment:
        return {
            "contract_version": BREAKOUT_ACTION_TARGET_CONTRACT_VERSION,
            "available": False,
            "target": "",
            "target_source": "",
            "provisional_target": False,
            "reason_summary": "alignment_missing",
        }

    manual_label = _to_str(alignment.get("manual_wait_teacher_label")).lower()
    breakout_state = _to_str(alignment.get("breakout_state")).lower()
    failure_risk = _to_float(alignment.get("breakout_failure_risk"))
    favorable_move = _to_float(alignment.get("future_favorable_move_ratio"))
    adverse_move = _to_float(alignment.get("future_adverse_move_ratio"))

    target = BREAKOUT_ACTION_TARGET_WAIT_MORE
    target_source = "runtime_guardrail"
    provisional_target = False
    reason_tokens: list[str] = []

    if manual_label == MANUAL_LABEL_GOOD_WAIT_PROTECTIVE_EXIT:
        target = BREAKOUT_ACTION_TARGET_EXIT_PROTECT
        target_source = "manual_truth_anchor"
        reason_tokens.extend(("manual_exit", "protective_exit"))
    elif manual_label == MANUAL_LABEL_BAD_WAIT_MISSED_MOVE:
        target = BREAKOUT_ACTION_TARGET_ENTER_NOW
        target_source = "manual_truth_anchor"
        reason_tokens.extend(("manual_missed_move", "enter_now"))
    elif manual_label == MANUAL_LABEL_GOOD_WAIT_BETTER_ENTRY:
        if breakout_state in {"initial_breakout", "breakout_pullback", "breakout_continuation"}:
            target = BREAKOUT_ACTION_TARGET_ENTER_NOW
            target_source = "manual_truth_anchor"
            reason_tokens.extend(("manual_better_entry", "enter_now"))
        else:
            target = BREAKOUT_ACTION_TARGET_WAIT_MORE
            target_source = "manual_truth_anchor"
            reason_tokens.extend(("manual_better_entry", "wait_more"))
    elif breakout_state == "failed_breakout" or (failure_risk >= 0.60 and adverse_move > favorable_move):
        target = BREAKOUT_ACTION_TARGET_AVOID_ENTRY
        target_source = "replay_outcome_guard"
        provisional_target = manual_label == ""
        reason_tokens.extend(("failed_breakout", "avoid_entry"))
    elif breakout_state in {"initial_breakout", "breakout_pullback"} and favorable_move >= adverse_move and allow_provisional:
        target = BREAKOUT_ACTION_TARGET_ENTER_NOW
        target_source = "provisional_breakout_runtime"
        provisional_target = True
        reason_tokens.extend(("runtime_breakout", "enter_now"))
    else:
        target = BREAKOUT_ACTION_TARGET_WAIT_MORE
        target_source = "runtime_guardrail" if manual_label == "" else "manual_truth_anchor"
        provisional_target = manual_label == ""
        reason_tokens.extend(("guardrail", "wait_more"))

    return {
        "contract_version": BREAKOUT_ACTION_TARGET_CONTRACT_VERSION,
        "available": True,
        "target": target,
        "target_source": target_source,
        "provisional_target": bool(provisional_target),
        "reason_summary": "|".join(reason_tokens),
    }
