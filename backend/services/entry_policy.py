"""
Entry decision policies (OOP composition).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.core.config import Config


@dataclass
class EntryComponentSnapshot:
    entry_h1_context_score: int = 0
    entry_h1_context_opposite: int = 0
    entry_m1_trigger_score: int = 0
    entry_m1_trigger_opposite: int = 0


@dataclass
class GateResult:
    ok: bool
    reason: str


@dataclass
class TopDownGateResult:
    ok: bool
    reason: str
    align: int = 0
    conflict: int = 0
    seen: int = 0


class EntryComponentExtractor:
    @staticmethod
    def extract(result: dict, action: str) -> EntryComponentSnapshot:
        comps = (result or {}).get("components", {}) if isinstance(result, dict) else {}
        buy_h1 = int(pd.to_numeric(comps.get("h1_context_buy", 0), errors="coerce") or 0)
        sell_h1 = int(pd.to_numeric(comps.get("h1_context_sell", 0), errors="coerce") or 0)
        buy_m1 = int(pd.to_numeric(comps.get("m1_trigger_buy", 0), errors="coerce") or 0)
        sell_m1 = int(pd.to_numeric(comps.get("m1_trigger_sell", 0), errors="coerce") or 0)
        side = str(action or "").upper()
        if side == "BUY":
            return EntryComponentSnapshot(
                entry_h1_context_score=buy_h1,
                entry_h1_context_opposite=sell_h1,
                entry_m1_trigger_score=buy_m1,
                entry_m1_trigger_opposite=sell_m1,
            )
        return EntryComponentSnapshot(
            entry_h1_context_score=sell_h1,
            entry_h1_context_opposite=buy_h1,
            entry_m1_trigger_score=sell_m1,
            entry_m1_trigger_opposite=buy_m1,
        )


class H1EntryGatePolicy:
    def evaluate(self, action: str, h1_context_score: float, h1_context_opposite: float) -> GateResult:
        if not bool(getattr(Config, "ENABLE_H1_ENTRY_GATE", True)):
            return GateResult(ok=True, reason="h1_gate_disabled")
        side = str(action or "").upper()
        if side not in {"BUY", "SELL"}:
            return GateResult(ok=True, reason="h1_gate_no_action")

        ctx = int(pd.to_numeric(h1_context_score, errors="coerce") or 0)
        opp = int(pd.to_numeric(h1_context_opposite, errors="coerce") or 0)
        min_ctx = max(0, int(getattr(Config, "H1_ENTRY_GATE_MIN_CONTEXT", 20)))
        strict = bool(getattr(Config, "H1_ENTRY_GATE_STRICT", True))
        min_gap = max(0, int(getattr(Config, "H1_ENTRY_GATE_MIN_GAP", 8)))

        if ctx < min_ctx:
            return GateResult(ok=False, reason=f"h1_gate_context_low({ctx}<{min_ctx})")
        if strict and ((ctx - opp) < min_gap):
            return GateResult(ok=False, reason=f"h1_gate_gap_low({ctx - opp}<{min_gap})")
        return GateResult(ok=True, reason=f"h1_gate_pass({ctx}/{opp})")


class TopDownEntryGatePolicy:
    def evaluate(self, result: dict, action: str) -> TopDownGateResult:
        stack = (result or {}).get("timeframe_stack", {}) if isinstance(result, dict) else {}
        side = str(action or "").upper()
        if side not in {"BUY", "SELL"}:
            return TopDownGateResult(ok=True, reason="topdown_no_action")
        if not bool(getattr(Config, "ENABLE_TOPDOWN_TIMEFRAME_GATE", True)):
            return TopDownGateResult(ok=True, reason="topdown_gate_disabled")

        target = side.lower()
        align = 0
        conflict = 0
        seen = 0

        def _extract_bias(node) -> str:
            # Backward-compatible parser:
            # - new/legacy dict form: {"bias": "..."}
            # - compact form: "buy"/"sell"/"neutral"
            if isinstance(node, dict):
                raw = node.get("bias", "neutral")
            else:
                raw = node
            bias_v = str(raw or "neutral").lower().strip()
            if bias_v in {"bull", "bullish", "long"}:
                bias_v = "buy"
            elif bias_v in {"bear", "bearish", "short"}:
                bias_v = "sell"
            if bias_v not in {"buy", "sell", "neutral"}:
                bias_v = "neutral"
            return bias_v

        for tf in ("1D", "4H", "2H", "1H"):
            node = stack.get(tf, {}) if isinstance(stack, dict) else {}
            bias = _extract_bias(node)
            if bias == "neutral":
                continue
            seen += 1
            if bias == target:
                align += 1
            else:
                conflict += 1

        min_align = max(0, int(getattr(Config, "TOPDOWN_HIGHER_TF_MIN_ALIGN", 2)))
        max_conflict = max(0, int(getattr(Config, "TOPDOWN_HIGHER_TF_MAX_CONFLICT", 1)))
        if align < min_align:
            return TopDownGateResult(
                ok=False,
                reason=f"topdown_align_low({align}<{min_align})",
                align=align,
                conflict=conflict,
                seen=seen,
            )
        if conflict > max_conflict:
            return TopDownGateResult(
                ok=False,
                reason=f"topdown_conflict_high({conflict}>{max_conflict})",
                align=align,
                conflict=conflict,
                seen=seen,
            )
        return TopDownGateResult(
            ok=True,
            reason=f"topdown_pass(align={align},conflict={conflict},seen={seen})",
            align=align,
            conflict=conflict,
            seen=seen,
        )
