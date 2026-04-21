from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_PA8_ACTION_PREVIEW_VERSION = "checkpoint_pa8_action_preview_v1"
PATH_CHECKPOINT_PA8_ACTION_PREVIEW_COLUMNS = [
    "symbol",
    "checkpoint_id",
    "surface_name",
    "checkpoint_type",
    "checkpoint_rule_family_hint",
    "baseline_action_label",
    "preview_action_label",
    "preview_changed",
    "preview_reason",
    "hindsight_best_management_action_label",
    "baseline_hindsight_match",
    "preview_hindsight_match",
    "current_profit",
    "runtime_hold_quality_score",
    "runtime_partial_exit_ev",
    "runtime_full_exit_risk",
    "runtime_continuation_odds",
    "runtime_reversal_odds",
    "giveback_ratio",
]


def default_checkpoint_pa8_nas100_profit_hold_bias_preview_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json"
    )


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
        return float(value)
    except Exception:
        return float(default)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _baseline_proxy_action(row: Mapping[str, Any]) -> str:
    return _to_text(row.get("runtime_proxy_management_action_label")).upper()


def _eligible_nas100_profit_hold_bias_preview(row: Mapping[str, Any]) -> tuple[bool, str]:
    symbol = _to_text(row.get("symbol")).upper()
    surface_name = _to_text(row.get("surface_name"))
    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    family = _to_text(row.get("checkpoint_rule_family_hint")).lower()
    baseline_action = _baseline_proxy_action(row)
    unrealized = _to_text(row.get("unrealized_pnl_state")).upper()
    hold_quality = _to_float(row.get("runtime_hold_quality_score"), 0.0)
    partial_exit_ev = _to_float(row.get("runtime_partial_exit_ev"), 0.0)
    full_exit_risk = _to_float(row.get("runtime_full_exit_risk"), 0.0)
    continuation = _to_float(row.get("runtime_continuation_odds"), 0.0)
    reversal = _to_float(row.get("runtime_reversal_odds"), 0.0)
    giveback_ratio = _to_float(row.get("giveback_ratio"), 0.0)

    if symbol != "NAS100":
        return False, "preview_symbol_out_of_scope"
    if surface_name != "continuation_hold_surface":
        return False, "preview_surface_out_of_scope"
    if checkpoint_type != "RUNNER_CHECK":
        return False, "preview_checkpoint_out_of_scope"
    if family != "profit_hold_bias":
        return False, "preview_family_out_of_scope"
    if baseline_action != "HOLD":
        return False, "preview_baseline_action_out_of_scope"
    if unrealized != "OPEN_PROFIT":
        return False, "preview_not_open_profit"
    if giveback_ratio > 0.05:
        return False, "preview_giveback_too_high"
    if not (0.47 <= hold_quality <= 0.54):
        return False, "preview_hold_quality_out_of_band"
    if partial_exit_ev < hold_quality + 0.03:
        return False, "preview_partial_edge_too_small"
    if partial_exit_ev > 0.60:
        return False, "preview_partial_edge_too_high"
    if full_exit_risk > 0.30:
        return False, "preview_full_exit_risk_too_high"
    if continuation < reversal + 0.20:
        return False, "preview_continuation_not_strong_enough"
    return True, "nas100_profit_hold_bias_preview_candidate"


def _preview_action_for_row(row: Mapping[str, Any]) -> tuple[str, str]:
    baseline_action = _baseline_proxy_action(row)
    eligible, eligibility_reason = _eligible_nas100_profit_hold_bias_preview(row)
    if not eligible:
        return baseline_action, eligibility_reason
    return "PARTIAL_THEN_HOLD", "nas100_profit_hold_bias_hold_to_partial_then_hold_preview"


def build_nas100_profit_hold_bias_action_preview(
    resolved_dataset: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_PA8_ACTION_PREVIEW_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "symbol": "NAS100",
        "resolved_row_count": 0,
        "eligible_row_count": 0,
        "preview_changed_row_count": 0,
        "baseline_runtime_proxy_match_rate": 0.0,
        "preview_runtime_proxy_match_rate": 0.0,
        "baseline_hold_precision": 0.0,
        "preview_hold_precision": 0.0,
        "baseline_partial_then_hold_quality": 0.0,
        "preview_partial_then_hold_quality": 0.0,
        "improved_row_count": 0,
        "worsened_row_count": 0,
        "unchanged_row_count": 0,
        "casebook_examples": [],
        "recommended_next_action": "collect_more_nas100_profit_hold_bias_preview_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_PA8_ACTION_PREVIEW_COLUMNS), summary

    required_columns = [
        "symbol",
        "checkpoint_id",
        "surface_name",
        "checkpoint_type",
        "checkpoint_rule_family_hint",
        "runtime_proxy_management_action_label",
        "hindsight_best_management_action_label",
        "unrealized_pnl_state",
        "current_profit",
        "runtime_hold_quality_score",
        "runtime_partial_exit_ev",
        "runtime_full_exit_risk",
        "runtime_continuation_odds",
        "runtime_reversal_odds",
        "giveback_ratio",
    ]
    for column in required_columns:
        if column not in frame.columns:
            frame[column] = ""

    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"] == "NAS100"].copy()
    summary["resolved_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_PA8_ACTION_PREVIEW_COLUMNS), summary

    preview_rows: list[dict[str, Any]] = []
    for row in scoped.to_dict(orient="records"):
        baseline_action = _baseline_proxy_action(row)
        preview_action, preview_reason = _preview_action_for_row(row)
        hindsight_action = _to_text(row.get("hindsight_best_management_action_label")).upper()
        preview_rows.append(
            {
                "symbol": "NAS100",
                "checkpoint_id": _to_text(row.get("checkpoint_id")),
                "surface_name": _to_text(row.get("surface_name")),
                "checkpoint_type": _to_text(row.get("checkpoint_type")).upper(),
                "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
                "baseline_action_label": baseline_action,
                "preview_action_label": preview_action,
                "preview_changed": bool(preview_action != baseline_action),
                "preview_reason": preview_reason,
                "hindsight_best_management_action_label": hindsight_action,
                "baseline_hindsight_match": bool(baseline_action and baseline_action == hindsight_action),
                "preview_hindsight_match": bool(preview_action and preview_action == hindsight_action),
                "current_profit": round(_to_float(row.get("current_profit"), 0.0), 6),
                "runtime_hold_quality_score": round(_to_float(row.get("runtime_hold_quality_score"), 0.0), 6),
                "runtime_partial_exit_ev": round(_to_float(row.get("runtime_partial_exit_ev"), 0.0), 6),
                "runtime_full_exit_risk": round(_to_float(row.get("runtime_full_exit_risk"), 0.0), 6),
                "runtime_continuation_odds": round(_to_float(row.get("runtime_continuation_odds"), 0.0), 6),
                "runtime_reversal_odds": round(_to_float(row.get("runtime_reversal_odds"), 0.0), 6),
                "giveback_ratio": round(_to_float(row.get("giveback_ratio"), 0.0), 6),
            }
        )

    preview_frame = pd.DataFrame(preview_rows)
    if preview_frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_PA8_ACTION_PREVIEW_COLUMNS), summary

    summary["eligible_row_count"] = int(
        preview_frame["preview_reason"].astype(str).eq("nas100_profit_hold_bias_hold_to_partial_then_hold_preview").sum()
    )
    summary["preview_changed_row_count"] = int(preview_frame["preview_changed"].sum())
    baseline_match = int(preview_frame["baseline_hindsight_match"].sum())
    preview_match = int(preview_frame["preview_hindsight_match"].sum())
    summary["baseline_runtime_proxy_match_rate"] = _safe_rate(baseline_match, int(len(preview_frame)))
    summary["preview_runtime_proxy_match_rate"] = _safe_rate(preview_match, int(len(preview_frame)))

    baseline_hold_rows = preview_frame.loc[preview_frame["baseline_action_label"] == "HOLD"]
    preview_hold_rows = preview_frame.loc[preview_frame["preview_action_label"] == "HOLD"]
    baseline_pth_rows = preview_frame.loc[preview_frame["baseline_action_label"] == "PARTIAL_THEN_HOLD"]
    preview_pth_rows = preview_frame.loc[preview_frame["preview_action_label"] == "PARTIAL_THEN_HOLD"]

    summary["baseline_hold_precision"] = _safe_rate(
        int((baseline_hold_rows["hindsight_best_management_action_label"] == "HOLD").sum()),
        int(len(baseline_hold_rows)),
    )
    summary["preview_hold_precision"] = _safe_rate(
        int((preview_hold_rows["hindsight_best_management_action_label"] == "HOLD").sum()),
        int(len(preview_hold_rows)),
    )
    summary["baseline_partial_then_hold_quality"] = _safe_rate(
        int((baseline_pth_rows["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD").sum()),
        int(len(baseline_pth_rows)),
    )
    summary["preview_partial_then_hold_quality"] = _safe_rate(
        int((preview_pth_rows["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD").sum()),
        int(len(preview_pth_rows)),
    )

    improved = int(((preview_frame["preview_hindsight_match"]) & (~preview_frame["baseline_hindsight_match"])).sum())
    worsened = int(((~preview_frame["preview_hindsight_match"]) & (preview_frame["baseline_hindsight_match"])).sum())
    summary["improved_row_count"] = improved
    summary["worsened_row_count"] = worsened
    summary["unchanged_row_count"] = int(len(preview_frame) - improved - worsened)
    summary["casebook_examples"] = (
        preview_frame.loc[preview_frame["preview_changed"]]
        .sort_values(
            by=["checkpoint_rule_family_hint", "checkpoint_type", "checkpoint_id"],
            ascending=[True, True, True],
        )
        .head(20)
        .to_dict(orient="records")
    )

    if (
        summary["preview_changed_row_count"] > 0
        and summary["worsened_row_count"] == 0
        and summary["preview_hold_precision"] >= 0.80
        and summary["preview_runtime_proxy_match_rate"] > summary["baseline_runtime_proxy_match_rate"]
    ):
        summary["recommended_next_action"] = "review_nas100_profit_hold_bias_preview_for_action_only_canary"
    else:
        summary["recommended_next_action"] = "keep_nas100_profit_hold_bias_preview_only"

    return preview_frame.loc[:, PATH_CHECKPOINT_PA8_ACTION_PREVIEW_COLUMNS], summary


def render_nas100_profit_hold_bias_action_preview_markdown(payload: Mapping[str, Any] | None) -> str:
    body = dict(payload or {})
    summary = dict(body.get("summary") or {})
    rows = list(summary.get("casebook_examples", []) or [])

    lines: list[str] = []
    lines.append("# PA8 NAS100 Profit Hold Bias Action Preview")
    lines.append("")
    lines.append(f"- baseline_runtime_proxy_match_rate: `{summary.get('baseline_runtime_proxy_match_rate', 0.0)}`")
    lines.append(f"- preview_runtime_proxy_match_rate: `{summary.get('preview_runtime_proxy_match_rate', 0.0)}`")
    lines.append(f"- baseline_hold_precision: `{summary.get('baseline_hold_precision', 0.0)}`")
    lines.append(f"- preview_hold_precision: `{summary.get('preview_hold_precision', 0.0)}`")
    lines.append(f"- baseline_partial_then_hold_quality: `{summary.get('baseline_partial_then_hold_quality', 0.0)}`")
    lines.append(f"- preview_partial_then_hold_quality: `{summary.get('preview_partial_then_hold_quality', 0.0)}`")
    lines.append(f"- eligible_row_count: `{summary.get('eligible_row_count', 0)}`")
    lines.append(f"- preview_changed_row_count: `{summary.get('preview_changed_row_count', 0)}`")
    lines.append(f"- improved_row_count: `{summary.get('improved_row_count', 0)}`")
    lines.append(f"- worsened_row_count: `{summary.get('worsened_row_count', 0)}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Changed Casebook")
    lines.append("")
    for index, row in enumerate(rows[:20], start=1):
        if not isinstance(row, Mapping):
            continue
        lines.append(f"### {index}. {_to_text(row.get('checkpoint_id'))}")
        lines.append("")
        lines.append(
            f"- action_path: `{_to_text(row.get('baseline_action_label'))} -> {_to_text(row.get('preview_action_label'))} -> {_to_text(row.get('hindsight_best_management_action_label'))}`"
        )
        lines.append(f"- family: `{_to_text(row.get('checkpoint_rule_family_hint'))}`")
        lines.append(f"- surface_name: `{_to_text(row.get('surface_name'))}`")
        lines.append(f"- checkpoint_type: `{_to_text(row.get('checkpoint_type'))}`")
        lines.append(f"- preview_reason: `{_to_text(row.get('preview_reason'))}`")
        lines.append(f"- current_profit: `{_to_float(row.get('current_profit'))}`")
        lines.append(f"- runtime_hold_quality_score: `{_to_float(row.get('runtime_hold_quality_score'))}`")
        lines.append(f"- runtime_partial_exit_ev: `{_to_float(row.get('runtime_partial_exit_ev'))}`")
        lines.append(f"- runtime_full_exit_risk: `{_to_float(row.get('runtime_full_exit_risk'))}`")
        lines.append(f"- runtime_continuation_odds: `{_to_float(row.get('runtime_continuation_odds'))}`")
        lines.append(f"- runtime_reversal_odds: `{_to_float(row.get('runtime_reversal_odds'))}`")
        lines.append(f"- giveback_ratio: `{_to_float(row.get('giveback_ratio'))}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
