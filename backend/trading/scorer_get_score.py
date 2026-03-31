# 파일 설명: Scorer의 메인 스코어 계산(get_score) 흐름을 분리한 모듈입니다.
"""get_score helper extracted from Scorer."""

from __future__ import annotations

from backend.core.config import Config
from backend.trading.scorer_helpers import collect_timeframe_rows, empty_score_result

def get_score(self, symbol, tick, df_all):
    empty_result = empty_score_result()

    if not tick:
        return empty_result

    price = float(tick.bid)
    spread = float(tick.ask - tick.bid)

    spread_limit = self._get_spread_limit(symbol, price)
    if spread > spread_limit:
        return empty_result

    h1 = df_all.get("1H")
    m15 = df_all.get("15M")
    m1 = df_all.get("1M")
    d1 = df_all.get("1D")
    if h1 is None or m15 is None or h1.empty or m15.empty:
        return empty_result

    m15 = self.trend_mgr.add_indicators(m15)
    if m15 is None or m15.empty:
        return empty_result
    h1_ind = self.trend_mgr.add_indicators(h1.copy())
    if h1_ind is None or h1_ind.empty:
        h1_ind = h1

    current = m15.iloc[-1]
    h1_current = h1_ind.iloc[-1] if h1_ind is not None and not h1_ind.empty else None

    buy_score = 0
    sell_score = 0
    wait_score = 0
    buy_reasons = []
    sell_reasons = []
    wait_reasons = []

    structure = self._analyze_structure(h1, d1, price, m15=m15)
    buy_score += int(structure["buy_score"])
    sell_score += int(structure["sell_score"])
    buy_reasons.extend(structure["buy_reasons"])
    sell_reasons.extend(structure["sell_reasons"])

    flow = self._analyze_flow(symbol, current, price, m15=m15, h1_current=h1_current)
    buy_score += int(flow["buy_score"])
    sell_score += int(flow["sell_score"])
    wait_score += int(flow.get("wait_score", 0) or 0)
    buy_reasons.extend(flow["buy_reasons"])
    sell_reasons.extend(flow["sell_reasons"])
    wait_reasons.extend(list(flow.get("wait_reasons", []) or []))

    vp = self._analyze_volume_profile(symbol, price, current)
    buy_score += int(vp["buy_score"])
    sell_score += int(vp["sell_score"])
    buy_reasons.extend(vp["buy_reasons"])
    sell_reasons.extend(vp["sell_reasons"])

    trigger = self._analyze_trigger(current, m1)
    buy_score += int(trigger["buy_score"])
    sell_score += int(trigger["sell_score"])
    buy_reasons.extend(trigger["buy_reasons"])
    sell_reasons.extend(trigger["sell_reasons"])

    tf_rows = collect_timeframe_rows(df_all=df_all, trend_mgr=self.trend_mgr)
    topdown = self._analyze_topdown_context(tf_rows=tf_rows, price=price)
    buy_score += int(topdown.get("buy_score", 0) or 0)
    sell_score += int(topdown.get("sell_score", 0) or 0)
    buy_reasons.extend(list(topdown.get("buy_reasons", []) or []))
    sell_reasons.extend(list(topdown.get("sell_reasons", []) or []))

    pri_structure = float(getattr(Config, "ENTRY_PRIORITY_STRUCTURE", 1.0))
    pri_flow = float(getattr(Config, "ENTRY_PRIORITY_FLOW", 1.0))
    pri_vp = float(getattr(Config, "ENTRY_PRIORITY_VP", 1.0))
    pri_trigger = float(getattr(Config, "ENTRY_PRIORITY_TRIGGER", 1.0))

    family_mult = self._get_entry_family_multipliers(symbol)
    if family_mult:
        structure_m = float(family_mult.get("structure", 1.0))
        flow_m = float(family_mult.get("flow", 1.0))
        vp_m = float(family_mult.get("vp", 1.0))
        trigger_m = float(family_mult.get("trigger", 1.0))
        buy_parts = self._rebalance_family_scores(
            {
                "structure": (float(structure["buy_score"]) * structure_m * pri_structure),
                "flow": (float(flow["buy_score"]) * flow_m * pri_flow),
                "vp": (float(vp["buy_score"]) * vp_m * pri_vp),
                "trigger": (float(trigger["buy_score"]) * trigger_m * pri_trigger),
            }
        )
        sell_parts = self._rebalance_family_scores(
            {
                "structure": (float(structure["sell_score"]) * structure_m * pri_structure),
                "flow": (float(flow["sell_score"]) * flow_m * pri_flow),
                "vp": (float(vp["sell_score"]) * vp_m * pri_vp),
                "trigger": (float(trigger["sell_score"]) * trigger_m * pri_trigger),
            }
        )
        buy_score = int(round(sum(float(v) for v in buy_parts.values())))
        sell_score = int(round(sum(float(v) for v in sell_parts.values())))
        learn_reason = f"Learned: S/F/VP/T x{structure_m:.2f}/{flow_m:.2f}/{vp_m:.2f}/{trigger_m:.2f}"
        buy_reasons.append(learn_reason)
        sell_reasons.append(learn_reason)
        fmeta = self._get_entry_feature_meta(symbol)
        if fmeta:
            f_reason = (
                "FeatureLearn: "
                + f"session={float(fmeta.get('session_mult_avg', 1.0)):.3f}, "
                + f"atr={float(fmeta.get('atr_ratio_avg', 1.0)):.3f}, "
                + f"slip={float(fmeta.get('slippage_points_avg', 0.0)):.2f}, "
                + f"w={float(fmeta.get('runtime_weight_avg', 1.0)):.3f}"
            )
            buy_reasons.append(f_reason)
            sell_reasons.append(f_reason)
        if not (
            abs(pri_structure - 1.0) < 1e-9
            and abs(pri_flow - 1.0) < 1e-9
            and abs(pri_vp - 1.0) < 1e-9
            and abs(pri_trigger - 1.0) < 1e-9
        ):
            pri_reason = f"Priority: S/F/VP/T x{pri_structure:.2f}/{pri_flow:.2f}/{pri_vp:.2f}/{pri_trigger:.2f}"
            buy_reasons.append(pri_reason)
            sell_reasons.append(pri_reason)

    buy_score, sell_score, buy_reasons, sell_reasons, regime = self._apply_market_regime_adjustment(
        m15=m15,
        spread=spread,
        spread_limit=spread_limit,
        buy_score=buy_score,
        sell_score=sell_score,
        buy_reasons=buy_reasons,
        sell_reasons=sell_reasons,
    )

    return {
        "buy": {"total": int(buy_score), "reasons": buy_reasons},
        "sell": {"total": int(sell_score), "reasons": sell_reasons},
        "wait": {"total": int(wait_score), "reasons": wait_reasons},
        "components": {
            "h1_context_buy": int(flow.get("h1_context_buy_score", 0) or 0),
            "h1_context_sell": int(flow.get("h1_context_sell_score", 0) or 0),
            "m1_trigger_buy": int(trigger.get("m1_trigger_buy_score", 0) or 0),
            "m1_trigger_sell": int(trigger.get("m1_trigger_sell_score", 0) or 0),
            "wait_score": int(wait_score),
            "wait_conflict": int(flow.get("wait_conflict_score", 0) or 0),
            "wait_noise": int(flow.get("wait_noise_score", 0) or 0),
        },
        "timeframe_stack": dict(topdown.get("stack", {}) or {}),
        "regime": regime,
    }
