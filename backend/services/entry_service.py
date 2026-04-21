"""
Entry execution service.
"""

import copy
import json
import time
import math
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.domain.decision_models import DecisionContext, DecisionResult, PredictionBundle, SetupCandidate, WaitState
from backend.services.entry_authority_trace import build_entry_authority_fields
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
    classify_entry_guard_reason,
    resolve_consumer_guard_result,
    resolve_consumer_handoff_payload,
    resolve_consumer_layer_mode_policy_resolution,
    resolve_consumer_observe_confirm_input,
    resolve_consumer_observe_confirm_resolution,
)
from backend.services.consumer_check_state import build_consumer_check_state_v1
from backend.services.context_classifier import ContextClassifier
from backend.services.entry_default_side_gate_policy import resolve_entry_default_side_gate_v1
from backend.services.energy_contract import (
    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
    ENERGY_MIGRATION_DUAL_WRITE_V1,
    ENERGY_SCOPE_CONTRACT_V1,
    attach_energy_consumer_usage_trace,
    build_energy_helper_v2,
    create_energy_usage_recorder,
    finalize_energy_usage_recorder,
    record_energy_usage,
    resolve_entry_service_energy_usage,
    resolve_energy_migration_bridge_state,
)
from backend.services.entry_energy_relief_policy import (
    DEFAULT_ENTRY_PROBE_MIN_CORE_SCORE,
    DEFAULT_ENTRY_PROBE_MIN_ENERGY_READY,
    resolve_entry_energy_soft_block_policy_v1,
)
from backend.services.entry_probe_handoff_policy import resolve_entry_probe_ready_handoff_v1
from backend.services.entry_probe_plan_policy import resolve_entry_probe_plan_v1
from backend.services.entry_policy import (
    EntryComponentExtractor,
    H1EntryGatePolicy,
    TopDownEntryGatePolicy,
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
from backend.services.setup_detector import SetupDetector
from backend.services.predictors import ShadowEntryPredictor, ShadowWaitPredictor
from backend.services.wait_engine import WaitEngine
from backend.services.entry_runtime_policy import (
    AtrThresholdPolicy,
    SessionPolicy,
    SlippagePolicy,
)
from backend.services.entry_engines import EntryDecisionRecorder, EntryGuardEngine, EntryThresholdEngine
from backend.services.adaptive_profile_helpers import refresh_entry_profile
from backend.services.entry_try_open_entry import try_open_entry as helper_try_open_entry
from backend.services.runtime_alignment_contract import RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
from backend.services.storage_compaction import (
    build_probe_quick_trace_fields,
    compact_entry_decision_context,
    compact_entry_decision_result,
    compact_trace_mapping,
)
from backend.services.symbol_temperament import (
    resolve_allowed_action,
    resolve_archetype_implied_action,
)
from ports.closed_trade_read_port import ClosedTradeReadPort
from ports.trading_runtime_port import EntryRuntimePort

logger = logging.getLogger(__name__)



def _resolve_entry_eval_profile_path(config=Config) -> Path:
    raw_path = str(getattr(config, "ENTRY_EVAL_PROFILE_PATH", "") or "").strip()
    path = Path(raw_path) if raw_path else Path(r"data\analysis\entry_eval_profile_latest.json")
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path.resolve()


def _record_entry_eval_stage_timing(stage_timings_ms: dict[str, float], stage_name: str, started_at: float) -> None:
    stage_timings_ms[str(stage_name)] = round((time.perf_counter() - float(started_at)) * 1000.0, 3)


def _build_entry_eval_profile(
    *,
    symbol: str,
    elapsed_ms: float,
    stage_timings_ms: dict[str, float],
    snapshot_row: dict | None = None,
    new_ticket_count: int = 0,
    newest_ticket: int = 0,
) -> dict:
    timings = {str(k): float(v) for k, v in dict(stage_timings_ms or {}).items()}
    dominant_stage = ""
    dominant_stage_ms = 0.0
    if timings:
        dominant_stage, dominant_stage_ms = max(timings.items(), key=lambda item: float(item[1]))
    snapshot_row = dict(snapshot_row or {})
    helper_prefront_profile = dict(snapshot_row.get("entry_helper_prefront_profile_v1", {}) or {})
    helper_front_profile = dict(snapshot_row.get("entry_helper_front_profile_v1", {}) or {})
    helper_back_profile = dict(snapshot_row.get("entry_helper_back_profile_v1", {}) or {})
    helper_internal_profile = dict(snapshot_row.get("entry_helper_payload_profile_v1", {}) or {})
    append_log_profile = dict(snapshot_row.get("entry_append_log_profile_v1", {}) or {})
    return {
        "contract_version": "entry_eval_profile_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "symbol": str(symbol or ""),
        "elapsed_ms": round(float(elapsed_ms), 3),
        "slow_warn_ms": float(getattr(Config, "ENTRY_EVAL_SLOW_WARN_MS", 800.0) or 800.0),
        "is_slow": bool(float(elapsed_ms) >= float(getattr(Config, "ENTRY_EVAL_SLOW_WARN_MS", 800.0) or 800.0)),
        "dominant_stage": str(dominant_stage or ""),
        "dominant_stage_ms": round(float(dominant_stage_ms or 0.0), 3),
        "stage_timings_ms": timings,
        "helper_prefront_profile": helper_prefront_profile,
        "helper_front_profile": helper_front_profile,
        "helper_back_profile": helper_back_profile,
        "helper_internal_profile": helper_internal_profile,
        "append_log_profile": append_log_profile,
        "new_ticket_count": int(new_ticket_count or 0),
        "newest_ticket": int(newest_ticket or 0),
        "snapshot": {
            "observe_reason": str(snapshot_row.get("observe_reason", "") or ""),
            "observe_action": str(snapshot_row.get("observe_action", "") or ""),
            "observe_side": str(snapshot_row.get("observe_side", "") or ""),
            "blocked_by": str(snapshot_row.get("blocked_by", "") or ""),
            "action_none_reason": str(snapshot_row.get("action_none_reason", "") or ""),
            "quick_trace_state": str(snapshot_row.get("quick_trace_state", "") or ""),
            "probe_scene_id": str(snapshot_row.get("probe_scene_id", "") or ""),
            "action": str(snapshot_row.get("action", "") or ""),
            "outcome": str(snapshot_row.get("outcome", "") or ""),
        },
    }


def _write_entry_eval_profile(runtime, profile: dict) -> None:
    if not bool(getattr(Config, "ENTRY_EVAL_PROFILE_ENABLED", True)):
        return
    path = _resolve_entry_eval_profile_path(Config)
    state = getattr(runtime, "entry_eval_profile_state", None)
    if not isinstance(state, dict):
        state = {
            "contract_version": "entry_eval_profile_collection_v1",
            "latest_by_symbol": {},
            "recent_slow_events": [],
        }
    latest_by_symbol = dict(state.get("latest_by_symbol", {}) or {})
    symbol = str((profile or {}).get("symbol", "") or "")
    if symbol:
        latest_by_symbol[symbol] = dict(profile or {})
    recent_slow_events = list(state.get("recent_slow_events", []) or [])
    if bool((profile or {}).get("is_slow", False)):
        recent_slow_events.append(dict(profile or {}))
        recent_slow_events = recent_slow_events[-12:]
    payload = {
        "contract_version": "entry_eval_profile_collection_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "slow_warn_ms": float(getattr(Config, "ENTRY_EVAL_SLOW_WARN_MS", 800.0) or 800.0),
        "latest_by_symbol": latest_by_symbol,
        "recent_slow_events": recent_slow_events,
    }
    setattr(runtime, "entry_eval_profile_state", payload)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to write entry eval profile: %s", path)


def _first_directional_value(*values: object) -> str:
    for value in values:
        direction = str(value or "").upper()
        if direction in {"BUY", "SELL"}:
            return direction
    return ""


def _directional_side_from_policy(value: object) -> str:
    policy = str(value or "").upper()
    if policy == "BUY_ONLY":
        return "BUY"
    if policy == "SELL_ONLY":
        return "SELL"
    return ""


def _resolve_blocked_guard(*, blocked_reason: str, explicit_guard: str = "") -> str:
    explicit = str(explicit_guard or "").strip()
    if explicit:
        return explicit
    reason = str(blocked_reason or "").strip()
    if reason.startswith("outer_band_") and reason.endswith("_reversal_support_required"):
        return "outer_band_guard"
    if reason.startswith("middle_") and reason.endswith("_requires_sr_anchor"):
        return "middle_sr_anchor_guard"
    if reason.endswith("_barrier_suppressed_confirm"):
        return "barrier_guard"
    if reason.endswith("_forecast_suppressed_confirm"):
        return "forecast_guard"
    return ""


def _resolve_core_intended_trace(
    *,
    shadow_action: str,
    shadow_side: str,
    probe_ready_action: str,
    consumer_archetype_id: str,
    default_side_gate_v1: dict[str, object],
    probe_candidate_direction: str,
    fallback_allowed_action: str,
) -> dict[str, str]:
    archetype_implied_action = _first_directional_value(
        resolve_archetype_implied_action(consumer_archetype_id),
        resolve_archetype_implied_action(default_side_gate_v1.get("acting_archetype", "")),
        resolve_archetype_implied_action(default_side_gate_v1.get("winner_archetype", "")),
    )
    resolved_shadow_action = _first_directional_value(
        shadow_action,
        probe_ready_action,
    )
    intended_direction = _first_directional_value(
        resolved_shadow_action,
        archetype_implied_action,
        shadow_side,
        default_side_gate_v1.get("acting_side", ""),
        default_side_gate_v1.get("winner_side", ""),
        probe_candidate_direction,
    )
    intended_action_source = (
        "shadow_action"
        if str(shadow_action or "").upper() in {"BUY", "SELL"}
        else "probe_ready_action"
        if str(probe_ready_action or "").upper() in {"BUY", "SELL"}
        else "archetype_implied_action"
        if archetype_implied_action in {"BUY", "SELL"}
        else "shadow_side"
        if str(shadow_side or "").upper() in {"BUY", "SELL"}
        else "default_side_gate.acting_side"
        if str(default_side_gate_v1.get("acting_side", "") or "").upper() in {"BUY", "SELL"}
        else "default_side_gate.winner_side"
        if str(default_side_gate_v1.get("winner_side", "") or "").upper() in {"BUY", "SELL"}
        else "probe_candidate.direction"
        if str(probe_candidate_direction or "").upper() in {"BUY", "SELL"}
        else "preflight_allowed_action"
    )
    intended_allowed_action = resolve_allowed_action(
        intended_direction,
        fallback=str(fallback_allowed_action or ""),
    )
    return {
        "resolved_shadow_action": str(resolved_shadow_action),
        "archetype_implied_action": str(archetype_implied_action),
        "intended_direction": str(intended_direction),
        "intended_action_source": str(intended_action_source),
        "intended_allowed_action": str(intended_allowed_action),
    }


class EntryService:
    def __init__(self, runtime: EntryRuntimePort, trade_logger: ClosedTradeReadPort):
        self.runtime = runtime
        self.trade_logger = trade_logger
        self._component_extractor = EntryComponentExtractor()
        self._h1_gate_policy = H1EntryGatePolicy()
        self._topdown_gate_policy = TopDownEntryGatePolicy()
        self._session_policy = SessionPolicy()
        self._atr_policy = AtrThresholdPolicy()
        self._slippage_policy = SlippagePolicy()
        self._context_classifier = ContextClassifier(getattr(runtime, "broker", None))
        self._setup_detector = SetupDetector()
        self._wait_engine = WaitEngine()
        self._entry_predictor = ShadowEntryPredictor()
        self._wait_predictor = ShadowWaitPredictor()
        self.guard_engine = EntryGuardEngine()
        self.threshold_engine = EntryThresholdEngine(trade_logger)
        self.decision_recorder = EntryDecisionRecorder(runtime)
        self._adaptive_entry_profile = {
            "updated_at": 0.0,
            "n": 0,
            "stage_quality": {"aggressive": 0.0, "balanced": 0.0, "conservative": 0.0},
            "stage_wr": {"aggressive": 0.50, "balanced": 0.50, "conservative": 0.50},
            "stage_exp": {"aggressive": 0.0, "balanced": 0.0, "conservative": 0.0},
            "directional_bias": {},
        }

    @staticmethod
    def _canonical_symbol(symbol: str) -> str:
        s = str(symbol or "").upper().strip()
        if "BTC" in s:
            return "BTCUSD"
        if "XAU" in s or "GOLD" in s:
            return "XAUUSD"
        if "NAS" in s or "US100" in s or "USTEC" in s:
            return "NAS100"
        return s

    @staticmethod
    def _entry_price_for_action(action: str, tick) -> float:
        return EntryGuardEngine.entry_price_for_action(action, tick)

    def _pass_bb_entry_guard(self, symbol: str, action: str, tick, indicators: dict) -> tuple[bool, str]:
        return self.guard_engine.pass_bb_entry_guard(symbol, action, tick, indicators)

    def _pass_cluster_guard(
        self,
        symbol: str,
        action: str,
        tick,
        *,
        setup_id: str = "",
        setup_reason: str = "",
        preflight_allowed_action: str = "",
    ) -> tuple[bool, str]:
        semantic_signature = {}
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if isinstance(rows, dict):
            current_row = rows.get(symbol, {})
            if isinstance(current_row, dict):
                semantic_signature = self.guard_engine.build_cluster_semantic_signature(
                    current_row,
                    action=str(action or ""),
                    setup_id=str(setup_id or ""),
                    setup_reason=str(setup_reason or ""),
                )
        ok, reason = self.guard_engine.pass_cluster_guard(
            symbol,
            action,
            tick,
            setup_id=str(setup_id or ""),
            setup_reason=str(setup_reason or ""),
            preflight_allowed_action=str(preflight_allowed_action or ""),
            semantic_signature=semantic_signature,
        )
        if isinstance(rows, dict):
            current_row = rows.get(symbol, {})
            if isinstance(current_row, dict):
                trace = dict(self.guard_engine._last_cluster_trace.get(str(symbol or "").upper(), {}) or {})
                current_row["entry_cluster_semantic_guard_v1"] = trace
                rows[symbol] = current_row
        return ok, reason

    def _pass_box_middle_guard(
        self,
        symbol: str,
        action: str,
        tick,
        df_all: dict,
        scorer,
        indicators: dict,
        *,
        setup_id: str = "",
        setup_reason: str = "",
        runtime_signal_row: dict | None = None,
    ) -> tuple[bool, str]:
        return self.guard_engine.pass_box_middle_guard(
            symbol,
            action,
            tick,
            df_all,
            scorer,
            indicators,
            setup_id=str(setup_id or ""),
            setup_reason=str(setup_reason or ""),
            runtime_signal_row=dict(runtime_signal_row or {}),
        )

    @staticmethod
    def _sigmoid(x: float) -> float:
        z = max(-60.0, min(60.0, float(x)))
        return 1.0 / (1.0 + math.exp(-z))

    @staticmethod
    def _extract_entry_component_scores(result: dict, action: str) -> dict:
        snap = EntryComponentExtractor.extract(result=result, action=action)
        return {
            "entry_h1_context_score": int(snap.entry_h1_context_score),
            "entry_h1_context_opposite": int(snap.entry_h1_context_opposite),
            "entry_m1_trigger_score": int(snap.entry_m1_trigger_score),
            "entry_m1_trigger_opposite": int(snap.entry_m1_trigger_opposite),
        }

    @staticmethod
    def _evaluate_h1_entry_gate(action: str, h1_context_score: float, h1_context_opposite: float) -> tuple[bool, str]:
        dec = H1EntryGatePolicy().evaluate(
            action=action,
            h1_context_score=h1_context_score,
            h1_context_opposite=h1_context_opposite,
        )
        return bool(dec.ok), str(dec.reason)

    @staticmethod
    def _evaluate_topdown_gate(result: dict, action: str) -> tuple[bool, str, dict]:
        dec = TopDownEntryGatePolicy().evaluate(result=result, action=action)
        return bool(dec.ok), str(dec.reason), {"align": int(dec.align), "conflict": int(dec.conflict), "seen": int(dec.seen)}

    def _refresh_adaptive_entry_profile_if_needed(self) -> None:
        self._adaptive_entry_profile = refresh_entry_profile(
            current_profile=self._adaptive_entry_profile,
            trade_logger=self.trade_logger,
        )

    def _choose_entry_stage(self, score: float, contra_score: float, regime: dict, entry_prob: float | None) -> tuple[str, dict]:
        edge = float(score) - float(contra_score)
        spread_ratio = float((regime or {}).get("spread_ratio", 0.0) or 0.0)
        vol_ratio = float((regime or {}).get("volatility_ratio", 1.0) or 1.0)
        regime_name = str((regime or {}).get("name", "") or "").upper()

        p_aggr_rule = self._sigmoid((edge - 10.0) / 30.0)
        p_cons_rule = self._sigmoid((edge - 70.0) / 30.0)
        if spread_ratio > 1.0:
            p_aggr_rule -= min(0.22, (spread_ratio - 1.0) * 0.30)
            p_cons_rule += min(0.18, (spread_ratio - 1.0) * 0.25)
        if regime_name in {"RANGE", "LOW_LIQUIDITY"}:
            p_cons_rule += 0.08
            p_aggr_rule -= 0.10
        if regime_name in {"EXPANSION", "TREND"} and vol_ratio >= 1.15:
            p_aggr_rule += 0.08

        p_aggr_rule = max(0.01, min(0.99, p_aggr_rule))
        p_cons_rule = max(0.01, min(0.99, p_cons_rule))
        p_bal_rule = max(0.01, min(0.99, 1.0 - abs(p_aggr_rule - p_cons_rule)))

        self._refresh_adaptive_entry_profile_if_needed()
        prof = self._adaptive_entry_profile
        q = prof.get("stage_quality", {})
        wr = prof.get("stage_wr", {})

        p_aggr_model = max(0.05, min(0.95, float(wr.get("aggressive", 0.50)) + (0.20 * float(q.get("aggressive", 0.0)))))
        p_bal_model = max(0.05, min(0.95, float(wr.get("balanced", 0.50)) + (0.20 * float(q.get("balanced", 0.0)))))
        p_cons_model = max(0.05, min(0.95, float(wr.get("conservative", 0.50)) + (0.20 * float(q.get("conservative", 0.0)))))

        rule_w = float(getattr(Config, "ENTRY_ADAPTIVE_RULE_WEIGHT", 0.60))
        model_w = float(getattr(Config, "ENTRY_ADAPTIVE_MODEL_WEIGHT", 0.40))
        s = max(1e-9, rule_w + model_w)
        rule_w /= s
        model_w /= s

        p_aggr = (rule_w * p_aggr_rule) + (model_w * p_aggr_model)
        p_bal = (rule_w * p_bal_rule) + (model_w * p_bal_model)
        p_cons = (rule_w * p_cons_rule) + (model_w * p_cons_model)

        if entry_prob is not None:
            ep = max(0.0, min(1.0, float(entry_prob)))
            p_aggr += (ep - 0.5) * 0.20
            p_bal += (ep - 0.5) * 0.10
            p_cons += (ep - 0.5) * 0.06

        p_aggr = max(0.01, min(0.99, p_aggr))
        p_bal = max(0.01, min(0.99, p_bal))
        p_cons = max(0.01, min(0.99, p_cons))

        ev = {"aggressive": p_aggr, "balanced": p_bal, "conservative": p_cons}
        stage = max(ev, key=ev.get)
        detail = {"stage": stage, "p": {k: round(v, 4) for k, v in ev.items()}, "hist_n": int(prof.get("n", 0))}
        return stage, detail

    @staticmethod
    def _volatility_state_from_ratio(vol_ratio: float) -> str:
        return ContextClassifier.volatility_state_from_ratio(vol_ratio)

    @staticmethod
    def _zone_from_regime(regime: dict) -> str:
        return ContextClassifier.zone_from_regime(regime)

    @staticmethod
    def _regime_name(regime: dict) -> str:
        return ContextClassifier.regime_name(regime)

    @staticmethod
    def _store_runtime_snapshot(runtime, symbol: str, key: str, payload: dict) -> None:
        try:
            rows = getattr(runtime, "latest_signal_by_symbol", None)
            if not isinstance(rows, dict):
                return
            row = rows.get(symbol, {})
            if not isinstance(row, dict):
                row = {}
            row[str(key)] = dict(payload or {})
            rows[symbol] = row
        except Exception:
            return

    @staticmethod
    def _attach_consumer_scope_contract(context: DecisionContext | None) -> DecisionContext | None:
        if context is None:
            return None
        metadata_ref = getattr(context, "metadata", {})
        if isinstance(metadata_ref, dict) and all(
            key in metadata_ref
            for key in (
                "consumer_input_contract_v1",
                "consumer_scope_contract_v1",
                "layer_mode_contract_v1",
            )
        ):
            return context
        metadata = dict(getattr(context, "metadata", {}) or {})
        metadata["consumer_input_contract_v1"] = copy.deepcopy(CONSUMER_INPUT_CONTRACT_V1)
        metadata["consumer_layer_mode_integration_v1"] = copy.deepcopy(CONSUMER_LAYER_MODE_INTEGRATION_V1)
        metadata["consumer_migration_freeze_v1"] = copy.deepcopy(CONSUMER_MIGRATION_FREEZE_V1)
        metadata["setup_detector_responsibility_contract_v1"] = copy.deepcopy(SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1)
        metadata["setup_mapping_contract_v1"] = copy.deepcopy(SETUP_MAPPING_CONTRACT_V1)
        metadata["entry_guard_contract_v1"] = copy.deepcopy(ENTRY_GUARD_CONTRACT_V1)
        metadata["entry_service_responsibility_contract_v1"] = copy.deepcopy(ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1)
        metadata["exit_handoff_contract_v1"] = copy.deepcopy(EXIT_HANDOFF_CONTRACT_V1)
        metadata["re_entry_contract_v1"] = copy.deepcopy(RE_ENTRY_CONTRACT_V1)
        metadata["consumer_logging_contract_v1"] = copy.deepcopy(CONSUMER_LOGGING_CONTRACT_V1)
        metadata["consumer_test_contract_v1"] = copy.deepcopy(CONSUMER_TEST_CONTRACT_V1)
        metadata["consumer_freeze_handoff_v1"] = copy.deepcopy(CONSUMER_FREEZE_HANDOFF_V1)
        metadata["consumer_scope_contract_v1"] = copy.deepcopy(CONSUMER_SCOPE_CONTRACT_V1)
        metadata["runtime_alignment_scope_contract_v1"] = copy.deepcopy(RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1)
        metadata["layer_mode_contract_v1"] = copy.deepcopy(LAYER_MODE_MODE_CONTRACT_V1)
        metadata["layer_mode_layer_inventory_v1"] = copy.deepcopy(LAYER_MODE_LAYER_INVENTORY_V1)
        metadata["layer_mode_default_policy_v1"] = copy.deepcopy(LAYER_MODE_DEFAULT_POLICY_V1)
        metadata["layer_mode_dual_write_contract_v1"] = copy.deepcopy(LAYER_MODE_DUAL_WRITE_CONTRACT_V1)
        metadata["layer_mode_influence_semantics_v1"] = copy.deepcopy(LAYER_MODE_INFLUENCE_SEMANTICS_V1)
        metadata["layer_mode_application_contract_v1"] = copy.deepcopy(LAYER_MODE_APPLICATION_CONTRACT_V1)
        metadata["layer_mode_identity_guard_contract_v1"] = copy.deepcopy(LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1)
        metadata["layer_mode_policy_overlay_output_contract_v1"] = copy.deepcopy(
            LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1
        )
        metadata["layer_mode_logging_replay_contract_v1"] = copy.deepcopy(
            LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1
        )
        metadata["layer_mode_test_contract_v1"] = copy.deepcopy(LAYER_MODE_TEST_CONTRACT_V1)
        metadata["layer_mode_freeze_handoff_v1"] = copy.deepcopy(LAYER_MODE_FREEZE_HANDOFF_V1)
        metadata["layer_mode_scope_contract_v1"] = copy.deepcopy(LAYER_MODE_SCOPE_CONTRACT_V1)
        for key, value in build_layer_mode_effective_metadata(metadata).items():
            metadata.setdefault(key, value)
        for key, value in build_layer_mode_influence_metadata().items():
            metadata.setdefault(key, value)
        for key, value in build_layer_mode_application_metadata().items():
            metadata.setdefault(key, value)
        for key, value in build_layer_mode_identity_guard_metadata().items():
            metadata.setdefault(key, value)
        for key, value in build_layer_mode_policy_overlay_metadata().items():
            metadata.setdefault(key, value)
        for key, value in build_layer_mode_logging_replay_metadata(metadata).items():
            metadata.setdefault(key, value)
        context.metadata = metadata
        return context

    @staticmethod
    def _infer_entry_wait_state(row: dict) -> WaitState:
        return WaitEngine.build_entry_wait_state_from_row(
            symbol=str((row or {}).get("symbol", "") or ""),
            row=row,
        )

    @classmethod
    def _entry_decision_result_from_row(cls, row: dict) -> DecisionResult:
        payload = dict(row or {})
        position_snapshot_v2 = payload.get("position_snapshot_v2", {})
        response_raw_snapshot_v1 = payload.get("response_raw_snapshot_v1", {})
        response_vector_v2 = payload.get("response_vector_v2", {})
        state_raw_snapshot_v1 = payload.get("state_raw_snapshot_v1", {})
        state_vector_v2 = payload.get("state_vector_v2", {})
        evidence_vector_v1 = payload.get("evidence_vector_v1", {})
        belief_state_v1 = payload.get("belief_state_v1", {})
        barrier_state_v1 = payload.get("barrier_state_v1", {})
        forecast_features_v1 = payload.get("forecast_features_v1", {})
        transition_forecast_v1 = payload.get("transition_forecast_v1", {})
        trade_management_forecast_v1 = payload.get("trade_management_forecast_v1", {})
        forecast_gap_metrics_v1 = payload.get("forecast_gap_metrics_v1", {})
        observe_confirm_v1 = payload.get("observe_confirm_v1", {})
        observe_confirm_v2 = payload.get("observe_confirm_v2", {})
        observe_confirm_migration_dual_write_v1 = payload.get("observe_confirm_migration_dual_write_v1", {})
        observe_confirm_input_contract_v2 = payload.get("observe_confirm_input_contract_v2", {})
        observe_confirm_output_contract_v2 = payload.get("observe_confirm_output_contract_v2", {})
        observe_confirm_scope_contract_v1 = payload.get("observe_confirm_scope_contract_v1", {})
        consumer_input_contract_v1 = payload.get("consumer_input_contract_v1", {})
        consumer_layer_mode_integration_v1 = payload.get("consumer_layer_mode_integration_v1", {})
        consumer_migration_freeze_v1 = payload.get("consumer_migration_freeze_v1", {})
        setup_detector_responsibility_contract_v1 = payload.get("setup_detector_responsibility_contract_v1", {})
        setup_mapping_contract_v1 = payload.get("setup_mapping_contract_v1", {})
        entry_guard_contract_v1 = payload.get("entry_guard_contract_v1", {})
        entry_service_responsibility_contract_v1 = payload.get("entry_service_responsibility_contract_v1", {})
        exit_handoff_contract_v1 = payload.get("exit_handoff_contract_v1", {})
        re_entry_contract_v1 = payload.get("re_entry_contract_v1", {})
        consumer_logging_contract_v1 = payload.get("consumer_logging_contract_v1", {})
        consumer_test_contract_v1 = payload.get("consumer_test_contract_v1", {})
        consumer_freeze_handoff_v1 = payload.get("consumer_freeze_handoff_v1", {})
        consumer_scope_contract_v1 = payload.get("consumer_scope_contract_v1", {})
        layer_mode_contract_v1 = payload.get("layer_mode_contract_v1", {})
        layer_mode_layer_inventory_v1 = payload.get("layer_mode_layer_inventory_v1", {})
        layer_mode_default_policy_v1 = payload.get("layer_mode_default_policy_v1", {})
        layer_mode_dual_write_contract_v1 = payload.get("layer_mode_dual_write_contract_v1", {})
        layer_mode_influence_semantics_v1 = payload.get("layer_mode_influence_semantics_v1", {})
        layer_mode_application_contract_v1 = payload.get("layer_mode_application_contract_v1", {})
        layer_mode_identity_guard_contract_v1 = payload.get("layer_mode_identity_guard_contract_v1", {})
        layer_mode_policy_overlay_output_contract_v1 = payload.get("layer_mode_policy_overlay_output_contract_v1", {})
        layer_mode_logging_replay_contract_v1 = payload.get("layer_mode_logging_replay_contract_v1", {})
        layer_mode_test_contract_v1 = payload.get("layer_mode_test_contract_v1", {})
        layer_mode_freeze_handoff_v1 = payload.get("layer_mode_freeze_handoff_v1", {})
        layer_mode_scope_contract_v1 = payload.get("layer_mode_scope_contract_v1", {})
        position_snapshot_effective_v1 = payload.get("position_snapshot_effective_v1", {})
        response_vector_effective_v1 = payload.get("response_vector_effective_v1", {})
        state_vector_effective_v1 = payload.get("state_vector_effective_v1", {})
        evidence_vector_effective_v1 = payload.get("evidence_vector_effective_v1", {})
        belief_state_effective_v1 = payload.get("belief_state_effective_v1", {})
        barrier_state_effective_v1 = payload.get("barrier_state_effective_v1", {})
        forecast_effective_policy_v1 = payload.get("forecast_effective_policy_v1", {})
        layer_mode_effective_trace_v1 = payload.get("layer_mode_effective_trace_v1", {})
        layer_mode_influence_trace_v1 = payload.get("layer_mode_influence_trace_v1", {})
        layer_mode_application_trace_v1 = payload.get("layer_mode_application_trace_v1", {})
        layer_mode_identity_guard_trace_v1 = payload.get("layer_mode_identity_guard_trace_v1", {})
        layer_mode_policy_v1 = payload.get("layer_mode_policy_v1", {})
        layer_mode_logging_replay_v1 = payload.get("layer_mode_logging_replay_v1", {})
        forecast_calibration_contract_v1 = payload.get("forecast_calibration_contract_v1", {})
        outcome_labeler_scope_contract_v1 = payload.get("outcome_labeler_scope_contract_v1", {})
        energy_snapshot = payload.get("energy_snapshot", {})
        energy_helper_v2 = payload.get("energy_helper_v2", {})
        energy_logging_replay_contract_v1 = payload.get("energy_logging_replay_contract_v1", {})
        energy_migration_dual_write_v1 = payload.get("energy_migration_dual_write_v1", {})
        energy_scope_contract_v1 = payload.get("energy_scope_contract_v1", {})
        runtime_alignment_scope_contract_v1 = payload.get("runtime_alignment_scope_contract_v1", {})
        consumer_input_observe_confirm_field = payload.get("consumer_input_observe_confirm_field", "")
        consumer_input_contract_version = payload.get("consumer_input_contract_version", "")
        consumer_migration_contract_version = payload.get("consumer_migration_contract_version", "")
        consumer_used_compatibility_fallback_v1 = payload.get("consumer_used_compatibility_fallback_v1", "")
        consumer_archetype_id = payload.get("consumer_archetype_id", "")
        consumer_invalidation_id = payload.get("consumer_invalidation_id", "")
        consumer_management_profile_id = payload.get("consumer_management_profile_id", "")
        consumer_setup_id = payload.get("consumer_setup_id", "")
        consumer_guard_result = payload.get("consumer_guard_result", "")
        consumer_effective_action = payload.get("consumer_effective_action", "")
        consumer_block_reason = payload.get("consumer_block_reason", "")
        consumer_block_kind = payload.get("consumer_block_kind", "")
        consumer_block_source_layer = payload.get("consumer_block_source_layer", "")
        consumer_block_is_execution = payload.get("consumer_block_is_execution", "")
        consumer_block_is_semantic_non_action = payload.get("consumer_block_is_semantic_non_action", "")
        consumer_handoff_contract_version = payload.get("consumer_handoff_contract_version", "")
        if isinstance(position_snapshot_v2, str) and position_snapshot_v2.strip():
            try:
                position_snapshot_v2 = json.loads(position_snapshot_v2)
            except Exception:
                position_snapshot_v2 = {}
        elif not isinstance(position_snapshot_v2, dict):
            position_snapshot_v2 = {}
        if isinstance(response_raw_snapshot_v1, str) and response_raw_snapshot_v1.strip():
            try:
                response_raw_snapshot_v1 = json.loads(response_raw_snapshot_v1)
            except Exception:
                response_raw_snapshot_v1 = {}
        elif not isinstance(response_raw_snapshot_v1, dict):
            response_raw_snapshot_v1 = {}
        if isinstance(response_vector_v2, str) and response_vector_v2.strip():
            try:
                response_vector_v2 = json.loads(response_vector_v2)
            except Exception:
                response_vector_v2 = {}
        elif not isinstance(response_vector_v2, dict):
            response_vector_v2 = {}
        if isinstance(state_raw_snapshot_v1, str) and state_raw_snapshot_v1.strip():
            try:
                state_raw_snapshot_v1 = json.loads(state_raw_snapshot_v1)
            except Exception:
                state_raw_snapshot_v1 = {}
        elif not isinstance(state_raw_snapshot_v1, dict):
            state_raw_snapshot_v1 = {}
        if isinstance(state_vector_v2, str) and state_vector_v2.strip():
            try:
                state_vector_v2 = json.loads(state_vector_v2)
            except Exception:
                state_vector_v2 = {}
        elif not isinstance(state_vector_v2, dict):
            state_vector_v2 = {}
        if isinstance(evidence_vector_v1, str) and evidence_vector_v1.strip():
            try:
                evidence_vector_v1 = json.loads(evidence_vector_v1)
            except Exception:
                evidence_vector_v1 = {}
        elif not isinstance(evidence_vector_v1, dict):
            evidence_vector_v1 = {}
        if isinstance(belief_state_v1, str) and belief_state_v1.strip():
            try:
                belief_state_v1 = json.loads(belief_state_v1)
            except Exception:
                belief_state_v1 = {}
        elif not isinstance(belief_state_v1, dict):
            belief_state_v1 = {}
        if isinstance(barrier_state_v1, str) and barrier_state_v1.strip():
            try:
                barrier_state_v1 = json.loads(barrier_state_v1)
            except Exception:
                barrier_state_v1 = {}
        elif not isinstance(barrier_state_v1, dict):
            barrier_state_v1 = {}
        if isinstance(forecast_features_v1, str) and forecast_features_v1.strip():
            try:
                forecast_features_v1 = json.loads(forecast_features_v1)
            except Exception:
                forecast_features_v1 = {}
        elif not isinstance(forecast_features_v1, dict):
            forecast_features_v1 = {}
        if isinstance(transition_forecast_v1, str) and transition_forecast_v1.strip():
            try:
                transition_forecast_v1 = json.loads(transition_forecast_v1)
            except Exception:
                transition_forecast_v1 = {}
        elif not isinstance(transition_forecast_v1, dict):
            transition_forecast_v1 = {}
        if isinstance(trade_management_forecast_v1, str) and trade_management_forecast_v1.strip():
            try:
                trade_management_forecast_v1 = json.loads(trade_management_forecast_v1)
            except Exception:
                trade_management_forecast_v1 = {}
        elif not isinstance(trade_management_forecast_v1, dict):
            trade_management_forecast_v1 = {}
        if isinstance(forecast_gap_metrics_v1, str) and forecast_gap_metrics_v1.strip():
            try:
                forecast_gap_metrics_v1 = json.loads(forecast_gap_metrics_v1)
            except Exception:
                forecast_gap_metrics_v1 = {}
        elif not isinstance(forecast_gap_metrics_v1, dict):
            forecast_gap_metrics_v1 = {}
        if isinstance(observe_confirm_v1, str) and observe_confirm_v1.strip():
            try:
                observe_confirm_v1 = json.loads(observe_confirm_v1)
            except Exception:
                observe_confirm_v1 = {}
        elif not isinstance(observe_confirm_v1, dict):
            observe_confirm_v1 = {}
        if isinstance(observe_confirm_v2, str) and observe_confirm_v2.strip():
            try:
                observe_confirm_v2 = json.loads(observe_confirm_v2)
            except Exception:
                observe_confirm_v2 = {}
        elif not isinstance(observe_confirm_v2, dict):
            observe_confirm_v2 = {}
        if isinstance(observe_confirm_migration_dual_write_v1, str) and observe_confirm_migration_dual_write_v1.strip():
            try:
                observe_confirm_migration_dual_write_v1 = json.loads(observe_confirm_migration_dual_write_v1)
            except Exception:
                observe_confirm_migration_dual_write_v1 = {}
        elif not isinstance(observe_confirm_migration_dual_write_v1, dict):
            observe_confirm_migration_dual_write_v1 = {}
        if isinstance(observe_confirm_input_contract_v2, str) and observe_confirm_input_contract_v2.strip():
            try:
                observe_confirm_input_contract_v2 = json.loads(observe_confirm_input_contract_v2)
            except Exception:
                observe_confirm_input_contract_v2 = {}
        elif not isinstance(observe_confirm_input_contract_v2, dict):
            observe_confirm_input_contract_v2 = {}
        if isinstance(observe_confirm_output_contract_v2, str) and observe_confirm_output_contract_v2.strip():
            try:
                observe_confirm_output_contract_v2 = json.loads(observe_confirm_output_contract_v2)
            except Exception:
                observe_confirm_output_contract_v2 = {}
        elif not isinstance(observe_confirm_output_contract_v2, dict):
            observe_confirm_output_contract_v2 = {}
        if isinstance(observe_confirm_scope_contract_v1, str) and observe_confirm_scope_contract_v1.strip():
            try:
                observe_confirm_scope_contract_v1 = json.loads(observe_confirm_scope_contract_v1)
            except Exception:
                observe_confirm_scope_contract_v1 = {}
        elif not isinstance(observe_confirm_scope_contract_v1, dict):
            observe_confirm_scope_contract_v1 = {}
        if isinstance(consumer_input_contract_v1, str) and consumer_input_contract_v1.strip():
            try:
                consumer_input_contract_v1 = json.loads(consumer_input_contract_v1)
            except Exception:
                consumer_input_contract_v1 = {}
        elif not isinstance(consumer_input_contract_v1, dict):
            consumer_input_contract_v1 = {}
        if isinstance(consumer_layer_mode_integration_v1, str) and consumer_layer_mode_integration_v1.strip():
            try:
                consumer_layer_mode_integration_v1 = json.loads(consumer_layer_mode_integration_v1)
            except Exception:
                consumer_layer_mode_integration_v1 = {}
        elif not isinstance(consumer_layer_mode_integration_v1, dict):
            consumer_layer_mode_integration_v1 = {}
        if isinstance(consumer_migration_freeze_v1, str) and consumer_migration_freeze_v1.strip():
            try:
                consumer_migration_freeze_v1 = json.loads(consumer_migration_freeze_v1)
            except Exception:
                consumer_migration_freeze_v1 = {}
        elif not isinstance(consumer_migration_freeze_v1, dict):
            consumer_migration_freeze_v1 = {}
        if isinstance(setup_detector_responsibility_contract_v1, str) and setup_detector_responsibility_contract_v1.strip():
            try:
                setup_detector_responsibility_contract_v1 = json.loads(setup_detector_responsibility_contract_v1)
            except Exception:
                setup_detector_responsibility_contract_v1 = {}
        elif not isinstance(setup_detector_responsibility_contract_v1, dict):
            setup_detector_responsibility_contract_v1 = {}
        if isinstance(setup_mapping_contract_v1, str) and setup_mapping_contract_v1.strip():
            try:
                setup_mapping_contract_v1 = json.loads(setup_mapping_contract_v1)
            except Exception:
                setup_mapping_contract_v1 = {}
        elif not isinstance(setup_mapping_contract_v1, dict):
            setup_mapping_contract_v1 = {}
        if isinstance(entry_guard_contract_v1, str) and entry_guard_contract_v1.strip():
            try:
                entry_guard_contract_v1 = json.loads(entry_guard_contract_v1)
            except Exception:
                entry_guard_contract_v1 = {}
        elif not isinstance(entry_guard_contract_v1, dict):
            entry_guard_contract_v1 = {}
        if isinstance(exit_handoff_contract_v1, str) and exit_handoff_contract_v1.strip():
            try:
                exit_handoff_contract_v1 = json.loads(exit_handoff_contract_v1)
            except Exception:
                exit_handoff_contract_v1 = {}
        elif not isinstance(exit_handoff_contract_v1, dict):
            exit_handoff_contract_v1 = {}
        if isinstance(re_entry_contract_v1, str) and re_entry_contract_v1.strip():
            try:
                re_entry_contract_v1 = json.loads(re_entry_contract_v1)
            except Exception:
                re_entry_contract_v1 = {}
        elif not isinstance(re_entry_contract_v1, dict):
            re_entry_contract_v1 = {}
        if isinstance(consumer_logging_contract_v1, str) and consumer_logging_contract_v1.strip():
            try:
                consumer_logging_contract_v1 = json.loads(consumer_logging_contract_v1)
            except Exception:
                consumer_logging_contract_v1 = {}
        elif not isinstance(consumer_logging_contract_v1, dict):
            consumer_logging_contract_v1 = {}
        if isinstance(consumer_test_contract_v1, str) and consumer_test_contract_v1.strip():
            try:
                consumer_test_contract_v1 = json.loads(consumer_test_contract_v1)
            except Exception:
                consumer_test_contract_v1 = {}
        elif not isinstance(consumer_test_contract_v1, dict):
            consumer_test_contract_v1 = {}
        if isinstance(consumer_freeze_handoff_v1, str) and consumer_freeze_handoff_v1.strip():
            try:
                consumer_freeze_handoff_v1 = json.loads(consumer_freeze_handoff_v1)
            except Exception:
                consumer_freeze_handoff_v1 = {}
        elif not isinstance(consumer_freeze_handoff_v1, dict):
            consumer_freeze_handoff_v1 = {}
        if isinstance(entry_service_responsibility_contract_v1, str) and entry_service_responsibility_contract_v1.strip():
            try:
                entry_service_responsibility_contract_v1 = json.loads(entry_service_responsibility_contract_v1)
            except Exception:
                entry_service_responsibility_contract_v1 = {}
        elif not isinstance(entry_service_responsibility_contract_v1, dict):
            entry_service_responsibility_contract_v1 = {}
        if isinstance(consumer_scope_contract_v1, str) and consumer_scope_contract_v1.strip():
            try:
                consumer_scope_contract_v1 = json.loads(consumer_scope_contract_v1)
            except Exception:
                consumer_scope_contract_v1 = {}
        elif not isinstance(consumer_scope_contract_v1, dict):
            consumer_scope_contract_v1 = {}
        if isinstance(layer_mode_scope_contract_v1, str) and layer_mode_scope_contract_v1.strip():
            try:
                layer_mode_scope_contract_v1 = json.loads(layer_mode_scope_contract_v1)
            except Exception:
                layer_mode_scope_contract_v1 = {}
        elif not isinstance(layer_mode_scope_contract_v1, dict):
            layer_mode_scope_contract_v1 = {}
        if isinstance(layer_mode_contract_v1, str) and layer_mode_contract_v1.strip():
            try:
                layer_mode_contract_v1 = json.loads(layer_mode_contract_v1)
            except Exception:
                layer_mode_contract_v1 = {}
        elif not isinstance(layer_mode_contract_v1, dict):
            layer_mode_contract_v1 = {}
        if isinstance(layer_mode_layer_inventory_v1, str) and layer_mode_layer_inventory_v1.strip():
            try:
                layer_mode_layer_inventory_v1 = json.loads(layer_mode_layer_inventory_v1)
            except Exception:
                layer_mode_layer_inventory_v1 = {}
        elif not isinstance(layer_mode_layer_inventory_v1, dict):
            layer_mode_layer_inventory_v1 = {}
        if isinstance(layer_mode_default_policy_v1, str) and layer_mode_default_policy_v1.strip():
            try:
                layer_mode_default_policy_v1 = json.loads(layer_mode_default_policy_v1)
            except Exception:
                layer_mode_default_policy_v1 = {}
        elif not isinstance(layer_mode_default_policy_v1, dict):
            layer_mode_default_policy_v1 = {}
        if isinstance(layer_mode_dual_write_contract_v1, str) and layer_mode_dual_write_contract_v1.strip():
            try:
                layer_mode_dual_write_contract_v1 = json.loads(layer_mode_dual_write_contract_v1)
            except Exception:
                layer_mode_dual_write_contract_v1 = {}
        elif not isinstance(layer_mode_dual_write_contract_v1, dict):
            layer_mode_dual_write_contract_v1 = {}
        if isinstance(layer_mode_influence_semantics_v1, str) and layer_mode_influence_semantics_v1.strip():
            try:
                layer_mode_influence_semantics_v1 = json.loads(layer_mode_influence_semantics_v1)
            except Exception:
                layer_mode_influence_semantics_v1 = {}
        elif not isinstance(layer_mode_influence_semantics_v1, dict):
            layer_mode_influence_semantics_v1 = {}
        if isinstance(layer_mode_application_contract_v1, str) and layer_mode_application_contract_v1.strip():
            try:
                layer_mode_application_contract_v1 = json.loads(layer_mode_application_contract_v1)
            except Exception:
                layer_mode_application_contract_v1 = {}
        elif not isinstance(layer_mode_application_contract_v1, dict):
            layer_mode_application_contract_v1 = {}
        if isinstance(layer_mode_identity_guard_contract_v1, str) and layer_mode_identity_guard_contract_v1.strip():
            try:
                layer_mode_identity_guard_contract_v1 = json.loads(layer_mode_identity_guard_contract_v1)
            except Exception:
                layer_mode_identity_guard_contract_v1 = {}
        elif not isinstance(layer_mode_identity_guard_contract_v1, dict):
            layer_mode_identity_guard_contract_v1 = {}
        if isinstance(layer_mode_policy_overlay_output_contract_v1, str) and layer_mode_policy_overlay_output_contract_v1.strip():
            try:
                layer_mode_policy_overlay_output_contract_v1 = json.loads(layer_mode_policy_overlay_output_contract_v1)
            except Exception:
                layer_mode_policy_overlay_output_contract_v1 = {}
        elif not isinstance(layer_mode_policy_overlay_output_contract_v1, dict):
            layer_mode_policy_overlay_output_contract_v1 = {}
        if isinstance(layer_mode_logging_replay_contract_v1, str) and layer_mode_logging_replay_contract_v1.strip():
            try:
                layer_mode_logging_replay_contract_v1 = json.loads(layer_mode_logging_replay_contract_v1)
            except Exception:
                layer_mode_logging_replay_contract_v1 = {}
        elif not isinstance(layer_mode_logging_replay_contract_v1, dict):
            layer_mode_logging_replay_contract_v1 = {}
        if isinstance(layer_mode_test_contract_v1, str) and layer_mode_test_contract_v1.strip():
            try:
                layer_mode_test_contract_v1 = json.loads(layer_mode_test_contract_v1)
            except Exception:
                layer_mode_test_contract_v1 = {}
        elif not isinstance(layer_mode_test_contract_v1, dict):
            layer_mode_test_contract_v1 = {}
        if isinstance(layer_mode_freeze_handoff_v1, str) and layer_mode_freeze_handoff_v1.strip():
            try:
                layer_mode_freeze_handoff_v1 = json.loads(layer_mode_freeze_handoff_v1)
            except Exception:
                layer_mode_freeze_handoff_v1 = {}
        elif not isinstance(layer_mode_freeze_handoff_v1, dict):
            layer_mode_freeze_handoff_v1 = {}
        if isinstance(forecast_calibration_contract_v1, str) and forecast_calibration_contract_v1.strip():
            try:
                forecast_calibration_contract_v1 = json.loads(forecast_calibration_contract_v1)
            except Exception:
                forecast_calibration_contract_v1 = {}
        elif not isinstance(forecast_calibration_contract_v1, dict):
            forecast_calibration_contract_v1 = {}
        if isinstance(outcome_labeler_scope_contract_v1, str) and outcome_labeler_scope_contract_v1.strip():
            try:
                outcome_labeler_scope_contract_v1 = json.loads(outcome_labeler_scope_contract_v1)
            except Exception:
                outcome_labeler_scope_contract_v1 = {}
        elif not isinstance(outcome_labeler_scope_contract_v1, dict):
            outcome_labeler_scope_contract_v1 = {}
        if isinstance(energy_snapshot, str) and energy_snapshot.strip():
            try:
                energy_snapshot = json.loads(energy_snapshot)
            except Exception:
                energy_snapshot = {}
        elif not isinstance(energy_snapshot, dict):
            energy_snapshot = {}
        if isinstance(energy_helper_v2, str) and energy_helper_v2.strip():
            try:
                energy_helper_v2 = json.loads(energy_helper_v2)
            except Exception:
                energy_helper_v2 = {}
        elif not isinstance(energy_helper_v2, dict):
            energy_helper_v2 = {}
        if isinstance(energy_logging_replay_contract_v1, str) and energy_logging_replay_contract_v1.strip():
            try:
                energy_logging_replay_contract_v1 = json.loads(energy_logging_replay_contract_v1)
            except Exception:
                energy_logging_replay_contract_v1 = {}
        elif not isinstance(energy_logging_replay_contract_v1, dict):
            energy_logging_replay_contract_v1 = {}
        if isinstance(energy_migration_dual_write_v1, str) and energy_migration_dual_write_v1.strip():
            try:
                energy_migration_dual_write_v1 = json.loads(energy_migration_dual_write_v1)
            except Exception:
                energy_migration_dual_write_v1 = {}
        elif not isinstance(energy_migration_dual_write_v1, dict):
            energy_migration_dual_write_v1 = {}
        if isinstance(energy_scope_contract_v1, str) and energy_scope_contract_v1.strip():
            try:
                energy_scope_contract_v1 = json.loads(energy_scope_contract_v1)
            except Exception:
                energy_scope_contract_v1 = {}
        elif not isinstance(energy_scope_contract_v1, dict):
            energy_scope_contract_v1 = {}
        if isinstance(runtime_alignment_scope_contract_v1, str) and runtime_alignment_scope_contract_v1.strip():
            try:
                runtime_alignment_scope_contract_v1 = json.loads(runtime_alignment_scope_contract_v1)
            except Exception:
                runtime_alignment_scope_contract_v1 = {}
        elif not isinstance(runtime_alignment_scope_contract_v1, dict):
            runtime_alignment_scope_contract_v1 = {}
        layer_mode_effective_defaults = build_layer_mode_effective_metadata(
            {
                "position_snapshot_v2": position_snapshot_v2,
                "response_vector_v2": response_vector_v2,
                "state_vector_v2": state_vector_v2,
                "evidence_vector_v1": evidence_vector_v1,
                "belief_state_v1": belief_state_v1,
                "barrier_state_v1": barrier_state_v1,
                "forecast_features_v1": forecast_features_v1,
                "transition_forecast_v1": transition_forecast_v1,
                "trade_management_forecast_v1": trade_management_forecast_v1,
                "forecast_gap_metrics_v1": forecast_gap_metrics_v1,
            }
        )
        layer_mode_influence_defaults = build_layer_mode_influence_metadata()
        layer_mode_application_defaults = build_layer_mode_application_metadata()
        layer_mode_identity_guard_defaults = build_layer_mode_identity_guard_metadata()
        layer_mode_policy_overlay_defaults = build_layer_mode_policy_overlay_metadata()
        layer_mode_logging_replay_defaults = build_layer_mode_logging_replay_metadata(payload)
        if isinstance(position_snapshot_effective_v1, str) and position_snapshot_effective_v1.strip():
            try:
                position_snapshot_effective_v1 = json.loads(position_snapshot_effective_v1)
            except Exception:
                position_snapshot_effective_v1 = dict(layer_mode_effective_defaults.get("position_snapshot_effective_v1", {}))
        elif not isinstance(position_snapshot_effective_v1, dict):
            position_snapshot_effective_v1 = dict(layer_mode_effective_defaults.get("position_snapshot_effective_v1", {}))
        if isinstance(response_vector_effective_v1, str) and response_vector_effective_v1.strip():
            try:
                response_vector_effective_v1 = json.loads(response_vector_effective_v1)
            except Exception:
                response_vector_effective_v1 = dict(layer_mode_effective_defaults.get("response_vector_effective_v1", {}))
        elif not isinstance(response_vector_effective_v1, dict):
            response_vector_effective_v1 = dict(layer_mode_effective_defaults.get("response_vector_effective_v1", {}))
        if isinstance(state_vector_effective_v1, str) and state_vector_effective_v1.strip():
            try:
                state_vector_effective_v1 = json.loads(state_vector_effective_v1)
            except Exception:
                state_vector_effective_v1 = dict(layer_mode_effective_defaults.get("state_vector_effective_v1", {}))
        elif not isinstance(state_vector_effective_v1, dict):
            state_vector_effective_v1 = dict(layer_mode_effective_defaults.get("state_vector_effective_v1", {}))
        if isinstance(evidence_vector_effective_v1, str) and evidence_vector_effective_v1.strip():
            try:
                evidence_vector_effective_v1 = json.loads(evidence_vector_effective_v1)
            except Exception:
                evidence_vector_effective_v1 = dict(layer_mode_effective_defaults.get("evidence_vector_effective_v1", {}))
        elif not isinstance(evidence_vector_effective_v1, dict):
            evidence_vector_effective_v1 = dict(layer_mode_effective_defaults.get("evidence_vector_effective_v1", {}))
        if isinstance(belief_state_effective_v1, str) and belief_state_effective_v1.strip():
            try:
                belief_state_effective_v1 = json.loads(belief_state_effective_v1)
            except Exception:
                belief_state_effective_v1 = dict(layer_mode_effective_defaults.get("belief_state_effective_v1", {}))
        elif not isinstance(belief_state_effective_v1, dict):
            belief_state_effective_v1 = dict(layer_mode_effective_defaults.get("belief_state_effective_v1", {}))
        if isinstance(barrier_state_effective_v1, str) and barrier_state_effective_v1.strip():
            try:
                barrier_state_effective_v1 = json.loads(barrier_state_effective_v1)
            except Exception:
                barrier_state_effective_v1 = dict(layer_mode_effective_defaults.get("barrier_state_effective_v1", {}))
        elif not isinstance(barrier_state_effective_v1, dict):
            barrier_state_effective_v1 = dict(layer_mode_effective_defaults.get("barrier_state_effective_v1", {}))
        if isinstance(forecast_effective_policy_v1, str) and forecast_effective_policy_v1.strip():
            try:
                forecast_effective_policy_v1 = json.loads(forecast_effective_policy_v1)
            except Exception:
                forecast_effective_policy_v1 = dict(layer_mode_effective_defaults.get("forecast_effective_policy_v1", {}))
        elif not isinstance(forecast_effective_policy_v1, dict):
            forecast_effective_policy_v1 = dict(layer_mode_effective_defaults.get("forecast_effective_policy_v1", {}))
        if isinstance(layer_mode_effective_trace_v1, str) and layer_mode_effective_trace_v1.strip():
            try:
                layer_mode_effective_trace_v1 = json.loads(layer_mode_effective_trace_v1)
            except Exception:
                layer_mode_effective_trace_v1 = dict(layer_mode_effective_defaults.get("layer_mode_effective_trace_v1", {}))
        elif not isinstance(layer_mode_effective_trace_v1, dict):
            layer_mode_effective_trace_v1 = dict(layer_mode_effective_defaults.get("layer_mode_effective_trace_v1", {}))
        if isinstance(layer_mode_influence_trace_v1, str) and layer_mode_influence_trace_v1.strip():
            try:
                layer_mode_influence_trace_v1 = json.loads(layer_mode_influence_trace_v1)
            except Exception:
                layer_mode_influence_trace_v1 = dict(layer_mode_influence_defaults.get("layer_mode_influence_trace_v1", {}))
        elif not isinstance(layer_mode_influence_trace_v1, dict):
            layer_mode_influence_trace_v1 = dict(layer_mode_influence_defaults.get("layer_mode_influence_trace_v1", {}))
        if isinstance(layer_mode_application_trace_v1, str) and layer_mode_application_trace_v1.strip():
            try:
                layer_mode_application_trace_v1 = json.loads(layer_mode_application_trace_v1)
            except Exception:
                layer_mode_application_trace_v1 = dict(layer_mode_application_defaults.get("layer_mode_application_trace_v1", {}))
        elif not isinstance(layer_mode_application_trace_v1, dict):
            layer_mode_application_trace_v1 = dict(layer_mode_application_defaults.get("layer_mode_application_trace_v1", {}))
        if isinstance(layer_mode_identity_guard_trace_v1, str) and layer_mode_identity_guard_trace_v1.strip():
            try:
                layer_mode_identity_guard_trace_v1 = json.loads(layer_mode_identity_guard_trace_v1)
            except Exception:
                layer_mode_identity_guard_trace_v1 = dict(
                    layer_mode_identity_guard_defaults.get("layer_mode_identity_guard_trace_v1", {})
                )
        elif not isinstance(layer_mode_identity_guard_trace_v1, dict):
            layer_mode_identity_guard_trace_v1 = dict(
                layer_mode_identity_guard_defaults.get("layer_mode_identity_guard_trace_v1", {})
            )
        if isinstance(layer_mode_policy_v1, str) and layer_mode_policy_v1.strip():
            try:
                layer_mode_policy_v1 = json.loads(layer_mode_policy_v1)
            except Exception:
                layer_mode_policy_v1 = dict(layer_mode_policy_overlay_defaults.get("layer_mode_policy_v1", {}))
        elif not isinstance(layer_mode_policy_v1, dict):
            layer_mode_policy_v1 = dict(layer_mode_policy_overlay_defaults.get("layer_mode_policy_v1", {}))
        if isinstance(layer_mode_logging_replay_v1, str) and layer_mode_logging_replay_v1.strip():
            try:
                layer_mode_logging_replay_v1 = json.loads(layer_mode_logging_replay_v1)
            except Exception:
                layer_mode_logging_replay_v1 = dict(
                    layer_mode_logging_replay_defaults.get("layer_mode_logging_replay_v1", {})
                )
        elif not isinstance(layer_mode_logging_replay_v1, dict):
            layer_mode_logging_replay_v1 = dict(layer_mode_logging_replay_defaults.get("layer_mode_logging_replay_v1", {}))
        if not position_snapshot_effective_v1:
            position_snapshot_effective_v1 = dict(layer_mode_effective_defaults.get("position_snapshot_effective_v1", {}))
        if not response_vector_effective_v1:
            response_vector_effective_v1 = dict(layer_mode_effective_defaults.get("response_vector_effective_v1", {}))
        if not state_vector_effective_v1:
            state_vector_effective_v1 = dict(layer_mode_effective_defaults.get("state_vector_effective_v1", {}))
        if not evidence_vector_effective_v1:
            evidence_vector_effective_v1 = dict(layer_mode_effective_defaults.get("evidence_vector_effective_v1", {}))
        if not belief_state_effective_v1:
            belief_state_effective_v1 = dict(layer_mode_effective_defaults.get("belief_state_effective_v1", {}))
        if not barrier_state_effective_v1:
            barrier_state_effective_v1 = dict(layer_mode_effective_defaults.get("barrier_state_effective_v1", {}))
        if not forecast_effective_policy_v1:
            forecast_effective_policy_v1 = dict(layer_mode_effective_defaults.get("forecast_effective_policy_v1", {}))
        if not layer_mode_effective_trace_v1:
            layer_mode_effective_trace_v1 = dict(layer_mode_effective_defaults.get("layer_mode_effective_trace_v1", {}))
        if not layer_mode_influence_trace_v1:
            layer_mode_influence_trace_v1 = dict(layer_mode_influence_defaults.get("layer_mode_influence_trace_v1", {}))
        if not layer_mode_application_trace_v1:
            layer_mode_application_trace_v1 = dict(layer_mode_application_defaults.get("layer_mode_application_trace_v1", {}))
        if not layer_mode_identity_guard_trace_v1:
            layer_mode_identity_guard_trace_v1 = dict(
                layer_mode_identity_guard_defaults.get("layer_mode_identity_guard_trace_v1", {})
            )
        if not layer_mode_policy_v1:
            layer_mode_policy_v1 = dict(layer_mode_policy_overlay_defaults.get("layer_mode_policy_v1", {}))
        if not layer_mode_logging_replay_v1:
            layer_mode_logging_replay_v1 = dict(layer_mode_logging_replay_defaults.get("layer_mode_logging_replay_v1", {}))
        consumer_migration_guard_v1 = build_consumer_migration_guard_metadata(
            {
                "observe_confirm_v2": dict(observe_confirm_v2 or {}),
                "observe_confirm_v1": dict(observe_confirm_v1 or {}),
                "prs_canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                "prs_compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                "prs_log_contract_v2": {
                    "canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                    "compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                },
            }
        )
        resolved_observe_confirm = dict(
            resolve_consumer_observe_confirm_resolution(
                {
                    "observe_confirm_v2": dict(observe_confirm_v2 or {}),
                    "observe_confirm_v1": dict(observe_confirm_v1 or {}),
                    "prs_canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                    "prs_compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                    "prs_log_contract_v2": {
                        "canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                        "compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                    },
                }
            ).get("payload", {})
            or {}
        )
        energy_migration_guard_v1 = resolve_energy_migration_bridge_state(
            {
                "energy_helper_v2": dict(energy_helper_v2 or {}),
                "energy_snapshot": dict(energy_snapshot or {}),
            }
        )
        energy_bridge_rebuild_active = bool(energy_migration_guard_v1.get("used_compatibility_bridge", False))
        if not energy_helper_v2:
            energy_helper_v2 = build_energy_helper_v2(
                {
                    "evidence_vector_effective_v1": evidence_vector_effective_v1,
                    "belief_state_effective_v1": belief_state_effective_v1,
                    "barrier_state_effective_v1": barrier_state_effective_v1,
                    "forecast_effective_policy_v1": forecast_effective_policy_v1,
                    "observe_confirm_v2": dict(resolved_observe_confirm or {}),
                },
                legacy_energy_snapshot=dict(energy_migration_guard_v1.get("legacy_snapshot", {}) or {}),
            )
            energy_migration_guard_v1 = resolve_energy_migration_bridge_state(
                {
                    "energy_helper_v2": dict(energy_helper_v2 or {}),
                    "energy_snapshot": dict(energy_snapshot or {}),
                }
            )
        energy_migration_guard_v1["compatibility_bridge_rebuild_active"] = bool(energy_bridge_rebuild_active)
        energy_usage_trace = resolve_entry_service_energy_usage(payload)
        energy_helper_v2 = attach_energy_consumer_usage_trace(
            energy_helper_v2,
            component=str(energy_usage_trace.get("component", "EntryService") or "EntryService"),
            consumed_fields=list(energy_usage_trace.get("consumed_fields", []) or []),
            usage_source=str(energy_usage_trace.get("usage_source", "inferred") or "inferred"),
            usage_mode=str(energy_usage_trace.get("usage_mode", "not_consumed") or "not_consumed"),
            effective_action=str(consumer_effective_action or payload.get("action", "") or ""),
            guard_result=str(consumer_guard_result or ""),
            block_reason=str(consumer_block_reason or ""),
            block_kind=str(consumer_block_kind or ""),
            block_source_layer=str(consumer_block_source_layer or ""),
            decision_outcome=str(payload.get("entry_wait_decision", "") or payload.get("outcome", "") or ""),
            wait_state=str(payload.get("entry_wait_state", "") or ""),
            wait_reason=str(payload.get("entry_wait_reason", "") or consumer_block_reason or ""),
            live_gate_applied=bool(energy_usage_trace.get("live_gate_applied", False)),
            branch_records=list(energy_usage_trace.get("branch_records", []) or []),
        )
        if not energy_logging_replay_contract_v1:
            energy_logging_replay_contract_v1 = copy.deepcopy(ENERGY_LOGGING_REPLAY_CONTRACT_V1)
        if not energy_migration_dual_write_v1:
            energy_migration_dual_write_v1 = copy.deepcopy(ENERGY_MIGRATION_DUAL_WRITE_V1)
        if not energy_scope_contract_v1:
            energy_scope_contract_v1 = copy.deepcopy(ENERGY_SCOPE_CONTRACT_V1)
        if not runtime_alignment_scope_contract_v1:
            runtime_alignment_scope_contract_v1 = copy.deepcopy(RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1)
        context = DecisionContext(
            symbol=str(payload.get("symbol", "")),
            phase="entry",
            market_mode=str(payload.get("preflight_regime", payload.get("macro_regime", "UNKNOWN")) or "UNKNOWN"),
            direction_policy=str(payload.get("preflight_allowed_action", "UNKNOWN") or "UNKNOWN"),
            box_state=str(payload.get("box_state", "UNKNOWN") or "UNKNOWN"),
            bb_state=str(payload.get("bb_state", "UNKNOWN") or "UNKNOWN"),
            liquidity_state=str(payload.get("preflight_liquidity", "UNKNOWN") or "UNKNOWN"),
            regime_name=str(payload.get("macro_regime", "UNKNOWN") or "UNKNOWN"),
            regime_zone=str(payload.get("macro_zone", "UNKNOWN") or "UNKNOWN"),
            volatility_state=str(payload.get("volatility_state", "UNKNOWN") or "UNKNOWN"),
            raw_scores={
                "entry_score_raw": payload.get("entry_score_raw", ""),
                "contra_score_raw": payload.get("contra_score_raw", ""),
                "core_score": payload.get("core_score", ""),
                "core_buy_raw": payload.get("core_buy_raw", ""),
                "core_sell_raw": payload.get("core_sell_raw", ""),
                "core_best_raw": payload.get("core_best_raw", ""),
                "core_min_raw": payload.get("core_min_raw", ""),
                "core_margin_raw": payload.get("core_margin_raw", ""),
                "core_tie_band_raw": payload.get("core_tie_band_raw", ""),
                "h1_bias_strength": payload.get("h1_bias_strength", ""),
                "m1_trigger_strength": payload.get("m1_trigger_strength", ""),
            },
            thresholds={
                "effective_entry_threshold": payload.get("effective_entry_threshold", ""),
                "base_entry_threshold": payload.get("base_entry_threshold", ""),
                "u_min": payload.get("u_min", ""),
            },
            metadata={
                "core_pass": payload.get("core_pass", ""),
                "core_reason": payload.get("core_reason", ""),
                "core_allowed_action": payload.get("core_allowed_action", ""),
                "entry_stage": payload.get("entry_stage", ""),
                "decision_mode": payload.get("entry_decision_mode", ""),
                "preflight_reason": payload.get("preflight_reason", ""),
                "position_snapshot_v2": dict(position_snapshot_v2 or {}),
                "position_snapshot_effective_v1": dict(position_snapshot_effective_v1 or {}),
                "response_raw_snapshot_v1": dict(response_raw_snapshot_v1 or {}),
                "response_vector_v2": dict(response_vector_v2 or {}),
                "response_vector_effective_v1": dict(response_vector_effective_v1 or {}),
                "state_raw_snapshot_v1": dict(state_raw_snapshot_v1 or {}),
                "state_vector_v2": dict(state_vector_v2 or {}),
                "state_vector_effective_v1": dict(state_vector_effective_v1 or {}),
                "evidence_vector_v1": dict(evidence_vector_v1 or {}),
                "evidence_vector_effective_v1": dict(evidence_vector_effective_v1 or {}),
                "belief_state_v1": dict(belief_state_v1 or {}),
                "belief_state_effective_v1": dict(belief_state_effective_v1 or {}),
                "barrier_state_v1": dict(barrier_state_v1 or {}),
                "barrier_state_effective_v1": dict(barrier_state_effective_v1 or {}),
                "forecast_features_v1": dict(forecast_features_v1 or {}),
                "transition_forecast_v1": dict(transition_forecast_v1 or {}),
                "trade_management_forecast_v1": dict(trade_management_forecast_v1 or {}),
                "forecast_gap_metrics_v1": dict(forecast_gap_metrics_v1 or {}),
                "forecast_effective_policy_v1": dict(forecast_effective_policy_v1 or {}),
                "energy_snapshot": dict(energy_snapshot or {}),
                "energy_helper_v2": dict(energy_helper_v2 or {}),
                "energy_logging_replay_contract_v1": dict(
                    energy_logging_replay_contract_v1 or ENERGY_LOGGING_REPLAY_CONTRACT_V1
                ),
                "energy_migration_dual_write_v1": dict(
                    energy_migration_dual_write_v1 or ENERGY_MIGRATION_DUAL_WRITE_V1
                ),
                "energy_migration_guard_v1": dict(energy_migration_guard_v1 or {}),
                "energy_scope_contract_v1": dict(energy_scope_contract_v1 or ENERGY_SCOPE_CONTRACT_V1),
                "runtime_alignment_scope_contract_v1": dict(
                    runtime_alignment_scope_contract_v1 or RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
                ),
                "observe_confirm_v1": dict(observe_confirm_v1 or {}),
                "observe_confirm_v2": dict(observe_confirm_v2 or {}),
                "observe_confirm_migration_dual_write_v1": dict(observe_confirm_migration_dual_write_v1 or {}),
                "observe_confirm_input_contract_v2": dict(observe_confirm_input_contract_v2 or {}),
                "observe_confirm_output_contract_v2": dict(observe_confirm_output_contract_v2 or {}),
                "observe_confirm_scope_contract_v1": dict(observe_confirm_scope_contract_v1 or {}),
                "consumer_input_contract_v1": dict(consumer_input_contract_v1 or CONSUMER_INPUT_CONTRACT_V1),
                "consumer_layer_mode_integration_v1": dict(
                    consumer_layer_mode_integration_v1 or CONSUMER_LAYER_MODE_INTEGRATION_V1
                ),
                "consumer_migration_freeze_v1": dict(consumer_migration_freeze_v1 or CONSUMER_MIGRATION_FREEZE_V1),
                "consumer_migration_guard_v1": dict(consumer_migration_guard_v1 or {}),
                "setup_detector_responsibility_contract_v1": dict(
                    setup_detector_responsibility_contract_v1 or SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1
                ),
                "setup_mapping_contract_v1": dict(setup_mapping_contract_v1 or SETUP_MAPPING_CONTRACT_V1),
                "entry_guard_contract_v1": dict(entry_guard_contract_v1 or ENTRY_GUARD_CONTRACT_V1),
                "entry_service_responsibility_contract_v1": dict(
                    entry_service_responsibility_contract_v1 or ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1
                ),
                "exit_handoff_contract_v1": dict(exit_handoff_contract_v1 or EXIT_HANDOFF_CONTRACT_V1),
                "re_entry_contract_v1": dict(re_entry_contract_v1 or RE_ENTRY_CONTRACT_V1),
                "consumer_logging_contract_v1": dict(consumer_logging_contract_v1 or CONSUMER_LOGGING_CONTRACT_V1),
                "consumer_test_contract_v1": dict(consumer_test_contract_v1 or CONSUMER_TEST_CONTRACT_V1),
                "consumer_freeze_handoff_v1": dict(consumer_freeze_handoff_v1 or CONSUMER_FREEZE_HANDOFF_V1),
                "consumer_scope_contract_v1": dict(consumer_scope_contract_v1 or CONSUMER_SCOPE_CONTRACT_V1),
                "layer_mode_contract_v1": dict(layer_mode_contract_v1 or LAYER_MODE_MODE_CONTRACT_V1),
                "layer_mode_layer_inventory_v1": dict(layer_mode_layer_inventory_v1 or LAYER_MODE_LAYER_INVENTORY_V1),
                "layer_mode_default_policy_v1": dict(layer_mode_default_policy_v1 or LAYER_MODE_DEFAULT_POLICY_V1),
                "layer_mode_dual_write_contract_v1": dict(layer_mode_dual_write_contract_v1 or LAYER_MODE_DUAL_WRITE_CONTRACT_V1),
                "layer_mode_influence_semantics_v1": dict(
                    layer_mode_influence_semantics_v1 or LAYER_MODE_INFLUENCE_SEMANTICS_V1
                ),
                "layer_mode_application_contract_v1": dict(
                    layer_mode_application_contract_v1 or LAYER_MODE_APPLICATION_CONTRACT_V1
                ),
                "layer_mode_identity_guard_contract_v1": dict(
                    layer_mode_identity_guard_contract_v1 or LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1
                ),
                "layer_mode_policy_overlay_output_contract_v1": dict(
                    layer_mode_policy_overlay_output_contract_v1 or LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1
                ),
                "layer_mode_logging_replay_contract_v1": dict(
                    layer_mode_logging_replay_contract_v1 or LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1
                ),
                "layer_mode_test_contract_v1": dict(layer_mode_test_contract_v1 or LAYER_MODE_TEST_CONTRACT_V1),
                "layer_mode_freeze_handoff_v1": dict(layer_mode_freeze_handoff_v1 or LAYER_MODE_FREEZE_HANDOFF_V1),
                "layer_mode_scope_contract_v1": dict(layer_mode_scope_contract_v1 or LAYER_MODE_SCOPE_CONTRACT_V1),
                "layer_mode_effective_trace_v1": dict(layer_mode_effective_trace_v1 or {}),
                "layer_mode_influence_trace_v1": dict(layer_mode_influence_trace_v1 or {}),
                "layer_mode_application_trace_v1": dict(layer_mode_application_trace_v1 or {}),
                "layer_mode_identity_guard_trace_v1": dict(layer_mode_identity_guard_trace_v1 or {}),
                "layer_mode_policy_v1": dict(layer_mode_policy_v1 or {}),
                "layer_mode_logging_replay_v1": dict(layer_mode_logging_replay_v1 or {}),
                "forecast_calibration_contract_v1": dict(forecast_calibration_contract_v1 or {}),
                "outcome_labeler_scope_contract_v1": dict(outcome_labeler_scope_contract_v1 or {}),
                "prs_contract_version": payload.get("prs_contract_version", "") or "v2",
                "prs_canonical_position_field": payload.get("prs_canonical_position_field", "") or "position_snapshot_v2",
                "prs_canonical_position_effective_field": payload.get("prs_canonical_position_effective_field", "") or "position_snapshot_effective_v1",
                "prs_canonical_response_field": payload.get("prs_canonical_response_field", "") or "response_vector_v2",
                "prs_canonical_response_effective_field": payload.get("prs_canonical_response_effective_field", "") or "response_vector_effective_v1",
                "prs_canonical_state_field": payload.get("prs_canonical_state_field", "") or "state_vector_v2",
                "prs_canonical_state_effective_field": payload.get("prs_canonical_state_effective_field", "") or "state_vector_effective_v1",
                "prs_canonical_evidence_field": payload.get("prs_canonical_evidence_field", "") or "evidence_vector_v1",
                "prs_canonical_evidence_effective_field": payload.get("prs_canonical_evidence_effective_field", "") or "evidence_vector_effective_v1",
                "prs_canonical_belief_field": payload.get("prs_canonical_belief_field", "") or "belief_state_v1",
                "prs_canonical_belief_effective_field": payload.get("prs_canonical_belief_effective_field", "") or "belief_state_effective_v1",
                "prs_canonical_barrier_field": payload.get("prs_canonical_barrier_field", "") or "barrier_state_v1",
                "prs_canonical_barrier_effective_field": payload.get("prs_canonical_barrier_effective_field", "") or "barrier_state_effective_v1",
                "prs_canonical_forecast_features_field": payload.get("prs_canonical_forecast_features_field", "") or "forecast_features_v1",
                "prs_canonical_transition_forecast_field": payload.get("prs_canonical_transition_forecast_field", "") or "transition_forecast_v1",
                "prs_canonical_trade_management_forecast_field": payload.get("prs_canonical_trade_management_forecast_field", "") or "trade_management_forecast_v1",
                "prs_canonical_forecast_gap_metrics_field": payload.get("prs_canonical_forecast_gap_metrics_field", "") or "forecast_gap_metrics_v1",
                "prs_canonical_forecast_effective_field": payload.get("prs_canonical_forecast_effective_field", "") or "forecast_effective_policy_v1",
                "prs_canonical_energy_field": payload.get("prs_canonical_energy_field", "") or "energy_helper_v2",
                "prs_canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", "") or "observe_confirm_v2",
                "prs_compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", "") or "observe_confirm_v1",
                "energy_migration_contract_field": payload.get("energy_migration_contract_field", "")
                or "energy_migration_dual_write_v1",
                "energy_migration_guard_field": payload.get("energy_migration_guard_field", "")
                or "energy_migration_guard_v1",
                "energy_scope_contract_field": payload.get("energy_scope_contract_field", "") or "energy_scope_contract_v1",
                "runtime_alignment_scope_contract_field": payload.get(
                    "runtime_alignment_scope_contract_field",
                    "",
                )
                or "runtime_alignment_scope_contract_v1",
                "energy_compatibility_runtime_field": payload.get("energy_compatibility_runtime_field", "") or "energy_snapshot",
                "energy_logging_replay_contract_field": payload.get("energy_logging_replay_contract_field", "")
                or "energy_logging_replay_contract_v1",
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
                "consumer_input_observe_confirm_field": payload.get("consumer_input_observe_confirm_field", ""),
                "consumer_input_contract_version": payload.get("consumer_input_contract_version", ""),
                "consumer_policy_input_field": payload.get("consumer_policy_input_field", "") or "layer_mode_policy_v1",
                "consumer_policy_contract_version": payload.get("consumer_policy_contract_version", "")
                or CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"],
                "consumer_policy_identity_preserved": bool(
                    payload.get(
                        "consumer_policy_identity_preserved",
                        bool((layer_mode_policy_v1 or {}).get("identity_preserved", False)),
                    )
                ),
                "consumer_migration_contract_version": consumer_migration_contract_version,
                "consumer_used_compatibility_fallback_v1": consumer_used_compatibility_fallback_v1,
                "consumer_archetype_id": consumer_archetype_id,
                "consumer_invalidation_id": consumer_invalidation_id,
                "consumer_management_profile_id": consumer_management_profile_id,
                "consumer_setup_id": consumer_setup_id or payload.get("setup_id", ""),
                "consumer_guard_result": consumer_guard_result,
                "consumer_effective_action": consumer_effective_action,
                "consumer_block_reason": consumer_block_reason,
                "consumer_block_kind": consumer_block_kind,
                "consumer_block_source_layer": consumer_block_source_layer,
                "consumer_block_is_execution": consumer_block_is_execution,
                "consumer_block_is_semantic_non_action": consumer_block_is_semantic_non_action,
                "consumer_handoff_contract_version": consumer_handoff_contract_version,
                "consumer_energy_action_readiness": payload.get("consumer_energy_action_readiness", ""),
                "consumer_energy_priority_hint": payload.get("consumer_energy_priority_hint", ""),
                "consumer_energy_wait_vs_enter_hint": payload.get("consumer_energy_wait_vs_enter_hint", ""),
                "consumer_energy_gap_dominant_hint": payload.get("consumer_energy_gap_dominant_hint", ""),
                "consumer_energy_forecast_branch_hint": payload.get("consumer_energy_forecast_branch_hint", ""),
                "consumer_energy_soft_block_active": bool(payload.get("consumer_energy_soft_block_active", False)),
                "consumer_energy_soft_block_reason": payload.get("consumer_energy_soft_block_reason", ""),
                "consumer_energy_soft_block_strength": payload.get("consumer_energy_soft_block_strength", ""),
                "consumer_energy_confidence_delta": payload.get("consumer_energy_confidence_delta", ""),
                "consumer_energy_forecast_gap_usage_active": bool(
                    payload.get("consumer_energy_forecast_gap_usage_active", False)
                ),
                "consumer_energy_forecast_gap_live_gate_used": bool(
                    payload.get("consumer_energy_forecast_gap_live_gate_used", False)
                ),
                "consumer_energy_transition_confirm_fake_gap": payload.get(
                    "consumer_energy_transition_confirm_fake_gap", ""
                ),
                "consumer_energy_management_continue_fail_gap": payload.get(
                    "consumer_energy_management_continue_fail_gap", ""
                ),
                "consumer_energy_management_recover_reentry_gap": payload.get(
                    "consumer_energy_management_recover_reentry_gap", ""
                ),
                "consumer_energy_hold_exit_gap": payload.get("consumer_energy_hold_exit_gap", ""),
                "consumer_energy_same_side_flip_gap": payload.get("consumer_energy_same_side_flip_gap", ""),
                "consumer_energy_forecast_gap_usage_v1": dict(
                    payload.get("consumer_energy_forecast_gap_usage_v1", {}) or {}
                ),
                "consumer_energy_live_gate_applied": bool(payload.get("consumer_energy_live_gate_applied", False)),
                "consumer_energy_usage_trace_v1": dict(payload.get("consumer_energy_usage_trace_v1", {}) or {}),
                "transition_side_separation": payload.get("transition_side_separation", ""),
                "transition_confirm_fake_gap": payload.get("transition_confirm_fake_gap", ""),
                "transition_reversal_continuation_gap": payload.get("transition_reversal_continuation_gap", ""),
                "management_continue_fail_gap": payload.get("management_continue_fail_gap", ""),
                "management_recover_reentry_gap": payload.get("management_recover_reentry_gap", ""),
                "forecast_assist_v1": dict(payload.get("forecast_assist_v1", {}) or {}),
                "consumer_forecast_assist_active": bool(payload.get("consumer_forecast_assist_active", False)),
                "consumer_forecast_assist_source": payload.get("consumer_forecast_assist_source", ""),
                "consumer_forecast_mode": payload.get("consumer_forecast_mode", ""),
                "consumer_forecast_decision_hint": payload.get("consumer_forecast_decision_hint", ""),
                "consumer_forecast_confirm_fake_gap": payload.get("consumer_forecast_confirm_fake_gap", ""),
                "consumer_forecast_wait_confirm_gap": payload.get("consumer_forecast_wait_confirm_gap", ""),
                "consumer_forecast_continue_fail_gap": payload.get("consumer_forecast_continue_fail_gap", ""),
                "consumer_forecast_action_confirm_score": payload.get("consumer_forecast_action_confirm_score", ""),
                "consumer_forecast_priority_boost_active": bool(
                    payload.get("consumer_forecast_priority_boost_active", False)
                ),
                "consumer_forecast_confidence_delta": payload.get("consumer_forecast_confidence_delta", ""),
            },
        )
        context = cls._attach_consumer_scope_contract(context)
        wait_state = cls._infer_entry_wait_state(payload)
        setup_id = str(payload.get("setup_id", "") or "")
        setup_status = str(payload.get("setup_status", "") or "")
        selected_setup = None
        if setup_id or setup_status:
            selected_setup = SetupCandidate(
                setup_id=setup_id,
                side=str(payload.get("setup_side", payload.get("action", "")) or ""),
                status=(setup_status or ("matched" if setup_id else "rejected")),
                trigger_state=str(payload.get("setup_trigger_state", "UNKNOWN") or "UNKNOWN"),
                entry_quality=float(
                    pd.to_numeric(
                        payload.get("setup_entry_quality", payload.get("entry_quality", 0.0)),
                        errors="coerce",
                    ) or 0.0
                ),
                score=float(pd.to_numeric(payload.get("setup_score", 0.0), errors="coerce") or 0.0),
                metadata={"reason": str(payload.get("setup_reason", "") or "")},
            )
        predictions = None
        pred_raw = payload.get("prediction_bundle", "")
        pred_map = {}
        if isinstance(pred_raw, str) and pred_raw.strip():
            try:
                pred_map = json.loads(pred_raw)
            except Exception:
                pred_map = {}
        elif isinstance(pred_raw, dict):
            pred_map = dict(pred_raw)
        if pred_map:
            predictions = PredictionBundle(
                entry=dict(pred_map.get("entry", {}) or {}),
                wait=dict(pred_map.get("wait", {}) or {}),
                exit=dict(pred_map.get("exit", {}) or {}),
                reverse=dict(pred_map.get("reverse", {}) or {}),
                metadata=dict(pred_map.get("metadata", {}) or {}),
            )
        return DecisionResult(
            phase="entry",
            symbol=str(payload.get("symbol", "")),
            action=str(payload.get("action", payload.get("action_selected", "")) or ""),
            outcome=str(payload.get("outcome", "") or ""),
            blocked_by=str(payload.get("blocked_by", "") or ""),
            reason=str(payload.get("core_reason", payload.get("action_none_reason", "")) or ""),
            decision_rule_version=str(payload.get("decision_rule_version", "") or ""),
            context=context,
            selected_setup=selected_setup,
            wait_state=wait_state,
            predictions=predictions,
            metrics={
                "considered": payload.get("considered", ""),
                "size_multiplier": payload.get("size_multiplier", ""),
                "cooldown_sec": payload.get("cooldown_sec", ""),
                "spread": payload.get("spread", ""),
                "ai_probability": payload.get("ai_probability", ""),
                "utility_u": payload.get("utility_u", ""),
                "utility_p": payload.get("utility_p", ""),
                "utility_w": payload.get("utility_w", ""),
                "utility_l": payload.get("utility_l", ""),
                "utility_cost": payload.get("utility_cost", ""),
                "utility_context_adj": payload.get("utility_context_adj", ""),
                "u_pass": payload.get("u_pass", ""),
                "observe_reason": payload.get("observe_reason", ""),
                "action_none_reason": payload.get("action_none_reason", ""),
            },
        )

    @classmethod
    def _build_lean_entry_decision_artifacts(cls, row: dict) -> tuple[dict, dict]:
        payload = dict(row or {})
        context_payload = {
            "symbol": str(payload.get("symbol", "") or ""),
            "phase": "entry",
            "market_mode": str(payload.get("preflight_regime", "") or ""),
            "direction_policy": str(payload.get("preflight_allowed_action", "") or ""),
            "box_state": str(payload.get("box_state", "") or ""),
            "bb_state": str(payload.get("bb_state", "") or ""),
            "liquidity_state": str(payload.get("preflight_liquidity", "") or ""),
            "regime_name": str(payload.get("preflight_regime", "") or ""),
            "regime_zone": str(payload.get("preflight_approach_mode", "") or ""),
            "volatility_state": "",
            "metadata": {
                "core_pass": payload.get("core_pass", ""),
                "core_reason": str(payload.get("core_reason", "") or ""),
                "core_allowed_action": str(payload.get("core_allowed_action", "") or ""),
                "entry_stage": str(payload.get("entry_stage", "") or ""),
                "decision_mode": str(payload.get("decision_rule_version", "") or ""),
                "preflight_reason": str(payload.get("preflight_reason", "") or ""),
                "observe_confirm_v2": payload.get("observe_confirm_v2", {}),
                "energy_helper_v2": payload.get("energy_helper_v2", {}),
                "forecast_effective_policy_v1": payload.get("forecast_effective_policy_v1", {}),
                "forecast_assist_v1": payload.get("forecast_assist_v1", {}),
                "entry_default_side_gate_v1": payload.get("entry_default_side_gate_v1", {}),
                "entry_probe_plan_v1": payload.get("entry_probe_plan_v1", {}),
                "edge_pair_law_v1": payload.get("edge_pair_law_v1", {}),
                "probe_candidate_v1": payload.get("probe_candidate_v1", {}),
            },
        }
        result_payload = {
            "phase": "entry",
            "symbol": str(payload.get("symbol", "") or ""),
            "action": str(payload.get("action", "") or ""),
            "outcome": str(payload.get("outcome", "") or ""),
            "blocked_by": str(payload.get("blocked_by", "") or ""),
            "reason": str(
                payload.get("observe_reason", "")
                or payload.get("action_none_reason", "")
                or payload.get("blocked_by", "")
                or ""
            ),
            "decision_rule_version": str(payload.get("decision_rule_version", "") or ""),
            "wait_state": str(payload.get("quick_trace_state", "") or payload.get("entry_wait_state", "") or ""),
            "selected_setup": {
                "setup_id": str(payload.get("setup_id", "") or ""),
                "setup_side": str(payload.get("setup_side", "") or ""),
                "setup_status": str(payload.get("setup_status", "") or ""),
                "setup_trigger_state": str(payload.get("setup_trigger_state", "") or ""),
                "setup_score": payload.get("setup_score", ""),
                "setup_entry_quality": payload.get("setup_entry_quality", ""),
                "setup_reason": str(payload.get("setup_reason", "") or ""),
            },
            "metrics": {
                "considered": payload.get("considered", ""),
                "size_multiplier": payload.get("size_multiplier", ""),
                "ai_probability": payload.get("ai_probability", ""),
                "utility_u": payload.get("utility_u", ""),
                "observe_reason": payload.get("observe_reason", ""),
                "action_none_reason": payload.get("action_none_reason", ""),
            },
            "predictions": {
                "wait": {
                    "observe_reason": str(payload.get("observe_reason", "") or ""),
                    "action_none_reason": str(payload.get("action_none_reason", "") or ""),
                }
            },
        }
        return (
            compact_entry_decision_context(context_payload),
            compact_entry_decision_result(result_payload),
        )

    def _compute_context_threshold_adjustment(
        self,
        regime: dict,
        topdown_stat: dict,
        entry_h1_context_score: int,
        entry_h1_context_opposite: int,
    ) -> tuple[int, dict]:
        return self.threshold_engine.compute_context_threshold_adjustment(
            regime=regime,
            topdown_stat=topdown_stat,
            entry_h1_context_score=entry_h1_context_score,
            entry_h1_context_opposite=entry_h1_context_opposite,
        )

    @staticmethod
    def _coerce_float(value: object, default: float = 0.0) -> float:
        try:
            parsed = pd.to_numeric(value, errors="coerce")
            if pd.isna(parsed):
                return float(default)
            return float(parsed)
        except Exception:
            return float(default)

    @staticmethod
    def _coerce_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        return text in {"1", "true", "yes", "on"}

    def _resolve_nas_clean_confirm_low_vol_relief(
        self,
        *,
        symbol: str,
        blocked_reason: str,
    ) -> tuple[bool, dict[str, object]]:
        canonical_symbol = self._canonical_symbol(symbol)
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        row = rows.get(symbol, {}) if isinstance(rows, dict) else {}
        row = dict(row or {}) if isinstance(row, dict) else {}
        observe_reason = str(row.get("observe_reason", "") or "").lower()
        plan = dict(row.get("entry_probe_plan_v1", {}) or {})
        probe_scene_id = str(
            row.get("probe_scene_id")
            or plan.get("scene_id")
            or plan.get("symbol_scene_relief")
            or ""
        ).lower()
        pair_gap = self._coerce_float(plan.get("pair_gap", row.get("probe_pair_gap", 0.0)))
        candidate_support = self._coerce_float(
            plan.get("candidate_support", row.get("probe_candidate_support", 0.0))
        )
        intended_action = str(plan.get("intended_action", row.get("action", "")) or "").upper()
        plan_ready = self._coerce_bool(plan.get("ready_for_entry", row.get("probe_plan_ready", False)))
        action_confirm_score = self._coerce_float(plan.get("action_confirm_score", 0.0))
        confirm_fake_gap = self._coerce_float(
            plan.get("confirm_fake_gap", row.get("transition_confirm_fake_gap", 0.0))
        )
        wait_confirm_gap = self._coerce_float(plan.get("wait_confirm_gap", 0.0))
        continue_fail_gap = self._coerce_float(
            plan.get("continue_fail_gap", row.get("management_continue_fail_gap", 0.0))
        )
        same_side_barrier = self._coerce_float(plan.get("same_side_barrier", 1.0), default=1.0)
        structural_relief_active = self._coerce_bool(plan.get("structural_relief_active", False))
        structural_relief_candidate_support = self._coerce_float(
            plan.get("structural_relief_candidate_support", 0.0)
        )
        structural_relief_action_confirm_score = self._coerce_float(
            plan.get("structural_relief_action_confirm_score", 0.0)
        )
        structural_relief_confirm_fake_gap = self._coerce_float(
            plan.get("structural_relief_confirm_fake_gap", -1.0),
            default=-1.0,
        )
        structural_relief_wait_confirm_gap = self._coerce_float(
            plan.get("structural_relief_wait_confirm_gap", -1.0),
            default=-1.0,
        )
        structural_relief_continue_fail_gap = self._coerce_float(
            plan.get("structural_relief_continue_fail_gap", -1.0),
            default=-1.0,
        )
        structural_relief_max_side_barrier = self._coerce_float(
            plan.get("structural_relief_max_side_barrier", 1.0),
            default=1.0,
        )
        near_confirm_pair_gap = self._coerce_float(plan.get("near_confirm_pair_gap", 0.10), default=0.10)
        near_confirm = self._coerce_bool(plan.get("near_confirm", False)) or (
            pair_gap >= near_confirm_pair_gap
        )
        allowed_observe_reasons = {
            "upper_reject_probe_observe",
            "lower_rebound_probe_observe",
        }
        relaxed_action_confirm_floor = max(structural_relief_action_confirm_score - 0.03, 0.05)
        relaxed_confirm_fake_floor = structural_relief_confirm_fake_gap - 0.04
        relaxed_wait_confirm_floor = structural_relief_wait_confirm_gap - 0.05
        relaxed_continue_fail_floor = structural_relief_continue_fail_gap - 0.04
        pair_support = bool(candidate_support >= structural_relief_candidate_support)
        near_confirm_support = bool(pair_gap >= near_confirm_pair_gap)
        forecast_support = bool(
            action_confirm_score >= relaxed_action_confirm_floor
            and confirm_fake_gap >= relaxed_confirm_fake_floor
            and wait_confirm_gap >= relaxed_wait_confirm_floor
            and continue_fail_gap >= relaxed_continue_fail_floor
        )
        barrier_support = bool(same_side_barrier <= structural_relief_max_side_barrier)
        active = self._coerce_bool(plan.get("active", row.get("probe_plan_active", False)))
        plan_ready_support = bool(
            active
            and plan_ready
            and intended_action in {"BUY", "SELL"}
            and probe_scene_id == "nas_clean_confirm_probe"
            and observe_reason in allowed_observe_reasons
        )
        applied = bool(
            canonical_symbol == "NAS100"
            and str(blocked_reason or "") == "hard_guard_volatility_too_low"
            and probe_scene_id == "nas_clean_confirm_probe"
            and observe_reason in allowed_observe_reasons
            and active
            and (
                (
                    structural_relief_active
                    and near_confirm
                    and pair_support
                    and near_confirm_support
                    and forecast_support
                    and barrier_support
                )
                or plan_ready_support
            )
        )
        trace = {
            "contract_version": "entry_hard_guard_relief_v1",
            "blocked_reason": str(blocked_reason or ""),
            "symbol": str(canonical_symbol),
            "scene_id": str(probe_scene_id or ""),
            "observe_reason": str(observe_reason or ""),
            "applied": bool(applied),
            "criteria": {
                "active": bool(active),
                "structural_relief_active": bool(structural_relief_active),
                "near_confirm": bool(near_confirm),
                "pair_support": bool(pair_support),
                "near_confirm_support": bool(near_confirm_support),
                "forecast_support": bool(forecast_support),
                "barrier_support": bool(barrier_support),
                "plan_ready": bool(plan_ready),
                "plan_ready_support": bool(plan_ready_support),
            },
            "metrics": {
                "intended_action": str(intended_action),
                "pair_gap": float(pair_gap),
                "candidate_support": float(candidate_support),
                "action_confirm_score": float(action_confirm_score),
                "confirm_fake_gap": float(confirm_fake_gap),
                "wait_confirm_gap": float(wait_confirm_gap),
                "continue_fail_gap": float(continue_fail_gap),
                "same_side_barrier": float(same_side_barrier),
                "near_confirm_pair_gap": float(near_confirm_pair_gap),
                "structural_relief_candidate_support": float(structural_relief_candidate_support),
                "relaxed_action_confirm_floor": float(relaxed_action_confirm_floor),
                "relaxed_confirm_fake_floor": float(relaxed_confirm_fake_floor),
                "relaxed_wait_confirm_floor": float(relaxed_wait_confirm_floor),
                "relaxed_continue_fail_floor": float(relaxed_continue_fail_floor),
                "structural_relief_max_side_barrier": float(structural_relief_max_side_barrier),
            },
            "reason": (
                "nas_clean_confirm_low_vol_relief"
                if applied
                else "no_relief_applied"
            ),
        }
        return applied, trace

    def _check_hard_no_trade_guard(self, symbol: str, regime: dict) -> str:
        blocked_reason = self.threshold_engine.check_hard_no_trade_guard(symbol, regime)
        if str(blocked_reason or "") != "hard_guard_volatility_too_low":
            return blocked_reason
        relief_applied, relief_trace = self._resolve_nas_clean_confirm_low_vol_relief(
            symbol=symbol,
            blocked_reason=blocked_reason,
        )
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if isinstance(rows, dict):
            current_row = rows.get(symbol, {})
            if isinstance(current_row, dict):
                current_row["entry_hard_guard_relief_v1"] = dict(relief_trace or {})
                rows[symbol] = current_row
        if relief_applied:
            return ""
        return blocked_reason

    @staticmethod
    def _trimmed_mean(series: pd.Series, q: float) -> float:
        return EntryThresholdEngine.trimmed_mean(series, q)

    def _load_symbol_utility_stats(self, symbol: str) -> dict | None:
        return self.threshold_engine.load_symbol_utility_stats(symbol)

    @staticmethod
    def _base_symbol_cost(symbol: str) -> float:
        return EntryThresholdEngine.base_symbol_cost(symbol)

    def _estimate_entry_cost(self, symbol: str, regime: dict, spread_now: float) -> float:
        return self.threshold_engine.estimate_entry_cost(symbol, regime, spread_now)

    def _recent_spread_ratio(self, symbol: str) -> float:
        return self.threshold_engine.recent_spread_ratio(symbol)

    def _utility_min(self, symbol: str, same_dir_count: int) -> float:
        return self.threshold_engine.utility_min(symbol, same_dir_count)

    def _context_usd_adjustment(self, context_adj: int, topdown_ok: bool, gate_ok: bool) -> float:
        return self.threshold_engine.context_usd_adjustment(context_adj, topdown_ok, gate_ok)

    def _bb_penalty_usd(self, symbol: str, reason: str) -> float:
        return self.threshold_engine.bb_penalty_usd(symbol, reason)

    def _resolve_h1_box_state(self, df_all: dict, tick, scorer) -> str:
        return self._context_classifier.resolve_h1_box_state(df_all=df_all, tick=tick, scorer=scorer)

    def _resolve_bb_state(self, symbol: str, tick, df_all: dict, scorer) -> str:
        return self._context_classifier.resolve_bb_state(symbol=symbol, tick=tick, df_all=df_all, scorer=scorer)

    def _build_preflight_2h(
        self,
        *,
        symbol: str,
        tick,
        df_all: dict,
        result: dict,
        buy_s: float,
        sell_s: float,
    ) -> dict:
        return self._context_classifier.build_preflight_2h(
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            result=result,
            buy_s=buy_s,
            sell_s=sell_s,
        )

    def _core_action_decision(
        self,
        *,
        symbol: str,
        tick,
        df_all: dict,
        scorer,
        result: dict,
        buy_s: float,
        sell_s: float,
        has_buy: bool,
        has_sell: bool,
        entry_context_bundle: dict | None = None,
    ) -> dict:
        comps = (result or {}).get("components", {}) if isinstance(result, dict) else {}
        buy_h1 = int(pd.to_numeric(comps.get("h1_context_buy", 0), errors="coerce") or 0)
        sell_h1 = int(pd.to_numeric(comps.get("h1_context_sell", 0), errors="coerce") or 0)
        buy_m1 = int(pd.to_numeric(comps.get("m1_trigger_buy", 0), errors="coerce") or 0)
        sell_m1 = int(pd.to_numeric(comps.get("m1_trigger_sell", 0), errors="coerce") or 0)
        wait_score = float(pd.to_numeric(comps.get("wait_score", 0), errors="coerce") or 0.0)
        wait_conflict = float(pd.to_numeric(comps.get("wait_conflict", 0), errors="coerce") or 0.0)
        wait_noise = float(pd.to_numeric(comps.get("wait_noise", 0), errors="coerce") or 0.0)
        h1_gap = float(buy_h1 - sell_h1)
        m1_gap = float(buy_m1 - sell_m1)
        if not isinstance(entry_context_bundle, dict):
            entry_context_bundle = self._context_classifier.build_entry_context(
                symbol=symbol,
                tick=tick,
                df_all=df_all,
                scorer=scorer,
                result=result,
                buy_s=buy_s,
                sell_s=sell_s,
            )
        context = entry_context_bundle.get("context")
        context = self._attach_consumer_scope_contract(context)
        preflight = entry_context_bundle.get("preflight", {})
        preflight_allowed_action_raw = str(preflight.get("allowed_action", "BOTH") or "BOTH").upper()
        preflight_approach_mode = str(preflight.get("approach_mode", "MIX") or "MIX").upper()
        preflight_reason = str(preflight.get("reason", "") or "")
        preflight_regime = str(preflight.get("regime", "UNKNOWN") or "UNKNOWN").upper()
        preflight_liquidity = str(preflight.get("liquidity", "OK") or "OK").upper()
        preflight_hard_block = bool(getattr(Config, "ENTRY_PREFLIGHT_HARD_BLOCK", False))
        preflight_hard_block_shock_only = bool(getattr(Config, "ENTRY_PREFLIGHT_HARD_BLOCK_SHOCK_ONLY", True))
        preflight_hard_direction = bool(getattr(Config, "ENTRY_PREFLIGHT_ENFORCE_DIRECTION_HARD", False))
        preflight_direction_penalty = float(
            Config.get_symbol_float(
                symbol,
                getattr(Config, "ENTRY_PREFLIGHT_DIRECTION_PENALTY_BY_SYMBOL", {}),
                float(getattr(Config, "ENTRY_PREFLIGHT_DIRECTION_PENALTY", 10.0)),
            )
        )
        preflight_hard_block_effective = bool(
            preflight_hard_block and ((not preflight_hard_block_shock_only) or preflight_regime == "SHOCK")
        )

        box_state = str(getattr(context, "box_state", "UNKNOWN") or "UNKNOWN")
        bb_state = str(getattr(context, "bb_state", "UNKNOWN") or "UNKNOWN")
        preflight_allowed_action = str(
            getattr(context, "direction_policy", preflight_allowed_action_raw) or preflight_allowed_action_raw
        ).upper()
        preflight_extreme_counter_neutralized = bool(
            (preflight_allowed_action == "BUY_ONLY" and box_state in {"UPPER", "ABOVE"} and bb_state in {"UPPER_EDGE", "BREAKOUT"})
            or (preflight_allowed_action == "SELL_ONLY" and box_state in {"LOWER", "BELOW"} and bb_state in {"LOWER_EDGE", "BREAKDOWN"})
        )
        learn_buy_penalty = 0.0
        learn_sell_penalty = 0.0
        preflight_direction_penalty_applied = 0.0
        core_buy = 0.0
        core_sell = 0.0
        core_best = 0.0
        core_min = 0.0
        core_margin = 0.0
        tie_band = 0.0
        default_side_gate_v1: dict[str, object] = {}
        probe_plan_v1: dict[str, object] = {}

        def _normalize_rows(payload: object) -> list[dict]:
            if not isinstance(payload, list):
                return []
            rows: list[dict] = []
            for item in payload:
                if isinstance(item, dict):
                    rows.append(dict(item))
            return rows

        def _priority_rank(value: str) -> int:
            normalized = str(value or "").strip().lower()
            if normalized == "high":
                return 2
            if normalized == "medium":
                return 1
            return 0

        def _priority_label(rank: int) -> str:
            if rank >= 2:
                return "high"
            if rank == 1:
                return "medium"
            return "low"

        def _confidence_delta_from_hint(hint: dict) -> float:
            direction = str((hint or {}).get("direction", "") or "").strip().lower()
            band = str((hint or {}).get("delta_band", "") or "").strip().lower()
            if direction == "increase":
                return 0.05 if band == "small_up" else 0.0
            if direction == "decrease":
                return -0.05 if band == "small_down" else 0.0
            return 0.0

        def _build_consumer_check_state(payload: dict) -> dict:
            return build_consumer_check_state_v1(
                payload=payload,
                canonical_symbol=self._canonical_symbol(symbol),
                shadow_reason=shadow_reason,
                shadow_side=shadow_side,
                box_state=box_state,
                bb_state=bb_state,
                probe_plan_default=probe_plan_v1,
                default_side_gate_v1=default_side_gate_v1,
            )

        def _with_core_debug(payload: dict) -> dict:
            out = dict(payload or {})
            out["core_buy_raw"] = float(core_buy)
            out["core_sell_raw"] = float(core_sell)
            out["core_best_raw"] = float(core_best)
            out["core_min_raw"] = float(core_min)
            out["core_margin_raw"] = float(core_margin)
            out["core_tie_band_raw"] = float(tie_band)
            out["core_resolved_shadow_action"] = str(resolved_shadow_action)
            out["core_intended_direction"] = str(intended_direction)
            out["core_archetype_implied_action"] = str(archetype_implied_action)
            out["core_intended_action_source"] = str(intended_action_source)
            out["consumer_archetype_id"] = str(consumer_archetype_id)
            out["consumer_invalidation_id"] = str(consumer_invalidation_id)
            out["consumer_management_profile_id"] = str(consumer_management_profile_id)
            prs_log_contract = dict((getattr(context, "metadata", {}) or {}).get("prs_log_contract_v2", {}) or {})
            observe_confirm_output_contract = dict(
                (getattr(context, "metadata", {}) or {}).get("observe_confirm_output_contract_v2", {}) or {}
            )
            consumer_handoff = resolve_consumer_handoff_payload(context)
            observe_confirm_resolution = dict(consumer_handoff.get("observe_confirm_resolution", {}) or {})
            layer_mode_policy_resolution = dict(consumer_handoff.get("layer_mode_policy_resolution", {}) or {})
            layer_mode_policy = dict(consumer_handoff.get("layer_mode_policy", {}) or {})
            effective_action = str(out.get("action", "") or "").strip().upper()
            if effective_action not in {"BUY", "SELL"}:
                effective_action = "NONE"
            explicit_block_reason = str(out.get("consumer_block_reason", "") or "")
            block_reason = explicit_block_reason
            explicit_block_kind = str(out.get("consumer_block_kind", "") or "")
            explicit_block_source_layer = str(out.get("consumer_block_source_layer", "") or "")
            explicit_is_execution = out.get("consumer_block_is_execution")
            explicit_is_semantic = out.get("consumer_block_is_semantic_non_action")
            if (
                explicit_block_kind
                or explicit_block_source_layer
                or isinstance(explicit_is_execution, bool)
                or isinstance(explicit_is_semantic, bool)
            ):
                block_info = {
                    "reason": block_reason,
                    "kind": explicit_block_kind,
                    "source_layer": explicit_block_source_layer,
                    "is_execution_block": bool(explicit_is_execution),
                    "is_semantic_non_action": bool(explicit_is_semantic),
                    "canonical": False,
                }
            else:
                block_info = classify_entry_guard_reason(block_reason)
            out["observe_reason"] = str(out.get("observe_reason", "") or shadow_reason)
            out["blocked_by"] = str(out.get("blocked_by", "") or block_reason)
            out["consumer_input_observe_confirm_field"] = str(
                observe_confirm_resolution.get("field_name", "")
                or prs_log_contract.get(
                    "canonical_observe_confirm_field",
                    CONSUMER_INPUT_CONTRACT_V1["canonical_observe_confirm_field"],
                )
                or CONSUMER_INPUT_CONTRACT_V1["canonical_observe_confirm_field"]
            )
            out["consumer_input_contract_version"] = str(CONSUMER_INPUT_CONTRACT_V1["contract_version"])
            out["consumer_migration_contract_version"] = str(
                observe_confirm_resolution.get("contract_version", "") or CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
            )
            out["consumer_used_compatibility_fallback_v1"] = bool(observe_confirm_resolution.get("used_fallback_v1", False))
            out["consumer_policy_input_field"] = str(
                layer_mode_policy_resolution.get("field_name", "")
                or prs_log_contract.get("layer_mode_policy_output_field", "")
                or "layer_mode_policy_v1"
            )
            out["consumer_policy_contract_version"] = str(
                layer_mode_policy_resolution.get("contract_version", "") or CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
            )
            out["consumer_policy_identity_preserved"] = bool(layer_mode_policy.get("identity_preserved", False))
            out["consumer_setup_id"] = str(out.get("consumer_setup_id", out.get("setup_id", "")) or "")
            out["consumer_effective_action"] = str(effective_action)
            out["consumer_guard_result"] = str(
                resolve_consumer_guard_result(
                    effective_action=effective_action,
                    block_kind=str(block_info.get("kind", "") or ""),
                )
            )
            out["consumer_block_reason"] = str(block_reason)
            out["consumer_block_kind"] = str(block_info.get("kind", "") or "")
            out["consumer_block_source_layer"] = str(block_info.get("source_layer", "") or "")
            out["consumer_block_is_execution"] = bool(block_info.get("is_execution_block", False))
            out["consumer_block_is_semantic_non_action"] = bool(block_info.get("is_semantic_non_action", False))
            out["consumer_layer_mode_hard_block_active"] = bool(layer_mode_hard_block_active)
            out["consumer_layer_mode_suppressed"] = bool(layer_mode_suppression_active)
            out["consumer_layer_mode_priority_boost_active"] = bool(layer_mode_priority_boost_active)
            out["consumer_layer_mode_confidence_delta"] = float(layer_mode_confidence_delta)
            out["consumer_energy_action_readiness"] = float(energy_action_readiness)
            out["consumer_energy_priority_hint"] = str(effective_priority_hint)
            out["consumer_energy_wait_vs_enter_hint"] = str(
                energy_utility_hints.get("wait_vs_enter_hint", "") or ""
            )
            out["consumer_energy_gap_dominant_hint"] = str(
                energy_utility_hints.get("gap_dominant_hint", "") or ""
            )
            out["consumer_energy_forecast_branch_hint"] = str(
                energy_utility_hints.get("forecast_branch_hint", "") or ""
            )
            out["consumer_energy_soft_block_active"] = bool(energy_soft_block_active)
            out["consumer_energy_soft_block_reason"] = str(energy_soft_block_reason)
            out["consumer_energy_soft_block_strength"] = float(energy_soft_block_strength)
            out["consumer_energy_confidence_delta"] = float(energy_confidence_delta)
            out["consumer_energy_confidence_reason"] = str(energy_confidence_hint.get("reason", "") or "")
            out["consumer_energy_forecast_gap_usage_active"] = bool(
                energy_forecast_gap_usage.get("active", False)
            )
            out["consumer_energy_forecast_gap_live_gate_used"] = bool(energy_forecast_gap_live_gate_used)
            out["consumer_energy_transition_confirm_fake_gap"] = float(
                energy_forecast_gap_usage.get("transition_confirm_fake_gap", 0.0) or 0.0
            )
            out["consumer_energy_management_continue_fail_gap"] = float(
                energy_forecast_gap_usage.get("management_continue_fail_gap", 0.0) or 0.0
            )
            out["consumer_energy_management_recover_reentry_gap"] = float(
                energy_forecast_gap_usage.get("management_recover_reentry_gap", 0.0) or 0.0
            )
            out["consumer_energy_hold_exit_gap"] = float(
                energy_forecast_gap_usage.get("hold_exit_gap", 0.0) or 0.0
            )
            out["consumer_energy_same_side_flip_gap"] = float(
                energy_forecast_gap_usage.get("same_side_flip_gap", 0.0) or 0.0
            )
            out["consumer_energy_forecast_gap_usage_v1"] = dict(energy_forecast_gap_usage or {})
            out["consumer_forecast_assist_active"] = bool(forecast_assist_v1.get("active", False))
            out["consumer_forecast_assist_source"] = str(forecast_assist_v1.get("input_source", "") or "")
            out["consumer_forecast_mode"] = str(forecast_assist_v1.get("source_mode", "") or "")
            out["consumer_forecast_decision_hint"] = str(forecast_assist_v1.get("decision_hint", "") or "")
            out["consumer_forecast_confirm_fake_gap"] = float(forecast_assist_v1.get("confirm_fake_gap", 0.0) or 0.0)
            out["consumer_forecast_wait_confirm_gap"] = float(forecast_assist_v1.get("wait_confirm_gap", 0.0) or 0.0)
            out["consumer_forecast_continue_fail_gap"] = float(forecast_assist_v1.get("continue_fail_gap", 0.0) or 0.0)
            out["consumer_forecast_action_confirm_score"] = float(
                forecast_assist_v1.get("action_confirm_score", 0.0) or 0.0
            )
            out["consumer_forecast_priority_boost_active"] = bool(
                forecast_assist_v1.get("priority_boost_active", False)
            )
            out["consumer_forecast_confidence_delta"] = float(
                forecast_assist_v1.get("confidence_delta", 0.0) or 0.0
            )
            out["forecast_assist_v1"] = dict(forecast_assist_v1 or {})
            out["entry_default_side_gate_v1"] = dict(default_side_gate_v1 or {})
            out["entry_probe_plan_v1"] = dict(probe_plan_v1 or {})
            out["consumer_policy_live_gate_applied"] = bool(layer_mode_live_gate_applied)
            out["consumer_energy_live_gate_applied"] = bool(energy_live_gate_applied)
            out["consumer_energy_usage_trace_v1"] = dict(
                _build_recorded_energy_usage_trace(
                    effective_action=effective_action,
                    guard_result=str(out["consumer_guard_result"]),
                    block_reason=str(block_reason or ""),
                )
            )
            out["consumer_handoff_contract_version"] = str(
                observe_confirm_output_contract.get("contract_version", "") or ""
            )
            consumer_check_state_v1 = _build_consumer_check_state(out)
            out["consumer_check_state_v1"] = dict(consumer_check_state_v1)
            out["consumer_check_candidate"] = bool(consumer_check_state_v1.get("check_candidate", False))
            out["consumer_check_display_ready"] = bool(consumer_check_state_v1.get("check_display_ready", False))
            out["consumer_check_entry_ready"] = bool(consumer_check_state_v1.get("entry_ready", False))
            out["consumer_check_side"] = str(consumer_check_state_v1.get("check_side", "") or "")
            out["consumer_check_stage"] = str(consumer_check_state_v1.get("check_stage", "") or "")
            out["consumer_check_reason"] = str(consumer_check_state_v1.get("check_reason", "") or "")
            out["consumer_check_display_strength_level"] = int(
                consumer_check_state_v1.get("display_strength_level", 0) or 0
            )
            out["consumer_check_display_score"] = float(
                consumer_check_state_v1.get("display_score", 0.0) or 0.0
            )
            out["consumer_check_display_repeat_count"] = int(
                consumer_check_state_v1.get("display_repeat_count", 0) or 0
            )
            return out

        consumer_handoff = resolve_consumer_handoff_payload(context)
        shadow_observe = dict(consumer_handoff.get("observe_confirm", {}) or {})
        consumer_archetype_id = str(shadow_observe.get("archetype_id", "") or "")
        consumer_invalidation_id = str(shadow_observe.get("invalidation_id", "") or "")
        consumer_management_profile_id = str(shadow_observe.get("management_profile_id", "") or "")
        shadow_state = str(shadow_observe.get("archetype_id", shadow_observe.get("state", "")) or "").upper()
        shadow_stage = str(shadow_observe.get("state", "") or "").upper()
        shadow_action = str(shadow_observe.get("action", "") or "").upper()
        shadow_side = str(shadow_observe.get("side", "") or "").upper()
        shadow_reason = str(shadow_observe.get("reason", "") or "").strip() or "shadow_wait"
        shadow_confidence = float(pd.to_numeric(shadow_observe.get("confidence", 0.0), errors="coerce") or 0.0)
        shadow_metadata = (
            dict(shadow_observe.get("metadata", {}) or {})
            if isinstance(shadow_observe.get("metadata"), dict)
            else {}
        )
        shadow_blocked_reason = str(shadow_metadata.get("blocked_reason", "") or "").strip()
        shadow_blocked_guard = str(shadow_metadata.get("blocked_guard", "") or "").strip()
        if not shadow_blocked_guard:
            shadow_blocked_guard = _resolve_blocked_guard(
                blocked_reason=shadow_blocked_reason,
                explicit_guard=shadow_blocked_guard,
            )

        def _build_forecast_assist_trace() -> dict:
            context_metadata = dict(getattr(context, "metadata", {}) or {})
            effective_policy = (
                dict(context_metadata.get("forecast_effective_policy_v1", {}) or {})
                if isinstance(context_metadata.get("forecast_effective_policy_v1"), dict)
                else {}
            )
            transition_payload = (
                dict(effective_policy.get("transition_forecast_v1", {}) or {})
                if isinstance(effective_policy.get("transition_forecast_v1"), dict)
                else {}
            )
            management_payload = (
                dict(effective_policy.get("trade_management_forecast_v1", {}) or {})
                if isinstance(effective_policy.get("trade_management_forecast_v1"), dict)
                else {}
            )
            gap_payload = (
                dict(effective_policy.get("forecast_gap_metrics_v1", {}) or {})
                if isinstance(effective_policy.get("forecast_gap_metrics_v1"), dict)
                else {}
            )
            if not transition_payload:
                transition_payload = (
                    dict(context_metadata.get("transition_forecast_v1", {}) or {})
                    if isinstance(context_metadata.get("transition_forecast_v1"), dict)
                    else {}
                )
            if not management_payload:
                management_payload = (
                    dict(context_metadata.get("trade_management_forecast_v1", {}) or {})
                    if isinstance(context_metadata.get("trade_management_forecast_v1"), dict)
                    else {}
                )
            if not gap_payload:
                gap_payload = (
                    dict(context_metadata.get("forecast_gap_metrics_v1", {}) or {})
                    if isinstance(context_metadata.get("forecast_gap_metrics_v1"), dict)
                    else {}
                )

            observe_metadata = (
                dict(shadow_observe.get("metadata", {}) or {})
                if isinstance(shadow_observe.get("metadata"), dict)
                else {}
            )
            observe_forecast_assist = (
                dict(observe_metadata.get("forecast_assist_v1", {}) or {})
                if isinstance(observe_metadata.get("forecast_assist_v1"), dict)
                else {}
            )
            side = shadow_action if shadow_action in {"BUY", "SELL"} else str(observe_forecast_assist.get("target_side", "") or "").upper()
            buy_confirm = float(pd.to_numeric(transition_payload.get("p_buy_confirm", 0.0), errors="coerce") or 0.0)
            sell_confirm = float(pd.to_numeric(transition_payload.get("p_sell_confirm", 0.0), errors="coerce") or 0.0)
            if side not in {"BUY", "SELL"}:
                side = "BUY" if buy_confirm > sell_confirm else "SELL" if sell_confirm > buy_confirm else ""

            confirm_fake_gap = float(
                pd.to_numeric(
                    gap_payload.get("transition_confirm_fake_gap", observe_forecast_assist.get("confirm_fake_gap", 0.0)),
                    errors="coerce",
                )
                or 0.0
            )
            wait_confirm_gap = float(
                pd.to_numeric(
                    gap_payload.get("wait_confirm_gap", observe_forecast_assist.get("wait_confirm_gap", 0.0)),
                    errors="coerce",
                )
                or 0.0
            )
            continue_fail_gap = float(
                pd.to_numeric(
                    gap_payload.get("management_continue_fail_gap", observe_forecast_assist.get("continue_fail_gap", 0.0)),
                    errors="coerce",
                )
                or 0.0
            )
            action_confirm_score = (
                buy_confirm
                if side == "BUY"
                else sell_confirm
                if side == "SELL"
                else max(buy_confirm, sell_confirm)
            )
            continue_favor = float(pd.to_numeric(management_payload.get("p_continue_favor", 0.0), errors="coerce") or 0.0)
            fail_now = float(pd.to_numeric(management_payload.get("p_fail_now", 0.0), errors="coerce") or 0.0)
            effective_has_numeric_signal = any(
                abs(value) > 1e-9
                for value in (
                    buy_confirm,
                    sell_confirm,
                    confirm_fake_gap,
                    wait_confirm_gap,
                    continue_fail_gap,
                    continue_favor,
                    fail_now,
                )
            )
            active = bool(effective_has_numeric_signal or observe_forecast_assist)
            decision_hint = str(observe_forecast_assist.get("decision_hint", "") or "")
            if not decision_hint:
                if confirm_fake_gap >= 0.10 and wait_confirm_gap >= 0.05 and continue_fail_gap >= 0.03:
                    decision_hint = "CONFIRM_FAVOR"
                elif wait_confirm_gap < 0.02 or continue_fail_gap < 0.02 or fail_now > continue_favor:
                    decision_hint = "OBSERVE_FAVOR"
                elif active:
                    decision_hint = "BALANCED"
                else:
                    decision_hint = "NEUTRAL"

            priority_boost_active = bool(
                active
                and decision_hint == "CONFIRM_FAVOR"
                and confirm_fake_gap >= 0.10
                and wait_confirm_gap >= 0.05
                and continue_fail_gap >= 0.03
            )
            caution_active = bool(
                active
                and (
                    decision_hint == "OBSERVE_FAVOR"
                    or wait_confirm_gap < 0.02
                    or continue_fail_gap < 0.02
                )
            )
            confidence_delta = 0.0
            if priority_boost_active:
                confidence_delta += 0.05
            if caution_active:
                confidence_delta -= 0.05

            return {
                "active": active,
                "source_mode": (
                    str(effective_policy.get("current_effective_mode", "") or "assist")
                    if effective_has_numeric_signal
                    else "raw"
                ),
                "input_source": "forecast_effective_policy_v1" if effective_has_numeric_signal else "raw_forecast_context",
                "intended_side": side,
                "action_confirm_score": float(action_confirm_score),
                "continue_favor": float(continue_favor),
                "fail_now": float(fail_now),
                "confirm_fake_gap": float(confirm_fake_gap),
                "wait_confirm_gap": float(wait_confirm_gap),
                "continue_fail_gap": float(continue_fail_gap),
                "decision_hint": decision_hint,
                "priority_boost_active": priority_boost_active,
                "caution_active": caution_active,
                "confidence_delta": float(confidence_delta),
            }

        layer_mode_policy = dict(consumer_handoff.get("layer_mode_policy", {}) or {})
        layer_mode_rows = _normalize_rows(layer_mode_policy.get("layer_modes", []))
        layer_mode_by_layer = {
            str(row.get("layer", "") or ""): str(row.get("mode", "shadow") or "shadow")
            for row in layer_mode_rows
            if str(row.get("layer", "") or "")
        }
        layer_mode_effective_influences = _normalize_rows(layer_mode_policy.get("effective_influences", []))
        layer_mode_confidence_adjustments = _normalize_rows(layer_mode_policy.get("confidence_adjustments", []))
        layer_mode_hard_blocks = _normalize_rows(layer_mode_policy.get("hard_blocks", []))
        layer_mode_suppressed_reasons = _normalize_rows(layer_mode_policy.get("suppressed_reasons", []))
        layer_mode_priority_boost_active = any(
            "priority_boost" in list(row.get("active_effects", []) or [])
            and layer_mode_by_layer.get(str(row.get("layer", "") or ""), "shadow") != "shadow"
            for row in layer_mode_effective_influences
        )
        layer_mode_confidence_delta = round(
            sum(float(pd.to_numeric(row.get("delta", 0.0), errors="coerce") or 0.0) for row in layer_mode_confidence_adjustments),
            4,
        )
        layer_mode_hard_block_active = bool(layer_mode_hard_blocks)
        layer_mode_suppression_active = bool(layer_mode_suppressed_reasons)
        layer_mode_live_gate_applied = bool(
            layer_mode_hard_block_active
            or layer_mode_suppression_active
            or layer_mode_priority_boost_active
            or layer_mode_confidence_adjustments
        )
        layer_mode_primary_hard_block = dict(layer_mode_hard_blocks[0]) if layer_mode_hard_blocks else {}
        layer_mode_primary_suppression = dict(layer_mode_suppressed_reasons[0]) if layer_mode_suppressed_reasons else {}
        energy_helper = dict(consumer_handoff.get("energy_helper", {}) or {})
        energy_metadata = dict(energy_helper.get("metadata", {}) or {}) if isinstance(energy_helper.get("metadata"), dict) else {}
        energy_utility_hints = (
            dict(energy_metadata.get("utility_hints", {}) or {})
            if isinstance(energy_metadata.get("utility_hints"), dict)
            else {}
        )
        energy_forecast_gap_usage = (
            dict(energy_metadata.get("forecast_gap_usage_v1", {}) or {})
            if isinstance(energy_metadata.get("forecast_gap_usage_v1"), dict)
            else {}
        )
        energy_action_readiness = float(pd.to_numeric(energy_helper.get("action_readiness", 0.0), errors="coerce") or 0.0)
        energy_confidence_hint = (
            dict(energy_helper.get("confidence_adjustment_hint", {}) or {})
            if isinstance(energy_helper.get("confidence_adjustment_hint"), dict)
            else {}
        )
        energy_confidence_delta = _confidence_delta_from_hint(energy_confidence_hint)
        energy_soft_block_hint = (
            dict(energy_helper.get("soft_block_hint", {}) or {})
            if isinstance(energy_helper.get("soft_block_hint"), dict)
            else {}
        )
        energy_soft_block_active = bool(energy_soft_block_hint.get("active", False))
        energy_soft_block_reason = str(energy_soft_block_hint.get("reason", "") or "")
        energy_soft_block_strength = float(pd.to_numeric(energy_soft_block_hint.get("strength", 0.0), errors="coerce") or 0.0)
        energy_priority_hint = str(energy_utility_hints.get("priority_hint", "") or "").strip().lower()
        if energy_priority_hint not in {"low", "medium", "high"}:
            energy_priority_hint = "medium" if shadow_action in {"BUY", "SELL"} else "low"
        forecast_assist_v1 = _build_forecast_assist_trace()
        forecast_priority_boost_active = bool(forecast_assist_v1.get("priority_boost_active", False))
        forecast_confidence_delta = float(forecast_assist_v1.get("confidence_delta", 0.0) or 0.0)
        context_metadata = dict(getattr(context, "metadata", {}) or {})
        observe_metadata = (
            dict(shadow_observe.get("metadata", {}) or {})
            if isinstance(shadow_observe.get("metadata"), dict)
            else {}
        )
        belief_payload = (
            dict(context_metadata.get("belief_state_v1", {}) or {})
            if isinstance(context_metadata.get("belief_state_v1"), dict)
            else {}
        )
        barrier_payload = (
            dict(context_metadata.get("barrier_state_v1", {}) or {})
            if isinstance(context_metadata.get("barrier_state_v1"), dict)
            else {}
        )
        edge_pair_law = (
            dict(observe_metadata.get("edge_pair_law_v1", {}) or {})
            if isinstance(observe_metadata.get("edge_pair_law_v1"), dict)
            else {}
        )
        if not edge_pair_law:
            derived_context_label = ""
            if bb_state in {"LOWER_EDGE", "BREAKDOWN"} or box_state in {"LOWER", "BELOW"}:
                derived_context_label = "LOWER_EDGE"
            elif bb_state in {"UPPER_EDGE", "BREAKOUT"} or box_state in {"UPPER", "ABOVE"}:
                derived_context_label = "UPPER_EDGE"
            elif box_state == "MIDDLE" and bb_state in {"MID", "MIDDLE"}:
                derived_context_label = "MIDDLE"
            if derived_context_label:
                edge_pair_law = {
                    "contract_version": "edge_pair_law_v1",
                    "context_label": derived_context_label,
                    "candidate_buy": 0.0,
                    "candidate_sell": 0.0,
                    "pair_gap": 0.0,
                    "winner_side": "BALANCED",
                    "winner_archetype": "",
                    "winner_clear": False,
                    "active_branch_side": "",
                    "active_branch_archetype": "",
                    "opposing_branch_side": "",
                    "opposing_branch_archetype": "",
                }

        default_side_gate_v1 = resolve_entry_default_side_gate_v1(
            edge_pair_law_v1=edge_pair_law,
            consumer_archetype_id=str(consumer_archetype_id or ""),
            shadow_observe_archetype_id=str(shadow_observe.get("archetype_id", "") or ""),
            shadow_action=str(shadow_action or ""),
            shadow_side=str(shadow_side or ""),
            shadow_reason=str(shadow_reason or ""),
            shadow_stage=str(shadow_stage or ""),
            box_state=str(box_state or ""),
            bb_state=str(bb_state or ""),
            belief_payload=belief_payload,
            barrier_payload=barrier_payload,
            forecast_assist_v1=forecast_assist_v1,
            observe_metadata=observe_metadata,
        )

        probe_plan_v1 = resolve_entry_probe_plan_v1(
            symbol=str(symbol or ""),
            shadow_action=str(shadow_action or ""),
            shadow_side=str(shadow_side or ""),
            shadow_stage=str(shadow_stage or ""),
            box_state=str(box_state or ""),
            bb_state=str(bb_state or ""),
            observe_metadata=observe_metadata,
            default_side_gate_v1=default_side_gate_v1,
        )
        probe_ready_handoff_v1 = resolve_entry_probe_ready_handoff_v1(
            probe_plan_v1=probe_plan_v1,
            consumer_archetype_id=str(consumer_archetype_id or ""),
            consumer_invalidation_id=str(consumer_invalidation_id or ""),
            consumer_management_profile_id=str(consumer_management_profile_id or ""),
            default_side_gate_v1=default_side_gate_v1,
        )
        if bool(probe_ready_handoff_v1.get("probe_ready_handoff", False)):
            consumer_archetype_id = str(probe_ready_handoff_v1.get("consumer_archetype_id", "") or "")
            consumer_invalidation_id = str(probe_ready_handoff_v1.get("consumer_invalidation_id", "") or "")
            consumer_management_profile_id = str(
                probe_ready_handoff_v1.get("consumer_management_profile_id", "") or ""
            )
        energy_forecast_gap_live_gate_used = bool(
            energy_forecast_gap_usage.get("confidence_assist_active", False)
            or energy_forecast_gap_usage.get("soft_block_assist_active", False)
            or energy_forecast_gap_usage.get("priority_assist_active", False)
            or energy_forecast_gap_usage.get("wait_assist_active", False)
        )
        effective_priority_rank = _priority_rank(energy_priority_hint)
        if layer_mode_priority_boost_active:
            effective_priority_rank = min(2, effective_priority_rank + 1)
        if forecast_priority_boost_active:
            effective_priority_rank = min(2, effective_priority_rank + 1)
        effective_priority_hint = _priority_label(effective_priority_rank)
        adjusted_core_score = float(
            max(
                0.0,
                min(
                    1.0,
                    round(
                        max(0.55, shadow_confidence)
                        + layer_mode_confidence_delta
                        + energy_confidence_delta
                        + forecast_confidence_delta,
                        4,
                    ),
                ),
            )
        )
        energy_relief_policy_v1 = resolve_entry_energy_soft_block_policy_v1(
            symbol=str(symbol or ""),
            shadow_action=str(shadow_action or ""),
            shadow_reason=str(shadow_reason or ""),
            consumer_archetype_id=str(consumer_archetype_id or ""),
            box_state=str(box_state or ""),
            bb_state=str(bb_state or ""),
            default_side_gate_v1=default_side_gate_v1,
            probe_plan_v1=probe_plan_v1,
            observe_metadata=observe_metadata,
            forecast_assist_v1=forecast_assist_v1,
            energy_soft_block_active=bool(energy_soft_block_active),
            energy_soft_block_reason=str(energy_soft_block_reason or ""),
            energy_soft_block_strength=float(energy_soft_block_strength),
            energy_action_readiness=float(energy_action_readiness),
            effective_priority_rank=int(effective_priority_rank),
            adjusted_core_score=float(adjusted_core_score),
            probe_energy_ready_default=DEFAULT_ENTRY_PROBE_MIN_ENERGY_READY,
            probe_core_score_default=DEFAULT_ENTRY_PROBE_MIN_CORE_SCORE,
        )
        probe_energy_relief = bool(energy_relief_policy_v1.get("probe_energy_relief", False))
        confirm_energy_relief = bool(energy_relief_policy_v1.get("confirm_energy_relief", False))
        xau_second_support_energy_relief = bool(
            energy_relief_policy_v1.get("xau_second_support_energy_relief", False)
        )
        xau_upper_sell_probe_energy_relief = bool(
            energy_relief_policy_v1.get("xau_upper_sell_probe_energy_relief", False)
        )
        xau_upper_mixed_confirm_energy_relief = bool(
            energy_relief_policy_v1.get("xau_upper_mixed_confirm_energy_relief", False)
        )
        energy_soft_block_should_block = bool(
            energy_relief_policy_v1.get("energy_soft_block_should_block", False)
        )
        energy_live_gate_applied = bool(
            energy_soft_block_active
            or abs(energy_confidence_delta) > 0.0
            or abs(forecast_confidence_delta) > 0.0
            or energy_forecast_gap_live_gate_used
        )

        def _build_recorded_energy_usage_trace(
            *,
            effective_action: str,
            guard_result: str,
            block_reason: str,
        ) -> dict[str, object]:
            recorder = create_energy_usage_recorder(component="EntryService")
            relief_flags = [str(flag) for flag in list(energy_relief_policy_v1.get("relief_flags", []) or []) if str(flag)]
            if energy_soft_block_active:
                soft_block_branch = (
                    "soft_block_block"
                    if energy_soft_block_should_block
                    else "soft_block_relief"
                    if relief_flags
                    else "soft_block_active"
                )
                recorder = record_energy_usage(
                    recorder,
                    branch=soft_block_branch,
                    consumed_fields=["action_readiness", "soft_block_hint"],
                    reason=str(energy_soft_block_reason or block_reason or "energy_soft_block"),
                    details={
                        "soft_block_strength": float(energy_soft_block_strength),
                        "relief_flags": relief_flags,
                        "priority_override_relief_applied": bool(
                            energy_relief_policy_v1.get("priority_override_relief_applied", False)
                        ),
                        "effective_priority_hint": str(effective_priority_hint),
                    },
                )
            if str(shadow_action or "").upper() in {"BUY", "SELL"}:
                recorder = record_energy_usage(
                    recorder,
                    branch="priority_rank_applied",
                    consumed_fields=["metadata.utility_hints.priority_hint"],
                    reason=str(energy_priority_hint or effective_priority_hint or ""),
                    details={
                        "energy_priority_hint": str(energy_priority_hint),
                        "effective_priority_hint": str(effective_priority_hint),
                        "layer_mode_priority_boost_active": bool(layer_mode_priority_boost_active),
                        "forecast_priority_boost_active": bool(forecast_priority_boost_active),
                    },
                )
            if abs(energy_confidence_delta) > 0.0:
                recorder = record_energy_usage(
                    recorder,
                    branch="confidence_adjustment",
                    consumed_fields=["confidence_adjustment_hint"],
                    reason=str(
                        energy_confidence_hint.get("reason", "")
                        or energy_confidence_hint.get("direction", "")
                        or ""
                    ),
                    details={
                        "direction": str(energy_confidence_hint.get("direction", "") or ""),
                        "delta_band": str(energy_confidence_hint.get("delta_band", "") or ""),
                        "delta": float(energy_confidence_delta),
                    },
                )
            if energy_forecast_gap_live_gate_used:
                recorder = record_energy_usage(
                    recorder,
                    branch="forecast_gap_live_gate",
                    consumed_fields=[
                        "metadata.forecast_gap_usage_v1",
                        "metadata.utility_hints.gap_dominant_hint",
                        "metadata.utility_hints.forecast_branch_hint",
                    ],
                    reason=str(
                        energy_forecast_gap_usage.get("branch_hint", "")
                        or energy_utility_hints.get("forecast_branch_hint", "")
                        or energy_utility_hints.get("gap_dominant_hint", "")
                        or ""
                    ),
                    details={
                        "usage_mode": str(energy_forecast_gap_usage.get("usage_mode", "") or ""),
                        "gap_dominant_hint": str(energy_utility_hints.get("gap_dominant_hint", "") or ""),
                        "forecast_branch_hint": str(
                            energy_utility_hints.get("forecast_branch_hint", "") or ""
                        ),
                    },
                )
            usage_mode = (
                "live_branch_applied"
                if bool(energy_live_gate_applied)
                else "advisory_only"
                if bool(recorder.get("consumed_fields", []))
                else "not_consumed"
            )
            return finalize_energy_usage_recorder(
                recorder,
                usage_mode=usage_mode,
                live_gate_applied=bool(energy_live_gate_applied),
            )
        h1_strength = float(abs(h1_gap) / max(1.0, abs(float(buy_h1)) + abs(float(sell_h1))))
        m1_strength = float(abs(m1_gap) / max(1.0, abs(float(buy_m1)) + abs(float(sell_m1))))
        wait_penalty = 0.0
        probe_ready_action = (
            str(probe_plan_v1.get("intended_action", "") or "").upper()
            if bool(probe_plan_v1.get("ready_for_entry", False))
            else ""
        )
        probe_candidate_payload = (
            dict(observe_metadata.get("probe_candidate_v1", {}) or {})
            if isinstance(observe_metadata.get("probe_candidate_v1"), dict)
            else {}
        )
        probe_candidate_direction = str(probe_candidate_payload.get("probe_direction", "") or "").upper()
        intended_trace = _resolve_core_intended_trace(
            shadow_action=shadow_action,
            shadow_side=shadow_side,
            probe_ready_action=probe_ready_action,
            consumer_archetype_id=consumer_archetype_id,
            default_side_gate_v1=default_side_gate_v1,
            probe_candidate_direction=probe_candidate_direction,
            fallback_allowed_action=str(preflight_allowed_action),
        )
        archetype_implied_action = str(intended_trace.get("archetype_implied_action", "") or "")
        resolved_shadow_action = str(intended_trace.get("resolved_shadow_action", "") or "")
        intended_direction = str(intended_trace.get("intended_direction", "") or "")
        intended_action_source = str(intended_trace.get("intended_action_source", "") or "")
        intended_allowed_action = str(intended_trace.get("intended_allowed_action", "") or "")

        if preflight_allowed_action == "NONE" or preflight_approach_mode == "NO_TRADE":
            if preflight_hard_block_effective:
                return _with_core_debug({
                    "core_pass": 0,
                    "core_reason": "preflight_no_trade_hard",
                    "core_allowed_action": "NONE",
                    "action": None,
                    "observe_reason": str(shadow_reason),
                    "blocked_by": "preflight_no_trade",
                    "action_none_reason": "preflight_blocked",
                    "consumer_block_reason": "preflight_no_trade",
                    "consumer_block_kind": "preflight_block",
                    "consumer_block_source_layer": "preflight_direction_gate",
                    "consumer_block_is_execution": False,
                    "consumer_block_is_semantic_non_action": False,
                    "h1_bias_strength": float(h1_strength),
                    "m1_trigger_strength": float(m1_strength),
                    "box_state": str(box_state),
                    "bb_state": str(bb_state),
                    "core_score": 0.0,
                    "wait_score": float(wait_score),
                    "wait_conflict": float(wait_conflict),
                    "wait_noise": float(wait_noise),
                    "wait_penalty": float(wait_penalty),
                    "learn_buy_penalty": float(learn_buy_penalty),
                    "learn_sell_penalty": float(learn_sell_penalty),
                    "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                    "preflight_regime": str(preflight_regime),
                    "preflight_liquidity": str(preflight_liquidity),
                    "preflight_allowed_action": str(preflight_allowed_action),
                    "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                    "preflight_approach_mode": str(preflight_approach_mode),
                    "preflight_reason": str(preflight_reason),
                })

        if not shadow_observe:
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "core_observe_confirm_missing",
                "core_allowed_action": str(preflight_allowed_action),
                "action": None,
                "observe_reason": "",
                "blocked_by": "observe_confirm_missing",
                "action_none_reason": "observe_confirm_missing",
                "consumer_block_reason": "observe_confirm_missing",
                "consumer_block_kind": "consumer_input_block",
                "consumer_block_source_layer": "consumer_input",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": False,
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": 0.0,
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
            })

        if resolved_shadow_action not in {"BUY", "SELL"}:
            observe_wait_reason = (
                "probe_not_promoted"
                if bool(probe_plan_v1.get("active", False))
                or bool((shadow_metadata.get("probe_candidate_v1", {}) or {}).get("active", False))
                else "observe_state_wait"
            )
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "core_shadow_observe_wait",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": str(shadow_blocked_guard or ""),
                "action_none_reason": str(observe_wait_reason),
                "consumer_block_reason": str(shadow_blocked_reason),
                "consumer_block_kind": "semantic_non_action" if (shadow_blocked_reason or shadow_blocked_guard) else "",
                "consumer_block_source_layer": "observe_confirm" if (shadow_blocked_reason or shadow_blocked_guard) else "",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": bool(shadow_blocked_reason or shadow_blocked_guard),
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": 0.0,
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
            })

        if (
            preflight_allowed_action in {"BUY_ONLY", "SELL_ONLY"}
            and preflight_hard_direction
            and (not preflight_extreme_counter_neutralized)
            and intended_allowed_action != preflight_allowed_action
        ):
            preflight_direction_penalty_applied = float(preflight_direction_penalty)
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "preflight_direction_hard_block",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": "preflight_action_blocked",
                "action_none_reason": "preflight_blocked",
                "consumer_block_reason": "preflight_action_blocked",
                "consumer_block_kind": "preflight_block",
                "consumer_block_source_layer": "preflight_direction_gate",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": False,
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": 0.0,
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                    "preflight_approach_mode": str(preflight_approach_mode),
                    "preflight_reason": str(preflight_reason),
                })

        if bool(default_side_gate_v1.get("blocked", False)):
            block_reason = str(default_side_gate_v1.get("reason", "") or "edge_pair_default_side_block")
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "edge_pair_default_side_block",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": block_reason,
                "action_none_reason": "default_side_blocked",
                "consumer_block_reason": block_reason,
                "consumer_block_kind": "semantic_non_action",
                "consumer_block_source_layer": "entry_default_side_gate",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": True,
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": float(adjusted_core_score),
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
                "shadow_state": str(shadow_state),
                "confirm_energy_relief_applied": bool(confirm_energy_relief),
            })

        if bool(probe_plan_v1.get("active", False)) and not bool(probe_plan_v1.get("ready_for_entry", False)):
            probe_reason = str(probe_plan_v1.get("reason", "") or "probe_not_ready")
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "core_shadow_probe_wait",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": "probe_promotion_gate",
                "action_none_reason": "probe_not_promoted",
                "consumer_block_reason": probe_reason,
                "consumer_block_kind": "semantic_non_action",
                "consumer_block_source_layer": "entry_probe_plan",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": True,
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": float(adjusted_core_score),
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
                "shadow_state": str(shadow_state),
                "confirm_energy_relief_applied": bool(confirm_energy_relief),
            })

        if layer_mode_hard_block_active:
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "layer_mode_policy_hard_block",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": "layer_mode_policy_hard_block",
                "action_none_reason": "policy_hard_blocked",
                "consumer_block_reason": "layer_mode_policy_hard_block",
                "consumer_block_kind": "execution_block",
                "consumer_block_source_layer": "layer_mode_policy",
                "consumer_block_is_execution": True,
                "consumer_block_is_semantic_non_action": False,
                "consumer_policy_block_layer": str(layer_mode_primary_hard_block.get("layer", "") or ""),
                "consumer_policy_block_effect": str(layer_mode_primary_hard_block.get("effect", "hard_block") or "hard_block"),
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": float(adjusted_core_score),
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
                "shadow_state": str(shadow_state),
                "confirm_energy_relief_applied": bool(confirm_energy_relief),
                "xau_second_support_energy_relief_applied": bool(xau_second_support_energy_relief),
                "xau_upper_sell_probe_energy_relief_applied": bool(xau_upper_sell_probe_energy_relief),
                "xau_upper_mixed_confirm_energy_relief_applied": bool(xau_upper_mixed_confirm_energy_relief),
            })

        if layer_mode_suppression_active:
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "layer_mode_confirm_suppressed",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": "layer_mode_confirm_suppressed",
                "action_none_reason": "confirm_suppressed",
                "consumer_block_reason": "layer_mode_confirm_suppressed",
                "consumer_block_kind": "semantic_non_action",
                "consumer_block_source_layer": "layer_mode_policy",
                "consumer_block_is_execution": False,
                "consumer_block_is_semantic_non_action": True,
                "consumer_policy_block_layer": str(layer_mode_primary_suppression.get("layer", "") or ""),
                "consumer_policy_block_effect": str(
                    layer_mode_primary_suppression.get("effect", "confirm_to_observe_suppression")
                    or "confirm_to_observe_suppression"
                ),
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": float(adjusted_core_score),
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
                "shadow_state": str(shadow_state),
                "confirm_energy_relief_applied": bool(confirm_energy_relief),
                "xau_second_support_energy_relief_applied": bool(xau_second_support_energy_relief),
                "xau_upper_sell_probe_energy_relief_applied": bool(xau_upper_sell_probe_energy_relief),
                "xau_upper_mixed_confirm_energy_relief_applied": bool(xau_upper_mixed_confirm_energy_relief),
            })

        if energy_soft_block_should_block:
            return _with_core_debug({
                "core_pass": 0,
                "core_reason": "energy_soft_block",
                "core_allowed_action": str(intended_allowed_action),
                "action": None,
                "observe_reason": str(shadow_reason),
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_block_reason": "energy_soft_block",
                "consumer_block_kind": "execution_block",
                "consumer_block_source_layer": "energy_helper",
                "consumer_block_is_execution": True,
                "consumer_block_is_semantic_non_action": False,
                "h1_bias_strength": float(h1_strength),
                "m1_trigger_strength": float(m1_strength),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "core_score": float(adjusted_core_score),
                "wait_score": float(wait_score),
                "wait_conflict": float(wait_conflict),
                "wait_noise": float(wait_noise),
                "wait_penalty": float(wait_penalty),
                "learn_buy_penalty": float(learn_buy_penalty),
                "learn_sell_penalty": float(learn_sell_penalty),
                "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
                "preflight_regime": str(preflight_regime),
                "preflight_liquidity": str(preflight_liquidity),
                "preflight_allowed_action": str(preflight_allowed_action),
                "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
                "preflight_approach_mode": str(preflight_approach_mode),
                "preflight_reason": str(preflight_reason),
                "shadow_state": str(shadow_state),
            })

        action = str(resolved_shadow_action)
        if action == "BUY" and has_sell:
            action = None
            none_reason = "opposite_position_lock"
        elif action == "SELL" and has_buy:
            action = None
            none_reason = "opposite_position_lock"
        else:
            none_reason = ""
        return _with_core_debug({
            "core_pass": 1,
            "core_reason": "core_shadow_probe_action" if bool(probe_plan_v1.get("ready_for_entry", False)) else "core_shadow_confirm_action",
            "core_allowed_action": str(intended_allowed_action),
            "action": action,
            "observe_reason": str(shadow_reason),
            "blocked_by": "opposite_position_lock" if none_reason else "",
            "action_none_reason": str(none_reason or ""),
            "consumer_block_reason": "opposite_position_lock" if none_reason else "",
            "consumer_block_kind": "execution_block" if none_reason else "",
            "consumer_block_source_layer": "position_lock" if none_reason else "",
            "consumer_block_is_execution": bool(none_reason),
            "consumer_block_is_semantic_non_action": False,
            "h1_bias_strength": float(h1_strength),
            "m1_trigger_strength": float(m1_strength),
            "box_state": str(box_state),
            "bb_state": str(bb_state),
            "core_score": float(adjusted_core_score),
            "wait_score": float(wait_score),
            "wait_conflict": float(wait_conflict),
            "wait_noise": float(wait_noise),
            "wait_penalty": float(wait_penalty),
            "learn_buy_penalty": float(learn_buy_penalty),
            "learn_sell_penalty": float(learn_sell_penalty),
            "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
            "preflight_regime": str(preflight_regime),
            "preflight_liquidity": str(preflight_liquidity),
            "preflight_allowed_action": str(preflight_allowed_action),
            "preflight_allowed_action_raw": str(preflight_allowed_action_raw),
            "preflight_approach_mode": str(preflight_approach_mode),
            "preflight_reason": str(preflight_reason),
            "shadow_state": str(shadow_state),
            "confirm_energy_relief_applied": bool(confirm_energy_relief),
            "xau_second_support_energy_relief_applied": bool(xau_second_support_energy_relief),
            "xau_upper_sell_probe_energy_relief_applied": bool(xau_upper_sell_probe_energy_relief),
            "xau_upper_mixed_confirm_energy_relief_applied": bool(xau_upper_mixed_confirm_energy_relief),
        })


    def _append_entry_decision_log(self, row: dict) -> None:
        row = dict(row or {})
        append_started_at = time.perf_counter()
        append_stage_timings_ms: dict[str, float] = {}

        def _record_append_stage(stage_name: str, started_at: float) -> None:
            append_stage_timings_ms[str(stage_name)] = round(
                (time.perf_counter() - float(started_at)) * 1000.0,
                3,
            )

        stage_started_at = time.perf_counter()
        canonical_observe_confirm_field = str(row.get("prs_canonical_observe_confirm_field", "") or "").strip()
        compatibility_observe_confirm_field = str(
            row.get("prs_compatibility_observe_confirm_field", "") or ""
        ).strip()
        observe_confirm_v2_payload = row.get("observe_confirm_v2", {})
        observe_confirm_v1_payload = row.get("observe_confirm_v1", {})
        v2_missing = observe_confirm_v2_payload in ("", None, {}, "{}", "null", "None")
        v1_present = observe_confirm_v1_payload not in ("", None, {}, "{}", "null", "None")
        if canonical_observe_confirm_field in {"", "observe_confirm_v1"}:
            row["prs_canonical_observe_confirm_field"] = "observe_confirm_v2"
        if compatibility_observe_confirm_field == "":
            row["prs_compatibility_observe_confirm_field"] = "observe_confirm_v1"
        if v2_missing and v1_present and str(row.get("prs_contract_version", "") or "v2").strip().lower() == "v2":
            row["observe_confirm_v2"] = observe_confirm_v1_payload
        if row.get("observe_confirm_v1", "") in ("", None, {}, "{}", "null", "None") and row.get(
            "observe_confirm_v2", {}
        ) not in ("", None, {}, "{}", "null", "None"):
            row["observe_confirm_v1"] = row.get("observe_confirm_v2", {})
        if row.get("observe_reason", "") in ("", None):
            row["observe_reason"] = str(row.get("shadow_reason_v1", "") or "")
        if row.get("consumer_input_observe_confirm_field", "") in ("", None):
            row["consumer_input_observe_confirm_field"] = str(
                row.get("prs_canonical_observe_confirm_field", "")
                or CONSUMER_INPUT_CONTRACT_V1["canonical_observe_confirm_field"]
            )
        if row.get("consumer_input_contract_version", "") in ("", None):
            row["consumer_input_contract_version"] = str(CONSUMER_INPUT_CONTRACT_V1["contract_version"])
        if row.get("consumer_migration_contract_version", "") in ("", None):
            row["consumer_migration_contract_version"] = str(CONSUMER_MIGRATION_FREEZE_V1["contract_version"])
        if row.get("consumer_used_compatibility_fallback_v1", "") in ("", None):
            row["consumer_used_compatibility_fallback_v1"] = str(
                str(row.get("consumer_input_observe_confirm_field", "") or "").strip() == "observe_confirm_v1"
            )
        if row.get("consumer_setup_id", "") in ("", None):
            row["consumer_setup_id"] = str(row.get("setup_id", "") or "")
        effective_action = str(row.get("consumer_effective_action") or row.get("action", "") or "").strip().upper()
        if effective_action not in {"BUY", "SELL"}:
            effective_action = "NONE"
        row["consumer_effective_action"] = effective_action
        if row.get("consumer_guard_result", "") in ("", None):
            row["consumer_guard_result"] = resolve_consumer_guard_result(
                effective_action=effective_action,
                block_kind=str(row.get("consumer_block_kind", "") or ""),
            )
        if row.get("consumer_handoff_contract_version", "") in ("", None):
            output_contract = row.get("observe_confirm_output_contract_v2", {})
            if isinstance(output_contract, str) and output_contract.strip():
                try:
                    output_contract = json.loads(output_contract)
                except Exception:
                    output_contract = {}
            elif not isinstance(output_contract, dict):
                output_contract = {}
            row["consumer_handoff_contract_version"] = str(
                output_contract.get("contract_version", "") or "observe_confirm_output_contract_v2"
            )
        row.update(build_entry_authority_fields(row))
        _record_append_stage("row_prepare", stage_started_at)
        stage_started_at = time.perf_counter()
        use_lean_materialization = str(row.get("outcome", "") or "").strip().lower() in {"wait", "skipped"}
        if use_lean_materialization:
            context_payload, compact_result_payload = self._build_lean_entry_decision_artifacts(row)
            context_metadata = dict((context_payload.get("metadata", {}) or {}))
            decision_result_dict = {}
        else:
            decision_result = self._entry_decision_result_from_row(row)
            context_payload = decision_result.context.to_dict() if decision_result.context is not None else {}
            context_metadata = dict((context_payload.get("metadata", {}) or {}))
            compact_result_payload = {}
            decision_result_dict = decision_result.to_dict()
        energy_helper_payload = dict(context_metadata.get("energy_helper_v2", {}) or {})
        if energy_helper_payload:
            row["energy_helper_v2"] = json.dumps(energy_helper_payload, ensure_ascii=False, separators=(",", ":"))
        energy_logging_replay_contract = dict(
            context_metadata.get("energy_logging_replay_contract_v1", {}) or ENERGY_LOGGING_REPLAY_CONTRACT_V1
        )
        row["energy_logging_replay_contract_v1"] = json.dumps(
            energy_logging_replay_contract,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        row["energy_migration_dual_write_v1"] = json.dumps(
            dict(context_metadata.get("energy_migration_dual_write_v1", {}) or ENERGY_MIGRATION_DUAL_WRITE_V1),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        row["energy_migration_guard_v1"] = json.dumps(
            dict(
                context_metadata.get("energy_migration_guard_v1", {})
                or resolve_energy_migration_bridge_state(context_metadata)
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        row["energy_scope_contract_v1"] = json.dumps(
            dict(context_metadata.get("energy_scope_contract_v1", {}) or ENERGY_SCOPE_CONTRACT_V1),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        row["runtime_alignment_scope_contract_v1"] = json.dumps(
            dict(
                context_metadata.get("runtime_alignment_scope_contract_v1", {})
                or RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        energy_snapshot_payload = dict(context_metadata.get("energy_snapshot", {}) or {})
        if energy_snapshot_payload:
            row["energy_snapshot"] = json.dumps(energy_snapshot_payload, ensure_ascii=False, separators=(",", ":"))
        row["prs_canonical_energy_field"] = str(row.get("prs_canonical_energy_field", "") or "energy_helper_v2")
        row["energy_migration_contract_field"] = str(
            row.get("energy_migration_contract_field", "") or "energy_migration_dual_write_v1"
        )
        row["energy_scope_contract_field"] = str(row.get("energy_scope_contract_field", "") or "energy_scope_contract_v1")
        row["runtime_alignment_scope_contract_field"] = str(
            row.get("runtime_alignment_scope_contract_field", "") or "runtime_alignment_scope_contract_v1"
        )
        row["energy_compatibility_runtime_field"] = str(
            row.get("energy_compatibility_runtime_field", "") or "energy_snapshot"
        )
        row["energy_logging_replay_contract_field"] = str(
            row.get("energy_logging_replay_contract_field", "") or "energy_logging_replay_contract_v1"
        )
        row["consumer_migration_guard_v1"] = json.dumps(
            dict(
                context_metadata.get("consumer_migration_guard_v1", {})
                or build_consumer_migration_guard_metadata(context_metadata)
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        row["consumer_used_compatibility_fallback_v1"] = str(
            bool(
                (
                    context_metadata.get("consumer_migration_guard_v1", {})
                    or build_consumer_migration_guard_metadata(context_metadata)
                ).get("used_compatibility_fallback_v1", False)
            )
        )
        forecast_features_meta = (
            ((context_payload.get("metadata", {}) or {}).get("forecast_features_v1", {}) or {}).get("metadata", {})
            or {}
        )
        if row.get("signal_timeframe", "") in ("", None):
            row["signal_timeframe"] = str(forecast_features_meta.get("signal_timeframe", "") or "")
        if row.get("signal_bar_ts", "") in ("", None):
            signal_bar_ts = forecast_features_meta.get("signal_bar_ts", "")
            row["signal_bar_ts"] = ("" if signal_bar_ts in ("", None) else int(signal_bar_ts))
        compact_context_payload = context_payload
        compact_context_metadata = dict((compact_context_payload.get("metadata", {}) or {}))
        for trace_key in (
            "forecast_assist_v1",
            "entry_default_side_gate_v1",
            "entry_probe_plan_v1",
            "edge_pair_law_v1",
            "probe_candidate_v1",
            "entry_blocked_guard_v1",
            "probe_promotion_guard_v1",
            "consumer_check_state_v1",
            "consumer_open_guard_v1",
        ):
            trace_payload = row.get(trace_key, {})
            if isinstance(trace_payload, dict) and trace_payload and not isinstance(compact_context_metadata.get(trace_key), dict):
                compact_context_metadata[trace_key] = dict(trace_payload)
        if compact_context_metadata:
            compact_context_payload = dict(compact_context_payload)
            compact_context_payload["metadata"] = compact_context_metadata

        row["entry_decision_context_v1"] = compact_entry_decision_context(compact_context_payload)
        row["entry_decision_result_v1"] = (
            dict(compact_result_payload)
            if use_lean_materialization
            else compact_entry_decision_result(decision_result_dict)
        )
        probe_quick_source = dict(row)
        for trace_key in (
            "forecast_assist_v1",
            "entry_default_side_gate_v1",
            "entry_probe_plan_v1",
            "edge_pair_law_v1",
            "probe_candidate_v1",
            "consumer_check_state_v1",
        ):
            row[trace_key] = compact_trace_mapping(row.get(trace_key))
        row.update(build_probe_quick_trace_fields(probe_quick_source))
        _record_append_stage("decision_materialization", stage_started_at)

        stage_started_at = time.perf_counter()
        runtime_rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if isinstance(runtime_rows, dict):
            runtime_symbol = str((row or {}).get("symbol", "") or "")
            runtime_row = runtime_rows.get(runtime_symbol, {})
            if not isinstance(runtime_row, dict):
                runtime_row = {}
            for scalar_key in (
                "state25_candidate_active_candidate_id",
                "state25_candidate_policy_source",
                "state25_candidate_rollout_phase",
                "state25_candidate_binding_mode",
                "state25_candidate_threshold_log_only_enabled",
                "state25_candidate_threshold_symbol_scope_hit",
                "state25_candidate_threshold_stage_scope_hit",
                "state25_candidate_effective_entry_threshold",
                "state25_candidate_entry_threshold_delta",
                "state25_candidate_size_log_only_enabled",
                "state25_candidate_size_symbol_scope_hit",
                "state25_candidate_size_multiplier",
                "state25_candidate_size_multiplier_delta",
                "state25_candidate_size_min_multiplier",
                "state25_candidate_size_max_multiplier",
                "forecast_state25_overlay_mode",
                "forecast_state25_overlay_enabled",
                "forecast_state25_candidate_effective_entry_threshold",
                "forecast_state25_candidate_entry_threshold_delta",
                "forecast_state25_candidate_size_multiplier",
                "forecast_state25_candidate_size_multiplier_delta",
                "forecast_state25_candidate_wait_bias_action",
                "forecast_state25_candidate_management_bias",
                "forecast_state25_overlay_reason_summary",
                "belief_action_hint_mode",
                "belief_action_hint_enabled",
                "belief_candidate_recommended_family",
                "belief_candidate_supporting_label",
                "belief_action_hint_confidence",
                "belief_action_hint_reason_summary",
                "barrier_action_hint_mode",
                "barrier_action_hint_enabled",
                "barrier_candidate_recommended_family",
                "barrier_candidate_supporting_label",
                "barrier_action_hint_confidence",
                "barrier_action_hint_cost_hint",
                "barrier_action_hint_reason_summary",
                "semantic_shadow_available",
                "semantic_shadow_reason",
                "semantic_shadow_activation_state",
                "semantic_shadow_activation_reason",
                "semantic_live_rollout_mode",
                "semantic_live_alert",
                "semantic_live_fallback_reason",
                "semantic_live_symbol_allowed",
                "semantic_live_entry_stage_allowed",
                "semantic_live_threshold_before",
                "semantic_live_threshold_after",
                "semantic_live_threshold_adjustment",
                "semantic_live_threshold_applied",
                "semantic_live_threshold_state",
                "semantic_live_threshold_reason",
                "semantic_live_partial_weight",
                "semantic_live_partial_live_applied",
                "semantic_live_reason",
                "entry_authority_contract_version",
                "entry_authority_owner",
                "entry_candidate_action_source",
                "entry_candidate_action",
                "entry_candidate_rejected_by",
                "entry_authority_stage",
                "entry_authority_threshold_owner",
                "entry_authority_execution_owner",
                "entry_authority_reason_summary",
                "entry_candidate_bridge_contract_version",
                "entry_candidate_bridge_baseline_no_action",
                "entry_candidate_bridge_mode",
                "entry_candidate_bridge_active_conflict",
                "entry_candidate_bridge_conflict_selected",
                "entry_candidate_bridge_effective_baseline_action",
                "entry_candidate_bridge_conflict_kind",
                "entry_candidate_bridge_available",
                "entry_candidate_bridge_selected",
                "entry_candidate_bridge_source",
                "entry_candidate_bridge_action",
                "entry_candidate_bridge_reason",
                "entry_candidate_bridge_confidence",
                "entry_candidate_bridge_candidate_count",
                "entry_candidate_surface_family",
                "entry_candidate_surface_state",
                "active_action_conflict_detected",
                "active_action_conflict_guard_eligible",
                "active_action_conflict_guard_applied",
                "active_action_conflict_resolution_state",
                "active_action_conflict_kind",
                "active_action_conflict_baseline_action",
                "active_action_conflict_directional_action",
                "active_action_conflict_directional_state",
                "active_action_conflict_directional_bias",
                "active_action_conflict_directional_owner_family",
                "active_action_conflict_precedence_owner",
                "active_action_conflict_up_bias_score",
                "active_action_conflict_down_bias_score",
                "active_action_conflict_bias_gap",
                "active_action_conflict_warning_count",
                "active_action_conflict_breakout_detected",
                "active_action_conflict_breakout_direction",
                "active_action_conflict_breakout_target",
                "active_action_conflict_breakout_confidence",
                "active_action_conflict_breakout_failure_risk",
                "active_action_conflict_failure_code",
                "active_action_conflict_failure_label",
                "active_action_conflict_reason_summary",
                "semantic_candidate_action",
                "semantic_candidate_confidence",
                "semantic_candidate_reason",
                "shadow_candidate_action",
                "shadow_candidate_confidence",
                "shadow_candidate_reason",
                "state25_candidate_action",
                "state25_candidate_confidence",
                "state25_candidate_reason",
                "breakout_candidate_action",
                "breakout_candidate_confidence",
                "breakout_candidate_reason",
                "breakout_candidate_source",
                "breakout_candidate_action_target",
                "breakout_candidate_direction",
                "breakout_candidate_conflict_action",
                "breakout_candidate_conflict_confidence",
                "breakout_candidate_conflict_mode",
                "breakout_candidate_surface_family",
                "breakout_candidate_surface_state",
                "countertrend_continuation_enabled",
                "countertrend_continuation_state",
                "countertrend_continuation_action",
                "countertrend_continuation_confidence",
                "countertrend_continuation_reason_summary",
                "countertrend_continuation_warning_count",
                "countertrend_continuation_surface_family",
                "countertrend_continuation_surface_state",
                "countertrend_candidate_action",
                "countertrend_candidate_confidence",
                "countertrend_candidate_reason",
                "consumer_check_candidate",
                "consumer_check_display_ready",
                "consumer_check_entry_ready",
                "consumer_check_side",
                "consumer_check_stage",
                "consumer_check_reason",
                "consumer_check_display_strength_level",
                "consumer_check_display_score",
                "consumer_check_display_repeat_count",
                "execution_diff_original_action_side",
                "execution_diff_guarded_action_side",
                "execution_diff_promoted_action_side",
                "execution_diff_final_action_side",
                "execution_diff_changed",
                "execution_diff_guard_applied",
                "execution_diff_promotion_active",
                "execution_diff_reason_keys",
                "leg_id",
                "leg_direction",
                "leg_state",
                "leg_transition_reason",
                "checkpoint_id",
                "checkpoint_type",
                "checkpoint_index_in_leg",
                "checkpoint_transition_reason",
            ):
                if scalar_key in row:
                    runtime_row[scalar_key] = row.get(scalar_key)
            runtime_rows[runtime_symbol] = runtime_row
        _record_append_stage("runtime_row_sync", stage_started_at)

        stage_started_at = time.perf_counter()
        runtime_snapshot_mode = "full_runtime_snapshot_store"
        runtime_snapshot_store_calls = 0
        runtime_direct_sync_keys: list[str] = []
        runtime_symbol = str((row or {}).get("symbol", "") or "")
        if use_lean_materialization and isinstance(runtime_rows, dict) and runtime_symbol:
            runtime_row = runtime_rows.get(runtime_symbol, {})
            if not isinstance(runtime_row, dict):
                runtime_row = {}
            compact_context_snapshot = dict(row.get("entry_decision_context_v1", {}) or {})
            compact_result_snapshot = dict(row.get("entry_decision_result_v1", {}) or {})
            runtime_row["entry_decision_context_v1"] = compact_context_snapshot
            runtime_row["entry_decision_result_v1"] = compact_result_snapshot
            runtime_direct_sync_keys.extend(
                [
                    "entry_decision_context_v1",
                    "entry_decision_result_v1",
                ]
            )
            for trace_key in (
                "entry_probe_plan_v1",
                "edge_pair_law_v1",
                "probe_candidate_v1",
                "consumer_check_state_v1",
                "execution_action_diff_v1",
            ):
                trace_payload = row.get(trace_key, {})
                if isinstance(trace_payload, dict) and trace_payload:
                    runtime_row[str(trace_key)] = dict(trace_payload)
                    runtime_direct_sync_keys.append(str(trace_key))
            runtime_rows[runtime_symbol] = runtime_row
            runtime_snapshot_mode = "lean_no_action_direct_row"
        else:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=runtime_symbol,
                key="entry_decision_context_v1",
                payload=context_payload,
            )
            runtime_snapshot_store_calls += 1
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=runtime_symbol,
                key="entry_decision_result_v1",
                payload=(dict(compact_result_payload) if use_lean_materialization else decision_result_dict),
            )
            runtime_snapshot_store_calls += 1
            for trace_key in (
                "forecast_assist_v1",
                "entry_default_side_gate_v1",
                "entry_probe_plan_v1",
                "edge_pair_law_v1",
                "probe_candidate_v1",
                "consumer_check_state_v1",
                "execution_action_diff_v1",
            ):
                trace_payload = row.get(trace_key, {})
                if isinstance(trace_payload, dict) and trace_payload:
                    self._store_runtime_snapshot(
                        runtime=self.runtime,
                        symbol=runtime_symbol,
                        key=str(trace_key),
                        payload=trace_payload,
                    )
                    runtime_snapshot_store_calls += 1
        _record_append_stage("runtime_snapshot_store", stage_started_at)
        debug_writer = getattr(self.runtime, "_write_loop_debug", None)
        debug_loop_count = int((((getattr(self.runtime, "loop_debug_state", {}) or {}).get("loop_count", 0)) or 0))
        debug_detail = (
            f"{str((row or {}).get('outcome', '') or '')}|{str((row or {}).get('blocked_by', '') or '')}"
        )[:240]
        if callable(debug_writer):
            try:
                debug_writer(
                    loop_count=debug_loop_count,
                    stage="entry_append_log_begin",
                    symbol=str((row or {}).get("symbol", "") or ""),
                    detail=debug_detail,
                )
            except Exception:
                pass
        stage_started_at = time.perf_counter()
        try:
            appended_row = dict(self.decision_recorder.append_entry_decision_log(row) or {})
        except Exception as exc:
            if callable(debug_writer):
                try:
                    debug_writer(
                        loop_count=debug_loop_count,
                        stage="entry_append_log_error",
                        symbol=str((row or {}).get("symbol", "") or ""),
                        detail=str(exc)[:240],
                    )
                except Exception:
                    pass
            raise
        _record_append_stage("recorder_append", stage_started_at)
        try:
            existing_append_profile: dict = {}
            try:
                runtime_rows = getattr(self.runtime, "latest_signal_by_symbol", None)
                runtime_symbol = str((row or {}).get("symbol", "") or "")
                if isinstance(runtime_rows, dict) and runtime_symbol:
                    existing_append_profile = dict(
                        ((runtime_rows.get(runtime_symbol, {}) or {}).get("entry_append_log_profile_v1", {}) or {})
                    )
            except Exception:
                existing_append_profile = {}
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str((row or {}).get("symbol", "") or ""),
                key="entry_append_log_profile_v1",
                payload={
                    "contract_version": "entry_append_log_profile_v1",
                    "total_ms": round((time.perf_counter() - append_started_at) * 1000.0, 3),
                    "stage_timings_ms": dict(append_stage_timings_ms),
                    "recorder_stage_timings_ms": dict(appended_row.get("_append_stage_timings_ms", {}) or {}),
                    "file_write_stage_timings_ms": dict(
                        appended_row.get("_file_write_stage_timings_ms", {})
                        or existing_append_profile.get("file_write_stage_timings_ms", {})
                        or {}
                    ),
                    "detail_payload_stage_timings_ms": dict(
                        appended_row.get("_detail_payload_stage_timings_ms", {})
                        or existing_append_profile.get("detail_payload_stage_timings_ms", {})
                        or {}
                    ),
                    "recorder_total_ms": float(appended_row.get("_append_total_ms", 0.0) or 0.0),
                    "detail_record_mode": str((appended_row or {}).get("_detail_record_mode", "") or ""),
                    "decision_row_key": str((appended_row or {}).get("decision_row_key", "") or ""),
                    "runtime_snapshot_key": str((appended_row or {}).get("runtime_snapshot_key", "") or ""),
                    "runtime_snapshot_mode": str(runtime_snapshot_mode),
                    "runtime_snapshot_store_calls": int(runtime_snapshot_store_calls),
                    "runtime_direct_sync_keys": list(runtime_direct_sync_keys),
                },
            )
        except Exception:
            pass
        if callable(debug_writer):
            try:
                debug_writer(
                    loop_count=debug_loop_count,
                    stage="entry_append_log_done",
                    symbol=str((row or {}).get("symbol", "") or ""),
                    detail=debug_detail,
                )
            except Exception:
                pass
        return appended_row
    def try_open_entry(self, symbol, tick, df_all, result, my_positions, pos_count, scorer, buy_s, sell_s, entry_threshold):
        before_tickets: set[int] = set()
        after_tickets: set[int] = set()
        symbol_key = str(symbol or "").upper()
        entry_eval_started_at = time.perf_counter()
        stage_timings_ms: dict[str, float] = {}
        stage_started_at = time.perf_counter()
        try:
            before_tickets = {
                int(ticket)
                for ticket in set(getattr(self.trade_logger, "active_tickets", set()) or set())
                if int(ticket) > 0
            }
        except Exception:
            before_tickets = set()
        _record_entry_eval_stage_timing(stage_timings_ms, "active_ticket_snapshot_before", stage_started_at)

        stage_started_at = time.perf_counter()
        result_value = helper_try_open_entry(
            self,
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            result=result,
            my_positions=my_positions,
            pos_count=pos_count,
            scorer=scorer,
            buy_s=buy_s,
            sell_s=sell_s,
            entry_threshold=entry_threshold,
        )
        _record_entry_eval_stage_timing(stage_timings_ms, "helper_try_open_entry", stage_started_at)

        stage_started_at = time.perf_counter()
        try:
            after_tickets = {
                int(ticket)
                for ticket in set(getattr(self.trade_logger, "active_tickets", set()) or set())
                if int(ticket) > 0
            }
        except Exception:
            after_tickets = set()
        _record_entry_eval_stage_timing(stage_timings_ms, "active_ticket_snapshot_after", stage_started_at)

        stage_started_at = time.perf_counter()
        try:
            new_tickets = sorted(int(ticket) for ticket in (after_tickets - before_tickets) if int(ticket) > 0)
            latest_signal = (getattr(self.runtime, "latest_signal_by_symbol", {}) or {}).get(str(symbol), {}) or {}
            entry_context = dict((latest_signal.get("entry_decision_context_v1", {}) or {}).get("metadata", {}) or {})
            observe_confirm = resolve_consumer_observe_confirm_input(entry_context)
            management_profile_id = str(observe_confirm.get("management_profile_id", "") or "")
            invalidation_id = str(observe_confirm.get("invalidation_id", "") or "")
            if management_profile_id or invalidation_id:
                for ticket in new_tickets:
                    self.trade_logger.update_exit_policy_context(
                        int(ticket),
                        {
                            "management_profile_id": management_profile_id,
                            "invalidation_id": invalidation_id,
                        },
                    )
        except Exception:
            logger.exception("entry handoff backfill failed: symbol=%s", symbol)
            new_tickets = []
        _record_entry_eval_stage_timing(stage_timings_ms, "handoff_backfill", stage_started_at)

        elapsed_ms = (time.perf_counter() - entry_eval_started_at) * 1000.0
        snapshot_row = {}
        try:
            snapshot_row = dict(((getattr(self.runtime, "latest_signal_by_symbol", {}) or {}).get(str(symbol), {}) or {}))
        except Exception:
            snapshot_row = {}
        profile_payload = _build_entry_eval_profile(
            symbol=symbol_key,
            elapsed_ms=elapsed_ms,
            stage_timings_ms=stage_timings_ms,
            snapshot_row=snapshot_row,
            new_ticket_count=len(new_tickets),
            newest_ticket=int(new_tickets[-1]) if new_tickets else 0,
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol),
            key="entry_eval_profile_v1",
            payload=dict(profile_payload),
        )
        _write_entry_eval_profile(self.runtime, profile_payload)
        if bool(profile_payload.get("is_slow", False)):
            logger.warning(
                "slow entry eval: symbol=%s elapsed=%.1fms dominant_stage=%s(%.1fms)",
                symbol_key,
                float(profile_payload.get("elapsed_ms", 0.0) or 0.0),
                str(profile_payload.get("dominant_stage", "") or ""),
                float(profile_payload.get("dominant_stage_ms", 0.0) or 0.0),
            )
        return result_value
