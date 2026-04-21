"""Scene candidate disagreement audit helpers for SA5.5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_scene_runtime_bridge import (
    build_checkpoint_scene_log_only_bridge_v1,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_VERSION = "checkpoint_scene_disagreement_audit_v1"
PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_COLUMNS = [
    "symbol",
    "row_count",
    "candidate_selected_label_counts",
    "runtime_unresolved_disagreement_share",
    "hindsight_unresolved_disagreement_share",
    "expected_action_alignment_rate",
    "high_conf_scene_disagreement_count",
    "recommended_focus",
]
_EXPECTED_ACTIONS_BY_SCENE = {
    "time_decay_risk": {"FULL_EXIT", "PARTIAL_EXIT", "WAIT"},
    "trend_exhaustion": {"PARTIAL_THEN_HOLD", "HOLD", "PARTIAL_EXIT"},
    "breakout_retest_hold": {"REBUY", "HOLD", "PARTIAL_THEN_HOLD"},
}


def default_checkpoint_scene_disagreement_audit_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_scene_disagreement_audit_latest.json"
    )


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _json_counts(counts: dict[str, int]) -> str:
    return json.dumps({str(key): int(value) for key, value in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _expected_action_alignment_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    matched = 0
    for row in frame.to_dict(orient="records"):
        selected = _to_text(row.get("scene_candidate_selected_label"), _to_text(row.get("candidate_selected_label")))
        action = _to_text(row.get("runtime_proxy_management_action_label")).upper()
        expected_actions = _EXPECTED_ACTIONS_BY_SCENE.get(selected, set())
        if action in expected_actions:
            matched += 1
    return _safe_rate(matched, int(len(frame)))


def _label_pull_profile(label_frame: pd.DataFrame, *, label: str) -> dict[str, Any]:
    top_slices = (
        label_frame.groupby(["symbol", "surface_name", "checkpoint_type"])
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    runtime_unresolved = int((label_frame["runtime_scene_fine_label"].fillna("").astype(str) == "unresolved").sum())
    hindsight_unresolved = int((label_frame["hindsight_scene_fine_label"].fillna("").astype(str) == "unresolved").sum())
    resolved_hindsight = int(len(label_frame) - hindsight_unresolved)
    expected_alignment = _expected_action_alignment_rate(label_frame)
    watch_state = "review"
    if len(label_frame) >= 25 and _safe_rate(resolved_hindsight, int(len(label_frame))) < 0.15 and _safe_rate(runtime_unresolved, int(len(label_frame))) > 0.85:
        watch_state = "overpull_watch"
    elif resolved_hindsight > 0 and expected_alignment >= 0.75:
        watch_state = "action_proxy_useful_watch"

    return {
        "candidate_selected_label": label,
        "row_count": int(len(label_frame)),
        "runtime_unresolved_share": _safe_rate(runtime_unresolved, int(len(label_frame))),
        "hindsight_unresolved_share": _safe_rate(hindsight_unresolved, int(len(label_frame))),
        "hindsight_resolved_share": _safe_rate(resolved_hindsight, int(len(label_frame))),
        "expected_action_alignment_rate": expected_alignment,
        "top_slices": [
            {
                "symbol": str(symbol),
                "surface_name": str(surface_name),
                "checkpoint_type": str(checkpoint_type),
                "count": int(count),
            }
            for (symbol, surface_name, checkpoint_type), count in top_slices.items()
        ],
        "watch_state": watch_state,
    }


def _casebook_examples(frame: pd.DataFrame, *, limit_per_label: int = 10) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for label in sorted(frame["scene_candidate_selected_label"].fillna("").astype(str).replace("", pd.NA).dropna().unique().tolist()):
        label_frame = frame.loc[frame["scene_candidate_selected_label"] == label].copy()
        label_frame = label_frame.sort_values(
            by=["scene_candidate_selected_confidence", "symbol", "checkpoint_id"],
            ascending=[False, True, True],
        ).head(limit_per_label)
        for row in label_frame.to_dict(orient="records"):
            examples.append(
                {
                    "candidate_selected_label": label,
                    "symbol": _to_text(row.get("symbol")).upper(),
                    "checkpoint_id": _to_text(row.get("checkpoint_id")),
                    "surface_name": _to_text(row.get("surface_name")),
                    "checkpoint_type": _to_text(row.get("checkpoint_type")),
                    "source": _to_text(row.get("source")),
                    "runtime_scene_fine_label": _to_text(row.get("runtime_scene_fine_label")),
                    "hindsight_scene_fine_label": _to_text(row.get("hindsight_scene_fine_label")),
                    "candidate_selected_confidence": round(_to_float(row.get("scene_candidate_selected_confidence"), 0.0), 6),
                    "runtime_proxy_management_action_label": _to_text(row.get("runtime_proxy_management_action_label")).upper(),
                    "hindsight_best_management_action_label": _to_text(row.get("hindsight_best_management_action_label")).upper(),
                    "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")),
                    "exit_stage_family": _to_text(row.get("exit_stage_family")),
                    "current_profit": round(_to_float(row.get("current_profit"), 0.0), 6),
                    "giveback_ratio": round(_to_float(row.get("giveback_ratio"), 0.0), 6),
                    "scene_candidate_reason": _to_text(row.get("scene_candidate_reason")),
                }
            )
    return examples


def build_checkpoint_scene_disagreement_audit(
    resolved_dataset: pd.DataFrame | None,
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
    symbols: tuple[str, ...] = ("BTCUSD", "NAS100", "XAUUSD"),
    high_conf_threshold: float = 0.70,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "resolved_row_count": 0,
        "high_conf_scene_disagreement_count": 0,
        "candidate_selected_label_counts": {},
        "runtime_unresolved_disagreement_share": 0.0,
        "hindsight_unresolved_disagreement_share": 0.0,
        "expected_action_alignment_rate": 0.0,
        "label_pull_profiles": [],
        "top_slice_counts": [],
        "casebook_examples": [],
        "recommended_next_action": "collect_more_scene_candidate_rows_before_sa6",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_COLUMNS), summary

    for column in (
        "symbol",
        "surface_name",
        "checkpoint_type",
        "source",
        "checkpoint_id",
        "runtime_scene_fine_label",
        "hindsight_scene_fine_label",
        "runtime_proxy_management_action_label",
        "hindsight_best_management_action_label",
        "checkpoint_rule_family_hint",
        "exit_stage_family",
        "current_profit",
        "giveback_ratio",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    summary["resolved_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_COLUMNS), summary

    disagreement_rows: list[dict[str, Any]] = []
    for row in scoped.to_dict(orient="records"):
        bridge = build_checkpoint_scene_log_only_bridge_v1(
            row,
            active_state_path=active_state_path,
            latest_run_path=latest_run_path,
        )["row"]
        selected_conf = _to_float(bridge.get("scene_candidate_selected_confidence"), 0.0)
        if not _to_bool(bridge.get("scene_candidate_available"), False):
            continue
        if selected_conf < float(high_conf_threshold):
            continue
        if _to_bool(bridge.get("scene_candidate_runtime_scene_match"), False):
            continue
        merged = dict(row)
        merged.update(bridge)
        disagreement_rows.append(merged)

    disagreements = pd.DataFrame(disagreement_rows)
    if disagreements.empty:
        summary["recommended_next_action"] = "scene_candidate_disagreement_clean_enough_for_sa6_review"
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_COLUMNS), summary

    summary["high_conf_scene_disagreement_count"] = int(len(disagreements))
    summary["candidate_selected_label_counts"] = (
        disagreements["scene_candidate_selected_label"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    summary["runtime_unresolved_disagreement_share"] = _safe_rate(
        int((disagreements["runtime_scene_fine_label"].fillna("").astype(str) == "unresolved").sum()),
        int(len(disagreements)),
    )
    summary["hindsight_unresolved_disagreement_share"] = _safe_rate(
        int((disagreements["hindsight_scene_fine_label"].fillna("").astype(str) == "unresolved").sum()),
        int(len(disagreements)),
    )
    summary["expected_action_alignment_rate"] = _expected_action_alignment_rate(disagreements)

    top_slices = (
        disagreements.groupby(["scene_candidate_selected_label", "symbol", "surface_name", "checkpoint_type"])
        .size()
        .sort_values(ascending=False)
        .head(20)
    )
    summary["top_slice_counts"] = [
        {
            "candidate_selected_label": str(label),
            "symbol": str(symbol),
            "surface_name": str(surface_name),
            "checkpoint_type": str(checkpoint_type),
            "count": int(count),
        }
        for (label, symbol, surface_name, checkpoint_type), count in top_slices.items()
    ]

    profiles: list[dict[str, Any]] = []
    for label in sorted(disagreements["scene_candidate_selected_label"].fillna("").astype(str).replace("", pd.NA).dropna().unique().tolist()):
        profiles.append(_label_pull_profile(disagreements.loc[disagreements["scene_candidate_selected_label"] == label].copy(), label=label))
    summary["label_pull_profiles"] = profiles
    summary["casebook_examples"] = _casebook_examples(disagreements)

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = disagreements.loc[disagreements["symbol"] == symbol].copy()
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "row_count": 0,
                    "candidate_selected_label_counts": "{}",
                    "runtime_unresolved_disagreement_share": 0.0,
                    "hindsight_unresolved_disagreement_share": 0.0,
                    "expected_action_alignment_rate": 0.0,
                    "high_conf_scene_disagreement_count": 0,
                    "recommended_focus": f"collect_more_{symbol.lower()}_scene_candidate_rows",
                }
            )
            continue
        recommended_focus = f"inspect_{symbol.lower()}_scene_candidate_overpull"
        if _safe_rate(
            int((symbol_frame["hindsight_scene_fine_label"].fillna("").astype(str) == "unresolved").sum()),
            int(len(symbol_frame)),
        ) >= 0.80:
            recommended_focus = f"inspect_{symbol.lower()}_hindsight_unresolved_scene_pull"
        rows.append(
            {
                "symbol": symbol,
                "row_count": int(len(symbol_frame)),
                "candidate_selected_label_counts": _json_counts(
                    symbol_frame["scene_candidate_selected_label"]
                    .fillna("")
                    .astype(str)
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .to_dict()
                ),
                "runtime_unresolved_disagreement_share": _safe_rate(
                    int((symbol_frame["runtime_scene_fine_label"].fillna("").astype(str) == "unresolved").sum()),
                    int(len(symbol_frame)),
                ),
                "hindsight_unresolved_disagreement_share": _safe_rate(
                    int((symbol_frame["hindsight_scene_fine_label"].fillna("").astype(str) == "unresolved").sum()),
                    int(len(symbol_frame)),
                ),
                "expected_action_alignment_rate": _expected_action_alignment_rate(symbol_frame),
                "high_conf_scene_disagreement_count": int(len(symbol_frame)),
                "recommended_focus": recommended_focus,
            }
        )

    report_frame = pd.DataFrame(rows, columns=PATH_CHECKPOINT_SCENE_DISAGREEMENT_AUDIT_COLUMNS)
    overpull_watch_labels = [
        profile["candidate_selected_label"]
        for profile in profiles
        if str(profile.get("watch_state")) == "overpull_watch"
    ]
    if overpull_watch_labels:
        summary["recommended_next_action"] = "keep_scene_candidate_log_only_and_patch_overpull_labels_before_sa6"
    elif summary["expected_action_alignment_rate"] >= 0.75:
        summary["recommended_next_action"] = "review_scene_bias_candidates_for_sa6"
    else:
        summary["recommended_next_action"] = "keep_sa5_log_only_and_collect_more_disagreement_rows"
    return report_frame, summary
