from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.path_checkpoint_action_resolver import (
    build_checkpoint_management_action_snapshot,
    default_checkpoint_management_action_snapshot_path,
)
from backend.services.path_checkpoint_context import default_checkpoint_rows_path
from backend.services.path_checkpoint_dataset import (
    build_checkpoint_action_eval,
    build_checkpoint_dataset_artifacts,
    build_checkpoint_scene_dataset_artifacts,
    build_checkpoint_scene_eval,
    default_checkpoint_action_eval_path,
    default_checkpoint_dataset_path,
    default_checkpoint_dataset_resolved_path,
    default_checkpoint_scene_dataset_path,
    default_checkpoint_scene_eval_path,
)
from backend.services.path_checkpoint_live_runner_watch import (
    build_checkpoint_live_runner_watch,
    default_checkpoint_live_runner_watch_path,
)
from backend.services.path_checkpoint_pa7_review_processor import (
    build_checkpoint_pa7_review_processor,
)
from backend.services.path_checkpoint_pa78_review_packet import (
    build_checkpoint_pa78_review_packet,
    default_checkpoint_pa78_review_packet_path,
)
from backend.services.path_checkpoint_pa8_canary_refresh import (
    build_checkpoint_pa8_canary_refresh_board,
    write_checkpoint_pa8_canary_refresh_outputs,
)
from backend.services.path_checkpoint_pa8_historical_replay import (
    build_checkpoint_pa8_historical_replay_board,
    write_checkpoint_pa8_historical_replay_outputs,
)
from backend.services.path_checkpoint_position_side_observation import (
    build_checkpoint_position_side_observation,
    default_checkpoint_position_side_observation_path,
)
from backend.services.path_checkpoint_scene_bias_preview import (
    build_trend_exhaustion_scene_bias_preview,
    default_checkpoint_trend_exhaustion_scene_bias_preview_path,
)
from backend.services.path_checkpoint_scene_candidate_pipeline import (
    default_checkpoint_scene_candidate_root,
)
from backend.services.path_checkpoint_scene_disagreement_audit import (
    build_checkpoint_scene_disagreement_audit,
    default_checkpoint_scene_disagreement_audit_path,
)
from backend.services.path_checkpoint_scene_runtime_bridge import (
    build_checkpoint_scene_log_only_bridge_report,
    default_checkpoint_scene_log_only_bridge_report_path,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_ANALYSIS_REFRESH_CONTRACT_VERSION = "checkpoint_analysis_refresh_chain_v1"
DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_RECENT_LIMIT = 2000
DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_LOCK_TTL_SECONDS = 1800


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_analysis_refresh_state_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_analysis_refresh_state_latest.json"


def default_checkpoint_analysis_refresh_report_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_analysis_refresh_latest.json"


def default_checkpoint_analysis_refresh_markdown_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_analysis_refresh_latest.md"


def default_checkpoint_analysis_refresh_lock_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_analysis_refresh.lock"


def default_checkpoint_pa7_review_processor_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa7_review_processor_latest.json"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_rows_payload_json(path: str | Path) -> dict[str, Any]:
    payload = _load_json(path)
    summary = _mapping(payload.get("summary"))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    return {"summary": summary, "rows": rows}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _count_csv_rows(path: str | Path) -> int:
    file_path = Path(path)
    if not file_path.exists():
        return 0
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _render_checkpoint_analysis_refresh_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    steps = list(body.get("steps", []) or [])
    lines: list[str] = []
    lines.append("# Checkpoint Analysis Refresh Chain")
    lines.append("")
    for key in (
        "trigger_state",
        "row_count_before",
        "row_count_after",
        "row_delta",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        lines.append(f"### {_to_text(step.get('step_id'))}")
        lines.append("")
        for key in ("status", "row_count", "match_rate", "notes"):
            if key in step:
                lines.append(f"- {key}: `{step.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_rows_payload_json(path: str | Path, rows: pd.DataFrame, summary: Mapping[str, Any]) -> None:
    _write_json(path, {"summary": dict(summary), "rows": rows.to_dict(orient="records")})


def _build_refresh_chain_payload(
    *,
    checkpoint_rows_path: str | Path,
    runtime_updated_at: str = "",
    recent_limit: int | None = None,
    include_deep_scene_review: bool = False,
) -> dict[str, Any]:
    checkpoint_rows = _load_csv(checkpoint_rows_path)
    runtime_updated_at_text = _to_text(runtime_updated_at, now_kst_dt().isoformat())

    base_dataset, resolved_dataset, dataset_summary = build_checkpoint_dataset_artifacts(
        checkpoint_rows,
        recent_limit=recent_limit,
    )
    Path(default_checkpoint_dataset_path()).parent.mkdir(parents=True, exist_ok=True)
    base_dataset.to_csv(default_checkpoint_dataset_path(), index=False, encoding="utf-8-sig")
    resolved_dataset.to_csv(default_checkpoint_dataset_resolved_path(), index=False, encoding="utf-8-sig")

    action_eval_rows, action_eval_summary = build_checkpoint_action_eval(resolved_dataset)
    _write_rows_payload_json(default_checkpoint_action_eval_path(), action_eval_rows, action_eval_summary)

    observation_rows, observation_summary = build_checkpoint_position_side_observation(checkpoint_rows)
    _write_rows_payload_json(default_checkpoint_position_side_observation_path(), observation_rows, observation_summary)

    previous_watch = _load_json(default_checkpoint_live_runner_watch_path())
    live_runner_rows, live_runner_summary = build_checkpoint_live_runner_watch(
        {"updated_at": runtime_updated_at_text},
        checkpoint_rows,
        previous_summary=_mapping(previous_watch.get("summary")),
        recent_minutes=60,
    )
    _write_rows_payload_json(default_checkpoint_live_runner_watch_path(), live_runner_rows, live_runner_summary)

    management_rows, management_summary = build_checkpoint_management_action_snapshot(
        {"updated_at": runtime_updated_at_text},
        checkpoint_rows,
        recent_limit=(400 if recent_limit in (None, 0) else int(recent_limit)),
    )
    _write_rows_payload_json(default_checkpoint_management_action_snapshot_path(), management_rows, management_summary)

    scene_dataset, scene_dataset_summary = build_checkpoint_scene_dataset_artifacts(
        resolved_dataset,
        recent_limit=recent_limit,
    )
    Path(default_checkpoint_scene_dataset_path()).parent.mkdir(parents=True, exist_ok=True)
    scene_dataset.to_csv(default_checkpoint_scene_dataset_path(), index=False, encoding="utf-8-sig")

    scene_eval_rows, scene_eval_summary = build_checkpoint_scene_eval(scene_dataset)
    _write_rows_payload_json(default_checkpoint_scene_eval_path(), scene_eval_rows, scene_eval_summary)

    candidate_root = default_checkpoint_scene_candidate_root()
    bridge_rows, bridge_summary = build_checkpoint_scene_log_only_bridge_report(
        scene_dataset,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
        ensure_active_state=True,
    )
    _write_rows_payload_json(default_checkpoint_scene_log_only_bridge_report_path(), bridge_rows, bridge_summary)

    if include_deep_scene_review:
        disagreement_rows, disagreement_summary = build_checkpoint_scene_disagreement_audit(
            resolved_dataset,
            active_state_path=candidate_root / "active_candidate_state.json",
            latest_run_path=candidate_root / "latest_candidate_run.json",
        )
        disagreement_payload = {
            "summary": disagreement_summary,
            "rows": disagreement_rows.to_dict(orient="records"),
        }
        _write_rows_payload_json(default_checkpoint_scene_disagreement_audit_path(), disagreement_rows, disagreement_summary)

        preview_rows, preview_summary = build_trend_exhaustion_scene_bias_preview(
            resolved_dataset,
            active_state_path=candidate_root / "active_candidate_state.json",
            latest_run_path=candidate_root / "latest_candidate_run.json",
            confidence_threshold=0.75,
        )
        preview_payload = {
            "summary": preview_summary,
            "rows": preview_rows.to_dict(orient="records"),
        }
        _write_rows_payload_json(default_checkpoint_trend_exhaustion_scene_bias_preview_path(), preview_rows, preview_summary)
    else:
        disagreement_payload = _load_rows_payload_json(default_checkpoint_scene_disagreement_audit_path())
        preview_payload = _load_rows_payload_json(default_checkpoint_trend_exhaustion_scene_bias_preview_path())
        disagreement_summary = _mapping(disagreement_payload.get("summary"))
        preview_summary = _mapping(preview_payload.get("summary"))

    pa7_review_processor_payload = build_checkpoint_pa7_review_processor(resolved_dataset)
    _write_json(default_checkpoint_pa7_review_processor_path(), pa7_review_processor_payload)

    pa78_payload = build_checkpoint_pa78_review_packet(
        action_eval_payload={"summary": action_eval_summary, "rows": action_eval_rows.to_dict(orient="records")},
        observation_payload={"summary": observation_summary, "rows": observation_rows.to_dict(orient="records")},
        live_runner_watch_payload={"summary": live_runner_summary, "rows": live_runner_rows.to_dict(orient="records")},
        pa7_review_processor_payload=pa7_review_processor_payload,
        scene_disagreement_payload=disagreement_payload,
        scene_bias_preview_payload=preview_payload,
    )
    _write_json(default_checkpoint_pa78_review_packet_path(), pa78_payload)

    pa8_refresh_payload = build_checkpoint_pa8_canary_refresh_board(resolved_dataset)
    write_checkpoint_pa8_canary_refresh_outputs(pa8_refresh_payload)

    historical_replay_payload = build_checkpoint_pa8_historical_replay_board(resolved_dataset)
    write_checkpoint_pa8_historical_replay_outputs(historical_replay_payload)

    return {
        "dataset_summary": dataset_summary,
        "action_eval_summary": action_eval_summary,
        "observation_summary": observation_summary,
        "live_runner_watch_summary": live_runner_summary,
        "management_summary": management_summary,
        "scene_dataset_summary": scene_dataset_summary,
        "scene_eval_summary": scene_eval_summary,
        "scene_bridge_summary": bridge_summary,
        "scene_disagreement_summary": disagreement_summary,
        "scene_bias_preview_summary": preview_summary,
        "deep_scene_review_refreshed": bool(include_deep_scene_review),
        "pa7_review_processor_summary": _mapping(pa7_review_processor_payload.get("summary")),
        "pa78_review_packet_summary": _mapping(pa78_payload.get("summary")),
        "pa8_refresh_summary": _mapping(pa8_refresh_payload.get("summary")),
        "pa8_historical_replay_summary": _mapping(historical_replay_payload.get("summary")),
    }


def maybe_refresh_checkpoint_analysis_chain(
    *,
    checkpoint_rows_path: str | Path | None = None,
    runtime_updated_at: str = "",
    min_interval_seconds: int = 300,
    min_new_rows: int = 25,
    force: bool = False,
    recent_limit: int | None = DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_RECENT_LIMIT,
    state_path: str | Path | None = None,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    lock_path: str | Path | None = None,
    lock_ttl_seconds: int = DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_LOCK_TTL_SECONDS,
    include_deep_scene_review: bool = False,
) -> dict[str, Any]:
    rows_path = Path(checkpoint_rows_path or default_checkpoint_rows_path())
    state_file = Path(state_path or default_checkpoint_analysis_refresh_state_path())
    report_file = Path(report_path or default_checkpoint_analysis_refresh_report_path())
    markdown_file = Path(markdown_path or default_checkpoint_analysis_refresh_markdown_path())
    lock_file = Path(lock_path or default_checkpoint_analysis_refresh_lock_path())
    now = now_kst_dt()
    row_count = _count_csv_rows(rows_path)
    prior_state = _load_json(state_file)
    prior_summary = _mapping(prior_state.get("summary"))
    last_refresh_row_count = _to_int(prior_summary.get("row_count_after"))
    last_refresh_at_text = _to_text(prior_summary.get("refreshed_at"))
    elapsed_seconds = None
    if last_refresh_at_text:
        try:
            elapsed_seconds = int((now - pd.to_datetime(last_refresh_at_text)).total_seconds())
        except Exception:
            elapsed_seconds = None
    row_delta = max(0, row_count - last_refresh_row_count)

    if not rows_path.exists():
        payload = {
            "summary": {
                "contract_version": PATH_CHECKPOINT_ANALYSIS_REFRESH_CONTRACT_VERSION,
                "generated_at": now.isoformat(),
                "trigger_state": "SKIP_CHECKPOINT_ROWS_MISSING",
                "row_count_before": last_refresh_row_count,
                "row_count_after": row_count,
                "row_delta": row_delta,
                "recommended_next_action": "wait_for_checkpoint_rows_before_refresh",
            },
            "steps": [],
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_checkpoint_analysis_refresh_markdown(payload))
        return payload

    if lock_file.exists():
        lock_age_seconds = None
        try:
            lock_age_seconds = int((now - datetime.fromisoformat(lock_file.read_text(encoding="utf-8").strip())).total_seconds())
        except Exception:
            try:
                lock_age_seconds = int(now.timestamp() - lock_file.stat().st_mtime)
            except Exception:
                lock_age_seconds = None
        if lock_age_seconds is not None and lock_age_seconds > max(60, int(lock_ttl_seconds)):
            try:
                lock_file.unlink()
            except OSError:
                pass

    if lock_file.exists():
        payload = {
            "summary": {
                "contract_version": PATH_CHECKPOINT_ANALYSIS_REFRESH_CONTRACT_VERSION,
                "generated_at": now.isoformat(),
                "trigger_state": "SKIP_LOCKED",
                "row_count_before": last_refresh_row_count,
                "row_count_after": row_count,
                "row_delta": row_delta,
                "recommended_next_action": "wait_for_inflight_refresh_completion_or_clear_stale_lock",
            },
            "steps": [],
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_checkpoint_analysis_refresh_markdown(payload))
        return payload

    throttled = (
        not force
        and elapsed_seconds is not None
        and elapsed_seconds < max(0, int(min_interval_seconds))
        and row_delta < max(1, int(min_new_rows))
    )
    if throttled:
        payload = {
            "summary": {
                "contract_version": PATH_CHECKPOINT_ANALYSIS_REFRESH_CONTRACT_VERSION,
                "generated_at": now.isoformat(),
                "trigger_state": "SKIP_THROTTLED",
                "row_count_before": last_refresh_row_count,
                "row_count_after": row_count,
                "row_delta": row_delta,
                "last_refresh_at": last_refresh_at_text,
                "min_interval_seconds": int(min_interval_seconds),
                "min_new_rows": int(min_new_rows),
                "recommended_next_action": "wait_for_more_rows_or_force_refresh",
            },
            "steps": [],
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_checkpoint_analysis_refresh_markdown(payload))
        return payload

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(now.isoformat(), encoding="utf-8")
    try:
        chain = _build_refresh_chain_payload(
            checkpoint_rows_path=rows_path,
            runtime_updated_at=runtime_updated_at,
            recent_limit=recent_limit,
            include_deep_scene_review=include_deep_scene_review,
        )
        payload = {
            "summary": {
                "contract_version": PATH_CHECKPOINT_ANALYSIS_REFRESH_CONTRACT_VERSION,
                "generated_at": now.isoformat(),
                "trigger_state": "REFRESHED",
                "refreshed_at": now.isoformat(),
                "row_count_before": last_refresh_row_count,
                "row_count_after": row_count,
                "row_delta": row_delta,
                "recent_limit": int(recent_limit) if recent_limit not in (None, 0) else 0,
                "include_deep_scene_review": bool(include_deep_scene_review),
                "recommended_next_action": "use_fresh_reports_and_keep_refresh_chain_running",
            },
            "steps": [
                {
                    "step_id": "dataset",
                    "status": "written",
                    "row_count": _to_int(_mapping(chain.get("dataset_summary")).get("resolved_row_count")),
                    "notes": str(default_checkpoint_dataset_resolved_path()),
                },
                {
                    "step_id": "action_eval",
                    "status": "written",
                    "match_rate": _to_float(_mapping(chain.get("action_eval_summary")).get("runtime_proxy_match_rate")),
                    "notes": str(default_checkpoint_action_eval_path()),
                },
                {
                    "step_id": "scene_bridge",
                    "status": "written",
                    "match_rate": _to_float(_mapping(chain.get("scene_bridge_summary")).get("runtime_candidate_scene_match_rate")),
                    "notes": str(default_checkpoint_scene_log_only_bridge_report_path()),
                },
                {
                    "step_id": "scene_disagreement",
                    "status": "written" if include_deep_scene_review else "reused",
                    "row_count": _to_int(_mapping(chain.get("scene_disagreement_summary")).get("high_conf_scene_disagreement_count")),
                    "notes": str(default_checkpoint_scene_disagreement_audit_path()),
                },
                {
                    "step_id": "scene_bias_preview",
                    "status": "written" if include_deep_scene_review else "reused",
                    "row_count": _to_int(_mapping(chain.get("scene_bias_preview_summary")).get("preview_changed_row_count")),
                    "notes": str(default_checkpoint_trend_exhaustion_scene_bias_preview_path()),
                },
                {
                    "step_id": "pa78_review_packet",
                    "status": "written",
                    "row_count": _to_int(_mapping(chain.get("pa78_review_packet_summary")).get("resolved_row_count")),
                    "notes": str(default_checkpoint_pa78_review_packet_path()),
                },
                {
                    "step_id": "pa8_refresh_board",
                    "status": "written",
                    "row_count": _to_int(_mapping(chain.get("pa8_refresh_summary")).get("active_symbol_count")),
                    "notes": "checkpoint_pa8_canary_refresh_board_latest.json",
                },
                {
                    "step_id": "pa8_historical_replay",
                    "status": "written",
                    "row_count": _to_int(_mapping(chain.get("pa8_historical_replay_summary")).get("replay_ready_count")),
                    "notes": "checkpoint_pa8_historical_replay_board_latest.json",
                },
            ],
            "chain": chain,
        }
        _write_json(state_file, payload)
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_checkpoint_analysis_refresh_markdown(payload))
        return payload
    finally:
        try:
            lock_file.unlink()
        except OSError:
            pass
