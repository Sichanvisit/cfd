"""
MT5 ?? ?????? ??? ?? ???? CSV? ?????.
"""

import json
import hashlib
import logging
import os
import re
import time
from collections import deque

import pandas as pd
from backend.services.context_classifier import ContextClassifier
from backend.services.symbol_temperament import (
    canonical_symbol,
    resolve_probe_scene_direction,
    resolve_probe_scene_policy_family,
)
from backend.trading.chart_flow_baseline_compare import generate_and_write_chart_flow_baseline_compare_reports
from backend.trading.chart_flow_distribution import generate_and_write_chart_flow_distribution_report
from backend.trading.chart_flow_rollout_status import generate_and_write_chart_flow_rollout_status
from backend.trading.chart_flow_policy import build_common_expression_policy_v1
from backend.trading.chart_symbol_override_policy import build_symbol_override_policy_v1
from backend.trading.session_manager import SessionManager
from backend.trading.trend_manager import TrendManager

logger = logging.getLogger(__name__)


class Painter:
    _FLOW_HISTORY_MAXLEN = 64
    _FLOW_HISTORY_RETENTION_SEC = 12 * 60 * 60
    _FLOW_SIGNAL_COMPACT_WINDOW_SEC = 2 * 60
    _FLOW_SIGNATURE_REPEAT_MIN_SEC = 6 * 60
    _FLOW_NEUTRAL_BLOCK_GUARDS = {
        "outer_band_guard",
        "forecast_guard",
        "middle_sr_anchor_guard",
        "barrier_guard",
    }
    MTF_MA_TIMEFRAMES = ("15M", "30M", "1H", "4H", "1D")
    _TF_SECONDS = {
        "1M": 60,
        "15M": 15 * 60,
        "30M": 30 * 60,
        "1H": 60 * 60,
        "4H": 4 * 60 * 60,
        "1D": 24 * 60 * 60,
    }
    _TRENDLINE_EXTEND_BARS = {
        "1M": 30,
        "15M": 16,
        "1H": 8,
        "4H": 4,
    }
    _MA_EXTEND_BARS = {
        "15M": 12,
        "30M": 10,
        "1H": 8,
        "4H": 4,
        "1D": 2,
    }
    _MA_COLORS = {
        "15M": 8421504,
        "30M": 12632256,
        "1H": 16777215,
        "4H": 65535,
        "1D": 16776960,
    }
    _FLOW_POLICY_V1 = build_common_expression_policy_v1()
    _SYMBOL_OVERRIDE_POLICY_V1 = build_symbol_override_policy_v1()
    _FLOW_EVENT_COLORS = dict(_FLOW_POLICY_V1.get("visual", {}).get("base_color_by_event_kind", {}))
    _FLOW_SIGNAL_COMPACT_KINDS = set(_FLOW_POLICY_V1.get("visual", {}).get("compact_history_kinds", ()))

    def __init__(self):
        self.session_mgr = SessionManager()
        self.trend_mgr = TrendManager()
        self.buffer = []
        self._flow_history_by_symbol = {}
        self._flow_history_loaded_symbols = set()
        self._last_flow_signature_by_symbol = {}
        self._last_saved_draw_signature = {}
        default_save_dir = os.getenv(
            "PAINTER_SAVE_DIR",
            r"C:\Users\bhs33\AppData\Roaming\MetaQuotes\Terminal\Common\Files",
        )
        self.save_dir = default_save_dir
        self._save_enabled = True
        self._session_box_opacity = self._parse_box_opacity(os.getenv("SESSION_BOX_OPACITY", "0.20"))

        if not os.path.exists(self.save_dir):
            try:
                os.makedirs(self.save_dir)
            except OSError as exc:
                logger.warning("Failed to create painter save_dir %s: %s", self.save_dir, exc)

        if not self._is_writable_dir(self.save_dir):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            fallback_dir = os.path.join(project_root, "data", "mt5_draw")
            try:
                os.makedirs(fallback_dir, exist_ok=True)
            except OSError as exc:
                logger.warning("Failed to create painter fallback_dir %s: %s", fallback_dir, exc)
            if self._is_writable_dir(fallback_dir):
                logger.warning(
                    "Painter save_dir is not writable (%s). Falling back to %s",
                    self.save_dir,
                    fallback_dir,
                )
                self.save_dir = fallback_dir
            else:
                logger.warning(
                    "Painter save_dir and fallback_dir are not writable (%s, %s). Disable painter save.",
                    self.save_dir,
                    fallback_dir,
                )
                self._save_enabled = False

    @classmethod
    def _flow_policy(cls) -> dict:
        policy = getattr(cls, "_FLOW_POLICY_V1", {})
        return policy if isinstance(policy, dict) else {}

    @classmethod
    def _flow_policy_section(cls, section_name: str) -> dict:
        section = cls._flow_policy().get(str(section_name or ""))
        return section if isinstance(section, dict) else {}

    @classmethod
    def _symbol_override_policy(cls) -> dict:
        policy = getattr(cls, "_SYMBOL_OVERRIDE_POLICY_V1", {})
        return policy if isinstance(policy, dict) else {}

    @classmethod
    def _symbol_override_lookup(cls, symbol: str, *path: str):
        symbols = cls._symbol_override_policy().get("symbols", {})
        if not isinstance(symbols, dict):
            return None
        node = symbols.get(canonical_symbol(symbol), {})
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(str(key or ""))
        return node

    @classmethod
    def _symbol_override_dict(cls, symbol: str, *path: str) -> dict:
        payload = cls._symbol_override_lookup(symbol, *path)
        return dict(payload or {}) if isinstance(payload, dict) else {}

    @classmethod
    def _symbol_override_flag(cls, symbol: str, *path: str, default: bool) -> bool:
        value = cls._symbol_override_lookup(symbol, *path)
        if isinstance(value, dict):
            value = value.get("enabled", default)
        return bool(default if value is None else value)

    @staticmethod
    def _policy_lower_set(values, *, default=()) -> set[str]:
        items = values if isinstance(values, (list, tuple, set, frozenset)) else default
        return {str(item).strip().lower() for item in items if str(item).strip()}

    @staticmethod
    def _policy_lower_tuple(values, *, default=()) -> tuple[str, ...]:
        items = values if isinstance(values, (list, tuple, set, frozenset)) else default
        return tuple(str(item).strip().lower() for item in items if str(item).strip())

    @staticmethod
    def _policy_upper_map(values, *, default=None) -> dict[str, object]:
        mapping = values if isinstance(values, dict) else (default or {})
        out = {}
        for key, value in dict(mapping).items():
            key_n = str(key).strip().upper()
            if key_n:
                out[key_n] = value
        return out

    @staticmethod
    def _policy_float(value, *, default: float) -> float:
        try:
            parsed = float(pd.to_numeric(value, errors="coerce"))
        except Exception:
            parsed = float("nan")
        if pd.isna(parsed):
            return float(default)
        return float(parsed)

    @classmethod
    def _flow_strength_level_count(cls) -> int:
        strength = cls._flow_policy_section("strength")
        try:
            value = int(pd.to_numeric(strength.get("level_count"), errors="coerce"))
        except Exception:
            value = 10
        return max(2, int(value or 10))

    @classmethod
    def _flow_strength_score_input_paths(cls) -> tuple[str, ...]:
        strength = cls._flow_policy_section("strength")
        values = strength.get("score_input_paths")
        items = values if isinstance(values, (list, tuple, set, frozenset)) else ()
        return tuple(str(item).strip() for item in items if str(item).strip())

    @classmethod
    def _flow_strength_value(cls, field_name: str, *, default: float) -> float:
        strength = cls._flow_policy_section("strength")
        return cls._policy_float(strength.get(str(field_name or "")), default=default)

    @classmethod
    def _flow_strength_block_penalty_by_guard(cls) -> dict[str, float]:
        strength = cls._flow_policy_section("strength")
        mapping = strength.get("block_penalty_by_guard")
        src = dict(mapping or {}) if isinstance(mapping, dict) else {}
        out = {}
        defaults = {
            "energy_soft_block": 0.08,
            "*_soft_block": 0.08,
            "probe_promotion_gate": 0.10,
            "forecast_guard": 0.12,
            "barrier_guard": 0.12,
            "middle_sr_anchor_guard": 0.15,
            "outer_band_guard": 0.15,
            "conflict_default": 0.24,
        }
        for key, fallback in defaults.items():
            out[str(key).strip().lower()] = cls._policy_float(src.get(key, fallback), default=float(fallback))
        for key, value in src.items():
            key_n = str(key).strip().lower()
            if key_n:
                out[key_n] = cls._policy_float(value, default=out.get(key_n, 0.0))
        return out

    @classmethod
    def _flow_strength_bucket_edges(cls) -> tuple[float, ...]:
        strength = cls._flow_policy_section("strength")
        defaults = (0.05, 0.11, 0.18, 0.26, 0.35, 0.45, 0.58, 0.72, 0.86)
        values = strength.get("bucket_edges")
        items = values if isinstance(values, (list, tuple, set, frozenset)) else defaults
        edges = []
        for item in items:
            edge = cls._policy_float(item, default=float("nan"))
            if pd.notna(edge):
                edges.append(float(edge))
        expected = max(1, cls._flow_strength_level_count() - 1)
        if len(edges) != expected:
            return tuple(float(edge) for edge in defaults[:expected])
        return tuple(sorted(float(edge) for edge in edges))

    @classmethod
    def _flow_strength_visual_binding(cls) -> dict:
        strength = cls._flow_policy_section("strength")
        payload = strength.get("visual_binding")
        return dict(payload or {}) if isinstance(payload, dict) else {}

    @classmethod
    def _flow_strength_visual_apply_kinds(cls, field_name: str = "apply_event_kinds") -> set[str]:
        binding = cls._flow_strength_visual_binding()
        values = binding.get(str(field_name or "apply_event_kinds"))
        items = values if isinstance(values, (list, tuple, set, frozenset)) else {
            "BUY_WAIT",
            "SELL_WAIT",
            "BUY_BLOCKED",
            "SELL_BLOCKED",
            "BUY_PROBE",
            "SELL_PROBE",
            "BUY_READY",
            "SELL_READY",
        }
        return {str(item).strip().upper() for item in items if str(item).strip()}

    @classmethod
    def _flow_strength_visual_alpha_by_level(cls) -> dict[int, float]:
        binding = cls._flow_strength_visual_binding()
        mapping = binding.get("alpha_by_level")
        src = dict(mapping or {}) if isinstance(mapping, dict) else {}
        defaults = {
            1: 0.0,
            2: 0.0,
            3: 0.0,
            4: 0.0,
            5: 0.08,
            6: 0.14,
            7: 0.20,
            8: 0.26,
            9: 0.34,
            10: 0.40,
        }
        out = {}
        for key, fallback in defaults.items():
            out[int(key)] = cls._policy_float(src.get(key, src.get(str(key), fallback)), default=float(fallback))
        for key, value in src.items():
            try:
                key_i = int(pd.to_numeric(key, errors="coerce"))
            except Exception:
                continue
            out[key_i] = cls._policy_float(value, default=out.get(key_i, 0.0))
        return out

    @classmethod
    def _flow_strength_line_width_by_level(cls) -> dict[int, int]:
        binding = cls._flow_strength_visual_binding()
        mapping = binding.get("line_width_by_level")
        src = dict(mapping or {}) if isinstance(mapping, dict) else {}
        defaults = {
            1: 1,
            2: 1,
            3: 1,
            4: 2,
            5: 2,
            6: 2,
            7: 2,
            8: 3,
            9: 3,
            10: 3,
        }
        out = {}
        for key, fallback in defaults.items():
            try:
                value = int(pd.to_numeric(src.get(key, src.get(str(key), fallback)), errors="coerce"))
            except Exception:
                value = int(fallback)
            out[int(key)] = max(1, int(value or fallback))
        for key, value in src.items():
            try:
                key_i = int(pd.to_numeric(key, errors="coerce"))
                value_i = int(pd.to_numeric(value, errors="coerce"))
            except Exception:
                continue
            out[key_i] = max(1, int(value_i or 1))
        return out

    @classmethod
    def _flow_semantic_flag(cls, field_name: str, *, default: bool) -> bool:
        semantics = cls._flow_policy_section("semantics")
        value = semantics.get(str(field_name or ""), default)
        return bool(default if value is None else value)

    @classmethod
    def _flow_translation_neutral_block_guards(cls) -> set[str]:
        translation = cls._flow_policy_section("translation")
        return cls._policy_lower_set(
            translation.get("neutral_block_guards"),
            default=cls._FLOW_NEUTRAL_BLOCK_GUARDS,
        )

    @classmethod
    def _flow_translation_structural_wait_recovery_guards(cls) -> set[str]:
        translation = cls._flow_policy_section("translation")
        return cls._policy_lower_set(
            translation.get("structural_wait_recovery_guards"),
            default={"middle_sr_anchor_guard", "outer_band_guard"},
        )

    @classmethod
    def _flow_translation_structural_wait_recovery_reasons(cls) -> set[str]:
        translation = cls._flow_policy_section("translation")
        return cls._policy_lower_set(
            translation.get("structural_wait_recovery_reasons"),
            default={"outer_band_reversal_support_required_observe", "middle_sr_anchor_required_observe"},
        )

    @classmethod
    def _flow_translation_watch_reason_suffix_by_side(cls) -> dict[str, str]:
        translation = cls._flow_policy_section("translation")
        defaults = {"BUY": "buy_watch", "SELL": "sell_watch"}
        mapping = cls._policy_upper_map(translation.get("watch_reason_suffix_by_side"), default=defaults)
        return {
            "BUY": str(mapping.get("BUY", defaults["BUY"]) or defaults["BUY"]).strip().lower(),
            "SELL": str(mapping.get("SELL", defaults["SELL"]) or defaults["SELL"]).strip().lower(),
        }

    @classmethod
    def _flow_translation_conflict_reason_prefixes(cls) -> tuple[str, ...]:
        translation = cls._flow_policy_section("translation")
        return cls._policy_lower_tuple(
            translation.get("conflict_reason_prefixes"),
            default=("conflict_",),
        )

    @classmethod
    def _flow_translation_probe_promotion_gate_neutralization_enabled(cls) -> bool:
        translation = cls._flow_policy_section("translation")
        value = translation.get("probe_promotion_gate_neutralization_enabled", True)
        return bool(value)

    @classmethod
    def _flow_translation_edge_pair_directional_wait_fallback_enabled(cls) -> bool:
        translation = cls._flow_policy_section("translation")
        value = translation.get("edge_pair_directional_wait_fallback_enabled", True)
        return bool(value)

    @classmethod
    def _flow_translation_scene_side_fallback_enabled(cls) -> bool:
        translation = cls._flow_policy_section("translation")
        value = translation.get("scene_side_fallback_enabled", True)
        return bool(value)

    @classmethod
    def _flow_probe_side_thresholds(cls, field_name: str, *, default: dict[str, float]) -> dict[str, float]:
        probe = cls._flow_policy_section("probe")
        mapping = cls._policy_upper_map(probe.get(str(field_name or "")), default=default)
        out = {}
        for key, fallback in dict(default).items():
            out[str(key).upper()] = cls._policy_float(mapping.get(str(key).upper(), fallback), default=float(fallback))
        return out

    @classmethod
    def _flow_probe_value(cls, field_name: str, *, default: float) -> float:
        probe = cls._flow_policy_section("probe")
        return cls._policy_float(probe.get(str(field_name or "")), default=default)

    @classmethod
    def _flow_probe_blocked_quick_states(cls) -> set[str]:
        probe = cls._flow_policy_section("probe")
        values = probe.get("blocked_quick_states")
        items = values if isinstance(values, (list, tuple, set, frozenset)) else {"BLOCKED", "PROBE_CANDIDATE_BLOCKED"}
        return {str(item).strip().upper() for item in items if str(item).strip()}

    @classmethod
    def _flow_readiness_side_thresholds(cls, field_name: str, *, default: dict[str, float]) -> dict[str, float]:
        readiness = cls._flow_policy_section("readiness")
        mapping = cls._policy_upper_map(readiness.get(str(field_name or "")), default=default)
        out = {}
        for key, fallback in dict(default).items():
            out[str(key).upper()] = cls._policy_float(mapping.get(str(key).upper(), fallback), default=float(fallback))
        return out

    @classmethod
    def _flow_visual_base_color(cls, event_kind: str, *, default: int) -> int:
        visual = cls._flow_policy_section("visual")
        mapping = cls._policy_upper_map(visual.get("base_color_by_event_kind"), default=cls._FLOW_EVENT_COLORS)
        value = mapping.get(str(event_kind or "").upper(), default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    @classmethod
    def _flow_visual_wait_config(cls, event_kind: str) -> dict:
        visual = cls._flow_policy_section("visual")
        wait_cfg = visual.get("wait_brightness_by_event_kind")
        mapping = wait_cfg if isinstance(wait_cfg, dict) else {}
        event_kind_u = str(event_kind or "").upper()
        event_cfg = mapping.get(event_kind_u)
        if not isinstance(event_cfg, dict) and event_kind_u.endswith("_BLOCKED"):
            event_cfg = mapping.get(event_kind_u.replace("_BLOCKED", "_WAIT"))
        return dict(event_cfg or {}) if isinstance(event_cfg, dict) else {}

    @classmethod
    def _flow_visual_scale_value(cls, key: str, *, default: float) -> float:
        visual = cls._flow_policy_section("visual")
        return max(0.10, cls._policy_float(visual.get(str(key or ""), default), default=default))

    @classmethod
    def _flow_visual_repeat_thresholds(cls) -> tuple[float, float, float]:
        visual = cls._flow_policy_section("visual")
        mapping = visual.get("display_repeat_thresholds")
        src = dict(mapping or {}) if isinstance(mapping, dict) else {}
        single = cls._policy_float(src.get("single"), default=0.70)
        double = cls._policy_float(src.get("double"), default=0.80)
        triple = cls._policy_float(src.get("triple"), default=0.90)
        return (
            max(0.0, min(1.0, float(single))),
            max(0.0, min(1.0, float(double))),
            max(0.0, min(1.0, float(triple))),
        )

    @classmethod
    def _flow_visual_repeat_apply_kinds(cls) -> set[str]:
        visual = cls._flow_policy_section("visual")
        values = visual.get("display_repeat_apply_event_kinds")
        items = values if isinstance(values, (list, tuple, set, frozenset)) else {
            "BUY_WAIT",
            "SELL_WAIT",
            "BUY_BLOCKED",
            "SELL_BLOCKED",
            "BUY_PROBE",
            "SELL_PROBE",
            "BUY_READY",
            "SELL_READY",
            "BUY_WATCH",
            "SELL_WATCH",
        }
        return {str(item).strip().upper() for item in items if str(item).strip()}

    @classmethod
    def _flow_visual_compact_history_kinds(cls) -> set[str]:
        visual = cls._flow_policy_section("visual")
        values = visual.get("compact_history_kinds")
        items = values if isinstance(values, (list, tuple, set, frozenset)) else cls._FLOW_SIGNAL_COMPACT_KINDS
        return {str(item).strip().upper() for item in items if str(item).strip()}

    @classmethod
    def _flow_anchor_mode(cls, field_name: str, *, default: str) -> str:
        anchor = cls._flow_policy_section("anchor")
        value = str(anchor.get(str(field_name or ""), default) or default).strip().lower()
        return value or str(default or "").strip().lower()

    @classmethod
    def _flow_anchor_value(cls, field_name: str, *, default: float) -> float:
        anchor = cls._flow_policy_section("anchor")
        return cls._policy_float(anchor.get(str(field_name or "")), default=default)

    @staticmethod
    def _parse_box_opacity(raw) -> float:
        try:
            v = float(raw)
        except Exception:
            v = 0.20
        return max(0.0, min(1.0, v))

    def _soften_box_color(self, color: int) -> int:
        # MT5 color int is BGR-packed (0x00BBGGRR). Blend to black for pseudo-transparency.
        c = int(color) & 0xFFFFFF
        r = c & 0xFF
        g = (c >> 8) & 0xFF
        b = (c >> 16) & 0xFF
        k = float(self._session_box_opacity)
        r2 = int(round(r * k))
        g2 = int(round(g * k))
        b2 = int(round(b * k))
        return (b2 << 16) | (g2 << 8) | r2

    @staticmethod
    def _is_writable_dir(path: str) -> bool:
        p = str(path or "").strip()
        if not p:
            return False
        if not os.path.isdir(p):
            return False
        probe = os.path.join(p, f".write_test_{os.getpid()}.tmp")
        try:
            with open(probe, "w", encoding="ascii", newline="") as f:
                f.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    @staticmethod
    def _is_retryable_file_error(exc):
        if isinstance(exc, PermissionError):
            return True
        if isinstance(exc, OSError) and int(getattr(exc, "errno", 0) or 0) in (13, 32):
            return True
        return False

    def _write_atomic_with_retry(self, filepath, lines, max_attempts=8, sleep_sec=0.15):
        parent = os.path.dirname(filepath) or "."
        last_exc = None
        for attempt in range(max_attempts):
            tmp_path = os.path.join(parent, f"{os.path.basename(filepath)}.{os.getpid()}.tmp")
            try:
                with open(tmp_path, "w", encoding="ascii", newline="") as f:
                    f.writelines(lines)
                os.replace(tmp_path, filepath)
                return
            except OSError as exc:
                last_exc = exc
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
                if (attempt + 1) >= max_attempts or not self._is_retryable_file_error(exc):
                    break
                time.sleep(sleep_sec)
        if last_exc is not None:
            # Some environments block temp-file creation but still allow direct overwrite.
            with open(filepath, "w", encoding="ascii", newline="") as f:
                f.writelines(lines)
            return

    def clear(self):
        self.buffer = []

    def _flow_history_filepath(self, symbol: str) -> str:
        safe_symbol = self._safe_symbol_for_filename(symbol)
        if not safe_symbol:
            return ""
        return os.path.join(self.save_dir, f"{safe_symbol}_flow_history.json")

    @staticmethod
    def _distribution_report_filepath() -> str:
        raw_path = str(os.getenv("CHART_FLOW_DISTRIBUTION_PATH", "") or "").strip()
        if raw_path:
            return os.path.abspath(raw_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(project_root, "data", "analysis", "chart_flow_distribution_latest.json")

    @staticmethod
    def _rollout_status_filepath() -> str:
        raw_path = str(os.getenv("CHART_FLOW_ROLLOUT_STATUS_PATH", "") or "").strip()
        if raw_path:
            return os.path.abspath(raw_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(project_root, "data", "analysis", "chart_flow_rollout_status_latest.json")

    def _load_flow_history_if_needed(self, symbol: str) -> None:
        safe_symbol = str(symbol or "").upper()
        if not safe_symbol or safe_symbol in self._flow_history_loaded_symbols:
            return
        self._flow_history_loaded_symbols.add(safe_symbol)
        filepath = self._flow_history_filepath(safe_symbol)
        if not filepath or not os.path.exists(filepath):
            return
        try:
            with open(filepath, "r", encoding="ascii") as f:
                payload = json.load(f)
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Failed to load painter flow history for %s (%s): %s", safe_symbol, filepath, exc)
            return

        if isinstance(payload, dict):
            raw_events = payload.get("events", [])
            persisted_signature = str(payload.get("last_signature", "") or "")
        elif isinstance(payload, list):
            raw_events = payload
            persisted_signature = ""
        else:
            raw_events = []
            persisted_signature = ""

        history = deque(maxlen=self._FLOW_HISTORY_MAXLEN)
        min_ts = int(time.time()) - int(self._FLOW_HISTORY_RETENTION_SEC)
        if isinstance(raw_events, list):
            for event in raw_events[-self._FLOW_HISTORY_MAXLEN :]:
                if not isinstance(event, dict):
                    continue
                normalized_event = self._normalize_loaded_flow_event(event)
                if normalized_event is None:
                    continue
                if int(normalized_event.get("ts", 0) or 0) < min_ts:
                    continue
                history.append(normalized_event)
        if history:
            self._flow_history_by_symbol[safe_symbol] = history
        if persisted_signature:
            self._last_flow_signature_by_symbol.setdefault(safe_symbol, persisted_signature)

    @classmethod
    def _normalize_loaded_flow_event(cls, event: dict) -> dict | None:
        try:
            event_ts = int(event.get("ts", 0) or 0)
            event_kind = str(event.get("event_kind", "") or "").upper()
            side = str(event.get("side", "") or "").upper()
            blocked_by = str(event.get("blocked_by", "") or "")
            if event_kind in {"BUY_READY", "SELL_READY"}:
                blocked_guard = blocked_by.strip().lower()
                if blocked_guard == "energy_soft_block" or blocked_guard.endswith("_soft_block"):
                    if event_kind == "BUY_READY":
                        event_kind = "BUY_BLOCKED"
                        side = side or "BUY"
                    else:
                        event_kind = "SELL_BLOCKED"
                        side = side or "SELL"
            return {
                "ts": event_ts,
                "price": float(event.get("price", 0.0) or 0.0),
                "event_kind": event_kind,
                "side": side,
                "reason": str(event.get("reason", "") or ""),
                "blocked_by": blocked_by,
                "action_none_reason": str(event.get("action_none_reason", "") or ""),
                "priority": int(event.get("priority", cls._flow_event_priority(event_kind)) or 0),
                "score": float(event.get("score", 0.0) or 0.0),
                "level": int(event.get("level", event.get("strength_level", 0)) or 0),
                "box_state": str(event.get("box_state", "") or ""),
                "bb_state": str(event.get("bb_state", "") or ""),
                "probe_scene_id": str(event.get("probe_scene_id", "") or ""),
                "my_position_count": float(event.get("my_position_count", 0.0) or 0.0),
            }
        except (TypeError, ValueError):
            return None

    def _persist_flow_history(self, symbol: str) -> None:
        safe_symbol = str(symbol or "").upper()
        if not safe_symbol or not self._save_enabled:
            return
        filepath = self._flow_history_filepath(safe_symbol)
        if not filepath:
            return
        min_ts = int(time.time()) - int(self._FLOW_HISTORY_RETENTION_SEC)
        history = [
            event
            for event in list(self._flow_history_by_symbol.get(safe_symbol, []))
            if int(event.get("ts", 0) or 0) >= min_ts
        ]
        self._flow_history_by_symbol[safe_symbol] = deque(history, maxlen=self._FLOW_HISTORY_MAXLEN)
        payload = {
            "version": 1,
            "symbol": safe_symbol,
            "updated_at": int(time.time()),
            "last_signature": str(self._last_flow_signature_by_symbol.get(safe_symbol, "") or ""),
            "events": history,
        }
        try:
            lines = [json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"]
            self._write_atomic_with_retry(filepath, lines)
        except OSError as exc:
            logger.warning("Failed to persist painter flow history for %s (%s): %s", safe_symbol, filepath, exc)
            return
        try:
            distribution_report, distribution_path = generate_and_write_chart_flow_distribution_report(
                save_dir=self.save_dir,
                output_path=self._distribution_report_filepath(),
                window_mode="candles",
                window_value=self._FLOW_HISTORY_MAXLEN,
                baseline_mode="override_on",
                now_ts=int(time.time()),
            )
        except Exception as exc:
            logger.warning("Failed to persist chart flow distribution report after %s: %s", safe_symbol, exc)
            return
        baseline_compare = {}
        try:
            baseline_compare = generate_and_write_chart_flow_baseline_compare_reports(
                now_ts=int(time.time()),
                window_mode="candles",
                window_value=self._FLOW_HISTORY_MAXLEN,
            )
        except Exception as exc:
            logger.warning("Failed to persist chart flow baseline compare report after %s: %s", safe_symbol, exc)
        try:
            generate_and_write_chart_flow_rollout_status(
                distribution_report=distribution_report,
                distribution_path=distribution_path,
                comparison_override_distribution_report=baseline_compare.get("compare_override_report"),
                comparison_override_distribution_path=baseline_compare.get("compare_override_distribution_path"),
                baseline_distribution_report=baseline_compare.get("baseline_report"),
                baseline_distribution_path=baseline_compare.get("baseline_distribution_path"),
                save_dir=self.save_dir,
                output_path=self._rollout_status_filepath(),
            )
        except Exception as exc:
            logger.warning("Failed to persist chart flow rollout status after %s: %s", safe_symbol, exc)

    @staticmethod
    def _coerce_dict(payload):
        return dict(payload or {}) if isinstance(payload, dict) else {}

    @classmethod
    def _event_price(cls, df_1m, tick, *, side: str = "", event_kind: str = "", reason: str = "") -> float:
        if df_1m is None or df_1m.empty:
            bid = getattr(tick, "bid", 0.0) if tick is not None else 0.0
            ask = getattr(tick, "ask", 0.0) if tick is not None else 0.0
            return float(bid or ask or 0.0)
        latest = df_1m.iloc[-1]
        open_ = float(pd.to_numeric(latest.get("open"), errors="coerce") or 0.0)
        close = float(pd.to_numeric(latest.get("close"), errors="coerce") or 0.0)
        high = float(pd.to_numeric(latest.get("high"), errors="coerce") or close)
        low = float(pd.to_numeric(latest.get("low"), errors="coerce") or close)
        span = max(high - low, abs(close - open_), 1e-9)
        body_low = min(open_, close)
        side_n = str(side or "").upper()
        kind_n = str(event_kind or "").upper()
        reason_n = str(reason or "").strip().lower()
        if kind_n in {"ENTER_BUY", "BUY_READY", "BUY_WAIT", "BUY_BLOCKED"} or side_n == "BUY":
            if "upper_reclaim" in reason_n or "upper_support_hold" in reason_n:
                reclaim_mode = cls._flow_anchor_mode("buy_upper_reclaim_mode", default="body_low")
                if reclaim_mode == "close":
                    return float(close)
                if reclaim_mode == "low":
                    return float(low)
                return float(body_low)
            if "middle_" in reason_n or "mid_" in reason_n:
                ratio = cls._flow_anchor_value("buy_middle_ratio", default=0.48)
                return float(min(body_low, low + (span * ratio)))
            if kind_n in {"BUY_PROBE", "BUY_WATCH"}:
                ratio = cls._flow_anchor_value("buy_probe_ratio", default=0.30)
                return float(min(body_low, low + (span * ratio)))
            ratio = cls._flow_anchor_value("buy_default_ratio", default=0.36)
            return float(min(body_low, low + (span * ratio)))
        if kind_n in {"ENTER_SELL", "SELL_READY", "SELL_WAIT", "SELL_BLOCKED", "EXIT_NOW", "REVERSE_READY"} or side_n == "SELL":
            sell_mode = cls._flow_anchor_mode("sell_mode", default="high")
            if sell_mode == "close":
                return float(close)
            if sell_mode == "body_low":
                return float(body_low)
            return float(high)
        neutral_mode = cls._flow_anchor_mode("neutral_mode", default="close")
        if neutral_mode == "high":
            return float(high)
        if neutral_mode == "body_low":
            return float(body_low)
        return float(close)

    @staticmethod
    def _event_span(df_1m) -> float:
        if df_1m is None or df_1m.empty:
            return 10.0
        frame = df_1m.tail(24).copy()
        highs = pd.to_numeric(frame.get("high"), errors="coerce")
        lows = pd.to_numeric(frame.get("low"), errors="coerce")
        ranges = (highs - lows).dropna()
        if ranges.empty:
            close = pd.to_numeric(frame.get("close"), errors="coerce").dropna()
            if close.empty:
                return 10.0
            return max(float(close.iloc[-1]) * 0.0015, 10.0)
        return max(float(ranges.mean()) * 0.35, 5.0)

    @classmethod
    def _flow_event_signature(cls, row: dict) -> str:
        shadow_owner = str(row.get("flow_shadow_chart_event_ownership_v1", "") or "").upper().strip()
        if shadow_owner == "SHADOW_DISPLAY":
            return "|".join(
                [
                    "shadow_display",
                    str(bool(row.get("flow_shadow_chart_event_emit_v1"))),
                    str(row.get("flow_shadow_chart_event_emit_state_v1", "") or ""),
                    str(row.get("flow_shadow_chart_event_emit_key_v1", "") or ""),
                    str(row.get("flow_shadow_chart_event_final_kind_v1", "") or ""),
                    str(row.get("flow_shadow_chart_event_emit_reason_v1", "") or ""),
                ]
            )
        observe = cls._coerce_dict(row.get("observe_confirm_v2"))
        observe_meta = cls._coerce_dict(observe.get("metadata"))
        edge_pair = cls._coerce_dict(row.get("edge_pair_law_v1") or observe_meta.get("edge_pair_law_v1"))
        entry = cls._coerce_dict(row.get("entry_decision_result_v1"))
        exit_wait = cls._coerce_dict(row.get("exit_wait_state_v1"))
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        continuation_overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        observe_action = str(observe.get("action") or row.get("observe_action") or "")
        observe_side = str(observe.get("side") or row.get("observe_side") or "")
        observe_reason = str(observe.get("reason") or row.get("observe_reason") or "")
        return "|".join(
            [
                observe_action,
                observe_side,
                observe_reason,
                str(row.get("probe_scene_id", "")),
                str(row.get("quick_trace_state", "")),
                str(row.get("blocked_by", "")),
                str(row.get("action_none_reason", "")),
                str(edge_pair.get("context_label", "")),
                str(edge_pair.get("winner_side", "")),
                str(entry.get("outcome", "")),
                str(entry.get("action", "")),
                str(exit_wait.get("state", "")),
                str(exit_wait.get("decision", "")),
                str(consumer_check.get("check_display_ready", "")),
                str(consumer_check.get("check_side", "")),
                str(consumer_check.get("check_stage", "")),
                str(consumer_check.get("chart_event_kind_hint", "")),
                str(consumer_check.get("chart_display_mode", "")),
                str(row.get("chart_event_kind_hint", "")),
                str(row.get("chart_event_reason_hint", "")),
                str(continuation_overlay.get("overlay_enabled", "")),
                str(continuation_overlay.get("overlay_direction", "")),
                str(continuation_overlay.get("overlay_event_kind_hint", "")),
                str(continuation_overlay.get("overlay_candidate_key", "")),
                str(continuation_overlay.get("overlay_selection_state", "")),
            ]
        )

    @classmethod
    def _resolve_explicit_chart_event_hint(cls, row: dict) -> tuple[str, str, str] | None:
        shadow_owner = str(row.get("flow_shadow_chart_event_ownership_v1", "") or "").upper().strip()
        if shadow_owner == "SHADOW_DISPLAY" and not bool(row.get("flow_shadow_chart_event_emit_v1")):
            return None
        event_kind = str(
            row.get("flow_shadow_chart_event_final_kind_v1")
            or row.get("chart_event_kind_hint")
            or ""
        ).upper().strip()
        if event_kind not in {
            "BUY_WATCH",
            "SELL_WATCH",
            "BUY_WAIT",
            "SELL_WAIT",
            "BUY_BLOCKED",
            "SELL_BLOCKED",
            "BUY_PROBE",
            "SELL_PROBE",
            "BUY_READY",
            "SELL_READY",
            "WAIT",
        }:
            return None
        if event_kind.startswith("BUY_"):
            side = "BUY"
        elif event_kind.startswith("SELL_"):
            side = "SELL"
        else:
            side = ""
        reason = str(
            row.get("flow_shadow_chart_event_emit_reason_v1")
            or row.get("chart_event_reason_hint")
            or row.get("flow_shadow_chart_event_override_reason_v1")
            or ""
        ).strip()
        return (event_kind, side, reason or event_kind.lower())

    @classmethod
    def _resolve_consumer_check_event_kind(cls, row: dict) -> tuple[str, str, str] | None:
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        if not consumer_check:
            return None
        check_display_ready = bool(consumer_check.get("check_display_ready", False))
        check_candidate = bool(consumer_check.get("check_candidate", False))
        if not check_display_ready and not check_candidate:
            return None
        reason = str(
            consumer_check.get("check_reason", "")
            or consumer_check.get("semantic_origin_reason", "")
            or consumer_check.get("entry_block_reason", "")
            or ""
        )
        side = str(consumer_check.get("check_side", "") or "").upper()
        event_kind_hint = str(consumer_check.get("chart_event_kind_hint", "") or "").upper().strip()
        stage = str(consumer_check.get("check_stage", "") or "").upper()
        if event_kind_hint == "WAIT":
            return ("WAIT", "", reason or "wait")
        if side not in {"BUY", "SELL"}:
            return None
        if bool(consumer_check.get("entry_ready", False)) or stage == "READY":
            return (f"{side}_READY", side, reason)
        if stage == "PROBE":
            return (f"{side}_PROBE", side, reason or f"{side.lower()}_probe")
        if stage == "BLOCKED":
            return (f"{side}_BLOCKED", side, reason or f"{side.lower()}_blocked")
        if stage == "OBSERVE":
            return (f"{side}_WAIT", side, reason or f"{side.lower()}_wait")
        return None

    @classmethod
    def _consumer_check_hidden_flow_suppressed(cls, row: dict) -> bool:
        shadow_owner = str(row.get("flow_shadow_chart_event_ownership_v1", "") or "").strip().upper()
        if shadow_owner == "SHADOW_DISPLAY":
            if bool(row.get("flow_shadow_chart_event_emit_v1")):
                return False
            consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
            if (
                bool(consumer_check.get("check_display_ready", False) or consumer_check.get("check_candidate", False))
                and str(consumer_check.get("check_side", "") or "").strip().upper() in {"BUY", "SELL"}
                and str(consumer_check.get("check_stage", "") or "").strip().upper()
                in {"OBSERVE", "BLOCKED", "PROBE", "READY"}
            ):
                return False
            return True
        explicit_chart_hint = str(row.get("chart_event_kind_hint", "") or "").strip().upper()
        overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        overlay_enabled = bool(overlay.get("overlay_enabled", False))
        overlay_event_kind_hint = str(overlay.get("overlay_event_kind_hint", "") or "").strip().upper()
        if explicit_chart_hint in {"BUY_WATCH", "SELL_WATCH", "BUY_WAIT", "SELL_WAIT", "BUY_PROBE", "SELL_PROBE"}:
            return False
        if overlay_enabled and overlay_event_kind_hint in {"BUY_WATCH", "SELL_WATCH", "BUY_WAIT", "SELL_WAIT", "BUY_PROBE", "SELL_PROBE"}:
            return False
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        if not consumer_check:
            return False
        if bool(consumer_check.get("check_display_ready", False)):
            return False
        if (
            bool(consumer_check.get("check_candidate", False))
            and str(consumer_check.get("check_side", "") or "").strip().upper() in {"BUY", "SELL"}
            and str(consumer_check.get("check_stage", "") or "").strip().upper() in {"OBSERVE", "BLOCKED", "PROBE", "READY"}
        ):
            return False
        modifier_primary_reason = str(consumer_check.get("modifier_primary_reason", "") or "").strip().lower()
        if modifier_primary_reason in {
            "balanced_conflict_wait_hide_without_probe",
            "btc_sell_middle_anchor_wait_hide_without_probe",
            "btc_lower_rebound_forecast_wait_hide_without_probe",
            "nas_upper_break_fail_wait_hide_without_probe",
            "nas_upper_reject_wait_hide_without_probe",
            "nas_sell_middle_anchor_wait_hide_without_probe",
            "nas_upper_reclaim_wait_hide_without_probe",
            "xau_upper_reclaim_wait_hide_without_probe",
            "sell_outer_band_wait_hide_without_probe",
            "structural_wait_hide_without_probe",
        }:
            return True
        check_reason = str(consumer_check.get("check_reason", "") or "").strip().lower()
        check_side = str(consumer_check.get("check_side", "") or "").strip().upper()
        check_stage = str(consumer_check.get("check_stage", "") or "").strip().upper()
        action_none_reason = str(row.get("action_none_reason", "") or "").strip().lower()
        probe_scene_id = str(row.get("probe_scene_id", "") or "").strip()
        return bool(
            check_reason.startswith("conflict_box_")
            and action_none_reason == "observe_state_wait"
            and not probe_scene_id
            and not check_side
            and check_stage in {"", "NONE"}
        )

    @classmethod
    def _resolve_directional_continuation_overlay_event_kind(
        cls,
        row: dict,
    ) -> tuple[str, str, str] | None:
        overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        if not overlay or not bool(overlay.get("overlay_enabled", False)):
            return None
        event_kind = str(overlay.get("overlay_event_kind_hint", "") or "").upper().strip()
        side = str(overlay.get("overlay_side", "") or "").upper().strip()
        if event_kind not in {"BUY_WATCH", "SELL_WATCH"} or side not in {"BUY", "SELL"}:
            return None
        reason = str(
            overlay.get("overlay_reason", "")
            or overlay.get("overlay_summary_ko", "")
            or overlay.get("overlay_reason_ko", "")
            or ""
        ).strip()
        return (event_kind, side, reason or event_kind.lower())

    @classmethod
    def _entry_terminal_event_conflicts_with_canonical_row(
        cls,
        row: dict,
        *,
        entry_action: str,
        continuation_overlay_event: tuple[str, str, str] | None = None,
        consumer_check_event: tuple[str, str, str] | None = None,
    ) -> bool:
        entry_action_u = str(entry_action or "").upper().strip()
        if entry_action_u not in {"BUY", "SELL"}:
            return False
        execution_diff = cls._coerce_dict(row.get("execution_action_diff_v1"))
        execution_final = str(
            row.get("execution_diff_final_action_side")
            or execution_diff.get("final_action_side")
            or ""
        ).upper().strip()
        if execution_final in {"BUY", "SELL", "SKIP"} and execution_final != entry_action_u:
            return True
        for event in (continuation_overlay_event, consumer_check_event):
            if not isinstance(event, tuple) or len(event) < 2:
                continue
            event_kind = str(event[0] or "").upper().strip()
            event_side = str(event[1] or "").upper().strip()
            if (
                event_side in {"BUY", "SELL"}
                and event_side != entry_action_u
                and event_kind.endswith(("_WATCH", "_WAIT", "_PROBE", "_READY"))
            ):
                return True
        return False

    @classmethod
    def _resolve_flow_event_kind(cls, symbol: str, row: dict) -> tuple[str, str, str]:
        observe = cls._coerce_dict(row.get("observe_confirm_v2"))
        observe_meta = cls._coerce_dict(observe.get("metadata"))
        edge_pair = cls._coerce_dict(row.get("edge_pair_law_v1") or observe_meta.get("edge_pair_law_v1"))
        entry = cls._coerce_dict(row.get("entry_decision_result_v1"))
        exit_wait = cls._coerce_dict(row.get("exit_wait_state_v1"))
        directional_wait_enabled = cls._flow_semantic_flag("directional_wait_enabled", default=True)
        soft_block_downgrades_ready = cls._flow_semantic_flag("soft_block_downgrades_ready", default=True)
        structural_wait_recovery_enabled = cls._flow_semantic_flag("structural_wait_recovery_enabled", default=True)
        flat_exit_suppression_enabled = cls._flow_semantic_flag("flat_exit_suppression_enabled", default=True)
        terminal_exit_requires_position = cls._flow_semantic_flag("terminal_exit_requires_position", default=True)
        neutral_block_guards = cls._flow_translation_neutral_block_guards()
        watch_reason_suffix_by_side = cls._flow_translation_watch_reason_suffix_by_side()
        conflict_reason_prefixes = cls._flow_translation_conflict_reason_prefixes()
        probe_promotion_gate_neutralization_enabled = cls._flow_translation_probe_promotion_gate_neutralization_enabled()
        edge_pair_directional_wait_fallback_enabled = cls._flow_translation_edge_pair_directional_wait_fallback_enabled()
        try:
            my_position_count = float(pd.to_numeric(row.get("my_position_count"), errors="coerce"))
        except Exception:
            my_position_count = float("nan")
        if (
            flat_exit_suppression_enabled
            and terminal_exit_requires_position
            and pd.notna(my_position_count)
            and my_position_count <= 0
        ):
            exit_wait = {}
        quick_trace_state = str(row.get("quick_trace_state", "") or "").upper()
        probe_candidate_active = bool(row.get("probe_candidate_active"))
        probe_plan_active = bool(row.get("probe_plan_active"))
        probe_plan_ready = bool(row.get("probe_plan_ready"))
        blocked_by = str(row.get("blocked_by", "") or "").strip().lower()
        action_none_reason = str(row.get("action_none_reason", "") or "").strip().lower()
        continuation_overlay_event = cls._resolve_directional_continuation_overlay_event_kind(row)
        consumer_check_event = cls._resolve_consumer_check_event_kind(row)

        entry_outcome = str(entry.get("outcome", "") or "").lower()
        entry_action = str(entry.get("action", "") or "").upper()
        if (
            entry_outcome == "entered"
            and entry_action in {"BUY", "SELL"}
            and not cls._entry_terminal_event_conflicts_with_canonical_row(
                row,
                entry_action=entry_action,
                continuation_overlay_event=continuation_overlay_event,
                consumer_check_event=consumer_check_event,
            )
        ):
            return (f"ENTER_{entry_action}", entry_action, str(entry.get("core_reason", "") or entry.get("reason", "") or ""))

        exit_state = str(exit_wait.get("state", "") or "").upper()
        if exit_state in {"REVERSE_READY", "REVERSAL_CONFIRM"}:
            decision = str(exit_wait.get("decision", "") or "").upper()
            side = "SELL" if "SELL" in decision else ("BUY" if "BUY" in decision else "")
            return ("REVERSE_READY", side, str(exit_wait.get("reason", "") or ""))
        if exit_state in {"CUT_IMMEDIATE", "EXIT_NOW", "EXIT_READY"}:
            return ("EXIT_NOW", "", str(exit_wait.get("reason", "") or ""))
        if exit_state in {"HOLD", "GREEN_CLOSE", "ACTIVE"}:
            return ("HOLD", "", str(exit_wait.get("reason", "") or ""))

        explicit_chart_event = cls._resolve_explicit_chart_event_hint(row)
        if explicit_chart_event is not None:
            return explicit_chart_event

        if continuation_overlay_event is not None:
            if consumer_check_event is None:
                return continuation_overlay_event
            consumer_kind = str(consumer_check_event[0] or "").upper()
            if consumer_kind in {"WAIT", "BUY_WAIT", "SELL_WAIT", "BUY_BLOCKED", "SELL_BLOCKED", "BUY_PROBE", "SELL_PROBE"}:
                return continuation_overlay_event
        if consumer_check_event is not None:
            return consumer_check_event

        action = str(observe.get("action", "") or row.get("observe_action", "") or "").upper()
        side = str(observe.get("side", "") or row.get("observe_side", "") or "").upper()
        reason = str(observe.get("reason", "") or row.get("observe_reason", "") or "")
        edge_context = str(edge_pair.get("context_label", "") or "").upper()
        edge_winner = str(edge_pair.get("winner_side", "") or "").upper()
        box_state = str(row.get("box_state", "") or "").upper()
        bb_state = str(row.get("bb_state", "") or "").upper()
        probe_scene_id = str(row.get("probe_scene_id", "") or "").strip()
        reason_n = str(reason or "").strip().lower()
        watch_suffixes = tuple(value for value in watch_reason_suffix_by_side.values() if value)
        if not action and (
            "_probe_observe" in reason
            or quick_trace_state.startswith("PROBE")
            or any(reason_n.endswith(suffix) for suffix in watch_suffixes)
        ):
            action = "WAIT"
        if soft_block_downgrades_ready and action in {"BUY", "SELL"} and (
            action_none_reason == "execution_soft_blocked"
            or blocked_by in {"energy_soft_block"}
            or blocked_by.endswith("_soft_block")
        ):
            action = "WAIT"
        blocked_wait_guards = set(neutral_block_guards)
        if probe_promotion_gate_neutralization_enabled:
            blocked_wait_guards.add("probe_promotion_gate")
        if (
            action in {"BUY", "SELL"}
            and blocked_by in blocked_wait_guards
            and (
                quick_trace_state.startswith("PROBE")
                or action_none_reason in {"probe_not_promoted", "observe_state_wait"}
                or "_probe_observe" in reason
            )
        ):
            action = "WAIT"
        side = cls._resolve_flow_observe_side(
            side=side,
            reason=reason,
            box_state=box_state,
            bb_state=bb_state,
            probe_scene_id=probe_scene_id,
        )
        try:
            probe_candidate_support = float(pd.to_numeric(row.get("probe_candidate_support"), errors="coerce"))
        except Exception:
            probe_candidate_support = float("nan")
        try:
            probe_pair_gap = float(pd.to_numeric(row.get("probe_pair_gap"), errors="coerce"))
        except Exception:
            probe_pair_gap = float("nan")
        is_probe_visual = bool(
            action == "WAIT"
            and not probe_plan_ready
            and (
                "_probe_observe" in reason
                or quick_trace_state.startswith("PROBE")
                or probe_candidate_active
                or probe_plan_active
            )
        )
        probe_visual_allowed = cls._resolve_probe_visual_allowed(
            symbol=symbol,
            reason=reason,
            probe_scene_id=probe_scene_id,
            probe_candidate_active=probe_candidate_active,
            probe_plan_active=probe_plan_active,
            probe_candidate_support=probe_candidate_support,
            probe_pair_gap=probe_pair_gap,
            box_state=box_state,
            bb_state=bb_state,
            is_probe_visual=is_probe_visual,
            observe_meta=observe_meta,
            blocked_by=blocked_by,
            quick_trace_state=quick_trace_state,
        )
        if (
            action == "WAIT"
            and blocked_by
            and blocked_by in neutral_block_guards
            and not probe_visual_allowed
        ):
            if structural_wait_recovery_enabled:
                blocked_structural_wait = cls._resolve_blocked_structural_wait(
                    side=side,
                    reason=reason,
                    blocked_by=blocked_by,
                    edge_context=edge_context,
                    edge_winner=edge_winner,
                    is_probe_visual=is_probe_visual,
                )
                if blocked_structural_wait is not None:
                    if cls._directional_wait_meets_baseline(
                        observe_meta=observe_meta,
                        edge_pair=edge_pair,
                        side=blocked_structural_wait[1],
                    ):
                        return blocked_structural_wait
                    return ("WAIT", "", reason)
            return ("WAIT", "", reason)
        if action == "BUY":
            return ("BUY_READY", "BUY", reason)
        if action == "SELL":
            return ("SELL_READY", "SELL", reason)
        if action == "WAIT" and side == "SELL" and reason_n.endswith(watch_reason_suffix_by_side["SELL"]):
            return ("SELL_WATCH", "SELL", reason)
        if action == "WAIT" and side == "BUY" and reason_n.endswith(watch_reason_suffix_by_side["BUY"]):
            return ("BUY_WATCH", "BUY", reason)
        if action == "WAIT" and side == "BUY" and probe_visual_allowed:
            return ("BUY_PROBE", "BUY", reason or "buy_probe")
        if action == "WAIT" and side == "SELL" and probe_visual_allowed:
            return ("SELL_PROBE", "SELL", reason or "sell_probe")
        if action == "WAIT" and side in {"BUY", "SELL"} and is_probe_visual and not probe_visual_allowed:
            return ("WAIT", "", reason)
        if (
            action == "WAIT"
            and side == "BUY"
            and cls._is_lower_rebound_buy_probe_family(
                probe_scene_id=probe_scene_id,
                reason=reason,
                side=side,
                action=action,
            )
            and bb_state
            not in {
                str(item).strip().upper()
                for item in cls._probe_scene_allow_config(
                    symbol=symbol,
                    probe_scene_id=probe_scene_id,
                    reason=reason,
                    side=side,
                    action=action,
                ).get("base_allowed_bb_states", ["LOWER_EDGE", "BREAKDOWN"])
                if str(item).strip()
            }
        ):
            return ("WAIT", "", reason)
        if (
            action == "WAIT"
            and side == "SELL"
            and cls._is_upper_reject_sell_probe_family(
                probe_scene_id=probe_scene_id,
                reason=reason,
                side=side,
                action=action,
            )
            and box_state
            not in {
                str(item).strip().upper()
                for item in cls._probe_scene_allow_config(
                    symbol=symbol,
                    probe_scene_id=probe_scene_id,
                    reason=reason,
                    side=side,
                    action=action,
                ).get("allowed_box_states", ["UPPER", "UPPER_EDGE", "ABOVE", "LOWER", "LOWER_EDGE", "BELOW", "MIDDLE"])
                if str(item).strip()
            }
        ):
            return ("WAIT", "", reason)
        if (
            action == "WAIT"
            and side == "BUY"
            and directional_wait_enabled
            and cls._directional_wait_meets_baseline(observe_meta=observe_meta, edge_pair=edge_pair, side="BUY")
        ):
            return ("BUY_WAIT", "BUY", reason)
        if (
            action == "WAIT"
            and side == "SELL"
            and directional_wait_enabled
            and cls._directional_wait_meets_baseline(observe_meta=observe_meta, edge_pair=edge_pair, side="SELL")
        ):
            return ("SELL_WAIT", "SELL", reason)
        if action == "WAIT" and side == "":
            if any(reason_n.startswith(prefix) for prefix in conflict_reason_prefixes):
                return ("WAIT", "", reason)
            if (
                edge_pair_directional_wait_fallback_enabled
                and directional_wait_enabled
                and edge_context == "LOWER_EDGE"
                and edge_winner == "BUY"
                and cls._directional_wait_meets_baseline(observe_meta=observe_meta, edge_pair=edge_pair, side="BUY")
            ):
                return ("BUY_WAIT", "BUY", reason or "edge_pair_buy_wait")
            if (
                edge_pair_directional_wait_fallback_enabled
                and directional_wait_enabled
                and edge_context == "UPPER_EDGE"
                and edge_winner == "SELL"
                and cls._directional_wait_meets_baseline(observe_meta=observe_meta, edge_pair=edge_pair, side="SELL")
            ):
                return ("SELL_WAIT", "SELL", reason or "edge_pair_sell_wait")
        return ("WAIT", "", reason)

    @classmethod
    def _resolve_blocked_structural_wait(
        cls,
        *,
        side: str,
        reason: str,
        blocked_by: str,
        edge_context: str,
        edge_winner: str,
        is_probe_visual: bool,
    ) -> tuple[str, str, str] | None:
        if is_probe_visual:
            return None
        reason_n = str(reason or "").strip().lower()
        if any(reason_n.startswith(prefix) for prefix in cls._flow_translation_conflict_reason_prefixes()):
            return None
        blocked_guard = str(blocked_by or "").strip().lower()
        if blocked_guard not in cls._flow_translation_structural_wait_recovery_guards():
            return None
        if reason_n not in cls._flow_translation_structural_wait_recovery_reasons():
            return None

        side_u = str(side or "").upper()
        if side_u not in {"BUY", "SELL"}:
            winner_u = str(edge_winner or "").upper()
            if winner_u in {"BUY", "SELL"}:
                side_u = winner_u
            else:
                context_u = str(edge_context or "").upper()
                if context_u == "LOWER_EDGE":
                    side_u = "BUY"
                elif context_u == "UPPER_EDGE":
                    side_u = "SELL"

        if side_u == "BUY":
            return ("BUY_WAIT", "BUY", reason_n)
        if side_u == "SELL":
            return ("SELL_WAIT", "SELL", reason_n)
        return None

    @classmethod
    def _resolve_probe_scene_side(
        cls,
        *,
        probe_scene_id: str,
        reason: str = "",
        side: str = "",
        action: str = "",
    ) -> str:
        return resolve_probe_scene_direction(
            probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )

    @classmethod
    def _resolve_probe_scene_family(
        cls,
        *,
        probe_scene_id: str,
        reason: str = "",
        side: str = "",
        action: str = "",
    ) -> str:
        return resolve_probe_scene_policy_family(
            probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )

    @classmethod
    def _probe_scene_allow_config(
        cls,
        *,
        symbol: str,
        probe_scene_id: str,
        reason: str = "",
        side: str = "",
        action: str = "",
    ) -> dict:
        family = cls._resolve_probe_scene_family(
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )
        merged = {}
        if family:
            merged.update(cls._symbol_override_dict(symbol, "painter", "scene_allow", family))
        if probe_scene_id:
            merged.update(cls._symbol_override_dict(symbol, "painter", "scene_allow", probe_scene_id))
        return merged

    @classmethod
    def _probe_scene_allow_enabled(
        cls,
        *,
        symbol: str,
        probe_scene_id: str,
        reason: str = "",
        side: str = "",
        action: str = "",
        default: bool = True,
    ) -> bool:
        scene_cfg = cls._probe_scene_allow_config(
            symbol=symbol,
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )
        value = scene_cfg.get("enabled", default)
        return bool(default if value is None else value)

    @classmethod
    def _is_upper_reject_sell_probe_family(
        cls,
        *,
        probe_scene_id: str,
        reason: str,
        side: str = "",
        action: str = "",
    ) -> bool:
        reason_n = str(reason or "").strip().lower()
        scene_side = cls._resolve_probe_scene_side(
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )
        return scene_side == "SELL" and reason_n in {
            "upper_reject_probe_observe",
            "outer_band_reversal_support_required_observe",
            "middle_sr_anchor_required_observe",
        }

    @classmethod
    def _is_lower_rebound_buy_probe_family(
        cls,
        *,
        probe_scene_id: str,
        reason: str,
        side: str = "",
        action: str = "",
    ) -> bool:
        reason_n = str(reason or "").strip().lower()
        scene_side = cls._resolve_probe_scene_side(
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=side,
            action=action,
        )
        return scene_side == "BUY" and reason_n == "lower_rebound_probe_observe"

    @classmethod
    def _resolve_flow_observe_side(
        cls,
        *,
        side: str,
        reason: str,
        box_state: str,
        bb_state: str,
        probe_scene_id: str,
    ) -> str:
        side_u = str(side or "").upper()
        if side_u in {"BUY", "SELL"}:
            return side_u

        reason_n = str(reason or "").strip().lower()
        watch_reason_suffix_by_side = cls._flow_translation_watch_reason_suffix_by_side()
        if reason_n in cls._flow_translation_structural_wait_recovery_reasons():
            upper_context = box_state in {"UPPER", "UPPER_EDGE", "ABOVE"} or bb_state in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
            lower_context = box_state in {"LOWER", "LOWER_EDGE", "BELOW"} or bb_state in {"LOWER_EDGE", "BREAKDOWN"}
            if upper_context and not lower_context:
                return "SELL"
            if lower_context and not upper_context:
                return "BUY"

        if cls._flow_translation_scene_side_fallback_enabled():
            scene_side = cls._resolve_probe_scene_side(
                probe_scene_id=probe_scene_id,
                reason=reason,
                side=side_u,
            )
            if scene_side in {"BUY", "SELL"}:
                return scene_side

        if "upper_reject" in reason_n or reason_n.endswith(watch_reason_suffix_by_side["SELL"]):
            return "SELL"
        if "lower_rebound" in reason_n or reason_n.endswith(watch_reason_suffix_by_side["BUY"]):
            return "BUY"
        return ""

    @classmethod
    def _resolve_probe_visual_allowed(
        cls,
        *,
        symbol: str,
        reason: str,
        probe_scene_id: str,
        probe_candidate_active: bool,
        probe_plan_active: bool,
        probe_candidate_support: float,
        probe_pair_gap: float,
        box_state: str,
        bb_state: str,
        is_probe_visual: bool,
        observe_meta=None,
        blocked_by: str = "",
        quick_trace_state: str = "",
    ) -> bool:
        if not is_probe_visual:
            return False

        scene_side = cls._resolve_probe_scene_side(
            probe_scene_id=probe_scene_id,
            reason=reason,
        )
        scene_family = cls._resolve_probe_scene_family(
            probe_scene_id=probe_scene_id,
            reason=reason,
        )
        probe_active = bool(probe_plan_active or probe_candidate_active)
        if not probe_active or not pd.notna(probe_candidate_support):
            return False
        meta = observe_meta if isinstance(observe_meta, dict) else {}
        blocked_guard = str(blocked_by or "").strip().lower()
        quick_state = str(quick_trace_state or "").strip().upper()
        neutral_block_guards = cls._flow_translation_neutral_block_guards()
        blocked_quick_states = cls._flow_probe_blocked_quick_states()
        scene_cfg = cls._probe_scene_allow_config(
            symbol=symbol,
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=scene_side,
        )
        scene_enabled = cls._probe_scene_allow_enabled(
            symbol=symbol,
            probe_scene_id=probe_scene_id,
            reason=reason,
            side=scene_side,
        )

        if blocked_guard in neutral_block_guards:
            return False
        if quick_state in blocked_quick_states:
            return False

        if reason in {"upper_reject_probe_observe", "outer_band_reversal_support_required_observe", "middle_sr_anchor_required_observe"}:
            upper_context_ok = box_state in {"UPPER", "UPPER_EDGE", "ABOVE"}
            if scene_side == "SELL":
                if scene_cfg:
                    if not scene_enabled:
                        return False
                    extended_bb_states = {
                        str(item).strip().upper()
                        for item in scene_cfg.get(
                            "extended_bb_states",
                            ["MID", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"],
                        )
                        if str(item).strip()
                    }
                    allow_unknown_bb_state = bool(scene_cfg.get("allow_unknown_bb_state", True))
                    upper_context_ok = upper_context_ok or bb_state in extended_bb_states
                    if allow_unknown_bb_state and bb_state in {"", "UNKNOWN"}:
                        upper_context_ok = True
                else:
                    upper_context_ok = upper_context_ok or bb_state in {"MID", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
                    if bb_state in {"", "UNKNOWN"}:
                        upper_context_ok = True
            upper_min_support_by_side = cls._flow_probe_side_thresholds(
                "upper_min_support_by_side",
                default={"SELL": 0.16, "BUY": 0.18},
            )
            upper_min_pair_gap_by_side = cls._flow_probe_side_thresholds(
                "upper_min_pair_gap_by_side",
                default={"SELL": 0.03, "BUY": 0.04},
            )
            min_support = float(upper_min_support_by_side.get(scene_side, upper_min_support_by_side.get("BUY", 0.18)))
            min_pair_gap = float(upper_min_pair_gap_by_side.get(scene_side, upper_min_pair_gap_by_side.get("BUY", 0.04)))
            if blocked_guard == "probe_promotion_gate":
                min_support += cls._flow_probe_value("promotion_gate_support_penalty", default=0.08)
                min_pair_gap += cls._flow_probe_value("promotion_gate_pair_gap_penalty", default=0.05)
            return bool(
                probe_candidate_support >= min_support
                and (not pd.notna(probe_pair_gap) or probe_pair_gap >= min_pair_gap)
                and upper_context_ok
            )

        if reason == "lower_rebound_probe_observe":
            lower_context_ok = box_state in {"LOWER", "LOWER_EDGE", "BELOW"}
            if scene_cfg:
                if not scene_enabled:
                    return False
                extra_bb_states = {
                    str(item).strip().upper()
                    for item in scene_cfg.get("extra_bb_states", ["MID", "MIDDLE", "LOWER_EDGE", "BREAKDOWN"])
                    if str(item).strip()
                }
                lower_context_ok = lower_context_ok or bb_state in extra_bb_states
            xau_second_support_relief = bool(meta.get("xau_second_support_probe_relief"))
            if scene_family == "lower_second_support" and xau_second_support_relief:
                relief_cfg = cls._symbol_override_dict(
                    symbol,
                    "painter",
                    "relief_visibility",
                    "xau_second_support_probe_relief",
                )
                relief_mid_states = {
                    str(item).strip().upper()
                    for item in relief_cfg.get("mid_bb_states", ["MID", "MIDDLE"])
                    if str(item).strip()
                }
                lower_context_ok = lower_context_ok or bb_state in relief_mid_states | {"LOWER_EDGE", "BREAKDOWN"}
            lower_min_support_by_side = cls._flow_probe_side_thresholds(
                "lower_min_support_by_side",
                default={"BUY": 0.22, "SELL": 0.26},
            )
            lower_min_pair_gap_by_side = cls._flow_probe_side_thresholds(
                "lower_min_pair_gap_by_side",
                default={"BUY": 0.12, "SELL": 0.18},
            )
            min_support = float(lower_min_support_by_side.get(scene_side, lower_min_support_by_side.get("BUY", 0.22)))
            min_pair_gap = float(lower_min_pair_gap_by_side.get(scene_side, lower_min_pair_gap_by_side.get("BUY", 0.12)))
            if blocked_guard == "probe_promotion_gate":
                min_support += cls._flow_probe_value("promotion_gate_support_penalty", default=0.08)
                min_pair_gap += cls._flow_probe_value("promotion_gate_pair_gap_penalty", default=0.05)
            allowed = bool(
                probe_candidate_support >= min_support
                and (not pd.notna(probe_pair_gap) or probe_pair_gap >= min_pair_gap)
                and lower_context_ok
            )
            if "base_allowed_bb_states" in scene_cfg:
                if not scene_enabled:
                    return False
                base_allowed_bb_states = {
                    str(item).strip().upper()
                    for item in scene_cfg.get("base_allowed_bb_states", ["LOWER_EDGE", "BREAKDOWN"])
                    if str(item).strip()
                }
                relief_cfg = cls._symbol_override_dict(
                    symbol,
                    "painter",
                    "relief_visibility",
                    "xau_second_support_probe_relief",
                )
                relief_mid_states = {
                    str(item).strip().upper()
                    for item in relief_cfg.get("mid_bb_states", ["MID", "MIDDLE"])
                    if str(item).strip()
                }
                allowed = bool(
                    allowed
                    and (
                        bb_state in base_allowed_bb_states
                        or (xau_second_support_relief and bb_state in relief_mid_states)
                    )
                )
            return allowed

        return True

    @classmethod
    def _directional_wait_meets_baseline(cls, *, observe_meta: dict, edge_pair: dict, side: str) -> bool:
        side_u = str(side or "").upper()
        if side_u not in {"BUY", "SELL"}:
            return True

        support_thresholds = cls._flow_readiness_side_thresholds(
            "directional_wait_min_support_by_side",
            default={"BUY": 0.05, "SELL": 0.05},
        )
        pair_gap_thresholds = cls._flow_readiness_side_thresholds(
            "directional_wait_min_pair_gap_by_side",
            default={"BUY": 0.02, "SELL": 0.02},
        )

        support_floor = float(support_thresholds.get(side_u, support_thresholds.get("BUY", 0.05)))
        pair_gap_floor = float(pair_gap_thresholds.get(side_u, pair_gap_thresholds.get("BUY", 0.02)))

        semantic_readiness = cls._coerce_dict(observe_meta.get("semantic_readiness_bridge_v1"))
        readiness_final = cls._coerce_dict(semantic_readiness.get("final"))
        raw_contributions = cls._coerce_dict(observe_meta.get("raw_contributions"))
        raw_readiness = cls._coerce_dict(raw_contributions.get("semantic_readiness_bridge_v1"))

        support_key = "buy_support" if side_u == "BUY" else "sell_support"
        try:
            support_value = float(
                pd.to_numeric(
                    readiness_final.get(support_key, raw_readiness.get(support_key)),
                    errors="coerce",
                )
            )
        except Exception:
            support_value = float("nan")
        try:
            pair_gap_value = float(
                pd.to_numeric(
                    edge_pair.get(
                        "pair_gap",
                        cls._coerce_dict(raw_contributions.get("edge_pair_law_v1")).get("pair_gap"),
                    ),
                    errors="coerce",
                )
            )
        except Exception:
            pair_gap_value = float("nan")

        has_support = pd.notna(support_value)
        has_pair_gap = pd.notna(pair_gap_value)
        if not has_support and not has_pair_gap:
            return True
        if has_support and support_value < support_floor:
            return False
        if has_pair_gap and pair_gap_value < pair_gap_floor:
            return False
        return True

    @staticmethod
    def _is_terminal_flow_event(kind: str) -> bool:
        return str(kind or "").upper() in {"ENTER_BUY", "ENTER_SELL", "EXIT_NOW", "REVERSE_READY"}

    @classmethod
    def _is_compactable_flow_event(cls, kind: str) -> bool:
        return str(kind or "").upper() in cls._flow_visual_compact_history_kinds()

    @staticmethod
    def _flow_event_compaction_group(kind: str) -> str:
        kind_u = str(kind or "").upper()
        if kind_u.startswith("BUY_"):
            return "BUY"
        if kind_u.startswith("SELL_"):
            return "SELL"
        if kind_u in {"WAIT", "HOLD"}:
            return kind_u
        return kind_u

    @staticmethod
    def _flow_event_priority(kind: str) -> int:
        kind_u = str(kind or "").upper()
        if kind_u in {"ENTER_BUY", "ENTER_SELL", "EXIT_NOW", "REVERSE_READY"}:
            return 100
        if kind_u in {"BUY_READY", "SELL_READY"}:
            return 80
        if kind_u in {"BUY_PROBE", "SELL_PROBE"}:
            return 65
        if kind_u in {"BUY_BLOCKED", "SELL_BLOCKED"}:
            return 60
        if kind_u in {"BUY_WATCH", "SELL_WATCH"}:
            return 55
        if kind_u in {"BUY_WAIT", "SELL_WAIT"}:
            return 45
        if kind_u == "HOLD":
            return 35
        if kind_u == "WAIT":
            return 20
        return 10

    @classmethod
    def _flow_event_signal_side(cls, row: dict, event_kind: str, side: str = "") -> str:
        side_u = str(side or "").upper()
        if side_u in {"BUY", "SELL"}:
            return side_u
        kind_u = str(event_kind or "").upper()
        if kind_u.startswith("BUY_") or kind_u == "ENTER_BUY":
            return "BUY"
        if kind_u.startswith("SELL_") or kind_u in {"ENTER_SELL", "REVERSE_READY", "EXIT_NOW"}:
            return "SELL"
        observe = cls._coerce_dict(row.get("observe_confirm_v2"))
        observe_side = str(observe.get("side", "") or "").upper()
        return observe_side if observe_side in {"BUY", "SELL"} else ""

    @classmethod
    def _flow_event_blocked_penalty(cls, row: dict) -> float:
        penalty_map = cls._flow_strength_block_penalty_by_guard()
        blocked_by = str(row.get("blocked_by", "") or "").strip().lower()
        action_none_reason = str(row.get("action_none_reason", "") or "").strip().lower()
        if blocked_by:
            if blocked_by in penalty_map:
                return float(penalty_map[blocked_by])
            if blocked_by.endswith("_soft_block"):
                soft_block = penalty_map.get("*_soft_block")
                if soft_block is not None:
                    return float(soft_block)
        if action_none_reason == "probe_not_promoted":
            return float(penalty_map.get("probe_promotion_gate", 0.10))
        if any(action_none_reason.startswith(prefix) for prefix in cls._flow_translation_conflict_reason_prefixes()):
            return float(penalty_map.get("conflict_default", 0.24))
        return 0.0

    @classmethod
    def _flow_event_signal_score(cls, row: dict, event_kind: str, side: str = "") -> float:
        observe = cls._coerce_dict(row.get("observe_confirm_v2"))
        observe_meta = cls._coerce_dict(observe.get("metadata"))
        continuation_overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        signal_side = cls._flow_event_signal_side(row, event_kind, side)
        try:
            confidence = float(pd.to_numeric(observe.get("confidence"), errors="coerce"))
        except Exception:
            confidence = float("nan")
        try:
            candidate_support = float(pd.to_numeric(row.get("probe_candidate_support"), errors="coerce"))
        except Exception:
            candidate_support = float("nan")
        if pd.isna(candidate_support):
            semantic_readiness = cls._coerce_dict(observe_meta.get("semantic_readiness_bridge_v1"))
            readiness_final = cls._coerce_dict(semantic_readiness.get("final"))
            if signal_side == "BUY":
                candidate_support = cls._policy_float(readiness_final.get("buy_support"), default=float("nan"))
            elif signal_side == "SELL":
                candidate_support = cls._policy_float(readiness_final.get("sell_support"), default=float("nan"))
        try:
            pair_gap = float(pd.to_numeric(row.get("probe_pair_gap"), errors="coerce"))
        except Exception:
            pair_gap = float("nan")
        if pd.isna(pair_gap):
            edge_pair = cls._coerce_dict(row.get("edge_pair_law_v1") or observe_meta.get("edge_pair_law_v1"))
            pair_gap = cls._policy_float(edge_pair.get("pair_gap"), default=float("nan"))
        score = 0.0
        if pd.notna(confidence):
            score = max(score, float(confidence))
        if pd.notna(candidate_support):
            score = max(score, float(candidate_support))
        overlay_kind = str(continuation_overlay.get("overlay_event_kind_hint", "") or "").upper().strip()
        overlay_score = cls._policy_float(continuation_overlay.get("overlay_score"), default=float("nan"))
        if bool(continuation_overlay.get("overlay_enabled", False)) and overlay_kind == str(event_kind or "").upper():
            if pd.notna(overlay_score):
                score = max(score, float(overlay_score))
        if pd.notna(pair_gap):
            score += float(pair_gap) * cls._flow_strength_value("pair_gap_weight", default=0.35)
        quick_trace_state = str(row.get("quick_trace_state", "") or "").upper()
        if quick_trace_state == "PROBE_READY" and str(event_kind or "").upper() in {"BUY_READY", "SELL_READY", "BUY_PROBE", "SELL_PROBE"}:
            scoring = cls._flow_policy_section("scoring")
            score += cls._flow_strength_value(
                "probe_ready_bonus",
                default=cls._policy_float(scoring.get("probe_ready_bonus"), default=0.05),
            )
        score -= cls._flow_event_blocked_penalty(row)
        return float(max(0.0, min(1.0, score)))

    @classmethod
    def _flow_event_strength_level(cls, *, score: float) -> int:
        score_f = cls._policy_float(score, default=0.0)
        score_f = max(0.0, min(1.0, score_f))
        edges = cls._flow_strength_bucket_edges()
        for idx, edge in enumerate(edges, start=1):
            if score_f < float(edge):
                return int(idx)
        return int(cls._flow_strength_level_count())

    @classmethod
    def _flow_event_min_score_for_level(cls, level: int) -> float:
        count = max(1, int(cls._flow_strength_level_count()))
        level_i = max(1, min(count, int(level or 1)))
        if count <= 1:
            return 1.0
        return float(max(0.01, min(1.0, (level_i - 1) / float(count - 1))))

    @classmethod
    def _flow_event_consumer_display_level(
        cls,
        row: dict,
        event_kind: str,
        *,
        side: str = "",
    ) -> int | None:
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        continuation_overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        overlay_kind = str(continuation_overlay.get("overlay_event_kind_hint", "") or "").upper().strip()
        overlay_side = str(continuation_overlay.get("overlay_side", "") or "").upper().strip()
        signal_side = cls._flow_event_signal_side(row, event_kind, side)
        if (
            bool(continuation_overlay.get("overlay_enabled", False))
            and overlay_kind == str(event_kind or "").upper()
            and (not overlay_side or not signal_side or overlay_side == signal_side)
        ):
            overlay_score = cls._policy_float(continuation_overlay.get("overlay_score"), default=float("nan"))
            if pd.notna(overlay_score) and overlay_score > 0.0:
                return cls._flow_event_strength_level(score=float(overlay_score))
        if not consumer_check:
            return None
        resolved = cls._resolve_consumer_check_event_kind(row)
        if resolved is None:
            return None
        expected_kind, expected_side, _expected_reason = resolved
        if str(expected_kind or "").upper() != str(event_kind or "").upper():
            return None
        if expected_side and signal_side and str(expected_side or "").upper() != str(signal_side or "").upper():
            return None
        level = int(consumer_check.get("display_strength_level", 0) or 0)
        return level if level > 0 else None

    @classmethod
    def _flow_event_consumer_display_score(
        cls,
        row: dict,
        event_kind: str,
        *,
        side: str = "",
    ) -> float | None:
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        continuation_overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        overlay_kind = str(continuation_overlay.get("overlay_event_kind_hint", "") or "").upper().strip()
        overlay_side = str(continuation_overlay.get("overlay_side", "") or "").upper().strip()
        signal_side = cls._flow_event_signal_side(row, event_kind, side)
        if (
            bool(continuation_overlay.get("overlay_enabled", False))
            and overlay_kind == str(event_kind or "").upper()
            and (not overlay_side or not signal_side or overlay_side == signal_side)
        ):
            overlay_score = cls._policy_float(continuation_overlay.get("overlay_score"), default=float("nan"))
            if pd.notna(overlay_score) and overlay_score > 0.0:
                return float(max(0.0, min(1.0, overlay_score)))
        if not consumer_check:
            return None
        resolved = cls._resolve_consumer_check_event_kind(row)
        if resolved is None:
            return None
        expected_kind, expected_side, _expected_reason = resolved
        if str(expected_kind or "").upper() != str(event_kind or "").upper():
            return None
        if expected_side and signal_side and str(expected_side or "").upper() != str(signal_side or "").upper():
            return None
        score = cls._policy_float(consumer_check.get("display_score"), default=float("nan"))
        if pd.isna(score) or score <= 0.0:
            return None
        return float(max(0.0, min(1.0, score)))

    @classmethod
    def _flow_event_consumer_repeat_count(
        cls,
        row: dict,
        event_kind: str,
        *,
        side: str = "",
    ) -> int | None:
        consumer_check = cls._coerce_dict(row.get("consumer_check_state_v1"))
        continuation_overlay = cls._coerce_dict(row.get("directional_continuation_overlay_v1"))
        overlay_kind = str(continuation_overlay.get("overlay_event_kind_hint", "") or "").upper().strip()
        overlay_side = str(continuation_overlay.get("overlay_side", "") or "").upper().strip()
        signal_side = cls._flow_event_signal_side(row, event_kind, side)
        if (
            bool(continuation_overlay.get("overlay_enabled", False))
            and overlay_kind == str(event_kind or "").upper()
            and (not overlay_side or not signal_side or overlay_side == signal_side)
        ):
            try:
                repeat_count = int(pd.to_numeric(continuation_overlay.get("overlay_repeat_count"), errors="coerce"))
            except Exception:
                repeat_count = 0
            if repeat_count > 0:
                return max(0, int(repeat_count))
        if not consumer_check:
            return None
        resolved = cls._resolve_consumer_check_event_kind(row)
        if resolved is None:
            return None
        expected_kind, expected_side, _expected_reason = resolved
        if str(expected_kind or "").upper() != str(event_kind or "").upper():
            return None
        if expected_side and signal_side and str(expected_side or "").upper() != str(signal_side or "").upper():
            return None
        try:
            repeat_count = int(pd.to_numeric(consumer_check.get("display_repeat_count"), errors="coerce"))
        except Exception:
            return None
        return max(0, int(repeat_count or 0))

    @classmethod
    def _flow_event_repeat_count(
        cls,
        event_kind: str,
        *,
        display_score: float | None = None,
        explicit_repeat_count: int | None = None,
    ) -> int:
        kind_u = str(event_kind or "").upper()
        if kind_u == "WAIT":
            if explicit_repeat_count is not None and int(explicit_repeat_count or 0) > 0:
                return max(1, int(explicit_repeat_count or 1))
            return 1
        if kind_u not in cls._flow_visual_repeat_apply_kinds():
            return 1
        if explicit_repeat_count is not None and int(explicit_repeat_count or 0) > 0:
            return max(1, int(explicit_repeat_count or 1))
        if display_score is None or not pd.notna(display_score):
            return 1
        score_f = max(0.0, min(1.0, float(display_score or 0.0)))
        single, double, triple = cls._flow_visual_repeat_thresholds()
        if score_f >= triple:
            return 3
        if score_f >= double:
            return 2
        if score_f >= single:
            return 1
        return 0

    @classmethod
    def _flow_event_default_display_score(
        cls,
        event_kind: str,
        *,
        level: int | None = None,
        score: float | None = None,
    ) -> float:
        kind_u = str(event_kind or "").upper()
        level_i = max(
            1,
            int(level or cls._flow_event_strength_level(score=cls._policy_float(score, default=0.0))),
        )
        if kind_u == "WAIT":
            return 1.0
        if kind_u in {"BUY_READY", "SELL_READY", "ENTER_BUY", "ENTER_SELL", "REVERSE_READY"}:
            return float(min(0.98, 0.92 + (max(0, level_i - 8) * 0.02)))
        if kind_u in {"BUY_PROBE", "SELL_PROBE"}:
            return float(min(0.89, 0.82 + (max(0, level_i - 6) * 0.04)))
        if kind_u in {"BUY_WATCH", "SELL_WATCH"}:
            return float(0.75 if level_i >= 5 else 0.72)
        if kind_u in {"BUY_WAIT", "SELL_WAIT"}:
            return float(min(0.79, 0.72 + (max(0, level_i - 4) * 0.03)))
        if kind_u in {"BUY_BLOCKED", "SELL_BLOCKED"}:
            return float(min(0.79, 0.71 + (max(0, level_i - 3) * 0.02)))
        return float(max(0.0, min(1.0, cls._policy_float(score, default=0.0))))

    @staticmethod
    def _flow_repeat_offsets(repeat_count: int) -> tuple[float, ...]:
        count = max(0, int(repeat_count or 0))
        if count <= 0:
            return ()
        if count <= 1:
            return (0.0,)
        if count == 2:
            return (-0.55, 0.55)
        return (-1.0, 0.0, 1.0)

    @staticmethod
    def _blend_bgr_color(color: int, target_color: int, alpha: float) -> int:
        alpha_f = max(0.0, min(1.0, float(alpha or 0.0)))
        src = int(color) & 0xFFFFFF
        dst = int(target_color) & 0xFFFFFF
        r = int(round(((src & 0xFF) * (1.0 - alpha_f)) + ((dst & 0xFF) * alpha_f)))
        g = int(round(((((src >> 8) & 0xFF) * (1.0 - alpha_f)) + (((dst >> 8) & 0xFF) * alpha_f))))
        b = int(round(((((src >> 16) & 0xFF) * (1.0 - alpha_f)) + (((dst >> 16) & 0xFF) * alpha_f))))
        return int((b << 16) | (g << 8) | r)

    @classmethod
    def _flow_event_color(cls, event_kind: str, score: float, *, level: int | None = None) -> int:
        kind_u = str(event_kind or "").upper()
        base = cls._flow_visual_base_color(kind_u, default=16777215)
        try:
            score_f = float(score)
        except Exception:
            return base
        if not pd.notna(score_f) or score_f <= 0.0:
            return base
        level_i = int(level or cls._flow_event_strength_level(score=score_f))
        if kind_u in cls._flow_strength_visual_apply_kinds("color_apply_event_kinds"):
            binding = cls._flow_strength_visual_binding()
            alpha = cls._flow_strength_visual_alpha_by_level().get(level_i, 0.0)
            if alpha > 0.0:
                target = int(binding.get("brighten_target_color", 0x00FFFFFF) or 0x00FFFFFF)
                return cls._blend_bgr_color(base, target, alpha)
            return base
        wait_cfg = cls._flow_visual_wait_config(kind_u)
        if wait_cfg:
            brighten_threshold = cls._policy_float(wait_cfg.get("brighten_threshold"), default=float("inf"))
            brighten_target_color = int(wait_cfg.get("brighten_target_color", 0x00FFFFFF) or 0x00FFFFFF)
            brighten_alpha_base = cls._policy_float(wait_cfg.get("brighten_alpha_base"), default=0.0)
            brighten_alpha_scale = cls._policy_float(wait_cfg.get("brighten_alpha_scale"), default=0.0)
            brighten_alpha_cap = cls._policy_float(wait_cfg.get("brighten_alpha_cap"), default=1.0)
            dim_threshold = cls._policy_float(wait_cfg.get("dim_threshold"), default=-1.0)
            dim_target_color = int(wait_cfg.get("dim_target_color", 0x00000000) or 0x00000000)
            dim_alpha = cls._policy_float(wait_cfg.get("dim_alpha"), default=0.0)
            if score_f >= brighten_threshold:
                alpha = min(brighten_alpha_cap, brighten_alpha_base + ((score_f - brighten_threshold) * brighten_alpha_scale))
                return cls._blend_bgr_color(base, brighten_target_color, alpha)
            if score_f < dim_threshold:
                return cls._blend_bgr_color(base, dim_target_color, dim_alpha)
        return base

    @classmethod
    def _flow_event_line_width(cls, event_kind: str, *, level: int | None = None, score: float | None = None) -> int:
        kind_u = str(event_kind or "").upper()
        if kind_u not in cls._flow_strength_visual_apply_kinds("line_width_apply_event_kinds"):
            return 2
        level_i = int(level or cls._flow_event_strength_level(score=cls._policy_float(score, default=0.0)))
        width = cls._flow_strength_line_width_by_level().get(level_i, 2)
        return max(1, int(width or 2))

    @classmethod
    def _should_replace_same_timestamp_flow_event(cls, previous_event: dict, next_event: dict) -> bool:
        prev_kind = str(previous_event.get("event_kind", "") or "").upper()
        next_kind = str(next_event.get("event_kind", "") or "").upper()
        next_blocked_by = str(next_event.get("blocked_by", "") or "").strip().lower()
        if next_kind == "WAIT" and next_blocked_by in cls._flow_translation_neutral_block_guards():
            return True
        if next_kind in {"BUY_BLOCKED", "SELL_BLOCKED"} and bool(next_blocked_by):
            return True
        if cls._is_terminal_flow_event(prev_kind) and not cls._is_terminal_flow_event(next_kind):
            return False
        if cls._is_terminal_flow_event(next_kind) and not cls._is_terminal_flow_event(prev_kind):
            return True

        prev_group = cls._flow_event_compaction_group(prev_kind)
        next_group = cls._flow_event_compaction_group(next_kind)
        prev_directional = prev_group in {"BUY", "SELL"}
        next_directional = next_group in {"BUY", "SELL"}
        if prev_directional and not next_directional:
            return False
        if next_directional and not prev_directional:
            return True

        prev_priority = int(previous_event.get("priority", cls._flow_event_priority(prev_kind)) or 0)
        next_priority = int(next_event.get("priority", cls._flow_event_priority(next_kind)) or 0)
        if next_priority != prev_priority:
            return next_priority > prev_priority

        prev_score = float(previous_event.get("score", 0.0) or 0.0)
        next_score = float(next_event.get("score", 0.0) or 0.0)
        if abs(next_score - prev_score) > 1e-9:
            return next_score > prev_score

        if prev_group != next_group and prev_directional and next_directional:
            return False
        return True

    @classmethod
    def _should_compact_recent_flow_event(cls, previous_event: dict, next_event: dict) -> bool:
        prev_kind = str(previous_event.get("event_kind", "") or "").upper()
        next_kind = str(next_event.get("event_kind", "") or "").upper()
        if cls._is_terminal_flow_event(prev_kind) or cls._is_terminal_flow_event(next_kind):
            return False
        if not cls._is_compactable_flow_event(prev_kind) or not cls._is_compactable_flow_event(next_kind):
            return False
        if cls._flow_event_compaction_group(prev_kind) != cls._flow_event_compaction_group(next_kind):
            return False
        try:
            prev_ts = int(previous_event.get("ts", 0) or 0)
            next_ts = int(next_event.get("ts", 0) or 0)
        except Exception:
            return False
        if prev_ts <= 0 or next_ts <= 0:
            return False
        return abs(next_ts - prev_ts) <= cls._FLOW_SIGNAL_COMPACT_WINDOW_SEC

    @classmethod
    def _is_directional_flow_event(cls, event_kind: str) -> bool:
        return cls._flow_event_compaction_group(event_kind) in {"BUY", "SELL"}

    @classmethod
    def _should_keep_repeated_signature_event(cls, previous_event: dict | None, next_event_kind: str, next_ts: int) -> bool:
        if not isinstance(previous_event, dict):
            return False
        if not cls._is_directional_flow_event(next_event_kind):
            return False
        try:
            prev_ts = int(previous_event.get("ts", 0) or 0)
            next_ts = int(next_ts or 0)
        except Exception:
            return False
        if prev_ts <= 0 or next_ts <= prev_ts:
            return False
        return abs(next_ts - prev_ts) >= cls._FLOW_SIGNATURE_REPEAT_MIN_SEC

    @classmethod
    def _resolve_pre_entry_precursor_event_kind(cls, symbol: str, row: dict) -> tuple[str, str, str]:
        if not isinstance(row, dict):
            return ("", "", "")
        precursor_row = dict(row)
        precursor_row["entry_decision_result_v1"] = {}
        return cls._resolve_flow_event_kind(symbol, precursor_row)

    @classmethod
    def _build_pre_entry_precursor_payload(
        cls,
        symbol: str,
        row: dict,
        df_1m,
        tick,
        *,
        event_ts: int,
        terminal_kind: str,
        terminal_side: str,
    ) -> dict | None:
        if str(terminal_kind or "").upper() not in {"ENTER_BUY", "ENTER_SELL"}:
            return None
        precursor_kind, precursor_side, precursor_reason = cls._resolve_pre_entry_precursor_event_kind(symbol, row)
        precursor_kind_u = str(precursor_kind or "").upper()
        precursor_side_u = str(precursor_side or "").upper()
        if precursor_kind_u not in {
            "BUY_PROBE",
            "SELL_PROBE",
            "BUY_WATCH",
            "SELL_WATCH",
            "BUY_WAIT",
            "SELL_WAIT",
            "BUY_BLOCKED",
            "SELL_BLOCKED",
            "BUY_READY",
            "SELL_READY",
        }:
            return None
        if precursor_side_u != str(terminal_side or "").upper():
            return None
        precursor_score = cls._flow_event_signal_score(row, precursor_kind_u, side=precursor_side_u)
        precursor_level = cls._flow_event_consumer_display_level(
            row,
            precursor_kind_u,
            side=precursor_side_u,
        ) or cls._flow_event_strength_level(score=precursor_score)
        precursor_display_score = cls._flow_event_consumer_display_score(
            row,
            precursor_kind_u,
            side=precursor_side_u,
        )
        if precursor_display_score is None:
            precursor_display_score = cls._flow_event_default_display_score(
                precursor_kind_u,
                level=precursor_level,
                score=precursor_score,
            )
        precursor_repeat_count = cls._flow_event_consumer_repeat_count(
            row,
            precursor_kind_u,
            side=precursor_side_u,
        )
        precursor_repeat_count = cls._flow_event_repeat_count(
            precursor_kind_u,
            display_score=float(precursor_display_score),
            explicit_repeat_count=precursor_repeat_count,
        )
        precursor_score = max(
            float(precursor_score),
            cls._flow_event_min_score_for_level(precursor_level),
        )
        precursor_price = cls._event_price(df_1m, tick, side=precursor_side_u, event_kind=precursor_kind_u, reason=precursor_reason)
        return {
            "ts": max(1, int(event_ts) - 1),
            "price": float(precursor_price),
            "event_kind": str(precursor_kind_u),
            "side": str(precursor_side_u),
            "reason": str(precursor_reason),
            "blocked_by": str(row.get("blocked_by", "") or ""),
            "action_none_reason": str(row.get("action_none_reason", "") or ""),
            "priority": int(cls._flow_event_priority(precursor_kind_u)),
            "score": float(precursor_score),
            "display_score": float(precursor_display_score),
            "repeat_count": int(precursor_repeat_count),
            "level": int(precursor_level),
            "box_state": str(row.get("box_state", "") or ""),
            "bb_state": str(row.get("bb_state", "") or ""),
            "probe_scene_id": str(row.get("probe_scene_id", "") or ""),
            "my_position_count": float(pd.to_numeric(row.get("my_position_count"), errors="coerce") or 0.0),
        }

    @classmethod
    def _recent_flow_event_matches(cls, previous_event: dict | None, next_event: dict | None) -> bool:
        if not isinstance(previous_event, dict) or not isinstance(next_event, dict):
            return False
        try:
            prev_ts = int(previous_event.get("ts", 0) or 0)
            next_ts = int(next_event.get("ts", 0) or 0)
        except Exception:
            return False
        if prev_ts <= 0 or next_ts <= 0:
            return False
        if abs(next_ts - prev_ts) > cls._FLOW_SIGNAL_COMPACT_WINDOW_SEC:
            return False
        return (
            str(previous_event.get("event_kind", "") or "").upper() == str(next_event.get("event_kind", "") or "").upper()
            and str(previous_event.get("side", "") or "").upper() == str(next_event.get("side", "") or "").upper()
            and str(previous_event.get("reason", "") or "") == str(next_event.get("reason", "") or "")
            and str(previous_event.get("probe_scene_id", "") or "") == str(next_event.get("probe_scene_id", "") or "")
        )

    @classmethod
    def _should_append_same_timestamp_terminal_after_precursor(cls, previous_event: dict, next_event: dict) -> bool:
        prev_kind = str(previous_event.get("event_kind", "") or "").upper()
        next_kind = str(next_event.get("event_kind", "") or "").upper()
        if next_kind not in {"ENTER_BUY", "ENTER_SELL"}:
            return False
        if cls._is_terminal_flow_event(prev_kind):
            return False
        prev_group = cls._flow_event_compaction_group(prev_kind)
        next_group = "BUY" if next_kind == "ENTER_BUY" else "SELL"
        return prev_group in {"BUY", "SELL"} and prev_group == next_group

    @classmethod
    def _push_flow_event_payload(cls, history: deque, event_payload: dict) -> None:
        if not history:
            history.append(event_payload)
            return
        if int(history[-1].get("ts", 0) or 0) == int(event_payload.get("ts", 0) or 0):
            if cls._should_append_same_timestamp_terminal_after_precursor(history[-1], event_payload):
                history.append(event_payload)
                return
            if cls._should_replace_same_timestamp_flow_event(history[-1], event_payload):
                history[-1] = event_payload
            return
        if cls._should_compact_recent_flow_event(history[-1], event_payload):
            history[-1] = event_payload
            return
        history.append(event_payload)

    @classmethod
    def _runtime_row_flow_event_ts(cls, row: dict) -> int:
        if not isinstance(row, dict):
            return 0
        for key in ("signal_bar_ts",):
            try:
                value = int(row.get(key, 0) or 0)
            except Exception:
                value = 0
            if value > 0:
                return value
        runtime_generated = row.get("runtime_snapshot_generated_ts")
        try:
            if runtime_generated not in (None, ""):
                value = int(float(runtime_generated))
                if value > 0:
                    return value
        except Exception:
            pass
        try:
            text = str(row.get("time", "") or "").strip()
            if text:
                return int(pd.Timestamp(text).timestamp())
        except Exception:
            pass
        return int(time.time())

    @classmethod
    def _runtime_row_flow_event_price(cls, row: dict, *, side: str = "", event_kind: str = "") -> float:
        if not isinstance(row, dict):
            return 0.0
        side_u = str(side or "").upper().strip()
        event_kind_u = str(event_kind or "").upper().strip()
        candidates = []
        if side_u == "BUY" or event_kind_u.startswith("BUY_"):
            candidates.extend((row.get("ask"), row.get("live_ask"), row.get("live_price")))
        elif side_u == "SELL" or event_kind_u.startswith("SELL_"):
            candidates.extend((row.get("bid"), row.get("live_bid"), row.get("live_price")))
        candidates.extend((row.get("current_close"), row.get("live_price"), row.get("bid"), row.get("ask")))
        for value in candidates:
            try:
                price = float(pd.to_numeric(value, errors="coerce"))
            except Exception:
                price = float("nan")
            if pd.notna(price) and price > 0:
                return float(price)
        return 0.0

    def sync_flow_history_from_runtime_row(self, symbol: str, row: dict) -> None:
        if not isinstance(row, dict):
            return
        safe_symbol = str(symbol or "").upper().strip()
        if not safe_symbol:
            return
        self._load_flow_history_if_needed(safe_symbol)
        suppressed = self._consumer_check_hidden_flow_suppressed(row)
        event_kind, side, reason = self._resolve_flow_event_kind(safe_symbol, row)
        if suppressed:
            overlay = self._coerce_dict(row.get("directional_continuation_overlay_v1"))
            selection_state = str(
                row.get("directional_continuation_overlay_selection_state")
                or overlay.get("overlay_selection_state")
                or ""
            ).upper()
            unresolved_selection = selection_state in {
                "LOW_ALIGNMENT",
                "DIRECTION_TIE",
                "NO_DIRECTIONAL_CANDIDATE",
                "NO_CANDIDATE",
            }
            if not unresolved_selection:
                return
            event_kind = "WAIT"
            side = ""
            reason = str(
                row.get("action_none_reason")
                or row.get("consumer_check_reason")
                or row.get("observe_reason")
                or "directional_signal_unresolved"
            ).strip()
        event_ts = self._runtime_row_flow_event_ts(row)
        event_score = self._flow_event_signal_score(row, event_kind, side=side)
        event_level = self._flow_event_consumer_display_level(
            row,
            event_kind,
            side=side,
        ) or self._flow_event_strength_level(score=event_score)
        event_display_score = self._flow_event_consumer_display_score(
            row,
            event_kind,
            side=side,
        )
        if event_display_score is None:
            event_display_score = self._flow_event_default_display_score(
                event_kind,
                level=event_level,
                score=event_score,
            )
        event_repeat_count = self._flow_event_consumer_repeat_count(
            row,
            event_kind,
            side=side,
        )
        event_repeat_count = self._flow_event_repeat_count(
            event_kind,
            display_score=float(event_display_score),
            explicit_repeat_count=event_repeat_count,
        )
        event_score = max(
            float(event_score),
            self._flow_event_min_score_for_level(event_level),
        )
        event_price = self._runtime_row_flow_event_price(row, side=side, event_kind=event_kind)
        history = self._flow_history_by_symbol.setdefault(safe_symbol, deque(maxlen=self._FLOW_HISTORY_MAXLEN))
        signature = self._flow_event_signature(row)
        last_signature = self._last_flow_signature_by_symbol.get(safe_symbol, "")
        if signature == last_signature and not self._should_keep_repeated_signature_event(history[-1] if history else None, event_kind, event_ts):
            persisted_signature = ""
            try:
                filepath = self._flow_history_filepath(safe_symbol)
                if filepath and os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as handle:
                        payload = json.loads(handle.read())
                    if isinstance(payload, dict):
                        persisted_signature = str(payload.get("last_signature", "") or "")
            except Exception:
                persisted_signature = ""
            if persisted_signature != signature:
                self._persist_flow_history(safe_symbol)
            return
        event_payload = {
            "ts": int(event_ts),
            "price": float(event_price),
            "event_kind": str(event_kind),
            "side": str(side),
            "reason": str(reason),
            "blocked_by": str(row.get("blocked_by", "") or ""),
            "action_none_reason": str(row.get("action_none_reason", "") or ""),
            "priority": int(self._flow_event_priority(event_kind)),
            "score": float(event_score),
            "display_score": float(event_display_score),
            "repeat_count": int(event_repeat_count),
            "level": int(event_level),
            "box_state": str(row.get("box_state", "") or ""),
            "bb_state": str(row.get("bb_state", "") or ""),
            "probe_scene_id": str(row.get("probe_scene_id", "") or ""),
            "my_position_count": float(pd.to_numeric(row.get("my_position_count"), errors="coerce") or 0.0),
        }
        self._push_flow_event_payload(history, event_payload)
        self._last_flow_signature_by_symbol[safe_symbol] = signature
        self._persist_flow_history(safe_symbol)

    def _record_flow_event(self, symbol: str, row: dict, df_1m, tick) -> None:
        if not isinstance(row, dict):
            return
        safe_symbol = str(symbol or "").upper()
        if not safe_symbol:
            return
        if self._consumer_check_hidden_flow_suppressed(row):
            return
        self._load_flow_history_if_needed(safe_symbol)
        event_kind, side, reason = self._resolve_flow_event_kind(safe_symbol, row)
        if df_1m is None or df_1m.empty:
            return
        event_ts = self._to_epoch_seconds(df_1m["time"].iloc[-1])
        event_score = self._flow_event_signal_score(row, event_kind, side=side)
        event_level = self._flow_event_consumer_display_level(
            row,
            event_kind,
            side=side,
        ) or self._flow_event_strength_level(score=event_score)
        event_display_score = self._flow_event_consumer_display_score(
            row,
            event_kind,
            side=side,
        )
        if event_display_score is None:
            event_display_score = self._flow_event_default_display_score(
                event_kind,
                level=event_level,
                score=event_score,
            )
        event_repeat_count = self._flow_event_consumer_repeat_count(
            row,
            event_kind,
            side=side,
        )
        event_repeat_count = self._flow_event_repeat_count(
            event_kind,
            display_score=float(event_display_score),
            explicit_repeat_count=event_repeat_count,
        )
        event_score = max(
            float(event_score),
            self._flow_event_min_score_for_level(event_level),
        )
        event_price = self._event_price(df_1m, tick, side=side, event_kind=event_kind, reason=reason)
        history = self._flow_history_by_symbol.setdefault(safe_symbol, deque(maxlen=self._FLOW_HISTORY_MAXLEN))
        signature = self._flow_event_signature(row)
        last_signature = self._last_flow_signature_by_symbol.get(safe_symbol, "")
        if signature == last_signature and not self._should_keep_repeated_signature_event(history[-1] if history else None, event_kind, event_ts):
            return
        event_payload = {
            "ts": int(event_ts),
            "price": float(event_price),
            "event_kind": str(event_kind),
            "side": str(side),
            "reason": str(reason),
            "blocked_by": str(row.get("blocked_by", "") or ""),
            "action_none_reason": str(row.get("action_none_reason", "") or ""),
            "priority": int(self._flow_event_priority(event_kind)),
            "score": float(event_score),
            "display_score": float(event_display_score),
            "repeat_count": int(event_repeat_count),
            "level": int(event_level),
            "box_state": str(row.get("box_state", "") or ""),
            "bb_state": str(row.get("bb_state", "") or ""),
            "probe_scene_id": str(row.get("probe_scene_id", "") or ""),
            "my_position_count": float(pd.to_numeric(row.get("my_position_count"), errors="coerce") or 0.0),
        }
        precursor_payload = self._build_pre_entry_precursor_payload(
            safe_symbol,
            row,
            df_1m,
            tick,
            event_ts=int(event_ts),
            terminal_kind=event_kind,
            terminal_side=side,
        )
        if precursor_payload and not self._recent_flow_event_matches(history[-1] if history else None, precursor_payload):
            self._push_flow_event_payload(history, precursor_payload)
        self._push_flow_event_payload(history, event_payload)
        self._last_flow_signature_by_symbol[safe_symbol] = signature
        self._persist_flow_history(safe_symbol)

    def _append_flow_line(self, *, name: str, t1: int, p1: float, t2: int, p2: float, color: int, width: int = 2) -> None:
        self.buffer.append(
            {
                "name": str(name),
                "type": "LINE",
                "t1": int(t1),
                "p1": float(p1),
                "t2": int(t2),
                "p2": float(p2),
                "color": int(color),
                "width": max(1, int(width or 2)),
            }
        )

    @staticmethod
    def _flow_object_names(safe_symbol: str, idx: int, repeat_idx: int = 0) -> tuple[str, str]:
        base = f"FLOW_{safe_symbol}_{idx}"
        if int(repeat_idx or 0) > 0:
            base = f"{base}_R{int(repeat_idx)}"
        return (f"{base}_A", f"{base}_B")

    def add_decision_flow_overlay(self, symbol: str, row: dict, df_all, tick) -> None:
        if not isinstance(df_all, dict):
            return
        df_1m = df_all.get("1M")
        if df_1m is None or df_1m.empty:
            return
        self._load_flow_history_if_needed(symbol)
        self._record_flow_event(symbol, row, df_1m, tick)
        safe_symbol = str(symbol or "").upper()
        history = list(self._flow_history_by_symbol.get(safe_symbol, []))
        if not history:
            return

        span = self._event_span(df_1m)
        base_half_width = max(60, int(self._TF_SECONDS.get("1M", 60) * 0.8))
        marker_time_scale = self._flow_visual_scale_value("marker_time_scale", default=1.0)
        marker_price_scale = self._flow_visual_scale_value("marker_price_scale", default=1.0)
        probe_marker_time_scale = self._flow_visual_scale_value("probe_marker_time_scale", default=marker_time_scale)
        probe_marker_price_scale = self._flow_visual_scale_value("probe_marker_price_scale", default=marker_price_scale)
        neutral_marker_time_scale = self._flow_visual_scale_value("neutral_marker_time_scale", default=marker_time_scale)
        neutral_marker_price_scale = self._flow_visual_scale_value("neutral_marker_price_scale", default=marker_price_scale)
        repeat_time_offset_scale = self._flow_visual_scale_value("display_repeat_time_offset_scale", default=0.36)
        repeat_price_offset_scale = self._flow_visual_scale_value("display_repeat_price_offset_scale", default=0.22)
        half_width = max(30, int(base_half_width * marker_time_scale))
        for idx, event in enumerate(history):
            ts = int(event["ts"])
            price = float(event["price"])
            kind = str(event["event_kind"])
            side = str(event["side"])
            score = float(event.get("score", 0.0) or 0.0)
            level = int(event.get("level", self._flow_event_strength_level(score=score)) or 1)
            display_score = self._policy_float(
                event.get("display_score"),
                default=self._flow_event_default_display_score(kind, level=level, score=score),
            )
            color = int(self._flow_event_color(kind, score, level=level))
            line_width = int(self._flow_event_line_width(kind, level=level, score=score))
            repeat_count = self._flow_event_repeat_count(
                kind,
                display_score=display_score,
                explicit_repeat_count=int(event.get("repeat_count", 0) or 0),
            )
            repeat_offsets = self._flow_repeat_offsets(repeat_count)
            if kind in {"BUY_PROBE", "SELL_PROBE", "BUY_WATCH", "SELL_WATCH"}:
                probe_half_width = max(20, int((base_half_width * 0.72) * probe_marker_time_scale))
                probe_span = span * (0.30 if kind in {"BUY_WATCH", "SELL_WATCH"} else 0.28) * probe_marker_price_scale
                direction = -1.0 if kind in {"BUY_PROBE", "BUY_WATCH"} else 1.0
                for repeat_idx, offset_factor in enumerate(repeat_offsets):
                    ts_offset = int(round(offset_factor * probe_half_width * repeat_time_offset_scale))
                    price_offset = float(offset_factor * span * repeat_price_offset_scale)
                    line_a_name, line_b_name = self._flow_object_names(safe_symbol, idx, repeat_idx)
                    self._append_flow_line(
                        name=line_a_name,
                        t1=ts + ts_offset - probe_half_width,
                        p1=price + price_offset + (probe_span * direction),
                        t2=ts + ts_offset,
                        p2=price + price_offset,
                        color=color,
                        width=line_width,
                    )
                    self._append_flow_line(
                        name=line_b_name,
                        t1=ts + ts_offset,
                        p1=price + price_offset,
                        t2=ts + ts_offset + probe_half_width,
                        p2=price + price_offset + (probe_span * direction),
                        color=color,
                        width=line_width,
                    )
            elif kind in {"BUY_READY", "BUY_WAIT", "BUY_BLOCKED", "ENTER_BUY"} or side == "BUY":
                directional_span = span * 0.35 * marker_price_scale
                for repeat_idx, offset_factor in enumerate(repeat_offsets):
                    ts_offset = int(round(offset_factor * half_width * repeat_time_offset_scale))
                    price_offset = float(offset_factor * span * repeat_price_offset_scale)
                    line_a_name, line_b_name = self._flow_object_names(safe_symbol, idx, repeat_idx)
                    self._append_flow_line(
                        name=line_a_name,
                        t1=ts + ts_offset - half_width,
                        p1=price + price_offset - directional_span,
                        t2=ts + ts_offset,
                        p2=price + price_offset,
                        color=color,
                        width=line_width,
                    )
                    self._append_flow_line(
                        name=line_b_name,
                        t1=ts + ts_offset,
                        p1=price + price_offset,
                        t2=ts + ts_offset + half_width,
                        p2=price + price_offset - directional_span,
                        color=color,
                        width=line_width,
                    )
            elif kind in {"SELL_READY", "SELL_WAIT", "SELL_BLOCKED", "ENTER_SELL", "REVERSE_READY"} or side == "SELL":
                directional_span = span * 0.35 * marker_price_scale
                for repeat_idx, offset_factor in enumerate(repeat_offsets):
                    ts_offset = int(round(offset_factor * half_width * repeat_time_offset_scale))
                    price_offset = float(offset_factor * span * repeat_price_offset_scale)
                    line_a_name, line_b_name = self._flow_object_names(safe_symbol, idx, repeat_idx)
                    self._append_flow_line(
                        name=line_a_name,
                        t1=ts + ts_offset - half_width,
                        p1=price + price_offset + directional_span,
                        t2=ts + ts_offset,
                        p2=price + price_offset,
                        color=color,
                        width=line_width,
                    )
                    self._append_flow_line(
                        name=line_b_name,
                        t1=ts + ts_offset,
                        p1=price + price_offset,
                        t2=ts + ts_offset + half_width,
                        p2=price + price_offset + directional_span,
                        color=color,
                        width=line_width,
                    )
            else:
                neutral_half_width = max(30, int(base_half_width * neutral_marker_time_scale))
                neutral_span = span * 0.20 * neutral_marker_price_scale
                for repeat_idx, offset_factor in enumerate(repeat_offsets):
                    ts_offset = int(round(offset_factor * neutral_half_width * repeat_time_offset_scale))
                    price_offset = float(offset_factor * span * repeat_price_offset_scale)
                    line_a_name, line_b_name = self._flow_object_names(safe_symbol, idx, repeat_idx)
                    self._append_flow_line(
                        name=line_a_name,
                        t1=ts + ts_offset - neutral_half_width,
                        p1=price + price_offset,
                        t2=ts + ts_offset + neutral_half_width,
                        p2=price + price_offset,
                        color=color,
                        width=line_width,
                    )
                    self._append_flow_line(
                        name=line_b_name,
                        t1=ts + ts_offset,
                        p1=price + price_offset - neutral_span,
                        t2=ts + ts_offset,
                        p2=price + price_offset + neutral_span,
                        color=color,
                        width=line_width,
                    )

    @staticmethod
    def _candidate_symbols_for_draw(symbol: str) -> list[str]:
        s = str(symbol or "").strip()
        if not s:
            return []
        out = [s]
        s_up = s.upper()
        # Keep candidates minimal to reduce file-lock collisions.
        if s_up == "NAS100":
            for cand in ("NAS100ft",):
                if cand not in out:
                    out.append(cand)
        if s_up == "XAUUSD":
            for cand in ("XAUUSD.crp",):
                if cand not in out:
                    out.append(cand)
        if s_up == "BTCUSD":
            for cand in ("BTCUSD.crp",):
                if cand not in out:
                    out.append(cand)
        return out

    @staticmethod
    def _safe_symbol_for_filename(symbol: str) -> str:
        s = str(symbol or "").strip()
        if not s:
            return ""
        # Keep only filename-safe characters for MT5 common files.
        s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
        s = s.strip("._-")
        return s

    def add_session_boxes(self, df_h1):
        if df_h1 is None or df_h1.empty:
            return

        sessions = self.session_mgr.get_all_sessions(df_h1)
        for name, data in sessions.items():
            top = max(float(data["high"]), float(data["low"]))
            bottom = min(float(data["high"]), float(data["low"]))
            box_color = self._soften_box_color(int(data["color"]))
            self.buffer.append(
                {
                    "name": f"S_{name}_BOX",
                    "type": "RECT",
                    "t1": data["t1"],
                    "p1": bottom,
                    "t2": data["t2"],
                    "p2": top,
                    "color": box_color,
                }
            )

            ext_time = data["t2"] + 3600 * 4
            self.buffer.append(
                {
                    "name": f"1H_{name}_HIGH",
                    "type": "LINE",
                    "t1": data["t1"],
                    "p1": data["high"],
                    "t2": ext_time,
                    "p2": data["high"],
                    "color": data["color"],
                }
            )
            self.buffer.append(
                {
                    "name": f"1H_{name}_LOW",
                    "type": "LINE",
                    "t1": data["t1"],
                    "p1": data["low"],
                    "t2": ext_time,
                    "p2": data["low"],
                    "color": data["color"],
                }
            )

    @staticmethod
    def _to_epoch_seconds(value):
        if isinstance(value, pd.Timestamp):
            return int(value.timestamp())
        return int(value)

    @classmethod
    def _project_trend_points(cls, *, frame, indices, column: str, timeframe_label: str, extend_bars: int):
        idx_list = ContextClassifier._pivot_indices_as_list(indices)
        if frame is None or frame.empty or len(idx_list) < 2:
            return None
        try:
            i1 = int(idx_list[-2])
            i2 = int(idx_list[-1])
            if i2 <= i1:
                return None
            p1 = float(pd.to_numeric(frame[column].iloc[i1], errors="coerce"))
            p2 = float(pd.to_numeric(frame[column].iloc[i2], errors="coerce"))
            if pd.isna(p1) or pd.isna(p2):
                return None
            current_idx = len(frame) - 1
            slope = (p2 - p1) / max(1, i2 - i1)
            ext_idx = current_idx + max(int(extend_bars), 1)
            ext_p = float(p2 + slope * (ext_idx - i2))
            t1 = cls._to_epoch_seconds(frame["time"].iloc[i1])
            last_t = cls._to_epoch_seconds(frame["time"].iloc[current_idx])
            ext_t = int(last_t + cls._TF_SECONDS.get(str(timeframe_label or "").upper(), 60) * max(int(extend_bars), 1))
            return {
                "t1": t1,
                "p1": float(p1),
                "t2": ext_t,
                "p2": ext_p,
            }
        except Exception:
            return None

    def add_trend_lines(self, df_h1, order=5, extend_hours=4):
        if df_h1 is None or df_h1.empty or len(df_h1) < (order * 2 + 2):
            return

        high_idx, low_idx = self.trend_mgr.get_pivots(df_h1, order=order)
        extend_bars = max(int(extend_hours), 1)
        resistance = self._project_trend_points(
            frame=df_h1,
            indices=high_idx,
            column="high",
            timeframe_label="1H",
            extend_bars=extend_bars,
        )
        if resistance is not None:
            self.buffer.append(
                {
                    "name": "1H_RES_TREND",
                    "type": "LINE",
                    "t1": resistance["t1"],
                    "p1": resistance["p1"],
                    "t2": resistance["t2"],
                    "p2": resistance["p2"],
                    "color": 255,
                }
            )

        support = self._project_trend_points(
            frame=df_h1,
            indices=low_idx,
            column="low",
            timeframe_label="1H",
            extend_bars=extend_bars,
        )
        if support is not None:
            self.buffer.append(
                {
                    "name": "1H_SUP_TREND",
                    "type": "LINE",
                    "t1": support["t1"],
                    "p1": support["p1"],
                    "t2": support["t2"],
                    "p2": support["p2"],
                    "color": 32768,
                }
            )

    def add_mtf_trend_lines(self, df_all):
        if not isinstance(df_all, dict):
            return

        for tf in ContextClassifier.MTF_TRENDLINE_TIMEFRAMES:
            frame = df_all.get(tf)
            if frame is None or frame.empty:
                continue
            order = int(ContextClassifier._TRENDLINE_ORDER_BY_TIMEFRAME.get(tf, 5))
            if len(frame) < (order * 2 + 2):
                continue
            try:
                high_idx, low_idx = self.trend_mgr.get_pivots(frame, order=order)
            except Exception:
                continue
            extend_bars = int(self._TRENDLINE_EXTEND_BARS.get(tf, 4))
            resistance = self._project_trend_points(
                frame=frame,
                indices=high_idx,
                column="high",
                timeframe_label=tf,
                extend_bars=extend_bars,
            )
            if resistance is not None:
                self.buffer.append(
                    {
                        "name": f"{tf}_RES_TREND",
                        "type": "LINE",
                        "t1": resistance["t1"],
                        "p1": resistance["p1"],
                        "t2": resistance["t2"],
                        "p2": resistance["p2"],
                        "color": 255,
                    }
                )
            support = self._project_trend_points(
                frame=frame,
                indices=low_idx,
                column="low",
                timeframe_label=tf,
                extend_bars=extend_bars,
            )
            if support is not None:
                self.buffer.append(
                    {
                        "name": f"{tf}_SUP_TREND",
                        "type": "LINE",
                        "t1": support["t1"],
                        "p1": support["p1"],
                        "t2": support["t2"],
                        "p2": support["p2"],
                        "color": 32768,
                    }
                )

    def add_mtf_ma_lines(self, df_all):
        if not isinstance(df_all, dict):
            return

        for tf in self.MTF_MA_TIMEFRAMES:
            frame = df_all.get(tf)
            if frame is None or frame.empty:
                continue
            try:
                frame_ind = self.trend_mgr.add_indicators(frame)
            except Exception:
                frame_ind = frame
            if frame_ind is None or frame_ind.empty or "ma_20" not in frame_ind.columns:
                continue
            ma_series = pd.to_numeric(frame_ind["ma_20"], errors="coerce").dropna()
            if ma_series.empty:
                continue
            price = float(ma_series.iloc[-1])
            line_frame = frame_ind.loc[ma_series.index]
            if line_frame.empty:
                continue
            start_idx = max(0, len(line_frame) - 10)
            t1 = self._to_epoch_seconds(line_frame["time"].iloc[start_idx])
            last_t = self._to_epoch_seconds(line_frame["time"].iloc[-1])
            extend_bars = int(self._MA_EXTEND_BARS.get(tf, 4))
            t2 = int(last_t + self._TF_SECONDS.get(tf, 60) * max(extend_bars, 1))
            self.buffer.append(
                {
                    "name": f"{tf}_MA20",
                    "type": "LINE",
                    "t1": t1,
                    "p1": price,
                    "t2": t2,
                    "p2": price,
                    "color": int(self._MA_COLORS.get(tf, 16777215)),
                }
            )

    def add_bollinger_lines(self, df_h1, period=20, std_mult=2.0, lookback=60):
        """
        H1 ??? ?????? ?? ?? ??? ????.
        """
        if df_h1 is None or df_h1.empty:
            return
        if len(df_h1) < max(period + 2, 10):
            return

        df = df_h1.copy()
        ma = df["close"].rolling(period).mean()
        std = df["close"].rolling(period).std()
        df["bb_up"] = ma + (std_mult * std)
        df["bb_mid"] = ma
        df["bb_dn"] = ma - (std_mult * std)
        df = df.dropna(subset=["bb_up", "bb_mid", "bb_dn"]).copy()
        if len(df) < 3:
            return

        df = df.iloc[-int(lookback):].copy()
        if len(df) < 3:
            return

        colors = {
            "up": 255,       # red
            "mid": 13421772, # gray
            "dn": 32768,     # green
        }

        for i in range(1, len(df)):
            t1 = self._to_epoch_seconds(df["time"].iloc[i - 1])
            t2 = self._to_epoch_seconds(df["time"].iloc[i])
            if t2 <= t1:
                continue

            self.buffer.append(
                {
                    "name": f"1H_BB20_UP_{i}",
                    "type": "LINE",
                    "t1": t1,
                    "p1": float(df["bb_up"].iloc[i - 1]),
                    "t2": t2,
                    "p2": float(df["bb_up"].iloc[i]),
                    "color": colors["up"],
                }
            )
            self.buffer.append(
                {
                    "name": f"1H_BB20_MID_{i}",
                    "type": "LINE",
                    "t1": t1,
                    "p1": float(df["bb_mid"].iloc[i - 1]),
                    "t2": t2,
                    "p2": float(df["bb_mid"].iloc[i]),
                    "color": colors["mid"],
                }
            )
            self.buffer.append(
                {
                    "name": f"1H_BB20_DN_{i}",
                    "type": "LINE",
                    "t1": t1,
                    "p1": float(df["bb_dn"].iloc[i - 1]),
                    "t2": t2,
                    "p2": float(df["bb_dn"].iloc[i]),
                    "color": colors["dn"],
                }
            )

    def save(self, symbol):
        status = {
            "ok": False,
            "symbol": str(symbol),
            "save_dir": self.save_dir,
            "line_count": int(len(self.buffer)),
            "file_results": [],
            "updated_at": int(time.time()),
        }
        if not self.buffer:
            status["reason"] = "empty_buffer"
            return status
        if not self._save_enabled:
            status["reason"] = "save_disabled"
            return status

        lines = []
        for item in self.buffer:
            item_type = str(item.get("type", "") or "").upper()
            default_width = 0 if item_type == "RECT" else 2
            width = int(item.get("width", default_width) or default_width)
            lines.append(
                f"{item['name']},{item['type']},"
                f"{int(item['t1'])},{item['p1']:.5f},"
                f"{int(item['t2'])},{item['p2']:.5f},"
                f"{item['color']},{width}\n"
            )
        payload_text = "".join(lines)
        payload_signature = hashlib.sha1(payload_text.encode("ascii", errors="ignore")).hexdigest()

        filepaths = []
        seen = set()
        for sym_name in self._candidate_symbols_for_draw(symbol):
            safe_name = self._safe_symbol_for_filename(sym_name)
            if not safe_name:
                continue
            for suffix in ("_draw_data.csv", "_draw.csv"):
                path = os.path.join(self.save_dir, f"{safe_name}{suffix}")
                if path not in seen:
                    seen.add(path)
                    filepaths.append(path)
        # Legacy fallback for indicators that read fixed filenames.
        for legacy in ("draw_data.csv", "draw.csv"):
            path = os.path.join(self.save_dir, legacy)
            if path not in seen:
                seen.add(path)
                filepaths.append(path)

        for filepath in filepaths:
            file_row = {"path": filepath, "ok": False}
            try:
                if self._last_saved_draw_signature.get(filepath) == payload_signature and os.path.exists(filepath):
                    file_row["ok"] = True
                    file_row["skipped_unchanged"] = True
                    try:
                        file_row["mtime"] = int(os.path.getmtime(filepath))
                    except OSError:
                        file_row["mtime"] = 0
                    status["file_results"].append(file_row)
                    continue
                self._write_atomic_with_retry(filepath, [payload_text])
                file_row["ok"] = True
                self._last_saved_draw_signature[filepath] = payload_signature
                try:
                    file_row["mtime"] = int(os.path.getmtime(filepath))
                except OSError:
                    file_row["mtime"] = 0
            except OSError as exc:
                file_row["error"] = str(exc)
                logger.warning("Failed to save painter output for %s (%s): %s", symbol, filepath, exc)
            status["file_results"].append(file_row)
        ok_count = int(sum(1 for row in status["file_results"] if bool(row.get("ok"))))
        status["ok"] = bool(ok_count == len(filepaths))
        status["ok_count"] = ok_count
        status["fail_count"] = int(len(filepaths) - ok_count)
        if not status["ok"] and "reason" not in status:
            status["reason"] = "write_failed"
        return status
