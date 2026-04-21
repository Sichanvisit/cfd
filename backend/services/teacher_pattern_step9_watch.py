"""Step 9 watch report for teacher-pattern state25."""

from __future__ import annotations

from typing import Any

from backend.services.teacher_pattern_execution_handoff import DEFAULT_MIN_LABELED_ROWS


DEFAULT_RECHECK_TOTAL_ROW_DELTA = 100


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _bullet_lines(items: list[str]) -> list[str]:
    rows = [str(item).strip() for item in items if str(item).strip()]
    if rows:
        return [f"- {row}" for row in rows]
    return ["- 없음"]


def _watchlist_rows(
    *,
    full_qa_report: dict[str, Any],
    confusion_report: dict[str, Any],
) -> list[dict[str, Any]]:
    watchlist_pairs = _as_mapping(_as_mapping(full_qa_report.get("confusion_proxy_summary")).get("watchlist_pairs"))
    watchlist_status = {
        str(row.get("pair", "")).strip(): row
        for row in _as_list(confusion_report.get("watchlist_status"))
        if isinstance(row, dict)
    }

    rows: list[dict[str, Any]] = []
    seen_pairs: set[str] = set()
    for pair_key, payload in sorted(watchlist_pairs.items()):
        pair = str(pair_key).strip()
        status_row = _as_mapping(watchlist_status.get(pair))
        rows.append(
            {
                "pair": pair,
                "count": _as_int(_as_mapping(payload).get("count", 0)),
                "ratio": _as_float(_as_mapping(payload).get("ratio", 0.0)),
                "status": str(status_row.get("status", "observe_only") or "observe_only"),
                "summary": str(status_row.get("summary", "") or ""),
            }
        )
        seen_pairs.add(pair)

    for pair, row in sorted(watchlist_status.items()):
        if pair in seen_pairs:
            continue
        rows.append(
            {
                "pair": pair,
                "count": _as_int(row.get("count", 0)),
                "ratio": _as_float(row.get("ratio", 0.0)),
                "status": str(row.get("status", "observe_only") or "observe_only"),
                "summary": str(row.get("summary", "") or ""),
            }
        )
    return rows


def _previous_watchlist_counts(previous_watch_report: dict[str, Any]) -> dict[str, int]:
    watch_items = _as_mapping(previous_watch_report.get("watch_items"))
    watchlist_pairs = _as_mapping(watch_items.get("watchlist_pairs"))
    rows = _as_list(watchlist_pairs.get("pairs"))
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pair = str(row.get("pair", "")).strip()
        if not pair:
            continue
        counts[pair] = _as_int(row.get("count", 0))
    return counts


def _previous_runtime_recycle(previous_watch_report: dict[str, Any]) -> dict[str, Any]:
    return _as_mapping(_as_mapping(previous_watch_report.get("watch_items")).get("runtime_recycle"))


def build_teacher_pattern_step9_watch_report(
    *,
    seed_report: dict[str, Any] | None,
    full_qa_report: dict[str, Any] | None,
    baseline_report: dict[str, Any] | None,
    confusion_report: dict[str, Any] | None,
    execution_handoff_report: dict[str, Any] | None,
    runtime_status_report: dict[str, Any] | None = None,
    previous_watch_report: dict[str, Any] | None = None,
    min_labeled_rows: int = DEFAULT_MIN_LABELED_ROWS,
    min_recheck_total_row_delta: int = DEFAULT_RECHECK_TOTAL_ROW_DELTA,
) -> dict[str, Any]:
    seed = _as_mapping(seed_report)
    full_qa = _as_mapping(full_qa_report)
    baseline = _as_mapping(baseline_report)
    confusion = _as_mapping(confusion_report)
    execution = _as_mapping(execution_handoff_report)
    runtime_status = _as_mapping(runtime_status_report)
    previous = _as_mapping(previous_watch_report)

    pattern_task = _as_mapping(_as_mapping(baseline.get("tasks")).get("pattern_task"))
    pattern_coverage = _as_mapping(full_qa.get("pattern_coverage"))

    total_rows = _as_int(seed.get("total_rows", 0))
    labeled_rows = _as_int(seed.get("labeled_rows", 0))
    unlabeled_rows = _as_int(seed.get("unlabeled_rows", 0))
    covered_primary_count = _as_int(pattern_coverage.get("covered_primary_count", 0))
    supported_pattern_ids = sorted(_as_int(value) for value in _as_list(pattern_task.get("supported_pattern_ids")) if _as_int(value) > 0)
    supported_pattern_count = len(supported_pattern_ids)
    labeled_rows_remaining = max(0, int(min_labeled_rows) - labeled_rows)

    blocker_codes = [
        str(row.get("code", "")).strip()
        for row in _as_list(execution.get("blockers"))
        if isinstance(row, dict) and str(row.get("code", "")).strip()
    ]
    warning_codes = [str(value).strip() for value in _as_list(execution.get("warnings")) if str(value).strip()]
    blocking_seed_only = bool(blocker_codes) and set(blocker_codes) == {"full_qa_seed_shortfall"}

    watchlist_pairs = _watchlist_rows(full_qa_report=full_qa, confusion_report=confusion)
    observed_watchlist_pairs = [row["pair"] for row in watchlist_pairs if _as_int(row.get("count", 0)) > 0]
    pending_watchlist_pairs = [row["pair"] for row in watchlist_pairs if _as_int(row.get("count", 0)) <= 0]

    previous_snapshot = _as_mapping(previous.get("snapshot"))
    previous_total_rows = _as_int(previous_snapshot.get("total_rows", 0))
    previous_labeled_rows = _as_int(previous_snapshot.get("labeled_rows", 0))
    previous_supported_pattern_ids = {
        _as_int(value)
        for value in _as_list(previous_snapshot.get("supported_pattern_ids"))
        if _as_int(value) > 0
    }
    previous_blocker_codes = set(
        str(value).strip()
        for value in _as_list(_as_mapping(_as_mapping(previous.get("watch_items")).get("execution_handoff")).get("blocker_codes"))
        if str(value).strip()
    )

    total_row_delta = total_rows - previous_total_rows if previous_total_rows > 0 else 0
    labeled_row_delta = labeled_rows - previous_labeled_rows if previous_labeled_rows > 0 else 0
    has_previous_watch = bool(previous)
    supported_pattern_delta = sorted(set(supported_pattern_ids) - previous_supported_pattern_ids) if has_previous_watch else []
    blocker_codes_changed = bool(previous_blocker_codes) and previous_blocker_codes != set(blocker_codes)

    previous_watchlist_counts = _previous_watchlist_counts(previous)
    new_watchlist_pairs = [
        row["pair"]
        for row in watchlist_pairs
        if has_previous_watch and _as_int(row.get("count", 0)) > 0 and previous_watchlist_counts.get(str(row.get("pair", "")), 0) <= 0
    ]

    runtime_recycle = _as_mapping(runtime_status.get("runtime_recycle"))
    previous_runtime_recycle = _previous_runtime_recycle(previous)
    runtime_log_only_count = _as_int(runtime_recycle.get("log_only_count", 0))
    previous_runtime_log_only_count = _as_int(previous_runtime_recycle.get("log_only_count", 0))
    runtime_cycle_advanced = bool(previous_runtime_recycle) and runtime_log_only_count > previous_runtime_log_only_count

    recheck_reasons: list[str] = []
    if _as_int(min_recheck_total_row_delta) > 0 and previous_total_rows > 0 and total_row_delta >= int(min_recheck_total_row_delta):
        recheck_reasons.append("fresh_closed_plus_100")
    if new_watchlist_pairs:
        recheck_reasons.append("new_watchlist_pair_observed")
    if supported_pattern_delta:
        recheck_reasons.append("supported_pattern_changed")
    if blocker_codes_changed:
        recheck_reasons.append("execution_blocker_set_changed")
    if bool(execution.get("execution_handoff_ready", False)):
        recheck_reasons.append("execution_handoff_ready")

    recheck_status = "recheck_now" if recheck_reasons else "watch_only"

    runtime_watch: dict[str, Any] = {}
    if runtime_recycle:
        runtime_watch = {
            "mode": str(runtime_recycle.get("mode", "") or ""),
            "last_status": str(runtime_recycle.get("last_status", "") or ""),
            "last_reason": str(runtime_recycle.get("last_reason", "") or ""),
            "last_block_reason": str(runtime_recycle.get("last_block_reason", "") or ""),
            "log_only_count": runtime_log_only_count,
            "reexec_count": _as_int(runtime_recycle.get("reexec_count", 0)),
            "next_due_at": str(runtime_recycle.get("next_due_at", "") or ""),
            "runtime_cycle_advanced_since_last_watch": runtime_cycle_advanced,
        }

    recommended_actions: list[str] = []
    if labeled_rows_remaining > 0:
        recommended_actions.append("Continue accumulating labeled rows toward the 10K execution-handoff seed target.")
    if pending_watchlist_pairs:
        recommended_actions.append("Keep observing the watchlist pairs during live accumulation instead of forcing a new retune.")
    if recheck_status == "recheck_now":
        recommended_actions.append("Re-run the E4/E5 checkpoint because a watch milestone changed since the last watch snapshot.")
    if runtime_watch and runtime_watch.get("mode") == "log_only":
        recommended_actions.append("Keep runtime recycle in log_only until at least one observed cycle is captured cleanly.")

    return {
        "contract_version": "teacher_pattern_step9_watch_v1",
        "operating_mode": "accumulate_watch_recheck",
        "snapshot": {
            "total_rows": total_rows,
            "labeled_rows": labeled_rows,
            "unlabeled_rows": unlabeled_rows,
            "target_labeled_rows": int(min_labeled_rows),
            "rows_to_target": labeled_rows_remaining,
            "labeled_progress_ratio": float(labeled_rows / min_labeled_rows) if min_labeled_rows else 0.0,
            "covered_primary_count": covered_primary_count,
            "supported_pattern_ids": supported_pattern_ids,
            "supported_pattern_count": supported_pattern_count,
        },
        "watch_items": {
            "seed_accumulation": {
                "status": "target_met" if labeled_rows_remaining <= 0 else "accumulating",
                "labeled_rows": labeled_rows,
                "target_labeled_rows": int(min_labeled_rows),
                "remaining_labeled_rows": labeled_rows_remaining,
            },
            "watchlist_pairs": {
                "status": "observed" if observed_watchlist_pairs else "observe_only",
                "pairs": watchlist_pairs,
                "observed_pairs": observed_watchlist_pairs,
                "pending_pairs": pending_watchlist_pairs,
            },
            "execution_handoff": {
                "handoff_status": str(execution.get("handoff_status", "") or ""),
                "execution_handoff_ready": bool(execution.get("execution_handoff_ready", False)),
                "blocker_codes": blocker_codes,
                "warning_codes": warning_codes,
                "blocking_seed_only": blocking_seed_only,
            },
            "runtime_recycle": runtime_watch,
        },
        "changes_since_last_watch": {
            "has_previous_watch": has_previous_watch,
            "total_row_delta": total_row_delta,
            "labeled_row_delta": labeled_row_delta,
            "supported_pattern_delta": supported_pattern_delta,
            "new_watchlist_pairs": new_watchlist_pairs,
            "blocker_codes_changed": blocker_codes_changed,
            "runtime_recycle_cycle_advanced": runtime_cycle_advanced,
        },
        "recheck_timing": {
            "status": recheck_status,
            "reasons": recheck_reasons,
            "reference_total_rows": previous_total_rows,
            "fresh_closed_delta": total_row_delta,
            "fresh_closed_recheck_threshold": int(min_recheck_total_row_delta),
            "rows_until_next_fresh_close_recheck": max(
                0,
                int(min_recheck_total_row_delta) - max(0, total_row_delta),
            )
            if previous_total_rows > 0
            else int(min_recheck_total_row_delta),
        },
        "recommended_actions": recommended_actions,
    }


def render_teacher_pattern_step9_watch_markdown(report: dict[str, Any] | None) -> str:
    payload = _as_mapping(report)
    snapshot = _as_mapping(payload.get("snapshot"))
    watch_items = _as_mapping(payload.get("watch_items"))
    seed_item = _as_mapping(watch_items.get("seed_accumulation"))
    watchlist_item = _as_mapping(watch_items.get("watchlist_pairs"))
    execution_item = _as_mapping(watch_items.get("execution_handoff"))
    runtime_item = _as_mapping(watch_items.get("runtime_recycle"))
    changes = _as_mapping(payload.get("changes_since_last_watch"))
    recheck = _as_mapping(payload.get("recheck_timing"))
    watchlist_rows = [row for row in _as_list(watchlist_item.get("pairs")) if isinstance(row, dict)]

    watchlist_lines = []
    for row in watchlist_rows:
        pair = str(row.get("pair", "")).strip()
        count = _as_int(row.get("count", 0))
        status = str(row.get("status", "")).strip() or "observe_only"
        summary = str(row.get("summary", "")).strip()
        line = f"`{pair}`: count `{count}`, status `{status}`"
        if summary:
            line += f", {summary}"
        watchlist_lines.append(line)

    blocker_lines = _bullet_lines([f"`{str(code).strip()}`" for code in _as_list(execution_item.get("blocker_codes")) if str(code).strip()])
    action_lines = _bullet_lines([str(text) for text in _as_list(payload.get("recommended_actions"))])
    reason_lines = _bullet_lines([str(text) for text in _as_list(recheck.get("reasons"))])

    lines = [
        "# Teacher Pattern Step9 Watch Report",
        "",
        "## 한 줄 요약",
        "",
        f"- 현재 상태: `{str(recheck.get('status', '') or 'watch_only')}`",
        f"- labeled rows: `{_as_int(snapshot.get('labeled_rows', 0))}` / `{_as_int(snapshot.get('target_labeled_rows', 0))}`",
        f"- rows to target: `{_as_int(snapshot.get('rows_to_target', 0))}`",
        f"- covered primary count: `{_as_int(snapshot.get('covered_primary_count', 0))}`",
        f"- supported pattern ids: `{', '.join(str(v) for v in _as_list(snapshot.get('supported_pattern_ids')) if str(v))}`",
        f"- execution handoff status: `{str(execution_item.get('handoff_status', '') or 'UNKNOWN')}`",
        "",
        "## 지금 보면 되는 것",
        "",
        f"- seed accumulation: `{str(seed_item.get('status', '') or 'unknown')}`",
        f"- watchlist status: `{str(watchlist_item.get('status', '') or 'unknown')}`",
        f"- E5 blocker가 seed만 남았는지: `{bool(execution_item.get('blocking_seed_only', False))}`",
        f"- runtime recycle mode: `{str(runtime_item.get('mode', '') or 'unavailable')}`",
        "",
        "## watchlist pair",
        "",
        *_bullet_lines(watchlist_lines),
        "",
        "## E5 blocker",
        "",
        *blocker_lines,
        "",
        "## runtime recycle",
        "",
        f"- mode: `{str(runtime_item.get('mode', '') or 'unavailable')}`",
        f"- last status: `{str(runtime_item.get('last_status', '') or '')}`",
        f"- last reason: `{str(runtime_item.get('last_reason', '') or '')}`",
        f"- last block reason: `{str(runtime_item.get('last_block_reason', '') or '')}`",
        f"- log_only_count: `{_as_int(runtime_item.get('log_only_count', 0))}`",
        f"- next due at: `{str(runtime_item.get('next_due_at', '') or '')}`",
        "",
        "## 지난 watch 대비 변화",
        "",
        f"- has previous watch: `{bool(changes.get('has_previous_watch', False))}`",
        f"- total row delta: `{_as_int(changes.get('total_row_delta', 0))}`",
        f"- labeled row delta: `{_as_int(changes.get('labeled_row_delta', 0))}`",
        f"- supported pattern delta: `{', '.join(str(v) for v in _as_list(changes.get('supported_pattern_delta')) if str(v)) or '없음'}`",
        f"- new watchlist pairs: `{', '.join(str(v) for v in _as_list(changes.get('new_watchlist_pairs')) if str(v)) or '없음'}`",
        "",
        "## 재확인 타이밍",
        "",
        f"- status: `{str(recheck.get('status', '') or 'watch_only')}`",
        f"- fresh closed delta: `{_as_int(recheck.get('fresh_closed_delta', 0))}` / `{_as_int(recheck.get('fresh_closed_recheck_threshold', 0))}`",
        f"- rows until next fresh-close recheck: `{_as_int(recheck.get('rows_until_next_fresh_close_recheck', 0))}`",
        "",
        "recheck reasons:",
        *reason_lines,
        "",
        "## 추천 액션",
        "",
        *action_lines,
    ]
    return "\n".join(lines).strip() + "\n"
