"""Materialize multi-surface objective and EV proxy specifications."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SURFACE_OBJECTIVE_SPEC_CONTRACT_VERSION = "surface_objective_spec_v1"
SURFACE_EV_PROXY_SPEC_CONTRACT_VERSION = "surface_ev_proxy_spec_v1"
SURFACE_ORDER = (
    "initial_entry_surface",
    "follow_through_surface",
    "continuation_hold_surface",
    "protective_exit_surface",
)
DEFAULT_MARKET_FAMILY_SYMBOLS = ("NAS100", "BTCUSD", "XAUUSD")

SURFACE_OBJECTIVE_SPEC_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "market_family",
    "surface_name",
    "objective_key",
    "objective_summary",
    "candidate_actions",
    "positive_ev_proxy",
    "do_nothing_ev_proxy",
    "false_positive_cost_proxy",
    "time_axis_fields",
    "distribution_gate_basis",
    "current_focus",
    "current_blocker_signature",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _json_loads_dict(text: object) -> dict[str, Any]:
    raw = _to_text(text)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _surface_spec_templates() -> dict[str, dict[str, Any]]:
    return {
        "initial_entry_surface": {
            "objective_key": "entry_forward_ev",
            "objective_summary": "Select first entry only when forward EV beats waiting and false-positive entry cost.",
            "candidate_actions": ["WAIT_MORE", "PROBE_ENTRY", "ENTER_NOW"],
            "positive_ev_proxy": "entry_forward_ev_proxy",
            "do_nothing_ev_proxy": "do_nothing_ev_proxy",
            "false_positive_cost_proxy": "entry_false_positive_cost_proxy",
            "time_axis_fields": ["bars_in_state", "time_since_last_relief"],
            "distribution_gate_basis": "market_family_scene_percentile",
        },
        "follow_through_surface": {
            "objective_key": "follow_through_extension_ev",
            "objective_summary": "Decide whether a direction already opened by the market is worth additional bounded participation.",
            "candidate_actions": ["WAIT_MORE", "WATCH", "PROBE_ENTRY", "ENTER_NOW"],
            "positive_ev_proxy": "follow_through_extension_ev_proxy",
            "do_nothing_ev_proxy": "wait_more_ev_proxy",
            "false_positive_cost_proxy": "late_follow_through_penalty_proxy",
            "time_axis_fields": ["time_since_breakout", "bars_in_state", "momentum_decay"],
            "distribution_gate_basis": "market_family_follow_through_percentile",
        },
        "continuation_hold_surface": {
            "objective_key": "runner_hold_ev",
            "objective_summary": "Preserve continuation and runner value when extension likelihood still dominates giveback risk.",
            "candidate_actions": ["LOCK_PROFIT", "PARTIAL_THEN_HOLD", "HOLD_RUNNER", "FULL_EXIT"],
            "positive_ev_proxy": "runner_hold_ev_proxy",
            "do_nothing_ev_proxy": "lock_profit_now_ev_proxy",
            "false_positive_cost_proxy": "runner_giveback_cost_proxy",
            "time_axis_fields": ["time_since_entry", "bars_in_state", "momentum_decay"],
            "distribution_gate_basis": "market_family_runner_hold_percentile",
        },
        "protective_exit_surface": {
            "objective_key": "protect_exit_loss_avoidance_ev",
            "objective_summary": "Exit only when not exiting is more dangerous than continuation or partial preservation.",
            "candidate_actions": ["WAIT_MORE", "PARTIAL_REDUCE", "EXIT_PROTECT"],
            "positive_ev_proxy": "protect_exit_loss_avoidance_ev_proxy",
            "do_nothing_ev_proxy": "hold_and_absorb_risk_ev_proxy",
            "false_positive_cost_proxy": "false_cut_regret_proxy",
            "time_axis_fields": ["time_since_entry", "bars_in_state", "momentum_decay"],
            "distribution_gate_basis": "market_family_protective_exit_percentile",
        },
    }


def _market_family_entry_focus(summary: Mapping[str, Any], symbol: str) -> str:
    focus_map = _json_loads_dict(summary.get("symbol_focus_map"))
    return _to_text(focus_map.get(symbol))


def _market_family_entry_blockers(summary: Mapping[str, Any], symbol: str) -> str:
    blocked_map = _json_loads_dict(summary.get("symbol_blocked_by_counts"))
    none_map = _json_loads_dict(summary.get("symbol_action_none_reason_counts"))
    observe_map = _json_loads_dict(summary.get("symbol_observe_reason_counts"))
    payload = {
        "blocked_by": blocked_map.get(symbol, {}),
        "action_none_reason": none_map.get(symbol, {}),
        "observe_reason": observe_map.get(symbol, {}),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _market_family_exit_focus(summary: Mapping[str, Any], symbol: str) -> str:
    focus_map = _json_loads_dict(summary.get("symbol_focus_map"))
    return _to_text(focus_map.get(symbol))


def _market_family_exit_blockers(summary: Mapping[str, Any], symbol: str) -> str:
    exit_map = _json_loads_dict(summary.get("symbol_auto_exit_reason_counts"))
    payload = {"auto_exit_reason": exit_map.get(symbol, {})}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _current_focus_for_surface(
    surface_name: str,
    symbol: str,
    entry_summary: Mapping[str, Any],
    exit_summary: Mapping[str, Any],
) -> str:
    if surface_name in {"initial_entry_surface", "follow_through_surface"}:
        return _market_family_entry_focus(entry_summary, symbol)
    return _market_family_exit_focus(exit_summary, symbol)


def _blocker_signature_for_surface(
    surface_name: str,
    symbol: str,
    entry_summary: Mapping[str, Any],
    exit_summary: Mapping[str, Any],
) -> str:
    if surface_name in {"initial_entry_surface", "follow_through_surface"}:
        return _market_family_entry_blockers(entry_summary, symbol)
    return _market_family_exit_blockers(exit_summary, symbol)


def build_surface_objective_ev_spec(
    runtime_status: Mapping[str, Any] | None,
    market_family_entry_audit: Mapping[str, Any] | None,
    market_family_exit_audit: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    semantic_live_config = dict(runtime.get("semantic_live_config", {}) or {})
    entry_payload = dict(market_family_entry_audit or {})
    exit_payload = dict(market_family_exit_audit or {})
    entry_summary = dict(entry_payload.get("summary", {}) or {})
    exit_summary = dict(exit_payload.get("summary", {}) or {})

    templates = _surface_spec_templates()
    rows: list[dict[str, Any]] = []
    for symbol in DEFAULT_MARKET_FAMILY_SYMBOLS:
        for surface_name in SURFACE_ORDER:
            template = templates[surface_name]
            rows.append(
                {
                    "observation_event_id": f"{SURFACE_OBJECTIVE_SPEC_CONTRACT_VERSION}:{generated_at}:{symbol}:{surface_name}",
                    "generated_at": generated_at,
                    "runtime_updated_at": _to_text(runtime.get("updated_at")),
                    "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
                    "market_family": symbol,
                    "surface_name": surface_name,
                    "objective_key": template["objective_key"],
                    "objective_summary": template["objective_summary"],
                    "candidate_actions": json.dumps(template["candidate_actions"], ensure_ascii=False),
                    "positive_ev_proxy": template["positive_ev_proxy"],
                    "do_nothing_ev_proxy": template["do_nothing_ev_proxy"],
                    "false_positive_cost_proxy": template["false_positive_cost_proxy"],
                    "time_axis_fields": json.dumps(template["time_axis_fields"], ensure_ascii=False),
                    "distribution_gate_basis": template["distribution_gate_basis"],
                    "current_focus": _current_focus_for_surface(surface_name, symbol, entry_summary, exit_summary),
                    "current_blocker_signature": _blocker_signature_for_surface(surface_name, symbol, entry_summary, exit_summary),
                }
            )

    frame = pd.DataFrame(rows, columns=SURFACE_OBJECTIVE_SPEC_COLUMNS)

    surface_summary = {
        "contract_version": SURFACE_OBJECTIVE_SPEC_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "market_family_count": len(DEFAULT_MARKET_FAMILY_SYMBOLS),
        "surface_count": len(SURFACE_ORDER),
        "row_count": int(len(frame)),
        "symbols": list(DEFAULT_MARKET_FAMILY_SYMBOLS),
        "surfaces": list(SURFACE_ORDER),
        "distribution_gate_principle": "cluster_relative_percentile_before_absolute_threshold",
        "do_nothing_mode": "explicit_ev_candidate",
        "market_adapter_principle": "shared_surface_plus_market_family_adapter",
        "recommended_next_action": "formalize_check_color_labels_and_time_axis",
        "surface_focus_map": {
            symbol: {
                surface_name: _current_focus_for_surface(surface_name, symbol, entry_summary, exit_summary)
                for surface_name in SURFACE_ORDER
            }
            for symbol in DEFAULT_MARKET_FAMILY_SYMBOLS
        },
    }

    ev_proxy_spec = {
        "contract_version": SURFACE_EV_PROXY_SPEC_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "do_nothing_global_policy": {
            "mode": "explicit_ev_candidate",
            "entry": "compare do_nothing_ev_proxy against enter_ev_proxy and probe_ev_proxy",
            "hold": "compare lock_profit_now_ev_proxy against runner_hold_ev_proxy and partial_then_hold_ev_proxy",
        },
        "surface_specs": {
            surface_name: {
                "objective_key": template["objective_key"],
                "candidate_actions": template["candidate_actions"],
                "positive_ev_proxy": template["positive_ev_proxy"],
                "do_nothing_ev_proxy": template["do_nothing_ev_proxy"],
                "false_positive_cost_proxy": template["false_positive_cost_proxy"],
                "time_axis_fields": template["time_axis_fields"],
                "distribution_gate_basis": template["distribution_gate_basis"],
            }
            for surface_name, template in templates.items()
        },
        "market_family_adapters": {
            symbol: {
                "entry_focus": _market_family_entry_focus(entry_summary, symbol),
                "exit_focus": _market_family_exit_focus(exit_summary, symbol),
            }
            for symbol in DEFAULT_MARKET_FAMILY_SYMBOLS
        },
        "failure_labels": [
            "failed_follow_through",
            "false_breakout",
            "early_exit_regret",
            "late_entry_chase_fail",
            "missed_good_wait_release",
        ],
        "recommended_next_action": "implement_mf3_check_color_label_formalization",
    }

    return frame, surface_summary, ev_proxy_spec


def render_surface_objective_ev_spec_markdown(
    summary: Mapping[str, Any],
    ev_proxy_spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    row = dict(summary or {})
    lines = [
        "# Surface Objective / EV Specification",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(row.get('rollout_mode'), 'disabled')}`",
        f"- market_family_count: `{int(_to_text(row.get('market_family_count'), '0'))}`",
        f"- surface_count: `{int(_to_text(row.get('surface_count'), '0'))}`",
        f"- row_count: `{int(_to_text(row.get('row_count'), '0'))}`",
        f"- distribution_gate_principle: `{_to_text(row.get('distribution_gate_principle'))}`",
        f"- do_nothing_mode: `{_to_text(row.get('do_nothing_mode'))}`",
        f"- market_adapter_principle: `{_to_text(row.get('market_adapter_principle'))}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
        "",
        "## Surface EV Proxy Spec",
        "",
        f"- failure_labels: `{json.dumps(list(ev_proxy_spec.get('failure_labels', [])), ensure_ascii=False)}`",
        f"- market_family_adapters: `{json.dumps(dict(ev_proxy_spec.get('market_family_adapters', {}) or {}), ensure_ascii=False, sort_keys=True)}`",
    ]
    if frame is None or frame.empty:
        lines.extend(["", "_No surface objective rows materialized._"])
        return "\n".join(lines) + "\n"

    for surface_name in SURFACE_ORDER:
        surface_frame = frame.loc[frame["surface_name"] == surface_name].copy()
        if surface_frame.empty:
            continue
        first = surface_frame.iloc[0].to_dict()
        lines.extend(
            [
                "",
                f"## {surface_name}",
                "",
                f"- objective_key: `{_to_text(first.get('objective_key'))}`",
                f"- positive_ev_proxy: `{_to_text(first.get('positive_ev_proxy'))}`",
                f"- do_nothing_ev_proxy: `{_to_text(first.get('do_nothing_ev_proxy'))}`",
                f"- false_positive_cost_proxy: `{_to_text(first.get('false_positive_cost_proxy'))}`",
                f"- time_axis_fields: `{_to_text(first.get('time_axis_fields'))}`",
            ]
        )
    return "\n".join(lines) + "\n"
