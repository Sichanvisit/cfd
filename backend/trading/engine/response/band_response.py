from __future__ import annotations

from backend.trading.engine.core.models import EngineContext


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _near(price: float, level: float | None, tol: float) -> bool:
    if level is None:
        return False
    return abs(price - float(level)) <= abs(tol)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_band_responses(ctx: EngineContext) -> dict[str, float]:
    md = dict(ctx.metadata or {})
    open_now = _to_float(md.get("current_open"), ctx.price)
    high_now = _to_float(md.get("current_high"), ctx.price)
    low_now = _to_float(md.get("current_low"), ctx.price)
    close_now = _to_float(md.get("current_close"), ctx.price)
    prev_close = _to_float(md.get("previous_close"), close_now)
    band_tol = max(abs(_to_float(md.get("band_touch_tolerance"), 0.0)), 1e-9)

    out = {
        "r_bb20_lower_hold": 0.0,
        "r_bb20_lower_break": 0.0,
        "r_bb20_mid_hold": 0.0,
        "r_bb20_mid_reclaim": 0.0,
        "r_bb20_mid_reject": 0.0,
        "r_bb20_mid_lose": 0.0,
        "r_bb20_upper_reject": 0.0,
        "r_bb20_upper_break": 0.0,
        "r_bb44_lower_hold": 0.0,
        "r_bb44_upper_reject": 0.0,
    }

    lower_wick = max(0.0, min(open_now, close_now) - low_now)
    upper_wick = max(0.0, high_now - max(open_now, close_now))
    body = max(abs(close_now - open_now), band_tol)

    # 20/2 lower band hold / break
    if ctx.bb20_dn is not None:
        bb20_dn = float(ctx.bb20_dn)
        close_back_inside = close_now >= bb20_dn - (band_tol * 0.25)
        if close_now < bb20_dn - band_tol:
            out["r_bb20_lower_break"] = 1.0
        elif low_now <= bb20_dn + band_tol and close_back_inside and close_now >= open_now:
            out["r_bb20_lower_hold"] = 1.0

    if ctx.bb20_mid is not None and ctx.bb20_up is not None and ctx.bb20_dn is not None:
        bb20_dn = float(ctx.bb20_dn)
        half_20 = max((float(ctx.bb20_up) - bb20_dn) / 2.0, 1e-9)
        lower_close_dist = abs(close_now - bb20_dn) / half_20
        lower_low_dist = abs(low_now - bb20_dn) / half_20
        lower_close_prox = _clamp01(1.0 - lower_close_dist / 0.95)
        lower_touch_prox = _clamp01(1.0 - lower_low_dist / 0.70)
        lower_wick_reject = lower_wick >= max(body * 0.45, band_tol * 1.2)
        lower_green_hold = close_now >= open_now and close_now >= (low_now + body * 0.18)
        close_back_inside = close_now >= bb20_dn - (band_tol * 0.25)
        if (
            lower_close_prox > 0.0
            and close_now >= bb20_dn - band_tol
            and ((close_back_inside and lower_green_hold) or lower_wick_reject)
        ):
            hold_strength = max(lower_close_prox * 0.62, lower_touch_prox * 0.78)
            if lower_wick_reject:
                hold_strength = max(hold_strength, lower_close_prox * 0.82)
            if not close_back_inside:
                hold_strength = min(hold_strength, 0.35)
            out["r_bb20_lower_hold"] = max(out["r_bb20_lower_hold"], min(1.0, hold_strength))

    # 20/2 midline hold / reject / reclaim / lose
    if ctx.bb20_mid is not None and ctx.bb20_up is not None and ctx.bb20_dn is not None:
        mid_20 = float(ctx.bb20_mid)
        half_20 = max((float(ctx.bb20_up) - float(ctx.bb20_dn)) / 2.0, 1e-9)
        close_dist = abs(close_now - mid_20) / half_20
        close_prox = _clamp01(1.0 - close_dist / 0.70)
        low_support_ok = low_now >= mid_20 - half_20 * 0.32
        high_reject_ok = high_now <= mid_20 + half_20 * 0.32

        if close_now >= mid_20 and close_now >= open_now and low_support_ok and close_prox > 0.0:
            out["r_bb20_mid_hold"] = max(out["r_bb20_mid_hold"], close_prox * 0.70)
        if close_now <= mid_20 and close_now <= open_now and high_reject_ok and close_prox > 0.0:
            out["r_bb20_mid_reject"] = max(out["r_bb20_mid_reject"], close_prox * 0.70)

    if (
        ctx.bb20_mid is not None
        and low_now <= float(ctx.bb20_mid) + band_tol
        and close_now >= float(ctx.bb20_mid)
        and close_now >= open_now
    ):
        out["r_bb20_mid_hold"] = 1.0
    elif (
        ctx.bb20_mid is not None
        and high_now >= float(ctx.bb20_mid) - band_tol
        and close_now <= float(ctx.bb20_mid)
        and close_now <= open_now
    ):
        out["r_bb20_mid_reject"] = 1.0

    if ctx.bb20_mid is not None and prev_close < float(ctx.bb20_mid) <= close_now:
        out["r_bb20_mid_reclaim"] = 1.0
    elif ctx.bb20_mid is not None and prev_close > float(ctx.bb20_mid) >= close_now:
        out["r_bb20_mid_lose"] = 1.0

    # 20/2 upper band reject / break
    if ctx.bb20_up is not None:
        bb20_up = float(ctx.bb20_up)
        close_back_inside = close_now <= bb20_up + (band_tol * 0.35)
        close_red = close_now <= open_now and close_now <= prev_close
        wick_reject = upper_wick >= max(body * 0.6, band_tol * 1.5)

        if close_now > bb20_up + band_tol:
            out["r_bb20_upper_break"] = 1.0
        elif high_now >= bb20_up - band_tol and close_back_inside and (close_red or wick_reject):
            out["r_bb20_upper_reject"] = 1.0 if close_red else max(out["r_bb20_upper_reject"], 0.7)
        elif high_now >= bb20_up - band_tol and close_now <= open_now:
            out["r_bb20_upper_reject"] = 1.0 if close_back_inside else max(out["r_bb20_upper_reject"], 0.35)

    # 4/4 is used as a secondary, more sensitive confirmation layer.
    if _near(low_now, ctx.bb44_dn, band_tol * 0.8) and close_now >= open_now:
        out["r_bb44_lower_hold"] = 1.0
    elif ctx.bb44_dn is not None and ctx.bb44_up is not None:
        half_44 = max((float(ctx.bb44_up) - float(ctx.bb44_dn)) / 2.0, 1e-9)
        lower44_dist = abs(close_now - float(ctx.bb44_dn)) / half_44
        lower44_prox = _clamp01(1.0 - lower44_dist / 1.05)
        lower44_reject = lower_wick >= max(body * 0.35, band_tol)
        if lower44_prox > 0.0 and (close_now >= open_now or lower44_reject):
            out["r_bb44_lower_hold"] = max(out["r_bb44_lower_hold"], min(0.75, lower44_prox * 0.55))
    if _near(high_now, ctx.bb44_up, band_tol * 0.8) and close_now <= open_now:
        out["r_bb44_upper_reject"] = 1.0

    return out
