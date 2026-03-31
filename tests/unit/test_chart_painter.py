import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.services.context_classifier import ContextClassifier
from backend.trading.chart_flow_distribution import build_chart_flow_distribution_report
from backend.trading.chart_painter import Painter


class _DummyTrendMgr:
    _ma20 = {
        "15M": 99.0,
        "30M": 100.0,
        "1H": 101.0,
        "4H": 103.0,
        "1D": 105.0,
    }

    def get_pivots(self, frame, order=5):
        _ = order
        return np.array([1, 3]), np.array([2, 4])

    def add_indicators(self, frame):
        out = frame.copy()
        tf = str(out["tf_marker"].iloc[-1])
        out["ma_20"] = float(self._ma20.get(tf, 100.0))
        return out


def _build_frame(tf: str, freq: str):
    periods = 24 if tf == "1M" else 12
    high = [101.0 + ((idx % 4) * 2.0) for idx in range(periods)]
    low = [99.0 - ((idx % 4) * 1.5) for idx in range(periods)]
    open_ = [100.0 + ((idx % 3) - 1) for idx in range(periods)]
    close = [100.0 + ((idx % 5) - 2) * 0.5 for idx in range(periods)]
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-03-13 00:00:00", periods=periods, freq=freq),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "tf_marker": [tf] * periods,
        }
    )


def _line_value_at(line: dict, event_ts: int) -> float:
    t1 = float(line["t1"])
    t2 = float(line["t2"])
    p1 = float(line["p1"])
    p2 = float(line["p2"])
    if t2 <= t1:
        return p2
    return float(p1 + ((p2 - p1) * ((float(event_ts) - t1) / (t2 - t1))))


def _flow_items(painter: Painter, prefix: str) -> list[dict]:
    return [item for item in painter.buffer if str(item.get("name", "")).startswith(prefix)]


def _deep_update(target: dict, updates: dict) -> dict:
    for key, value in dict(updates or {}).items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def _policy_painter(
    *,
    semantics=None,
    readiness=None,
    probe=None,
    translation=None,
    visual=None,
    anchor=None,
    strength=None,
    symbol_override=None,
):
    symbol_override_policy = copy.deepcopy(Painter._SYMBOL_OVERRIDE_POLICY_V1)
    if symbol_override:
        _deep_update(symbol_override_policy, symbol_override)

    class _PolicyPainter(Painter):
        _FLOW_POLICY_V1 = {
            **Painter._FLOW_POLICY_V1,
            "semantics": {
                **Painter._FLOW_POLICY_V1["semantics"],
                **(semantics or {}),
            },
            "readiness": {
                **Painter._FLOW_POLICY_V1["readiness"],
                **(readiness or {}),
            },
            "translation": {
                **Painter._FLOW_POLICY_V1["translation"],
                **(translation or {}),
            },
            "probe": {
                **Painter._FLOW_POLICY_V1["probe"],
                **(probe or {}),
            },
            "visual": {
                **Painter._FLOW_POLICY_V1["visual"],
                **(visual or {}),
            },
            "anchor": {
                **Painter._FLOW_POLICY_V1["anchor"],
                **(anchor or {}),
            },
            "strength": {
                **Painter._FLOW_POLICY_V1["strength"],
                **(strength or {}),
            },
        }
        _SYMBOL_OVERRIDE_POLICY_V1 = symbol_override_policy

    return _PolicyPainter


@pytest.fixture(autouse=True)
def _isolate_painter_save_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("PAINTER_SAVE_DIR", str(tmp_path))
    monkeypatch.setenv("CHART_FLOW_DISTRIBUTION_PATH", str(tmp_path / "chart_flow_distribution_latest.json"))
    monkeypatch.setenv("CHART_FLOW_ROLLOUT_STATUS_PATH", str(tmp_path / "chart_flow_rollout_status_latest.json"))
    fixed_now = pd.Timestamp("2026-03-13 01:00:00").timestamp()
    monkeypatch.setattr("backend.trading.chart_painter.time.time", lambda: fixed_now)


def test_add_mtf_trend_lines_matches_context_classifier_projection():
    painter = Painter()
    painter.trend_mgr = _DummyTrendMgr()
    df_all = {
        "1M": _build_frame("1M", "min"),
        "15M": _build_frame("15M", "15min"),
        "1H": _build_frame("1H", "h"),
        "4H": _build_frame("4H", "4h"),
    }

    painter.add_mtf_trend_lines(df_all)

    names = {item["name"] for item in painter.buffer}
    assert {"1M_RES_TREND", "15M_RES_TREND", "1H_RES_TREND", "4H_RES_TREND"} <= names
    assert {"1M_SUP_TREND", "15M_SUP_TREND", "1H_SUP_TREND", "4H_SUP_TREND"} <= names

    h1_res_line = next(item for item in painter.buffer if item["name"] == "1H_RES_TREND")
    h1_frame = df_all["1H"]
    high_idx, _ = painter.trend_mgr.get_pivots(
        h1_frame,
        order=int(ContextClassifier._TRENDLINE_ORDER_BY_TIMEFRAME["1H"]),
    )
    expected = ContextClassifier._project_trendline_value(
        h1_frame,
        ContextClassifier._pivot_indices_as_list(high_idx),
        "high",
    )
    event_ts = int(pd.Timestamp(h1_frame["time"].iloc[-1]).timestamp())
    assert expected is not None
    assert abs(_line_value_at(h1_res_line, event_ts) - float(expected)) < 1e-6


def test_add_mtf_ma_lines_draws_latest_ma20_levels():
    painter = Painter()
    painter.trend_mgr = _DummyTrendMgr()
    df_all = {
        "15M": _build_frame("15M", "15min"),
        "30M": _build_frame("30M", "30min"),
        "1H": _build_frame("1H", "h"),
        "4H": _build_frame("4H", "4h"),
        "1D": _build_frame("1D", "D"),
    }

    painter.add_mtf_ma_lines(df_all)

    names = {item["name"] for item in painter.buffer}
    assert {"15M_MA20", "30M_MA20", "1H_MA20", "4H_MA20", "1D_MA20"} <= names
    one_day = next(item for item in painter.buffer if item["name"] == "1D_MA20")
    assert float(one_day["p1"]) == 105.0
    assert float(one_day["p2"]) == 105.0


def test_add_decision_flow_overlay_draws_recent_buy_and_wait_markers():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_row = {
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "reason": "lower_rebound_confirm",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", buy_row, df_all, tick)

    next_df = {"1M": df_all["1M"].copy()}
    next_df["1M"]["time"] = next_df["1M"]["time"] + pd.Timedelta(minutes=1)
    wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "middle_wait",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", wait_row, next_df, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B", "FLOW_BTCUSD_1_A", "FLOW_BTCUSD_1_B"} <= names
    assert any(int(item["color"]) == Painter._FLOW_EVENT_COLORS["BUY_READY"] for item in _flow_items(painter, "FLOW_BTCUSD_0_"))
    assert any(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_BTCUSD_1_"))


def test_add_decision_flow_overlay_ignores_exit_now_when_flat():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "middle_wait",
        },
        "my_position_count": 0,
        "exit_wait_state_v1": {
            "state": "CUT_IMMEDIATE",
            "reason": "adverse_loss_expand",
        },
        "entry_decision_result_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["XAUUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "WAIT"


def test_add_decision_flow_overlay_uses_edge_pair_wait_for_structural_upper_sell_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "outer_band_reversal_support_required_observe",
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "UPPER_EDGE",
                    "winner_side": "SELL",
                },
            },
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B"} <= names
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["SELL_WAIT"] for item in _flow_items(painter, "FLOW_BTCUSD_0_"))


def test_flow_event_color_brightens_strong_wait_hints():
    assert Painter._flow_event_color("BUY_WAIT", 0.10) == Painter._FLOW_EVENT_COLORS["BUY_WAIT"]
    assert Painter._flow_event_color("SELL_WAIT", 0.10) == Painter._FLOW_EVENT_COLORS["SELL_WAIT"]
    assert Painter._flow_event_color("BUY_WAIT", 0.34) != Painter._FLOW_EVENT_COLORS["BUY_WAIT"]
    assert Painter._flow_event_color("SELL_WAIT", 0.42) != Painter._FLOW_EVENT_COLORS["SELL_WAIT"]


def test_add_decision_flow_overlay_uses_blocked_middle_edge_pair_buy_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "middle_sr_anchor_required_observe",
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "MIDDLE",
                    "winner_side": "BUY",
                },
            },
        },
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "quick_trace_state": "BLOCKED",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert {"FLOW_NAS100_0_A", "FLOW_NAS100_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["BUY_WAIT"] for item in _flow_items(painter, "FLOW_NAS100_0_"))


def test_add_decision_flow_overlay_uses_blocked_lower_buy_wait_for_structural_rebound():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "blocked_by": "outer_band_guard",
        "action_none_reason": "observe_state_wait",
        "quick_trace_state": "BLOCKED",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["BUY_WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_record_flow_event_places_upper_reclaim_buy_wait_near_body_not_candle_low():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "upper_reclaim_strength_observe",
            "confidence": 0.32,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("XAUUSD", row, df_all["1M"], tick)

    latest = df_all["1M"].iloc[-1]
    expected_body_low = min(float(latest["open"]), float(latest["close"]))
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    assert history[0]["event_kind"] == "BUY_WAIT"
    assert history[0]["price"] == pytest.approx(expected_body_low)


def test_record_flow_event_lifts_generic_buy_wait_above_candle_low():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_edge_observe",
            "confidence": 0.14,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", row, df_all["1M"], tick)

    latest = df_all["1M"].iloc[-1]
    low = float(latest["low"])
    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert history[0]["event_kind"] == "BUY_WAIT"
    assert history[0]["price"] > low


def test_add_decision_flow_overlay_keeps_soft_blocked_sell_consumer_check_as_sell_blocked():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "SELL",
            "side": "SELL",
            "reason": "upper_reject_mixed_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "BLOCKED",
            "check_reason": "upper_reject_mixed_confirm",
            "entry_block_reason": "energy_soft_block",
            "display_strength_level": 5,
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "entry_decision_result_v1": {
            "action": "",
            "outcome": "skipped",
        },
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["XAUUSD"])
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert history[0]["event_kind"] == "SELL_BLOCKED"
    assert history[0]["level"] == 5
    assert all(int(item["width"]) == 3 for item in _flow_items(painter, "FLOW_XAUUSD_0_"))
    assert all(int(item["color"]) != Painter._FLOW_EVENT_COLORS["SELL_BLOCKED"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_keeps_conflict_edge_pair_wait_neutral():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "conflict_box_lower_bb20_upper_upper_dominant_observe",
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BUY",
                },
            },
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_draws_probe_markers_separate_from_ready_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B"} <= names
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_prefers_consumer_check_probe_state():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "CONFLICT_OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "conflict_box_lower_bb20_upper_upper_dominant_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_probe_observe",
            "display_strength_level": 6,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_NAS100_0_")
    history = list(painter._flow_history_by_symbol["NAS100"])

    assert history[0]["event_kind"] == "SELL_PROBE"
    assert history[0]["level"] == 6
    assert all(int(item["width"]) == 3 for item in flow_items)
    assert all(int(item["color"]) != Painter._FLOW_EVENT_COLORS["SELL_PROBE"] for item in flow_items)


def test_add_decision_flow_overlay_prefers_consumer_check_ready_state():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": True,
            "check_side": "BUY",
            "check_stage": "READY",
            "check_reason": "lower_rebound_confirm",
            "display_strength_level": 8,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "BUY_READY"
    assert history[0]["level"] == 8
    assert all(int(item["width"]) == 4 for item in flow_items)
    assert all(int(item["color"]) != Painter._FLOW_EVENT_COLORS["BUY_READY"] for item in flow_items)


def test_add_decision_flow_overlay_prefers_consumer_check_blocked_state():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "BLOCKED",
            "check_reason": "upper_reject_probe_observe",
            "entry_block_reason": "energy_soft_block",
            "display_strength_level": 5,
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_NAS100_0_")
    history = list(painter._flow_history_by_symbol["NAS100"])

    assert history[0]["event_kind"] == "SELL_BLOCKED"
    assert history[0]["level"] == 5
    assert all(int(item["width"]) == 3 for item in flow_items)
    assert all(int(item["color"]) != Painter._FLOW_EVENT_COLORS["SELL_BLOCKED"] for item in flow_items)


def test_add_decision_flow_overlay_falls_back_to_top_level_observe_fields_when_nested_is_empty():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": None,
            "action": None,
            "side": None,
            "reason": None,
        },
        "observe_action": "WAIT",
        "observe_side": "SELL",
        "observe_reason": "upper_reject_probe_observe",
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.05,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_inferrs_probe_side_from_reason_and_scene_when_action_side_missing():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": None,
            "action": None,
            "side": None,
            "reason": None,
        },
        "observe_action": "",
        "observe_side": "",
        "observe_reason": "upper_reject_probe_observe",
        "box_state": "BELOW",
        "bb_state": "UNKNOWN",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.25,
        "probe_pair_gap": 0.05,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_suppresses_weak_upper_probe_into_neutral_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "UNKNOWN",
        "probe_candidate_active": True,
        "probe_plan_active": False,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.07,
        "quick_trace_state": "PROBE_CANDIDATE",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B"} <= names
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_BTCUSD_0_"))


def test_add_decision_flow_overlay_suppresses_late_xau_second_support_buy_probe_above_midline():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.85,
        "probe_pair_gap": 0.19,
        "probe_scene_id": "xau_second_support_buy_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= names
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_draws_xau_second_support_buy_probe_when_relief_is_confirmed():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
            "metadata": {
                "xau_second_support_probe_relief": True,
            },
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.85,
        "probe_pair_gap": 0.19,
        "probe_scene_id": "xau_second_support_buy_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= names
    assert all(
        int(item["color"]) == expected_color
        for item in flow_items
    )


def test_add_decision_flow_overlay_respects_symbol_override_for_xau_second_support_relief_visibility():
    painter = _policy_painter(
        symbol_override={
            "symbols": {
                "XAUUSD": {
                    "painter": {
                        "relief_visibility": {
                            "xau_second_support_probe_relief": {
                                "mid_bb_states": [],
                            }
                        }
                    }
                }
            }
        }
    )()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
            "metadata": {
                "xau_second_support_probe_relief": True,
            },
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.85,
        "probe_pair_gap": 0.19,
        "probe_scene_id": "xau_second_support_buy_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_draws_xau_upper_sell_probe_when_upper_scene_active():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "UPPER",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.08,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= names
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_respects_symbol_override_for_xau_upper_sell_scene_toggle():
    painter = _policy_painter(
        symbol_override={
            "symbols": {
                "XAUUSD": {
                    "painter": {
                        "scene_allow": {
                            "xau_upper_sell_probe": {
                                "enabled": False,
                            }
                        }
                    }
                }
            }
        }
    )()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "UPPER",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.08,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_draws_xau_upper_sell_probe_from_local_upper_scene_even_if_box_below():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.05,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_draws_xau_upper_sell_probe_when_bb_state_unknown_but_scene_is_clear():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "BELOW",
        "bb_state": "UNKNOWN",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.25,
        "probe_pair_gap": 0.05,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == expected_color for item in flow_items)


def test_add_decision_flow_overlay_suppresses_late_xau_upper_sell_probe_after_upper_context_is_lost():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "BELOW",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.08,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= names
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_draws_sell_watch_marker_for_midline_sell_watch():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "btc_midline_sell_watch",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    names = {item["name"] for item in painter.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B"} <= names
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["SELL_WATCH"] for item in _flow_items(painter, "FLOW_BTCUSD_0_"))


def test_add_decision_flow_overlay_uses_stable_flow_object_names_per_index():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", buy_probe_row, df_all, tick)
    first_names = {item["name"] for item in painter.buffer}
    assert {
        "FLOW_BTCUSD_0_A",
        "FLOW_BTCUSD_0_B",
        "FLOW_BTCUSD_0_R1_A",
        "FLOW_BTCUSD_0_R1_B",
    } == first_names

    painter.clear()
    sell_watch_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "btc_midline_sell_watch",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", sell_watch_row, df_all, tick)
    second_names = {item["name"] for item in painter.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B"} <= second_names
    assert all(str(name).startswith("FLOW_BTCUSD_0_") for name in second_names)


def test_add_decision_flow_overlay_keeps_same_timestamp_directional_probe_over_later_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    sell_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
            "confidence": 0.42,
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.28,
        "probe_pair_gap": 0.07,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", sell_probe_row, df_all, tick)

    later_wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "conflict_box_lower_bb20_upper_lower_rebound_confirm",
            "confidence": 0.11,
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "quick_trace_state": "BLOCKED",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", later_wait_row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == expected_color for item in flow_items)
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["SELL_WATCH"] for item in _flow_items(painter, "FLOW_BTCUSD_0_"))


def test_record_flow_event_replaces_same_candle_signal_with_latest_state():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    sell_watch_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "btc_midline_sell_watch",
        },
        "probe_candidate_active": False,
        "probe_plan_active": False,
        "probe_plan_ready": False,
        "quick_trace_state": "OBSERVE",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", buy_probe_row, df_all["1M"], tick)
    painter._record_flow_event("BTCUSD", sell_watch_row, df_all["1M"], tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "SELL_WATCH"
    assert history[0]["reason"] == "btc_midline_sell_watch"


def test_record_flow_event_replaces_same_candle_directional_signal_with_blocked_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    sell_ready_row = {
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "SELL",
            "side": "SELL",
            "reason": "upper_reject_confirm",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", sell_ready_row, df_all, tick)

    later_blocked_wait = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "blocked_by": "outer_band_guard",
        "quick_trace_state": "PROBE_WAIT",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.30,
        "probe_pair_gap": 0.09,
        "probe_scene_id": "nas_clean_confirm_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", df_all=df_all, row=later_blocked_wait, tick=tick)

    history = list(painter._flow_history_by_symbol["NAS100"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["blocked_by"] == "outer_band_guard"


def test_add_decision_flow_overlay_respects_symbol_override_for_nas_clean_confirm_scene_toggle(tmp_path):
    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.32,
        "probe_pair_gap": 0.14,
        "probe_scene_id": "nas_clean_confirm_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    default_painter = Painter()
    default_dir = tmp_path / "default_nas_scene"
    default_dir.mkdir()
    default_painter.save_dir = str(default_dir)
    default_painter.add_decision_flow_overlay("NAS100", row, df_all, tick)
    flow_items = _flow_items(default_painter, "FLOW_NAS100_0_")
    history = list(default_painter._flow_history_by_symbol["NAS100"])
    expected_color = Painter._flow_event_color(
        history[0]["event_kind"],
        history[0]["score"],
        level=history[0]["level"],
    )
    assert all(
        int(item["color"]) == expected_color
        for item in flow_items
    )

    disabled_painter = _policy_painter(
        symbol_override={
            "symbols": {
                "NAS100": {
                    "painter": {
                        "scene_allow": {
                            "nas_clean_confirm_probe": {
                                "enabled": False,
                            }
                        }
                    }
                }
            }
        }
    )()
    disabled_dir = tmp_path / "disabled_nas_scene"
    disabled_dir.mkdir()
    disabled_painter.save_dir = str(disabled_dir)
    disabled_painter.add_decision_flow_overlay("NAS100", row, df_all, tick)
    assert all(
        int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"]
        for item in _flow_items(disabled_painter, "FLOW_NAS100_0_")
    )


def test_record_flow_event_keeps_enter_state_over_later_same_candle_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    enter_row = {
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "reason": "lower_rebound_confirm",
        },
        "entry_decision_result_v1": {
            "outcome": "entered",
            "action": "BUY",
            "core_reason": "entry_submitted",
        },
        "exit_wait_state_v1": {},
    }
    later_wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "middle_wait",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", enter_row, df_all["1M"], tick)
    painter._record_flow_event("BTCUSD", later_wait_row, df_all["1M"], tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 2
    assert history[0]["event_kind"] == "BUY_READY"
    assert history[1]["event_kind"] == "ENTER_BUY"


def test_record_flow_event_preserves_pre_entry_probe_before_same_candle_enter():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    enter_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "quick_trace_state": "PROBE_READY",
        "entry_decision_result_v1": {
            "outcome": "entered",
            "action": "BUY",
            "core_reason": "btc_lower_rebound_semantic_probe_bridge",
        },
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", enter_row, df_all["1M"], tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 2
    assert history[0]["event_kind"] == "BUY_PROBE"
    assert history[1]["event_kind"] == "ENTER_BUY"
    assert history[0]["ts"] < history[1]["ts"]


def test_record_flow_event_does_not_duplicate_recent_precursor_before_enter():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "quick_trace_state": "PROBE_READY",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    enter_row = {
        **probe_row,
        "entry_decision_result_v1": {
            "outcome": "entered",
            "action": "BUY",
            "core_reason": "btc_lower_rebound_semantic_probe_bridge",
        },
    }

    painter._record_flow_event("BTCUSD", probe_row, df_all["1M"], tick)
    painter._record_flow_event("BTCUSD", enter_row, df_all["1M"], tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 2
    assert history[0]["event_kind"] == "BUY_PROBE"
    assert history[1]["event_kind"] == "ENTER_BUY"


def test_record_flow_event_compacts_recent_directional_hints_across_adjacent_candles():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.30,
        "probe_pair_gap": 0.20,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    later_buy_wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.34,
        "probe_pair_gap": 0.23,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", buy_wait_row, df_all["1M"], tick)
    next_df = df_all["1M"].copy()
    next_df["time"] = next_df["time"] + pd.Timedelta(minutes=1)
    painter._record_flow_event("BTCUSD", later_buy_wait_row, next_df, tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "BUY_PROBE"


def test_record_flow_event_suppresses_repeated_signature_inside_extended_repeat_window():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_wait_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.30,
        "probe_pair_gap": 0.20,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("BTCUSD", buy_wait_row, df_all["1M"], tick)
    later_df = df_all["1M"].copy()
    later_df["time"] = later_df["time"] + pd.Timedelta(minutes=5)
    painter._record_flow_event("BTCUSD", buy_wait_row, later_df, tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "BUY_PROBE"


def test_record_flow_event_keeps_opposite_direction_probe_events_separate():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    sell_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.24,
        "probe_pair_gap": 0.08,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    buy_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("XAUUSD", sell_probe_row, df_all["1M"], tick)
    next_df = df_all["1M"].copy()
    next_df["time"] = next_df["time"] + pd.Timedelta(minutes=1)
    painter._record_flow_event("XAUUSD", buy_probe_row, next_df, tick)

    history = list(painter._flow_history_by_symbol["XAUUSD"])
    assert len(history) == 2
    assert history[0]["event_kind"] == "SELL_PROBE"
    assert history[1]["event_kind"] == "BUY_PROBE"


def test_flow_history_persists_and_reloads_across_painter_instances(tmp_path):
    painter = Painter()
    painter.save_dir = str(tmp_path)
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    sell_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "BELOW",
        "bb_state": "MID",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.28,
        "probe_pair_gap": 0.07,
        "probe_scene_id": "xau_upper_sell_probe",
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter._record_flow_event("XAUUSD", sell_probe_row, df_all["1M"], tick)
    history_path = tmp_path / "XAUUSD_flow_history.json"
    assert history_path.exists()

    restored = Painter()
    restored.save_dir = str(tmp_path)
    restored._load_flow_history_if_needed("XAUUSD")

    history = list(restored._flow_history_by_symbol["XAUUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "SELL_PROBE"
    assert history[0]["reason"] == "upper_reject_probe_observe"
    assert restored._last_flow_signature_by_symbol["XAUUSD"] == painter._last_flow_signature_by_symbol["XAUUSD"]


def test_flow_history_reload_converts_soft_blocked_ready_events_into_blocked(tmp_path):
    history_path = tmp_path / "XAUUSD_flow_history.json"
    history_path.write_text(
        json.dumps(
            {
                "version": 1,
                "symbol": "XAUUSD",
                "updated_at": 1,
                "last_signature": "SELL|SELL|upper_reject_mixed_confirm",
                "events": [
                    {
                        "ts": 1774356840,
                        "price": 4417.52,
                        "event_kind": "SELL_READY",
                        "side": "SELL",
                        "reason": "upper_reject_mixed_confirm",
                        "blocked_by": "energy_soft_block",
                        "priority": 80,
                        "score": 0.53,
                    }
                ],
            }
        ),
        encoding="ascii",
    )

    restored = Painter()
    restored.save_dir = str(tmp_path)
    restored._load_flow_history_if_needed("XAUUSD")

    history = list(restored._flow_history_by_symbol["XAUUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "SELL_BLOCKED"
    assert history[0]["blocked_by"] == "energy_soft_block"


def test_add_decision_flow_overlay_reuses_persisted_flow_history_after_restart(tmp_path):
    original = Painter()
    original.save_dir = str(tmp_path)
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    buy_probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.30,
        "probe_pair_gap": 0.20,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    original._record_flow_event("BTCUSD", buy_probe_row, df_all["1M"], tick)

    restarted = Painter()
    restarted.save_dir = str(tmp_path)
    next_df = {"1M": df_all["1M"].copy()}
    next_df["1M"]["time"] = next_df["1M"]["time"] + pd.Timedelta(minutes=1)
    sell_watch_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "btc_midline_sell_watch",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    restarted.add_decision_flow_overlay("BTCUSD", sell_watch_row, next_df, tick)

    flow_names = {item["name"] for item in restarted.buffer}
    assert {"FLOW_BTCUSD_0_A", "FLOW_BTCUSD_0_B", "FLOW_BTCUSD_1_A", "FLOW_BTCUSD_1_B"} <= flow_names
    history = list(restarted._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 2
    assert history[0]["event_kind"] == "BUY_PROBE"
    assert history[1]["event_kind"] == "SELL_WATCH"


def test_add_decision_flow_overlay_neutralizes_blocked_probe_visual_into_wait():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.32,
        "probe_pair_gap": 0.09,
        "quick_trace_state": "PROBE_WAIT",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_upper_sell_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    assert {"FLOW_XAUUSD_0_A", "FLOW_XAUUSD_0_B"} <= {item["name"] for item in painter.buffer}
    assert all(int(item["color"]) == Painter._FLOW_EVENT_COLORS["WAIT"] for item in _flow_items(painter, "FLOW_XAUUSD_0_"))


def test_add_decision_flow_overlay_respects_policy_directional_wait_toggle():
    painter = _policy_painter(semantics={"directional_wait_enabled": False})()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_edge_observe",
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "WAIT"


def test_add_decision_flow_overlay_respects_policy_neutral_block_guards_for_probe_wait():
    painter = _policy_painter(
        translation={
            "neutral_block_guards": [
                "outer_band_guard",
                "middle_sr_anchor_guard",
                "barrier_guard",
            ],
        }
    )()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.32,
        "probe_pair_gap": 0.09,
        "quick_trace_state": "PROBE_WAIT",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_upper_sell_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["XAUUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "SELL_PROBE"


def test_add_decision_flow_overlay_respects_policy_lower_probe_support_threshold():
    painter = _policy_painter(
        probe={
            "lower_min_support_by_side": {
                "BUY": 0.40,
                "SELL": 0.26,
            }
        }
    )()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_plan_ready": False,
        "probe_candidate_support": 0.31,
        "probe_pair_gap": 0.21,
        "quick_trace_state": "PROBE_WAIT",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert len(history) == 1
    assert history[0]["event_kind"] == "WAIT"


def test_flow_event_color_respects_policy_strength_alpha_override():
    strength_binding = {
        **Painter._FLOW_POLICY_V1["strength"]["visual_binding"],
        "alpha_by_level": {
            **Painter._FLOW_POLICY_V1["strength"]["visual_binding"]["alpha_by_level"],
            5: 0.20,
        },
    }
    painter_cls = _policy_painter(
        strength={"visual_binding": strength_binding}
    )

    assert Painter._flow_event_color("BUY_WAIT", 0.30, level=5) != painter_cls._flow_event_color("BUY_WAIT", 0.30, level=5)


def test_flow_event_strength_level_uses_common_bucket_edges():
    assert Painter._flow_event_strength_level(score=0.04) == 1
    assert Painter._flow_event_strength_level(score=0.11) == 3
    assert Painter._flow_event_strength_level(score=0.60) == 8
    assert Painter._flow_event_strength_level(score=0.90) == 10


def test_flow_event_signal_score_applies_readiness_gap_bonus_and_block_penalty():
    row = {
        "observe_confirm_v2": {
            "confidence": 0.24,
            "side": "BUY",
            "metadata": {
                "semantic_readiness_bridge_v1": {
                    "final": {
                        "buy_support": 0.42,
                        "sell_support": 0.05,
                    }
                },
                "edge_pair_law_v1": {
                    "pair_gap": 0.20,
                },
            },
        },
        "quick_trace_state": "PROBE_READY",
        "blocked_by": "outer_band_guard",
    }

    score = Painter._flow_event_signal_score(row, "BUY_WAIT", side="BUY")
    assert score == pytest.approx(0.34)


def test_flow_event_color_uses_strength_visual_binding_for_directional_events():
    base = Painter._FLOW_EVENT_COLORS["BUY_WAIT"]
    assert Painter._flow_event_color("BUY_WAIT", 0.04, level=1) == base
    assert Painter._flow_event_color("BUY_WAIT", 0.36, level=6) != base
    assert Painter._flow_event_color("BUY_WAIT", 0.30, level=5) != base


def test_flow_event_line_width_uses_strength_level_band():
    assert Painter._flow_event_line_width("BUY_WAIT", level=2) == 2
    assert Painter._flow_event_line_width("BUY_WAIT", level=6) == 3
    assert Painter._flow_event_line_width("BUY_WAIT", level=9) == 4
    assert Painter._flow_event_line_width("WAIT", level=9) == 2


def test_add_decision_flow_overlay_uses_reduced_default_marker_scale():
    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_observe",
            "confidence": 0.42,
        },
        "box_state": "LOWER",
        "bb_state": "MID",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    default_painter = Painter()
    full_scale_painter = _policy_painter(
        visual={
            "marker_time_scale": 1.0,
            "marker_price_scale": 1.0,
            "probe_marker_time_scale": 1.0,
            "probe_marker_price_scale": 1.0,
            "neutral_marker_time_scale": 1.0,
            "neutral_marker_price_scale": 1.0,
        }
    )()

    default_painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)
    full_scale_painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    default_item = _flow_items(default_painter, "FLOW_BTCUSD_0_")[0]
    full_item = _flow_items(full_scale_painter, "FLOW_BTCUSD_0_")[0]
    event_ts = list(default_painter._flow_history_by_symbol["BTCUSD"])[0]["ts"]
    event_price = list(default_painter._flow_history_by_symbol["BTCUSD"])[0]["price"]

    assert abs(int(default_item["t1"]) - int(event_ts)) < abs(int(full_item["t1"]) - int(event_ts))
    assert abs(float(default_item["p1"]) - float(event_price)) < abs(float(full_item["p1"]) - float(event_price))


def test_add_decision_flow_overlay_records_strength_level_and_width():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
            "confidence": 0.31,
            "metadata": {
                "semantic_readiness_bridge_v1": {
                    "final": {
                        "buy_support": 0.56,
                        "sell_support": 0.04,
                    }
                },
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BUY",
                    "pair_gap": 0.32,
                },
            },
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_candidate_support": 0.56,
        "probe_pair_gap": 0.32,
        "quick_trace_state": "PROBE_READY",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    history = list(painter._flow_history_by_symbol["BTCUSD"])
    assert history[0]["event_kind"] == "BUY_PROBE"
    assert history[0]["level"] == 9
    rollout_status = json.loads((Path(painter._rollout_status_filepath())).read_text(encoding="utf-8"))
    assert rollout_status["contract_version"] == "chart_flow_rollout_status_v1"
    assert rollout_status["inputs"]["distribution_report"]["available"] is True
    flow_lines = _flow_items(painter, "FLOW_BTCUSD_0_")
    assert flow_lines
    assert all(int(item["width"]) == 4 for item in flow_lines)


def test_add_decision_flow_overlay_passes_sampled_compare_reports_into_rollout_status(monkeypatch):
    comparison_history = {
        "BTCUSD": [
            {
                "ts": 100,
                "event_kind": "BUY_WAIT",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "level": 4,
                "score": 0.22,
            }
        ]
    }
    comparison_override_report = build_chart_flow_distribution_report(
        comparison_history,
        window_mode="candles",
        window_value=16,
        baseline_mode="comparison_override",
    )
    baseline_report = build_chart_flow_distribution_report(
        comparison_history,
        window_mode="candles",
        window_value=16,
        baseline_mode="baseline_only",
    )

    monkeypatch.setattr(
        "backend.trading.chart_painter.generate_and_write_chart_flow_baseline_compare_reports",
        lambda **kwargs: {
            "compare_override_report": comparison_override_report,
            "baseline_report": baseline_report,
            "compare_override_distribution_path": Path(
                os.environ["CHART_FLOW_DISTRIBUTION_PATH"]
            ).with_name("chart_flow_distribution_compare_override_latest.json"),
            "baseline_distribution_path": Path(
                os.environ["CHART_FLOW_DISTRIBUTION_PATH"]
            ).with_name("chart_flow_distribution_baseline_latest.json"),
        },
    )

    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)
    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
            "confidence": 0.31,
            "metadata": {
                "semantic_readiness_bridge_v1": {"final": {"buy_support": 0.56, "sell_support": 0.04}},
                "edge_pair_law_v1": {"context_label": "LOWER_EDGE", "winner_side": "BUY", "pair_gap": 0.32},
            },
        },
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_candidate_active": True,
        "probe_plan_active": True,
        "probe_candidate_support": 0.56,
        "probe_pair_gap": 0.32,
        "quick_trace_state": "PROBE_READY",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    rollout_status = json.loads(Path(painter._rollout_status_filepath()).read_text(encoding="utf-8"))
    assert rollout_status["inputs"]["comparison_override_distribution_report"]["available"] is True
    assert rollout_status["inputs"]["baseline_distribution_report"]["available"] is True
    assert rollout_status["inputs"]["comparison_override_distribution_report"]["baseline_mode"] == "comparison_override"


def test_save_writes_width_column_for_lines(tmp_path):
    painter = Painter()
    painter.save_dir = str(tmp_path)
    painter.buffer = [
        {
            "name": "FLOW_XAUUSD_0_A",
            "type": "LINE",
            "t1": 1,
            "p1": 100.0,
            "t2": 2,
            "p2": 101.0,
            "color": Painter._FLOW_EVENT_COLORS["SELL_WAIT"],
            "width": 3,
        }
    ]

    result = painter.save("XAUUSD")

    assert result["ok"] is True
    draw_path = tmp_path / "XAUUSD_draw_data.csv"
    payload = draw_path.read_text(encoding="ascii").strip()
    assert payload.endswith(",3")


def test_event_price_respects_policy_buy_default_anchor_ratio():
    painter_cls = _policy_painter(anchor={"buy_default_ratio": 0.10})
    df_1m = _build_frame("1M", "min")
    tick = SimpleNamespace(bid=100.0, ask=100.2)
    latest = df_1m.iloc[-1]
    open_ = float(latest["open"])
    close = float(latest["close"])
    high = float(latest["high"])
    low = float(latest["low"])
    span = max(high - low, abs(close - open_), 1e-9)
    expected = min(min(open_, close), low + (span * 0.10))

    assert painter_cls._event_price(df_1m, tick, side="BUY", event_kind="BUY_WAIT", reason="lower_rebound_observe") == pytest.approx(expected)


def test_resolve_flow_event_kind_respects_policy_directional_wait_readiness_gate():
    painter_cls = _policy_painter(
        readiness={
            "directional_wait_min_support_by_side": {"BUY": 0.08, "SELL": 0.08},
            "directional_wait_min_pair_gap_by_side": {"BUY": 0.05, "SELL": 0.05},
        }
    )
    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "middle_wait",
            "metadata": {
                "semantic_readiness_bridge_v1": {
                    "final": {
                        "buy_support": 0.06,
                        "sell_support": 0.02,
                    }
                },
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BUY",
                    "pair_gap": 0.03,
                },
            },
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    assert Painter._resolve_flow_event_kind("BTCUSD", row)[0] == "BUY_WAIT"
    assert painter_cls._resolve_flow_event_kind("BTCUSD", row)[0] == "WAIT"


def test_save_skips_unchanged_draw_payload(tmp_path):
    painter = Painter()
    painter.save_dir = str(tmp_path)
    painter.buffer = [
        {
            "name": "FLOW_XAUUSD_0_A",
            "type": "LINE",
            "t1": 1,
            "p1": 100.0,
            "t2": 2,
            "p2": 101.0,
            "color": Painter._FLOW_EVENT_COLORS["SELL_WAIT"],
        }
    ]

    first = painter.save("XAUUSD")
    second = painter.save("XAUUSD")

    assert first["ok"] is True
    assert second["ok"] is True
    assert any(bool(row.get("skipped_unchanged")) for row in second["file_results"])


def test_add_decision_flow_overlay_draws_single_double_triple_repeat_markers_from_consumer_display_score():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    observe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 4,
            "display_score": 0.74,
            "display_repeat_count": 1,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("BTCUSD", observe_row, df_all, tick)
    assert len(_flow_items(painter, "FLOW_BTCUSD_0_")) == 2

    probe_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_probe_observe",
            "display_strength_level": 7,
            "display_score": 0.85,
            "display_repeat_count": 2,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("XAUUSD", probe_row, df_all, tick)
    assert len(_flow_items(painter, "FLOW_XAUUSD_0_")) == 4

    ready_row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "BUY",
            "side": "BUY",
            "reason": "lower_rebound_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": True,
            "check_side": "BUY",
            "check_stage": "READY",
            "check_reason": "lower_rebound_confirm",
            "display_strength_level": 8,
            "display_score": 0.92,
            "display_repeat_count": 3,
        },
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }
    painter.add_decision_flow_overlay("NAS100", ready_row, df_all, tick)
    assert len(_flow_items(painter, "FLOW_NAS100_0_")) == 6


def test_add_decision_flow_overlay_renders_probe_guard_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "middle_sr_anchor_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "middle_sr_anchor_required_observe",
            "display_strength_level": 5,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "probe_guard_wait_as_wait_checks",
        },
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_nas_outer_band_probe_guard_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 5,
            "display_score": 0.75,
            "display_repeat_count": 1,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "probe_guard_wait_as_wait_checks",
        },
        "blocked_by": "outer_band_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_NAS100_0_")
    history = list(painter._flow_history_by_symbol["NAS100"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 1
    assert len(flow_items) == 2


def test_add_decision_flow_overlay_renders_btc_outer_band_probe_guard_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 5,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "probe_guard_wait_as_wait_checks",
        },
        "blocked_by": "outer_band_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_xau_upper_reject_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_mixed_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_mixed_confirm",
            "display_strength_level": 6,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "xau_upper_reject_mixed_guard_wait_as_wait_checks",
        },
        "blocked_by": "barrier_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_xau_middle_anchor_guard_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "middle_sr_anchor_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "check_reason": "middle_sr_anchor_required_observe",
            "display_strength_level": 5,
            "display_score": 0.75,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "xau_middle_anchor_guard_wait_as_wait_checks",
        },
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_xau_probe_energy_soft_block_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "BLOCKED",
            "check_reason": "upper_reject_probe_observe",
            "display_strength_level": 5,
            "display_score": 0.75,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "xau_upper_reject_probe_energy_soft_block_as_wait_checks",
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_upper_sell_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_xau_middle_anchor_probe_energy_soft_block_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "middle_sr_anchor_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "BLOCKED",
            "check_reason": "middle_sr_anchor_required_observe",
            "display_strength_level": 5,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "xau_middle_anchor_probe_energy_soft_block_as_wait_checks",
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_second_support_buy_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_xau_outer_band_probe_energy_soft_block_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "BLOCKED",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 5,
            "display_score": 0.75,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "xau_outer_band_probe_energy_soft_block_as_wait_checks",
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_upper_sell_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("XAUUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_XAUUSD_0_")
    history = list(painter._flow_history_by_symbol["XAUUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_btc_probe_energy_soft_block_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_probe_observe",
            "display_strength_level": 6,
            "display_score": 0.91,
            "display_repeat_count": 3,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "btc_lower_rebound_probe_energy_soft_block_as_wait_checks",
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 3
    assert len(flow_items) == 6
    assert any("_R2_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_btc_lower_probe_promotion_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_probe_observe",
            "display_strength_level": 6,
            "display_score": 0.91,
            "display_repeat_count": 3,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "btc_lower_probe_promotion_wait_as_wait_checks",
        },
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 3
    assert len(flow_items) == 6
    assert any("_R2_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_nas_upper_reject_probe_forecast_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_probe_observe",
            "display_strength_level": 6,
            "display_score": 0.86,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "nas_upper_reject_probe_forecast_wait_as_wait_checks",
        },
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_NAS100_0_")
    history = list(painter._flow_history_by_symbol["NAS100"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_nas_upper_reject_probe_promotion_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_probe_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_probe_observe",
            "display_strength_level": 6,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "nas_upper_reject_probe_promotion_wait_as_wait_checks",
        },
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_NAS100_0_")
    history = list(painter._flow_history_by_symbol["NAS100"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_renders_btc_structural_probe_energy_soft_block_wait_relief_as_neutral_wait_checks():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "BLOCKED",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 5,
            "display_score": 0.82,
            "display_repeat_count": 2,
            "chart_event_kind_hint": "WAIT",
            "chart_display_mode": "wait_check_repeat",
            "chart_display_reason": "btc_structural_probe_energy_soft_block_as_wait_checks",
        },
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    flow_items = _flow_items(painter, "FLOW_BTCUSD_0_")
    history = list(painter._flow_history_by_symbol["BTCUSD"])

    assert history[0]["event_kind"] == "WAIT"
    assert history[0]["side"] == ""
    assert history[0]["repeat_count"] == 2
    assert len(flow_items) == 4
    assert any("_R1_" in str(item["name"]) for item in flow_items)


def test_add_decision_flow_overlay_skips_hidden_nas_sell_outer_band_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "outer_band_reversal_support_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "check_reason": "outer_band_reversal_support_required_observe",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "sell_outer_band_wait_hide_without_probe",
        },
        "blocked_by": "outer_band_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert _flow_items(painter, "FLOW_NAS100_0_") == []
    assert not list(painter._flow_history_by_symbol.get("NAS100", []))


def test_add_decision_flow_overlay_skips_hidden_nas_sell_middle_anchor_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "middle_sr_anchor_required_observe",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "check_reason": "middle_sr_anchor_required_observe",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "nas_sell_middle_anchor_wait_hide_without_probe",
        },
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert _flow_items(painter, "FLOW_NAS100_0_") == []
    assert not list(painter._flow_history_by_symbol.get("NAS100", []))


def test_add_decision_flow_overlay_skips_hidden_nas_upper_reject_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_reject_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "check_reason": "upper_reject_confirm",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "nas_upper_reject_wait_hide_without_probe",
        },
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert _flow_items(painter, "FLOW_NAS100_0_") == []
    assert not list(painter._flow_history_by_symbol.get("NAS100", []))


def test_add_decision_flow_overlay_skips_hidden_nas_upper_break_fail_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "SELL",
            "reason": "upper_break_fail_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "check_reason": "upper_break_fail_confirm",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "nas_upper_break_fail_wait_hide_without_probe",
        },
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert _flow_items(painter, "FLOW_NAS100_0_") == []
    assert not list(painter._flow_history_by_symbol.get("NAS100", []))


def test_add_decision_flow_overlay_skips_hidden_nas_upper_reclaim_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "upper_reclaim_strength_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "upper_reclaim_strength_confirm",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "nas_upper_reclaim_wait_hide_without_probe",
        },
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("NAS100", row, df_all, tick)

    assert _flow_items(painter, "FLOW_NAS100_0_") == []
    assert not list(painter._flow_history_by_symbol.get("NAS100", []))


def test_add_decision_flow_overlay_skips_hidden_btc_lower_rebound_forecast_wait_without_probe():
    painter = Painter()
    df_all = {"1M": _build_frame("1M", "min")}
    tick = SimpleNamespace(bid=100.0, ask=100.2)

    row = {
        "observe_confirm_v2": {
            "state": "PROBE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_confirm",
        },
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_confirm",
            "display_strength_level": 0,
            "display_score": 0.0,
            "display_repeat_count": 0,
            "modifier_primary_reason": "btc_lower_rebound_forecast_wait_hide_without_probe",
        },
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
    }

    painter.add_decision_flow_overlay("BTCUSD", row, df_all, tick)

    assert _flow_items(painter, "FLOW_BTCUSD_0_") == []
    assert not list(painter._flow_history_by_symbol.get("BTCUSD", []))
