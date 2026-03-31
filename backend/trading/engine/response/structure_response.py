from __future__ import annotations

from backend.trading.engine.core.models import EngineContext


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_structure_responses(ctx: EngineContext) -> dict[str, float]:
    md = dict(ctx.metadata or {})
    open_now = _to_float(md.get("current_open"), ctx.price)
    high_now = _to_float(md.get("current_high"), ctx.price)
    low_now = _to_float(md.get("current_low"), ctx.price)
    close_now = _to_float(md.get("current_close"), ctx.price)
    box_tol = max(abs(_to_float(md.get("box_touch_tolerance"), 0.0)), 1e-9)

    out = {
        "r_box_lower_bounce": 0.0,
        "r_box_lower_break": 0.0,
        "r_box_mid_hold": 0.0,
        "r_box_mid_reject": 0.0,
        "r_box_upper_reject": 0.0,
        "r_box_upper_break": 0.0,
    }

    lower_edge_bias = str(ctx.bb_state or "UNKNOWN").upper() in {"LOWER_EDGE", "BREAKDOWN"} or str(ctx.box_state or "UNKNOWN").upper() in {"LOWER", "BELOW"}

    if ctx.box_low is not None and ctx.box_high is not None:
        box_mid = (float(ctx.box_low) + float(ctx.box_high)) / 2.0
        box_half = max((float(ctx.box_high) - float(ctx.box_low)) / 2.0, 1e-9)
        close_dist = abs(close_now - box_mid) / box_half
        close_prox = _clamp01(1.0 - close_dist / 0.70)
        low_hold_ok = low_now >= box_mid - box_half * 0.28
        high_reject_ok = high_now <= box_mid + box_half * 0.28
        if close_now >= box_mid and close_now >= open_now and low_hold_ok and close_prox > 0.0:
            out["r_box_mid_hold"] = max(out["r_box_mid_hold"], close_prox * 0.65)
        elif close_now <= box_mid and close_now <= open_now and high_reject_ok and close_prox > 0.0:
            out["r_box_mid_reject"] = max(out["r_box_mid_reject"], close_prox * 0.65)

        if low_now <= box_mid + box_tol and close_now >= box_mid and close_now >= open_now:
            out["r_box_mid_hold"] = 1.0
        elif high_now >= box_mid - box_tol and close_now <= box_mid and close_now <= open_now:
            out["r_box_mid_reject"] = 1.0

        if lower_edge_bias and out["r_box_mid_reject"] > 0.0:
            if close_now >= open_now or low_now <= (float(ctx.box_low) + box_half * 0.30):
                out["r_box_mid_reject"] *= 0.12
            else:
                out["r_box_mid_reject"] *= 0.25

    if ctx.box_low is not None:
        box_low = float(ctx.box_low)
        close_back_inside = close_now >= box_low - (box_tol * 0.25)
        if close_now < box_low - box_tol:
            out["r_box_lower_break"] = 1.0
        elif low_now <= box_low + box_tol and close_back_inside and close_now >= open_now:
            out["r_box_lower_bounce"] = 1.0
    if ctx.box_low is not None and ctx.box_high is not None:
        box_low = float(ctx.box_low)
        box_half = max((float(ctx.box_high) - box_low) / 2.0, 1e-9)
        lower_box_dist = abs(close_now - box_low) / box_half
        lower_box_prox = _clamp01(1.0 - lower_box_dist / 0.95)
        lower_wick = max(0.0, min(open_now, close_now) - low_now)
        body = max(abs(close_now - open_now), box_tol)
        close_back_inside = close_now >= box_low - (box_tol * 0.25)
        wick_reject = lower_wick >= max(body * 0.35, box_tol)
        if (
            lower_box_prox > 0.0
            and close_now >= box_low - box_tol
            and ((close_back_inside and close_now >= open_now) or wick_reject)
        ):
            bounce_strength = min(0.8, lower_box_prox * 0.58)
            if not close_back_inside:
                bounce_strength = min(bounce_strength, 0.35)
            out["r_box_lower_bounce"] = max(out["r_box_lower_bounce"], bounce_strength)

    if ctx.box_high is not None:
        box_high = float(ctx.box_high)
        upper_wick = max(0.0, high_now - max(open_now, close_now))
        body = max(abs(close_now - open_now), box_tol)
        close_back_inside = close_now <= box_high + (box_tol * 0.35)
        close_red = close_now <= open_now
        wick_reject = upper_wick >= max(body * 0.6, box_tol * 1.5)

        if close_now > box_high + box_tol:
            out["r_box_upper_break"] = 1.0
        elif high_now >= box_high - box_tol and close_back_inside and (close_red or wick_reject):
            out["r_box_upper_reject"] = 1.0 if close_red else max(out["r_box_upper_reject"], 0.7)
        elif high_now >= box_high - box_tol and close_now <= open_now:
            out["r_box_upper_reject"] = 1.0 if close_back_inside else max(out["r_box_upper_reject"], 0.35)

    return out
