# 한글 설명: 런타임 상태 응답에서 정책 스냅샷과 learning_apply_loop 계산을 담당하는 분리 모듈입니다.
"""Policy/runtime split helpers for runtime status."""

from __future__ import annotations

from datetime import datetime


def build_policy_learning_state(*, Config, policy_snapshot: dict, payload, now_ts: float, _canonical_symbol, exit_blend_runtime: dict):
    symbol_policy_snapshot = {}
    symbol_default_snapshot = {}
    symbol_applied_vs_default = {}
    symbol_learning_split = {}

    try:
        symbol_policy_snapshot = dict((policy_snapshot or {}).get("symbol_policy_snapshot", {}) or {})
    except Exception:
        symbol_policy_snapshot = {}
    try:
        symbol_default_snapshot = dict((policy_snapshot or {}).get("symbol_default_snapshot", {}) or {})
    except Exception:
        symbol_default_snapshot = {}
    try:
        symbol_applied_vs_default = dict((policy_snapshot or {}).get("symbol_applied_vs_default", {}) or {})
    except Exception:
        symbol_applied_vs_default = {}
    try:
        policy_runtime = dict((policy_snapshot or {}).get("policy_runtime", {}) or {})
    except Exception:
        policy_runtime = {}
    try:
        policy_min_interval_sec = max(30.0, float(getattr(Config, "POLICY_UPDATE_MIN_INTERVAL_SEC", 900.0) or 900.0))
    except Exception:
        policy_min_interval_sec = 900.0

    def _iso_to_ts(text: str):
        try:
            if not text:
                return None
            norm = str(text).strip()
            if norm.endswith("Z"):
                norm = norm[:-1] + "+00:00"
            dt = datetime.fromisoformat(norm)
            return float(dt.timestamp())
        except Exception:
            return None

    runtime_updated_at = ""
    runtime_loop_count = 0
    if isinstance(payload, dict):
        try:
            runtime_updated_at = str(payload.get("updated_at", "") or "")
        except Exception:
            runtime_updated_at = ""
        try:
            runtime_loop_count = int(payload.get("loop_count", 0) or 0)
        except Exception:
            runtime_loop_count = 0

    policy_updated_at = str(policy_runtime.get("updated_at", "") or "")
    policy_updated_ts = _iso_to_ts(policy_updated_at)
    policy_age_sec = None
    if policy_updated_ts is not None:
        policy_age_sec = max(0.0, float(now_ts) - float(policy_updated_ts))

    policy_update_count = int(policy_runtime.get("policy_update_count", 0) or 0)
    policy_update_rejected_count = int(policy_runtime.get("policy_update_rejected_count", 0) or 0)
    policy_rollback_count = int(policy_runtime.get("rollback_count", 0) or 0)
    policy_guard_block_count = int(policy_runtime.get("policy_guard_block_count", 0) or 0)
    policy_reject_streak = int(policy_runtime.get("policy_update_reject_streak", 0) or 0)
    policy_blocked_until_ts = float(policy_runtime.get("policy_blocked_until_ts", 0.0) or 0.0)
    policy_blocked_until = str(policy_runtime.get("policy_blocked_until", "") or "")
    policy_blocked_remain_sec = max(0.0, float(policy_blocked_until_ts) - float(now_ts)) if policy_blocked_until_ts > 0 else 0.0

    if not policy_updated_at or policy_update_count <= 0:
        apply_status = "bootstrap"
    elif policy_blocked_remain_sec > 0.0:
        apply_status = "blocked"
    elif policy_age_sec is not None and policy_age_sec > (policy_min_interval_sec * 3.0):
        apply_status = "stale"
    elif policy_update_rejected_count > 0 or policy_rollback_count > 0:
        apply_status = "warn"
    else:
        apply_status = "ok"

    learning_apply_loop = {
        "status": apply_status,
        "runtime_updated_at": runtime_updated_at,
        "runtime_loop_count": int(runtime_loop_count),
        "policy_updated_at": policy_updated_at,
        "policy_age_sec": (round(float(policy_age_sec), 1) if policy_age_sec is not None else None),
        "policy_min_interval_sec": float(policy_min_interval_sec),
        "policy_next_refresh_eta_sec": (
            round(max(0.0, float(policy_min_interval_sec) - float(policy_age_sec)), 1)
            if policy_age_sec is not None
            else None
        ),
        "policy_update_count": int(policy_update_count),
        "policy_update_rejected_count": int(policy_update_rejected_count),
        "policy_rollback_count": int(policy_rollback_count),
        "policy_guard_block_count": int(policy_guard_block_count),
        "policy_update_reject_streak": int(policy_reject_streak),
        "policy_blocked_until": policy_blocked_until,
        "policy_blocked_remaining_sec": round(float(policy_blocked_remain_sec), 1),
        "last_update_skip_reason": str(policy_runtime.get("last_update_skip_reason", "") or ""),
        "last_guard_block_reason": str(policy_runtime.get("last_guard_block_reason", "") or ""),
        "last_rollback_reason": str(policy_runtime.get("last_rollback_reason", "") or ""),
        "sample_confidence": float(policy_runtime.get("sample_confidence", 0.0) or 0.0),
        "samples_total": int(policy_runtime.get("samples_total", 0) or 0),
        "fallback_applied": bool(policy_runtime.get("fallback_applied", False)),
    }

    try:
        raw_symbol_counts = dict(policy_runtime.get("symbol_counts", {}) or {})
    except Exception:
        raw_symbol_counts = {}

    canonical_counts = {}
    try:
        for k, v in raw_symbol_counts.items():
            ck = _canonical_symbol(k)
            canonical_counts[ck] = int(canonical_counts.get(ck, 0)) + int(v or 0)
    except Exception:
        canonical_counts = {}

    try:
        watch_symbols = tuple(getattr(Config, "WATCH_LIST", ["BTCUSD", "NAS100", "XAUUSD"]))
    except Exception:
        watch_symbols = ("BTCUSD", "NAS100", "XAUUSD")

    c2_symbols = sorted({_canonical_symbol(s) for s in watch_symbols if str(s).strip()})
    for sym in c2_symbols:
        sp = dict(symbol_policy_snapshot.get(sym, {}) or {})
        src_n = int(canonical_counts.get(sym, 0) or 0)
        pol_n = int(sp.get("sample_count", 0) or 0)
        reg_counts = dict(sp.get("regime_counts", {}) or {})
        dominant_regime = "UNKNOWN"
        if reg_counts:
            try:
                dominant_regime = str(max(reg_counts.items(), key=lambda kv: int(kv[1] or 0))[0])
            except Exception:
                dominant_regime = "UNKNOWN"
        symbol_learning_split[sym] = {
            "source_sample_count": int(src_n),
            "policy_sample_count": int(pol_n),
            "sample_gap": int(src_n - pol_n),
            "sample_match": bool(src_n == pol_n),
            "policy_scope": str(sp.get("policy_scope", "GLOBAL")),
            "sample_confidence": float(sp.get("sample_confidence", 0.0) or 0.0),
            "ready": bool(pol_n > 0),
            "regime_count": int(sum(1 for _, c in reg_counts.items() if int(c or 0) > 0)),
            "dominant_regime": dominant_regime,
            "regime_counts": reg_counts,
        }

    symbol_blend_runtime = {}
    try:
        symbol_blend_runtime = dict((exit_blend_runtime or {}).get("symbol_blend_runtime", {}) or {})
    except Exception:
        symbol_blend_runtime = {}

    return {
        "symbol_policy_snapshot": symbol_policy_snapshot,
        "symbol_default_snapshot": symbol_default_snapshot,
        "symbol_applied_vs_default": symbol_applied_vs_default,
        "symbol_learning_split": symbol_learning_split,
        "learning_apply_loop": learning_apply_loop,
        "symbol_blend_runtime": symbol_blend_runtime,
    }
