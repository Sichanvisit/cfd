"""
Shared trade CSV schema/time normalization utilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from backend.core.config import Config

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")
VALID_EXIT_REGIMES = {"UNKNOWN", "NORMAL", "RANGE", "LOW_LIQUIDITY", "EXPANSION", "TREND"}

INDICATOR_COLUMNS = [
    "ind_rsi",
    "ind_adx",
    "ind_plus_di",
    "ind_minus_di",
    "ind_disparity",
    "ind_ma_20",
    "ind_ma_60",
    "ind_ma_120",
    "ind_ma_240",
    "ind_ma_480",
    "ind_bb_20_up",
    "ind_bb_20_mid",
    "ind_bb_20_dn",
    "ind_bb_4_up",
    "ind_bb_4_dn",
]

REGIME_COLUMNS = [
    "regime_name",
    "regime_volume_ratio",
    "regime_volatility_ratio",
    "regime_spread_ratio",
    "regime_buy_multiplier",
    "regime_sell_multiplier",
]

TRADE_COLUMNS = [
    "ticket",
    "symbol",
    "direction",
    "lot",
    "open_time",
    "open_ts",
    "open_price",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "signal_age_sec",
    "bar_age_sec",
    "decision_latency_ms",
    "order_submit_latency_ms",
    "missing_feature_count",
    "data_completeness_ratio",
    "used_fallback_count",
    "compatibility_mode",
    "detail_blob_bytes",
    "snapshot_payload_bytes",
    "row_payload_bytes",
    "entry_score",
    "contra_score_at_entry",
    "entry_stage",
    "entry_setup_id",
    "management_profile_id",
    "invalidation_id",
    "entry_wait_state",
    "entry_quality",
    "entry_model_confidence",
    "regime_at_entry",
    "entry_h1_context_score",
    "entry_m1_trigger_score",
    "entry_h1_gate_pass",
    "entry_h1_gate_reason",
    "entry_topdown_gate_pass",
    "entry_topdown_gate_reason",
    "entry_topdown_align_count",
    "entry_topdown_conflict_count",
    "entry_topdown_seen_count",
    "entry_session_name",
    "entry_weekday",
    "entry_session_threshold_mult",
    "entry_atr_ratio",
    "entry_atr_threshold_mult",
    "entry_request_price",
    "entry_fill_price",
    "entry_slippage_points",
    "exit_request_price",
    "exit_fill_price",
    "exit_slippage_points",
    "close_time",
    "close_ts",
    "close_price",
    "profit",
    "gross_pnl",
    "cost_total",
    "net_pnl_after_cost",
    "points",
    "entry_reason",
    "exit_reason",
    "exit_score",
    "signed_exit_score",
    "decision_winner",
    "utility_exit_now",
    "utility_hold",
    "utility_reverse",
    "utility_wait_exit",
    "u_cut_now",
    "u_wait_be",
    "u_wait_tp1",
    "u_reverse",
    "exit_policy_stage",
    "exit_policy_profile",
    "exit_profile",
    "exit_wait_state",
    "exit_wait_state_family",
    "exit_wait_hold_class",
    "exit_wait_selected",
    "exit_wait_decision",
    "exit_wait_decision_family",
    "exit_wait_bridge_status",
    "p_recover_be",
    "p_recover_tp1",
    "p_deeper_loss",
    "p_reverse_valid",
    "exit_policy_regime",
    "exit_threshold_triplet",
    "exit_confirm_ticks_applied",
    "exit_route_ev",
    "exit_confidence",
    "exit_delay_ticks",
    "peak_profit_at_exit",
    "giveback_usd",
    "post_exit_mae",
    "post_exit_mfe",
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
    "decision_reason",
    "prediction_bundle",
    "final_outcome",
    "symbol_key",
    "regime_key",
    "policy_scope",
    "status",
] + INDICATOR_COLUMNS + REGIME_COLUMNS


TEXT_TRADE_COLUMNS = {
    "symbol",
    "direction",
    "open_time",
    "close_time",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "compatibility_mode",
    "entry_reason",
    "exit_reason",
    "decision_winner",
    "exit_wait_decision",
    "regime_name",
    "entry_stage",
    "entry_setup_id",
    "management_profile_id",
    "invalidation_id",
    "entry_wait_state",
    "regime_at_entry",
    "entry_h1_gate_reason",
    "entry_topdown_gate_reason",
    "entry_session_name",
    "exit_policy_stage",
    "exit_policy_profile",
    "exit_profile",
    "exit_wait_state",
    "exit_wait_state_family",
    "exit_wait_hold_class",
    "exit_policy_regime",
    "exit_wait_decision_family",
    "exit_wait_bridge_status",
    "exit_threshold_triplet",
    "exit_route_ev",
    "shock_level",
    "shock_reason",
    "shock_action",
    "pre_shock_stage",
    "post_shock_stage",
    "loss_quality_label",
    "loss_quality_reason",
    "wait_quality_label",
    "wait_quality_reason",
    "decision_reason",
    "prediction_bundle",
    "final_outcome",
    "symbol_key",
    "regime_key",
    "policy_scope",
}


def _canonical_symbol_key(value: str) -> str:
    text = str(value or "").upper()
    if "BTC" in text:
        return "BTCUSD"
    if "NAS" in text or "US100" in text or "USTEC" in text:
        return "NAS100"
    if "XAU" in text or "GOLD" in text:
        return "XAUUSD"
    return text.strip()


def now_kst_dt() -> datetime:
    return datetime.now(KST)


def now_kst_text() -> str:
    return now_kst_dt().strftime("%Y-%m-%d %H:%M:%S")


def mt5_ts_to_kst_dt(ts: int) -> datetime:
    dt_utc = datetime.fromtimestamp(int(ts), tz=UTC)
    now_utc = datetime.now(UTC)
    if dt_utc > (now_utc + timedelta(minutes=10)):
        skew_h = int(round((dt_utc - now_utc).total_seconds() / 3600.0))
        if 1 <= skew_h <= 5:
            dt_utc = dt_utc - timedelta(hours=skew_h)
    return dt_utc.astimezone(KST)


def mt5_ts_to_kst_text(ts: int) -> str:
    return mt5_ts_to_kst_dt(ts).strftime("%Y-%m-%d %H:%M:%S")


def text_to_kst_epoch(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return 0
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.tz_localize(KST)
        else:
            dt = dt.tz_convert(KST)
        return int(dt.timestamp())
    except Exception:
        return 0


def epoch_to_kst_text(ts: int) -> str:
    try:
        n = int(ts or 0)
        if n <= 0:
            return ""
        return datetime.fromtimestamp(n, tz=KST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def read_csv_resilient(path: str | Path, *, expected_columns: list[str] | None = None) -> tuple[pd.DataFrame, bool]:
    csv_path = Path(path)
    if not csv_path.exists():
        cols = list(expected_columns or [])
        return pd.DataFrame(columns=cols), True

    encodings = ("utf-8-sig", "utf-8", "cp949")
    last_error: Exception | None = None
    non_empty_lines = 0
    try:
        non_empty_lines = sum(1 for line in csv_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
    except Exception:
        non_empty_lines = 0

    for _ in range(2):
        for enc in encodings:
            try:
                return pd.read_csv(csv_path, encoding=enc), True
            except EmptyDataError:
                cols = list(expected_columns or [])
                return pd.DataFrame(columns=cols), True
            except (UnicodeDecodeError, ParserError) as exc:
                last_error = exc
                try:
                    fallback = pd.read_csv(
                        csv_path,
                        encoding=enc,
                        engine="python",
                        on_bad_lines="skip",
                    )
                    if (not fallback.empty) or non_empty_lines <= 1:
                        return fallback, True
                except Exception as fallback_exc:
                    last_error = fallback_exc
            except Exception as exc:
                last_error = exc
        # External writers sometimes leave the CSV half-written for a short window.
        if last_error is not None:
            import time

            time.sleep(0.05)

    cols = list(expected_columns or [])
    return pd.DataFrame(columns=cols), False


def normalize_trade_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    if df.empty:
        out = df.copy()
        for col in TRADE_COLUMNS:
            if col not in out.columns:
                if col in TEXT_TRADE_COLUMNS:
                    out[col] = ""
                elif col == "status":
                    out[col] = "OPEN"
                else:
                    out[col] = 0.0
        return out

    out = df.copy()

    rename_map = {
        "entry_time": "open_time",
        "entry_price": "open_price",
        "reason": "entry_reason",
        "buy_score": "entry_score",
        "sell_score": "contra_score_at_entry",
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})

    for col in TRADE_COLUMNS:
        if col not in out.columns:
            if col in TEXT_TRADE_COLUMNS:
                out[col] = ""
            elif col == "status":
                out[col] = "OPEN"
            else:
                out[col] = 0.0

    # Legacy shifted row recovery.
    symbol_raw = out["symbol"].fillna("").astype(str).str.upper().str.strip()
    direction_raw = out["direction"].fillna("").astype(str).str.strip()
    open_time_raw = out["open_time"].fillna("").astype(str).str.upper().str.strip()
    direction_is_datetime = direction_raw.str.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", na=False)
    shifted_mask = (
        symbol_raw.isin(["BUY", "SELL"])
        & direction_is_datetime
        & open_time_raw.str.contains("BTC|XAU|NAS|US100|USTEC|GOLD", regex=True, na=False)
    )
    if shifted_mask.any():
        fixed_symbol = out.loc[shifted_mask, "open_time"].copy()
        fixed_direction = out.loc[shifted_mask, "symbol"].copy()
        fixed_open_time = out.loc[shifted_mask, "direction"].copy()
        out.loc[shifted_mask, "symbol"] = fixed_symbol
        out.loc[shifted_mask, "direction"] = fixed_direction
        out.loc[shifted_mask, "open_time"] = fixed_open_time

    # Type normalization.
    out["ticket"] = pd.to_numeric(out["ticket"], errors="coerce").fillna(0).astype(int)
    out["lot"] = pd.to_numeric(out["lot"], errors="coerce").fillna(0.0)
    out["open_price"] = pd.to_numeric(out["open_price"], errors="coerce").fillna(0.0)
    out["signal_age_sec"] = pd.to_numeric(out["signal_age_sec"], errors="coerce").fillna(0.0)
    out["bar_age_sec"] = pd.to_numeric(out["bar_age_sec"], errors="coerce").fillna(0.0)
    out["decision_latency_ms"] = pd.to_numeric(out["decision_latency_ms"], errors="coerce").fillna(0).astype(int)
    out["order_submit_latency_ms"] = pd.to_numeric(out["order_submit_latency_ms"], errors="coerce").fillna(0).astype(int)
    out["missing_feature_count"] = pd.to_numeric(out["missing_feature_count"], errors="coerce").fillna(0).astype(int)
    out["data_completeness_ratio"] = pd.to_numeric(out["data_completeness_ratio"], errors="coerce").fillna(0.0)
    out["used_fallback_count"] = pd.to_numeric(out["used_fallback_count"], errors="coerce").fillna(0).astype(int)
    out["detail_blob_bytes"] = pd.to_numeric(out["detail_blob_bytes"], errors="coerce").fillna(0).astype(int)
    out["snapshot_payload_bytes"] = pd.to_numeric(out["snapshot_payload_bytes"], errors="coerce").fillna(0).astype(int)
    out["row_payload_bytes"] = pd.to_numeric(out["row_payload_bytes"], errors="coerce").fillna(0).astype(int)
    out["entry_score"] = pd.to_numeric(out["entry_score"], errors="coerce").fillna(0.0)
    out["contra_score_at_entry"] = pd.to_numeric(out["contra_score_at_entry"], errors="coerce").fillna(0.0)
    out["entry_quality"] = pd.to_numeric(out["entry_quality"], errors="coerce").fillna(0.0)
    out["entry_model_confidence"] = pd.to_numeric(out["entry_model_confidence"], errors="coerce").fillna(0.0)
    out["entry_h1_context_score"] = pd.to_numeric(out["entry_h1_context_score"], errors="coerce").fillna(0.0)
    out["entry_m1_trigger_score"] = pd.to_numeric(out["entry_m1_trigger_score"], errors="coerce").fillna(0.0)
    out["entry_h1_gate_pass"] = pd.to_numeric(out["entry_h1_gate_pass"], errors="coerce").fillna(0.0)
    out["entry_topdown_gate_pass"] = pd.to_numeric(out["entry_topdown_gate_pass"], errors="coerce").fillna(0.0)
    out["entry_topdown_align_count"] = pd.to_numeric(out["entry_topdown_align_count"], errors="coerce").fillna(0.0)
    out["entry_topdown_conflict_count"] = pd.to_numeric(out["entry_topdown_conflict_count"], errors="coerce").fillna(0.0)
    out["entry_topdown_seen_count"] = pd.to_numeric(out["entry_topdown_seen_count"], errors="coerce").fillna(0.0)
    out["entry_weekday"] = pd.to_numeric(out["entry_weekday"], errors="coerce").fillna(0.0)
    out["entry_session_threshold_mult"] = pd.to_numeric(out["entry_session_threshold_mult"], errors="coerce").fillna(1.0)
    out["entry_atr_ratio"] = pd.to_numeric(out["entry_atr_ratio"], errors="coerce").fillna(1.0)
    out["entry_atr_threshold_mult"] = pd.to_numeric(out["entry_atr_threshold_mult"], errors="coerce").fillna(1.0)
    out["entry_request_price"] = pd.to_numeric(out["entry_request_price"], errors="coerce").fillna(0.0)
    out["entry_fill_price"] = pd.to_numeric(out["entry_fill_price"], errors="coerce").fillna(0.0)
    out["entry_slippage_points"] = pd.to_numeric(out["entry_slippage_points"], errors="coerce").fillna(0.0)
    out["exit_request_price"] = pd.to_numeric(out["exit_request_price"], errors="coerce").fillna(0.0)
    out["exit_fill_price"] = pd.to_numeric(out["exit_fill_price"], errors="coerce").fillna(0.0)
    out["exit_slippage_points"] = pd.to_numeric(out["exit_slippage_points"], errors="coerce").fillna(0.0)
    out["close_price"] = pd.to_numeric(out["close_price"], errors="coerce").fillna(0.0)
    out["profit"] = pd.to_numeric(out["profit"], errors="coerce").fillna(0.0)
    out["gross_pnl"] = pd.to_numeric(out["gross_pnl"], errors="coerce").fillna(out["profit"])
    out["cost_total"] = pd.to_numeric(out["cost_total"], errors="coerce").fillna(0.0)
    out["net_pnl_after_cost"] = pd.to_numeric(out["net_pnl_after_cost"], errors="coerce").fillna(
        out["gross_pnl"] - out["cost_total"]
    )
    out["points"] = pd.to_numeric(out["points"], errors="coerce").fillna(0.0)
    out["exit_score"] = pd.to_numeric(out["exit_score"], errors="coerce").fillna(0.0)
    out["signed_exit_score"] = pd.to_numeric(out["signed_exit_score"], errors="coerce")
    out["utility_exit_now"] = pd.to_numeric(out["utility_exit_now"], errors="coerce").fillna(0.0)
    out["utility_hold"] = pd.to_numeric(out["utility_hold"], errors="coerce").fillna(0.0)
    out["utility_reverse"] = pd.to_numeric(out["utility_reverse"], errors="coerce").fillna(0.0)
    out["utility_wait_exit"] = pd.to_numeric(out["utility_wait_exit"], errors="coerce").fillna(0.0)
    out["u_cut_now"] = pd.to_numeric(out["u_cut_now"], errors="coerce").fillna(0.0)
    out["u_wait_be"] = pd.to_numeric(out["u_wait_be"], errors="coerce").fillna(0.0)
    out["u_wait_tp1"] = pd.to_numeric(out["u_wait_tp1"], errors="coerce").fillna(0.0)
    out["u_reverse"] = pd.to_numeric(out["u_reverse"], errors="coerce").fillna(0.0)
    out["exit_confirm_ticks_applied"] = pd.to_numeric(out["exit_confirm_ticks_applied"], errors="coerce").fillna(0).astype(int)
    out["exit_wait_selected"] = pd.to_numeric(out["exit_wait_selected"], errors="coerce").fillna(0).astype(int)
    out["exit_confidence"] = pd.to_numeric(out["exit_confidence"], errors="coerce").fillna(0.0)
    out["exit_delay_ticks"] = pd.to_numeric(out["exit_delay_ticks"], errors="coerce").fillna(0).astype(int)
    out["peak_profit_at_exit"] = pd.to_numeric(out["peak_profit_at_exit"], errors="coerce").fillna(0.0)
    out["giveback_usd"] = pd.to_numeric(out["giveback_usd"], errors="coerce").fillna(0.0)
    out["p_recover_be"] = pd.to_numeric(out["p_recover_be"], errors="coerce").fillna(0.0)
    out["p_recover_tp1"] = pd.to_numeric(out["p_recover_tp1"], errors="coerce").fillna(0.0)
    out["p_deeper_loss"] = pd.to_numeric(out["p_deeper_loss"], errors="coerce").fillna(0.0)
    out["post_exit_mae"] = pd.to_numeric(out["post_exit_mae"], errors="coerce").fillna(0.0)
    out["post_exit_mfe"] = pd.to_numeric(out["post_exit_mfe"], errors="coerce").fillna(0.0)
    out["shock_score"] = pd.to_numeric(out["shock_score"], errors="coerce").fillna(0.0)
    out["shock_at_profit"] = pd.to_numeric(out["shock_at_profit"], errors="coerce").fillna(0.0)
    out["shock_hold_delta_10"] = pd.to_numeric(out["shock_hold_delta_10"], errors="coerce").fillna(0.0)
    out["shock_hold_delta_30"] = pd.to_numeric(out["shock_hold_delta_30"], errors="coerce").fillna(0.0)
    out["loss_quality_score"] = pd.to_numeric(out["loss_quality_score"], errors="coerce").fillna(0.0)
    out["wait_quality_score"] = pd.to_numeric(out["wait_quality_score"], errors="coerce").fillna(0.0)
    out["entry_reason"] = out["entry_reason"].fillna("").astype(str)
    out["exit_reason"] = out["exit_reason"].fillna("").astype(str)
    out["decision_winner"] = out["decision_winner"].fillna("").astype(str).str.strip().str.lower()
    out["exit_wait_decision"] = out["exit_wait_decision"].fillna("").astype(str).str.strip().str.lower()
    out["regime_name"] = out["regime_name"].fillna("").astype(str)
    out["entry_stage"] = out["entry_stage"].fillna("").astype(str).str.strip().str.lower()
    out["entry_setup_id"] = out["entry_setup_id"].fillna("").astype(str).str.strip().str.lower()
    out["management_profile_id"] = out["management_profile_id"].fillna("").astype(str).str.strip().str.lower()
    out["invalidation_id"] = out["invalidation_id"].fillna("").astype(str).str.strip().str.lower()
    out["entry_wait_state"] = out["entry_wait_state"].fillna("").astype(str).str.strip().str.upper()
    out["regime_at_entry"] = out["regime_at_entry"].fillna("").astype(str).str.strip().str.upper()
    out["entry_h1_gate_reason"] = out["entry_h1_gate_reason"].fillna("").astype(str).str.strip()
    out["entry_topdown_gate_reason"] = out["entry_topdown_gate_reason"].fillna("").astype(str).str.strip()
    out["entry_session_name"] = out["entry_session_name"].fillna("").astype(str).str.strip().str.upper()
    out["exit_policy_stage"] = out["exit_policy_stage"].fillna("").astype(str).str.strip().str.lower()
    out["exit_policy_profile"] = out["exit_policy_profile"].fillna("").astype(str).str.strip().str.lower()
    out["exit_profile"] = out["exit_profile"].fillna("").astype(str).str.strip().str.lower()
    out["exit_wait_state"] = out["exit_wait_state"].fillna("").astype(str).str.strip().str.upper()
    out["exit_wait_state_family"] = out["exit_wait_state_family"].fillna("").astype(str).str.strip().str.lower()
    out["exit_wait_hold_class"] = out["exit_wait_hold_class"].fillna("").astype(str).str.strip().str.lower()
    out["exit_wait_decision_family"] = out["exit_wait_decision_family"].fillna("").astype(str).str.strip().str.lower()
    out["exit_wait_bridge_status"] = out["exit_wait_bridge_status"].fillna("").astype(str).str.strip().str.lower()
    out["exit_policy_regime"] = out["exit_policy_regime"].fillna("").astype(str).str.strip().str.upper()
    out["exit_threshold_triplet"] = out["exit_threshold_triplet"].fillna("").astype(str).str.strip()
    out["exit_route_ev"] = out["exit_route_ev"].fillna("").astype(str).str.strip()
    out["shock_level"] = out["shock_level"].fillna("").astype(str).str.strip().str.lower()
    out["shock_reason"] = out["shock_reason"].fillna("").astype(str).str.strip()
    out["shock_action"] = out["shock_action"].fillna("").astype(str).str.strip().str.lower()
    out["pre_shock_stage"] = out["pre_shock_stage"].fillna("").astype(str).str.strip().str.lower()
    out["post_shock_stage"] = out["post_shock_stage"].fillna("").astype(str).str.strip().str.lower()
    out["loss_quality_label"] = out["loss_quality_label"].fillna("").astype(str).str.strip().str.lower()
    out["loss_quality_reason"] = out["loss_quality_reason"].fillna("").astype(str).str.strip()
    out["wait_quality_label"] = out["wait_quality_label"].fillna("").astype(str).str.strip().str.lower()
    out["wait_quality_reason"] = out["wait_quality_reason"].fillna("").astype(str).str.strip()
    out["decision_reason"] = out["decision_reason"].fillna("").astype(str).str.strip()
    out["prediction_bundle"] = out["prediction_bundle"].fillna("").astype(str).str.strip()
    out["final_outcome"] = out["final_outcome"].fillna("").astype(str).str.strip().str.lower()
    out["symbol_key"] = out["symbol_key"].fillna("").astype(str).str.strip().str.upper()
    out["regime_key"] = out["regime_key"].fillna("").astype(str).str.strip().str.upper()
    out["policy_scope"] = out["policy_scope"].fillna("").astype(str).str.strip().str.upper()
    out["open_time"] = out["open_time"].fillna("").astype(str)
    out["close_time"] = out["close_time"].fillna("").astype(str)
    out["decision_row_key"] = out["decision_row_key"].fillna("").astype(str).str.strip()
    out["runtime_snapshot_key"] = out["runtime_snapshot_key"].fillna("").astype(str).str.strip()
    out["trade_link_key"] = out["trade_link_key"].fillna("").astype(str).str.strip()
    out["replay_row_key"] = out["replay_row_key"].fillna("").astype(str).str.strip()
    out["compatibility_mode"] = out["compatibility_mode"].fillna("").astype(str).str.strip().str.lower()
    out["status"] = out["status"].fillna("").astype(str).str.upper()
    valid_stages = {"aggressive", "balanced", "conservative"}
    out.loc[~out["entry_stage"].isin(valid_stages), "entry_stage"] = "balanced"
    out["entry_quality"] = out["entry_quality"].clip(lower=0.0, upper=1.0)
    out["entry_model_confidence"] = out["entry_model_confidence"].clip(lower=0.0, upper=1.0)
    out["entry_h1_gate_pass"] = out["entry_h1_gate_pass"].clip(lower=0.0, upper=1.0)
    out["entry_topdown_gate_pass"] = out["entry_topdown_gate_pass"].clip(lower=0.0, upper=1.0)
    out["entry_weekday"] = out["entry_weekday"].clip(lower=0.0, upper=6.0)
    out["entry_session_threshold_mult"] = out["entry_session_threshold_mult"].clip(lower=0.5, upper=1.5)
    out["entry_atr_ratio"] = out["entry_atr_ratio"].clip(lower=0.0, upper=10.0)
    out["entry_atr_threshold_mult"] = out["entry_atr_threshold_mult"].clip(lower=0.5, upper=1.5)
    out["signal_age_sec"] = out["signal_age_sec"].clip(lower=0.0, upper=86400.0)
    out["bar_age_sec"] = out["bar_age_sec"].clip(lower=0.0, upper=86400.0)
    out["decision_latency_ms"] = out["decision_latency_ms"].clip(lower=0, upper=3_600_000)
    out["order_submit_latency_ms"] = out["order_submit_latency_ms"].clip(lower=0, upper=3_600_000)
    out["missing_feature_count"] = out["missing_feature_count"].clip(lower=0, upper=1000)
    out["data_completeness_ratio"] = out["data_completeness_ratio"].clip(lower=0.0, upper=1.0)
    out["used_fallback_count"] = out["used_fallback_count"].clip(lower=0, upper=100)
    out["entry_slippage_points"] = out["entry_slippage_points"].clip(lower=0.0, upper=1000000.0)
    out["exit_slippage_points"] = out["exit_slippage_points"].clip(lower=0.0, upper=1000000.0)
    out["exit_confidence"] = out["exit_confidence"].clip(lower=0.0, upper=1.0)
    valid_exit_stages = {"short", "mid", "long", "auto"}
    out.loc[~out["exit_policy_stage"].isin(valid_exit_stages), "exit_policy_stage"] = ""
    # Guard against malformed regime values caused by legacy row shifts/corruption.
    invalid_regime = (out["exit_policy_regime"].str.strip() != "") & (~out["exit_policy_regime"].isin(VALID_EXIT_REGIMES))
    out.loc[invalid_regime, "exit_policy_regime"] = "UNKNOWN"
    out.loc[out["regime_at_entry"].str.strip() == "", "regime_at_entry"] = (
        out["regime_name"].fillna("").astype(str).str.strip().str.upper()
    )
    out.loc[out["exit_policy_regime"].str.strip() == "", "exit_policy_regime"] = (
        out["regime_name"].fillna("").astype(str).str.strip().str.upper()
    )
    out.loc[out["symbol_key"].str.strip() == "", "symbol_key"] = out["symbol"].map(_canonical_symbol_key)
    out.loc[out["regime_key"].str.strip() == "", "regime_key"] = (
        out["exit_policy_regime"].where(out["exit_policy_regime"].str.strip() != "", out["regime_name"])
    ).fillna("").astype(str).str.strip().str.upper()
    out.loc[out["regime_key"].str.strip() == "", "regime_key"] = "UNKNOWN"
    missing_scope = out["policy_scope"].str.strip() == ""
    out.loc[missing_scope, "policy_scope"] = (
        out.loc[missing_scope, "symbol_key"].fillna("").astype(str).str.strip().str.upper()
        + ":"
        + out.loc[missing_scope, "regime_key"].fillna("").astype(str).str.strip().str.upper()
    )
    out["policy_scope"] = out["policy_scope"].fillna("").astype(str).str.strip().str.upper()

    # Always recompute signed target + loss-quality labels for consistency.
    out = add_signed_exit_score(out)

    invalid_status = out["status"].isin(["", "NAN", "NONE", "NULL"])
    closed_hint = (
        (out["close_time"].str.strip() != "")
        | (out["close_price"] != 0.0)
        | (out["profit"] != 0.0)
    )
    out.loc[invalid_status & closed_hint, "status"] = "CLOSED"
    out.loc[invalid_status & ~closed_hint, "status"] = "OPEN"

    out["open_ts"] = pd.to_numeric(out["open_ts"], errors="coerce").fillna(0).astype(int)
    out["close_ts"] = pd.to_numeric(out["close_ts"], errors="coerce").fillna(0).astype(int)
    open_ts_from_text = out["open_time"].map(text_to_kst_epoch)
    close_ts_from_text = out["close_time"].map(text_to_kst_epoch)
    out.loc[out["open_ts"] <= 0, "open_ts"] = pd.to_numeric(open_ts_from_text, errors="coerce").fillna(0).astype(int)
    out.loc[out["close_ts"] <= 0, "close_ts"] = pd.to_numeric(close_ts_from_text, errors="coerce").fillna(0).astype(int)

    for col in INDICATOR_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in REGIME_COLUMNS:
        if col == "regime_name":
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def add_signed_exit_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Learning target helper:
    - Keep exit_score as raw signal intensity.
    - signed_exit_score adds PnL sign and magnitude scaling.
    """
    if df is None:
        out = pd.DataFrame()
        out["signed_exit_score"] = pd.Series(dtype=float)
        out["loss_quality_label"] = pd.Series(dtype=str)
        out["loss_quality_score"] = pd.Series(dtype=float)
        out["loss_quality_reason"] = pd.Series(dtype=str)
        out["wait_quality_label"] = pd.Series(dtype=str)
        out["wait_quality_score"] = pd.Series(dtype=float)
        out["wait_quality_reason"] = pd.Series(dtype=str)
        return out
    out = df.copy()
    if out.empty:
        out["signed_exit_score"] = pd.Series(dtype=float)
        out["loss_quality_label"] = pd.Series(dtype=str)
        out["loss_quality_score"] = pd.Series(dtype=float)
        out["loss_quality_reason"] = pd.Series(dtype=str)
        out["wait_quality_label"] = pd.Series(dtype=str)
        out["wait_quality_score"] = pd.Series(dtype=float)
        out["wait_quality_reason"] = pd.Series(dtype=str)
        return out

    for c in ["exit_reason", "exit_policy_stage", "loss_quality_label", "loss_quality_reason", "wait_quality_label", "wait_quality_reason"]:
        if c not in out.columns:
            out[c] = ""
    for c in ["exit_delay_ticks", "peak_profit_at_exit", "giveback_usd", "post_exit_mae", "post_exit_mfe", "loss_quality_score", "wait_quality_score"]:
        if c not in out.columns:
            out[c] = 0.0

    out["exit_reason"] = out["exit_reason"].fillna("").astype(str).str.strip()
    out["exit_policy_stage"] = out["exit_policy_stage"].fillna("").astype(str).str.strip().str.lower()
    out["exit_delay_ticks"] = pd.to_numeric(out["exit_delay_ticks"], errors="coerce").fillna(0).astype(int)
    out["peak_profit_at_exit"] = pd.to_numeric(out["peak_profit_at_exit"], errors="coerce").fillna(0.0)
    out["giveback_usd"] = pd.to_numeric(out["giveback_usd"], errors="coerce").fillna(0.0)
    out["post_exit_mae"] = pd.to_numeric(out["post_exit_mae"], errors="coerce").fillna(0.0)
    out["post_exit_mfe"] = pd.to_numeric(out["post_exit_mfe"], errors="coerce").fillna(0.0)

    exit_abs = pd.to_numeric(out.get("exit_score", 0.0), errors="coerce").fillna(0.0).abs()
    profit = pd.to_numeric(out.get("profit", 0.0), errors="coerce").fillna(0.0)
    scale = profit.abs().map(lambda x: 1.0 + min(2.0, math.log1p(float(x))))
    sign = profit.map(lambda p: 1.0 if p > 0 else (-1.0 if p < 0 else 0.0))

    small_loss = float(getattr(Config, "LOSS_QUALITY_SMALL_LOSS_USD", 1.0))
    large_loss = float(getattr(Config, "LOSS_QUALITY_LARGE_LOSS_USD", 3.0))
    good_delay_max = int(getattr(Config, "LOSS_QUALITY_GOOD_DELAY_TICKS_MAX", 2))
    bad_delay_min = int(getattr(Config, "LOSS_QUALITY_BAD_DELAY_TICKS_MIN", 5))
    good_mult = float(getattr(Config, "LOSS_QUALITY_GOOD_MULT", 0.55))
    neutral_mult = float(getattr(Config, "LOSS_QUALITY_NEUTRAL_MULT", 0.85))
    bad_mult = float(getattr(Config, "LOSS_QUALITY_BAD_MULT", 1.15))
    wait_recovery_bonus = float(getattr(Config, "LOSS_QUALITY_WAIT_RECOVERY_BONUS", 0.20))
    wait_timeout_penalty = float(getattr(Config, "LOSS_QUALITY_WAIT_TIMEOUT_PENALTY", 0.20))
    wait_delay_relief = float(getattr(Config, "LOSS_QUALITY_WAIT_DELAY_RELIEF", 0.20))
    wait_unnecessary_penalty = float(getattr(Config, "LOSS_QUALITY_WAIT_UNNECESSARY_PENALTY", 0.10))

    labels: list[str] = []
    scores: list[float] = []
    reasons: list[str] = []
    wait_labels: list[str] = []
    wait_scores: list[float] = []
    wait_reasons: list[str] = []
    for _, row in out.iterrows():
        p = float(pd.to_numeric(row.get("profit", 0.0), errors="coerce") or 0.0)
        if p >= 0:
            labels.append("non_loss")
            scores.append(1.0 if p > 0 else 0.0)
            reasons.append("profit_non_negative")
            wait_labels.append("no_wait")
            wait_scores.append(0.0)
            wait_reasons.append("profit_non_negative")
            continue

        loss_abs = abs(p)
        delay = int(pd.to_numeric(row.get("exit_delay_ticks", 0), errors="coerce") or 0)
        peak = float(pd.to_numeric(row.get("peak_profit_at_exit", 0.0), errors="coerce") or 0.0)
        giveback = float(pd.to_numeric(row.get("giveback_usd", 0.0), errors="coerce") or 0.0)
        if giveback <= 0.0 and peak > 0.0:
            giveback = max(0.0, peak - p)
        reason = str(row.get("exit_reason", "") or "").lower()
        stage = str(row.get("exit_policy_stage", "") or "").lower()
        wait_recovery_hit = "adverse_wait=recovery(" in reason
        wait_timeout_hit = "adverse_wait=timeout(" in reason
        wait_label = "no_wait"
        wait_score = 0.0
        wait_why = "no_wait_signal"
        recovery_ratio = 0.0
        if wait_recovery_hit:
            recovery_match = re.search(r"adverse_wait=recovery\(([-+]?\d+(?:\.\d+)?)\/([-+]?\d+(?:\.\d+)?)\)", reason)
            recovery_ratio = 1.0
            if recovery_match:
                try:
                    recovery = float(recovery_match.group(1))
                    recovery_need = max(1e-9, float(recovery_match.group(2)))
                    recovery_ratio = max(0.0, min(1.5, recovery / recovery_need))
                except Exception:
                    recovery_ratio = 1.0
            if (recovery_ratio < 1.10) or (delay >= bad_delay_min and recovery_ratio < 1.20):
                wait_label = "unnecessary_wait"
                wait_score = -0.20
                wait_why = "wait_recovery_marginal"
            else:
                wait_label = "good_wait"
                wait_score = max(0.30, min(1.0, 0.30 + ((recovery_ratio - 1.0) * 0.80)))
                wait_why = "wait_recovery_effective"
        elif wait_timeout_hit:
            wait_label = "bad_wait"
            wait_score = -1.0
            wait_why = "wait_timeout"

        q = 0.0
        why = []
        if loss_abs <= small_loss:
            q += 0.25
            why.append("small_loss")
        if loss_abs >= large_loss:
            q -= 0.45
            why.append("large_loss")
        if 0 < delay <= good_delay_max:
            q += 0.10
            why.append("fast_exit")
        if delay >= bad_delay_min:
            delay_penalty = 0.35
            if wait_recovery_hit:
                delay_penalty = max(0.0, delay_penalty - max(0.0, wait_delay_relief))
            q -= float(delay_penalty)
            why.append("delayed_exit" if delay_penalty >= 0.35 else "delayed_exit_relieved")
        if ("protect exit" in reason) or ("adverse stop" in reason) or (stage == "short"):
            q += 0.10
            why.append("defensive_exit")
        if wait_label == "good_wait":
            q += float(wait_recovery_bonus) * float(recovery_ratio)
            why.append("wait_recovery")
        elif wait_label == "bad_wait":
            q -= float(wait_timeout_penalty)
            why.append("wait_timeout")
        elif wait_label == "unnecessary_wait":
            q -= float(wait_unnecessary_penalty)
            why.append("wait_unnecessary")
        if peak > 0:
            ratio = giveback / max(1e-9, peak)
            if ratio <= 0.40:
                q += 0.10
                why.append("controlled_giveback")
            elif ratio >= 0.80:
                q -= 0.35
                why.append("excessive_giveback")

        q = max(-1.0, min(1.0, float(q)))
        if q >= 0.25:
            labels.append("good_loss")
        elif q <= -0.25:
            labels.append("bad_loss")
        else:
            labels.append("neutral_loss")
        scores.append(round(q, 4))
        reasons.append("|".join(why) if why else "loss_neutral")
        wait_labels.append(wait_label)
        wait_scores.append(round(float(wait_score), 4))
        wait_reasons.append(wait_why)

    out["loss_quality_label"] = pd.Series(labels, index=out.index).astype(str)
    out["loss_quality_score"] = pd.to_numeric(pd.Series(scores, index=out.index), errors="coerce").fillna(0.0)
    out["loss_quality_reason"] = pd.Series(reasons, index=out.index).astype(str)
    out["wait_quality_label"] = pd.Series(wait_labels, index=out.index).astype(str)
    out["wait_quality_score"] = pd.to_numeric(pd.Series(wait_scores, index=out.index), errors="coerce").fillna(0.0)
    out["wait_quality_reason"] = pd.Series(wait_reasons, index=out.index).astype(str)

    mult = pd.Series(1.0, index=out.index, dtype=float)
    mult = mult.where(out["loss_quality_label"] != "good_loss", float(good_mult))
    mult = mult.where(out["loss_quality_label"] != "neutral_loss", float(neutral_mult))
    mult = mult.where(out["loss_quality_label"] != "bad_loss", float(bad_mult))
    out["signed_exit_score"] = ((exit_abs * scale * sign) * mult).clip(lower=-300.0, upper=300.0).round(3)
    return out
