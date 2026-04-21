"""Watch live runner growth and rebuild PA5/PA6 artifacts when it appears."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_action_resolver import (  # noqa: E402
    build_checkpoint_management_action_snapshot,
    default_checkpoint_management_action_snapshot_path,
)
from backend.services.path_checkpoint_context import (  # noqa: E402
    default_checkpoint_rows_path,
)
from backend.services.path_checkpoint_dataset import (  # noqa: E402
    build_checkpoint_action_eval,
    build_checkpoint_dataset_artifacts,
    default_checkpoint_action_eval_path,
    default_checkpoint_dataset_path,
    default_checkpoint_dataset_resolved_path,
)
from backend.services.path_checkpoint_live_runner_watch import (  # noqa: E402
    build_checkpoint_live_runner_watch,
    default_checkpoint_live_runner_watch_path,
)
from backend.services.path_checkpoint_open_trade_backfill import (  # noqa: E402
    backfill_open_trade_checkpoint_rows,
    default_runtime_status_detail_path,
    default_trade_db_path,
)
from backend.services.path_checkpoint_position_side_observation import (  # noqa: E402
    build_checkpoint_position_side_observation,
    default_checkpoint_position_side_observation_path,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _run_once(args: argparse.Namespace) -> dict[str, Any]:
    backfill_summary: dict[str, Any] = {}
    if not args.skip_backfill:
        backfill_payload = backfill_open_trade_checkpoint_rows(
            runtime_status_detail_path=args.runtime_status_detail_path,
            trade_db_path=args.trade_db_path,
            checkpoint_rows_path=args.checkpoint_rows_path,
        )
        backfill_summary = dict(backfill_payload.get("summary", {}) or {})

    runtime_status = _load_json(args.runtime_status_detail_path)
    previous_watch_payload = _load_json(args.watch_output_path)
    checkpoint_rows = _load_csv(args.checkpoint_rows_path)

    watch_rows, watch_summary = build_checkpoint_live_runner_watch(
        runtime_status,
        checkpoint_rows,
        previous_summary=dict(previous_watch_payload.get("summary", {}) or {}),
        recent_minutes=max(1, int(args.recent_minutes)),
    )
    _write_json(args.watch_output_path, {"summary": watch_summary, "rows": watch_rows.to_dict(orient="records")})

    live_runner_count = int(watch_summary.get("live_runner_source_row_count", 0) or 0)
    live_runner_delta = int(watch_summary.get("live_runner_source_delta", 0) or 0)
    rebuild_triggered = bool(args.always_rebuild or live_runner_delta > 0 or (live_runner_count > 0 and not previous_watch_payload))
    rebuild_reason = "forced_rebuild" if args.always_rebuild else "await_live_exit_manage_runner_rows"
    if rebuild_triggered and not args.always_rebuild:
        rebuild_reason = "live_runner_growth_detected"

    outputs: dict[str, str] = {
        "watch_output_path": str(Path(args.watch_output_path)),
    }
    downstream_summary: dict[str, Any] = {}
    if rebuild_triggered:
        observation_rows, observation_summary = build_checkpoint_position_side_observation(checkpoint_rows)
        _write_json(args.observation_output_path, {"summary": observation_summary, "rows": observation_rows.to_dict(orient="records")})

        management_rows, management_summary = build_checkpoint_management_action_snapshot(
            runtime_status,
            checkpoint_rows,
            recent_limit=(400 if int(args.recent_limit) <= 0 else int(args.recent_limit)),
        )
        _write_json(args.management_output_path, {"summary": management_summary, "rows": management_rows.to_dict(orient="records")})

        base, resolved, dataset_summary = build_checkpoint_dataset_artifacts(
            checkpoint_rows,
            recent_limit=(None if int(args.recent_limit) <= 0 else int(args.recent_limit)),
        )
        Path(args.dataset_output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.resolved_output_path).parent.mkdir(parents=True, exist_ok=True)
        base.to_csv(args.dataset_output_path, index=False, encoding="utf-8-sig")
        resolved.to_csv(args.resolved_output_path, index=False, encoding="utf-8-sig")

        eval_rows, eval_summary = build_checkpoint_action_eval(resolved)
        _write_json(args.eval_output_path, {"summary": eval_summary, "rows": eval_rows.to_dict(orient="records")})

        outputs.update(
            {
                "observation_output_path": str(Path(args.observation_output_path)),
                "management_output_path": str(Path(args.management_output_path)),
                "dataset_output_path": str(Path(args.dataset_output_path)),
                "resolved_output_path": str(Path(args.resolved_output_path)),
                "eval_output_path": str(Path(args.eval_output_path)),
            }
        )
        downstream_summary = {
            "observation": observation_summary,
            "management": management_summary,
            "dataset": dataset_summary,
            "eval": eval_summary,
        }

    summary = {
        "contract_version": "checkpoint_live_runner_pipeline_v1",
        "generated_at": watch_summary.get("generated_at", ""),
        "runtime_updated_at": watch_summary.get("runtime_updated_at", ""),
        "backfill_appended_count": int(backfill_summary.get("appended_count", 0) or 0),
        "live_runner_source_row_count": live_runner_count,
        "live_runner_source_delta": live_runner_delta,
        "rebuild_triggered": rebuild_triggered,
        "rebuild_reason": rebuild_reason,
        "recommended_next_action": (
            "review_rebuilt_pa5_pa6_artifacts_for_pa7_pa8"
            if rebuild_triggered
            else "keep_runtime_running_until_exit_manage_runner_rows_appear"
        ),
        "outputs": outputs,
    }
    payload = {
        "summary": summary,
        "watch_summary": watch_summary,
        "backfill_summary": backfill_summary,
        "downstream_summary": downstream_summary,
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-detail-path", default=str(default_runtime_status_detail_path()))
    parser.add_argument("--trade-db-path", default=str(default_trade_db_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--watch-output-path", default=str(default_checkpoint_live_runner_watch_path()))
    parser.add_argument("--observation-output-path", default=str(default_checkpoint_position_side_observation_path()))
    parser.add_argument("--management-output-path", default=str(default_checkpoint_management_action_snapshot_path()))
    parser.add_argument("--dataset-output-path", default=str(default_checkpoint_dataset_path()))
    parser.add_argument("--resolved-output-path", default=str(default_checkpoint_dataset_resolved_path()))
    parser.add_argument("--eval-output-path", default=str(default_checkpoint_action_eval_path()))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "checkpoint_live_runner_pipeline_latest.json"))
    parser.add_argument("--recent-minutes", type=int, default=60)
    parser.add_argument("--recent-limit", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=int, default=10)
    parser.add_argument("--skip-backfill", action="store_true")
    parser.add_argument("--always-rebuild", action="store_true")
    args = parser.parse_args(argv)

    iteration_payloads: list[dict[str, Any]] = []
    total_iterations = max(1, int(args.iterations or 1))
    sleep_seconds = max(0, int(args.sleep_seconds or 0))
    final_payload: dict[str, Any] = {}
    for iteration_index in range(total_iterations):
        current_payload = _run_once(args)
        iteration_summary = dict(current_payload.get("summary", {}) or {})
        iteration_summary["iteration_index"] = int(iteration_index + 1)
        iteration_payloads.append(iteration_summary)
        final_payload = dict(current_payload)
        if iteration_index < (total_iterations - 1) and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    final_summary = dict(final_payload.get("summary", {}) or {})
    final_summary["iterations"] = int(total_iterations)
    final_summary["sleep_seconds"] = int(sleep_seconds)
    final_payload["summary"] = final_summary
    if total_iterations > 1:
        final_payload["iteration_summaries"] = iteration_payloads

    _write_json(args.json_output_path, final_payload)
    print(json.dumps({"json_output_path": str(Path(args.json_output_path)), **final_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
