from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


DIRECTIONAL_CONTINUATION_ACCURACY_TRACKER_VERSION = (
    "directional_continuation_accuracy_tracker_v1"
)
DEFAULT_HORIZON_BARS: tuple[int, ...] = (10, 20, 30)
PRIMARY_HORIZON_BARS = 20
MIN_OBSERVATION_SPACING_SEC = 300
MIN_DECISIVE_MOVE_PCT = 0.0005
MAX_PENDING_OBSERVATIONS = 500
MAX_RESOLVED_OBSERVATIONS = 600


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _default_state_path() -> Path:
    return _default_shadow_auto_dir() / "directional_continuation_accuracy_tracker_state.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_direction(value: object) -> str:
    text = _to_text(value).upper()
    return text if text in {"UP", "DOWN"} else ""


def _safe_rate(numerator: int, denominator: int) -> float:
    if int(denominator) <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _row_timestamp_ts(row: Mapping[str, Any] | None, *, default_ts: float) -> float:
    payload = _mapping(row)
    value = payload.get("time")
    if value not in ("", None):
        try:
            numeric = float(value)
            if math.isfinite(numeric) and numeric > 0.0:
                return numeric
        except Exception:
            pass
    timestamp_text = _to_text(payload.get("timestamp"))
    if timestamp_text:
        try:
            parsed = datetime.fromisoformat(timestamp_text)
            return float(parsed.timestamp())
        except Exception:
            pass
    return float(default_ts)


def _reference_price_from_row(row: Mapping[str, Any] | None) -> tuple[float | None, str]:
    payload = _mapping(row)
    for key in (
        "current_close",
        "live_price",
        "price",
        "close",
        "current_price",
        "last_price",
    ):
        value = payload.get(key)
        if value in ("", None):
            continue
        try:
            numeric = float(value)
        except Exception:
            continue
        if math.isfinite(numeric) and numeric > 0.0:
            return float(numeric), str(key)
    return None, ""


def _append_unique(items: list[str], value: object) -> None:
    text = _to_text(value)
    if text and text not in items:
        items.append(text)


def _trim_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = sorted(
        [dict(row) for row in rows if isinstance(row, Mapping)],
        key=lambda item: float(_to_float(item.get("observed_at_ts"), 0.0)),
    )
    return ordered[-max(int(limit), 1) :]


def _build_observation(
    *,
    symbol: str,
    direction: str,
    candidate_key: str,
    source_kind: str,
    overlay_score: float,
    current_side: str,
    reference_price: float,
    price_source_field: str,
    observed_at_ts: float,
    observed_at: str,
    horizon_bars: int,
) -> dict[str, Any]:
    observation_id = (
        f"{symbol}|{direction}|{candidate_key}|{int(round(observed_at_ts))}|h{int(horizon_bars)}"
    )
    return {
        "observation_id": observation_id,
        "symbol": str(symbol),
        "direction": str(direction),
        "candidate_key": str(candidate_key),
        "source_kind": str(source_kind),
        "overlay_score": round(float(overlay_score), 4),
        "current_side": str(current_side),
        "price_source_field": str(price_source_field),
        "reference_price": round(float(reference_price), 8),
        "observed_at_ts": float(observed_at_ts),
        "observed_at": str(observed_at),
        "horizon_bars": int(horizon_bars),
        "evaluation_due_ts": float(observed_at_ts + (int(horizon_bars) * 60)),
        "latest_price_seen": round(float(reference_price), 8),
        "latest_seen_at_ts": float(observed_at_ts),
        "max_price_seen": round(float(reference_price), 8),
        "min_price_seen": round(float(reference_price), 8),
        "update_count": 1,
        "evaluation_state": "PENDING",
    }


def _update_observation_with_price(
    observation: Mapping[str, Any] | None,
    *,
    current_price: float,
    seen_at_ts: float,
) -> dict[str, Any]:
    payload = _mapping(observation)
    if not (math.isfinite(float(current_price)) and float(current_price) > 0.0):
        return payload
    max_seen = max(_to_float(payload.get("max_price_seen"), float(current_price)), float(current_price))
    min_seen = min(_to_float(payload.get("min_price_seen"), float(current_price)), float(current_price))
    payload["latest_price_seen"] = round(float(current_price), 8)
    payload["latest_seen_at_ts"] = float(seen_at_ts)
    payload["max_price_seen"] = round(float(max_seen), 8)
    payload["min_price_seen"] = round(float(min_seen), 8)
    payload["update_count"] = int(_to_int(payload.get("update_count"), 0) + 1)
    return payload


def _evaluate_observation(
    observation: Mapping[str, Any] | None,
    *,
    min_decisive_move_pct: float,
    evaluated_at_ts: float,
) -> dict[str, Any]:
    payload = _mapping(observation)
    direction = _normalize_direction(payload.get("direction"))
    reference_price = _to_float(payload.get("reference_price"), 0.0)
    max_seen = _to_float(payload.get("max_price_seen"), reference_price)
    min_seen = _to_float(payload.get("min_price_seen"), reference_price)
    favorable_move_pct = 0.0
    adverse_move_pct = 0.0
    actual_direction = "FLAT"
    evaluation_state = "UNRESOLVED"
    continuation_correct = False
    false_alarm = False

    if direction == "UP" and reference_price > 0.0:
        favorable_move_pct = max(0.0, (max_seen - reference_price) / reference_price)
        adverse_move_pct = max(0.0, (reference_price - min_seen) / reference_price)
        actual_direction = "UP" if favorable_move_pct >= adverse_move_pct else "DOWN"
    elif direction == "DOWN" and reference_price > 0.0:
        favorable_move_pct = max(0.0, (reference_price - min_seen) / reference_price)
        adverse_move_pct = max(0.0, (max_seen - reference_price) / reference_price)
        actual_direction = "DOWN" if favorable_move_pct >= adverse_move_pct else "UP"

    if favorable_move_pct >= float(min_decisive_move_pct) and favorable_move_pct >= adverse_move_pct:
        evaluation_state = "CORRECT"
        continuation_correct = True
    elif adverse_move_pct >= float(min_decisive_move_pct) and adverse_move_pct > favorable_move_pct:
        evaluation_state = "INCORRECT"
        false_alarm = True
    elif favorable_move_pct > 0.0 or adverse_move_pct > 0.0:
        evaluation_state = "UNRESOLVED"

    payload["evaluation_state"] = str(evaluation_state)
    payload["evaluated_at_ts"] = float(evaluated_at_ts)
    payload["evaluated_at"] = datetime.fromtimestamp(float(evaluated_at_ts)).astimezone().isoformat()
    payload["actual_followthrough_direction"] = str(actual_direction)
    payload["continuation_correct"] = bool(continuation_correct)
    payload["continuation_false_alarm"] = bool(false_alarm)
    payload["favorable_move_pct"] = round(float(favorable_move_pct), 6)
    payload["adverse_move_pct"] = round(float(adverse_move_pct), 6)
    return payload


def _primary_summary_key(symbol: object, direction: object) -> str:
    return f"{_to_text(symbol).upper()}|{_normalize_direction(direction)}"


def _build_symbol_direction_primary_summary(
    resolved_rows: list[dict[str, Any]],
    *,
    primary_horizon_bars: int,
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    rows = [
        _mapping(row)
        for row in list(resolved_rows or [])
        if _to_int(_mapping(row).get("horizon_bars"), 0) == int(primary_horizon_bars)
    ]
    rows.sort(key=lambda item: float(_to_float(item.get("evaluated_at_ts"), 0.0)))
    for row in rows:
        key = _primary_summary_key(row.get("symbol"), row.get("direction"))
        if not key.endswith("|"):
            summary.setdefault(
                key,
                {
                    "symbol": _to_text(row.get("symbol")).upper(),
                    "direction": _normalize_direction(row.get("direction")),
                    "horizon_bars": int(primary_horizon_bars),
                    "sample_count": 0,
                    "measured_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "unresolved_count": 0,
                    "correct_rate": 0.0,
                    "false_alarm_rate": 0.0,
                    "unresolved_rate": 0.0,
                    "last_evaluation_state": "",
                    "last_candidate_key": "",
                    "last_overlay_score": 0.0,
                },
            )
            bucket = summary[key]
            bucket["sample_count"] = int(bucket["sample_count"]) + 1
            state = _to_text(row.get("evaluation_state")).upper()
            if state == "CORRECT":
                bucket["correct_count"] = int(bucket["correct_count"]) + 1
                bucket["measured_count"] = int(bucket["measured_count"]) + 1
            elif state == "INCORRECT":
                bucket["incorrect_count"] = int(bucket["incorrect_count"]) + 1
                bucket["measured_count"] = int(bucket["measured_count"]) + 1
            else:
                bucket["unresolved_count"] = int(bucket["unresolved_count"]) + 1
            bucket["last_evaluation_state"] = state
            bucket["last_candidate_key"] = _to_text(row.get("candidate_key"))
            bucket["last_overlay_score"] = round(_to_float(row.get("overlay_score"), 0.0), 4)
    for bucket in summary.values():
        sample_count = int(bucket.get("sample_count", 0) or 0)
        measured_count = int(bucket.get("measured_count", 0) or 0)
        bucket["correct_rate"] = _safe_rate(int(bucket.get("correct_count", 0) or 0), measured_count)
        bucket["false_alarm_rate"] = _safe_rate(int(bucket.get("incorrect_count", 0) or 0), measured_count)
        bucket["unresolved_rate"] = _safe_rate(int(bucket.get("unresolved_count", 0) or 0), sample_count)
    return summary


def _build_summary(
    *,
    pending_rows: list[dict[str, Any]],
    resolved_rows: list[dict[str, Any]],
    primary_summary: Mapping[str, Any] | None,
    primary_horizon_bars: int,
    generated_at: str,
) -> dict[str, Any]:
    measured_primary = 0
    correct_primary = 0
    incorrect_primary = 0
    for value in dict(primary_summary or {}).values():
        row = _mapping(value)
        measured_primary += int(_to_int(row.get("measured_count"), 0))
        correct_primary += int(_to_int(row.get("correct_count"), 0))
        incorrect_primary += int(_to_int(row.get("incorrect_count"), 0))
    return {
        "generated_at": str(generated_at),
        "primary_horizon_bars": int(primary_horizon_bars),
        "horizon_bars": list(DEFAULT_HORIZON_BARS),
        "pending_observation_count": int(len(list(pending_rows or []))),
        "resolved_observation_count": int(len(list(resolved_rows or []))),
        "primary_measured_count": int(measured_primary),
        "primary_correct_count": int(correct_primary),
        "primary_incorrect_count": int(incorrect_primary),
        "primary_correct_rate": _safe_rate(correct_primary, measured_primary),
        "primary_false_alarm_rate": _safe_rate(incorrect_primary, measured_primary),
        "symbol_direction_summary_count": int(len(dict(primary_summary or {}))),
    }


def render_directional_continuation_accuracy_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Directional Continuation Accuracy Tracker",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- primary_horizon_bars: `{int(_to_int(summary.get('primary_horizon_bars'), PRIMARY_HORIZON_BARS))}`",
        f"- pending_observation_count: `{int(_to_int(summary.get('pending_observation_count'), 0))}`",
        f"- resolved_observation_count: `{int(_to_int(summary.get('resolved_observation_count'), 0))}`",
        f"- primary_measured_count: `{int(_to_int(summary.get('primary_measured_count'), 0))}`",
        f"- primary_correct_rate: `{float(_to_float(summary.get('primary_correct_rate'), 0.0)):.4f}`",
        f"- primary_false_alarm_rate: `{float(_to_float(summary.get('primary_false_alarm_rate'), 0.0)):.4f}`",
        "",
        "## Symbol Direction Summary",
        "",
    ]
    symbol_summary = _mapping(payload.get("symbol_direction_primary_summary"))
    if not symbol_summary:
        lines.append("- none")
    for key in sorted(symbol_summary):
        row = _mapping(symbol_summary.get(key))
        lines.append(
            f"- `{key}`: sample={int(_to_int(row.get('sample_count'), 0))} "
            f"| measured={int(_to_int(row.get('measured_count'), 0))} "
            f"| correct_rate={float(_to_float(row.get('correct_rate'), 0.0)):.4f} "
            f"| false_alarm_rate={float(_to_float(row.get('false_alarm_rate'), 0.0)):.4f} "
            f"| last={_to_text(row.get('last_evaluation_state'), '-')}"
        )
    lines.extend(["", "## Recent Resolved Rows", ""])
    recent_rows = list(payload.get("recent_resolved_rows") or [])
    if not recent_rows:
        lines.append("- none")
    for row in recent_rows[:12]:
        mapped = _mapping(row)
        lines.append(
            f"- {_to_text(mapped.get('symbol'))} {_normalize_direction(mapped.get('direction'))} "
            f"h{int(_to_int(mapped.get('horizon_bars'), 0))}: {_to_text(mapped.get('evaluation_state'))} "
            f"| favorable={float(_to_float(mapped.get('favorable_move_pct'), 0.0)):.4f} "
            f"| adverse={float(_to_float(mapped.get('adverse_move_pct'), 0.0)):.4f}"
        )
    return "\n".join(lines).strip() + "\n"


def build_directional_continuation_accuracy_flat_fields_v1(
    report: Mapping[str, Any] | None,
    *,
    symbol: str,
    direction: str,
    primary_horizon_bars: int = PRIMARY_HORIZON_BARS,
) -> dict[str, Any]:
    key = _primary_summary_key(symbol, direction)
    summary = _mapping(_mapping(report).get("symbol_direction_primary_summary")).get(key)
    row = _mapping(summary)
    return {
        "directional_continuation_accuracy_horizon_bars": int(primary_horizon_bars),
        "directional_continuation_accuracy_sample_count": int(_to_int(row.get("sample_count"), 0)),
        "directional_continuation_accuracy_measured_count": int(_to_int(row.get("measured_count"), 0)),
        "directional_continuation_accuracy_correct_rate": round(_to_float(row.get("correct_rate"), 0.0), 4),
        "directional_continuation_accuracy_false_alarm_rate": round(
            _to_float(row.get("false_alarm_rate"), 0.0), 4
        ),
        "directional_continuation_accuracy_unresolved_rate": round(
            _to_float(row.get("unresolved_rate"), 0.0), 4
        ),
        "directional_continuation_accuracy_last_state": _to_text(row.get("last_evaluation_state")),
        "directional_continuation_accuracy_last_candidate_key": _to_text(row.get("last_candidate_key")),
    }


def update_directional_continuation_accuracy_tracker(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    state_path: str | Path | None = None,
    shadow_auto_dir: str | Path | None = None,
    horizons: tuple[int, ...] = DEFAULT_HORIZON_BARS,
    primary_horizon_bars: int = PRIMARY_HORIZON_BARS,
    min_observation_spacing_sec: int = MIN_OBSERVATION_SPACING_SEC,
    min_decisive_move_pct: float = MIN_DECISIVE_MOVE_PCT,
) -> dict[str, Any]:
    now_ts = float(time.time())
    generated_at = _now_iso()
    latest_rows = {
        _to_text(symbol).upper(): _mapping(row)
        for symbol, row in dict(latest_signal_by_symbol or {}).items()
        if _to_text(symbol) and isinstance(row, Mapping)
    }

    resolved_output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_state_path = Path(state_path) if state_path is not None else _default_state_path()
    state_payload = _load_json(resolved_state_path)
    pending_rows = [
        _mapping(row)
        for row in list(state_payload.get("pending_observations") or [])
        if isinstance(row, Mapping)
    ]
    resolved_rows = [
        _mapping(row)
        for row in list(state_payload.get("resolved_observations") or [])
        if isinstance(row, Mapping)
    ]
    group_last_observed_ts = {
        _to_text(key): float(_to_float(value, 0.0))
        for key, value in dict(state_payload.get("group_last_observed_ts") or {}).items()
        if _to_text(key)
    }

    symbol_price_index: dict[str, tuple[float, str, float]] = {}
    for symbol, row in latest_rows.items():
        price, price_field = _reference_price_from_row(row)
        row_ts = _row_timestamp_ts(row, default_ts=now_ts)
        if price is not None:
            symbol_price_index[symbol] = (float(price), str(price_field), float(row_ts))

    refreshed_pending: list[dict[str, Any]] = []
    for row in pending_rows:
        symbol = _to_text(row.get("symbol")).upper()
        price_tuple = symbol_price_index.get(symbol)
        if price_tuple is not None:
            current_price, _, seen_at_ts = price_tuple
            row = _update_observation_with_price(
                row,
                current_price=float(current_price),
                seen_at_ts=float(seen_at_ts),
            )
        evaluation_due_ts = float(_to_float(row.get("evaluation_due_ts"), 0.0))
        if evaluation_due_ts > 0.0 and now_ts >= evaluation_due_ts:
            resolved_rows.append(
                _evaluate_observation(
                    row,
                    min_decisive_move_pct=float(min_decisive_move_pct),
                    evaluated_at_ts=now_ts,
                )
            )
        else:
            refreshed_pending.append(row)
    pending_rows = refreshed_pending

    for symbol, row in latest_rows.items():
        direction = _normalize_direction(row.get("directional_continuation_overlay_direction"))
        candidate_key = _to_text(row.get("directional_continuation_overlay_candidate_key"))
        overlay_enabled = bool(row.get("directional_continuation_overlay_enabled"))
        if not overlay_enabled or not direction or not candidate_key:
            continue
        price, price_field = _reference_price_from_row(row)
        if price is None:
            continue
        observed_at_ts = _row_timestamp_ts(row, default_ts=now_ts)
        group_key = _primary_summary_key(symbol, direction) + "|" + candidate_key
        last_observed_ts = float(group_last_observed_ts.get(group_key, 0.0) or 0.0)
        if last_observed_ts > 0.0 and (observed_at_ts - last_observed_ts) < float(
            min_observation_spacing_sec
        ):
            continue
        observed_at = _to_text(row.get("timestamp")) or datetime.fromtimestamp(
            float(observed_at_ts)
        ).astimezone().isoformat()
        source_kind = _to_text(row.get("directional_continuation_overlay_source_kind"))
        overlay_score = _to_float(row.get("directional_continuation_overlay_score"), 0.0)
        current_side = _to_text(row.get("consumer_check_side")).upper()
        for horizon_bars in tuple(int(value) for value in horizons if int(value) > 0):
            pending_rows.append(
                _build_observation(
                    symbol=str(symbol),
                    direction=str(direction),
                    candidate_key=str(candidate_key),
                    source_kind=str(source_kind),
                    overlay_score=float(overlay_score),
                    current_side=str(current_side),
                    reference_price=float(price),
                    price_source_field=str(price_field),
                    observed_at_ts=float(observed_at_ts),
                    observed_at=str(observed_at),
                    horizon_bars=int(horizon_bars),
                )
            )
        group_last_observed_ts[group_key] = float(observed_at_ts)

    pending_rows = _trim_rows(pending_rows, MAX_PENDING_OBSERVATIONS)
    resolved_rows = _trim_rows(resolved_rows, MAX_RESOLVED_OBSERVATIONS)
    if len(group_last_observed_ts) > 1000:
        ordered_group_items = sorted(group_last_observed_ts.items(), key=lambda item: float(item[1]))
        group_last_observed_ts = dict(ordered_group_items[-1000:])

    primary_summary = _build_symbol_direction_primary_summary(
        resolved_rows,
        primary_horizon_bars=int(primary_horizon_bars),
    )
    report = {
        "contract_version": DIRECTIONAL_CONTINUATION_ACCURACY_TRACKER_VERSION,
        "summary": _build_summary(
            pending_rows=pending_rows,
            resolved_rows=resolved_rows,
            primary_summary=primary_summary,
            primary_horizon_bars=int(primary_horizon_bars),
            generated_at=str(generated_at),
        ),
        "symbol_direction_primary_summary": primary_summary,
        "recent_resolved_rows": sorted(
            resolved_rows,
            key=lambda row: float(_to_float(_mapping(row).get("evaluated_at_ts"), 0.0)),
            reverse=True,
        )[:20],
        "pending_rows": sorted(
            pending_rows,
            key=lambda row: float(_to_float(_mapping(row).get("observed_at_ts"), 0.0)),
            reverse=True,
        )[:20],
    }

    state_out = {
        "contract_version": DIRECTIONAL_CONTINUATION_ACCURACY_TRACKER_VERSION,
        "updated_at": str(generated_at),
        "pending_observations": pending_rows,
        "resolved_observations": resolved_rows,
        "group_last_observed_ts": group_last_observed_ts,
    }
    _write_json(resolved_state_path, state_out)

    json_path = resolved_output_dir / "directional_continuation_accuracy_tracker_latest.json"
    md_path = resolved_output_dir / "directional_continuation_accuracy_tracker_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_directional_continuation_accuracy_markdown(report))
    report["artifact_paths"] = {
        "state_path": str(resolved_state_path),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    return report
