"""
Shared context classifier for entry/exit decision layers.
"""

from __future__ import annotations

import copy

import pandas as pd

from backend.core.config import Config
from ports.broker_port import BrokerPort
from backend.services.consumer_contract import (
    CONSUMER_FREEZE_HANDOFF_V1,
    CONSUMER_INPUT_CONTRACT_V1,
    CONSUMER_LAYER_MODE_INTEGRATION_V1,
    CONSUMER_LOGGING_CONTRACT_V1,
    CONSUMER_MIGRATION_FREEZE_V1,
    CONSUMER_SCOPE_CONTRACT_V1,
    CONSUMER_TEST_CONTRACT_V1,
    ENTRY_GUARD_CONTRACT_V1,
    ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
    EXIT_HANDOFF_CONTRACT_V1,
    RE_ENTRY_CONTRACT_V1,
    SETUP_MAPPING_CONTRACT_V1,
    SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1,
    build_consumer_migration_guard_metadata,
    resolve_exit_handoff,
)
from backend.services.energy_contract import (
    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
    ENERGY_MIGRATION_DUAL_WRITE_V1,
    ENERGY_SCOPE_CONTRACT_V1,
    build_energy_helper_v2,
    resolve_energy_migration_bridge_state,
)
from backend.services.layer_mode_contract import (
    LAYER_MODE_APPLICATION_CONTRACT_V1,
    LAYER_MODE_DEFAULT_POLICY_V1,
    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    LAYER_MODE_LAYER_INVENTORY_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_MODE_CONTRACT_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_SCOPE_CONTRACT_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
    build_layer_mode_application_metadata,
    build_layer_mode_effective_metadata,
    build_layer_mode_identity_guard_metadata,
    build_layer_mode_influence_metadata,
    build_layer_mode_logging_replay_metadata,
    build_layer_mode_policy_overlay_metadata,
)
from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
)
from backend.services.outcome_labeler_contract import OUTCOME_LABELER_SCOPE_CONTRACT_V1
from backend.services.runtime_alignment_contract import RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
from backend.trading.engine.core.barrier_engine import build_barrier_state
from backend.domain.decision_models import DecisionContext
from backend.trading.engine.core.belief_engine import build_belief_state
from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.evidence_engine import build_evidence_vector
from backend.trading.engine.core.energy_engine import compute_energy_snapshot
from backend.trading.engine.core.normalizer import normalize_distance
from backend.trading.engine.core.forecast_engine import (
    build_trade_management_forecast,
    build_transition_forecast,
    extract_forecast_gap_metrics,
)
from backend.trading.engine.core.forecast_features import build_forecast_features
from backend.trading.engine.core.observe_confirm_router import route_observe_confirm
from backend.trading.engine.position import build_position_snapshot
from backend.trading.engine.response import (
    build_response_raw_snapshot,
    build_response_vector_execution_bridge_from_raw,
    build_response_vector_from_raw,
    build_response_vector_v2_from_raw,
)
from backend.trading.engine.state.advanced_inputs import collect_optional_advanced_state_inputs
from backend.trading.engine.state import build_state_raw_snapshot, build_state_vector, build_state_vector_v2

SEMANTIC_FOUNDATION_CONTRACT_V1 = {
    "contract_version": "semantic_foundation_v1",
    "feature_layers": [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ],
    "raw_support_layers": [
        "response_raw_snapshot_v1",
        "state_raw_snapshot_v1",
    ],
    "direct_action_layer": False,
    "frozen_for_forecast": True,
}

FORECAST_CALIBRATION_CONTRACT_V1 = {
    "contract_version": "forecast_calibration_v1",
    "scope": "forecast_calibration_only",
    "allowed_changes": [
        "forecast_score_structure",
        "separation_metrics",
        "shadow_validation_reporting",
    ],
    "forbidden_changes": [
        "semantic_foundation_recomposition",
        "symbol_exceptions",
        "consumer_retuning",
        "ml_model_activation",
        "live_action_gate_change",
    ],
    "live_action_gate_changed": False,
    "shadow_validation_ready": True,
}

class ContextClassifier:
    MTF_MA_BIG_MAP_TIMEFRAMES = ("1D", "4H", "1H", "30M", "15M")
    MTF_TRENDLINE_TIMEFRAMES = ("1M", "15M", "1H", "4H")
    MICRO_RESPONSE_TIMEFRAMES = ("1M", "5M")
    _MTF_MA_STATE_WEIGHT_BY_TIMEFRAME = {
        "1D": 0.34,
        "4H": 0.27,
        "1H": 0.20,
        "30M": 0.11,
        "15M": 0.08,
    }
    _TRENDLINE_ORDER_BY_TIMEFRAME = {
        "1M": 8,
        "15M": 5,
        "1H": 5,
        "4H": 3,
    }

    def __init__(self, broker: BrokerPort | None = None):
        self._broker = broker

    @staticmethod
    def apply_edge_direction_override(
        *,
        symbol: str,
        market_mode: str,
        direction_policy: str,
        box_state: str,
        bb_state: str,
    ) -> tuple[str, str]:
        sym = str(symbol or "").upper()
        mode = str(market_mode or "").upper()
        policy = str(direction_policy or "BOTH").upper()
        box = str(box_state or "UNKNOWN").upper()
        bb = str(bb_state or "UNKNOWN").upper()

        if mode != "TREND":
            return policy, ""

        upper_extreme = box in {"UPPER", "ABOVE"} and bb in {"UPPER_EDGE", "BREAKOUT"}
        lower_extreme = box in {"LOWER", "BELOW"} and bb in {"LOWER_EDGE", "BREAKDOWN"}

        # BTC/NAS trend rows frequently reach upper/lower extremes while the raw
        # 2H preflight still points one-way. Keep the edge logic symmetric by
        # relaxing to BOTH and letting observe/confirm decide the side.
        if sym in {"BTCUSD", "NAS100"}:
            prefix = "btc" if sym == "BTCUSD" else "nas"
            if upper_extreme and policy == "BUY_ONLY":
                return "BOTH", f"{prefix}_trend_upper_extreme_relax"
            if lower_extreme and policy == "SELL_ONLY":
                return "BOTH", f"{prefix}_trend_lower_extreme_relax"

        return policy, ""

    @staticmethod
    def _coerce_float(value) -> float | None:
        try:
            cast = float(pd.to_numeric(value, errors="coerce"))
        except Exception:
            return None
        if pd.isna(cast):
            return None
        return float(cast)

    @staticmethod
    def _coerce_epoch_seconds(value) -> int | None:
        if value is None:
            return None
        try:
            if isinstance(value, pd.Timestamp):
                return int(value.timestamp())
            if hasattr(value, "timestamp"):
                return int(value.timestamp())
        except Exception:
            pass
        try:
            numeric = pd.to_numeric(value, errors="coerce")
            if pd.isna(numeric):
                return None
            numeric = float(numeric)
            if numeric > 1_000_000_000_000:
                return int(numeric / 1000.0)
            return int(numeric)
        except Exception:
            return None

    @classmethod
    def _extract_frame_event_ts(cls, frame) -> int | None:
        try:
            if frame is None or frame.empty:
                return None
            cur = frame.iloc[-1]
            for key in ("time_msc", "time", "timestamp", "ts"):
                if key in getattr(frame, "columns", []):
                    value = cur.get(key)
                    event_ts = cls._coerce_epoch_seconds(value)
                    if event_ts is not None:
                        return event_ts
            try:
                idx_value = frame.index[-1]
            except Exception:
                idx_value = None
            return cls._coerce_epoch_seconds(idx_value)
        except Exception:
            return None

    @staticmethod
    def volatility_state_from_ratio(vol_ratio: float) -> str:
        v = float(vol_ratio)
        if v >= 1.20:
            return "expanding"
        if v <= 0.90:
            return "contracting"
        return "normal"

    @staticmethod
    def zone_from_regime(regime: dict) -> str:
        zone = str((regime or {}).get("zone", "") or "").strip().upper()
        return zone if zone else "UNKNOWN"

    @staticmethod
    def regime_name(regime: dict) -> str:
        name = str((regime or {}).get("name", "") or "").strip().upper()
        return name if name else "UNKNOWN"

    @classmethod
    def _mtf_ma_stack_state(cls, entries: dict[str, dict]) -> str:
        ordered = []
        for tf in cls.MTF_MA_BIG_MAP_TIMEFRAMES:
            entry = entries.get(tf)
            if not isinstance(entry, dict):
                continue
            ma_value = cls._coerce_float(entry.get("ma20"))
            if ma_value is None:
                continue
            ordered.append((tf, ma_value))
        if len(ordered) < 2:
            return "UNKNOWN"
        values = [value for _, value in ordered]
        if all(values[idx] <= values[idx + 1] for idx in range(len(values) - 1)):
            return "BULL_STACK"
        if all(values[idx] >= values[idx + 1] for idx in range(len(values) - 1)):
            return "BEAR_STACK"
        return "MIXED_STACK"

    @classmethod
    def _mtf_ma_spacing_score(cls, entries: dict[str, dict], scale: float) -> float:
        ordered: list[float] = []
        for tf in cls.MTF_MA_BIG_MAP_TIMEFRAMES:
            entry = entries.get(tf)
            if not isinstance(entry, dict):
                continue
            ma_value = cls._coerce_float(entry.get("ma20"))
            if ma_value is None:
                continue
            ordered.append(float(ma_value))
        if len(ordered) < 2:
            return 0.0
        normalized_gaps = [
            abs(float(ordered[idx] - ordered[idx + 1])) / max(float(scale), 1e-9)
            for idx in range(len(ordered) - 1)
        ]
        if not normalized_gaps:
            return 0.0
        return float(max(0.0, min(1.0, (sum(normalized_gaps) / len(normalized_gaps)) / 1.40)))

    @classmethod
    def _mtf_ma_slope_summary(cls, entries: dict[str, dict]) -> tuple[float, float]:
        total_weight = 0.0
        signed_weighted_sum = 0.0
        positive_weight = 0.0
        negative_weight = 0.0
        for tf in cls.MTF_MA_BIG_MAP_TIMEFRAMES:
            entry = entries.get(tf)
            if not isinstance(entry, dict):
                continue
            slope_signed = cls._coerce_float(entry.get("ma20_slope_signed"))
            if slope_signed is None:
                continue
            weight = float(cls._MTF_MA_STATE_WEIGHT_BY_TIMEFRAME.get(tf, 0.10))
            clamped_slope = max(-1.0, min(1.0, float(slope_signed)))
            signed_weighted_sum += clamped_slope * weight
            total_weight += weight
            if clamped_slope >= 0.05:
                positive_weight += weight
            elif clamped_slope <= -0.05:
                negative_weight += weight
        if total_weight <= 0.0:
            return 0.0, 0.0
        slope_bias = signed_weighted_sum / total_weight
        slope_agreement = abs(positive_weight - negative_weight) / total_weight
        return float(max(-1.0, min(1.0, slope_bias))), float(max(0.0, min(1.0, slope_agreement)))

    @classmethod
    def _build_mtf_ma_big_map(cls, *, df_all: dict, scorer, price: float, volatility_scale: float | None) -> dict:
        trend_mgr = getattr(scorer, "trend_mgr", None) if scorer is not None else None
        scale = float(volatility_scale or max(abs(float(price or 0.0)) * 0.002, 1e-6))
        entries: dict[str, dict] = {}

        for tf in cls.MTF_MA_BIG_MAP_TIMEFRAMES:
            frame = (df_all or {}).get(tf)
            if frame is None or frame.empty or trend_mgr is None:
                continue
            try:
                frame_ind = trend_mgr.add_indicators(frame.copy())
            except Exception:
                frame_ind = frame
            if frame_ind is None or frame_ind.empty:
                continue
            cur = frame_ind.iloc[-1]
            prev = frame_ind.iloc[-2] if len(frame_ind) >= 2 else cur
            ma20 = cls._coerce_float(cur.get("ma_20"))
            prev_ma20 = cls._coerce_float(prev.get("ma_20"))
            if ma20 is None:
                continue
            raw_distance = float(price) - float(ma20)
            signed_distance = float(normalize_distance(float(price), float(ma20), scale, clip=False))
            proximity = float(1.0 / (1.0 + abs(signed_distance)))
            side = "ABOVE" if raw_distance > 0.0 else ("BELOW" if raw_distance < 0.0 else "ON_LINE")
            prev_ma20_value = float(prev_ma20) if prev_ma20 is not None else float(ma20)
            ma20_slope_points = float(ma20) - prev_ma20_value
            ma20_slope_signed = float(normalize_distance(float(ma20), prev_ma20_value, scale, clip=False))
            entries[tf] = {
                "ma20": float(ma20),
                "previous_ma20": prev_ma20_value,
                "raw_distance": raw_distance,
                "signed_distance": signed_distance,
                "proximity": proximity,
                "side": side,
                "ma20_slope_points": ma20_slope_points,
                "ma20_slope_signed": ma20_slope_signed,
                "ma20_slope_side": "UP" if ma20_slope_points > 0.0 else ("DOWN" if ma20_slope_points < 0.0 else "FLAT"),
            }

        upper_candidates = [
            (tf, payload)
            for tf, payload in entries.items()
            if float(payload.get("raw_distance", 0.0) or 0.0) < 0.0
        ]
        lower_candidates = [
            (tf, payload)
            for tf, payload in entries.items()
            if float(payload.get("raw_distance", 0.0) or 0.0) > 0.0
        ]
        upper_anchor = min(
            upper_candidates,
            key=lambda item: abs(float(item[1].get("raw_distance", 0.0) or 0.0)),
            default=(None, {}),
        )
        lower_anchor = min(
            lower_candidates,
            key=lambda item: abs(float(item[1].get("raw_distance", 0.0) or 0.0)),
            default=(None, {}),
        )

        spacing_score = cls._mtf_ma_spacing_score(entries, scale)
        slope_bias, slope_agreement = cls._mtf_ma_slope_summary(entries)

        return {
            "version": "mtf_ma_big_map_v1",
            "reference_ma": "ma20",
            "timeframes_requested": list(cls.MTF_MA_BIG_MAP_TIMEFRAMES),
            "timeframes_available": [tf for tf in cls.MTF_MA_BIG_MAP_TIMEFRAMES if tf in entries],
            "entries": entries,
            "stack_state": cls._mtf_ma_stack_state(entries),
            "spacing_score": spacing_score,
            "slope_bias": slope_bias,
            "slope_agreement": slope_agreement,
            "recent_upper_anchor_tf": upper_anchor[0] or "",
            "recent_upper_anchor_value": cls._coerce_float((upper_anchor[1] or {}).get("ma20")) or 0.0,
            "recent_upper_anchor_distance": abs(float((upper_anchor[1] or {}).get("raw_distance", 0.0) or 0.0)),
            "recent_upper_anchor_proximity": float((upper_anchor[1] or {}).get("proximity", 0.0) or 0.0),
            "recent_lower_anchor_tf": lower_anchor[0] or "",
            "recent_lower_anchor_value": cls._coerce_float((lower_anchor[1] or {}).get("ma20")) or 0.0,
            "recent_lower_anchor_distance": abs(float((lower_anchor[1] or {}).get("raw_distance", 0.0) or 0.0)),
            "recent_lower_anchor_proximity": float((lower_anchor[1] or {}).get("proximity", 0.0) or 0.0),
        }

    @staticmethod
    def _project_trendline_value(frame, indices: list[int], column: str) -> float | None:
        if frame is None or frame.empty or len(indices) < 2:
            return None
        try:
            i1 = int(indices[-2])
            i2 = int(indices[-1])
            if i2 <= i1:
                return None
            p1 = float(pd.to_numeric(frame[column].iloc[i1], errors="coerce"))
            p2 = float(pd.to_numeric(frame[column].iloc[i2], errors="coerce"))
            if pd.isna(p1) or pd.isna(p2):
                return None
            current_idx = len(frame) - 1
            slope = (p2 - p1) / max(1, i2 - i1)
            return float(p2 + slope * (current_idx - i2))
        except Exception:
            return None

    @classmethod
    def _trendline_distance_payload(
        cls,
        *,
        price: float,
        anchor_value: float | None,
        scale: float,
    ) -> dict[str, float | str | None]:
        anchor = cls._coerce_float(anchor_value)
        if anchor is None:
            return {
                "value": None,
                "raw_distance": None,
                "signed_distance": None,
                "proximity": 0.0,
                "side": "UNKNOWN",
            }
        raw_distance = float(price) - float(anchor)
        signed_distance = float(normalize_distance(float(price), float(anchor), scale, clip=False))
        proximity = float(1.0 / (1.0 + abs(signed_distance)))
        side = "ABOVE" if raw_distance > 0.0 else ("BELOW" if raw_distance < 0.0 else "ON_LINE")
        return {
            "value": float(anchor),
            "raw_distance": raw_distance,
            "signed_distance": signed_distance,
            "proximity": proximity,
            "side": side,
        }

    @staticmethod
    def _trendline_flat_suffix(tf: str) -> str:
        return {
            "1M": "m1",
            "15M": "m15",
            "1H": "h1",
            "4H": "h4",
        }.get(str(tf or "").upper(), str(tf or "").lower())

    @classmethod
    def _build_mtf_trendline_bar_map(cls, *, df_all: dict) -> dict:
        entries: dict[str, dict] = {}
        for tf in cls.MTF_TRENDLINE_TIMEFRAMES:
            frame = (df_all or {}).get(tf)
            if frame is None or frame.empty:
                continue
            try:
                cur = frame.iloc[-1]
            except Exception:
                continue
            try:
                prev = frame.iloc[-2] if len(frame) >= 2 else cur
            except Exception:
                prev = cur
            open_now = cls._coerce_float(cur.get("open"))
            high_now = cls._coerce_float(cur.get("high"))
            low_now = cls._coerce_float(cur.get("low"))
            close_now = cls._coerce_float(cur.get("close"))
            if open_now is None or high_now is None or low_now is None or close_now is None:
                continue
            entries[tf] = {
                "open": float(open_now),
                "high": float(high_now),
                "low": float(low_now),
                "close": float(close_now),
                "previous_close": float(cls._coerce_float(prev.get("close")) or close_now),
                "event_ts": cls._extract_frame_event_ts(frame),
            }
        return {
            "version": "mtf_trendline_bar_map_v1",
            "timeframes_requested": list(cls.MTF_TRENDLINE_TIMEFRAMES),
            "timeframes_available": [tf for tf in cls.MTF_TRENDLINE_TIMEFRAMES if tf in entries],
            "entries": entries,
        }

    @classmethod
    def _build_micro_tf_bar_map(cls, *, df_all: dict) -> dict:
        entries: dict[str, dict] = {}
        for tf in cls.MICRO_RESPONSE_TIMEFRAMES:
            frame = (df_all or {}).get(tf)
            if frame is None or frame.empty:
                continue
            try:
                cur = frame.iloc[-1]
            except Exception:
                continue
            try:
                prev = frame.iloc[-2] if len(frame) >= 2 else cur
            except Exception:
                prev = cur
            open_now = cls._coerce_float(cur.get("open"))
            high_now = cls._coerce_float(cur.get("high"))
            low_now = cls._coerce_float(cur.get("low"))
            close_now = cls._coerce_float(cur.get("close"))
            if open_now is None or high_now is None or low_now is None or close_now is None:
                continue
            entries[tf] = {
                "open": float(open_now),
                "high": float(high_now),
                "low": float(low_now),
                "close": float(close_now),
                "previous_close": float(cls._coerce_float(prev.get("close")) or close_now),
                "event_ts": cls._extract_frame_event_ts(frame),
            }
        return {
            "version": "micro_tf_bar_map_v1",
            "timeframes_requested": list(cls.MICRO_RESPONSE_TIMEFRAMES),
            "timeframes_available": [tf for tf in cls.MICRO_RESPONSE_TIMEFRAMES if tf in entries],
            "entries": entries,
        }

    @classmethod
    def _build_micro_tf_window_map(cls, *, df_all: dict, window_size: int = 9) -> dict:
        entries: dict[str, dict] = {}
        for tf in cls.MICRO_RESPONSE_TIMEFRAMES:
            frame = (df_all or {}).get(tf)
            if frame is None or frame.empty:
                continue
            try:
                window = frame.tail(max(1, int(window_size)))
            except Exception:
                continue
            opens = pd.to_numeric(window.get("open"), errors="coerce").dropna().tolist() if "open" in window.columns else []
            highs = pd.to_numeric(window.get("high"), errors="coerce").dropna().tolist() if "high" in window.columns else []
            lows = pd.to_numeric(window.get("low"), errors="coerce").dropna().tolist() if "low" in window.columns else []
            closes = pd.to_numeric(window.get("close"), errors="coerce").dropna().tolist() if "close" in window.columns else []
            if not opens or not highs or not lows or not closes:
                continue
            entries[tf] = {
                "window_size": int(min(len(opens), len(highs), len(lows), len(closes))),
                "opens": [float(v) for v in opens],
                "highs": [float(v) for v in highs],
                "lows": [float(v) for v in lows],
                "closes": [float(v) for v in closes],
            }
        return {
            "version": "micro_tf_window_map_v1",
            "timeframes_requested": list(cls.MICRO_RESPONSE_TIMEFRAMES),
            "timeframes_available": [tf for tf in cls.MICRO_RESPONSE_TIMEFRAMES if tf in entries],
            "entries": entries,
        }

    @staticmethod
    def _pivot_indices_as_list(values) -> list[int]:
        if values is None:
            return []
        if hasattr(values, "tolist"):
            try:
                values = values.tolist()
            except Exception:
                pass
        try:
            return [int(v) for v in values]
        except Exception:
            return []

    @classmethod
    def _build_mtf_trendline_map(cls, *, df_all: dict, scorer, price: float, volatility_scale: float | None) -> dict:
        trend_mgr = getattr(scorer, "trend_mgr", None) if scorer is not None else None
        scale = float(volatility_scale or max(abs(float(price or 0.0)) * 0.002, 1e-6))
        entries: dict[str, dict] = {}
        flat_fields: dict[str, float | str] = {}
        upper_candidates: list[tuple[str, str, dict]] = []
        lower_candidates: list[tuple[str, str, dict]] = []

        for tf in cls.MTF_TRENDLINE_TIMEFRAMES:
            frame = (df_all or {}).get(tf)
            if frame is None or frame.empty or trend_mgr is None or not hasattr(trend_mgr, "get_pivots"):
                continue
            try:
                high_idx, low_idx = trend_mgr.get_pivots(
                    frame,
                    order=int(cls._TRENDLINE_ORDER_BY_TIMEFRAME.get(tf, 5)),
                )
            except Exception:
                continue

            support_payload = cls._trendline_distance_payload(
                price=price,
                anchor_value=cls._project_trendline_value(frame, cls._pivot_indices_as_list(low_idx), "low"),
                scale=scale,
            )
            resistance_payload = cls._trendline_distance_payload(
                price=price,
                anchor_value=cls._project_trendline_value(frame, cls._pivot_indices_as_list(high_idx), "high"),
                scale=scale,
            )

            candidates = []
            if support_payload["value"] is not None:
                candidates.append(("SUPPORT", support_payload))
            if resistance_payload["value"] is not None:
                candidates.append(("RESISTANCE", resistance_payload))
            if not candidates:
                continue

            nearest_kind, nearest_payload = min(
                candidates,
                key=lambda item: abs(float(item[1].get("raw_distance", 0.0) or 0.0)),
            )
            entry = {
                "support_value": support_payload["value"],
                "support_raw_distance": support_payload["raw_distance"],
                "support_signed_distance": support_payload["signed_distance"],
                "support_proximity": support_payload["proximity"],
                "support_side": support_payload["side"],
                "resistance_value": resistance_payload["value"],
                "resistance_raw_distance": resistance_payload["raw_distance"],
                "resistance_signed_distance": resistance_payload["signed_distance"],
                "resistance_proximity": resistance_payload["proximity"],
                "resistance_side": resistance_payload["side"],
                "nearest_kind": nearest_kind,
                "nearest_value": nearest_payload["value"],
                "nearest_raw_distance": nearest_payload["raw_distance"],
                "nearest_signed_distance": nearest_payload["signed_distance"],
                "nearest_proximity": nearest_payload["proximity"],
                "nearest_side": nearest_payload["side"],
            }
            entries[tf] = entry

            suffix = cls._trendline_flat_suffix(tf)
            flat_fields[f"x_tl_{suffix}"] = float(nearest_payload["signed_distance"] or 0.0)
            flat_fields[f"tl_proximity_{suffix}"] = float(nearest_payload["proximity"] or 0.0)
            flat_fields[f"tl_side_{suffix}"] = str(nearest_payload["side"] or "UNKNOWN")
            flat_fields[f"tl_kind_{suffix}"] = str(nearest_kind or "UNKNOWN")

            for kind, payload in candidates:
                raw_distance = payload.get("raw_distance")
                if raw_distance is None:
                    continue
                candidate = (tf, kind, payload)
                if float(raw_distance) < 0.0:
                    upper_candidates.append(candidate)
                elif float(raw_distance) > 0.0:
                    lower_candidates.append(candidate)

        upper_anchor = min(
            upper_candidates,
            key=lambda item: abs(float(item[2].get("raw_distance", 0.0) or 0.0)),
            default=(None, "", {}),
        )
        lower_anchor = min(
            lower_candidates,
            key=lambda item: abs(float(item[2].get("raw_distance", 0.0) or 0.0)),
            default=(None, "", {}),
        )

        return {
            "version": "mtf_trendline_map_v1",
            "timeframes_requested": list(cls.MTF_TRENDLINE_TIMEFRAMES),
            "timeframes_available": [tf for tf in cls.MTF_TRENDLINE_TIMEFRAMES if tf in entries],
            "entries": entries,
            "recent_upper_anchor_tf": upper_anchor[0] or "",
            "recent_upper_anchor_kind": str(upper_anchor[1] or ""),
            "recent_upper_anchor_value": cls._coerce_float((upper_anchor[2] or {}).get("value")) or 0.0,
            "recent_upper_anchor_distance": abs(float((upper_anchor[2] or {}).get("raw_distance", 0.0) or 0.0)),
            "recent_upper_anchor_proximity": float((upper_anchor[2] or {}).get("proximity", 0.0) or 0.0),
            "recent_lower_anchor_tf": lower_anchor[0] or "",
            "recent_lower_anchor_kind": str(lower_anchor[1] or ""),
            "recent_lower_anchor_value": cls._coerce_float((lower_anchor[2] or {}).get("value")) or 0.0,
            "recent_lower_anchor_distance": abs(float((lower_anchor[2] or {}).get("raw_distance", 0.0) or 0.0)),
            "recent_lower_anchor_proximity": float((lower_anchor[2] or {}).get("proximity", 0.0) or 0.0),
            **flat_fields,
        }

    @staticmethod
    def resolve_h1_box_state(df_all: dict, tick, scorer) -> str:
        try:
            h1 = (df_all or {}).get("1H")
            if h1 is None or h1.empty:
                return "UNKNOWN"
            session = scorer.session_mgr.get_session_range(h1, 8, 16)
            if not session:
                return "UNKNOWN"
            px = float(getattr(tick, "bid", 0.0) or 0.0)
            if px <= 0.0:
                return "UNKNOWN"
            return str(scorer.session_mgr.get_position_in_box(session, px) or "UNKNOWN").upper()
        except Exception:
            return "UNKNOWN"

    @staticmethod
    def resolve_bb_state(symbol: str, tick, df_all: dict, scorer) -> str:
        try:
            m15 = (df_all or {}).get("15M")
            if m15 is None or m15.empty:
                return "UNKNOWN"
            if scorer is None or not hasattr(scorer, "trend_mgr"):
                return "UNKNOWN"
            m15_ind = scorer.trend_mgr.add_indicators(m15)
            if m15_ind is None or m15_ind.empty:
                return "UNKNOWN"
            cur = m15_ind.iloc[-1]
            up = float(pd.to_numeric(cur.get("bb_20_up", 0.0), errors="coerce") or 0.0)
            mid = float(pd.to_numeric(cur.get("bb_20_mid", 0.0), errors="coerce") or 0.0)
            dn = float(pd.to_numeric(cur.get("bb_20_dn", 0.0), errors="coerce") or 0.0)
            if not (up > 0.0 and mid > 0.0 and dn > 0.0):
                return "UNKNOWN"
            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
            px = bid if bid > 0.0 else ask
            if px <= 0.0 and ask > 0.0:
                px = ask
            if px <= 0.0:
                return "UNKNOWN"
            mid_tol = abs(
                float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_MID_TOL_PCT_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_MID_TOL_PCT", 0.00015)},
                        ),
                        float(getattr(Config, "ENTRY_BB_MID_TOL_PCT", 0.00015)),
                    )
                )
            )
            near_band = abs(
                float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_NEAR_BAND_PCT_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_NEAR_BAND_PCT", 0.00020)},
                        ),
                        float(getattr(Config, "ENTRY_BB_NEAR_BAND_PCT", 0.00020)),
                    )
                )
            )
            breakout_pct = abs(
                float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_BREAKOUT_BLOCK_PCT_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_BREAKOUT_BLOCK_PCT", 0.00005)},
                        ),
                        float(getattr(Config, "ENTRY_BB_BREAKOUT_BLOCK_PCT", 0.00005)),
                    )
                )
            )
            if px >= (up * (1.0 + breakout_pct)):
                return "BREAKOUT"
            if px <= (dn * (1.0 - breakout_pct)):
                return "BREAKDOWN"
            if px >= (up * (1.0 - near_band)):
                return "UPPER_EDGE"
            if px <= (dn * (1.0 + near_band)):
                return "LOWER_EDGE"
            if abs(px - mid) / max(1e-9, abs(px)) <= mid_tol:
                return "MID"
            width = float(up - dn)
            if width > 0.0:
                channel_pos = (px - dn) / max(1e-9, width)
                upper_ratio = float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_CHANNEL_UPPER_RATIO_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_CHANNEL_UPPER_RATIO", 0.72)},
                        ),
                        float(getattr(Config, "ENTRY_BB_CHANNEL_UPPER_RATIO", 0.72)),
                    )
                )
                lower_ratio = float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_CHANNEL_LOWER_RATIO_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_CHANNEL_LOWER_RATIO", 0.28)},
                        ),
                        float(getattr(Config, "ENTRY_BB_CHANNEL_LOWER_RATIO", 0.28)),
                    )
                )
                mid_half_width = float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "ENTRY_BB_CHANNEL_MID_HALF_WIDTH_BY_SYMBOL",
                            {"DEFAULT": getattr(Config, "ENTRY_BB_CHANNEL_MID_HALF_WIDTH", 0.12)},
                        ),
                        float(getattr(Config, "ENTRY_BB_CHANNEL_MID_HALF_WIDTH", 0.12)),
                    )
                )
                if channel_pos >= upper_ratio:
                    return "UPPER_EDGE"
                if channel_pos <= lower_ratio:
                    return "LOWER_EDGE"
                if abs(channel_pos - 0.5) <= mid_half_width:
                    return "MID"
            return "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def build_preflight_2h(
        self,
        *,
        symbol: str,
        tick,
        df_all: dict,
        result: dict,
        buy_s: float,
        sell_s: float,
    ) -> dict:
        out = {
            "regime": "UNKNOWN",
            "liquidity": "OK",
            "allowed_action": "BOTH",
            "approach_mode": "MIX",
            "reason": "",
            "ret2h_ratio": 0.0,
            "ret2h_signed": 0.0,
            "spread_ratio": 0.0,
            "enabled": bool(getattr(Config, "ENABLE_ENTRY_PREFLIGHT_2H", True)),
        }
        if not out["enabled"]:
            return out

        regime = (result or {}).get("regime", {}) if isinstance(result, dict) else {}
        spread_ratio = float((regime or {}).get("spread_ratio", 0.0) or 0.0)
        out["spread_ratio"] = float(spread_ratio)
        if spread_ratio >= float(getattr(Config, "ENTRY_PREFLIGHT_SPREAD_BAD_RATIO", 1.60)):
            out["liquidity"] = "BAD"
        elif spread_ratio >= float(getattr(Config, "ENTRY_PREFLIGHT_SPREAD_OK_RATIO", 1.20)):
            out["liquidity"] = "OK"
        else:
            out["liquidity"] = "GOOD"

        h1 = (df_all or {}).get("1H")
        if h1 is None or h1.empty or len(h1) < 3:
            if out["liquidity"] == "BAD":
                out["regime"] = "SHOCK"
                out["allowed_action"] = "NONE"
                out["approach_mode"] = "NO_TRADE"
                out["reason"] = "preflight_missing_h1_bad_liquidity"
            return out
        try:
            frame = h1.tail(max(20, int(getattr(Config, "ENTRY_PREFLIGHT_H1_LOOKBACK", 24)))).copy()
            close_now = float(pd.to_numeric(frame["close"].iloc[-1], errors="coerce") or 0.0)
            close_prev_2h = float(pd.to_numeric(frame["close"].iloc[-3], errors="coerce") or close_now)
            if close_now <= 0.0:
                return out
            ret2h_signed = (close_now - close_prev_2h) / max(1e-9, close_prev_2h)
            ret2h_abs = abs(ret2h_signed)
            ranges = (pd.to_numeric(frame["high"], errors="coerce") - pd.to_numeric(frame["low"], errors="coerce")).abs()
            norm = pd.to_numeric(frame["close"], errors="coerce").abs().replace(0, pd.NA)
            range_pct = (ranges / norm).dropna()
            avg_range_pct = float(range_pct.tail(12).mean()) if not range_pct.empty else 0.0
            if not (avg_range_pct > 0):
                avg_range_pct = max(1e-6, abs(ret2h_abs))
            ret2h_ratio = float(ret2h_abs / max(1e-9, avg_range_pct))
            out["ret2h_ratio"] = float(ret2h_ratio)
            out["ret2h_signed"] = float(ret2h_signed)

            shock_thr = float(getattr(Config, "ENTRY_PREFLIGHT_2H_SHOCK_RATIO", 2.40))
            trend_thr = float(getattr(Config, "ENTRY_PREFLIGHT_2H_TREND_RATIO", 1.15))
            pullback_mode_thr = float(getattr(Config, "ENTRY_PREFLIGHT_2H_PULLBACK_ONLY_RATIO", 1.80))
            if ret2h_ratio >= shock_thr or out["liquidity"] == "BAD":
                out["regime"] = "SHOCK"
                out["allowed_action"] = "NONE"
                out["approach_mode"] = "NO_TRADE"
                out["reason"] = "preflight_shock_or_bad_liquidity"
                return out
            if ret2h_ratio >= trend_thr:
                out["regime"] = "TREND"
                if ret2h_signed > 0:
                    out["allowed_action"] = "BUY_ONLY"
                elif ret2h_signed < 0:
                    out["allowed_action"] = "SELL_ONLY"
                else:
                    out["allowed_action"] = "BOTH"
                out["approach_mode"] = "PULLBACK_ONLY" if ret2h_ratio >= pullback_mode_thr else "MIX"
                out["reason"] = "preflight_trend"
                return out

            out["regime"] = "RANGE"
            out["allowed_action"] = "BOTH"
            out["approach_mode"] = "MIX"
            out["reason"] = "preflight_range"
            return out
        except Exception:
            return out

    def build_entry_context(
        self,
        *,
        symbol: str,
        tick,
        df_all: dict,
        scorer,
        result: dict,
        buy_s: float,
        sell_s: float,
    ) -> dict:
        regime = (result or {}).get("regime", {}) if isinstance(result, dict) else {}
        preflight = self.build_preflight_2h(
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            result=result,
            buy_s=buy_s,
            sell_s=sell_s,
        )
        comps = (result or {}).get("components", {}) if isinstance(result, dict) else {}
        box_state = self.resolve_h1_box_state(df_all=df_all, tick=tick, scorer=scorer)
        bb_state = self.resolve_bb_state(symbol=symbol, tick=tick, df_all=df_all, scorer=scorer)
        raw_direction_policy = str(preflight.get("allowed_action", "BOTH") or "BOTH").upper()
        direction_policy, direction_override_reason = self.apply_edge_direction_override(
            symbol=symbol,
            market_mode=str(preflight.get("regime", "UNKNOWN") or "UNKNOWN").upper(),
            direction_policy=raw_direction_policy,
            box_state=box_state,
            bb_state=bb_state,
        )

        context = DecisionContext(
            symbol=str(symbol or ""),
            phase="entry",
            market_mode=str(preflight.get("regime", "UNKNOWN") or "UNKNOWN").upper(),
            direction_policy=direction_policy,
            box_state=box_state,
            bb_state=bb_state,
            liquidity_state=str(preflight.get("liquidity", "OK") or "OK").upper(),
            regime_name=self.regime_name(regime),
            regime_zone=self.zone_from_regime(regime),
            volatility_state=self.volatility_state_from_ratio(float((regime or {}).get("volatility_ratio", 1.0) or 1.0)),
            raw_scores={
                "buy_score": float(buy_s),
                "sell_score": float(sell_s),
                "wait_score": float(pd.to_numeric(comps.get("wait_score", 0.0), errors="coerce") or 0.0),
                "wait_conflict": float(pd.to_numeric(comps.get("wait_conflict", 0.0), errors="coerce") or 0.0),
                "wait_noise": float(pd.to_numeric(comps.get("wait_noise", 0.0), errors="coerce") or 0.0),
            },
            metadata={
                "preflight_approach_mode": str(preflight.get("approach_mode", "MIX") or "MIX").upper(),
                "preflight_reason": str(preflight.get("reason", "") or ""),
                "preflight_enabled": bool(preflight.get("enabled", False)),
                "preflight_allowed_action_raw": raw_direction_policy,
                "direction_policy_override_reason": direction_override_reason,
                "preflight_spread_ratio": float(preflight.get("spread_ratio", 0.0) or 0.0),
                "preflight_ret2h_ratio": float(preflight.get("ret2h_ratio", 0.0) or 0.0),
                "preflight_ret2h_signed": float(preflight.get("ret2h_signed", 0.0) or 0.0),
            },
        )
        engine_bundle = self.build_engine_context_snapshot(
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            scorer=scorer,
            market_mode=context.market_mode,
            direction_policy=context.direction_policy,
            liquidity_state=context.liquidity_state,
            spread_ratio=float(preflight.get("spread_ratio", 0.0) or 0.0),
            box_state=context.box_state,
            bb_state=context.bb_state,
            raw_scores=context.raw_scores,
        )
        context.metadata["engine_context_v1"] = engine_bundle["engine_context"].to_dict()
        context.metadata["position_snapshot_v2"] = engine_bundle["position_snapshot"].to_dict()
        context.metadata["position_vector_v2"] = engine_bundle["position_vector"].to_dict()
        context.metadata["position_zones_v2"] = engine_bundle["position_zones"].to_dict()
        context.metadata["position_interpretation_v2"] = engine_bundle["position_interpretation"].to_dict()
        context.metadata["position_energy_v2"] = engine_bundle["position_energy"].to_dict()
        context.metadata["response_raw_snapshot_v1"] = engine_bundle["response_raw_snapshot"].to_dict()
        context.metadata["response_vector_legacy_v1"] = engine_bundle["response_vector_legacy"].to_dict()
        context.metadata["response_vector_execution_bridge_v1"] = engine_bundle["response_vector_execution_bridge"].to_dict()
        context.metadata["response_vector_v2"] = engine_bundle["response_vector_v2"].to_dict()
        context.metadata["state_raw_snapshot_v1"] = engine_bundle["state_raw_snapshot"].to_dict()
        context.metadata["state_vector_v2"] = engine_bundle["state_vector_v2"].to_dict()
        context.metadata["evidence_vector_v1"] = engine_bundle["evidence_vector"].to_dict()
        context.metadata["belief_state_v1"] = engine_bundle["belief_state"].to_dict()
        context.metadata["barrier_state_v1"] = engine_bundle["barrier_state"].to_dict()
        context.metadata["forecast_features_v1"] = engine_bundle["forecast_features"].to_dict()
        context.metadata["transition_forecast_v1"] = engine_bundle["transition_forecast"].to_dict()
        context.metadata["trade_management_forecast_v1"] = engine_bundle["trade_management_forecast"].to_dict()
        context.metadata["forecast_gap_metrics_v1"] = dict(engine_bundle.get("forecast_gap_metrics", {}) or {})
        context.metadata["energy_snapshot"] = engine_bundle["energy_snapshot"].to_dict()
        observe_confirm_payload = engine_bundle["observe_confirm"].to_dict()
        context.metadata["observe_confirm_v1"] = copy.deepcopy(observe_confirm_payload)
        context.metadata["observe_confirm_v2"] = copy.deepcopy(observe_confirm_payload)
        context.metadata["observe_confirm_input_contract_v2"] = copy.deepcopy(OBSERVE_CONFIRM_INPUT_CONTRACT_V2)
        context.metadata["observe_confirm_migration_dual_write_v1"] = copy.deepcopy(OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1)
        context.metadata["observe_confirm_output_contract_v2"] = copy.deepcopy(OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2)
        context.metadata["observe_confirm_scope_contract_v1"] = copy.deepcopy(OBSERVE_CONFIRM_SCOPE_CONTRACT_V1)
        context.metadata["consumer_input_contract_v1"] = copy.deepcopy(CONSUMER_INPUT_CONTRACT_V1)
        context.metadata["consumer_layer_mode_integration_v1"] = copy.deepcopy(CONSUMER_LAYER_MODE_INTEGRATION_V1)
        context.metadata["consumer_migration_freeze_v1"] = copy.deepcopy(CONSUMER_MIGRATION_FREEZE_V1)
        context.metadata["consumer_migration_guard_v1"] = build_consumer_migration_guard_metadata(context.metadata)
        context.metadata["setup_detector_responsibility_contract_v1"] = copy.deepcopy(SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1)
        context.metadata["setup_mapping_contract_v1"] = copy.deepcopy(SETUP_MAPPING_CONTRACT_V1)
        context.metadata["entry_guard_contract_v1"] = copy.deepcopy(ENTRY_GUARD_CONTRACT_V1)
        context.metadata["entry_service_responsibility_contract_v1"] = copy.deepcopy(ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1)
        context.metadata["exit_handoff_contract_v1"] = copy.deepcopy(EXIT_HANDOFF_CONTRACT_V1)
        context.metadata["re_entry_contract_v1"] = copy.deepcopy(RE_ENTRY_CONTRACT_V1)
        context.metadata["consumer_logging_contract_v1"] = copy.deepcopy(CONSUMER_LOGGING_CONTRACT_V1)
        context.metadata["consumer_test_contract_v1"] = copy.deepcopy(CONSUMER_TEST_CONTRACT_V1)
        context.metadata["consumer_freeze_handoff_v1"] = copy.deepcopy(CONSUMER_FREEZE_HANDOFF_V1)
        context.metadata["consumer_scope_contract_v1"] = copy.deepcopy(CONSUMER_SCOPE_CONTRACT_V1)
        context.metadata["layer_mode_contract_v1"] = copy.deepcopy(LAYER_MODE_MODE_CONTRACT_V1)
        context.metadata["layer_mode_layer_inventory_v1"] = copy.deepcopy(LAYER_MODE_LAYER_INVENTORY_V1)
        context.metadata["layer_mode_default_policy_v1"] = copy.deepcopy(LAYER_MODE_DEFAULT_POLICY_V1)
        context.metadata["layer_mode_dual_write_contract_v1"] = copy.deepcopy(LAYER_MODE_DUAL_WRITE_CONTRACT_V1)
        context.metadata["layer_mode_influence_semantics_v1"] = copy.deepcopy(LAYER_MODE_INFLUENCE_SEMANTICS_V1)
        context.metadata["layer_mode_application_contract_v1"] = copy.deepcopy(LAYER_MODE_APPLICATION_CONTRACT_V1)
        context.metadata["layer_mode_identity_guard_contract_v1"] = copy.deepcopy(LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1)
        context.metadata["layer_mode_policy_overlay_output_contract_v1"] = copy.deepcopy(
            LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1
        )
        context.metadata["layer_mode_logging_replay_contract_v1"] = copy.deepcopy(
            LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1
        )
        context.metadata["layer_mode_test_contract_v1"] = copy.deepcopy(LAYER_MODE_TEST_CONTRACT_V1)
        context.metadata["layer_mode_freeze_handoff_v1"] = copy.deepcopy(LAYER_MODE_FREEZE_HANDOFF_V1)
        context.metadata["layer_mode_scope_contract_v1"] = copy.deepcopy(LAYER_MODE_SCOPE_CONTRACT_V1)
        context.metadata.update(build_layer_mode_effective_metadata(context.metadata))
        context.metadata.update(build_layer_mode_influence_metadata())
        context.metadata.update(build_layer_mode_application_metadata())
        context.metadata.update(build_layer_mode_identity_guard_metadata())
        context.metadata.update(build_layer_mode_policy_overlay_metadata())
        context.metadata.update(build_layer_mode_logging_replay_metadata(context.metadata))
        energy_helper_payload = build_energy_helper_v2(
            context.metadata,
            legacy_energy_snapshot=engine_bundle["energy_snapshot"].to_dict(),
        )
        context.metadata["energy_helper_v2"] = copy.deepcopy(energy_helper_payload)
        context.metadata["energy_logging_replay_contract_v1"] = copy.deepcopy(ENERGY_LOGGING_REPLAY_CONTRACT_V1)
        context.metadata["energy_migration_dual_write_v1"] = copy.deepcopy(ENERGY_MIGRATION_DUAL_WRITE_V1)
        context.metadata["energy_migration_guard_v1"] = resolve_energy_migration_bridge_state(context.metadata)
        context.metadata["energy_scope_contract_v1"] = copy.deepcopy(ENERGY_SCOPE_CONTRACT_V1)
        context.metadata["runtime_alignment_scope_contract_v1"] = copy.deepcopy(RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1)
        engine_bundle["energy_helper"] = copy.deepcopy(energy_helper_payload)
        context.metadata["semantic_foundation_contract_v1"] = copy.deepcopy(SEMANTIC_FOUNDATION_CONTRACT_V1)
        context.metadata["forecast_calibration_contract_v1"] = copy.deepcopy(FORECAST_CALIBRATION_CONTRACT_V1)
        context.metadata["outcome_labeler_scope_contract_v1"] = copy.deepcopy(OUTCOME_LABELER_SCOPE_CONTRACT_V1)
        context.metadata["prs_log_contract_v2"] = {
            "canonical_position_field": "position_snapshot_v2",
            "canonical_position_effective_field": "position_snapshot_effective_v1",
            "canonical_response_field": "response_vector_v2",
            "canonical_response_effective_field": "response_vector_effective_v1",
            "canonical_state_field": "state_vector_v2",
            "canonical_state_effective_field": "state_vector_effective_v1",
            "canonical_evidence_field": "evidence_vector_v1",
            "canonical_evidence_effective_field": "evidence_vector_effective_v1",
            "canonical_belief_field": "belief_state_v1",
            "canonical_belief_effective_field": "belief_state_effective_v1",
            "canonical_barrier_field": "barrier_state_v1",
            "canonical_barrier_effective_field": "barrier_state_effective_v1",
            "canonical_forecast_features_field": "forecast_features_v1",
            "canonical_transition_forecast_field": "transition_forecast_v1",
            "canonical_trade_management_forecast_field": "trade_management_forecast_v1",
            "canonical_forecast_gap_metrics_field": "forecast_gap_metrics_v1",
            "canonical_forecast_effective_field": "forecast_effective_policy_v1",
            "canonical_energy_field": "energy_helper_v2",
            "energy_migration_contract_field": "energy_migration_dual_write_v1",
            "energy_migration_guard_field": "energy_migration_guard_v1",
            "energy_scope_contract_field": "energy_scope_contract_v1",
            "runtime_alignment_scope_contract_field": "runtime_alignment_scope_contract_v1",
            "compatibility_energy_runtime_field": "energy_snapshot",
            "energy_logging_replay_contract_field": "energy_logging_replay_contract_v1",
            "canonical_observe_confirm_field": "observe_confirm_v2",
            "compatibility_observe_confirm_field": "observe_confirm_v1",
            "observe_confirm_input_contract_field": "observe_confirm_input_contract_v2",
            "observe_confirm_migration_contract_field": "observe_confirm_migration_dual_write_v1",
            "observe_confirm_output_contract_field": "observe_confirm_output_contract_v2",
            "observe_confirm_scope_contract_field": "observe_confirm_scope_contract_v1",
            "consumer_input_contract_field": "consumer_input_contract_v1",
            "consumer_layer_mode_integration_field": "consumer_layer_mode_integration_v1",
            "consumer_migration_freeze_field": "consumer_migration_freeze_v1",
            "consumer_migration_guard_field": "consumer_migration_guard_v1",
            "setup_detector_responsibility_contract_field": "setup_detector_responsibility_contract_v1",
            "setup_mapping_contract_field": "setup_mapping_contract_v1",
            "entry_guard_contract_field": "entry_guard_contract_v1",
            "entry_service_responsibility_contract_field": "entry_service_responsibility_contract_v1",
            "exit_handoff_contract_field": "exit_handoff_contract_v1",
            "re_entry_contract_field": "re_entry_contract_v1",
            "consumer_logging_contract_field": "consumer_logging_contract_v1",
            "consumer_test_contract_field": "consumer_test_contract_v1",
            "consumer_freeze_handoff_field": "consumer_freeze_handoff_v1",
            "consumer_scope_contract_field": "consumer_scope_contract_v1",
            "layer_mode_contract_field": "layer_mode_contract_v1",
            "layer_mode_layer_inventory_field": "layer_mode_layer_inventory_v1",
            "layer_mode_default_policy_field": "layer_mode_default_policy_v1",
            "layer_mode_dual_write_contract_field": "layer_mode_dual_write_contract_v1",
            "layer_mode_influence_semantics_field": "layer_mode_influence_semantics_v1",
            "layer_mode_application_contract_field": "layer_mode_application_contract_v1",
            "layer_mode_identity_guard_contract_field": "layer_mode_identity_guard_contract_v1",
            "layer_mode_policy_overlay_output_contract_field": "layer_mode_policy_overlay_output_contract_v1",
            "layer_mode_logging_replay_contract_field": "layer_mode_logging_replay_contract_v1",
            "layer_mode_test_contract_field": "layer_mode_test_contract_v1",
            "layer_mode_freeze_handoff_field": "layer_mode_freeze_handoff_v1",
            "layer_mode_scope_contract_field": "layer_mode_scope_contract_v1",
            "layer_mode_effective_trace_field": "layer_mode_effective_trace_v1",
            "layer_mode_influence_trace_field": "layer_mode_influence_trace_v1",
            "layer_mode_application_trace_field": "layer_mode_application_trace_v1",
            "layer_mode_identity_guard_trace_field": "layer_mode_identity_guard_trace_v1",
            "layer_mode_policy_output_field": "layer_mode_policy_v1",
            "layer_mode_logging_replay_field": "layer_mode_logging_replay_v1",
            "semantic_foundation_contract_field": "semantic_foundation_contract_v1",
            "forecast_calibration_contract_field": "forecast_calibration_contract_v1",
            "outcome_labeler_scope_contract_field": "outcome_labeler_scope_contract_v1",
        }
        return {"context": context, "preflight": preflight, **engine_bundle}

    def build_engine_context_snapshot(
        self,
        *,
        symbol: str,
        tick,
        df_all: dict,
        scorer,
        market_mode: str,
        direction_policy: str,
        liquidity_state: str = "UNKNOWN",
        spread_ratio: float = 0.0,
        box_state: str,
        bb_state: str,
        raw_scores: dict | None = None,
    ) -> dict:
        price = float(getattr(tick, "bid", 0.0) or getattr(tick, "ask", 0.0) or 0.0)
        tick_bid = self._coerce_float(getattr(tick, "bid", 0.0))
        tick_ask = self._coerce_float(getattr(tick, "ask", 0.0))
        tick_spread_points = 0.0
        if tick_bid is not None and tick_ask is not None and tick_ask >= tick_bid:
            tick_spread_points = float(tick_ask - tick_bid)
        box_low = None
        box_high = None
        session_high = None
        session_low = None
        session_box_height = None
        session_expansion_target = None
        session_position = "UNKNOWN"
        session_position_bias = 0.0
        session_expansion_progress = 0.0
        h1 = (df_all or {}).get("1H")
        if h1 is not None and not h1.empty and scorer is not None and hasattr(scorer, "session_mgr"):
            try:
                session = scorer.session_mgr.get_session_range(h1, 8, 16)
            except Exception:
                session = None
            if session:
                box_low = self._coerce_float(session.get("low"))
                box_high = self._coerce_float(session.get("high"))
                session_high = self._coerce_float(session.get("high"))
                session_low = self._coerce_float(session.get("low"))
                if session_high is not None and session_low is not None:
                    session_box_height = float(max(session_high - session_low, 0.0))
                get_expansion_target = getattr(scorer.session_mgr, "get_expansion_target", None)
                if callable(get_expansion_target):
                    try:
                        session_expansion_target = self._coerce_float(get_expansion_target(session, price))
                    except Exception:
                        session_expansion_target = None
                get_position_in_box = getattr(scorer.session_mgr, "get_position_in_box", None)
                if callable(get_position_in_box):
                    try:
                        session_position = str(get_position_in_box(session, price) or "UNKNOWN").upper()
                    except Exception:
                        session_position = "UNKNOWN"
                session_position_bias = {
                    "BELOW": -1.15,
                    "LOWER": -0.66,
                    "MIDDLE": 0.0,
                    "UPPER": 0.66,
                    "ABOVE": 1.15,
                }.get(session_position, 0.0)
                if session_box_height and session_box_height > 0.0:
                    if price > session_high:
                        session_expansion_progress = float((price - session_high) / session_box_height)
                    elif price < session_low:
                        session_expansion_progress = float((session_low - price) / session_box_height)

        bb20_up = bb20_mid = bb20_dn = None
        bb44_up = bb44_mid = bb44_dn = None
        ma20 = ma60 = ma120 = ma240 = ma480 = None
        support = resistance = None
        volatility_scale = None
        metadata = {"source": "context_classifier", "raw_scores": dict(raw_scores or {})}
        mtf_ma_big_map_v1 = {}
        mtf_trendline_map_v1 = {}
        try:
            m15 = (df_all or {}).get("15M")
            if m15 is not None and not m15.empty and scorer is not None and hasattr(scorer, "trend_mgr"):
                m15_ind = scorer.trend_mgr.add_indicators(m15)
                if m15_ind is not None and not m15_ind.empty:
                    signal_bar_ts = self._extract_frame_event_ts(m15_ind)
                    metadata["signal_timeframe"] = "15M"
                    metadata["signal_bar_ts"] = signal_bar_ts
                    cur = m15_ind.iloc[-1]
                    prev = m15_ind.iloc[-2] if len(m15_ind) >= 2 else cur
                    prev2 = m15_ind.iloc[-3] if len(m15_ind) >= 3 else prev
                    get_ma_alignment = getattr(scorer.trend_mgr, "get_ma_alignment", None)
                    ma_alignment = get_ma_alignment(cur) if callable(get_ma_alignment) else "MIXED"
                    bb20_up = self._coerce_float(cur.get("bb_20_up"))
                    bb20_mid = self._coerce_float(cur.get("bb_20_mid"))
                    bb20_dn = self._coerce_float(cur.get("bb_20_dn"))
                    bb44_up = self._coerce_float(cur.get("bb_4_up"))
                    bb44_dn = self._coerce_float(cur.get("bb_4_dn"))
                    if bb44_up is not None and bb44_dn is not None:
                        bb44_mid = (bb44_up + bb44_dn) / 2.0
                    ma20 = self._coerce_float(cur.get("ma_20"))
                    ma60 = self._coerce_float(cur.get("ma_60"))
                    ma120 = self._coerce_float(cur.get("ma_120"))
                    ma240 = self._coerce_float(cur.get("ma_240"))
                    ma480 = self._coerce_float(cur.get("ma_480"))
                    highs = pd.to_numeric(m15_ind.get("high"), errors="coerce")
                    lows = pd.to_numeric(m15_ind.get("low"), errors="coerce")
                    opens = pd.to_numeric(m15_ind.get("open"), errors="coerce") if "open" in m15_ind.columns else None
                    closes = pd.to_numeric(m15_ind.get("close"), errors="coerce")
                    ranges = (highs - lows).abs()
                    bodies = (closes - opens).abs() if opens is not None else pd.Series(dtype=float)
                    volatility_scale = self._coerce_float(ranges.tail(20).mean())
                    recent = pd.to_numeric(m15_ind.get("close"), errors="coerce").dropna().tail(20)
                    recent_ret = recent.pct_change().abs().dropna()
                    metadata.update(
                        {
                            "current_open": self._coerce_float(cur.get("open")),
                            "current_high": self._coerce_float(cur.get("high")),
                            "current_low": self._coerce_float(cur.get("low")),
                            "current_close": self._coerce_float(cur.get("close")),
                            "previous_open": self._coerce_float(prev.get("open")),
                            "previous_high": self._coerce_float(prev.get("high")),
                            "previous_low": self._coerce_float(prev.get("low")),
                            "previous_close": self._coerce_float(prev.get("close")),
                            "pre_previous_open": self._coerce_float(prev2.get("open")),
                            "pre_previous_high": self._coerce_float(prev2.get("high")),
                            "pre_previous_low": self._coerce_float(prev2.get("low")),
                            "pre_previous_close": self._coerce_float(prev2.get("close")),
                            "current_disparity": self._coerce_float(cur.get("disparity")),
                            "current_rsi": self._coerce_float(cur.get("rsi")),
                            "current_adx": self._coerce_float(cur.get("adx")),
                            "current_plus_di": self._coerce_float(cur.get("plus_di")),
                            "current_minus_di": self._coerce_float(cur.get("minus_di")),
                            "ma_alignment": str(ma_alignment or "MIXED").upper(),
                            "band_touch_tolerance": max(price, 1e-9) * 0.0002,
                            "box_touch_tolerance": max(price, 1e-9) * 0.0002,
                            "current_volatility_ratio": self._coerce_float(
                                (recent_ret.tail(5).mean() / max(recent_ret.mean(), 1e-9)) if not recent_ret.empty else 1.0
                            ),
                            "current_spread_ratio": float(spread_ratio or 0.0),
                            "recent_range_mean": self._coerce_float(ranges.tail(20).mean()),
                            "recent_body_mean": self._coerce_float(bodies.tail(20).mean()) if not bodies.empty else None,
                        }
                    )
                    current_rate_spread = self._coerce_float(cur.get("spread"))
                    recent_rate_spread_mean = None
                    if "spread" in m15_ind.columns:
                        recent_spreads = pd.to_numeric(m15_ind["spread"], errors="coerce").dropna()
                        if not recent_spreads.empty:
                            recent_rate_spread_mean = self._coerce_float(recent_spreads.tail(20).mean())
                    current_tick_volume = self._coerce_float(cur.get("tick_volume"))
                    recent_tick_volume_mean = None
                    if "tick_volume" in m15_ind.columns:
                        tick_volumes = pd.to_numeric(m15_ind["tick_volume"], errors="coerce").dropna()
                        if not tick_volumes.empty:
                            recent_tick_volume_mean = self._coerce_float(tick_volumes.tail(20).mean())
                    current_real_volume = self._coerce_float(cur.get("real_volume"))
                    recent_real_volume_mean = None
                    if "real_volume" in m15_ind.columns:
                        real_volumes = pd.to_numeric(m15_ind["real_volume"], errors="coerce").dropna()
                        if not real_volumes.empty:
                            recent_real_volume_mean = self._coerce_float(real_volumes.tail(20).mean())
                    tick_spread_ratio = (
                        float(tick_spread_points / max(float(volatility_scale), 1e-9))
                        if volatility_scale and float(volatility_scale) > 0.0
                        else 0.0
                    )
                    rate_spread_ratio = (
                        float(current_rate_spread / max(float(recent_rate_spread_mean), 1e-9))
                        if current_rate_spread is not None
                        and recent_rate_spread_mean is not None
                        and float(recent_rate_spread_mean) > 0.0
                        else 0.0
                    )
                    tick_volume_ratio = (
                        float(current_tick_volume / max(float(recent_tick_volume_mean), 1e-9))
                        if current_tick_volume is not None
                        and recent_tick_volume_mean is not None
                        and float(recent_tick_volume_mean) > 0.0
                        else 0.0
                    )
                    real_volume_ratio = (
                        float(current_real_volume / max(float(recent_real_volume_mean), 1e-9))
                        if current_real_volume is not None
                        and recent_real_volume_mean is not None
                        and float(recent_real_volume_mean) > 0.0
                        else 0.0
                    )
                    metadata.update(
                        {
                            "current_tick_spread_points": float(tick_spread_points or 0.0),
                            "current_tick_spread_ratio": tick_spread_ratio,
                            "current_rate_spread": self._coerce_float(current_rate_spread),
                            "current_rate_spread_ratio": rate_spread_ratio,
                            "recent_rate_spread_mean": self._coerce_float(recent_rate_spread_mean),
                            "current_tick_volume": self._coerce_float(current_tick_volume),
                            "current_tick_volume_ratio": tick_volume_ratio,
                            "recent_tick_volume_mean": self._coerce_float(recent_tick_volume_mean),
                            "current_real_volume": self._coerce_float(current_real_volume),
                            "current_real_volume_ratio": real_volume_ratio,
                            "recent_real_volume_mean": self._coerce_float(recent_real_volume_mean),
                        }
                    )
                    if session_box_height is not None:
                        session_box_height_ratio = (
                            float(session_box_height / max(float(volatility_scale), 1e-9))
                            if volatility_scale and float(volatility_scale) > 0.0
                            else 0.0
                        )
                        metadata.update(
                            {
                                "session_state_source": "ASIA",
                                "session_range_high": session_high,
                                "session_range_low": session_low,
                                "session_box_height": session_box_height,
                                "session_box_height_ratio": session_box_height_ratio,
                                "session_expansion_target": session_expansion_target,
                                "position_in_session_box": session_position,
                                "session_expansion_progress": session_expansion_progress,
                                "session_position_bias": session_position_bias,
                            }
                        )
                    pattern_window = m15_ind.tail(9)
                    metadata.update(
                        {
                            "pattern_recent_highs": [
                                float(v)
                                for v in pd.to_numeric(pattern_window.get("high"), errors="coerce").dropna().tolist()
                            ],
                            "pattern_recent_lows": [
                                float(v)
                                for v in pd.to_numeric(pattern_window.get("low"), errors="coerce").dropna().tolist()
                            ],
                            "pattern_recent_closes": [
                                float(v)
                                for v in pd.to_numeric(pattern_window.get("close"), errors="coerce").dropna().tolist()
                            ],
                            "pattern_window_size": int(len(pattern_window)),
                        }
                    )
        except Exception:
            pass

        try:
            mtf_ma_big_map_v1 = self._build_mtf_ma_big_map(
                df_all=df_all,
                scorer=scorer,
                price=price,
                volatility_scale=volatility_scale,
            )
            metadata["mtf_ma_big_map_v1"] = dict(mtf_ma_big_map_v1)
        except Exception:
            metadata["mtf_ma_big_map_v1"] = {}

        try:
            mtf_trendline_map_v1 = self._build_mtf_trendline_map(
                df_all=df_all,
                scorer=scorer,
                price=price,
                volatility_scale=volatility_scale,
            )
            metadata["mtf_trendline_map_v1"] = dict(mtf_trendline_map_v1)
        except Exception:
            metadata["mtf_trendline_map_v1"] = {}

        try:
            metadata["mtf_trendline_bar_map_v1"] = dict(self._build_mtf_trendline_bar_map(df_all=df_all))
        except Exception:
            metadata["mtf_trendline_bar_map_v1"] = {}

        try:
            metadata["micro_tf_bar_map_v1"] = dict(self._build_micro_tf_bar_map(df_all=df_all))
        except Exception:
            metadata["micro_tf_bar_map_v1"] = {}

        try:
            metadata["micro_tf_window_map_v1"] = dict(self._build_micro_tf_window_map(df_all=df_all))
        except Exception:
            metadata["micro_tf_window_map_v1"] = {}

        try:
            h1 = (df_all or {}).get("1H")
            if h1 is not None and not h1.empty:
                highs = pd.to_numeric(h1.get("high"), errors="coerce").dropna().tail(24)
                lows = pd.to_numeric(h1.get("low"), errors="coerce").dropna().tail(24)
                if not highs.empty:
                    resistance = self._coerce_float(highs.max())
                if not lows.empty:
                    support = self._coerce_float(lows.min())
                metadata["sr_active_support_tf"] = "1H"
                metadata["sr_active_resistance_tf"] = "1H"
                metadata["sr_level_rank"] = 1
                metadata["sr_touch_count"] = 0
        except Exception:
            pass

        try:
            advanced_state_inputs_v1 = collect_optional_advanced_state_inputs(
                symbol=symbol,
                tick=tick,
                broker=self._broker,
                metadata=metadata,
                market_mode=market_mode,
                raw_scores=raw_scores,
            )
            metadata["state_advanced_inputs_v1"] = dict(advanced_state_inputs_v1)
            metadata["advanced_input_activation_state"] = str(
                advanced_state_inputs_v1.get("activation_state", "INACTIVE") or "INACTIVE"
            )
            metadata["advanced_input_activation_reasons"] = list(
                advanced_state_inputs_v1.get("activation_reasons", []) or []
            )
        except Exception:
            metadata["state_advanced_inputs_v1"] = {
                "advanced_input_contract": "state_advanced_inputs_v1",
                "activation_state": "UNAVAILABLE",
                "activation_reasons": ["collector_failed"],
            }
            metadata["advanced_input_activation_state"] = "UNAVAILABLE"
            metadata["advanced_input_activation_reasons"] = ["collector_failed"]

        engine_ctx = build_engine_context(
            symbol=symbol,
            price=price,
            market_mode=market_mode,
            direction_policy=direction_policy,
            box_state=box_state,
            bb_state=bb_state,
            box_low=box_low,
            box_high=box_high,
            bb20_up=bb20_up,
            bb20_mid=bb20_mid,
            bb20_dn=bb20_dn,
            bb44_up=bb44_up,
            bb44_mid=bb44_mid,
            bb44_dn=bb44_dn,
            ma20=ma20,
            ma60=ma60,
            ma120=ma120,
            ma240=ma240,
            ma480=ma480,
            support=support,
            resistance=resistance,
            volatility_scale=volatility_scale,
            metadata={**metadata, "liquidity_state": str(liquidity_state or "UNKNOWN").upper()},
        )
        position_snapshot = build_position_snapshot(engine_ctx)
        position_vector = position_snapshot.vector
        engine_ctx.metadata["position_gate_input_v1"] = {
            "zones": {
                "box_zone": str(position_snapshot.zones.box_zone),
                "bb20_zone": str(position_snapshot.zones.bb20_zone),
                "bb44_zone": str(position_snapshot.zones.bb44_zone),
            },
            "interpretation": {
                "primary_label": str(position_snapshot.interpretation.primary_label),
                "alignment_label": str(position_snapshot.interpretation.alignment_label),
                "bias_label": str(position_snapshot.interpretation.bias_label),
                "conflict_kind": str(position_snapshot.interpretation.conflict_kind),
                "dominance_label": str(position_snapshot.interpretation.dominance_label),
                "secondary_context_label": str(position_snapshot.interpretation.secondary_context_label),
                "mtf_context_weight_profile_v1": dict(
                    (position_snapshot.interpretation.metadata or {}).get("mtf_context_weight_profile_v1", {}) or {}
                ),
            },
            "energy": {
                "middle_neutrality": float(position_snapshot.energy.middle_neutrality),
                "position_conflict_score": float(position_snapshot.energy.position_conflict_score),
                "lower_position_force": float(position_snapshot.energy.lower_position_force),
                "upper_position_force": float(position_snapshot.energy.upper_position_force),
            },
            "position_scale": dict(
                (position_snapshot.interpretation.metadata or {}).get("position_scale", {}) or {}
            ),
        }
        response_raw_snapshot = build_response_raw_snapshot(engine_ctx)
        response_vector_legacy = build_response_vector_from_raw(response_raw_snapshot)
        response_vector_v2 = build_response_vector_v2_from_raw(response_raw_snapshot)
        response_vector_execution_bridge = build_response_vector_execution_bridge_from_raw(response_raw_snapshot)
        state_raw_snapshot = build_state_raw_snapshot(engine_ctx)
        state_vector = build_state_vector(engine_ctx)
        state_vector_v2 = build_state_vector_v2(engine_ctx, position_snapshot=position_snapshot)
        state_vector.metadata = {
            **dict(state_vector.metadata or {}),
            "state_vector_v2": state_vector_v2.to_dict(),
            "state_execution_bridge_v1": {
                "canonical_state_field": "state_vector_v2",
                "handoff_role": "observe_confirm_execution_temperament",
                "wait_patience_gain": float(state_vector_v2.wait_patience_gain),
                "confirm_aggression_gain": float(state_vector_v2.confirm_aggression_gain),
                "hold_patience_gain": float(state_vector_v2.hold_patience_gain),
                "fast_exit_risk_penalty": float(state_vector_v2.fast_exit_risk_penalty),
                "patience_state_label": str((state_vector_v2.metadata or {}).get("patience_state_label", "") or ""),
                "topdown_state_label": str((state_vector_v2.metadata or {}).get("topdown_state_label", "") or ""),
                "quality_state_label": str((state_vector_v2.metadata or {}).get("quality_state_label", "") or ""),
                "execution_friction_state": str((state_vector_v2.metadata or {}).get("execution_friction_state", "") or ""),
                "session_exhaustion_state": str((state_vector_v2.metadata or {}).get("session_exhaustion_state", "") or ""),
                "event_risk_state": str((state_vector_v2.metadata or {}).get("event_risk_state", "") or ""),
            },
        }
        evidence_vector = build_evidence_vector(position_snapshot, response_vector_v2, state_vector_v2)
        belief_state = build_belief_state(
            key=(str(symbol or ""), str((engine_ctx.metadata or {}).get("signal_timeframe") or "15M")),
            evidence_vector_v1=evidence_vector,
            event_ts=self._coerce_epoch_seconds((engine_ctx.metadata or {}).get("signal_bar_ts")),
        )
        barrier_state = build_barrier_state(
            position_snapshot,
            state_vector_v2,
            evidence_vector,
            belief_state,
        )
        forecast_features = build_forecast_features(
            position_snapshot,
            response_vector_v2,
            state_vector_v2,
            evidence_vector,
            belief_state,
            barrier_state,
        )
        forecast_features.metadata["signal_timeframe"] = str((engine_ctx.metadata or {}).get("signal_timeframe", "") or "")
        forecast_features.metadata["signal_bar_ts"] = self._coerce_epoch_seconds((engine_ctx.metadata or {}).get("signal_bar_ts"))
        forecast_features.metadata["anchor_time_priority_fields"] = ["signal_bar_ts", "time"]
        forecast_horizon_meta = (
            (OUTCOME_LABELER_SCOPE_CONTRACT_V1.get("horizon_definition_v1", {}) or {}).get("recommended_metadata", {}) or {}
        )
        forecast_features.metadata["transition_horizon_bars"] = int(forecast_horizon_meta.get("transition_horizon_bars", 3) or 3)
        forecast_features.metadata["management_horizon_bars"] = int(forecast_horizon_meta.get("management_horizon_bars", 6) or 6)
        transition_forecast = build_transition_forecast(forecast_features)
        trade_management_forecast = build_trade_management_forecast(forecast_features)
        forecast_gap_metrics = extract_forecast_gap_metrics(transition_forecast, trade_management_forecast)
        energy_snapshot = compute_energy_snapshot(
            position_vector,
            response_vector_execution_bridge,
            state_vector_v2,
            position_snapshot=position_snapshot,
        )
        observe_confirm = route_observe_confirm(
            position_vector,
            response_vector_execution_bridge,
            state_vector_v2,
            position_snapshot,
            evidence_vector_v1=evidence_vector,
            belief_state_v1=belief_state,
            barrier_state_v1=barrier_state,
            transition_forecast_v1=transition_forecast,
            trade_management_forecast_v1=trade_management_forecast,
            forecast_gap_metrics_v1=forecast_gap_metrics,
        )
        return {
            "engine_context": engine_ctx,
            "position_snapshot": position_snapshot,
            "position_vector": position_vector,
            "position_zones": position_snapshot.zones,
            "position_interpretation": position_snapshot.interpretation,
            "position_energy": position_snapshot.energy,
            "response_raw_snapshot": response_raw_snapshot,
            "response_vector": response_vector_execution_bridge,
            "response_vector_legacy": response_vector_legacy,
            "response_vector_execution_bridge": response_vector_execution_bridge,
            "response_vector_v2": response_vector_v2,
            "state_raw_snapshot": state_raw_snapshot,
            "state_vector": state_vector,
            "state_vector_v2": state_vector_v2,
            "evidence_vector": evidence_vector,
            "belief_state": belief_state,
            "barrier_state": barrier_state,
            "forecast_features": forecast_features,
            "transition_forecast": transition_forecast,
            "trade_management_forecast": trade_management_forecast,
            "forecast_gap_metrics": dict(forecast_gap_metrics),
            "energy_snapshot": energy_snapshot,
            "observe_confirm": observe_confirm,
        }

    def build_exit_context(
        self,
        *,
        symbol: str,
        trade_ctx: dict,
        stage_inputs: dict,
        adverse_risk: bool,
        tf_confirm: bool,
    ) -> DecisionContext:
        vol_ratio = float((stage_inputs or {}).get("vol_ratio", (trade_ctx or {}).get("regime_volatility_ratio", 1.0)) or 1.0)
        exit_handoff = resolve_exit_handoff(trade_ctx or {})
        return DecisionContext(
            symbol=str(symbol or ""),
            phase="exit",
            market_mode=str((stage_inputs or {}).get("regime_now", "UNKNOWN") or "UNKNOWN").upper(),
            direction_policy=str((trade_ctx or {}).get("entry_direction", "") or ""),
            box_state=str(
                (stage_inputs or {}).get("current_box_state", (trade_ctx or {}).get("box_state", "UNKNOWN")) or "UNKNOWN"
            ).upper(),
            bb_state=str(
                (stage_inputs or {}).get("current_bb_state", (trade_ctx or {}).get("bb_state", "UNKNOWN")) or "UNKNOWN"
            ).upper(),
            liquidity_state=str((trade_ctx or {}).get("preflight_liquidity", "UNKNOWN") or "UNKNOWN").upper(),
            regime_name=str((stage_inputs or {}).get("regime_now", "UNKNOWN") or "UNKNOWN").upper(),
            regime_zone=str((trade_ctx or {}).get("regime_zone", "UNKNOWN") or "UNKNOWN").upper(),
            volatility_state=self.volatility_state_from_ratio(vol_ratio),
            raw_scores={
                "entry_quality": float((stage_inputs or {}).get("entry_quality", 0.0) or 0.0),
                "entry_model_confidence": float((stage_inputs or {}).get("entry_model_confidence", 0.0) or 0.0),
                "profit": float((stage_inputs or {}).get("profit", 0.0) or 0.0),
                "score_gap": int((stage_inputs or {}).get("score_gap", 0) or 0),
            },
            metadata={
                "regime_at_entry": str((stage_inputs or {}).get("regime_at_entry", "UNKNOWN") or "UNKNOWN").upper(),
                "adverse_risk": bool(adverse_risk),
                "tf_confirm": bool(tf_confirm),
                "entry_setup_id": str((trade_ctx or {}).get("entry_setup_id", "") or "").strip().lower(),
                "exit_profile": str((trade_ctx or {}).get("exit_profile", "") or "").strip().lower(),
                "management_profile_id": str(exit_handoff.get("management_profile_id", "") or ""),
                "invalidation_id": str(exit_handoff.get("invalidation_id", "") or ""),
                "exit_handoff_v1": dict(exit_handoff),
                "exit_handoff_contract_v1": copy.deepcopy(EXIT_HANDOFF_CONTRACT_V1),
                "consumer_freeze_handoff_v1": copy.deepcopy(CONSUMER_FREEZE_HANDOFF_V1),
            },
        )
