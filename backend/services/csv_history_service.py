"""
CSV history view service.
Caps rows per symbol for stable UI/learning previews.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os

import pandas as pd
from backend.services.trade_csv_schema import add_signed_exit_score

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CsvHistoryPolicy:
    symbols: tuple[str, ...] = ("BTCUSD", "NAS100", "XAUUSD")
    per_symbol_limit: int = int(os.getenv("CSV_HISTORY_PER_SYMBOL_LIMIT", "1000") or 1000)
    min_symbol_regime_samples: int = 12
    min_symbol_samples: int = 30
    min_global_samples: int = 90
    signed_exit_clip_abs: float = float(os.getenv("SIGNED_EXIT_SCORE_CLIP_ABS", "300.0") or 300.0)
    sample_weight_min: float = float(os.getenv("LABEL_WEIGHT_MIN", "0.2") or 0.2)
    sample_weight_max: float = float(os.getenv("LABEL_WEIGHT_MAX", "1.0") or 1.0)
    default_cost_usd: float = float(os.getenv("LEARNING_DEFAULT_COST_USD", "0.5") or 0.5)
    cost_by_symbol: tuple[tuple[str, float], ...] = (
        ("BTCUSD", float(os.getenv("LEARNING_COST_BTCUSD", "1.2") or 1.2)),
        ("NAS100", float(os.getenv("LEARNING_COST_NAS100", "0.8") or 0.8)),
        ("XAUUSD", float(os.getenv("LEARNING_COST_XAUUSD", "0.7") or 0.7)),
    )


class CsvHistoryService:
    def __init__(self, trade_read_service, policy: CsvHistoryPolicy | None = None):
        self._trade_read_service = trade_read_service
        self._policy = policy or CsvHistoryPolicy()

    @staticmethod
    def _canonical_symbol(value: str) -> str:
        text = str(value or "").upper()
        if "BTC" in text:
            return "BTCUSD"
        if "NAS" in text or "US100" in text or "USTEC" in text:
            return "NAS100"
        if "XAU" in text or "GOLD" in text:
            return "XAUUSD"
        return ""

    def _base_closed(self) -> pd.DataFrame:
        df = self._trade_read_service.read_closed_trade_df()
        if df.empty:
            return df
        out = df.copy()
        out = add_signed_exit_score(out)
        out["canonical_symbol"] = out.get("symbol", "").map(self._canonical_symbol)
        out = out[out["canonical_symbol"] != ""].copy()
        out["symbol_key"] = out.get("symbol_key", out["canonical_symbol"]).fillna("").astype(str).str.upper()
        out.loc[out["symbol_key"].str.strip() == "", "symbol_key"] = out["canonical_symbol"]
        out["regime_key"] = out.get("regime_key", out.get("exit_policy_regime", out.get("regime_name", ""))).fillna("").astype(str).str.upper()
        out.loc[out["regime_key"].str.strip() == "", "regime_key"] = "UNKNOWN"
        out["policy_scope"] = out.get("policy_scope", "").fillna("").astype(str).str.upper()
        miss_scope = out["policy_scope"].str.strip() == ""
        out.loc[miss_scope, "policy_scope"] = (
            out.loc[miss_scope, "symbol_key"].fillna("").astype(str).str.upper()
            + ":"
            + out.loc[miss_scope, "regime_key"].fillna("").astype(str).str.upper()
        )
        out["open_ts"] = pd.to_numeric(out.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
        out["close_ts"] = pd.to_numeric(out.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
        out["row_ts"] = out["close_ts"].where(out["close_ts"] > 0, out["open_ts"]).fillna(0).astype(int)
        return out

    def _estimate_cost(self, symbol_key: str) -> float:
        sk = str(symbol_key or "").upper().strip()
        for k, v in self._policy.cost_by_symbol:
            if str(k).upper().strip() == sk:
                return float(v)
        return float(self._policy.default_cost_usd)

    @staticmethod
    def _stage_target_idx(stage: str) -> int:
        s = str(stage or "").strip().lower()
        if s == "short":
            return 0
        if s == "mid":
            return 1
        if s == "long":
            return 2
        return -1

    def _build_learning_targets(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        if out.empty:
            return out
        out["profit"] = pd.to_numeric(out.get("profit", 0.0), errors="coerce").fillna(0.0)
        out["gross_pnl"] = pd.to_numeric(out.get("gross_pnl", out["profit"]), errors="coerce").fillna(out["profit"])
        out["cost_total"] = pd.to_numeric(out.get("cost_total", 0.0), errors="coerce")
        out["signed_exit_score"] = pd.to_numeric(out.get("signed_exit_score", 0.0), errors="coerce").fillna(0.0)
        out["exit_score"] = pd.to_numeric(out.get("exit_score", 0.0), errors="coerce").fillna(0.0)
        out["exit_confidence"] = pd.to_numeric(out.get("exit_confidence", 0.0), errors="coerce").fillna(0.0).clip(lower=0.0, upper=1.0)
        out["shock_score"] = pd.to_numeric(out.get("shock_score", 0.0), errors="coerce").fillna(0.0).clip(lower=0.0, upper=100.0)
        out["shock_at_profit"] = pd.to_numeric(out.get("shock_at_profit", 0.0), errors="coerce").fillna(0.0)
        out["shock_hold_delta_10"] = pd.to_numeric(out.get("shock_hold_delta_10", 0.0), errors="coerce").fillna(0.0)
        out["shock_hold_delta_30"] = pd.to_numeric(out.get("shock_hold_delta_30", 0.0), errors="coerce").fillna(0.0)
        out["loss_quality_score"] = pd.to_numeric(out.get("loss_quality_score", 0.0), errors="coerce").fillna(0.0)
        out["wait_quality_score"] = pd.to_numeric(out.get("wait_quality_score", 0.0), errors="coerce").fillna(0.0)
        out["loss_quality_label"] = out.get("loss_quality_label", "").fillna("").astype(str).str.strip().str.lower()
        out["wait_quality_label"] = out.get("wait_quality_label", "").fillna("").astype(str).str.strip().str.lower()
        out["loss_quality_reason"] = out.get("loss_quality_reason", "").fillna("").astype(str).str.strip()
        out["wait_quality_reason"] = out.get("wait_quality_reason", "").fillna("").astype(str).str.strip()
        out["shock_level"] = out.get("shock_level", "").fillna("").astype(str).str.strip().str.lower()
        out["shock_reason"] = out.get("shock_reason", "").fillna("").astype(str).str.strip()
        out["shock_action"] = out.get("shock_action", "").fillna("").astype(str).str.strip().str.lower()
        out["pre_shock_stage"] = out.get("pre_shock_stage", "").fillna("").astype(str).str.strip().str.lower()
        out["post_shock_stage"] = out.get("post_shock_stage", "").fillna("").astype(str).str.strip().str.lower()
        out["exit_policy_stage"] = out.get("exit_policy_stage", "").astype(str).str.strip().str.lower()
        out.loc[out["exit_policy_stage"] == "", "exit_policy_stage"] = "mid"
        out["exit_policy_profile"] = out.get("exit_policy_profile", "").astype(str).str.strip().str.lower()
        out.loc[out["exit_policy_profile"] == "", "exit_policy_profile"] = "legacy"
        out["exit_policy_regime"] = out.get("exit_policy_regime", "").astype(str).str.strip().str.upper()
        out.loc[out["exit_policy_regime"] == "", "exit_policy_regime"] = (
            out.get("regime_name", "").fillna("").astype(str).str.strip().str.upper()
        )
        out.loc[out["exit_policy_regime"] == "", "exit_policy_regime"] = "UNKNOWN"
        out["symbol_key"] = out.get("symbol_key", out.get("canonical_symbol", "")).fillna("").astype(str).str.upper()
        out.loc[out["symbol_key"].str.strip() == "", "symbol_key"] = out.get("canonical_symbol", "").fillna("").astype(str).str.upper()
        miss_cost = out["cost_total"].isna()
        if miss_cost.any():
            out.loc[miss_cost, "cost_total"] = out.loc[miss_cost, "symbol_key"].map(self._estimate_cost)
        out["cost_total"] = pd.to_numeric(out.get("cost_total", 0.0), errors="coerce").fillna(0.0)
        out["net_pnl_after_cost"] = pd.to_numeric(
            out.get("net_pnl_after_cost", out["gross_pnl"] - out["cost_total"]), errors="coerce"
        ).fillna(out["gross_pnl"] - out["cost_total"])
        out["regime_key"] = out.get("regime_key", out["exit_policy_regime"]).fillna("").astype(str).str.upper()
        out.loc[out["regime_key"].str.strip() == "", "regime_key"] = "UNKNOWN"
        out["policy_scope"] = out.get("policy_scope", "").fillna("").astype(str).str.upper()
        miss_scope = out["policy_scope"].str.strip() == ""
        out.loc[miss_scope, "policy_scope"] = (
            out.loc[miss_scope, "symbol_key"].fillna("").astype(str).str.upper()
            + ":"
            + out.loc[miss_scope, "regime_key"].fillna("").astype(str).str.upper()
        )
        out["stage_target"] = out["exit_policy_stage"]
        out["stage_target_idx"] = out["stage_target"].map(CsvHistoryService._stage_target_idx).astype(int)
        out["now_exit_target"] = 1
        out["signed_exit_score"] = out["signed_exit_score"].clip(
            lower=-abs(float(self._policy.signed_exit_clip_abs)),
            upper=abs(float(self._policy.signed_exit_clip_abs)),
        )
        out["realized_pnl_net"] = out["net_pnl_after_cost"].astype(float)
        out["drawdown_penalty"] = out["net_pnl_after_cost"].map(lambda p: float(abs(p)) if float(p) < 0 else 0.0)
        out["adverse_tail_penalty"] = (
            (out["exit_policy_stage"].isin(["short"]) & (out["net_pnl_after_cost"] < 0)).astype(int)
            * out["net_pnl_after_cost"].abs().astype(float)
            * 0.35
        )
        # Proxy for "expected delta if hold": positive when current exit quality is good, negative when tail-risk dominates.
        out["expected_delta_if_hold"] = (
            (out["signed_exit_score"] * 0.60)
            - (out["drawdown_penalty"] * 0.25)
            - (out["adverse_tail_penalty"] * 0.40)
            + (out["wait_quality_score"] * 0.35)
        ).astype(float)

        # EMA-like recency sample weight (bounded 0.2~1.0)
        out["row_ts"] = pd.to_numeric(out.get("row_ts", 0), errors="coerce").fillna(0).astype(int)
        ts = out["row_ts"]
        if int(ts.max()) > 0 and int(ts.min()) > 0 and int(ts.max()) > int(ts.min()):
            recency = (ts - ts.min()) / max(1, int(ts.max() - ts.min()))
        else:
            recency = pd.Series(1.0, index=out.index)
        min_w = float(self._policy.sample_weight_min)
        max_w = float(self._policy.sample_weight_max)
        out["sample_weight_ema"] = (min_w + ((max_w - min_w) * recency)).astype(float).clip(lower=min_w, upper=max_w)
        out["regime_key"] = out["exit_policy_regime"].where(out["exit_policy_regime"].str.strip() != "", "UNKNOWN")
        return out

    def _build_fallback_plan(self, learning_trimmed: pd.DataFrame) -> tuple[list[dict], dict]:
        if learning_trimmed is None or learning_trimmed.empty:
            return [], {
                "global_samples": 0,
                "min_symbol_regime_samples": int(self._policy.min_symbol_regime_samples),
                "min_symbol_samples": int(self._policy.min_symbol_samples),
                "min_global_samples": int(self._policy.min_global_samples),
                "symbol_regime_ready_count": 0,
                "symbol_ready_count": 0,
                "global_ready": False,
            }
        frame = learning_trimmed.copy()
        frame["symbol_key"] = frame.get("symbol_key", "").fillna("").astype(str).str.upper()
        frame["regime_key"] = frame.get("regime_key", "").fillna("").astype(str).str.upper()
        frame = frame[(frame["symbol_key"].str.strip() != "") & (frame["regime_key"].str.strip() != "")]
        if frame.empty:
            return [], {
                "global_samples": 0,
                "min_symbol_regime_samples": int(self._policy.min_symbol_regime_samples),
                "min_symbol_samples": int(self._policy.min_symbol_samples),
                "min_global_samples": int(self._policy.min_global_samples),
                "symbol_regime_ready_count": 0,
                "symbol_ready_count": 0,
                "global_ready": False,
            }
        global_n = int(len(frame))
        min_sr = max(1, int(self._policy.min_symbol_regime_samples))
        min_s = max(1, int(self._policy.min_symbol_samples))
        min_g = max(1, int(self._policy.min_global_samples))

        by_symbol_regime = frame.groupby(["symbol_key", "regime_key"], dropna=False).size().reset_index(name="samples")
        by_symbol = frame.groupby(["symbol_key"], dropna=False).size().reset_index(name="samples")
        symbol_n_map = {str(r["symbol_key"]): int(r["samples"]) for _, r in by_symbol.iterrows()}
        symbol_regime_ready_count = 0
        symbol_ready_count = 0
        seen_symbol_ready = set()
        plan_rows = []
        for _, row in by_symbol_regime.iterrows():
            symbol_key = str(row["symbol_key"])
            regime_key = str(row["regime_key"])
            sr_n = int(row["samples"])
            s_n = int(symbol_n_map.get(symbol_key, 0))
            if sr_n >= min_sr:
                scope = "SYMBOL_REGIME"
                reason = f"symbol_regime_samples({sr_n})>=min({min_sr})"
                symbol_regime_ready_count += 1
            elif s_n >= min_s:
                scope = "SYMBOL"
                reason = f"symbol_samples({s_n})>=min({min_s})"
                seen_symbol_ready.add(symbol_key)
            elif global_n >= min_g:
                scope = "GLOBAL"
                reason = f"global_samples({global_n})>=min({min_g})"
            else:
                scope = "GLOBAL_COLDSTART"
                reason = f"global_samples({global_n})<min({min_g})"
            plan_rows.append(
                {
                    "symbol_key": symbol_key,
                    "regime_key": regime_key,
                    "symbol_regime_samples": int(sr_n),
                    "symbol_samples": int(s_n),
                    "global_samples": int(global_n),
                    "chosen_scope": scope,
                    "reason": reason,
                }
            )
        symbol_ready_count = int(len(seen_symbol_ready))
        scope_used_counts = {}
        if plan_rows:
            plan_df = pd.DataFrame(plan_rows)
            if "chosen_scope" in plan_df.columns:
                scope_used_counts = {
                    str(k): int(v)
                    for k, v in plan_df["chosen_scope"].value_counts(dropna=False).to_dict().items()
                }
        summary = {
            "global_samples": int(global_n),
            "min_symbol_regime_samples": int(min_sr),
            "min_symbol_samples": int(min_s),
            "min_global_samples": int(min_g),
            "symbol_regime_ready_count": int(symbol_regime_ready_count),
            "symbol_ready_count": int(symbol_ready_count),
            "global_ready": bool(global_n >= min_g),
            "scope_used_counts": scope_used_counts,
        }
        return plan_rows, summary

    def get_training_and_history_rows(
        self,
        per_symbol_limit: int | None = None,
        symbols: list[str] | None = None,
    ) -> dict[str, object]:
        policy_symbols = tuple(symbols or self._policy.symbols)
        sym_norm = [self._canonical_symbol(s) for s in policy_symbols]
        sym_norm = [s for s in sym_norm if s]
        if not sym_norm:
            sym_norm = list(self._policy.symbols)
        n = max(1, int(per_symbol_limit or self._policy.per_symbol_limit))

        base = self._base_closed()
        if base.empty:
            return {
                "symbols": sym_norm,
                "per_symbol_limit": n,
                "history_rows": [],
                "learning_rows": [],
                "stage_label_distribution": {},
                "regime_distribution": {},
                "invalid_learning_sample_count": 0,
            }

        base = base[base["canonical_symbol"].isin(sym_norm)].copy()
        if base.empty:
            return {
                "symbols": sym_norm,
                "per_symbol_limit": n,
                "history_rows": [],
                "learning_rows": [],
                "stage_label_distribution": {},
                "regime_distribution": {},
                "invalid_learning_sample_count": 0,
            }

        trimmed = (
            base.sort_values(["canonical_symbol", "row_ts"], ascending=[True, False])
            .groupby("canonical_symbol", group_keys=False)
            .head(n)
            .sort_values(["canonical_symbol", "row_ts"], ascending=[True, False])
        )

        history_cols = [c for c in ["ticket", "canonical_symbol", "symbol", "direction", "open_time", "close_time", "profit", "status", "entry_reason", "exit_reason"] if c in trimmed.columns]
        learning_trimmed = trimmed.copy()
        if "exit_policy_stage" in learning_trimmed.columns:
            learning_trimmed["exit_policy_stage"] = learning_trimmed["exit_policy_stage"].fillna("").astype(str).str.strip().str.lower()
            learning_trimmed.loc[learning_trimmed["exit_policy_stage"] == "", "exit_policy_stage"] = "mid"
        if "exit_policy_profile" in learning_trimmed.columns:
            learning_trimmed["exit_policy_profile"] = learning_trimmed["exit_policy_profile"].fillna("").astype(str).str.strip().str.lower()
            learning_trimmed.loc[learning_trimmed["exit_policy_profile"] == "", "exit_policy_profile"] = "legacy"
        if "exit_policy_regime" in learning_trimmed.columns:
            learning_trimmed["exit_policy_regime"] = learning_trimmed["exit_policy_regime"].fillna("").astype(str).str.strip().str.upper()
            learning_trimmed.loc[learning_trimmed["exit_policy_regime"] == "", "exit_policy_regime"] = (
                learning_trimmed.get("regime_name", "").fillna("").astype(str).str.strip().str.upper()
            )
            learning_trimmed.loc[learning_trimmed["exit_policy_regime"] == "", "exit_policy_regime"] = "UNKNOWN"
        required_all = ["signed_exit_score", "exit_policy_stage", "exit_policy_profile", "exit_policy_regime"]
        required = [c for c in required_all if c in learning_trimmed.columns]
        missing_required = [c for c in required_all if c not in learning_trimmed.columns]
        invalid_mask = pd.Series(False, index=learning_trimmed.index)
        if missing_required:
            invalid_mask = invalid_mask | True
        if "signed_exit_score" in learning_trimmed.columns:
            invalid_mask = invalid_mask | pd.to_numeric(learning_trimmed["signed_exit_score"], errors="coerce").isna()
        for c in ("exit_policy_stage", "exit_policy_profile", "exit_policy_regime"):
            if c in learning_trimmed.columns:
                invalid_mask = invalid_mask | (learning_trimmed[c].astype(str).str.strip() == "")
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning(
                "learning rows filtered (fail-closed): invalid_samples=%s required=%s missing_required=%s",
                invalid_count,
                required,
                missing_required,
            )
            learning_trimmed = learning_trimmed[~invalid_mask].copy()
        learning_trimmed = self._build_learning_targets(learning_trimmed)
        signed_abs = pd.to_numeric(learning_trimmed.get("signed_exit_score", 0.0), errors="coerce").fillna(0.0).abs()
        label_clip_applied_count = int((signed_abs >= abs(float(self._policy.signed_exit_clip_abs))).sum())
        net_vs_gross_gap_avg = float(
            (
                pd.to_numeric(learning_trimmed.get("gross_pnl", 0.0), errors="coerce").fillna(0.0)
                - pd.to_numeric(learning_trimmed.get("net_pnl_after_cost", 0.0), errors="coerce").fillna(0.0)
            ).abs().mean()
            if not learning_trimmed.empty
            else 0.0
        )
        fallback_plan_rows, fallback_summary = self._build_fallback_plan(learning_trimmed)

        learning_cols = [c for c in [
            "ticket",
            "canonical_symbol",
            "symbol",
            "direction",
            "entry_score",
            "contra_score_at_entry",
            "entry_stage",
            "entry_quality",
            "entry_model_confidence",
            "regime_at_entry",
            "exit_score",
            "signed_exit_score",
            "exit_policy_stage",
            "exit_policy_profile",
            "exit_policy_regime",
            "exit_threshold_triplet",
            "exit_confirm_ticks_applied",
            "exit_route_ev",
            "exit_confidence",
            "shock_score",
            "shock_level",
            "shock_reason",
            "shock_action",
            "pre_shock_stage",
            "post_shock_stage",
            "shock_at_profit",
            "shock_hold_delta_10",
            "shock_hold_delta_30",
            "loss_quality_label",
            "loss_quality_score",
            "loss_quality_reason",
            "wait_quality_label",
            "wait_quality_score",
            "wait_quality_reason",
            "stage_target",
            "stage_target_idx",
            "now_exit_target",
            "realized_pnl_net",
            "drawdown_penalty",
            "adverse_tail_penalty",
            "expected_delta_if_hold",
            "sample_weight_ema",
            "symbol_key",
            "regime_key",
            "policy_scope",
            "points",
            "gross_pnl",
            "cost_total",
            "net_pnl_after_cost",
            "profit",
            "row_ts",
        ] if c in learning_trimmed.columns]
        return {
            "symbols": sym_norm,
            "per_symbol_limit": n,
            "history_rows": trimmed[history_cols].to_dict(orient="records"),
            "learning_rows": learning_trimmed[learning_cols].to_dict(orient="records"),
            "stage_label_distribution": (
                learning_trimmed["stage_target"].value_counts(dropna=False).to_dict()
                if "stage_target" in learning_trimmed.columns
                else {}
            ),
            "regime_distribution": (
                learning_trimmed["regime_key"].value_counts(dropna=False).to_dict()
                if "regime_key" in learning_trimmed.columns
                else {}
            ),
            "symbol_distribution": (
                learning_trimmed["symbol_key"].value_counts(dropna=False).to_dict()
                if "symbol_key" in learning_trimmed.columns
                else {}
            ),
            "policy_scope_distribution": (
                learning_trimmed["policy_scope"].value_counts(dropna=False).to_dict()
                if "policy_scope" in learning_trimmed.columns
                else {}
            ),
            "learning_fallback_plan": fallback_plan_rows,
            "learning_fallback_summary": fallback_summary,
            "invalid_learning_sample_count": invalid_count,
            "label_clip_applied_count": int(label_clip_applied_count),
            "net_vs_gross_gap_avg": round(float(net_vs_gross_gap_avg), 6),
        }
