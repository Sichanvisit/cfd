"""Watch MF17 performance and activation guard recovery across iterations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.bounded_symbol_surface_activation_apply import (  # noqa: E402
    build_bounded_symbol_surface_activation_apply,
)
from backend.services.entry_performance_baseline import (  # noqa: E402
    build_entry_performance_regression_watch,
)
from backend.services.mf17_rollout_pending_diagnostic import (  # noqa: E402
    build_mf17_rollout_pending_diagnostic,
)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_shadow_auto_dir() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto"


def _comparison_lookup(regression_watch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = list(regression_watch.get("comparisons", []) or [])
    return {
        str((row or {}).get("symbol", "") or "").upper(): dict(row or {})
        for row in rows
        if str((row or {}).get("symbol", "") or "").strip()
    }


def _activation_lookup(activation_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = list(activation_payload.get("rows", []) or [])
    return {
        str((row or {}).get("market_family", "") or "").upper(): dict(row or {})
        for row in rows
        if str((row or {}).get("market_family", "") or "").strip()
    }


def _run_once(args: argparse.Namespace) -> dict[str, Any]:
    entry_eval_profile = _load_json(args.entry_eval_profile_path)
    runtime_status = _load_json(args.runtime_status_path)
    runtime_loop_debug = _load_json(args.runtime_loop_debug_path)
    baseline_lock = _load_json(args.baseline_json_path)

    regression_watch = build_entry_performance_regression_watch(
        entry_eval_profile,
        baseline_lock,
        runtime_status=runtime_status,
        runtime_loop_debug=runtime_loop_debug,
    )
    _write_json(args.regression_json_output_path, regression_watch)

    activation_frame, resolved_contract, activation_summary = build_bounded_symbol_surface_activation_apply(
        bounded_symbol_surface_activation_contract_payload=_load_json(args.activation_contract_path),
        symbol_surface_manual_signoff_apply_payload=_load_json(args.manual_signoff_apply_path),
        entry_performance_regression_watch_payload=regression_watch,
        runtime_status=runtime_status,
    )
    activation_payload = {
        "summary": activation_summary,
        "rows": activation_frame.to_dict(orient="records"),
        "resolved_contract_path": str(Path(args.resolved_contract_output_path)),
    }
    Path(args.resolved_contract_output_path).parent.mkdir(parents=True, exist_ok=True)
    resolved_contract.to_csv(args.resolved_contract_output_path, index=False, encoding="utf-8-sig")
    activation_frame.to_csv(args.activation_csv_output_path, index=False, encoding="utf-8-sig")
    _write_json(args.activation_json_output_path, activation_payload)

    diagnostic_frame, diagnostic_summary = build_mf17_rollout_pending_diagnostic(
        symbol_surface_preview_evaluation_payload=_load_json(args.preview_evaluation_path),
        bounded_rollout_candidate_gate_payload=_load_json(args.candidate_gate_path),
        bounded_rollout_review_manifest_payload=_load_json(args.review_manifest_path),
        bounded_rollout_signoff_criteria_payload=_load_json(args.signoff_criteria_path),
        symbol_surface_canary_signoff_packet_payload=_load_json(args.signoff_packet_path),
        symbol_surface_manual_signoff_apply_payload=_load_json(args.manual_signoff_apply_path),
        bounded_symbol_surface_activation_contract_payload=_load_json(args.activation_contract_path),
        bounded_symbol_surface_activation_apply_payload=activation_payload,
    )
    diagnostic_payload = {
        "summary": diagnostic_summary,
        "rows": diagnostic_frame.to_dict(orient="records"),
    }
    _write_json(args.diagnostic_json_output_path, diagnostic_payload)

    comparison_lookup = _comparison_lookup(regression_watch)
    activation_lookup = _activation_lookup(activation_payload)
    nas_perf = comparison_lookup.get("NAS100", {})
    xau_perf = comparison_lookup.get("XAUUSD", {})
    xau_activation = activation_lookup.get("XAUUSD", {})

    summary = {
        "contract_version": "mf17_runtime_guard_watch_v1",
        "generated_at": diagnostic_summary.get("generated_at", regression_watch.get("generated_at", "")),
        "reentry_symbols": list(regression_watch.get("reentry_symbols", []) or []),
        "nas_current_elapsed_ms": float(nas_perf.get("current_elapsed_ms", 0.0) or 0.0),
        "nas_reentry_required": bool(nas_perf.get("reentry_required", False)),
        "xau_current_elapsed_ms": float(xau_perf.get("current_elapsed_ms", 0.0) or 0.0),
        "xau_reentry_required": bool(xau_perf.get("reentry_required", False)),
        "xau_activation_state": str(xau_activation.get("activation_state", "") or ""),
        "xau_open_positions_count": int(xau_activation.get("open_positions_count", 0) or 0),
        "pending_stage": str(diagnostic_summary.get("pending_stage", "") or ""),
        "top_blocker_counts": dict(diagnostic_summary.get("top_blocker_counts", {}) or {}),
        "recommended_next_action": str(diagnostic_summary.get("recommended_next_action", "") or ""),
    }
    return {
        "summary": summary,
        "regression_watch": regression_watch,
        "activation": activation_payload,
        "diagnostic": diagnostic_payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-eval-profile-path", default=str(ROOT / "data" / "analysis" / "entry_eval_profile_latest.json"))
    parser.add_argument("--runtime-status-path", default=str(ROOT / "data" / "runtime_status.json"))
    parser.add_argument("--runtime-loop-debug-path", default=str(ROOT / "data" / "runtime_loop_debug.json"))
    parser.add_argument("--baseline-json-path", default=str(_default_shadow_auto_dir() / "entry_performance_baseline_latest.json"))
    parser.add_argument("--regression-json-output-path", default=str(_default_shadow_auto_dir() / "entry_performance_regression_watch_latest.json"))
    parser.add_argument("--preview-evaluation-path", default=str(_default_shadow_auto_dir() / "symbol_surface_preview_evaluation_latest.json"))
    parser.add_argument("--candidate-gate-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_candidate_gate_latest.json"))
    parser.add_argument("--review-manifest-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_review_manifest_latest.json"))
    parser.add_argument("--signoff-criteria-path", default=str(_default_shadow_auto_dir() / "bounded_rollout_signoff_criteria_latest.json"))
    parser.add_argument("--signoff-packet-path", default=str(_default_shadow_auto_dir() / "symbol_surface_canary_signoff_packet_latest.json"))
    parser.add_argument("--manual-signoff-apply-path", default=str(_default_shadow_auto_dir() / "symbol_surface_manual_signoff_apply_latest.json"))
    parser.add_argument("--activation-contract-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_latest.json"))
    parser.add_argument("--activation-csv-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.csv"))
    parser.add_argument("--activation-json-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_apply_latest.json"))
    parser.add_argument("--resolved-contract-output-path", default=str(_default_shadow_auto_dir() / "bounded_symbol_surface_activation_contract_applied.csv"))
    parser.add_argument("--diagnostic-json-output-path", default=str(_default_shadow_auto_dir() / "mf17_rollout_pending_diagnostic_latest.json"))
    parser.add_argument("--json-output-path", default=str(_default_shadow_auto_dir() / "mf17_runtime_guard_watch_latest.json"))
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=int, default=10)
    args = parser.parse_args(argv)

    total_iterations = max(1, int(args.iterations or 1))
    sleep_seconds = max(0, int(args.sleep_seconds or 0))
    iteration_summaries: list[dict[str, Any]] = []
    final_payload: dict[str, Any] = {}

    for iteration_index in range(total_iterations):
        payload = _run_once(args)
        iteration_summary = dict(payload.get("summary", {}) or {})
        iteration_summary["iteration_index"] = int(iteration_index + 1)
        iteration_summaries.append(iteration_summary)
        final_payload = dict(payload)
        if iteration_index < (total_iterations - 1) and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    final_summary = dict(final_payload.get("summary", {}) or {})
    final_summary["iterations"] = int(total_iterations)
    final_summary["sleep_seconds"] = int(sleep_seconds)
    final_payload["summary"] = final_summary
    if total_iterations > 1:
        final_payload["iteration_summaries"] = iteration_summaries

    _write_json(args.json_output_path, final_payload)
    print(json.dumps({"json_output_path": str(Path(args.json_output_path)), **final_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
