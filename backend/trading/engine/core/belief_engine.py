from __future__ import annotations

from threading import Lock
from typing import Any

from backend.trading.engine.core.models import BeliefState, EvidenceVector

_BELIEF_SUPPORT_WEIGHT = 0.25
_BELIEF_ALPHA_RISE = 0.45
_BELIEF_ALPHA_DECAY = 0.25
_BELIEF_ACTIVATION_THRESHOLD = 0.12
_BELIEF_ADVANTAGE_THRESHOLD = 0.05
_BELIEF_REVERSAL_STREAK_EVIDENCE_THRESHOLD = 0.16
_BELIEF_REVERSAL_STREAK_ADVANTAGE = 0.02
_XAU_REVERSAL_RETEST_EVIDENCE_THRESHOLD = 0.10
_XAU_REVERSAL_RETEST_OPPOSITE_TOLERANCE = 0.03
_BELIEF_DOMINANCE_DEADBAND = 0.05
_BELIEF_PERSISTENCE_WINDOW = 5.0
_BELIEF_MEMORY_MODE_FIELDS = (
    "buy_reversal_belief",
    "sell_reversal_belief",
    "buy_continuation_belief",
    "sell_continuation_belief",
)
_BELIEF_MEMORY_STREAK_FIELDS = ("buy_streak", "sell_streak")
_BELIEF_MEMORY_TRANSITION_FIELDS = ("dominant_side", "dominant_mode", "transition_age", "recent_flip_side", "recent_flip_age")
_BELIEF_FREEZE_PHASE = "B0"
_BELIEF_PRE_ML_PHASE = "B6"
_BELIEF_SEMANTIC_OWNER_CONTRACT = "belief_thesis_persistence_only_v1"
_BELIEF_CANONICAL_IDENTITY_FIELDS = (
    "buy_belief",
    "sell_belief",
    "buy_persistence",
    "sell_persistence",
    "belief_spread",
    "flip_readiness",
    "belief_instability",
    "dominant_side",
    "dominant_mode",
    "buy_streak",
    "sell_streak",
    "transition_age",
)
_BELIEF_PRE_ML_REQUIRED_FEATURE_FIELDS = (
    "buy_belief",
    "sell_belief",
    "buy_persistence",
    "sell_persistence",
    "belief_spread",
    "transition_age",
    "dominant_side",
    "dominant_mode",
)
_BELIEF_PRE_ML_RECOMMENDED_FEATURE_FIELDS = (
    "flip_readiness",
    "belief_instability",
)
_BELIEF_OWNER_BOUNDARIES = {
    "position_owner_fields": [],
    "response_owner_fields": [],
    "state_owner_fields": [],
    "direct_side_identity_allowed": False,
    "direct_action_identity_allowed": False,
    "role": "thesis_persistence_and_reconfirmation_only",
    "ml_feature_usage_allowed": True,
    "ml_owner_override_allowed": False,
}

_belief_memory_lock = Lock()
_belief_memory: dict[tuple[str, str], dict[str, Any]] = {}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_key(key: tuple[str, str] | list[str] | str) -> tuple[str, str]:
    if isinstance(key, tuple) and len(key) == 2:
        return str(key[0] or "").upper(), str(key[1] or "").upper()
    if isinstance(key, list) and len(key) == 2:
        return str(key[0] or "").upper(), str(key[1] or "").upper()
    return str(key or "").upper(), "15M"


def _ema_update(previous: float, current: float) -> float:
    prev = float(previous)
    cur = max(0.0, float(current))
    alpha = _BELIEF_ALPHA_RISE if cur >= prev else _BELIEF_ALPHA_DECAY
    return prev + (alpha * (cur - prev))


def _capped_dominant_merge(first: float, second: float) -> tuple[float, float, float]:
    dominant = max(float(first), float(second))
    support = min(float(first), float(second))
    total = dominant + (_BELIEF_SUPPORT_WEIGHT * support)
    return total, dominant, support


def _is_active_side(side_total: float, opposite_total: float) -> bool:
    return (
        float(side_total) >= _BELIEF_ACTIVATION_THRESHOLD
        and float(side_total) >= (float(opposite_total) + _BELIEF_ADVANTAGE_THRESHOLD)
    )


def _is_reversal_probe_active(reversal_evidence: float, side_total: float, opposite_total: float) -> bool:
    return (
        float(reversal_evidence) >= _BELIEF_REVERSAL_STREAK_EVIDENCE_THRESHOLD
        and float(side_total) >= (float(opposite_total) - _BELIEF_REVERSAL_STREAK_ADVANTAGE)
    )


def _is_xau_retest_buy_active(
    *,
    symbol: str,
    prev_dominant_side: str,
    prev_dominant_mode: str,
    prev_buy_streak: int,
    prev_buy_belief: float,
    buy_total: float,
    sell_total: float,
    buy_reversal_evidence: float,
) -> bool:
    return bool(
        str(symbol or "").upper() == "XAUUSD"
        and str(prev_dominant_side or "").upper() == "BUY"
        and str(prev_dominant_mode or "").lower() == "reversal"
        and (int(prev_buy_streak) >= 1 or float(prev_buy_belief) >= 0.45)
        and float(buy_reversal_evidence) >= _XAU_REVERSAL_RETEST_EVIDENCE_THRESHOLD
        and float(buy_total) >= (float(sell_total) - _XAU_REVERSAL_RETEST_OPPOSITE_TOLERANCE)
    )


def _dominant_mode(reversal_belief: float, continuation_belief: float) -> str:
    return "reversal" if float(reversal_belief) >= float(continuation_belief) else "continuation"


def _resolve_side_dominance(buy_belief: float, sell_belief: float) -> tuple[str, float]:
    spread = float(buy_belief) - float(sell_belief)
    if abs(spread) < _BELIEF_DOMINANCE_DEADBAND:
        return "BALANCED", spread
    return ("BUY", spread) if spread > 0.0 else ("SELL", spread)


def _next_transition_age(
    *,
    dominant_side: str,
    dominant_mode: str,
    prev_dominant_side: str,
    prev_dominant_mode: str,
    prev_transition_age: int,
) -> int:
    if str(dominant_side) == "BALANCED":
        return 0
    if str(dominant_side) == str(prev_dominant_side) and str(dominant_mode) == str(prev_dominant_mode):
        return int(prev_transition_age) + 1
    return 1


def _next_recent_flip_state(
    *,
    dominant_side: str,
    prev_dominant_side: str,
    prev_recent_flip_side: str,
    prev_recent_flip_age: int,
) -> tuple[str, int]:
    current_side = str(dominant_side or "BALANCED").upper()
    prev_side = str(prev_dominant_side or "BALANCED").upper()
    recent_side = str(prev_recent_flip_side or "BALANCED").upper()
    recent_age = int(prev_recent_flip_age)

    if current_side in {"", "BALANCED"}:
        return "BALANCED", 0
    if prev_side not in {"", "BALANCED"} and current_side != prev_side:
        return current_side, 1
    if recent_side == current_side and recent_age > 0:
        return current_side, recent_age + 1
    return "BALANCED", 0


def _belief_totals_from_mode_memory(memory: dict[str, Any]) -> tuple[float, float]:
    buy_total, _, _ = _capped_dominant_merge(
        float(memory.get("buy_reversal_belief", 0.0) or 0.0),
        float(memory.get("buy_continuation_belief", 0.0) or 0.0),
    )
    sell_total, _, _ = _capped_dominant_merge(
        float(memory.get("sell_reversal_belief", 0.0) or 0.0),
        float(memory.get("sell_continuation_belief", 0.0) or 0.0),
    )
    return float(buy_total), float(sell_total)


def _flip_side_inputs(
    *,
    prev_dominant_side: str,
    buy_belief: float,
    sell_belief: float,
    prev_buy_belief: float,
    prev_sell_belief: float,
) -> tuple[float, float, bool]:
    prev_side = str(prev_dominant_side or "BALANCED").upper()
    if prev_side == "BUY":
        old_prev = float(prev_buy_belief)
        old_now = float(buy_belief)
        opposite_prev = float(prev_sell_belief)
        opposite_now = float(sell_belief)
        return old_prev, old_now, opposite_now - opposite_prev > 0.0
    if prev_side == "SELL":
        old_prev = float(prev_sell_belief)
        old_now = float(sell_belief)
        opposite_prev = float(prev_buy_belief)
        opposite_now = float(buy_belief)
        return old_prev, old_now, opposite_now - opposite_prev > 0.0
    return 0.0, 0.0, False


def _compute_flip_readiness(
    *,
    prev_dominant_side: str,
    dominant_side: str,
    transition_age: int,
    recent_flip_side: str,
    recent_flip_age: int,
    buy_belief: float,
    sell_belief: float,
    prev_buy_belief: float,
    prev_sell_belief: float,
    dominance_deadband: float,
) -> tuple[float, dict[str, Any]]:
    prev_side = str(prev_dominant_side or "BALANCED").upper()
    current_side = str(dominant_side or "BALANCED").upper()
    old_prev, old_now, opposite_is_rising = _flip_side_inputs(
        prev_dominant_side=prev_side,
        buy_belief=buy_belief,
        sell_belief=sell_belief,
        prev_buy_belief=prev_buy_belief,
        prev_sell_belief=prev_sell_belief,
    )
    if prev_side == "BUY":
        opposite_prev = float(prev_sell_belief)
        opposite_now = float(sell_belief)
    elif prev_side == "SELL":
        opposite_prev = float(prev_buy_belief)
        opposite_now = float(buy_belief)
    else:
        opposite_prev = 0.0
        opposite_now = 0.0

    old_side_decay = _clamp01((old_prev - old_now) / max(0.20, old_prev, 1e-9)) if prev_side in {"BUY", "SELL"} else 0.0
    opposite_side_rise = _clamp01((opposite_now - opposite_prev) / max(0.20, opposite_now, 1e-9)) if prev_side in {"BUY", "SELL"} else 0.0
    opposite_side_confirmed = bool(
        prev_side in {"BUY", "SELL"}
        and current_side not in {"", "BALANCED", prev_side}
    )
    opposite_side_age = _clamp01(float(transition_age) / 3.0) if opposite_side_confirmed else 0.0
    spread_factor = _clamp01((abs(float(buy_belief) - float(sell_belief)) - float(dominance_deadband)) / 0.20)

    flip_readiness = _clamp01(
        (old_side_decay * 0.30)
        + (opposite_side_rise * 0.30)
        + (opposite_side_age * 0.28)
        + (spread_factor * 0.12)
    )
    recent_confirmed_flip = (
        str(recent_flip_side or "BALANCED").upper() == current_side
        and 2 <= int(recent_flip_age) <= 3
    )
    if opposite_side_confirmed or recent_confirmed_flip:
        confirmed_floor = 0.55 + (0.10 * _clamp01((float(recent_flip_age) - 2.0) / 1.0))
        flip_readiness = max(float(flip_readiness), float(confirmed_floor))
    return flip_readiness, {
        "prev_dominant_side": prev_side,
        "recent_flip_side": str(recent_flip_side or "BALANCED").upper(),
        "recent_flip_age": int(recent_flip_age),
        "old_side_decay": float(old_side_decay),
        "opposite_side_rise": float(opposite_side_rise),
        "opposite_is_rising": bool(opposite_is_rising),
        "opposite_side_confirmed": bool(opposite_side_confirmed),
        "opposite_side_age": float(opposite_side_age),
        "spread_factor": float(spread_factor),
    }


def _compute_belief_instability(
    *,
    dominant_side: str,
    prev_dominant_side: str,
    transition_age: int,
    buy_persistence: float,
    sell_persistence: float,
    belief_spread: float,
    dominance_deadband: float,
) -> tuple[float, dict[str, Any]]:
    spread_abs = abs(float(belief_spread))
    spread_instability = _clamp01(((float(dominance_deadband) * 2.0) - spread_abs) / max(0.02, float(dominance_deadband) * 2.0))
    persistence_instability = _clamp01(1.0 - max(float(buy_persistence), float(sell_persistence)))
    balanced_instability = 1.0 if str(dominant_side or "BALANCED").upper() == "BALANCED" else 0.0
    fresh_flip_instability = 1.0 if (
        str(dominant_side or "BALANCED").upper() not in {"", "BALANCED"}
        and str(prev_dominant_side or "BALANCED").upper() not in {"", str(dominant_side or "BALANCED").upper()}
        and int(transition_age) <= 1
    ) else 0.0

    belief_instability = _clamp01(
        (spread_instability * 0.42)
        + (persistence_instability * 0.28)
        + (balanced_instability * 0.18)
        + (fresh_flip_instability * 0.12)
    )
    return belief_instability, {
        "spread_instability": float(spread_instability),
        "persistence_instability": float(persistence_instability),
        "balanced_instability": float(balanced_instability),
        "fresh_flip_instability": float(fresh_flip_instability),
    }


def _blank_memory() -> dict[str, Any]:
    return {
        "buy_reversal_belief": 0.0,
        "sell_reversal_belief": 0.0,
        "buy_continuation_belief": 0.0,
        "sell_continuation_belief": 0.0,
        "buy_streak": 0,
        "sell_streak": 0,
        "dominant_side": "BALANCED",
        "dominant_mode": "balanced",
        "transition_age": 0,
        "recent_flip_side": "BALANCED",
        "recent_flip_age": 0,
        "last_event_ts": None,
        "last_output": None,
    }


def reset_belief_memory() -> None:
    with _belief_memory_lock:
        _belief_memory.clear()


def get_belief_memory_snapshot(key: tuple[str, str] | list[str] | str | None = None) -> dict[str, Any]:
    with _belief_memory_lock:
        if key is None:
            return {
                f"{symbol}:{timeframe}": {
                    k: v for k, v in memory.items() if k != "last_output"
                }
                for (symbol, timeframe), memory in _belief_memory.items()
            }
        memory_key = _normalize_key(key)
        memory = dict(_belief_memory.get(memory_key, _blank_memory()))
        return {k: v for k, v in memory.items() if k != "last_output"}


def build_belief_state(
    key: tuple[str, str] | list[str] | str,
    evidence_vector_v1: EvidenceVector,
    event_ts: int | None = None,
) -> BeliefState:
    memory_key = _normalize_key(key)

    with _belief_memory_lock:
        memory = _belief_memory.setdefault(memory_key, _blank_memory())
        if event_ts is not None and memory.get("last_event_ts") == int(event_ts) and isinstance(memory.get("last_output"), dict):
            cached = dict(memory["last_output"])
            return BeliefState(**cached)

        prev_buy_belief, prev_sell_belief = _belief_totals_from_mode_memory(memory)
        prev_dominant_side = str(memory.get("dominant_side", "BALANCED"))
        prev_dominant_mode = str(memory.get("dominant_mode", "balanced"))
        prev_recent_flip_side = str(memory.get("recent_flip_side", "BALANCED"))
        prev_recent_flip_age = int(memory.get("recent_flip_age", 0))
        prev_buy_streak = int(memory.get("buy_streak", 0))

        buy_reversal_belief = _ema_update(memory["buy_reversal_belief"], evidence_vector_v1.buy_reversal_evidence)
        sell_reversal_belief = _ema_update(memory["sell_reversal_belief"], evidence_vector_v1.sell_reversal_evidence)
        buy_continuation_belief = _ema_update(memory["buy_continuation_belief"], evidence_vector_v1.buy_continuation_evidence)
        sell_continuation_belief = _ema_update(memory["sell_continuation_belief"], evidence_vector_v1.sell_continuation_evidence)

        buy_belief, buy_dominant_component, buy_support_component = _capped_dominant_merge(
            buy_reversal_belief,
            buy_continuation_belief,
        )
        sell_belief, sell_dominant_component, sell_support_component = _capped_dominant_merge(
            sell_reversal_belief,
            sell_continuation_belief,
        )

        buy_active = _is_active_side(
            evidence_vector_v1.buy_total_evidence,
            evidence_vector_v1.sell_total_evidence,
        ) or _is_reversal_probe_active(
            evidence_vector_v1.buy_reversal_evidence,
            evidence_vector_v1.buy_total_evidence,
            evidence_vector_v1.sell_total_evidence,
        ) or _is_xau_retest_buy_active(
            symbol=key[0],
            prev_dominant_side=prev_dominant_side,
            prev_dominant_mode=prev_dominant_mode,
            prev_buy_streak=prev_buy_streak,
            prev_buy_belief=prev_buy_belief,
            buy_total=evidence_vector_v1.buy_total_evidence,
            sell_total=evidence_vector_v1.sell_total_evidence,
            buy_reversal_evidence=evidence_vector_v1.buy_reversal_evidence,
        )
        sell_active = _is_active_side(
            evidence_vector_v1.sell_total_evidence,
            evidence_vector_v1.buy_total_evidence,
        ) or _is_reversal_probe_active(
            evidence_vector_v1.sell_reversal_evidence,
            evidence_vector_v1.sell_total_evidence,
            evidence_vector_v1.buy_total_evidence,
        )

        buy_streak = int(memory["buy_streak"]) + 1 if buy_active else 0
        sell_streak = int(memory["sell_streak"]) + 1 if sell_active else 0

        buy_persistence = _clamp01(buy_streak / _BELIEF_PERSISTENCE_WINDOW)
        sell_persistence = _clamp01(sell_streak / _BELIEF_PERSISTENCE_WINDOW)
        dominant_side, belief_spread = _resolve_side_dominance(buy_belief, sell_belief)
        if dominant_side == "BUY":
            dominant_mode = _dominant_mode(buy_reversal_belief, buy_continuation_belief)
        elif dominant_side == "SELL":
            dominant_mode = _dominant_mode(sell_reversal_belief, sell_continuation_belief)
        else:
            dominant_mode = "balanced"

        transition_age = _next_transition_age(
            dominant_side=dominant_side,
            dominant_mode=dominant_mode,
            prev_dominant_side=prev_dominant_side,
            prev_dominant_mode=prev_dominant_mode,
            prev_transition_age=int(memory.get("transition_age", 0)),
        )
        recent_flip_side, recent_flip_age = _next_recent_flip_state(
            dominant_side=dominant_side,
            prev_dominant_side=prev_dominant_side,
            prev_recent_flip_side=prev_recent_flip_side,
            prev_recent_flip_age=prev_recent_flip_age,
        )
        flip_readiness, flip_components = _compute_flip_readiness(
            prev_dominant_side=prev_dominant_side,
            dominant_side=dominant_side,
            transition_age=transition_age,
            recent_flip_side=recent_flip_side,
            recent_flip_age=recent_flip_age,
            buy_belief=buy_belief,
            sell_belief=sell_belief,
            prev_buy_belief=prev_buy_belief,
            prev_sell_belief=prev_sell_belief,
            dominance_deadband=_BELIEF_DOMINANCE_DEADBAND,
        )
        belief_instability, instability_components = _compute_belief_instability(
            dominant_side=dominant_side,
            prev_dominant_side=prev_dominant_side,
            transition_age=transition_age,
            buy_persistence=buy_persistence,
            sell_persistence=sell_persistence,
            belief_spread=belief_spread,
            dominance_deadband=_BELIEF_DOMINANCE_DEADBAND,
        )

        belief_reasons = {
            "buy_belief": (
                f"buy {_dominant_mode(buy_reversal_belief, buy_continuation_belief)} belief "
                f"dominant, buy_streak={buy_streak}, buy_total_evidence={float(evidence_vector_v1.buy_total_evidence):.4f}"
            ),
            "sell_belief": (
                f"sell {_dominant_mode(sell_reversal_belief, sell_continuation_belief)} belief "
                f"dominant, sell_streak={sell_streak}, sell_total_evidence={float(evidence_vector_v1.sell_total_evidence):.4f}"
            ),
            "transition_age": (
                f"global dominant {dominant_side.lower()} {dominant_mode} age={transition_age}"
                if dominant_side != "BALANCED"
                else "belief spread inside deadband -> balanced"
            ),
            "flip_readiness": (
                f"prev={prev_dominant_side.lower()} -> current={dominant_side.lower()}, "
                f"old_side_decay={flip_components['old_side_decay']:.4f}, "
                f"opposite_side_rise={flip_components['opposite_side_rise']:.4f}, "
                f"transition_age={transition_age}"
            ),
            "belief_instability": (
                f"spread_instability={instability_components['spread_instability']:.4f}, "
                f"persistence_instability={instability_components['persistence_instability']:.4f}, "
                f"fresh_flip_instability={instability_components['fresh_flip_instability']:.4f}"
            ),
        }

        output = BeliefState(
            buy_belief=float(buy_belief),
            sell_belief=float(sell_belief),
            buy_persistence=float(buy_persistence),
            sell_persistence=float(sell_persistence),
            belief_spread=float(belief_spread),
            flip_readiness=float(flip_readiness),
            belief_instability=float(belief_instability),
            dominant_side=str(dominant_side),
            dominant_mode=str(dominant_mode),
            buy_streak=int(buy_streak),
            sell_streak=int(sell_streak),
            transition_age=int(transition_age),
            metadata={
                "belief_contract": "canonical_v1",
                "mapper_version": "belief_state_v1_b7",
                "semantic_owner_contract": _BELIEF_SEMANTIC_OWNER_CONTRACT,
                "belief_freeze_phase": _BELIEF_FREEZE_PHASE,
                "belief_pre_ml_phase": _BELIEF_PRE_ML_PHASE,
                "belief_role_statement": "Belief measures thesis persistence and reconfirmation over time.",
                "canonical_belief_identity_fields_v1": list(_BELIEF_CANONICAL_IDENTITY_FIELDS),
                "owner_boundaries_v1": dict(_BELIEF_OWNER_BOUNDARIES),
                "pre_ml_readiness_contract_v1": {
                    "phase": _BELIEF_PRE_ML_PHASE,
                    "status": "READY",
                    "required_feature_fields": list(_BELIEF_PRE_ML_REQUIRED_FEATURE_FIELDS),
                    "recommended_feature_fields": list(_BELIEF_PRE_ML_RECOMMENDED_FEATURE_FIELDS),
                    "semantic_explainable_without_ml": True,
                    "ml_usage_role": "feature_only_not_owner",
                    "owner_collision_allowed": False,
                    "owner_collision_boundary": (
                        "Belief may be consumed by ML as a calibration feature, "
                        "but ML must not redefine position identity, response event identity, "
                        "state regime identity, or direct action ownership."
                    ),
                    "safe_ml_targets": [
                        "wait_quality_calibration",
                        "entry_quality_calibration",
                        "hold_exit_patience_calibration",
                        "flip_readiness_calibration",
                    ],
                },
                "source_evidence_contract": str((evidence_vector_v1.metadata or {}).get("evidence_contract") or "canonical_v1"),
                "source_evidence_mapper_version": str((evidence_vector_v1.metadata or {}).get("mapper_version") or ""),
                "memory_key": {"symbol": memory_key[0], "timeframe": memory_key[1]},
                "memory_contract": {
                    "store_scope": "per_symbol_timeframe",
                    "key_fields": ["symbol", "timeframe"],
                    "mode_belief_fields": list(_BELIEF_MEMORY_MODE_FIELDS),
                    "streak_fields": list(_BELIEF_MEMORY_STREAK_FIELDS),
                    "transition_fields": list(_BELIEF_MEMORY_TRANSITION_FIELDS),
                    "duplicate_event_policy": "same_event_ts_returns_cached_output",
                },
                "update_contract": {
                    "belief_update_mode": "ema_rise_decay",
                    "persistence_mode": "activation_streak_window",
                    "side_dominance_mode": "belief_spread_deadband",
                    "mode_dominance_mode": "per_side_max_component",
                    "merge_mode": "capped_dominant_merge",
                },
                "window_bars": int(_BELIEF_PERSISTENCE_WINDOW),
                "alpha_rise": float(_BELIEF_ALPHA_RISE),
                "alpha_decay": float(_BELIEF_ALPHA_DECAY),
                "activation_threshold": float(_BELIEF_ACTIVATION_THRESHOLD),
                "advantage_threshold": float(_BELIEF_ADVANTAGE_THRESHOLD),
                "dominance_deadband": float(_BELIEF_DOMINANCE_DEADBAND),
                "merge_weight": float(_BELIEF_SUPPORT_WEIGHT),
                "buy_reversal_belief": float(buy_reversal_belief),
                "sell_reversal_belief": float(sell_reversal_belief),
                "buy_continuation_belief": float(buy_continuation_belief),
                "sell_continuation_belief": float(sell_continuation_belief),
                "buy_dominant_mode": _dominant_mode(buy_reversal_belief, buy_continuation_belief),
                "sell_dominant_mode": _dominant_mode(sell_reversal_belief, sell_continuation_belief),
                "global_dominant_side": dominant_side,
                "global_dominant_mode": dominant_mode,
                "buy_streak": int(buy_streak),
                "sell_streak": int(sell_streak),
                "prev_buy_belief": float(prev_buy_belief),
                "prev_sell_belief": float(prev_sell_belief),
                "prev_dominant_side": str(prev_dominant_side),
                "prev_dominant_mode": str(prev_dominant_mode),
                "recent_flip_side": str(recent_flip_side),
                "recent_flip_age": int(recent_flip_age),
                "flip_readiness": float(flip_readiness),
                "belief_instability": float(belief_instability),
                "flip_components_v1": dict(flip_components),
                "belief_instability_components_v1": dict(instability_components),
                "component_scores": {
                    "buy_total_evidence": float(evidence_vector_v1.buy_total_evidence),
                    "sell_total_evidence": float(evidence_vector_v1.sell_total_evidence),
                    "buy_dominant_component": float(buy_dominant_component),
                    "buy_support_component": float(buy_support_component),
                    "sell_dominant_component": float(sell_dominant_component),
                    "sell_support_component": float(sell_support_component),
                },
                "last_event_ts": None if event_ts is None else int(event_ts),
                "belief_reasons": belief_reasons,
            },
        )

        memory.update(
            {
                "buy_reversal_belief": float(buy_reversal_belief),
                "sell_reversal_belief": float(sell_reversal_belief),
                "buy_continuation_belief": float(buy_continuation_belief),
                "sell_continuation_belief": float(sell_continuation_belief),
                "buy_streak": int(buy_streak),
                "sell_streak": int(sell_streak),
                "dominant_side": dominant_side,
                "dominant_mode": dominant_mode,
                "transition_age": int(transition_age),
                "recent_flip_side": str(recent_flip_side),
                "recent_flip_age": int(recent_flip_age),
                "last_event_ts": None if event_ts is None else int(event_ts),
                "last_output": output.to_dict(),
            }
        )
        return output
