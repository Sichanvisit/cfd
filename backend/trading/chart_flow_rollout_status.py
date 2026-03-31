from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from backend.trading.chart_flow_distribution import load_flow_history_by_symbol


_PRIMARY_EVENT_KINDS = (
    "BUY_WAIT",
    "SELL_WAIT",
    "BUY_PROBE",
    "SELL_PROBE",
    "BUY_READY",
    "SELL_READY",
    "WAIT",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_chart_flow_rollout_status_output_path() -> Path:
    raw_path = str(os.getenv("CHART_FLOW_ROLLOUT_STATUS_PATH", "") or "").strip()
    if raw_path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        return path.resolve()
    return (_project_root() / "data" / "analysis" / "chart_flow_rollout_status_latest.json").resolve()


def resolve_chart_flow_baseline_distribution_input_path() -> Path | None:
    raw_path = str(os.getenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", "") or "").strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = (_project_root() / path).resolve()
    return path.resolve()


def resolve_chart_flow_compare_override_distribution_input_path() -> Path | None:
    raw_path = str(os.getenv("CHART_FLOW_COMPARE_OVERRIDE_DISTRIBUTION_PATH", "") or "").strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = (_project_root() / path).resolve()
    return path.resolve()


def resolve_runtime_status_input_path() -> Path:
    return (_project_root() / "data" / "runtime_status.json").resolve()


def resolve_runtime_status_detail_input_path() -> Path:
    return (_project_root() / "data" / "runtime_status.detail.json").resolve()


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(parsed) if parsed == parsed else float(default)


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def _load_json_document(path: str | Path | None):
    if not path:
        return None
    doc_path = Path(path).resolve()
    if not doc_path.exists():
        return None
    try:
        raw_text = doc_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except (ValueError, TypeError):
        return None


def _presence(summary: dict | None) -> dict:
    return dict((summary or {}).get("presence", {}) or {})


def _event_counts(summary: dict | None) -> dict:
    return dict((summary or {}).get("event_counts", {}) or {})


def _class_presence(counts: dict | None) -> dict[str, int]:
    counts = dict(counts or {})
    return {
        "directional_wait": int(counts.get("BUY_WAIT", 0) or 0) + int(counts.get("SELL_WAIT", 0) or 0),
        "probe": int(counts.get("BUY_PROBE", 0) or 0) + int(counts.get("SELL_PROBE", 0) or 0),
        "ready": int(counts.get("BUY_READY", 0) or 0) + int(counts.get("SELL_READY", 0) or 0),
        "neutral_wait": int(counts.get("WAIT", 0) or 0),
    }


def _stage_result(
    *,
    key: str,
    label: str,
    status: str,
    advance_gate: bool,
    stop_gate: bool,
    summary: str,
    checks: dict | None = None,
    metrics: dict | None = None,
) -> dict:
    return {
        "stage_key": str(key),
        "label": str(label),
        "status": str(status),
        "advance_gate": bool(advance_gate),
        "stop_gate": bool(stop_gate),
        "summary": str(summary or ""),
        "checks": dict(checks or {}),
        "metrics": dict(metrics or {}),
    }


def _history_schema_summary(history_by_symbol: dict[str, list[dict]] | None) -> dict:
    payload = dict(history_by_symbol or {})
    per_symbol = {}
    symbols_with_zone = 0
    symbols_with_level = 0
    symbols_with_probe_scene = 0
    symbols_with_position_count = 0

    for symbol, events in sorted(payload.items()):
        rows = [dict(event) for event in list(events or []) if isinstance(event, dict)]
        total_events = len(rows)
        level_events = sum(1 for event in rows if event.get("level") not in (None, "", 0, "0"))
        zone_events = sum(
            1
            for event in rows
            if str(event.get("box_state", "") or "").strip() or str(event.get("bb_state", "") or "").strip()
        )
        probe_scene_events = sum(1 for event in rows if str(event.get("probe_scene_id", "") or "").strip())
        position_count_events = sum(1 for event in rows if "my_position_count" in event and event.get("my_position_count") is not None)
        if zone_events > 0:
            symbols_with_zone += 1
        if level_events > 0:
            symbols_with_level += 1
        if probe_scene_events > 0:
            symbols_with_probe_scene += 1
        if position_count_events > 0:
            symbols_with_position_count += 1
        per_symbol[_normalize_symbol(symbol)] = {
            "event_count": int(total_events),
            "zone_coverage_count": int(zone_events),
            "level_coverage_count": int(level_events),
            "probe_scene_coverage_count": int(probe_scene_events),
            "position_count_coverage_count": int(position_count_events),
        }

    return {
        "symbol_count": int(len(per_symbol)),
        "symbols_with_zone": int(symbols_with_zone),
        "symbols_with_level": int(symbols_with_level),
        "symbols_with_probe_scene": int(symbols_with_probe_scene),
        "symbols_with_position_count": int(symbols_with_position_count),
        "per_symbol": per_symbol,
    }


def _comparison_summary(override_report: dict | None, baseline_report: dict | None) -> dict:
    override_symbols = dict((override_report or {}).get("symbols", {}) or {})
    baseline_symbols = dict((baseline_report or {}).get("symbols", {}) or {})
    if not override_symbols or not baseline_symbols:
        return {
            "available": False,
            "comparable_symbol_count": 0,
            "directional_wait_regression_symbols": [],
            "probe_regression_symbols": [],
            "ready_regression_symbols": [],
            "presence_delta_by_symbol": {},
        }

    comparable = sorted(set(override_symbols.keys()) & set(baseline_symbols.keys()))
    directional_wait_regression_symbols = []
    probe_regression_symbols = []
    ready_regression_symbols = []
    presence_delta_by_symbol = {}

    for symbol in comparable:
        override_counts = _class_presence(_event_counts(override_symbols.get(symbol)))
        baseline_counts = _class_presence(_event_counts(baseline_symbols.get(symbol)))
        baseline_presence = _presence(baseline_symbols.get(symbol))
        override_presence = _presence(override_symbols.get(symbol))
        if int(baseline_counts["directional_wait"]) > 0 and int(override_counts["directional_wait"]) <= 0:
            directional_wait_regression_symbols.append(symbol)
        if int(baseline_counts["probe"]) > 0 and int(override_counts["probe"]) <= 0:
            probe_regression_symbols.append(symbol)
        if int(baseline_counts["ready"]) > 0 and int(override_counts["ready"]) <= 0:
            ready_regression_symbols.append(symbol)
        presence_delta_by_symbol[symbol] = {
            "buy_presence_delta": round(
                _safe_float(override_presence.get("buy_presence_ratio", 0.0))
                - _safe_float(baseline_presence.get("buy_presence_ratio", 0.0)),
                6,
            ),
            "sell_presence_delta": round(
                _safe_float(override_presence.get("sell_presence_ratio", 0.0))
                - _safe_float(baseline_presence.get("sell_presence_ratio", 0.0)),
                6,
            ),
            "neutral_ratio_delta": round(
                _safe_float(override_presence.get("neutral_ratio", 0.0))
                - _safe_float(baseline_presence.get("neutral_ratio", 0.0)),
                6,
            ),
        }

    return {
        "available": True,
        "comparable_symbol_count": int(len(comparable)),
        "directional_wait_regression_symbols": directional_wait_regression_symbols,
        "probe_regression_symbols": probe_regression_symbols,
        "ready_regression_symbols": ready_regression_symbols,
        "presence_delta_by_symbol": presence_delta_by_symbol,
    }


def _stage_semantic_baseline(report: dict | None) -> dict:
    if not isinstance(report, dict):
        return _stage_result(
            key="stage_a_semantic_baseline",
            label="Stage A Semantic Baseline",
            status="pending",
            advance_gate=False,
            stop_gate=False,
            summary="distribution report unavailable",
        )

    symbols = dict(report.get("symbols", {}) or {})
    flat_exit_count = _safe_int(dict(report.get("anomalies", {}) or {}).get("flat_exit_count", 0))
    directional_wait_symbol_count = sum(
        1
        for payload in symbols.values()
        if int(_event_counts(payload).get("BUY_WAIT", 0) or 0) + int(_event_counts(payload).get("SELL_WAIT", 0) or 0) > 0
    )
    checks = {
        "flat_exit_clear": bool(flat_exit_count == 0),
        "directional_wait_present": bool(directional_wait_symbol_count > 0),
    }
    if flat_exit_count > 0:
        status = "stop"
        summary = f"flat exit anomaly detected ({flat_exit_count})"
    elif directional_wait_symbol_count <= 0:
        status = "hold"
        summary = "directional wait coverage not observed yet"
    else:
        status = "advance"
        summary = f"directional wait observed in {directional_wait_symbol_count} symbol(s)"
    return _stage_result(
        key="stage_a_semantic_baseline",
        label="Stage A Semantic Baseline",
        status=status,
        advance_gate=bool(status == "advance"),
        stop_gate=bool(status == "stop"),
        summary=summary,
        checks=checks,
        metrics={
            "symbol_count": int(len(symbols)),
            "directional_wait_symbol_count": int(directional_wait_symbol_count),
            "flat_exit_count": int(flat_exit_count),
        },
    )


def _stage_common_threshold(report: dict | None) -> dict:
    if not isinstance(report, dict):
        return _stage_result(
            key="stage_b_common_threshold",
            label="Stage B Common Threshold",
            status="pending",
            advance_gate=False,
            stop_gate=False,
            summary="distribution report unavailable",
        )

    symbols = dict(report.get("symbols", {}) or {})
    global_presence = dict(dict(report.get("global_summary", {}) or {}).get("presence", {}) or {})
    anomalies = dict(report.get("anomalies", {}) or {})
    total_events = _safe_int(global_presence.get("total_events", 0))
    zone_coverage_symbols = 0
    for payload in symbols.values():
        zone_counts = dict(payload.get("zone_counts", {}) or {})
        covered = False
        for zone_name in ("LOWER", "MIDDLE", "UPPER"):
            zone_payload = dict(zone_counts.get(zone_name, {}) or {})
            if sum(_safe_int(zone_payload.get(kind, 0)) for kind in _PRIMARY_EVENT_KINDS) > 0:
                covered = True
                break
        if covered:
            zone_coverage_symbols += 1
    extreme_imbalance_symbols = list(anomalies.get("extreme_imbalance_symbols", []) or [])
    symbol_count = len(symbols)
    all_symbols_extreme = bool(symbol_count > 0 and len(extreme_imbalance_symbols) >= symbol_count)
    checks = {
        "distribution_available": bool(total_events > 0),
        "zone_data_available": bool(zone_coverage_symbols > 0),
        "all_symbols_extreme_imbalance": bool(all_symbols_extreme),
    }
    if total_events <= 0:
        status = "pending"
        summary = "no distribution events available yet"
    elif zone_coverage_symbols <= 0:
        status = "hold"
        summary = "zone coverage is still missing from latest histories"
    elif all_symbols_extreme:
        status = "hold"
        summary = "all tracked symbols are in extreme imbalance state"
    else:
        status = "advance"
        summary = f"zone coverage observed in {zone_coverage_symbols} / {symbol_count} symbol(s)"
    return _stage_result(
        key="stage_b_common_threshold",
        label="Stage B Common Threshold",
        status=status,
        advance_gate=bool(status == "advance"),
        stop_gate=False,
        summary=summary,
        checks=checks,
        metrics={
            "symbol_count": int(symbol_count),
            "total_events": int(total_events),
            "zone_coverage_symbols": int(zone_coverage_symbols),
            "extreme_imbalance_symbol_count": int(len(extreme_imbalance_symbols)),
        },
    )


def _stage_strength_rollout(report: dict | None) -> dict:
    if not isinstance(report, dict):
        return _stage_result(
            key="stage_c_strength_rollout",
            label="Stage C Strength Rollout",
            status="pending",
            advance_gate=False,
            stop_gate=False,
            summary="distribution report unavailable",
        )

    symbols = dict(report.get("symbols", {}) or {})
    strength_coverage_symbols = 0
    unique_levels = set()
    for payload in symbols.values():
        level_counts = dict(payload.get("strength_level_counts", {}) or {})
        if level_counts:
            strength_coverage_symbols += 1
            unique_levels.update(str(level) for level in level_counts.keys())
    checks = {
        "strength_data_available": bool(strength_coverage_symbols > 0),
        "multiple_strength_levels_present": bool(len(unique_levels) >= 2),
    }
    if strength_coverage_symbols <= 0:
        status = "hold"
        summary = "fresh histories with strength levels are not accumulated yet"
    elif len(unique_levels) < 2:
        status = "hold"
        summary = "strength data exists but level spread is still too narrow"
    else:
        status = "advance"
        summary = f"strength coverage observed in {strength_coverage_symbols} symbol(s)"
    return _stage_result(
        key="stage_c_strength_rollout",
        label="Stage C Strength Rollout",
        status=status,
        advance_gate=bool(status == "advance"),
        stop_gate=False,
        summary=summary,
        checks=checks,
        metrics={
            "symbol_count": int(len(symbols)),
            "strength_coverage_symbols": int(strength_coverage_symbols),
            "unique_strength_level_count": int(len(unique_levels)),
        },
    )


def _stage_override_restore(override_report: dict | None, baseline_report: dict | None) -> tuple[dict, dict]:
    comparison = _comparison_summary(override_report, baseline_report)
    if not isinstance(override_report, dict):
        return (
            _stage_result(
                key="stage_d_override_restore",
                label="Stage D Symbol Override Restore",
                status="pending",
                advance_gate=False,
                stop_gate=False,
                summary="override distribution report unavailable",
            ),
            comparison,
        )
    if not comparison.get("available", False):
        return (
            _stage_result(
                key="stage_d_override_restore",
                label="Stage D Symbol Override Restore",
                status="pending",
                advance_gate=False,
                stop_gate=False,
                summary="baseline-only comparison report unavailable",
                checks={"baseline_comparison_available": False},
            ),
            comparison,
        )

    directional_wait_regression_symbols = list(comparison.get("directional_wait_regression_symbols", []) or [])
    probe_regression_symbols = list(comparison.get("probe_regression_symbols", []) or [])
    ready_regression_symbols = list(comparison.get("ready_regression_symbols", []) or [])
    family_regression_count = (
        len(directional_wait_regression_symbols) + len(probe_regression_symbols) + len(ready_regression_symbols)
    )
    checks = {
        "baseline_comparison_available": True,
        "directional_wait_regression_clear": bool(not directional_wait_regression_symbols),
        "probe_regression_clear": bool(not probe_regression_symbols),
        "ready_regression_clear": bool(not ready_regression_symbols),
    }
    if family_regression_count > 0:
        status = "stop"
        summary = f"override comparison found {family_regression_count} family regression signal(s)"
    else:
        status = "advance"
        summary = f"override comparison passed for {comparison.get('comparable_symbol_count', 0)} symbol(s)"
    return (
        _stage_result(
            key="stage_d_override_restore",
            label="Stage D Symbol Override Restore",
            status=status,
            advance_gate=bool(status == "advance"),
            stop_gate=bool(status == "stop"),
            summary=summary,
            checks=checks,
            metrics={
                "comparable_symbol_count": int(comparison.get("comparable_symbol_count", 0) or 0),
                "directional_wait_regression_symbol_count": int(len(directional_wait_regression_symbols)),
                "probe_regression_symbol_count": int(len(probe_regression_symbols)),
                "ready_regression_symbol_count": int(len(ready_regression_symbols)),
            },
        ),
        comparison,
    )


def _stage_micro_calibration(report: dict | None, stage_d_status: str) -> dict:
    if not isinstance(report, dict):
        return _stage_result(
            key="stage_e_micro_calibration",
            label="Stage E Micro Calibration",
            status="pending",
            advance_gate=False,
            stop_gate=False,
            summary="distribution report unavailable",
        )

    anomalies = dict(report.get("anomalies", {}) or {})
    symbols = dict(report.get("symbols", {}) or {})
    flat_exit_count = _safe_int(anomalies.get("flat_exit_count", 0))
    extreme_imbalance_symbols = [dict(item) for item in list(anomalies.get("extreme_imbalance_symbols", []) or [])]
    calibration_targets = []
    for symbol, payload in symbols.items():
        deviation = dict(payload.get("deviation", {}) or {})
        if max(
            abs(_safe_float(deviation.get("buy_deviation", 0.0))),
            abs(_safe_float(deviation.get("sell_deviation", 0.0))),
            abs(_safe_float(deviation.get("neutral_deviation", 0.0))),
        ) >= 0.20:
            calibration_targets.append(symbol)
    calibration_targets.extend(str(item.get("symbol", "") or "") for item in extreme_imbalance_symbols)
    calibration_targets = sorted({symbol for symbol in calibration_targets if symbol})

    checks = {
        "flat_exit_clear": bool(flat_exit_count == 0),
        "override_restore_completed": bool(stage_d_status == "advance"),
        "calibration_targets_present": bool(bool(calibration_targets)),
    }
    if flat_exit_count > 0:
        status = "stop"
        summary = f"flat exit anomaly blocks calibration ({flat_exit_count})"
    elif stage_d_status in {"pending", "hold"}:
        status = "hold"
        summary = "baseline-only vs override-on comparison should be completed first"
    elif stage_d_status == "stop":
        status = "stop"
        summary = "override comparison failed, calibration should not continue"
    elif calibration_targets:
        status = "hold"
        summary = f"micro calibration targets identified: {', '.join(calibration_targets)}"
    else:
        status = "advance"
        summary = "no immediate calibration target detected in latest window"
    return _stage_result(
        key="stage_e_micro_calibration",
        label="Stage E Micro Calibration",
        status=status,
        advance_gate=bool(status == "advance"),
        stop_gate=bool(status == "stop"),
        summary=summary,
        checks=checks,
        metrics={
            "flat_exit_count": int(flat_exit_count),
            "calibration_target_count": int(len(calibration_targets)),
            "calibration_targets": calibration_targets,
        },
    )


def _resolve_overall_decision(stages: list[dict]) -> dict:
    ordered = list(stages or [])
    stop_stage = next((stage for stage in ordered if str(stage.get("status", "")) == "stop"), None)
    if stop_stage:
        return {
            "overall_status": "stop",
            "recommended_action": "stop",
            "next_stage": str(stop_stage.get("stage_key", "") or ""),
            "summary": str(stop_stage.get("summary", "") or ""),
            "phase6_complete": False,
        }
    blocking_stage = next((stage for stage in ordered if str(stage.get("status", "")) in {"hold", "pending"}), None)
    if blocking_stage:
        return {
            "overall_status": str(blocking_stage.get("status", "") or "hold"),
            "recommended_action": "hold",
            "next_stage": str(blocking_stage.get("stage_key", "") or ""),
            "summary": str(blocking_stage.get("summary", "") or ""),
            "phase6_complete": False,
        }
    return {
        "overall_status": "advance",
        "recommended_action": "advance",
        "next_stage": "phase6_complete",
        "summary": "all rollout gates in the latest window are satisfied",
        "phase6_complete": True,
    }


def build_chart_flow_rollout_status(
    distribution_report: dict | None,
    *,
    comparison_override_distribution_report: dict | None = None,
    baseline_distribution_report: dict | None = None,
    runtime_status: dict | None = None,
    runtime_status_detail: dict | None = None,
    history_by_symbol: dict[str, list[dict]] | None = None,
    comparison_override_distribution_path: str | Path | None = None,
    distribution_path: str | Path | None = None,
    baseline_distribution_path: str | Path | None = None,
    runtime_status_path: str | Path | None = None,
    runtime_status_detail_path: str | Path | None = None,
) -> dict:
    report = dict(distribution_report or {}) if isinstance(distribution_report, dict) else {}
    comparison_override_report = (
        dict(comparison_override_distribution_report or {})
        if isinstance(comparison_override_distribution_report, dict)
        else {}
    )
    baseline_report = (
        dict(baseline_distribution_report or {}) if isinstance(baseline_distribution_report, dict) else {}
    )
    runtime_payload = dict(runtime_status or {}) if isinstance(runtime_status, dict) else {}
    runtime_detail_payload = dict(runtime_status_detail or {}) if isinstance(runtime_status_detail, dict) else {}
    history_summary = _history_schema_summary(history_by_symbol)

    stage_a = _stage_semantic_baseline(report)
    stage_b = _stage_common_threshold(report)
    stage_c = _stage_strength_rollout(report)
    stage_d_source = comparison_override_report if comparison_override_report else report
    stage_d, comparison = _stage_override_restore(stage_d_source, baseline_report)
    stage_e = _stage_micro_calibration(report, str(stage_d.get("status", "") or "pending"))
    stages = [stage_a, stage_b, stage_c, stage_d, stage_e]
    decision = _resolve_overall_decision(stages)

    comparison_override_source = (
        Path(comparison_override_distribution_path).resolve() if comparison_override_distribution_path else None
    )
    distribution_source = Path(distribution_path).resolve() if distribution_path else None
    baseline_source = Path(baseline_distribution_path).resolve() if baseline_distribution_path else None
    runtime_source = Path(runtime_status_path).resolve() if runtime_status_path else None
    runtime_detail_source = Path(runtime_status_detail_path).resolve() if runtime_status_detail_path else None

    return {
        "contract_version": "chart_flow_rollout_status_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inputs": {
            "distribution_report": {
                "available": bool(report),
                "path": str(distribution_source) if distribution_source else "",
                "baseline_mode": str(report.get("baseline_mode", "") or ""),
                "generated_at": str(report.get("generated_at", "") or ""),
                "window": dict(report.get("window", {}) or {}),
            },
            "comparison_override_distribution_report": {
                "available": bool(comparison_override_report),
                "path": str(comparison_override_source) if comparison_override_source else "",
                "baseline_mode": str(comparison_override_report.get("baseline_mode", "") or ""),
                "generated_at": str(comparison_override_report.get("generated_at", "") or ""),
                "window": dict(comparison_override_report.get("window", {}) or {}),
            },
            "baseline_distribution_report": {
                "available": bool(baseline_report),
                "path": str(baseline_source) if baseline_source else "",
                "baseline_mode": str(baseline_report.get("baseline_mode", "") or ""),
                "generated_at": str(baseline_report.get("generated_at", "") or ""),
                "window": dict(baseline_report.get("window", {}) or {}),
            },
            "runtime_status": {
                "available": bool(runtime_payload),
                "path": str(runtime_source) if runtime_source else "",
                "updated_at": str(runtime_payload.get("updated_at", "") or ""),
                "symbol_count": int(len(list(runtime_payload.get("symbols", []) or []))),
            },
            "runtime_status_detail": {
                "available": bool(runtime_detail_payload),
                "path": str(runtime_detail_source) if runtime_detail_source else "",
                "keys": sorted(runtime_detail_payload.keys()),
            },
            "history_schema_summary": history_summary,
        },
        "comparison": comparison,
        "stages": {str(stage["stage_key"]): stage for stage in stages},
        "decision": {
            **decision,
            "decision_log_latest": {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "overall_status": str(decision.get("overall_status", "") or ""),
                "recommended_action": str(decision.get("recommended_action", "") or ""),
                "next_stage": str(decision.get("next_stage", "") or ""),
                "summary": str(decision.get("summary", "") or ""),
            },
        },
    }


def write_chart_flow_rollout_status(status: dict, *, output_path: str | Path | None = None) -> Path:
    path = Path(output_path).resolve() if output_path else resolve_chart_flow_rollout_status_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_and_write_chart_flow_rollout_status(
    *,
    distribution_report: dict | None = None,
    distribution_path: str | Path | None = None,
    comparison_override_distribution_report: dict | None = None,
    comparison_override_distribution_path: str | Path | None = None,
    baseline_distribution_report: dict | None = None,
    baseline_distribution_path: str | Path | None = None,
    runtime_status: dict | None = None,
    runtime_status_path: str | Path | None = None,
    runtime_status_detail: dict | None = None,
    runtime_status_detail_path: str | Path | None = None,
    history_by_symbol: dict[str, list[dict]] | None = None,
    save_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[dict, Path]:
    report = dict(distribution_report or {}) if isinstance(distribution_report, dict) else {}
    report_path = Path(distribution_path).resolve() if distribution_path else None
    if not report and report_path is not None:
        loaded = _load_json_document(report_path)
        report = dict(loaded or {}) if isinstance(loaded, dict) else {}

    comparison_override_report = (
        dict(comparison_override_distribution_report or {})
        if isinstance(comparison_override_distribution_report, dict)
        else {}
    )
    comparison_override_path = (
        Path(comparison_override_distribution_path).resolve()
        if comparison_override_distribution_path
        else resolve_chart_flow_compare_override_distribution_input_path()
    )
    if not comparison_override_report and comparison_override_path is not None:
        loaded = _load_json_document(comparison_override_path)
        comparison_override_report = dict(loaded or {}) if isinstance(loaded, dict) else {}

    baseline_report = dict(baseline_distribution_report or {}) if isinstance(baseline_distribution_report, dict) else {}
    baseline_path = (
        Path(baseline_distribution_path).resolve()
        if baseline_distribution_path
        else resolve_chart_flow_baseline_distribution_input_path()
    )
    if not baseline_report and baseline_path is not None:
        loaded = _load_json_document(baseline_path)
        baseline_report = dict(loaded or {}) if isinstance(loaded, dict) else {}

    runtime_payload = dict(runtime_status or {}) if isinstance(runtime_status, dict) else {}
    runtime_path = Path(runtime_status_path).resolve() if runtime_status_path else resolve_runtime_status_input_path()
    if not runtime_payload:
        loaded = _load_json_document(runtime_path)
        runtime_payload = dict(loaded or {}) if isinstance(loaded, dict) else {}

    runtime_detail_payload = dict(runtime_status_detail or {}) if isinstance(runtime_status_detail, dict) else {}
    runtime_detail_path_obj = (
        Path(runtime_status_detail_path).resolve() if runtime_status_detail_path else resolve_runtime_status_detail_input_path()
    )
    if not runtime_detail_payload:
        loaded = _load_json_document(runtime_detail_path_obj)
        runtime_detail_payload = dict(loaded or {}) if isinstance(loaded, dict) else {}

    histories = dict(history_by_symbol or {})
    if not histories and save_dir is not None:
        histories = load_flow_history_by_symbol(save_dir)

    status = build_chart_flow_rollout_status(
        report,
        comparison_override_distribution_report=comparison_override_report,
        baseline_distribution_report=baseline_report,
        runtime_status=runtime_payload,
        runtime_status_detail=runtime_detail_payload,
        history_by_symbol=histories,
        comparison_override_distribution_path=comparison_override_path,
        distribution_path=report_path,
        baseline_distribution_path=baseline_path,
        runtime_status_path=runtime_path,
        runtime_status_detail_path=runtime_detail_path_obj,
    )
    path = write_chart_flow_rollout_status(status, output_path=output_path)
    return status, path
