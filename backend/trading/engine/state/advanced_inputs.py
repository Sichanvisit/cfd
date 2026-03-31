from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.config import Config, PROJECT_ROOT

_SHOCK_EVENT_CACHE: dict[str, Any] = {
    "path": "",
    "mtime": -1.0,
    "df": None,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _clamp01(value: float) -> float:
    return _clamp(value, 0.0, 1.0)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        cast = float(pd.to_numeric(value, errors="coerce"))
    except Exception:
        return float(default)
    if pd.isna(cast):
        return float(default)
    return float(cast)


def _infer_mid_price(tick: Any) -> float:
    bid = _safe_float(getattr(tick, "bid", 0.0), 0.0)
    ask = _safe_float(getattr(tick, "ask", 0.0), 0.0)
    if bid > 0.0 and ask > 0.0:
        return (bid + ask) / 2.0
    return max(bid, ask, 0.0)


def _activation_reasons(*, market_mode: str, metadata: dict, raw_scores: dict) -> list[str]:
    reasons: list[str] = []
    if bool(getattr(Config, "STATE_ADVANCED_FORCE_ON", False)):
        reasons.append("force_on")
    if str(market_mode or "").upper() == "SHOCK":
        reasons.append("shock_regime")

    tick_spread_ratio = _safe_float(metadata.get("current_tick_spread_ratio"), 0.0)
    rate_spread_ratio = _safe_float(metadata.get("current_rate_spread_ratio"), 0.0)
    if max(tick_spread_ratio * 1.80, rate_spread_ratio) >= float(getattr(Config, "STATE_ADVANCED_SPREAD_TRIGGER", 1.15)):
        reasons.append("spread_stress")

    tick_volume_ratio = _safe_float(metadata.get("current_tick_volume_ratio"), 0.0)
    real_volume_ratio = _safe_float(metadata.get("current_real_volume_ratio"), 0.0)
    effective_volume_ratio = real_volume_ratio if real_volume_ratio > 0.0 else tick_volume_ratio
    if 0.0 < effective_volume_ratio <= float(getattr(Config, "STATE_ADVANCED_VOLUME_TRIGGER", 0.55)):
        reasons.append("low_participation")

    wait_conflict = _safe_float((raw_scores or {}).get("wait_conflict"), 0.0)
    wait_noise = _safe_float((raw_scores or {}).get("wait_noise"), 0.0)
    if wait_conflict >= float(getattr(Config, "STATE_ADVANCED_WAIT_CONFLICT_TRIGGER", 8.0)):
        reasons.append("wait_conflict")
    if wait_noise >= float(getattr(Config, "STATE_ADVANCED_WAIT_NOISE_TRIGGER", 10.0)):
        reasons.append("wait_noise")
    return reasons


def _empty_tick_history_payload(state: str, *, collector_enabled: bool, source: str, sample_size: int = 0) -> dict:
    return {
        "collector_enabled": bool(collector_enabled),
        "collector_available": False,
        "collector_active": False,
        "collector_state": str(state or "UNAVAILABLE").upper(),
        "collector_source": str(source or "unavailable"),
        "tick_flow_bias": 0.0,
        "tick_flow_burst": 0.0,
        "tick_sample_size": int(sample_size),
    }


def _collect_tick_history(symbol: str, broker: Any) -> dict:
    if not bool(getattr(Config, "STATE_ADVANCED_TICK_HISTORY_ENABLED", True)):
        return _empty_tick_history_payload("DISABLED", collector_enabled=False, source="disabled")

    getter = getattr(broker, "copy_ticks_from", None) if broker is not None else None
    if not callable(getter):
        return _empty_tick_history_payload("UNAVAILABLE", collector_enabled=True, source="broker_missing")

    lookback_sec = max(10, int(getattr(Config, "STATE_ADVANCED_TICK_LOOKBACK_SEC", 90)))
    tick_count = max(16, int(getattr(Config, "STATE_ADVANCED_TICK_COUNT", 96)))
    date_from = datetime.now(timezone.utc) - timedelta(seconds=lookback_sec)
    try:
        ticks = getter(symbol, date_from, tick_count)
    except TypeError:
        ticks = getter(symbol, date_from, tick_count, None)
    except Exception:
        ticks = None

    if ticks is None:
        return _empty_tick_history_payload("UNAVAILABLE", collector_enabled=True, source="copy_failed")

    df = pd.DataFrame(ticks)
    if df.empty:
        return _empty_tick_history_payload("UNAVAILABLE", collector_enabled=True, source="empty_ticks")

    reference = None
    for col in ("last", "bid", "ask"):
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty:
                reference = series.reset_index(drop=True)
                break
    if reference is None or len(reference) < 2:
        return _empty_tick_history_payload("UNAVAILABLE", collector_enabled=True, source="insufficient_ticks", sample_size=int(len(df)))

    deltas = pd.to_numeric(reference.diff(), errors="coerce").dropna()
    up_moves = int((deltas > 0).sum())
    down_moves = int((deltas < 0).sum())
    total_moves = max(up_moves + down_moves, 1)
    flow_bias = _clamp((up_moves - down_moves) / total_moves, -1.0, 1.0)
    flow_burst = _clamp01(len(reference) / max(float(tick_count), 1.0))

    if flow_burst >= 0.52 and flow_bias >= 0.24:
        state = "BURST_UP_FLOW"
    elif flow_burst >= 0.52 and flow_bias <= -0.24:
        state = "BURST_DOWN_FLOW"
    elif flow_burst <= 0.20:
        state = "QUIET_FLOW"
    else:
        state = "BALANCED_FLOW"

    return {
        "collector_enabled": True,
        "collector_available": True,
        "collector_active": True,
        "collector_state": state,
        "collector_source": "mt5_tick_history",
        "tick_flow_bias": float(flow_bias),
        "tick_flow_burst": float(flow_burst),
        "tick_sample_size": int(len(reference)),
    }


def _empty_order_book_payload(state: str, *, collector_enabled: bool, source: str) -> dict:
    return {
        "collector_enabled": bool(collector_enabled),
        "collector_available": False,
        "collector_active": False,
        "collector_state": str(state or "UNAVAILABLE").upper(),
        "collector_source": str(source or "unavailable"),
        "order_book_imbalance": 0.0,
        "order_book_thinness": 1.0,
        "order_book_levels": 0,
    }


def _collect_order_book(symbol: str, tick: Any, broker: Any) -> dict:
    if not bool(getattr(Config, "STATE_ADVANCED_ORDER_BOOK_ENABLED", True)):
        return _empty_order_book_payload("DISABLED", collector_enabled=False, source="disabled")

    add_fn = getattr(broker, "market_book_add", None) if broker is not None else None
    get_fn = getattr(broker, "market_book_get", None) if broker is not None else None
    release_fn = getattr(broker, "market_book_release", None) if broker is not None else None
    if not callable(get_fn):
        return _empty_order_book_payload("UNAVAILABLE", collector_enabled=True, source="broker_missing")

    subscribed = False
    try:
        if callable(add_fn):
            subscribed = bool(add_fn(symbol))
        book = get_fn(symbol)
    except Exception:
        book = None
    finally:
        try:
            if callable(release_fn):
                release_fn(symbol)
        except Exception:
            pass

    if not book:
        source = "empty_book_after_subscribe" if subscribed else "empty_book"
        return _empty_order_book_payload("UNAVAILABLE", collector_enabled=True, source=source)

    mid = _infer_mid_price(tick)
    bid_volume = 0.0
    ask_volume = 0.0
    level_count = 0
    for level in list(book):
        price = _safe_float(getattr(level, "price", 0.0), 0.0)
        volume = max(
            _safe_float(getattr(level, "volume", 0.0), 0.0),
            _safe_float(getattr(level, "volume_dbl", 0.0), 0.0),
        )
        if price <= 0.0 or volume <= 0.0:
            continue
        level_count += 1
        if mid > 0.0 and price <= mid:
            bid_volume += volume
        elif mid > 0.0 and price > mid:
            ask_volume += volume

    total_volume = bid_volume + ask_volume
    if level_count <= 0 or total_volume <= 0.0:
        return _empty_order_book_payload("UNAVAILABLE", collector_enabled=True, source="unclassified_book")

    imbalance = _clamp((bid_volume - ask_volume) / total_volume, -1.0, 1.0)
    thinness = 1.0 - _clamp(level_count / 8.0, 0.0, 1.0)

    if thinness >= 0.72:
        state = "THIN_BOOK"
    elif imbalance >= 0.18:
        state = "BID_IMBALANCE"
    elif imbalance <= -0.18:
        state = "ASK_IMBALANCE"
    else:
        state = "BALANCED_BOOK"

    return {
        "collector_enabled": True,
        "collector_available": True,
        "collector_active": True,
        "collector_state": state,
        "collector_source": "mt5_market_book",
        "order_book_imbalance": float(imbalance),
        "order_book_thinness": float(_clamp01(thinness)),
        "order_book_levels": int(level_count),
    }


def _shock_event_paths() -> list[Path]:
    trade_csv = Path(getattr(Config, "TRADE_HISTORY_CSV_PATH", r"data\trades\trade_history.csv"))
    if not trade_csv.is_absolute():
        trade_csv = PROJECT_ROOT / trade_csv
    trade_dir = trade_csv.parent
    return [
        trade_dir / "trade_shock_events.csv",
        trade_dir / "shock_events.csv",
        PROJECT_ROOT / "trade_shock_events.csv",
        PROJECT_ROOT / "shock_events.csv",
    ]


def _load_shock_events() -> tuple[pd.DataFrame, str]:
    for path in _shock_event_paths():
        try:
            if not path.exists():
                continue
            mtime = float(path.stat().st_mtime)
            if _SHOCK_EVENT_CACHE.get("path") == str(path) and _SHOCK_EVENT_CACHE.get("mtime") == mtime:
                cached = _SHOCK_EVENT_CACHE.get("df")
                return (cached.copy() if isinstance(cached, pd.DataFrame) else pd.DataFrame(), str(path))

            df = pd.read_csv(path, encoding="utf-8-sig")
            if "event_ts" not in df.columns or "symbol" not in df.columns:
                continue
            df = df.copy()
            df["event_ts"] = pd.to_numeric(df["event_ts"], errors="coerce")
            df["shock_score"] = pd.to_numeric(df.get("shock_score"), errors="coerce").fillna(0.0)
            df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
            df = df.dropna(subset=["event_ts"])
            _SHOCK_EVENT_CACHE["path"] = str(path)
            _SHOCK_EVENT_CACHE["mtime"] = mtime
            _SHOCK_EVENT_CACHE["df"] = df
            return df.copy(), str(path)
        except Exception:
            continue
    return pd.DataFrame(), ""


def _empty_event_risk_payload(state: str, *, collector_enabled: bool, source: str) -> dict:
    return {
        "collector_enabled": bool(collector_enabled),
        "collector_available": False,
        "collector_active": False,
        "collector_state": str(state or "UNAVAILABLE").upper(),
        "collector_source": str(source or "unavailable"),
        "event_risk_score": 0.0,
        "event_match_count": 0,
    }


def _collect_event_risk(symbol: str, event_ts: int | None) -> dict:
    if not bool(getattr(Config, "STATE_ADVANCED_EVENT_RISK_ENABLED", True)):
        return _empty_event_risk_payload("DISABLED", collector_enabled=False, source="disabled")

    df, source_path = _load_shock_events()
    if df.empty:
        return _empty_event_risk_payload("UNAVAILABLE", collector_enabled=True, source="shock_events_missing")

    symbol_u = str(symbol or "").upper().strip()
    symbol_df = df[df["symbol"] == symbol_u].copy()
    if symbol_df.empty:
        return {
            "collector_enabled": True,
            "collector_available": True,
            "collector_active": True,
            "collector_state": "LOW_EVENT_RISK",
            "collector_source": f"shock_events:{Path(source_path).name}",
            "event_risk_score": 0.0,
            "event_match_count": 0,
        }

    lookback_days = max(1, int(getattr(Config, "STATE_ADVANCED_SHOCK_LOOKBACK_DAYS", 21)))
    window_min = max(5, int(getattr(Config, "STATE_ADVANCED_EVENT_WINDOW_MIN", 45)))
    now_ts = int(event_ts or datetime.now(timezone.utc).timestamp())
    now_kst = pd.to_datetime(now_ts, unit="s", utc=True).tz_convert("Asia/Seoul")
    cur_minute = int(now_kst.hour * 60 + now_kst.minute)
    symbol_df["event_dt_kst"] = pd.to_datetime(symbol_df["event_ts"], unit="s", utc=True).dt.tz_convert("Asia/Seoul")
    cutoff = now_kst - pd.Timedelta(days=lookback_days)
    symbol_df = symbol_df[symbol_df["event_dt_kst"] >= cutoff]
    if symbol_df.empty:
        return {
            "collector_enabled": True,
            "collector_available": True,
            "collector_active": True,
            "collector_state": "LOW_EVENT_RISK",
            "collector_source": f"shock_events:{Path(source_path).name}",
            "event_risk_score": 0.0,
            "event_match_count": 0,
        }

    event_minutes = symbol_df["event_dt_kst"].dt.hour * 60 + symbol_df["event_dt_kst"].dt.minute
    minute_diff = (event_minutes - cur_minute).abs()
    minute_diff = minute_diff.where(minute_diff <= 720, 1440 - minute_diff)
    within = minute_diff <= window_min
    symbol_df = symbol_df[within].copy()
    if symbol_df.empty:
        return {
            "collector_enabled": True,
            "collector_available": True,
            "collector_active": True,
            "collector_state": "LOW_EVENT_RISK",
            "collector_source": f"shock_events:{Path(source_path).name}",
            "event_risk_score": 0.0,
            "event_match_count": 0,
        }

    minute_diff = minute_diff[within]
    age_days = (now_kst - symbol_df["event_dt_kst"]).dt.total_seconds() / 86400.0
    same_weekday_bonus = (symbol_df["event_dt_kst"].dt.dayofweek == now_kst.dayofweek).astype(float) * 0.12
    time_weight = (1.0 - (minute_diff / max(float(window_min), 1.0))).clip(lower=0.0)
    recency_weight = (1.0 - (age_days / max(float(lookback_days), 1.0))).clip(lower=0.05)
    weights = (time_weight * 0.62) + (recency_weight * 0.38) + same_weekday_bonus
    normalized_shock = symbol_df["shock_score"].clip(lower=0.0) / 60.0
    weighted_score = float((normalized_shock * weights).sum() / max(float(weights.sum()), 1e-9))
    frequency_bonus = min(len(symbol_df) / 4.0, 1.0) * 0.18
    risk_score = _clamp01(weighted_score + frequency_bonus)

    if risk_score >= 0.68:
        state = "HIGH_EVENT_RISK"
    elif risk_score >= 0.34:
        state = "WATCH_EVENT_RISK"
    else:
        state = "LOW_EVENT_RISK"

    return {
        "collector_enabled": True,
        "collector_available": True,
        "collector_active": True,
        "collector_state": state,
        "collector_source": f"shock_events:{Path(source_path).name}",
        "event_risk_score": float(risk_score),
        "event_match_count": int(len(symbol_df)),
    }


def collect_optional_advanced_state_inputs(
    *,
    symbol: str,
    tick: Any,
    broker: Any,
    metadata: dict[str, Any],
    market_mode: str,
    raw_scores: dict[str, Any] | None,
) -> dict[str, Any]:
    enabled = bool(getattr(Config, "STATE_ADVANCED_INPUTS_ENABLED", True))
    reasons = _activation_reasons(market_mode=market_mode, metadata=metadata, raw_scores=raw_scores or {})
    if not enabled:
        return {
            "advanced_input_contract": "state_advanced_inputs_v1",
            "activation_state": "DISABLED",
            "activation_reasons": [],
            "collector_count_active": 0,
            "tick_history": _empty_tick_history_payload("DISABLED", collector_enabled=False, source="disabled"),
            "order_book": _empty_order_book_payload("DISABLED", collector_enabled=False, source="disabled"),
            "event_risk": _empty_event_risk_payload("DISABLED", collector_enabled=False, source="disabled"),
        }

    should_activate = bool(reasons) or bool(getattr(Config, "STATE_ADVANCED_FORCE_ON", False))
    if not should_activate:
        return {
            "advanced_input_contract": "state_advanced_inputs_v1",
            "activation_state": "INACTIVE",
            "activation_reasons": [],
            "collector_count_active": 0,
            "tick_history": _empty_tick_history_payload("INACTIVE", collector_enabled=bool(getattr(Config, "STATE_ADVANCED_TICK_HISTORY_ENABLED", True)), source="inactive"),
            "order_book": _empty_order_book_payload("INACTIVE", collector_enabled=bool(getattr(Config, "STATE_ADVANCED_ORDER_BOOK_ENABLED", True)), source="inactive"),
            "event_risk": _empty_event_risk_payload("INACTIVE", collector_enabled=bool(getattr(Config, "STATE_ADVANCED_EVENT_RISK_ENABLED", True)), source="inactive"),
        }

    event_ts = metadata.get("signal_bar_ts")
    tick_payload = _collect_tick_history(symbol, broker)
    order_book_payload = _collect_order_book(symbol, tick, broker)
    event_risk_payload = _collect_event_risk(symbol, event_ts)
    collectors = [tick_payload, order_book_payload, event_risk_payload]
    active_count = sum(1 for item in collectors if bool(item.get("collector_active")))
    available_count = sum(1 for item in collectors if bool(item.get("collector_available")))
    if active_count >= 3:
        activation_state = "ACTIVE"
    elif active_count >= 1:
        activation_state = "PARTIAL_ACTIVE"
    elif available_count >= 1:
        activation_state = "PASSIVE_ONLY"
    else:
        activation_state = "UNAVAILABLE"

    return {
        "advanced_input_contract": "state_advanced_inputs_v1",
        "activation_state": activation_state,
        "activation_reasons": reasons,
        "collector_count_active": int(active_count),
        "tick_history": tick_payload,
        "order_book": order_book_payload,
        "event_risk": event_risk_payload,
    }
