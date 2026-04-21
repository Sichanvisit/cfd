"""Entry performance baseline lock and regression watch helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


ENTRY_PERFORMANCE_BASELINE_CONTRACT_VERSION = "entry_performance_baseline_v1"
ENTRY_PERFORMANCE_REGRESSION_WATCH_CONTRACT_VERSION = "entry_performance_regression_watch_v1"
DEFAULT_ENTRY_PERFORMANCE_SYMBOLS = ("NAS100", "BTCUSD", "XAUUSD")


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _latest_profile_rows(
    profile_collection: Mapping[str, Any] | None,
    *,
    symbols: tuple[str, ...] = DEFAULT_ENTRY_PERFORMANCE_SYMBOLS,
) -> dict[str, dict[str, Any]]:
    payload = _mapping(profile_collection)
    latest_by_symbol = _mapping(payload.get("latest_by_symbol"))
    rows: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        row = _mapping(latest_by_symbol.get(symbol))
        if row:
            rows[str(symbol)] = row
    return rows


def _extract_symbol_metrics(symbol: str, profile_row: Mapping[str, Any] | None) -> dict[str, Any]:
    row = _mapping(profile_row)
    append_log_profile = _mapping(row.get("append_log_profile"))
    recorder = _mapping(append_log_profile.get("recorder_stage_timings_ms"))
    detail = _mapping(append_log_profile.get("detail_payload_stage_timings_ms"))
    file_write = _mapping(append_log_profile.get("file_write_stage_timings_ms"))
    return {
        "symbol": str(symbol),
        "elapsed_ms": round(_to_float(row.get("elapsed_ms")), 3),
        "dominant_stage": _to_text(row.get("dominant_stage")),
        "append_total_ms": round(_to_float(append_log_profile.get("total_ms")), 3),
        "recorder_total_ms": round(_to_float(append_log_profile.get("recorder_total_ms")), 3),
        "detail_payload_build_ms": round(_to_float(recorder.get("detail_payload_build")), 3),
        "file_write_ms": round(_to_float(recorder.get("file_write")), 3),
        "compact_runtime_row_ms": round(_to_float(detail.get("compact_runtime_row")), 3),
        "detail_record_json_ms": round(_to_float(detail.get("detail_record_json")), 3),
        "hot_payload_build_ms": round(_to_float(detail.get("hot_payload_build")), 3),
        "payload_size_metrics_ms": round(_to_float(detail.get("payload_size_metrics")), 3),
        "csv_append_ms": round(_to_float(file_write.get("csv_append")), 3),
        "detail_append_ms": round(_to_float(file_write.get("detail_append")), 3),
        "rollover_ms": round(_to_float(file_write.get("rollover")), 3),
        "runtime_snapshot_mode": _to_text(append_log_profile.get("runtime_snapshot_mode")),
        "runtime_snapshot_store_calls": _to_int(append_log_profile.get("runtime_snapshot_store_calls")),
    }


def build_entry_performance_baseline_lock(
    profile_collection: Mapping[str, Any] | None,
    *,
    runtime_status: Mapping[str, Any] | None = None,
    symbols: tuple[str, ...] = DEFAULT_ENTRY_PERFORMANCE_SYMBOLS,
    reentry_elapsed_ms: float = 200.0,
) -> dict[str, Any]:
    generated_at = datetime.now().isoformat(timespec="seconds")
    runtime = _mapping(runtime_status)
    rows_by_symbol = _latest_profile_rows(profile_collection, symbols=symbols)
    symbol_metrics = [_extract_symbol_metrics(symbol, rows_by_symbol.get(symbol)) for symbol in symbols if rows_by_symbol.get(symbol)]
    max_elapsed_ms = max((_to_float(row.get("elapsed_ms")) for row in symbol_metrics), default=0.0)
    max_append_total_ms = max((_to_float(row.get("append_total_ms")) for row in symbol_metrics), default=0.0)
    return {
        "contract_version": ENTRY_PERFORMANCE_BASELINE_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "baseline_locked": True,
        "reentry_elapsed_ms_threshold": round(float(reentry_elapsed_ms), 3),
        "symbol_count": len(symbol_metrics),
        "symbols": list(symbols),
        "max_elapsed_ms": round(float(max_elapsed_ms), 3),
        "max_append_total_ms": round(float(max_append_total_ms), 3),
        "recommended_next_action": (
            "resume_market_family_roadmap"
            if max_elapsed_ms < float(reentry_elapsed_ms)
            else "hold_performance_work_before_roadmap"
        ),
        "symbol_metrics": symbol_metrics,
    }


def build_entry_performance_regression_watch(
    profile_collection: Mapping[str, Any] | None,
    baseline_lock: Mapping[str, Any] | None,
    *,
    runtime_status: Mapping[str, Any] | None = None,
    runtime_loop_debug: Mapping[str, Any] | None = None,
    symbols: tuple[str, ...] = DEFAULT_ENTRY_PERFORMANCE_SYMBOLS,
) -> dict[str, Any]:
    generated_at = datetime.now().isoformat(timespec="seconds")
    runtime = _mapping(runtime_status)
    loop_debug = _mapping(runtime_loop_debug)
    baseline = _mapping(baseline_lock)
    threshold = _to_float(baseline.get("reentry_elapsed_ms_threshold"), 200.0)
    baseline_rows = {
        _to_text(row.get("symbol")): _mapping(row)
        for row in list(baseline.get("symbol_metrics", []) or [])
        if _to_text(_mapping(row).get("symbol"))
    }
    current_rows = _latest_profile_rows(profile_collection, symbols=symbols)
    comparisons: list[dict[str, Any]] = []
    reentry_symbols: list[str] = []
    for symbol in symbols:
        current_metrics = _extract_symbol_metrics(symbol, current_rows.get(symbol))
        baseline_metrics = baseline_rows.get(symbol, {})
        current_elapsed = _to_float(current_metrics.get("elapsed_ms"))
        baseline_elapsed = _to_float(baseline_metrics.get("elapsed_ms"))
        current_append = _to_float(current_metrics.get("append_total_ms"))
        baseline_append = _to_float(baseline_metrics.get("append_total_ms"))
        reentry_required = current_elapsed >= threshold
        if reentry_required:
            reentry_symbols.append(symbol)
        comparisons.append(
            {
                "symbol": symbol,
                "baseline_elapsed_ms": round(baseline_elapsed, 3),
                "current_elapsed_ms": round(current_elapsed, 3),
                "elapsed_delta_ms": round(current_elapsed - baseline_elapsed, 3),
                "baseline_append_total_ms": round(baseline_append, 3),
                "current_append_total_ms": round(current_append, 3),
                "append_delta_ms": round(current_append - baseline_append, 3),
                "current_detail_payload_build_ms": round(_to_float(current_metrics.get("detail_payload_build_ms")), 3),
                "current_compact_runtime_row_ms": round(_to_float(current_metrics.get("compact_runtime_row_ms")), 3),
                "current_hot_payload_build_ms": round(_to_float(current_metrics.get("hot_payload_build_ms")), 3),
                "current_runtime_snapshot_mode": _to_text(current_metrics.get("runtime_snapshot_mode")),
                "reentry_required": bool(reentry_required),
                "status": "reentry_required" if reentry_required else "healthy",
            }
        )
    return {
        "contract_version": ENTRY_PERFORMANCE_REGRESSION_WATCH_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "runtime_loop_updated_at": _to_text(loop_debug.get("updated_at")),
        "runtime_loop_stage": _to_text(loop_debug.get("stage")),
        "runtime_loop_symbol": _to_text(loop_debug.get("symbol")),
        "baseline_locked": bool(baseline.get("baseline_locked", False)),
        "reentry_elapsed_ms_threshold": round(threshold, 3),
        "symbol_count": len(comparisons),
        "reentry_required": bool(reentry_symbols),
        "reentry_symbols": list(reentry_symbols),
        "recommended_next_action": (
            "reenter_entry_performance_optimization"
            if reentry_symbols
            else "resume_market_family_roadmap"
        ),
        "comparisons": comparisons,
    }


def render_entry_performance_baseline_markdown(
    baseline_lock: Mapping[str, Any] | None,
    regression_watch: Mapping[str, Any] | None,
) -> str:
    baseline = _mapping(baseline_lock)
    regression = _mapping(regression_watch)
    lines = [
        "# Entry Performance Baseline",
        "",
        "## Baseline Lock",
        "",
        f"- generated_at: `{_to_text(baseline.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(baseline.get('runtime_updated_at'))}`",
        f"- baseline_locked: `{bool(baseline.get('baseline_locked', False))}`",
        f"- reentry_elapsed_ms_threshold: `{_to_float(baseline.get('reentry_elapsed_ms_threshold'), 200.0)}`",
        f"- max_elapsed_ms: `{_to_float(baseline.get('max_elapsed_ms'), 0.0)}`",
        f"- max_append_total_ms: `{_to_float(baseline.get('max_append_total_ms'), 0.0)}`",
        "",
        "## Regression Watch",
        "",
        f"- generated_at: `{_to_text(regression.get('generated_at'))}`",
        f"- runtime_loop_stage: `{_to_text(regression.get('runtime_loop_stage'))}`",
        f"- reentry_required: `{bool(regression.get('reentry_required', False))}`",
        f"- reentry_symbols: `{','.join(list(regression.get('reentry_symbols', []) or []))}`",
        f"- recommended_next_action: `{_to_text(regression.get('recommended_next_action'))}`",
        "",
        "## Symbol Status",
        "",
    ]
    for row in list(regression.get("comparisons", []) or []):
        item = _mapping(row)
        lines.append(
            "- `{symbol}` status=`{status}` current_elapsed_ms=`{current_elapsed_ms}` baseline_elapsed_ms=`{baseline_elapsed_ms}` append_total_ms=`{current_append_total_ms}` detail_payload_build_ms=`{current_detail_payload_build_ms}` compact_runtime_row_ms=`{current_compact_runtime_row_ms}` hot_payload_build_ms=`{current_hot_payload_build_ms}`".format(
                symbol=_to_text(item.get("symbol")),
                status=_to_text(item.get("status")),
                current_elapsed_ms=_to_float(item.get("current_elapsed_ms"), 0.0),
                baseline_elapsed_ms=_to_float(item.get("baseline_elapsed_ms"), 0.0),
                current_append_total_ms=_to_float(item.get("current_append_total_ms"), 0.0),
                current_detail_payload_build_ms=_to_float(item.get("current_detail_payload_build_ms"), 0.0),
                current_compact_runtime_row_ms=_to_float(item.get("current_compact_runtime_row_ms"), 0.0),
                current_hot_payload_build_ms=_to_float(item.get("current_hot_payload_build_ms"), 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- Keep this baseline fixed while roadmap work resumes.",
            "- Do not resume micro-optimization unless a real live symbol exceeds the reentry threshold.",
            "- If a symbol exceeds the threshold again, re-enter the performance thread with the latest profile artifact first.",
            "",
        ]
    )
    return "\n".join(lines)
