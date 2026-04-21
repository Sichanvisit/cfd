"""Common edge-creation helpers for the shadow auto roadmap."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import json

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEMO_PATH = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_runtime_activation_demo_latest.csv"
DEFAULT_FEATURE_ROWS_PATH = PROJECT_ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy" / "bridge_proxy_feature_rows.parquet"
DEFAULT_MANUAL_WAIT_TRUTH_PATH = PROJECT_ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"
DEFAULT_SHADOW_OVERLAP_REVIEWED_DRAFT_PATH = (
    PROJECT_ROOT / "data" / "manual_annotations" / "shadow_manual_overlap_seed_draft_latest.csv"
)
DEFAULT_MANUAL_MATCH_THRESHOLD_MINUTES = 180.0
DEFAULT_SHADOW_OVERLAP_WINDOW_MINUTES = 30.0

DEFAULT_BRIDGE_TARGET_VARIANT_MAPPING: dict[str, str] = {
    "avoided_loss_by_wait": "wait_more",
    "neutral_wait": "wait_small_value",
    "insufficient_evidence": "wait_more",
    "good_wait_better_entry": "wait_better_entry",
    "bad_wait_missed_move": "enter_now",
    "missed_move_by_wait": "enter_now",
    "bad_wait_no_timing_edge": "enter_now_weak",
    "good_wait_protective_exit": "exit_protect",
    "good_wait_reversal_escape": "exit_protect",
}

DEFAULT_MANUAL_TARGET_VARIANT_MAPPING: dict[str, str] = {
    "good_wait_better_entry": "wait_better_entry",
    "good_wait_protective_exit": "exit_protect",
    "good_wait_reversal_escape": "exit_protect",
    "bad_wait_missed_move": "enter_now",
    "bad_wait_no_timing_edge": "enter_now_weak",
    "neutral_wait_small_value": "wait_small_value",
}

TARGET_VARIANT_TO_CLASS: dict[str, str] = {
    "enter_now": "enter_now",
    "enter_now_weak": "enter_now",
    "wait_better_entry": "wait_more",
    "wait_small_value": "wait_more",
    "wait_more": "wait_more",
    "exit_protect": "exit_protect",
}

DEFAULT_BRIDGE_TARGET_MAPPING: dict[str, str] = {
    key: TARGET_VARIANT_TO_CLASS.get(value, "wait_more")
    for key, value in DEFAULT_BRIDGE_TARGET_VARIANT_MAPPING.items()
}

DEFAULT_MANUAL_TARGET_MAPPING: dict[str, str] = {
    key: TARGET_VARIANT_TO_CLASS.get(value, "wait_more")
    for key, value in DEFAULT_MANUAL_TARGET_VARIANT_MAPPING.items()
}

FREEZE_LIKE_BRIDGE_LABELS = {"insufficient_evidence", "neutral_wait"}
WAIT_BETTER_ENTRY_PREMIUM_MAX = 0.002
WAIT_BETTER_ENTRY_BRIDGE_DIVISOR = 25000.0
WAIT_BETTER_ENTRY_MANUAL_MULTIPLIER = 5.0
WAIT_BETTER_ENTRY_CONFIDENCE_SCALE: dict[str, float] = {
    "high": 1.0,
    "medium": 0.8,
    "low": 0.6,
}


def _to_text(value: Any, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_float(value: Any, default: float = 0.0) -> float:
    text = _to_text(value)
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _to_bool(value: Any, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def _parse_local_timestamp(value: Any) -> pd.Timestamp | None:
    text = _to_text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        return stamp.tz_convert("Asia/Seoul").tz_localize(None)
    return stamp


def _clamp_positive(value: Any, *, upper: float) -> float:
    numeric = max(0.0, _to_float(value, 0.0))
    return min(float(upper), numeric)


def load_demo_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_feature_rows_frame(path: str | Path) -> pd.DataFrame:
    parquet_path = Path(path)
    if not parquet_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(parquet_path)
    except Exception:
        return pd.DataFrame()


def load_manual_truth_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    base = normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    if csv_path.exists():
        for encoding in ("utf-8-sig", "utf-8", "cp949"):
            try:
                base = normalize_manual_wait_teacher_annotation_df(
                    pd.read_csv(csv_path, encoding=encoding, low_memory=False)
                )
                break
            except Exception:
                continue
        else:
            base = normalize_manual_wait_teacher_annotation_df(pd.read_csv(csv_path, low_memory=False))

    reviewed_shadow_overlap = normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    reviewed_path = DEFAULT_SHADOW_OVERLAP_REVIEWED_DRAFT_PATH
    if reviewed_path.exists():
        for encoding in ("utf-8-sig", "utf-8", "cp949"):
            try:
                reviewed_shadow_overlap = normalize_manual_wait_teacher_annotation_df(
                    pd.read_csv(reviewed_path, encoding=encoding, low_memory=False)
                )
                break
            except Exception:
                continue
        else:
            reviewed_shadow_overlap = normalize_manual_wait_teacher_annotation_df(
                pd.read_csv(reviewed_path, low_memory=False)
            )
        if not reviewed_shadow_overlap.empty:
            review_status = reviewed_shadow_overlap.get("review_status", pd.Series(dtype=object)).fillna("").astype(str).str.lower()
            annotation_source = reviewed_shadow_overlap.get("annotation_source", pd.Series(dtype=object)).fillna("").astype(str).str.lower()
            reviewed_shadow_overlap = reviewed_shadow_overlap.loc[
                annotation_source.str.contains("shadow_overlap")
                & ~review_status.isin(
                    {
                        "",
                        "pending",
                        "needs_manual_recheck",
                        "review_needed",
                        "hold_review_needed",
                    }
                )
            ].copy()

    if base.empty and reviewed_shadow_overlap.empty:
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    if reviewed_shadow_overlap.empty:
        return base
    merged = pd.concat([base, reviewed_shadow_overlap], ignore_index=True)
    merged = merged.drop_duplicates(subset=["annotation_id"], keep="last")
    return normalize_manual_wait_teacher_annotation_df(merged)


def classify_baseline_action(action: Any, outcome: Any) -> str:
    action_text = _to_text(action).upper()
    outcome_text = _to_text(outcome).lower()
    if action_text in {"EXIT", "CLOSE", "CLOSE_ALL"} or outcome_text in {"exit", "closed", "protective_exit"}:
        return "exit_protect"
    if action_text in {"BUY", "SELL", "ENTER"} or outcome_text in {"entered", "fill", "filled"}:
        return "enter_now"
    return "wait_more"


def classify_proxy_target(row: Mapping[str, Any]) -> str:
    return TARGET_VARIANT_TO_CLASS.get(classify_proxy_target_variant(row), "wait_more")


def classify_proxy_target_variant(row: Mapping[str, Any]) -> str:
    exit_target = int(_to_float(row.get("target_exit_management"), 0.0))
    timing_target = int(_to_float(row.get("target_timing_now_vs_wait"), 0.0))
    entry_target = int(_to_float(row.get("target_entry_quality"), 0.0))
    if exit_target == 1:
        return "exit_protect"
    if timing_target == 1 and entry_target == 1:
        return "enter_now"
    if timing_target == 1:
        return "enter_now_weak"
    if entry_target == 1:
        return "wait_better_entry"
    return "wait_more"


def classify_bridge_target(label: Any, row: Mapping[str, Any] | None = None) -> str:
    return TARGET_VARIANT_TO_CLASS.get(classify_bridge_target_variant(label, row), "wait_more")


def classify_bridge_target_variant(label: Any, row: Mapping[str, Any] | None = None) -> str:
    if isinstance(label, Mapping):
        row_map = dict(label)
        key = _to_text(row_map.get("entry_wait_quality_label")).lower()
    else:
        row_map = dict(row) if isinstance(row, Mapping) else {}
        key = _to_text(label).lower()
    if key == "insufficient_evidence":
        economic = _as_mapping(row_map.get("economic_target_summary"))
        state_hint = _as_mapping(row_map.get("state25_runtime_hint_v1"))
        learning_total_label = _to_text(
            row_map.get("learning_total_label") or economic.get("learning_total_label")
        ).lower()
        signed_exit_score = _to_float(
            row_map.get("signed_exit_score", economic.get("signed_exit_score")),
            0.0,
        )
        wait_bias_hint = _to_text(
            row_map.get("wait_bias_hint") or state_hint.get("wait_bias_hint")
        ).lower()
        forecast_decision_hint = _to_text(row_map.get("forecast_decision_hint")).upper()
        if learning_total_label == "negative" or signed_exit_score < 0.0:
            return "exit_protect"
        if wait_bias_hint == "wait" and learning_total_label in {"positive", "neutral"}:
            return "wait_better_entry"
        if wait_bias_hint == "wait" and forecast_decision_hint in {"BUY", "SELL", "BALANCED"}:
            return "wait_better_entry"
        if learning_total_label == "positive":
            return "enter_now"
        if learning_total_label == "neutral":
            return "wait_more"
        return "wait_more"
    return DEFAULT_BRIDGE_TARGET_VARIANT_MAPPING.get(key, "wait_more")


def classify_manual_target(label: Any, family: Any = "") -> str:
    return TARGET_VARIANT_TO_CLASS.get(classify_manual_target_variant(label, family), "wait_more")


def classify_manual_target_variant(label: Any, family: Any = "") -> str:
    key = _to_text(label).lower()
    if key in DEFAULT_MANUAL_TARGET_VARIANT_MAPPING:
        return DEFAULT_MANUAL_TARGET_VARIANT_MAPPING[key]
    family_key = _to_text(family).lower()
    family_map = {
        "timing_improvement": "wait_better_entry",
        "failed_wait": "enter_now",
        "protective_exit": "exit_protect",
        "reversal_escape": "exit_protect",
        "neutral_wait": "wait_small_value",
    }
    return family_map.get(family_key, "wait_more")


def classify_shadow_action(
    *,
    shadow_should_enter: Any,
    shadow_recommendation: Any = "",
    shadow_exit_management_probability: Any = None,
    exit_threshold: float = 0.8,
) -> str:
    return TARGET_VARIANT_TO_CLASS.get(
        classify_shadow_action_variant(
            shadow_should_enter=shadow_should_enter,
            shadow_recommendation=shadow_recommendation,
            shadow_exit_management_probability=shadow_exit_management_probability,
            exit_threshold=exit_threshold,
        ),
        "wait_more",
    )


def classify_shadow_action_variant(
    *,
    shadow_should_enter: Any,
    shadow_recommendation: Any = "",
    shadow_exit_management_probability: Any = None,
    exit_threshold: float = 0.8,
) -> str:
    recommendation = _to_text(shadow_recommendation).lower()
    exit_probability = _to_float(shadow_exit_management_probability, 0.0)
    if recommendation == "exit_protect" or exit_probability >= float(exit_threshold):
        return "exit_protect"
    if recommendation == "wait_better_entry":
        return "wait_better_entry"
    if bool(shadow_should_enter):
        return "enter_now"
    return "wait_more"


def resolve_shadow_value_proxy(
    *,
    baseline_realized_value: Any,
    shadow_action_variant: Any,
    effective_target_action_variant: Any = "",
    wait_better_entry_premium: Any = 0.0,
) -> float:
    baseline_value = _to_float(baseline_realized_value, 0.0)
    variant = _to_text(shadow_action_variant).lower()
    target_variant = _to_text(effective_target_action_variant).lower()
    if variant in {"enter_now", "enter_now_weak"}:
        return baseline_value
    if variant == "wait_better_entry" and target_variant == "wait_better_entry":
        premium = _clamp_positive(wait_better_entry_premium, upper=WAIT_BETTER_ENTRY_PREMIUM_MAX)
        return max(0.0, baseline_value) + premium
    return 0.0


def resolve_wait_better_entry_premium(row: Mapping[str, Any] | None) -> float:
    row_map = dict(row or {})
    effective_variant = _to_text(row_map.get("effective_target_action_variant")).lower()
    if effective_variant != "wait_better_entry":
        return 0.0

    manual_variant = _to_text(row_map.get("manual_target_action_variant")).lower()
    manual_premium = 0.0
    if manual_variant == "wait_better_entry":
        anchor_price = _to_float(
            row_map.get("manual_wait_teacher_anchor_price", row_map.get("anchor_price")),
            0.0,
        )
        ideal_entry_price = _to_float(
            row_map.get("manual_wait_teacher_ideal_entry_price", row_map.get("ideal_entry_price")),
            0.0,
        )
        if anchor_price > 0.0 and ideal_entry_price > 0.0:
            confidence = _to_text(
                row_map.get("manual_wait_teacher_confidence", row_map.get("manual_teacher_confidence")),
                "medium",
            ).lower()
            confidence_scale = WAIT_BETTER_ENTRY_CONFIDENCE_SCALE.get(confidence, 0.7)
            relative_delta = abs(ideal_entry_price - anchor_price) / max(abs(anchor_price), 1.0)
            manual_premium = min(
                WAIT_BETTER_ENTRY_PREMIUM_MAX,
                relative_delta * WAIT_BETTER_ENTRY_MANUAL_MULTIPLIER * confidence_scale,
            )

    bridge_variant = _to_text(
        row_map.get("mapped_target_action_variant", row_map.get("proxy_target_action_variant")),
    ).lower()
    bridge_premium = 0.0
    if bridge_variant == "wait_better_entry":
        entry_quality_margin = max(0.0, _to_float(row_map.get("target_entry_quality_margin"), 0.0))
        bridge_premium = min(
            WAIT_BETTER_ENTRY_PREMIUM_MAX,
            entry_quality_margin / WAIT_BETTER_ENTRY_BRIDGE_DIVISOR,
        )

    return round(max(manual_premium, bridge_premium), 6)


def merge_demo_with_feature_rows(demo: pd.DataFrame, feature_rows: pd.DataFrame) -> pd.DataFrame:
    demo_df = demo.copy() if demo is not None else pd.DataFrame()
    feature_df = feature_rows.copy() if feature_rows is not None else pd.DataFrame()
    if demo_df.empty:
        return pd.DataFrame()
    if feature_df.empty:
        merged = demo_df.copy()
        merged["entry_wait_quality_label"] = ""
        merged["scene_family"] = ""
        return merged

    join_columns = ["bridge_decision_time", "symbol"]
    available_feature_columns = [
        "bridge_decision_time",
        "symbol",
        "entry_wait_quality_label",
        "scene_family",
        "learning_total_label",
        "learning_total_score",
        "loss_quality_label",
        "signed_exit_score",
        "wait_bias_hint",
        "forecast_decision_hint",
        "target_timing_now_vs_wait",
        "target_timing_margin",
        "target_entry_quality",
        "target_entry_quality_margin",
        "target_exit_management",
        "target_exit_management_margin",
        "bridge_quality_status",
        "economic_target_summary",
        "state25_runtime_hint_v1",
        "baseline_action",
        "baseline_outcome",
        "baseline_realized_value",
    ]
    feature_subset = feature_df[[col for col in available_feature_columns if col in feature_df.columns]].copy()
    feature_subset = feature_subset.drop_duplicates(subset=join_columns, keep="last")
    merged = demo_df.merge(feature_subset, on=join_columns, how="left", suffixes=("", "_feature"))
    if "baseline_action_feature" in merged.columns:
        merged["baseline_action"] = merged["baseline_action_feature"].where(
            merged["baseline_action_feature"].fillna("").astype(str).ne(""),
            merged["baseline_action"],
        )
    if "baseline_outcome_feature" in merged.columns:
        merged["baseline_outcome"] = merged["baseline_outcome_feature"].where(
            merged["baseline_outcome_feature"].fillna("").astype(str).ne(""),
            merged["baseline_outcome"],
        )
    if "baseline_realized_value_feature" in merged.columns:
        merged["baseline_realized_value"] = pd.to_numeric(
            merged["baseline_realized_value_feature"], errors="coerce"
        ).fillna(pd.to_numeric(merged["baseline_realized_value"], errors="coerce").fillna(0.0))
    return merged


def attach_manual_truth(
    frame: pd.DataFrame,
    manual_truth: pd.DataFrame | None = None,
    *,
    time_column: str = "bridge_decision_time",
    threshold_minutes: float = DEFAULT_MANUAL_MATCH_THRESHOLD_MINUTES,
) -> pd.DataFrame:
    working = frame.copy() if frame is not None else pd.DataFrame()
    if working.empty:
        return pd.DataFrame()

    defaults: dict[str, Any] = {
        "manual_reference_found": False,
        "manual_reference_gap_minutes": 0.0,
        "manual_reference_kind": "",
        "manual_wait_teacher_label": "",
        "manual_wait_teacher_family": "",
        "manual_wait_teacher_confidence": "",
        "manual_wait_teacher_usage_bucket": "",
        "manual_wait_teacher_review_status": "",
        "manual_wait_teacher_source": "",
        "manual_wait_teacher_episode_id": "",
        "manual_wait_teacher_anchor_time": "",
        "manual_wait_teacher_entry_time": "",
        "manual_wait_teacher_anchor_price": 0.0,
        "manual_wait_teacher_ideal_entry_price": 0.0,
        "manual_wait_better_entry_premium": 0.0,
        "manual_target_action_class": "",
    }
    for column, default in defaults.items():
        if column not in working.columns:
            working[column] = default

    normalized_manual = (
        normalize_manual_wait_teacher_annotation_df(manual_truth.copy())
        if manual_truth is not None and not manual_truth.empty
        else normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    )
    manual_rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    if not normalized_manual.empty:
        prepared_manual = normalized_manual.copy()
        prepared_manual["anchor_ts"] = prepared_manual["anchor_time"].apply(_parse_local_timestamp)
        prepared_manual["entry_ts"] = prepared_manual["ideal_entry_time"].apply(_parse_local_timestamp)
        prepared_manual["exit_ts"] = prepared_manual["ideal_exit_time"].apply(_parse_local_timestamp)
        prepared_manual["symbol"] = prepared_manual["symbol"].fillna("").astype(str).str.upper()
        for symbol, subset in prepared_manual.groupby("symbol", dropna=False):
            manual_rows_by_symbol[str(symbol or "").upper()] = subset.to_dict(orient="records")

    for index, row in working.iterrows():
        existing_label = _to_text(row.get("manual_wait_teacher_label", ""))
        existing_family = _to_text(row.get("manual_wait_teacher_family", ""))
        if existing_label or existing_family:
            working.at[index, "manual_reference_found"] = True
            working.at[index, "manual_reference_kind"] = _to_text(row.get("manual_reference_kind", ""), "pre_enriched")
            working.at[index, "manual_target_action_class"] = classify_manual_target(existing_label, existing_family)
            continue

        symbol = _to_text(row.get("symbol", "")).upper()
        reference_ts = _parse_local_timestamp(row.get(time_column, "")) or _parse_local_timestamp(row.get("time", ""))
        if not symbol or reference_ts is None:
            continue
        candidates = manual_rows_by_symbol.get(symbol, [])
        if not candidates:
            continue

        best_row: dict[str, Any] | None = None
        best_gap = float("inf")
        best_kind = ""
        for candidate in candidates:
            anchor_ts = candidate.get("anchor_ts")
            entry_ts = candidate.get("entry_ts")
            exit_ts = candidate.get("exit_ts")
            annotation_source = _to_text(candidate.get("annotation_source", ""), "").lower()
            is_shadow_overlap_reviewed = "shadow_overlap_reviewed" in annotation_source
            if is_shadow_overlap_reviewed:
                if not isinstance(anchor_ts, pd.Timestamp):
                    continue
                window_end_ts = (
                    exit_ts
                    if isinstance(exit_ts, pd.Timestamp)
                    else anchor_ts + pd.Timedelta(minutes=DEFAULT_SHADOW_OVERLAP_WINDOW_MINUTES)
                )
                if reference_ts < anchor_ts or reference_ts >= window_end_ts:
                    continue
                gap = abs((reference_ts - anchor_ts).total_seconds()) / 60.0
                kind = "shadow_overlap_window"
                if gap < best_gap:
                    best_row = candidate
                    best_gap = gap
                    best_kind = kind
                continue
            anchor_gap = (
                abs((reference_ts - anchor_ts).total_seconds()) / 60.0
                if isinstance(anchor_ts, pd.Timestamp)
                else float("inf")
            )
            entry_gap = (
                abs((reference_ts - entry_ts).total_seconds()) / 60.0
                if isinstance(entry_ts, pd.Timestamp)
                else float("inf")
            )
            gap = min(anchor_gap, entry_gap)
            if gap > float(threshold_minutes):
                continue
            kind = "entry_time" if entry_gap <= anchor_gap else "anchor_time"
            if gap < best_gap:
                best_row = candidate
                best_gap = gap
                best_kind = kind

        if best_row is None:
            continue

        working.at[index, "manual_reference_found"] = True
        working.at[index, "manual_reference_gap_minutes"] = round(float(best_gap), 6)
        working.at[index, "manual_reference_kind"] = best_kind
        working.at[index, "manual_wait_teacher_label"] = _to_text(best_row.get("manual_wait_teacher_label", "")).lower()
        working.at[index, "manual_wait_teacher_family"] = _to_text(best_row.get("manual_wait_teacher_family", "")).lower()
        working.at[index, "manual_wait_teacher_confidence"] = _to_text(best_row.get("manual_wait_teacher_confidence", "")).lower()
        working.at[index, "manual_wait_teacher_usage_bucket"] = _to_text(best_row.get("manual_wait_teacher_usage_bucket", "")).lower()
        working.at[index, "manual_wait_teacher_review_status"] = _to_text(best_row.get("review_status", "")).lower()
        working.at[index, "manual_wait_teacher_source"] = _to_text(best_row.get("annotation_source", "")).lower()
        working.at[index, "manual_wait_teacher_episode_id"] = _to_text(best_row.get("episode_id", ""))
        working.at[index, "manual_wait_teacher_anchor_time"] = _to_text(best_row.get("anchor_time", ""))
        working.at[index, "manual_wait_teacher_entry_time"] = _to_text(best_row.get("ideal_entry_time", ""))
        working.at[index, "manual_wait_teacher_anchor_price"] = _to_float(best_row.get("anchor_price"), 0.0)
        working.at[index, "manual_wait_teacher_ideal_entry_price"] = _to_float(best_row.get("ideal_entry_price"), 0.0)
        working.at[index, "manual_target_action_class"] = classify_manual_target(
            best_row.get("manual_wait_teacher_label", ""),
            best_row.get("manual_wait_teacher_family", ""),
        )

    return working


def enrich_action_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy() if frame is not None else pd.DataFrame()
    if working.empty:
        return pd.DataFrame()

    baseline_action = (
        working["baseline_action"]
        if "baseline_action" in working.columns
        else pd.Series([""] * len(working), index=working.index, dtype=object)
    )
    baseline_outcome = (
        working["baseline_outcome"]
        if "baseline_outcome" in working.columns
        else pd.Series([""] * len(working), index=working.index, dtype=object)
    )
    working["baseline_action_class"] = [
        classify_baseline_action(action, outcome)
        for action, outcome in zip(
            baseline_action,
            baseline_outcome,
        )
    ]
    working["proxy_target_action_class"] = [
        classify_proxy_target(row) for row in working.to_dict(orient="records")
    ]
    working["proxy_target_action_variant"] = [
        classify_proxy_target_variant(row) for row in working.to_dict(orient="records")
    ]
    working["mapped_target_action_class"] = [
        classify_bridge_target(row)
        for row in working.to_dict(orient="records")
    ]
    working["mapped_target_action_variant"] = [
        classify_bridge_target_variant(row)
        for row in working.to_dict(orient="records")
    ]
    if "manual_target_action_class" not in working.columns:
        working["manual_target_action_class"] = ""
    if "manual_target_action_variant" not in working.columns:
        working["manual_target_action_variant"] = ""
    working["manual_target_action_class"] = [
        classify_manual_target(label, family) if (_to_text(label) or _to_text(family)) else _to_text(target)
        for label, family, target in zip(
            working.get("manual_wait_teacher_label", pd.Series(dtype=object)),
            working.get("manual_wait_teacher_family", pd.Series(dtype=object)),
            working.get("manual_target_action_class", pd.Series(dtype=object)),
        )
    ]
    working["manual_target_action_variant"] = [
        classify_manual_target_variant(label, family) if (_to_text(label) or _to_text(family)) else _to_text(target_variant)
        for label, family, target_variant in zip(
            working.get("manual_wait_teacher_label", pd.Series(dtype=object)),
            working.get("manual_wait_teacher_family", pd.Series(dtype=object)),
            working.get("manual_target_action_variant", pd.Series(dtype=object)),
        )
    ]
    if "manual_reference_found" not in working.columns:
        working["manual_reference_found"] = False
    working["manual_reference_found"] = [
        _to_bool(value, default=bool(_to_text(label) or _to_text(family)))
        for value, label, family in zip(
            working.get("manual_reference_found", pd.Series(dtype=object)),
            working.get("manual_wait_teacher_label", pd.Series(dtype=object)),
            working.get("manual_wait_teacher_family", pd.Series(dtype=object)),
        )
    ]
    working["effective_target_action_class"] = [
        manual_target if found and _to_text(manual_target) else mapped_target
        for found, manual_target, mapped_target in zip(
            working["manual_reference_found"],
            working["manual_target_action_class"],
            working["mapped_target_action_class"],
        )
    ]
    working["effective_target_action_variant"] = [
        manual_target if found and _to_text(manual_target) else mapped_target
        for found, manual_target, mapped_target in zip(
            working["manual_reference_found"],
            working["manual_target_action_variant"],
            working["mapped_target_action_variant"],
        )
    ]
    working["effective_target_source"] = [
        "manual_truth" if found and _to_text(manual_target) else "bridge_mapping"
        for found, manual_target in zip(
            working["manual_reference_found"],
            working["manual_target_action_class"],
        )
    ]
    working["bridge_wait_better_entry_premium"] = [
        resolve_wait_better_entry_premium(
            {
                **row,
                "manual_target_action_variant": "",
                "effective_target_action_variant": row.get("mapped_target_action_variant", ""),
            }
        )
        for row in working.to_dict(orient="records")
    ]
    working["manual_wait_better_entry_premium"] = [
        resolve_wait_better_entry_premium(
            {
                **row,
                "mapped_target_action_variant": "",
                "proxy_target_action_variant": "",
            }
        )
        for row in working.to_dict(orient="records")
    ]
    working["effective_wait_better_entry_premium"] = [
        resolve_wait_better_entry_premium(row)
        for row in working.to_dict(orient="records")
    ]
    shadow_should_enter = (
        working["shadow_should_enter"]
        if "shadow_should_enter" in working.columns
        else pd.Series([False] * len(working), index=working.index, dtype=bool)
    )
    shadow_recommendation = (
        working["shadow_recommendation"]
        if "shadow_recommendation" in working.columns
        else pd.Series([""] * len(working), index=working.index, dtype=object)
    )
    shadow_exit_management_probability = (
        working["shadow_exit_management_probability"]
        if "shadow_exit_management_probability" in working.columns
        else pd.Series([0.0] * len(working), index=working.index, dtype=float)
    )
    working["shadow_action_class"] = [
        classify_shadow_action(
            shadow_should_enter=should_enter,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
        )
        for should_enter, recommendation, exit_prob in zip(
            shadow_should_enter,
            shadow_recommendation,
            shadow_exit_management_probability,
        )
    ]
    working["shadow_action_variant"] = [
        classify_shadow_action_variant(
            shadow_should_enter=should_enter,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
        )
        for should_enter, recommendation, exit_prob in zip(
            shadow_should_enter,
            shadow_recommendation,
            shadow_exit_management_probability,
        )
    ]
    working["baseline_action_variant"] = working["baseline_action_class"].fillna("").astype(str)
    working["action_diverged_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        != working["shadow_action_variant"].fillna("").astype(str)
    )
    working["proxy_target_match_flag"] = (
        working["shadow_action_variant"].fillna("").astype(str)
        == working["proxy_target_action_variant"].fillna("").astype(str)
    )
    working["mapped_target_match_flag"] = (
        working["shadow_action_variant"].fillna("").astype(str)
        == working["mapped_target_action_variant"].fillna("").astype(str)
    )
    working["manual_target_match_flag"] = (
        working["shadow_action_variant"].fillna("").astype(str)
        == working["manual_target_action_variant"].fillna("").astype(str)
    ) & working["manual_reference_found"].astype(bool)
    working["effective_target_match_flag"] = (
        working["shadow_action_variant"].fillna("").astype(str)
        == working["effective_target_action_variant"].fillna("").astype(str)
    )
    working["baseline_proxy_target_match_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        == working["proxy_target_action_variant"].fillna("").astype(str)
    )
    working["baseline_mapped_target_match_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        == working["mapped_target_action_variant"].fillna("").astype(str)
    )
    working["baseline_manual_target_match_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        == working["manual_target_action_variant"].fillna("").astype(str)
    ) & working["manual_reference_found"].astype(bool)
    working["baseline_effective_target_match_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        == working["effective_target_action_variant"].fillna("").astype(str)
    )
    working["target_mapping_disagreement_flag"] = (
        working["proxy_target_action_variant"].fillna("").astype(str)
        != working["mapped_target_action_variant"].fillna("").astype(str)
    )
    working["effective_target_disagreement_flag"] = (
        working["proxy_target_action_variant"].fillna("").astype(str)
        != working["effective_target_action_variant"].fillna("").astype(str)
    )
    bridge_label = working.get("entry_wait_quality_label", pd.Series(dtype=object)).fillna("").astype(str).str.lower()
    usage_bucket = working.get("manual_wait_teacher_usage_bucket", pd.Series(dtype=object)).fillna("").astype(str).str.lower()
    working["freeze_family_flag"] = (
        usage_bucket.eq("diagnostic")
        | (~working["manual_reference_found"].astype(bool) & bridge_label.isin(FREEZE_LIKE_BRIDGE_LABELS))
    )
    working["collect_more_truth_flag"] = (
        ~working["manual_reference_found"].astype(bool)
        & bridge_label.eq("insufficient_evidence")
    )
    working["shadow_realized_value"] = pd.to_numeric(
        working.get("shadow_realized_value", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(pd.to_numeric(working.get("baseline_realized_value", pd.Series(dtype=float)), errors="coerce").fillna(0.0))
    working["baseline_realized_value"] = pd.to_numeric(
        working.get("baseline_realized_value", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0)
    return working


def summarize_action_frame(
    frame: pd.DataFrame,
    *,
    scope_kind: str,
    scope_value: str,
) -> dict[str, Any]:
    working = enrich_action_frame(frame)
    if working.empty:
        return {
            "candidate_id": f"{scope_kind}::{scope_value}",
            "family_key": scope_value if scope_kind == "scene_family" else "",
            "scope_kind": scope_kind,
            "scope_value": scope_value,
            "row_count": 0,
            "same_action_count": 0,
            "different_action_count": 0,
            "divergence_rate": 0.0,
            "enter_flip_count": 0,
            "wait_flip_count": 0,
            "exit_flip_count": 0,
            "manual_reference_row_count": 0,
            "manual_alignment_rate_baseline": 0.0,
            "manual_alignment_rate_shadow": 0.0,
            "manual_alignment_delta": 0.0,
            "baseline_alignment_rate_proxy": 0.0,
            "shadow_alignment_rate_proxy": 0.0,
            "proxy_alignment_improvement": 0.0,
            "baseline_alignment_rate_mapped": 0.0,
            "shadow_alignment_rate_mapped": 0.0,
            "mapped_alignment_improvement": 0.0,
            "baseline_value_sum": 0.0,
            "shadow_value_sum": 0.0,
            "value_diff_proxy": 0.0,
            "bounded_risk_flag": "no_rows",
        }

    row_count = int(len(working))
    same_action_count = int((~working["action_diverged_flag"]).sum())
    different_action_count = int(working["action_diverged_flag"].sum())
    baseline_proxy_alignment_rate = float(working["baseline_proxy_target_match_flag"].mean())
    shadow_proxy_alignment_rate = float(working["proxy_target_match_flag"].mean())
    baseline_mapped_alignment_rate = float(working["baseline_mapped_target_match_flag"].mean())
    shadow_mapped_alignment_rate = float(working["mapped_target_match_flag"].mean())
    baseline_value_sum = float(working["baseline_realized_value"].sum())
    shadow_value_sum = float(working["shadow_realized_value"].sum())
    manual_rows = working.loc[working["manual_reference_found"].astype(bool)].copy()
    manual_reference_row_count = int(len(manual_rows))
    baseline_manual_alignment_rate = (
        float(manual_rows["baseline_manual_target_match_flag"].mean())
        if not manual_rows.empty
        else 0.0
    )
    shadow_manual_alignment_rate = (
        float(manual_rows["manual_target_match_flag"].mean())
        if not manual_rows.empty
        else 0.0
    )
    if manual_reference_row_count <= 0:
        bounded_risk_flag = "manual_truth_missing"
    elif shadow_manual_alignment_rate < baseline_manual_alignment_rate:
        bounded_risk_flag = "manual_alignment_regression"
    elif different_action_count <= 0:
        bounded_risk_flag = "no_behavior_change"
    else:
        bounded_risk_flag = "bounded"

    diverged = working.loc[working["action_diverged_flag"].astype(bool)].copy()
    return {
        "candidate_id": f"{scope_kind}::{scope_value}",
        "family_key": scope_value if scope_kind == "scene_family" else "",
        "scope_kind": scope_kind,
        "scope_value": scope_value,
        "row_count": row_count,
        "baseline_enter_count": int(working["baseline_action_class"].eq("enter_now").sum()),
        "shadow_enter_count": int(working["shadow_action_class"].eq("enter_now").sum()),
        "baseline_wait_count": int(working["baseline_action_class"].eq("wait_more").sum()),
        "shadow_wait_count": int(working["shadow_action_class"].eq("wait_more").sum()),
        "baseline_exit_count": int(working["baseline_action_class"].eq("exit_protect").sum()),
        "shadow_exit_count": int(working["shadow_action_class"].eq("exit_protect").sum()),
        "same_action_count": same_action_count,
        "different_action_count": different_action_count,
        "divergence_rate": round(different_action_count / row_count, 6) if row_count else 0.0,
        "enter_flip_count": int(diverged["shadow_action_class"].eq("enter_now").sum()),
        "wait_flip_count": int(diverged["shadow_action_class"].eq("wait_more").sum()),
        "exit_flip_count": int(diverged["shadow_action_class"].eq("exit_protect").sum()),
        "manual_reference_row_count": manual_reference_row_count,
        "manual_alignment_rate_baseline": round(baseline_manual_alignment_rate, 6),
        "manual_alignment_rate_shadow": round(shadow_manual_alignment_rate, 6),
        "manual_alignment_delta": round(shadow_manual_alignment_rate - baseline_manual_alignment_rate, 6),
        "baseline_alignment_rate_proxy": round(baseline_proxy_alignment_rate, 6),
        "shadow_alignment_rate_proxy": round(shadow_proxy_alignment_rate, 6),
        "proxy_alignment_improvement": round(shadow_proxy_alignment_rate - baseline_proxy_alignment_rate, 6),
        "baseline_alignment_rate_mapped": round(baseline_mapped_alignment_rate, 6),
        "shadow_alignment_rate_mapped": round(shadow_mapped_alignment_rate, 6),
        "mapped_alignment_improvement": round(shadow_mapped_alignment_rate - baseline_mapped_alignment_rate, 6),
        "baseline_value_sum": round(baseline_value_sum, 6),
        "shadow_value_sum": round(shadow_value_sum, 6),
        "value_diff_proxy": round(shadow_value_sum - baseline_value_sum, 6),
        "bounded_risk_flag": bounded_risk_flag,
    }
