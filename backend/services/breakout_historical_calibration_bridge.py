"""Historical breakout calibration bridge over matched replay/manual rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.barrier_state25_runtime_bridge import build_barrier_runtime_summary_v1
from backend.services.belief_state25_runtime_bridge import build_belief_runtime_summary_v1
from backend.services.breakout_event_overlay import build_breakout_event_overlay_candidates_v1
from backend.services.breakout_event_runtime import build_breakout_event_runtime_v1
from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_runtime_summary_v1,
    build_state25_runtime_hint_v1,
)
from backend.services.trade_csv_schema import now_kst_dt


BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_CONTRACT_VERSION = "breakout_historical_calibration_bridge_v1"
BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "episode_id",
    "symbol",
    "calibration_scope",
    "seed_status",
    "seed_grade",
    "action_target",
    "continuation_target",
    "matched_decision_time",
    "time_gap_sec",
    "runtime_breakout_direction",
    "runtime_breakout_state",
    "runtime_effective_breakout_readiness_state",
    "runtime_breakout_type_candidate",
    "runtime_breakout_confidence",
    "barrier_total",
    "confirm_score",
    "false_break_score",
    "continuation_score",
    "overlay_target",
    "overlay_reason_summary",
    "conflict_level",
    "action_demotion_rule",
    "historical_alignment_result",
    "replay_dataset_path",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _load_alignment_frame(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _load_seed_frame(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _parse_json_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _normalize_decision_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    for key in (
        "response_vector_v2",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "entry_decision_result_v1",
        "forecast_assist_v1",
        "forecast_features_v1",
        "forecast_gap_metrics_v1",
        "current_entry_context_v1",
        "observe_confirm_v2",
        "entry_wait_state_policy_input_v1",
        "entry_wait_context_v1",
        "energy_helper_v2",
    ):
        if key in normalized:
            mapped = _parse_json_mapping(normalized.get(key))
            if mapped:
                normalized[key] = mapped
    return normalized


def _parse_iso_ts(value: object) -> pd.Timestamp:
    return pd.to_datetime(_to_text(value), errors="coerce")


def _load_replay_rows(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except Exception:
                continue
            if isinstance(record, dict):
                rows.append(record)
    return rows


def _match_replay_row(
    replay_rows: list[dict[str, Any]],
    matched_decision_time: object,
) -> dict[str, Any]:
    target_time = _parse_iso_ts(matched_decision_time)
    if pd.isna(target_time):
        return {}

    best_row: dict[str, Any] = {}
    best_gap: float | None = None
    for record in replay_rows:
        decision_row = record.get("decision_row")
        if not isinstance(decision_row, Mapping):
            continue
        decision_time = _parse_iso_ts(decision_row.get("time"))
        if pd.isna(decision_time):
            continue
        gap = abs((decision_time - target_time).total_seconds())
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_row = dict(record)
            if gap == 0:
                break
    if best_gap is not None and best_gap <= 10.0:
        return best_row
    return {}


def _historical_alignment_result(
    *,
    action_target: str,
    overlay_target: str,
) -> str:
    action = _to_text(action_target).upper()
    overlay = _to_text(overlay_target).upper()
    if action == "ENTER_NOW":
        if overlay == "ENTER_NOW":
            return "aligned_enter_now"
        if overlay in {"PROBE_BREAKOUT", "WATCH_BREAKOUT"}:
            return "demoted_but_supportive"
        return "underfired_wait_more"
    if action == "EXIT_PROTECT":
        return "aligned_exit_protect" if overlay == "EXIT_PROTECT" else "missed_exit_protect"
    if action == "WAIT_MORE":
        return "aligned_wait_more" if overlay == "WAIT_MORE" else "overfired_breakout"
    return "unknown_action_target"


def build_breakout_historical_calibration_bridge(
    alignment_csv_path: str | Path,
    seed_csv_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    alignment = _load_alignment_frame(alignment_csv_path)
    seed = _load_seed_frame(seed_csv_path)

    summary: dict[str, Any] = {
        "contract_version": BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_CONTRACT_VERSION,
        "generated_at": generated_at,
        "alignment_row_count": int(len(alignment)),
        "matched_row_count": 0,
        "gold_seed_row_count": 0,
        "bridge_row_count": 0,
        "manual_enter_now_count": 0,
        "overlay_enter_now_count": 0,
        "overlay_probe_count": 0,
        "overlay_watch_count": 0,
        "overlay_wait_count": 0,
        "direction_none_count": 0,
        "historical_alignment_result_counts": "{}",
        "overlay_target_counts": "{}",
        "conflict_level_counts": "{}",
        "action_demotion_rule_counts": "{}",
        "recommended_next_action": "build_breakout_historical_bridge_inputs",
    }

    if alignment.empty:
        return pd.DataFrame(columns=BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_COLUMNS), summary

    matched = alignment.loc[alignment.get("match_status", "").fillna("").astype(str).eq("matched")].copy()
    summary["matched_row_count"] = int(len(matched))
    if matched.empty:
        summary["recommended_next_action"] = "recover_more_breakout_matched_rows"
        return pd.DataFrame(columns=BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_COLUMNS), summary

    seed_lookup = pd.DataFrame()
    if not seed.empty:
        seed_lookup = seed.copy()
        if "promote_to_training" not in seed_lookup.columns:
            seed_lookup["promote_to_training"] = False
        summary["gold_seed_row_count"] = int(seed_lookup["promote_to_training"].fillna(False).astype(bool).sum())
        seed_lookup = seed_lookup[
            [
                column
                for column in [
                    "episode_id",
                    "seed_status",
                    "seed_grade",
                    "promote_to_training",
                ]
                if column in seed_lookup.columns
            ]
        ].drop_duplicates(subset=["episode_id"])

    bridge_rows: list[dict[str, Any]] = []
    replay_cache: dict[str, list[dict[str, Any]]] = {}
    for row in matched.to_dict(orient="records"):
        episode_id = _to_text(row.get("episode_id"))
        replay_path = _to_text(row.get("replay_dataset_path"))
        if not replay_path:
            continue
        replay_rows = replay_cache.get(replay_path)
        if replay_rows is None:
            replay_rows = _load_replay_rows(replay_path)
            replay_cache[replay_path] = replay_rows
        record = _match_replay_row(replay_rows, row.get("matched_decision_time"))
        decision_row = record.get("decision_row")
        if not isinstance(decision_row, Mapping):
            continue
        decision_payload = _normalize_decision_payload(decision_row)

        forecast_bridge = {
            "forecast_runtime_summary_v1": build_forecast_runtime_summary_v1(decision_payload),
            "state25_runtime_hint_v1": build_state25_runtime_hint_v1(decision_payload),
        }
        belief_bridge = {
            "belief_runtime_summary_v1": build_belief_runtime_summary_v1(decision_payload),
        }
        barrier_bridge = {
            "barrier_runtime_summary_v1": build_barrier_runtime_summary_v1(decision_payload),
        }
        runtime_payload = build_breakout_event_runtime_v1(
            decision_payload,
            forecast_state25_runtime_bridge_v1=forecast_bridge,
        )
        overlay_payload = build_breakout_event_overlay_candidates_v1(
            decision_payload,
            breakout_event_runtime_v1=runtime_payload,
            forecast_state25_runtime_bridge_v1=forecast_bridge,
            belief_state25_runtime_bridge_v1=belief_bridge,
            barrier_state25_runtime_bridge_v1=barrier_bridge,
        )

        seed_status = ""
        seed_grade = ""
        calibration_scope = "matched_alignment"
        if not seed_lookup.empty:
            matched_seed = seed_lookup.loc[seed_lookup["episode_id"].astype(str) == episode_id]
            if not matched_seed.empty:
                seed_status = _to_text(matched_seed.iloc[0].get("seed_status"))
                seed_grade = _to_text(matched_seed.iloc[0].get("seed_grade"))
                if bool(matched_seed.iloc[0].get("promote_to_training")):
                    calibration_scope = "gold_seed"

        overlay_target = _to_text(overlay_payload.get("candidate_action_target")).upper()
        forecast_summary = forecast_bridge.get("forecast_runtime_summary_v1", {}) if isinstance(forecast_bridge, Mapping) else {}
        barrier_summary = barrier_bridge.get("barrier_runtime_summary_v1", {}) if isinstance(barrier_bridge, Mapping) else {}
        bridge_rows.append(
            {
                "observation_event_id": f"breakout_historical_calibration::{episode_id}",
                "generated_at": generated_at,
                "episode_id": episode_id,
                "symbol": _to_text(row.get("symbol")).upper(),
                "calibration_scope": calibration_scope,
                "seed_status": seed_status,
                "seed_grade": seed_grade,
                "action_target": _to_text(row.get("action_target")).upper(),
                "continuation_target": _to_text(row.get("continuation_target")).upper(),
                "matched_decision_time": _to_text(row.get("matched_decision_time")),
                "time_gap_sec": round(_to_float(row.get("time_gap_sec"), 0.0), 6),
                "runtime_breakout_direction": _to_text(runtime_payload.get("breakout_direction")).upper(),
                "runtime_breakout_state": _to_text(runtime_payload.get("breakout_state")).lower(),
                "runtime_effective_breakout_readiness_state": _to_text(
                    runtime_payload.get("effective_breakout_readiness_state")
                ).upper(),
                "runtime_breakout_type_candidate": _to_text(runtime_payload.get("breakout_type_candidate")).lower(),
                "runtime_breakout_confidence": round(_to_float(runtime_payload.get("breakout_confidence"), 0.0), 6),
                "barrier_total": round(_to_float(barrier_summary.get("barrier_total"), 0.0), 6),
                "confirm_score": round(_to_float(forecast_summary.get("confirm_score"), 0.0), 6),
                "false_break_score": round(_to_float(forecast_summary.get("false_break_score"), 0.0), 6),
                "continuation_score": round(_to_float(forecast_summary.get("continuation_score"), 0.0), 6),
                "overlay_target": overlay_target,
                "overlay_reason_summary": _to_text(overlay_payload.get("reason_summary")),
                "conflict_level": _to_text(overlay_payload.get("conflict_level")).lower(),
                "action_demotion_rule": _to_text(overlay_payload.get("action_demotion_rule")).lower(),
                "historical_alignment_result": _historical_alignment_result(
                    action_target=row.get("action_target"),
                    overlay_target=overlay_target,
                ),
                "replay_dataset_path": replay_path,
            }
        )

    frame = pd.DataFrame(bridge_rows, columns=BREAKOUT_HISTORICAL_CALIBRATION_BRIDGE_COLUMNS)
    summary["bridge_row_count"] = int(len(frame))
    if frame.empty:
        summary["recommended_next_action"] = "rebuild_matched_replay_row_lookup"
        return frame, summary

    summary.update(
        {
            "manual_enter_now_count": int(frame["action_target"].eq("ENTER_NOW").sum()),
            "overlay_enter_now_count": int(frame["overlay_target"].eq("ENTER_NOW").sum()),
            "overlay_probe_count": int(frame["overlay_target"].eq("PROBE_BREAKOUT").sum()),
            "overlay_watch_count": int(frame["overlay_target"].eq("WATCH_BREAKOUT").sum()),
            "overlay_wait_count": int(frame["overlay_target"].eq("WAIT_MORE").sum()),
            "direction_none_count": int(frame["runtime_breakout_direction"].eq("NONE").sum()),
            "historical_alignment_result_counts": json.dumps(
                frame["historical_alignment_result"].value_counts().to_dict(),
                ensure_ascii=False,
                sort_keys=True,
            ),
            "overlay_target_counts": json.dumps(
                frame["overlay_target"].value_counts().to_dict(),
                ensure_ascii=False,
                sort_keys=True,
            ),
            "conflict_level_counts": json.dumps(
                frame["conflict_level"].replace("", pd.NA).dropna().value_counts().to_dict(),
                ensure_ascii=False,
                sort_keys=True,
            )
            if frame["conflict_level"].replace("", pd.NA).dropna().any()
            else "{}",
            "action_demotion_rule_counts": json.dumps(
                frame["action_demotion_rule"].replace("", pd.NA).dropna().value_counts().to_dict(),
                ensure_ascii=False,
                sort_keys=True,
            )
            if frame["action_demotion_rule"].replace("", pd.NA).dropna().any()
            else "{}",
        }
    )

    if summary["overlay_enter_now_count"] > 0:
        summary["recommended_next_action"] = "compare_historical_enter_now_with_live_candidate_bridge"
    elif summary["overlay_probe_count"] > 0 or summary["overlay_watch_count"] > 0:
        summary["recommended_next_action"] = "promote_historical_probe_watch_into_candidate_surface"
    elif summary["direction_none_count"] == len(frame):
        summary["recommended_next_action"] = "inspect_historical_breakout_direction_scale"
    else:
        summary["recommended_next_action"] = "inspect_historical_wait_more_overfire"
    return frame, summary


def render_breakout_historical_calibration_bridge_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    row = dict(summary or {})
    lines = [
        "# Breakout Historical Calibration Bridge",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- alignment_row_count: `{int(_to_float(row.get('alignment_row_count'), 0.0))}`",
        f"- matched_row_count: `{int(_to_float(row.get('matched_row_count'), 0.0))}`",
        f"- gold_seed_row_count: `{int(_to_float(row.get('gold_seed_row_count'), 0.0))}`",
        f"- bridge_row_count: `{int(_to_float(row.get('bridge_row_count'), 0.0))}`",
        f"- manual_enter_now_count: `{int(_to_float(row.get('manual_enter_now_count'), 0.0))}`",
        f"- overlay_enter_now_count: `{int(_to_float(row.get('overlay_enter_now_count'), 0.0))}`",
        f"- overlay_probe_count: `{int(_to_float(row.get('overlay_probe_count'), 0.0))}`",
        f"- overlay_watch_count: `{int(_to_float(row.get('overlay_watch_count'), 0.0))}`",
        f"- overlay_wait_count: `{int(_to_float(row.get('overlay_wait_count'), 0.0))}`",
        f"- direction_none_count: `{int(_to_float(row.get('direction_none_count'), 0.0))}`",
        f"- historical_alignment_result_counts: `{_to_text(row.get('historical_alignment_result_counts'), '{}')}`",
        f"- overlay_target_counts: `{_to_text(row.get('overlay_target_counts'), '{}')}`",
        f"- conflict_level_counts: `{_to_text(row.get('conflict_level_counts'), '{}')}`",
        f"- action_demotion_rule_counts: `{_to_text(row.get('action_demotion_rule_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
    ]
    if frame is not None and not frame.empty:
        preview = frame.head(10).copy()
        lines.extend(["", "## Preview", "", "```text", preview.to_csv(index=False), "```"])
    return "\n".join(lines) + "\n"
