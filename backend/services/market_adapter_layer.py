"""Market-family adapter layer over shared surfaces."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


MARKET_ADAPTER_LAYER_CONTRACT_VERSION = "market_adapter_layer_v1"

MARKET_ADAPTER_LAYER_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "market_family",
    "surface_name",
    "adapter_id",
    "adapter_mode",
    "adapter_priority",
    "adapter_scope",
    "objective_key",
    "positive_ev_proxy",
    "do_nothing_ev_proxy",
    "false_positive_cost_proxy",
    "time_axis_fields",
    "entry_focus",
    "exit_focus",
    "current_focus",
    "dominant_failure_label",
    "failure_label_counts",
    "distribution_combined_gate",
    "distribution_combined_gate_counts",
    "dominant_candidate_source",
    "distribution_source_counts",
    "market_adapter_feature_flags",
    "recommended_bias_action",
    "adapter_note",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_json_counts(value: object) -> dict[str, int]:
    if isinstance(value, Mapping):
        return {str(k): int(v) for k, v in value.items()}
    raw = _to_text(value)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return {str(k): int(v) for k, v in dict(parsed).items()} if isinstance(parsed, Mapping) else {}


def _to_json_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_to_text(item) for item in value if _to_text(item)]
    raw = _to_text(value)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return [token.strip() for token in raw.split(",") if token.strip()]
    if isinstance(parsed, list):
        return [_to_text(item) for item in parsed if _to_text(item)]
    return []


def _stable_json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True)


def _dominant_key(counts: Mapping[str, int]) -> str:
    if not counts:
        return ""
    return max(counts.items(), key=lambda item: (int(item[1]), str(item[0])))[0]


def _surface_failure_focus(surface_name: str) -> set[str]:
    surface = _to_text(surface_name)
    if surface == "initial_entry_surface":
        return {"missed_good_wait_release", "late_entry_chase_fail", "false_breakout"}
    if surface == "follow_through_surface":
        return {"failed_follow_through", "false_breakout", "missed_good_wait_release"}
    if surface == "continuation_hold_surface":
        return {"early_exit_regret", "failed_follow_through"}
    if surface == "protective_exit_surface":
        return {"early_exit_regret", "false_breakout"}
    return set()


def _adapter_mode(symbol: str, surface_name: str, current_focus: str) -> str:
    symbol_text = _to_text(symbol).upper()
    surface_text = _to_text(surface_name)
    focus_text = _to_text(current_focus)
    if symbol_text == "XAUUSD" and surface_text == "initial_entry_surface":
        return "xau_initial_entry_selective_adapter"
    if symbol_text == "XAUUSD" and surface_text == "follow_through_surface":
        return "xau_follow_through_relief_adapter"
    if symbol_text == "XAUUSD" and surface_text == "continuation_hold_surface":
        return "xau_runner_preservation_adapter"
    if symbol_text == "XAUUSD" and surface_text == "protective_exit_surface":
        return "xau_protective_exit_balance_adapter"
    if symbol_text == "BTCUSD" and surface_text == "initial_entry_surface":
        return "btc_observe_relief_adapter"
    if symbol_text == "BTCUSD" and surface_text == "follow_through_surface":
        return "btc_follow_through_balance_adapter"
    if symbol_text == "NAS100" and surface_text == "initial_entry_surface":
        return "nas_conflict_observe_adapter"
    if symbol_text == "NAS100" and surface_text == "follow_through_surface":
        return "nas_follow_through_conflict_adapter"
    if "runner" in focus_text:
        return "runner_preservation_adapter"
    if "protective_exit" in focus_text:
        return "protective_exit_balance_adapter"
    if "follow_through" in focus_text:
        return "follow_through_relief_adapter"
    if "observe" in focus_text or "probe" in focus_text:
        return "observe_probe_adapter"
    return "shared_surface_market_adapter"


def _recommended_bias_action(
    *,
    surface_name: str,
    current_focus: str,
    dominant_failure_label: str,
    distribution_combined_gate: str,
) -> str:
    surface_text = _to_text(surface_name)
    focus_text = _to_text(current_focus)
    failure_text = _to_text(dominant_failure_label)
    gate_text = _to_text(distribution_combined_gate)
    if surface_text == "initial_entry_surface" and "xau" in focus_text.lower():
        return "bias_initial_entry_selectivity"
    if surface_text == "follow_through_surface" and gate_text == "PROBE_ELIGIBLE":
        return "bias_probe_relief"
    if surface_text == "continuation_hold_surface":
        return "bias_runner_hold"
    if surface_text == "protective_exit_surface" and "protective_exit_overfire" in focus_text:
        return "bias_protective_dampen"
    if failure_text == "failed_follow_through":
        return "bias_follow_through_capture"
    if failure_text == "missed_good_wait_release":
        return "bias_release_wait"
    if failure_text == "early_exit_regret":
        return "bias_runner_preserve"
    return "bias_neutral"


def _focus_maps(entry_audit_payload: Mapping[str, Any] | None, exit_audit_payload: Mapping[str, Any] | None) -> tuple[dict[str, str], dict[str, str], str]:
    entry_summary = dict((entry_audit_payload or {}).get("summary", {}) or {})
    exit_summary = dict((exit_audit_payload or {}).get("summary", {}) or {})
    entry_focus_map = {str(k): _to_text(v) for k, v in _to_json_counts({}).items()}
    # symbol_focus_map is stored as json object string in summary
    raw_entry_focus = entry_summary.get("symbol_focus_map")
    raw_exit_focus = exit_summary.get("symbol_focus_map")
    try:
        entry_focus_map = {str(k): _to_text(v) for k, v in json.loads(raw_entry_focus or "{}").items()}
    except Exception:
        entry_focus_map = {}
    try:
        exit_focus_map = {str(k): _to_text(v) for k, v in json.loads(raw_exit_focus or "{}").items()}
    except Exception:
        exit_focus_map = {}
    runtime_updated_at = _to_text(entry_summary.get("runtime_updated_at") or exit_summary.get("runtime_updated_at"))
    return entry_focus_map, exit_focus_map, runtime_updated_at


def _failure_rows(failure_payload: Mapping[str, Any] | None) -> pd.DataFrame:
    rows = list((failure_payload or {}).get("rows", []) or [])
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in ("market_family", "surface_label_family", "failure_label"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["surface_label_family"] = frame["surface_label_family"].fillna("").astype(str)
    frame["failure_label"] = frame["failure_label"].fillna("").astype(str)
    return frame


def _distribution_rows(distribution_payload: Mapping[str, Any] | None) -> pd.DataFrame:
    rows = list((distribution_payload or {}).get("rows", []) or [])
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in ("market_family", "surface_family", "combined_gate_state", "candidate_source"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["surface_family"] = frame["surface_family"].fillna("").astype(str)
    frame["combined_gate_state"] = frame["combined_gate_state"].fillna("").astype(str)
    frame["candidate_source"] = frame["candidate_source"].fillna("").astype(str)
    return frame


def _surface_rows(surface_spec_payload: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = dict(surface_spec_payload or {})
    return list(payload.get("rows", []) or []), dict(payload.get("summary", {}) or {})


def build_market_adapter_layer(
    market_family_entry_audit_payload: Mapping[str, Any] | None,
    market_family_exit_audit_payload: Mapping[str, Any] | None,
    surface_objective_spec_payload: Mapping[str, Any] | None,
    failure_label_harvest_payload: Mapping[str, Any] | None,
    distribution_promotion_gate_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    entry_focus_map, exit_focus_map, runtime_updated_at = _focus_maps(
        market_family_entry_audit_payload,
        market_family_exit_audit_payload,
    )
    surface_rows, surface_summary = _surface_rows(surface_objective_spec_payload)
    failure_frame = _failure_rows(failure_label_harvest_payload)
    distribution_frame = _distribution_rows(distribution_promotion_gate_payload)

    symbols = list(surface_summary.get("symbols", []) or []) or sorted(set(entry_focus_map) | set(exit_focus_map))
    summary: dict[str, Any] = {
        "contract_version": MARKET_ADAPTER_LAYER_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": runtime_updated_at,
        "market_adapter_principle": _to_text(
            surface_summary.get("market_adapter_principle"),
            "shared_surface_plus_market_family_adapter",
        ),
        "market_family_count": len(symbols),
        "surface_count": len({_to_text(row.get("surface_name")) for row in surface_rows if _to_text(row.get("surface_name"))}),
        "row_count": 0,
        "adapter_mode_counts": "{}",
        "recommended_bias_action_counts": "{}",
        "dominant_failure_label_counts": "{}",
        "distribution_combined_gate_counts": "{}",
        "recommended_next_action": "collect_more_market_adapter_inputs",
    }
    if not surface_rows or not symbols:
        return pd.DataFrame(columns=MARKET_ADAPTER_LAYER_COLUMNS), summary

    rows: list[dict[str, Any]] = []
    direct_symbol_rows = all(_to_text(surface_row.get("market_family")) for surface_row in surface_rows)
    adapter_rows: list[tuple[str, dict[str, Any]]] = []
    if direct_symbol_rows:
        for surface_row in surface_rows:
            adapter_rows.append((_to_text(surface_row.get("market_family")).upper(), surface_row))
    else:
        for symbol in symbols:
            symbol_text = _to_text(symbol).upper()
            for surface_row in surface_rows:
                adapter_rows.append((symbol_text, surface_row))

    for symbol_text, surface_row in adapter_rows:
        entry_focus = _to_text(entry_focus_map.get(symbol_text))
        exit_focus = _to_text(exit_focus_map.get(symbol_text))
        symbol_failure_frame = failure_frame.loc[failure_frame["market_family"] == symbol_text].copy() if not failure_frame.empty else pd.DataFrame()
        symbol_distribution_frame = distribution_frame.loc[
            distribution_frame["market_family"] == symbol_text
        ].copy() if not distribution_frame.empty else pd.DataFrame()
        surface_name = _to_text(surface_row.get("surface_name"))
        current_focus = _to_text(surface_row.get("current_focus")) or (
            entry_focus if surface_name in {"initial_entry_surface", "follow_through_surface"} else exit_focus
        )
        relevant_failures = _surface_failure_focus(surface_name)
        exact_failure_frame = symbol_failure_frame.loc[
            symbol_failure_frame["surface_label_family"] == surface_name
        ].copy() if not symbol_failure_frame.empty else pd.DataFrame()
        if exact_failure_frame.empty and relevant_failures:
            exact_failure_frame = symbol_failure_frame.loc[
                symbol_failure_frame["failure_label"].isin(relevant_failures)
            ].copy() if not symbol_failure_frame.empty else pd.DataFrame()
        failure_counts = (
            exact_failure_frame["failure_label"].value_counts().to_dict()
            if not exact_failure_frame.empty
            else {}
        )
        failure_counts = {str(k): int(v) for k, v in failure_counts.items()}
        dominant_failure_label = _dominant_key(failure_counts)

        surface_distribution = symbol_distribution_frame.loc[
            symbol_distribution_frame["surface_family"] == surface_name
        ].copy() if not symbol_distribution_frame.empty else pd.DataFrame()
        combined_gate_counts = (
            surface_distribution["combined_gate_state"].value_counts().to_dict()
            if not surface_distribution.empty
            else {}
        )
        combined_gate_counts = {str(k): int(v) for k, v in combined_gate_counts.items()}
        distribution_combined_gate = _dominant_key(combined_gate_counts)
        source_counts = (
            surface_distribution["candidate_source"].value_counts().to_dict()
            if not surface_distribution.empty
            else {}
        )
        source_counts = {str(k): int(v) for k, v in source_counts.items()}
        dominant_candidate_source = _dominant_key(source_counts)

        adapter_mode = _adapter_mode(symbol_text, surface_name, current_focus)
        recommended_bias_action = _recommended_bias_action(
            surface_name=surface_name,
            current_focus=current_focus,
            dominant_failure_label=dominant_failure_label,
            distribution_combined_gate=distribution_combined_gate,
        )
        feature_flags = {
            "use_market_family_feature": True,
            "use_distribution_relative_gate": surface_name in {"initial_entry_surface", "follow_through_surface"},
            "use_failure_feedback": bool(failure_counts),
            "use_time_axis": bool(_to_json_list(surface_row.get("time_axis_fields"))),
            "use_do_nothing_ev": True,
            "bounded_adapter": True,
            "allow_live_override": False,
        }

        rows.append(
            {
                "observation_event_id": f"{MARKET_ADAPTER_LAYER_CONTRACT_VERSION}:{symbol_text}:{surface_name}",
                "generated_at": generated_at,
                "runtime_updated_at": runtime_updated_at,
                "market_family": symbol_text,
                "surface_name": surface_name,
                "adapter_id": f"{symbol_text.lower()}::{surface_name}",
                "adapter_mode": adapter_mode,
                "adapter_priority": "P1" if surface_name in {"initial_entry_surface", "follow_through_surface"} else "P2",
                "adapter_scope": "shared_surface_plus_market_family_adapter",
                "objective_key": _to_text(surface_row.get("objective_key")),
                "positive_ev_proxy": _to_text(surface_row.get("positive_ev_proxy")),
                "do_nothing_ev_proxy": _to_text(surface_row.get("do_nothing_ev_proxy")),
                "false_positive_cost_proxy": _to_text(surface_row.get("false_positive_cost_proxy")),
                "time_axis_fields": _stable_json({"fields": _to_json_list(surface_row.get("time_axis_fields"))}),
                "entry_focus": entry_focus,
                "exit_focus": exit_focus,
                "current_focus": current_focus,
                "dominant_failure_label": dominant_failure_label,
                "failure_label_counts": _stable_json(failure_counts),
                "distribution_combined_gate": distribution_combined_gate,
                "distribution_combined_gate_counts": _stable_json(combined_gate_counts),
                "dominant_candidate_source": dominant_candidate_source,
                "distribution_source_counts": _stable_json(source_counts),
                "market_adapter_feature_flags": _stable_json(feature_flags),
                "recommended_bias_action": recommended_bias_action,
                "adapter_note": _to_text(surface_row.get("current_blocker_signature")) or current_focus,
            }
        )

    frame = pd.DataFrame(rows, columns=MARKET_ADAPTER_LAYER_COLUMNS)
    if frame.empty:
        return frame, summary

    summary["market_family_count"] = int(frame["market_family"].nunique())
    summary["surface_count"] = int(frame["surface_name"].nunique())
    summary["row_count"] = int(len(frame))
    summary["adapter_mode_counts"] = _stable_json({str(k): int(v) for k, v in frame["adapter_mode"].value_counts().to_dict().items()})
    summary["recommended_bias_action_counts"] = _stable_json({str(k): int(v) for k, v in frame["recommended_bias_action"].value_counts().to_dict().items()})
    summary["dominant_failure_label_counts"] = _stable_json(_to_json_counts(frame["dominant_failure_label"].replace("", pd.NA).dropna().value_counts().to_dict()))
    summary["distribution_combined_gate_counts"] = _stable_json(_to_json_counts(frame["distribution_combined_gate"].replace("", pd.NA).dropna().value_counts().to_dict()))
    summary["recommended_next_action"] = "proceed_to_mf15_preview_dataset_export"
    return frame, summary


def render_market_adapter_layer_markdown(summary: Mapping[str, Any] | None, frame: pd.DataFrame | None) -> str:
    payload = dict(summary or {})
    rows = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    lines = [
        "# Market Adapter Layer",
        "",
        f"- generated_at: `{_to_text(payload.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(payload.get('runtime_updated_at'))}`",
        f"- market_adapter_principle: `{_to_text(payload.get('market_adapter_principle'))}`",
        f"- market_family_count: `{int(payload.get('market_family_count') or 0)}`",
        f"- surface_count: `{int(payload.get('surface_count') or 0)}`",
        f"- row_count: `{int(payload.get('row_count') or 0)}`",
        f"- recommended_next_action: `{_to_text(payload.get('recommended_next_action'))}`",
        "",
        "## Counts",
        "",
        f"- adapter_mode_counts: `{_to_text(payload.get('adapter_mode_counts'), '{}')}`",
        f"- recommended_bias_action_counts: `{_to_text(payload.get('recommended_bias_action_counts'), '{}')}`",
        f"- dominant_failure_label_counts: `{_to_text(payload.get('dominant_failure_label_counts'), '{}')}`",
        f"- distribution_combined_gate_counts: `{_to_text(payload.get('distribution_combined_gate_counts'), '{}')}`",
    ]
    if rows.empty:
        lines.extend(["", "## Adapter Rows", "", "- no rows materialized"])
        return "\n".join(lines) + "\n"
    lines.extend(["", "## Adapter Rows", ""])
    for _, row in rows.head(12).iterrows():
        lines.append(
            "- "
            + f"{_to_text(row.get('market_family'))} | "
            + f"`{_to_text(row.get('surface_name'))}` | "
            + f"mode={_to_text(row.get('adapter_mode'))} | "
            + f"focus={_to_text(row.get('current_focus')) or 'none'} | "
            + f"failure={_to_text(row.get('dominant_failure_label')) or 'none'} | "
            + f"gate={_to_text(row.get('distribution_combined_gate')) or 'none'} | "
            + f"bias={_to_text(row.get('recommended_bias_action'))}"
        )
    return "\n".join(lines) + "\n"
