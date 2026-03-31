"""
Policy orchestration for adaptive thresholds and risk rules.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import time

import pandas as pd
from ports.closed_trade_read_port import ClosedTradeReadPort


class PolicyService:
    def __init__(self, trade_logger: ClosedTradeReadPort, config):
        self.trade_logger = trade_logger
        self.config = config
        self.entry_threshold = int(config.ENTRY_THRESHOLD)
        self.exit_threshold = int(config.EXIT_THRESHOLD)
        self.adverse_loss_usd = float(config.ADVERSE_LOSS_USD)
        self.reverse_signal_threshold = int(config.REVERSE_SIGNAL_THRESHOLD)
        self.exit_policy = {
            "score_multiplier": {"Reversal": 1.0},
            "profit_multiplier": {"RSI Scalp": 1.0, "BB Scalp": 1.0},
            "stats": {},
        }
        self._default_entry_threshold = int(config.ENTRY_THRESHOLD)
        self._default_exit_threshold = int(config.EXIT_THRESHOLD)
        self._default_adverse_loss_usd = float(config.ADVERSE_LOSS_USD)
        self._default_reverse_signal_threshold = int(config.REVERSE_SIGNAL_THRESHOLD)
        self._symbol_default_overrides = {}
        self._symbol_states = {}
        for sym in tuple(getattr(config, "WATCH_LIST", ["BTCUSD", "NAS100", "XAUUSD"])):
            cs = self._canonical_symbol(sym)
            if cs:
                self._symbol_default_overrides[cs] = self._resolve_symbol_defaults(cs)
                self._symbol_states[cs] = self._new_symbol_state(cs)
        self._policy_runtime = {
            "updated_at": None,
            "samples_total": 0,
            "sample_confidence": 0.0,
            "symbol_counts": {},
            "regime_counts": {},
            "fallback_applied": False,
            "fallback_reasons": [],
            "symbol_policy_snapshot": {},
            "fallback_scope_used_counts": {},
            "policy_update_count": 0,
            "policy_update_rejected_count": 0,
            "rollback_count": 0,
            "policy_guard_block_count": 0,
            "policy_update_reject_streak": 0,
            "policy_blocked_until_ts": 0.0,
            "policy_blocked_until": "",
            "last_rollback_reason": "",
            "last_update_skip_reason": "",
            "last_guard_block_reason": "",
            "shock_ops": {
                "last_report_at": "",
                "last_tuning_at": "",
                "last_report_path": "",
                "last_report_rows": 0,
                "last_skip_reason": "",
                "weekly_tuning_applied": False,
                "watch_threshold": float(getattr(config, "SHOCK_LEVEL_WATCH_THRESHOLD", 35.0)),
                "alert_threshold": float(getattr(config, "SHOCK_LEVEL_ALERT_THRESHOLD", 60.0)),
            },
        }
        self._last_policy_update_at = 0.0
        self._last_shock_report_at = 0.0
        self._last_shock_tuning_at = 0.0
        self._last_applied_snapshot = self._snapshot_state()

    @staticmethod
    def _canonical_symbol(value: str) -> str:
        text = str(value or "").upper()
        if "BTC" in text:
            return "BTCUSD"
        if "NAS" in text or "US100" in text or "USTEC" in text:
            return "NAS100"
        if "XAU" in text or "GOLD" in text:
            return "XAUUSD"
        return text.strip()

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(float(lo), min(float(hi), float(v)))

    def _blend(self, current: float, target: float, alpha: float) -> float:
        a = self._clamp(alpha, 0.05, 1.0)
        return ((1.0 - a) * float(current)) + (a * float(target))

    def _new_symbol_state(self, symbol: str) -> dict:
        sym = str(symbol or "").upper()
        defaults = self._symbol_default_overrides.get(sym) or self._resolve_symbol_defaults(sym)
        return {
            "symbol": sym,
            "entry_threshold": int(defaults["entry_threshold"]),
            "exit_threshold": int(defaults["exit_threshold"]),
            "adverse_loss_usd": float(defaults["adverse_loss_usd"]),
            "reverse_signal_threshold": int(defaults["reverse_signal_threshold"]),
            "exit_policy": deepcopy(self.exit_policy),
            "policy_scope": "GLOBAL",
            "sample_confidence": 0.0,
            "sample_count": 0,
            "regime_counts": {},
            "updated_at": None,
        }

    def _value_by_symbol(self, mapping: dict, symbol: str, fallback):
        sym = str(symbol or "").upper().strip()
        if not isinstance(mapping, dict):
            return fallback
        if sym in mapping:
            return mapping[sym]
        return mapping.get("DEFAULT", fallback)

    def _resolve_symbol_defaults(self, symbol: str) -> dict:
        sym = self._canonical_symbol(symbol)
        return {
            "entry_threshold": int(
                self._value_by_symbol(
                    getattr(self.config, "ENTRY_THRESHOLD_BY_SYMBOL", {}),
                    sym,
                    self._default_entry_threshold,
                )
            ),
            "exit_threshold": int(
                self._value_by_symbol(
                    getattr(self.config, "EXIT_THRESHOLD_BY_SYMBOL", {}),
                    sym,
                    self._default_exit_threshold,
                )
            ),
            "adverse_loss_usd": float(
                self._value_by_symbol(
                    getattr(self.config, "ADVERSE_LOSS_USD_BY_SYMBOL", {}),
                    sym,
                    self._default_adverse_loss_usd,
                )
            ),
            "reverse_signal_threshold": int(
                self._value_by_symbol(
                    getattr(self.config, "REVERSE_SIGNAL_THRESHOLD_BY_SYMBOL", {}),
                    sym,
                    self._default_reverse_signal_threshold,
                )
            ),
        }

    def _snapshot_state(self) -> dict:
        return {
            "entry_threshold": int(self.entry_threshold),
            "exit_threshold": int(self.exit_threshold),
            "adverse_loss_usd": float(self.adverse_loss_usd),
            "reverse_signal_threshold": int(self.reverse_signal_threshold),
            "exit_policy": deepcopy(self.exit_policy),
            "symbol_states": deepcopy(self._symbol_states),
        }

    def _restore_state(self, snap: dict) -> None:
        if not isinstance(snap, dict):
            return
        self.entry_threshold = int(snap.get("entry_threshold", self.entry_threshold))
        self.exit_threshold = int(snap.get("exit_threshold", self.exit_threshold))
        self.adverse_loss_usd = float(snap.get("adverse_loss_usd", self.adverse_loss_usd))
        self.reverse_signal_threshold = int(snap.get("reverse_signal_threshold", self.reverse_signal_threshold))
        self.exit_policy = deepcopy(snap.get("exit_policy", self.exit_policy))
        self._symbol_states = deepcopy(snap.get("symbol_states", self._symbol_states))

    def _apply_update_guards(self, prev: dict) -> tuple[bool, str]:
        max_pct = float(getattr(self.config, "POLICY_UPDATE_MAX_CHANGE_PCT", 0.10))
        max_pct = self._clamp(max_pct, 0.01, 0.50)
        checks = [
            ("entry_threshold", float(prev.get("entry_threshold", self.entry_threshold)), float(self.entry_threshold)),
            ("exit_threshold", float(prev.get("exit_threshold", self.exit_threshold)), float(self.exit_threshold)),
            ("adverse_loss_usd", float(prev.get("adverse_loss_usd", self.adverse_loss_usd)), float(self.adverse_loss_usd)),
            ("reverse_signal_threshold", float(prev.get("reverse_signal_threshold", self.reverse_signal_threshold)), float(self.reverse_signal_threshold)),
        ]
        for key, old_v, new_v in checks:
            base = max(1.0, abs(float(old_v)))
            pct = abs(float(new_v) - float(old_v)) / base
            if pct > float(max_pct):
                return False, f"policy_update_cap_exceeded:{key}:{pct:.4f}>{max_pct:.4f}"
        return True, ""

    def _apply_soft_update_cap(self, prev: dict, notes: list[str]) -> None:
        """
        Limit one-cycle policy jumps before hard guard check.
        This keeps updates gradual and prevents avoidable rollbacks.
        """
        max_pct = float(getattr(self.config, "POLICY_UPDATE_MAX_CHANGE_PCT", 0.10))
        max_pct = self._clamp(max_pct, 0.01, 0.50)

        def _cap_value(old_v: float, new_v: float, min_band: float = 0.0) -> tuple[float, bool]:
            old_f = float(old_v)
            new_f = float(new_v)
            band = abs(old_f) * float(max_pct)
            if band < float(min_band):
                band = float(min_band)
            lo = old_f - band
            hi = old_f + band
            capped = max(lo, min(hi, new_f))
            return capped, (abs(capped - new_f) > 1e-9)

        e_old = float(prev.get("entry_threshold", self.entry_threshold))
        e_new, e_changed = _cap_value(e_old, float(self.entry_threshold), min_band=1.0)
        self.entry_threshold = int(round(e_new))

        x_old = float(prev.get("exit_threshold", self.exit_threshold))
        x_new, x_changed = _cap_value(x_old, float(self.exit_threshold), min_band=1.0)
        self.exit_threshold = int(round(x_new))

        a_old = float(prev.get("adverse_loss_usd", self.adverse_loss_usd))
        a_new, a_changed = _cap_value(a_old, float(self.adverse_loss_usd), min_band=0.0)
        self.adverse_loss_usd = float(round(a_new, 4))

        r_old = float(prev.get("reverse_signal_threshold", self.reverse_signal_threshold))
        r_new, r_changed = _cap_value(r_old, float(self.reverse_signal_threshold), min_band=1.0)
        self.reverse_signal_threshold = int(round(r_new))

        if e_changed or x_changed or a_changed or r_changed:
            notes.append(
                "policy soft-cap applied: "
                f"entry={int(round(e_old))}->{self.entry_threshold}, "
                f"exit={int(round(x_old))}->{self.exit_threshold}, "
                f"adverse={a_old:.4f}->{self.adverse_loss_usd:.4f}, "
                f"reverse={int(round(r_old))}->{self.reverse_signal_threshold}"
            )

    def _state_for_symbol(self, symbol: str) -> dict:
        cs = self._canonical_symbol(symbol)
        if cs not in self._symbol_states:
            self._symbol_default_overrides[cs] = self._resolve_symbol_defaults(cs)
            self._symbol_states[cs] = self._new_symbol_state(cs)
        return self._symbol_states[cs]

    def _sample_summary(self) -> tuple[int, dict, dict, dict]:
        reader = getattr(self.trade_logger, "read_closed_df", None)
        if not callable(reader):
            return 0, {}, {}, {}
        try:
            closed = reader()
        except Exception:
            return 0, {}, {}, {}
        if closed is None or closed.empty:
            return 0, {}, {}, {}
        frame = closed.copy()
        frame["symbol"] = frame.get("symbol", "").fillna("").astype(str).map(self._canonical_symbol)
        frame["exit_policy_regime"] = frame.get("exit_policy_regime", "").fillna("").astype(str).str.upper().str.strip()
        frame = frame[frame["symbol"].astype(str).str.strip() != ""].copy()
        if frame.empty:
            return 0, {}, {}, {}
        symbol_counts = frame["symbol"].value_counts().to_dict()
        regime_col = frame["exit_policy_regime"].where(frame["exit_policy_regime"] != "", "UNKNOWN")
        regime_counts = regime_col.value_counts().to_dict()
        symbol_regime_counts = {}
        for sym, grp in frame.groupby("symbol"):
            rs = grp["exit_policy_regime"].where(grp["exit_policy_regime"] != "", "UNKNOWN").value_counts().to_dict()
            symbol_regime_counts[str(sym)] = {str(k): int(v) for k, v in rs.items()}
        return (
            int(len(frame)),
            {str(k): int(v) for k, v in symbol_counts.items()},
            {str(k): int(v) for k, v in regime_counts.items()},
            symbol_regime_counts,
        )

    def _fallback_adjust(self, notes: list[str], sample_summary: tuple[int, dict, dict, dict] | None = None) -> None:
        total_n, symbol_counts, regime_counts, symbol_regime_counts = sample_summary or self._sample_summary()
        target_n = max(1, int(getattr(self.config, "POLICY_ADAPTIVE_TARGET_SAMPLES", 160)))
        alpha = float(getattr(self.config, "POLICY_ADAPTIVE_EMA_ALPHA", 0.35))
        min_symbol_n = max(1, int(getattr(self.config, "POLICY_ADAPTIVE_MIN_SYMBOL_SAMPLES", 20)))
        min_regime_n = max(1, int(getattr(self.config, "POLICY_ADAPTIVE_MIN_REGIME_SAMPLES", 20)))

        confidence = self._clamp(float(total_n) / float(target_n), 0.0, 1.0)
        fallback_reasons = []
        if total_n < target_n:
            fallback_reasons.append(f"low_total_samples({total_n}<{target_n})")
        if symbol_counts and min(symbol_counts.values()) < min_symbol_n:
            fallback_reasons.append(f"low_symbol_samples(min<{min_symbol_n})")
        if regime_counts and min(regime_counts.values()) < min_regime_n:
            fallback_reasons.append(f"low_regime_samples(min<{min_regime_n})")

        target_entry = (confidence * float(self.entry_threshold)) + ((1.0 - confidence) * float(self._default_entry_threshold))
        target_exit = (confidence * float(self.exit_threshold)) + ((1.0 - confidence) * float(self._default_exit_threshold))
        target_adverse = (confidence * float(self.adverse_loss_usd)) + ((1.0 - confidence) * float(self._default_adverse_loss_usd))
        target_reverse = (confidence * float(self.reverse_signal_threshold)) + ((1.0 - confidence) * float(self._default_reverse_signal_threshold))
        self.entry_threshold = int(round(self._blend(self.entry_threshold, target_entry, alpha)))
        self.exit_threshold = int(round(self._blend(self.exit_threshold, target_exit, alpha)))
        self.adverse_loss_usd = float(round(self._blend(self.adverse_loss_usd, target_adverse, alpha), 4))
        self.reverse_signal_threshold = int(round(self._blend(self.reverse_signal_threshold, target_reverse, alpha)))

        stats = dict(self.exit_policy.get("stats", {}) or {})
        score_mult = dict(self.exit_policy.get("score_multiplier", {}) or {})
        profit_mult = dict(self.exit_policy.get("profit_multiplier", {}) or {})
        rev_n = int((stats.get("Reversal", {}) or {}).get("count", 0) or 0)
        rsi_n = int((stats.get("RSI Scalp", {}) or {}).get("count", 0) or 0)
        bb_n = int((stats.get("BB Scalp", {}) or {}).get("count", 0) or 0)
        per_reason_conf = {
            "Reversal": self._clamp(float(rev_n) / float(max(1, min_symbol_n)), 0.0, 1.0),
            "RSI Scalp": self._clamp(float(rsi_n) / float(max(1, min_symbol_n)), 0.0, 1.0),
            "BB Scalp": self._clamp(float(bb_n) / float(max(1, min_symbol_n)), 0.0, 1.0),
        }
        score_mult["Reversal"] = round(
            self._blend(
                float(score_mult.get("Reversal", 1.0)),
                (per_reason_conf["Reversal"] * float(score_mult.get("Reversal", 1.0))) + ((1.0 - per_reason_conf["Reversal"]) * 1.0),
                alpha,
            ),
            4,
        )
        for key in ("RSI Scalp", "BB Scalp"):
            p_conf = float(per_reason_conf.get(key, 0.0))
            cur = float(profit_mult.get(key, 1.0))
            tgt = (p_conf * cur) + ((1.0 - p_conf) * 1.0)
            profit_mult[key] = round(self._blend(cur, tgt, alpha), 4)
        self.exit_policy = {
            "score_multiplier": score_mult,
            "profit_multiplier": profit_mult,
            "stats": stats,
        }

        all_symbols = set(self._symbol_states.keys()) | set(symbol_counts.keys())
        symbol_snapshot = {}
        per_symbol_target_n = max(1, int(round(float(target_n) / max(1, len(all_symbols) or 3))))
        for sym in sorted(all_symbols):
            state = self._state_for_symbol(sym)
            sym_n = int(symbol_counts.get(sym, 0))
            sym_conf = self._clamp(float(sym_n) / float(per_symbol_target_n), 0.0, 1.0)
            sym_defaults = self._symbol_default_overrides.get(sym) or self._resolve_symbol_defaults(sym)
            sym_target_entry = (sym_conf * float(self.entry_threshold)) + ((1.0 - sym_conf) * float(sym_defaults["entry_threshold"]))
            sym_target_exit = (sym_conf * float(self.exit_threshold)) + ((1.0 - sym_conf) * float(sym_defaults["exit_threshold"]))
            sym_target_adverse = (sym_conf * float(self.adverse_loss_usd)) + ((1.0 - sym_conf) * float(sym_defaults["adverse_loss_usd"]))
            sym_target_reverse = (sym_conf * float(self.reverse_signal_threshold)) + ((1.0 - sym_conf) * float(sym_defaults["reverse_signal_threshold"]))
            state["entry_threshold"] = int(round(self._blend(state["entry_threshold"], sym_target_entry, alpha)))
            state["exit_threshold"] = int(round(self._blend(state["exit_threshold"], sym_target_exit, alpha)))
            state["adverse_loss_usd"] = float(round(self._blend(state["adverse_loss_usd"], sym_target_adverse, alpha), 4))
            state["reverse_signal_threshold"] = int(round(self._blend(state["reverse_signal_threshold"], sym_target_reverse, alpha)))
            state["exit_policy"] = deepcopy(self.exit_policy)
            state["sample_confidence"] = round(float(sym_conf), 4)
            state["sample_count"] = int(sym_n)
            state["regime_counts"] = dict(symbol_regime_counts.get(sym, {}))
            state["policy_scope"] = "SYMBOL" if sym_conf >= 0.65 else ("MIXED" if sym_conf >= 0.35 else "GLOBAL")
            state["updated_at"] = datetime.now().isoformat()
            symbol_snapshot[sym] = {
                "policy_scope": state["policy_scope"],
                "sample_confidence": state["sample_confidence"],
                "sample_count": state["sample_count"],
                "regime_counts": state["regime_counts"],
                "entry_threshold": state["entry_threshold"],
                "exit_threshold": state["exit_threshold"],
                "adverse_loss_usd": state["adverse_loss_usd"],
                "reverse_signal_threshold": state["reverse_signal_threshold"],
            }

        self._policy_runtime = {
            "updated_at": datetime.now().isoformat(),
            "samples_total": int(total_n),
            "sample_confidence": round(float(confidence), 4),
            "symbol_counts": symbol_counts,
            "regime_counts": regime_counts,
            "fallback_applied": bool(len(fallback_reasons) > 0),
            "fallback_reasons": fallback_reasons,
            "symbol_policy_snapshot": symbol_snapshot,
            "fallback_scope_used_counts": {
                "SYMBOL": int(sum(1 for s in symbol_snapshot.values() if str(s.get("policy_scope", "")) == "SYMBOL")),
                "MIXED": int(sum(1 for s in symbol_snapshot.values() if str(s.get("policy_scope", "")) == "MIXED")),
                "GLOBAL": int(sum(1 for s in symbol_snapshot.values() if str(s.get("policy_scope", "")) == "GLOBAL")),
            },
            "policy_update_count": int(self._policy_runtime.get("policy_update_count", 0)),
            "policy_update_rejected_count": int(self._policy_runtime.get("policy_update_rejected_count", 0)),
            "rollback_count": int(self._policy_runtime.get("rollback_count", 0)),
            "policy_guard_block_count": int(self._policy_runtime.get("policy_guard_block_count", 0)),
            "policy_update_reject_streak": int(self._policy_runtime.get("policy_update_reject_streak", 0)),
            "policy_blocked_until_ts": float(self._policy_runtime.get("policy_blocked_until_ts", 0.0) or 0.0),
            "policy_blocked_until": str(self._policy_runtime.get("policy_blocked_until", "")),
            "last_rollback_reason": str(self._policy_runtime.get("last_rollback_reason", "")),
            "last_update_skip_reason": str(self._policy_runtime.get("last_update_skip_reason", "")),
            "last_guard_block_reason": str(self._policy_runtime.get("last_guard_block_reason", "")),
            "effective_thresholds": {
                "entry_threshold": int(self.entry_threshold),
                "exit_threshold": int(self.exit_threshold),
                "adverse_loss_usd": float(self.adverse_loss_usd),
                "reverse_signal_threshold": int(self.reverse_signal_threshold),
            },
        }
        if fallback_reasons:
            notes.append(
                "policy fallback: "
                + ", ".join(fallback_reasons)
                + f" | confidence={self._policy_runtime['sample_confidence']:.2f}"
            )

    def reconcile_startup(self, lookback_days=120):
        return self.trade_logger.reconcile_open_trades(
            lookback_days=lookback_days,
            light_mode=bool(getattr(self.config, "STARTUP_RECONCILE_LIGHT_MODE", False)),
            profile=bool(getattr(self.config, "STARTUP_RECONCILE_PROFILE_ENABLED", True)),
        )

    def _shock_report_paths(self, now_dt: datetime) -> tuple[Path, Path]:
        report_dir = Path(str(getattr(self.config, "SHOCK_REPORT_DIR", r"data\reports") or r"data\reports"))
        if not report_dir.is_absolute():
            report_dir = Path(__file__).resolve().parents[2] / report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = now_dt.strftime("%Y%m%d")
        return (
            report_dir / f"shock_weekly_{stamp}.json",
            report_dir / f"shock_weekly_{stamp}.md",
        )

    def _build_shock_weekly_report(self) -> tuple[dict, pd.DataFrame]:
        reader = getattr(self.trade_logger, "read_closed_df", None)
        if not callable(reader):
            return {"rows": 0}, pd.DataFrame()
        closed = reader()
        if closed is None or closed.empty:
            return {"rows": 0}, pd.DataFrame()
        frame = closed.copy()
        for c in ("shock_action", "shock_level", "symbol", "exit_policy_regime"):
            if c not in frame.columns:
                frame[c] = ""
            frame[c] = frame[c].fillna("").astype(str).str.strip()
        for c in ("shock_hold_delta_10", "shock_hold_delta_30", "net_pnl_after_cost", "profit", "shock_score"):
            if c not in frame.columns:
                frame[c] = 0.0
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
        if "close_ts" not in frame.columns:
            frame["close_ts"] = 0
        frame["close_ts"] = pd.to_numeric(frame["close_ts"], errors="coerce").fillna(0).astype(int)
        window_days = max(1, int(getattr(self.config, "SHOCK_REPORT_WINDOW_DAYS", 7)))
        now_s = int(time.time())
        min_ts = int(now_s - (window_days * 86400))
        frame = frame[(frame["shock_action"].str.strip() != "") & (frame["close_ts"] >= min_ts)].copy()
        if frame.empty:
            return {"rows": 0, "window_days": window_days}, frame
        frame["net_realized"] = pd.to_numeric(frame.get("net_pnl_after_cost", frame.get("profit", 0.0)), errors="coerce").fillna(
            pd.to_numeric(frame.get("profit", 0.0), errors="coerce").fillna(0.0)
        )
        d10 = pd.to_numeric(frame.get("shock_hold_delta_10", 0.0), errors="coerce")
        d30 = pd.to_numeric(frame.get("shock_hold_delta_30", 0.0), errors="coerce")
        protective = frame["shock_action"].isin(["downgrade_to_mid", "downgrade_to_short", "force_exit_candidate"])
        holdish = frame["shock_action"].isin(["hold"])
        early_exit_wrong = protective & (d10 > 0.0)
        bad_hold_wrong = holdish & (d10 < 0.0)
        valid_mis = protective | holdish
        mis_rate = float((early_exit_wrong | bad_hold_wrong).sum() / max(1, int(valid_mis.sum())))
        early_exit_rate = float(early_exit_wrong.sum() / max(1, int(protective.sum())))
        bad_hold_rate = float(bad_hold_wrong.sum() / max(1, int(holdish.sum())))
        action_rows = []
        for action, grp in frame.groupby(frame["shock_action"].str.lower().str.strip()):
            g10 = pd.to_numeric(grp.get("shock_hold_delta_10", 0.0), errors="coerce")
            g30 = pd.to_numeric(grp.get("shock_hold_delta_30", 0.0), errors="coerce")
            action_rows.append(
                {
                    "action": str(action),
                    "samples": int(len(grp)),
                    "expectancy_net": round(float(pd.to_numeric(grp["net_realized"], errors="coerce").fillna(0.0).mean()), 6),
                    "delta10_mean": round(float(g10.mean()), 6),
                    "delta10_p25": round(float(g10.quantile(0.25)), 6),
                    "delta10_p50": round(float(g10.quantile(0.50)), 6),
                    "delta10_p75": round(float(g10.quantile(0.75)), 6),
                    "delta30_mean": round(float(g30.mean()), 6),
                    "delta30_p25": round(float(g30.quantile(0.25)), 6),
                    "delta30_p50": round(float(g30.quantile(0.50)), 6),
                    "delta30_p75": round(float(g30.quantile(0.75)), 6),
                }
            )
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "window_days": int(window_days),
            "rows": int(len(frame)),
            "misclassification": {
                "overall_rate": round(float(mis_rate), 6),
                "early_exit_rate": round(float(early_exit_rate), 6),
                "bad_hold_rate": round(float(bad_hold_rate), 6),
                "protective_samples": int(protective.sum()),
                "hold_samples": int(holdish.sum()),
            },
            "action_expectancy": sorted(action_rows, key=lambda x: int(x.get("samples", 0)), reverse=True),
        }
        return report, frame

    def _write_shock_weekly_report(self, report: dict) -> tuple[str, str]:
        now_dt = datetime.now()
        json_path, md_path = self._shock_report_paths(now_dt)
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Shock Weekly Report",
            "",
            f"- generated_at: {report.get('generated_at','')}",
            f"- window_days: {report.get('window_days', 7)}",
            f"- rows: {report.get('rows', 0)}",
            "",
            "## Misclassification",
            f"- overall_rate: {report.get('misclassification',{}).get('overall_rate',0.0)}",
            f"- early_exit_rate: {report.get('misclassification',{}).get('early_exit_rate',0.0)}",
            f"- bad_hold_rate: {report.get('misclassification',{}).get('bad_hold_rate',0.0)}",
            "",
            "## Action Expectancy",
        ]
        for row in report.get("action_expectancy", []):
            lines.append(
                f"- {row.get('action')}: samples={row.get('samples')}, "
                f"expectancy_net={row.get('expectancy_net')}, "
                f"delta10_p50={row.get('delta10_p50')}, delta30_p50={row.get('delta30_p50')}"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(json_path), str(md_path)

    def _maybe_tune_shock_thresholds(self, report: dict) -> tuple[bool, str]:
        if not bool(getattr(self.config, "ENABLE_SHOCK_WEEKLY_TUNING", True)):
            return False, "tuning_disabled"
        if int(report.get("rows", 0)) < max(1, int(getattr(self.config, "SHOCK_TUNING_MIN_SAMPLES", 30))):
            return False, "insufficient_samples"
        mis = dict(report.get("misclassification", {}) or {})
        early_exit_rate = float(mis.get("early_exit_rate", 0.0) or 0.0)
        bad_hold_rate = float(mis.get("bad_hold_rate", 0.0) or 0.0)
        early_hi = float(getattr(self.config, "SHOCK_TUNING_EARLY_EXIT_HIGH", 0.55))
        bad_hold_hi = float(getattr(self.config, "SHOCK_TUNING_BAD_HOLD_HIGH", 0.55))
        step = float(getattr(self.config, "SHOCK_TUNING_STEP", 3.0))
        watch = float(getattr(self.config, "SHOCK_LEVEL_WATCH_THRESHOLD", 35.0))
        alert = float(getattr(self.config, "SHOCK_LEVEL_ALERT_THRESHOLD", 60.0))
        moved = ""
        if early_exit_rate >= early_hi:
            watch += step
            alert += step
            moved = "raise_thresholds"
        elif bad_hold_rate >= bad_hold_hi:
            watch -= step
            alert -= step
            moved = "lower_thresholds"
        else:
            return False, "no_change"
        watch = self._clamp(watch, float(getattr(self.config, "SHOCK_LEVEL_WATCH_MIN", 20.0)), float(getattr(self.config, "SHOCK_LEVEL_WATCH_MAX", 60.0)))
        alert = self._clamp(alert, float(getattr(self.config, "SHOCK_LEVEL_ALERT_MIN", 45.0)), float(getattr(self.config, "SHOCK_LEVEL_ALERT_MAX", 85.0)))
        if alert < (watch + 10.0):
            alert = watch + 10.0
        self.config.SHOCK_LEVEL_WATCH_THRESHOLD = float(round(watch, 3))
        self.config.SHOCK_LEVEL_ALERT_THRESHOLD = float(round(alert, 3))
        return True, f"{moved}:watch={watch:.3f},alert={alert:.3f}"

    def maybe_maintain_shock_ops(self, loop_count: int) -> list[str]:
        notes = []
        startup_warmup_loops = max(1, int(getattr(self.config, "POLICY_STARTUP_WARMUP_LOOPS", 5)))
        if int(loop_count) <= startup_warmup_loops:
            return notes
        if int(loop_count) % 120 != 1:
            return notes
        ops = dict(self._policy_runtime.get("shock_ops", {}) or {})
        if not bool(getattr(self.config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
            ops["last_skip_reason"] = "counterfactual_disabled"
            ops["weekly_tuning_applied"] = False
            self._policy_runtime["shock_ops"] = ops
            return notes
        now_s = float(time.time())
        report_due = bool(getattr(self.config, "ENABLE_SHOCK_WEEKLY_REPORT", True)) and (
            (now_s - float(self._last_shock_report_at)) >= max(300.0, float(getattr(self.config, "SHOCK_REPORT_INTERVAL_SEC", 604800)))
        )
        tune_due = bool(getattr(self.config, "ENABLE_SHOCK_WEEKLY_TUNING", True)) and (
            (now_s - float(self._last_shock_tuning_at)) >= max(300.0, float(getattr(self.config, "SHOCK_TUNING_INTERVAL_SEC", 604800)))
        )
        if not report_due and not tune_due:
            return notes
        report, _ = self._build_shock_weekly_report()
        ops["last_report_rows"] = int(report.get("rows", 0))
        if report_due:
            try:
                json_path, md_path = self._write_shock_weekly_report(report)
                self._last_shock_report_at = now_s
                ops["last_report_at"] = datetime.now().isoformat(timespec="seconds")
                ops["last_report_path"] = str(json_path)
                ops["last_skip_reason"] = ""
                notes.append(f"shock weekly report updated: {md_path}")
            except Exception as exc:
                ops["last_skip_reason"] = f"report_write_failed:{exc}"
        if tune_due:
            tuned, reason = self._maybe_tune_shock_thresholds(report)
            self._last_shock_tuning_at = now_s
            ops["last_tuning_at"] = datetime.now().isoformat(timespec="seconds")
            ops["weekly_tuning_applied"] = bool(tuned)
            ops["watch_threshold"] = float(getattr(self.config, "SHOCK_LEVEL_WATCH_THRESHOLD", 35.0))
            ops["alert_threshold"] = float(getattr(self.config, "SHOCK_LEVEL_ALERT_THRESHOLD", 60.0))
            if tuned:
                notes.append(f"shock weekly tuning applied: {reason}")
            else:
                notes.append(f"shock weekly tuning skipped: {reason}")
        self._policy_runtime["shock_ops"] = ops
        return notes

    def maybe_refresh(self, loop_count):
        startup_warmup_loops = max(1, int(getattr(self.config, "POLICY_STARTUP_WARMUP_LOOPS", 5)))
        if int(loop_count) <= startup_warmup_loops:
            self._policy_runtime["last_update_skip_reason"] = "startup_warmup_guard"
            return []
        if int(loop_count) % 120 != 1:
            return []
        now_s = time.time()
        blocked_until_ts = float(self._policy_runtime.get("policy_blocked_until_ts", 0.0) or 0.0)
        if blocked_until_ts > now_s:
            self._policy_runtime["last_update_skip_reason"] = "rollback_cooldown_guard"
            self._policy_runtime["last_guard_block_reason"] = "rollback_cooldown_guard"
            self._policy_runtime["policy_guard_block_count"] = int(self._policy_runtime.get("policy_guard_block_count", 0)) + 1
            return ["policy guard: rollback_cooldown_guard"]
        min_interval = max(30.0, float(getattr(self.config, "POLICY_UPDATE_MIN_INTERVAL_SEC", 900.0)))
        if (now_s - float(self._last_policy_update_at)) < min_interval:
            self._policy_runtime["last_update_skip_reason"] = "min_interval_guard"
            return []
        total_n, symbol_counts, regime_counts, symbol_regime_counts = self._sample_summary()
        min_total = max(1, int(getattr(self.config, "POLICY_C3_MIN_TOTAL_SAMPLES", 120)))
        min_ready_symbols = max(1, int(getattr(self.config, "POLICY_C3_MIN_READY_SYMBOLS", 2)))
        min_symbol_samples = max(1, int(getattr(self.config, "POLICY_C3_MIN_SYMBOL_SAMPLES", 20)))
        ready_symbols = int(sum(1 for _, n in symbol_counts.items() if int(n) >= min_symbol_samples))
        required_symbols = min(max(1, len(self._symbol_states)), min_ready_symbols)
        if int(total_n) < min_total:
            reason = f"hard_guard_low_total_samples({int(total_n)}<{int(min_total)})"
            self._policy_runtime["last_update_skip_reason"] = reason
            self._policy_runtime["last_guard_block_reason"] = reason
            self._policy_runtime["policy_guard_block_count"] = int(self._policy_runtime.get("policy_guard_block_count", 0)) + 1
            return [f"policy guard: {reason}"]
        if int(ready_symbols) < int(required_symbols):
            reason = f"hard_guard_low_symbol_coverage({int(ready_symbols)}<{int(required_symbols)})"
            self._policy_runtime["last_update_skip_reason"] = reason
            self._policy_runtime["last_guard_block_reason"] = reason
            self._policy_runtime["policy_guard_block_count"] = int(self._policy_runtime.get("policy_guard_block_count", 0)) + 1
            return [f"policy guard: {reason}"]
        notes = []
        prev_snapshot = self._snapshot_state()
        self.entry_threshold, self.exit_threshold, note = self.trade_logger.recommend_thresholds(
            self.entry_threshold,
            self.exit_threshold,
        )
        if note:
            notes.append(note)
        self.exit_policy, note = self.trade_logger.recommend_exit_policy()
        if note:
            notes.append(note)
        self.adverse_loss_usd, self.reverse_signal_threshold, note = self.trade_logger.recommend_adverse_policy(
            self.adverse_loss_usd,
            self.reverse_signal_threshold,
        )
        if note:
            notes.append(note)
        self._fallback_adjust(notes, sample_summary=(total_n, symbol_counts, regime_counts, symbol_regime_counts))
        self._apply_soft_update_cap(prev_snapshot, notes)
        ok, reason = self._apply_update_guards(prev_snapshot)
        if not ok:
            self._restore_state(prev_snapshot)
            self._policy_runtime["policy_update_rejected_count"] = int(self._policy_runtime.get("policy_update_rejected_count", 0)) + 1
            self._policy_runtime["rollback_count"] = int(self._policy_runtime.get("rollback_count", 0)) + 1
            reject_streak = int(self._policy_runtime.get("policy_update_reject_streak", 0)) + 1
            self._policy_runtime["policy_update_reject_streak"] = int(reject_streak)
            block_streak = max(1, int(getattr(self.config, "POLICY_C3_REJECT_STREAK_BLOCK", 2)))
            cooldown_sec = max(30.0, float(getattr(self.config, "POLICY_C3_ROLLBACK_COOLDOWN_SEC", 1800.0)))
            if reject_streak >= block_streak:
                blocked_until = float(now_s + cooldown_sec)
                self._policy_runtime["policy_blocked_until_ts"] = blocked_until
                self._policy_runtime["policy_blocked_until"] = datetime.fromtimestamp(blocked_until).isoformat(timespec="seconds")
            self._policy_runtime["last_rollback_reason"] = str(reason)
            self._policy_runtime["last_guard_block_reason"] = str(reason)
            notes.append(f"policy rollback: {reason}")
            return notes
        self._last_policy_update_at = now_s
        self._last_applied_snapshot = self._snapshot_state()
        self._policy_runtime["policy_update_count"] = int(self._policy_runtime.get("policy_update_count", 0)) + 1
        self._policy_runtime["policy_update_reject_streak"] = 0
        self._policy_runtime["policy_blocked_until_ts"] = 0.0
        self._policy_runtime["policy_blocked_until"] = ""
        self._policy_runtime["last_update_skip_reason"] = ""
        self._policy_runtime["last_guard_block_reason"] = ""
        return notes

    def get_symbol_policy(self, symbol: str) -> dict:
        state = self._state_for_symbol(symbol)
        return {
            "symbol": str(state["symbol"]),
            "entry_threshold": int(state["entry_threshold"]),
            "exit_threshold": int(state["exit_threshold"]),
            "adverse_loss_usd": float(state["adverse_loss_usd"]),
            "reverse_signal_threshold": int(state["reverse_signal_threshold"]),
            "exit_policy": deepcopy(state["exit_policy"]),
            "policy_scope": str(state.get("policy_scope", "GLOBAL")),
            "sample_confidence": float(state.get("sample_confidence", 0.0)),
            "sample_count": int(state.get("sample_count", 0)),
            "regime_counts": dict(state.get("regime_counts", {})),
        }

    def get_runtime_snapshot(self) -> dict:
        symbol_default_snapshot = {}
        symbol_applied_vs_default = {}
        for sym in sorted(self._symbol_states.keys()):
            defaults = dict(self._symbol_default_overrides.get(sym) or self._resolve_symbol_defaults(sym))
            state = self._state_for_symbol(sym)
            symbol_default_snapshot[sym] = {
                "entry_threshold": int(defaults.get("entry_threshold", self._default_entry_threshold)),
                "exit_threshold": int(defaults.get("exit_threshold", self._default_exit_threshold)),
                "adverse_loss_usd": float(defaults.get("adverse_loss_usd", self._default_adverse_loss_usd)),
                "reverse_signal_threshold": int(defaults.get("reverse_signal_threshold", self._default_reverse_signal_threshold)),
            }
            symbol_applied_vs_default[sym] = {
                "entry_threshold_default": int(defaults.get("entry_threshold", self._default_entry_threshold)),
                "entry_threshold_applied": int(state.get("entry_threshold", self.entry_threshold)),
                "entry_threshold_delta": int(state.get("entry_threshold", self.entry_threshold)) - int(defaults.get("entry_threshold", self._default_entry_threshold)),
                "exit_threshold_default": int(defaults.get("exit_threshold", self._default_exit_threshold)),
                "exit_threshold_applied": int(state.get("exit_threshold", self.exit_threshold)),
                "exit_threshold_delta": int(state.get("exit_threshold", self.exit_threshold)) - int(defaults.get("exit_threshold", self._default_exit_threshold)),
                "adverse_loss_usd_default": float(defaults.get("adverse_loss_usd", self._default_adverse_loss_usd)),
                "adverse_loss_usd_applied": float(state.get("adverse_loss_usd", self.adverse_loss_usd)),
                "adverse_loss_usd_delta": round(float(state.get("adverse_loss_usd", self.adverse_loss_usd)) - float(defaults.get("adverse_loss_usd", self._default_adverse_loss_usd)), 6),
                "reverse_signal_threshold_default": int(defaults.get("reverse_signal_threshold", self._default_reverse_signal_threshold)),
                "reverse_signal_threshold_applied": int(state.get("reverse_signal_threshold", self.reverse_signal_threshold)),
                "reverse_signal_threshold_delta": int(state.get("reverse_signal_threshold", self.reverse_signal_threshold)) - int(defaults.get("reverse_signal_threshold", self._default_reverse_signal_threshold)),
                "policy_scope": str(state.get("policy_scope", "GLOBAL")),
                "sample_confidence": float(state.get("sample_confidence", 0.0)),
                "sample_count": int(state.get("sample_count", 0)),
            }
        return {
            "entry_threshold": int(self.entry_threshold),
            "exit_threshold": int(self.exit_threshold),
            "adverse_loss_usd": float(self.adverse_loss_usd),
            "reverse_signal_threshold": int(self.reverse_signal_threshold),
            "exit_policy": deepcopy(self.exit_policy),
            "policy_runtime": deepcopy(self._policy_runtime),
            "symbol_policy_snapshot": {k: self.get_symbol_policy(k) for k in sorted(self._symbol_states.keys())},
            "symbol_default_snapshot": symbol_default_snapshot,
            "symbol_applied_vs_default": symbol_applied_vs_default,
        }

