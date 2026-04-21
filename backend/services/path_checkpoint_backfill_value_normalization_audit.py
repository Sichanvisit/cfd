from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


PATH_CHECKPOINT_BACKFILL_VALUE_NORMALIZATION_AUDIT_CONTRACT_VERSION = (
    "checkpoint_backfill_value_normalization_audit_v1"
)
_BACKFILL_SOURCES = {"open_trade_backfill", "closed_trade_hold_backfill", "closed_trade_runner_backfill"}


def default_checkpoint_backfill_value_normalization_audit_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_backfill_value_normalization_audit_latest.json"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
        if value in ("", None):
            return float(default)
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


def _review_group_key(row: Mapping[str, Any]) -> str:
    return " | ".join(
        [
            _to_text(row.get("symbol")).upper(),
            _to_text(row.get("surface_name")),
            _to_text(row.get("checkpoint_type")).upper(),
            _to_text(row.get("management_row_family")),
            _to_text(row.get("checkpoint_rule_family_hint")),
            _to_text(row.get("hindsight_best_management_action_label")).upper(),
        ]
    )


def _median_abs(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return round(float(cleaned.abs().median()), 6)


def _median_float(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return round(float(cleaned.median()), 6)


def _scale_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if abs(float(denominator)) <= 1e-9:
        return None
    return round(float(numerator) / float(denominator), 6)


def build_checkpoint_backfill_value_normalization_audit(
    resolved: pd.DataFrame | None,
    *,
    review_processor_payload: Mapping[str, Any] | None = None,
    top_n_groups: int = 5,
    sample_rows_per_group: int = 5,
) -> dict[str, Any]:
    frame = resolved.copy() if isinstance(resolved, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        return {
            "summary": {
                "contract_version": PATH_CHECKPOINT_BACKFILL_VALUE_NORMALIZATION_AUDIT_CONTRACT_VERSION,
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": 0,
                "target_group_count": 0,
                "recommended_next_action": "collect_resolved_rows_before_backfill_value_audit",
            },
            "group_rows": [],
            "symbol_source_scale_hints": [],
        }

    for column in (
        "symbol",
        "surface_name",
        "checkpoint_type",
        "management_row_family",
        "checkpoint_rule_family_hint",
        "hindsight_best_management_action_label",
        "source",
        "checkpoint_id",
    ):
        if column not in frame.columns:
            frame[column] = ""

    for column in ("current_profit", "giveback_ratio"):
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")

    frame["group_key"] = frame.apply(_review_group_key, axis=1)
    frame["source"] = frame["source"].fillna("").astype(str)
    frame["is_backfill_source"] = frame["source"].isin(_BACKFILL_SOURCES)

    review_payload = _mapping(review_processor_payload)
    target_group_keys = [
        _to_text(row.get("group_key"))
        for row in list(review_payload.get("group_rows") or [])
        if _to_text(row.get("review_disposition")) == "mixed_backfill_value_scale_review"
    ]
    if not target_group_keys:
        return {
            "summary": {
                "contract_version": PATH_CHECKPOINT_BACKFILL_VALUE_NORMALIZATION_AUDIT_CONTRACT_VERSION,
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": int(len(frame)),
                "target_group_count": 0,
                "recommended_next_action": "no_mixed_backfill_value_scale_groups_detected",
            },
            "group_rows": [],
            "symbol_source_scale_hints": [],
        }

    group_rows: list[dict[str, Any]] = []
    symbol_source_hints: list[dict[str, Any]] = []
    for group_key in target_group_keys[: max(1, int(top_n_groups))]:
        group = frame.loc[frame["group_key"].eq(group_key)].copy()
        if group.empty:
            continue

        backfill = group.loc[group["is_backfill_source"]].copy()
        non_backfill = group.loc[~group["is_backfill_source"]].copy()

        backfill_abs_profit_median = _median_abs(backfill["current_profit"])
        non_backfill_abs_profit_median = _median_abs(non_backfill["current_profit"])
        scale_ratio_hint = _scale_ratio(backfill_abs_profit_median, non_backfill_abs_profit_median)
        backfill_giveback_ratio_median = _median_float(backfill["giveback_ratio"])
        non_backfill_giveback_ratio_median = _median_float(non_backfill["giveback_ratio"])

        checkpoint_scale_hints: list[dict[str, Any]] = []
        if "checkpoint_id" in group.columns:
            for checkpoint_id, cp_group in group.groupby("checkpoint_id", dropna=False):
                cp_backfill = cp_group.loc[cp_group["is_backfill_source"]]
                cp_non_backfill = cp_group.loc[~cp_group["is_backfill_source"]]
                cp_ratio = _scale_ratio(_median_abs(cp_backfill["current_profit"]), _median_abs(cp_non_backfill["current_profit"]))
                if cp_ratio is None:
                    continue
                checkpoint_scale_hints.append(
                    {
                        "checkpoint_id": _to_text(checkpoint_id),
                        "row_count": int(len(cp_group)),
                        "backfill_row_count": int(len(cp_backfill)),
                        "non_backfill_row_count": int(len(cp_non_backfill)),
                        "scale_ratio_hint": cp_ratio,
                    }
                )

        source_rows: list[dict[str, Any]] = []
        for source, source_group in group.groupby("source", dropna=False):
            source_rows.append(
                {
                    "source": _to_text(source),
                    "row_count": int(len(source_group)),
                    "avg_current_profit": round(float(source_group["current_profit"].dropna().mean()), 6)
                    if not source_group["current_profit"].dropna().empty
                    else None,
                    "median_abs_current_profit": _median_abs(source_group["current_profit"]),
                    "median_giveback_ratio": _median_float(source_group["giveback_ratio"]),
                    "is_backfill_source": bool(_to_text(source) in _BACKFILL_SOURCES),
                }
            )

        samples: list[dict[str, Any]] = []
        for _, sample in group.sort_values("generated_at").head(max(1, int(sample_rows_per_group))).iterrows():
            samples.append(
                {
                    "generated_at": _to_text(sample.get("generated_at")),
                    "source": _to_text(sample.get("source")),
                    "checkpoint_id": _to_text(sample.get("checkpoint_id")),
                    "current_profit": _to_float(sample.get("current_profit")),
                    "giveback_ratio": _to_float(sample.get("giveback_ratio")),
                    "management_action_label": _to_text(sample.get("management_action_label")).upper(),
                    "runtime_proxy_management_action_label": _to_text(
                        sample.get("runtime_proxy_management_action_label")
                    ).upper(),
                    "hindsight_best_management_action_label": _to_text(
                        sample.get("hindsight_best_management_action_label")
                    ).upper(),
                }
            )

        audit_state = "insufficient_live_peer_reference"
        if scale_ratio_hint is not None and scale_ratio_hint >= 10.0:
            audit_state = "source_scale_incompatibility_likely"
        elif scale_ratio_hint is not None and scale_ratio_hint >= 5.0:
            audit_state = "source_scale_incompatibility_possible"

        latest = group.sort_values("generated_at").iloc[-1].to_dict()
        group_rows.append(
            {
                "group_key": group_key,
                "symbol": _to_text(latest.get("symbol")).upper(),
                "surface_name": _to_text(latest.get("surface_name")),
                "checkpoint_type": _to_text(latest.get("checkpoint_type")).upper(),
                "management_row_family": _to_text(latest.get("management_row_family")),
                "checkpoint_rule_family_hint": _to_text(latest.get("checkpoint_rule_family_hint")),
                "row_count": int(len(group)),
                "backfill_row_count": int(len(backfill)),
                "non_backfill_row_count": int(len(non_backfill)),
                "backfill_source_share": _safe_rate(int(len(backfill)), int(len(group))),
                "backfill_abs_profit_median": backfill_abs_profit_median,
                "non_backfill_abs_profit_median": non_backfill_abs_profit_median,
                "scale_ratio_hint": scale_ratio_hint,
                "backfill_giveback_ratio_median": backfill_giveback_ratio_median,
                "non_backfill_giveback_ratio_median": non_backfill_giveback_ratio_median,
                "audit_state": audit_state,
                "review_recommendation": (
                    "treat_backfill_profit_as_source_scaled_and_keep_rule_patch_blocked"
                    if audit_state == "source_scale_incompatibility_likely"
                    else "inspect_more_live_peer_rows_before_normalization"
                ),
                "source_rows": source_rows,
                "checkpoint_scale_hints": checkpoint_scale_hints,
                "samples": samples,
            }
        )

        if scale_ratio_hint is not None:
            symbol_source_hints.append(
                {
                    "symbol": _to_text(latest.get("symbol")).upper(),
                    "backfill_sources": sorted({_to_text(row.get("source")) for row in source_rows if row.get("is_backfill_source")}),
                    "scale_ratio_hint": scale_ratio_hint,
                    "group_key": group_key,
                }
            )

    likely_count = sum(1 for row in group_rows if _to_text(row.get("audit_state")) == "source_scale_incompatibility_likely")
    summary = {
        "contract_version": PATH_CHECKPOINT_BACKFILL_VALUE_NORMALIZATION_AUDIT_CONTRACT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "resolved_row_count": int(len(frame)),
        "target_group_count": int(len(group_rows)),
        "likely_source_scale_incompatibility_group_count": int(likely_count),
        "recommended_next_action": (
            "review_backfill_source_scale_incompatibility_before_any_rule_patch"
            if likely_count > 0
            else "inspect_more_live_peer_rows_before_normalization"
        ),
    }
    return {
        "summary": summary,
        "group_rows": group_rows,
        "symbol_source_scale_hints": symbol_source_hints,
    }
