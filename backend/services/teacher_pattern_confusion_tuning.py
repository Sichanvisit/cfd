"""Step 9-E4 top confusion-pair tuning report for teacher-pattern state25."""

from __future__ import annotations

from typing import Any


DEFAULT_MIN_CONFUSION_COUNT = 3
DEFAULT_MIN_CONFUSION_RATIO = 0.01

PAIR_ACTION_MAP: dict[str, dict[str, str]] = {
    "1-5": {
        "summary": "Disambiguate quiet loose range from explicit range-reversal setups.",
        "rule_focus": "Reduce loose-market fallback when range reversal setup and reversal-risk are explicit; strengthen pattern 5 proxy even when retest/doji detail is sparse.",
    },
    "5-10": {
        "summary": "Separate active range reversal from empty sideways chop.",
        "rule_focus": "Require reversal-risk or range-reversal setup for pattern 5 and keep pattern 10 for neutral chop without reversal pressure.",
    },
    "12-23": {
        "summary": "Separate breakout-ready compression from triangle squeeze.",
        "rule_focus": "Tighten compression thresholds and promote secondary attach when both squeeze and breakout readiness are high.",
    },
    "2-16": {
        "summary": "Separate broad volatility from fakeout reversal.",
        "rule_focus": "Use wick asymmetry and false-break evidence to keep fakeout reversal distinct from generic volatility.",
    },
}

GROUP_ACTION_MAP: dict[str, dict[str, str]] = {
    "A->D": {
        "summary": "Reduce neutral/chop fallback inside explicit reversal-range contexts.",
        "rule_focus": "Prefer D-group when reversal-risk is explicit and setup_id already implies range reversal; keep A-group for truly passive thin/noise conditions.",
    },
}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_pair(true_label: str, pred_label: str) -> str:
    left, right = sorted((str(true_label), str(pred_label)))
    return f"{left}-{right}"


def _severity(*, count: int, ratio: float) -> str:
    if count >= 10 or ratio >= 0.03:
        return "high"
    if count >= 5 or ratio >= 0.015:
        return "medium"
    return "observe"


def _pattern_candidate(confusion: dict[str, Any]) -> dict[str, Any]:
    true_label = str(confusion.get("true_label", "") or "")
    pred_label = str(confusion.get("pred_label", "") or "")
    pair_key = _normalize_pair(true_label, pred_label)
    count = int(confusion.get("count", 0) or 0)
    ratio = float(confusion.get("ratio", 0.0) or 0.0)
    action = PAIR_ACTION_MAP.get(
        pair_key,
        {
            "summary": "Inspect the top observed pattern confusion before touching execution.",
            "rule_focus": "Review threshold overlap, secondary attach rules, and setup-specific proxy fields around this pair.",
        },
    )
    return {
        "pair": pair_key,
        "true_label": true_label,
        "pred_label": pred_label,
        "count": count,
        "ratio": ratio,
        "severity": _severity(count=count, ratio=ratio),
        "summary": action["summary"],
        "rule_focus": action["rule_focus"],
    }


def _group_candidate(confusion: dict[str, Any]) -> dict[str, Any]:
    true_label = str(confusion.get("true_label", "") or "")
    pred_label = str(confusion.get("pred_label", "") or "")
    pair_key = f"{true_label}->{pred_label}"
    count = int(confusion.get("count", 0) or 0)
    ratio = float(confusion.get("ratio", 0.0) or 0.0)
    action = GROUP_ACTION_MAP.get(
        pair_key,
        {
            "summary": "Inspect the dominant group confusion before adding new pattern rules.",
            "rule_focus": "Review fallback/noise rules and the strongest proxy signals that currently push rows across group boundaries.",
        },
    )
    return {
        "pair": pair_key,
        "true_label": true_label,
        "pred_label": pred_label,
        "count": count,
        "ratio": ratio,
        "severity": _severity(count=count, ratio=ratio),
        "summary": action["summary"],
        "rule_focus": action["rule_focus"],
    }


def build_teacher_pattern_confusion_tuning_report(
    *,
    full_qa_report: dict[str, Any] | None,
    baseline_report: dict[str, Any] | None,
    min_confusion_count: int = DEFAULT_MIN_CONFUSION_COUNT,
    min_confusion_ratio: float = DEFAULT_MIN_CONFUSION_RATIO,
) -> dict[str, Any]:
    full_qa = _as_mapping(full_qa_report)
    baseline = _as_mapping(baseline_report)
    tasks = _as_mapping(baseline.get("tasks"))
    group_task = _as_mapping(tasks.get("group_task"))
    pattern_task = _as_mapping(tasks.get("pattern_task"))

    raw_group_confusions = _as_list(group_task.get("top_confusions"))
    raw_pattern_confusions = _as_list(pattern_task.get("top_confusions"))

    group_candidates = [
        _group_candidate(confusion)
        for confusion in raw_group_confusions
        if int(confusion.get("count", 0) or 0) >= int(min_confusion_count)
        or float(confusion.get("ratio", 0.0) or 0.0) >= float(min_confusion_ratio)
    ]
    pattern_candidates = [
        _pattern_candidate(confusion)
        for confusion in raw_pattern_confusions
        if int(confusion.get("count", 0) or 0) >= int(min_confusion_count)
        or float(confusion.get("ratio", 0.0) or 0.0) >= float(min_confusion_ratio)
    ]

    confusion_proxy = _as_mapping(full_qa.get("confusion_proxy_summary"))
    watchlist_pairs = _as_mapping(confusion_proxy.get("watchlist_pairs"))
    watchlist_status = []
    for pair_key, payload in sorted(watchlist_pairs.items()):
        count = int(_as_mapping(payload).get("count", 0) or 0)
        ratio = float(_as_mapping(payload).get("ratio", 0.0) or 0.0)
        watchlist_status.append(
            {
                "pair": str(pair_key),
                "count": count,
                "ratio": ratio,
                "status": "ready_for_tuning" if count > 0 else "observe_only",
                "summary": PAIR_ACTION_MAP.get(str(pair_key), {}).get(
                    "summary",
                    "Observe coverage first before rule changes.",
                ),
            }
        )

    priority_actions: list[dict[str, Any]] = []
    if group_candidates:
        priority_actions.append(
            {
                "kind": "group_confusion",
                **group_candidates[0],
            }
        )
    if pattern_candidates:
        priority_actions.append(
            {
                "kind": "pattern_confusion",
                **pattern_candidates[0],
            }
        )
    if not pattern_candidates:
        observed_watchlist = next((row for row in watchlist_status if row["status"] == "ready_for_tuning"), None)
        if observed_watchlist is not None:
            priority_actions.append(
                {
                    "kind": "watchlist_pair",
                    **observed_watchlist,
                    "rule_focus": PAIR_ACTION_MAP.get(observed_watchlist["pair"], {}).get(
                        "rule_focus",
                        "Observe this pair with more samples before touching thresholds.",
                    ),
                }
            )

    readiness = {
        "baseline_ready": bool(baseline.get("baseline_ready", False)),
        "full_qa_ready": bool(_as_mapping(full_qa.get("full_qa_readiness")).get("full_qa_ready", False)),
        "labeled_rows": int(full_qa.get("labeled_rows", 0) or 0),
        "supported_pattern_ids": list(pattern_task.get("supported_pattern_ids", [])),
    }

    warnings: list[str] = []
    if not pattern_candidates:
        warnings.append("no_pattern_confusions_above_threshold")
    if not group_candidates:
        warnings.append("no_group_confusions_above_threshold")
    if all(row.get("status") == "observe_only" for row in watchlist_status):
        warnings.append("watchlist_pairs_not_yet_observed")

    return {
        "readiness": readiness,
        "group_candidates": group_candidates,
        "pattern_candidates": pattern_candidates,
        "watchlist_status": watchlist_status,
        "priority_actions": priority_actions,
        "warnings": warnings,
    }
