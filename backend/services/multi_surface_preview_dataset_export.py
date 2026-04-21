"""Export multi-surface preview datasets from manual/time-axis/failure/adapter artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYSIS_ROOT = PROJECT_ROOT / "data" / "analysis" / "shadow_auto"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "datasets" / "multi_surface_preview"

MULTI_SURFACE_PREVIEW_DATASET_EXPORT_VERSION = "multi_surface_preview_dataset_export_v1"

MULTI_SURFACE_PREVIEW_CORPUS_COLUMNS = [
    "preview_row_id",
    "source_kind",
    "annotation_id",
    "episode_id",
    "symbol",
    "market_family",
    "surface_name",
    "surface_state",
    "action_target",
    "continuation_target",
    "hold_target",
    "protect_target",
    "failure_label",
    "supervision_strength",
    "review_status",
    "training_weight",
    "time_axis_phase",
    "time_axis_quality",
    "time_since_breakout_minutes",
    "time_since_entry_minutes",
    "bars_in_state",
    "momentum_decay",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
    "positive_ev_proxy",
    "do_nothing_ev_proxy",
    "false_positive_cost_proxy",
    "current_focus",
]

INITIAL_ENTRY_DATASET_COLUMNS = [
    "preview_row_id",
    "symbol",
    "market_family",
    "surface_state",
    "action_target",
    "enter_now_binary",
    "failure_label",
    "training_weight",
    "time_axis_phase",
    "bars_in_state",
    "momentum_decay",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
]

FOLLOW_THROUGH_DATASET_COLUMNS = [
    "preview_row_id",
    "symbol",
    "market_family",
    "surface_state",
    "continuation_target",
    "continuation_positive_binary",
    "failure_label",
    "training_weight",
    "time_axis_phase",
    "time_since_breakout_minutes",
    "bars_in_state",
    "momentum_decay",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
]

CONTINUATION_HOLD_DATASET_COLUMNS = [
    "preview_row_id",
    "symbol",
    "market_family",
    "surface_state",
    "hold_target",
    "hold_runner_binary",
    "failure_label",
    "training_weight",
    "time_axis_phase",
    "time_since_entry_minutes",
    "bars_in_state",
    "momentum_decay",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
]

PROTECTIVE_EXIT_DATASET_COLUMNS = [
    "preview_row_id",
    "symbol",
    "market_family",
    "surface_state",
    "protect_target",
    "protect_exit_binary",
    "failure_label",
    "training_weight",
    "time_axis_phase",
    "time_since_entry_minutes",
    "bars_in_state",
    "momentum_decay",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
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


def _json_loads_rows(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    return list((payload or {}).get("rows", []) or [])


def _training_weight(source_kind: str, supervision_strength: str, review_status: str) -> float:
    source = _to_text(source_kind)
    strength = _to_text(supervision_strength).lower()
    review = _to_text(review_status).lower()
    if source == "failure_candidate":
        return 0.35
    if review == "promoted_canonical":
        return 1.0
    if strength == "strong":
        return 1.0
    if strength == "weak":
        return 0.7
    if strength == "diagnostic":
        return 0.45
    return 0.5


def _continuation_positive_binary(value: str) -> int | None:
    target = _to_text(value).upper()
    if not target:
        return None
    return 1 if target in {"CONTINUE_AFTER_BREAK", "PULLBACK_THEN_CONTINUE", "CONTINUE_THEN_PROTECT"} else 0


def _enter_now_binary(value: str) -> int | None:
    target = _to_text(value).upper()
    if not target:
        return None
    if target == "ENTER_NOW":
        return 1
    if target in {"WAIT_MORE", "EXIT_PROTECT"}:
        return 0
    return None


def _hold_runner_binary(value: str) -> int | None:
    target = _to_text(value).upper()
    if not target:
        return None
    return 1 if target == "HOLD_RUNNER" else 0


def _protect_exit_binary(value: str) -> int | None:
    target = _to_text(value).upper()
    if not target:
        return None
    return 1 if target == "EXIT_PROTECT" else 0


def _adapter_lookup(adapter_payload: Mapping[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _json_loads_rows(adapter_payload):
        market_family = _to_text(row.get("market_family")).upper()
        surface_name = _to_text(row.get("surface_name"))
        if market_family and surface_name:
            lookup[(market_family, surface_name)] = dict(row)
    return lookup


def _time_axis_lookup(time_axis_payload: Mapping[str, Any] | None) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in _json_loads_rows(time_axis_payload):
        key = (
            _to_text(row.get("annotation_id")),
            _to_text(row.get("episode_id")),
            _to_text(row.get("market_family")).upper(),
            _to_text(row.get("surface_label_family")),
        )
        lookup[key] = dict(row)
    return lookup


def _manual_corpus_rows(
    check_color_payload: Mapping[str, Any] | None,
    time_axis_payload: Mapping[str, Any] | None,
    adapter_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    time_lookup = _time_axis_lookup(time_axis_payload)
    adapter_lookup = _adapter_lookup(adapter_payload)
    for idx, row in enumerate(_json_loads_rows(check_color_payload), start=1):
        market_family = _to_text(row.get("market_family") or row.get("symbol")).upper()
        surface_name = _to_text(row.get("surface_label_family"))
        surface_state = _to_text(row.get("surface_label_state"))
        annotation_id = _to_text(row.get("annotation_id"))
        episode_id = _to_text(row.get("episode_id"))
        key = (annotation_id, episode_id, market_family, surface_name)
        time_row = time_lookup.get(key, {})
        if not time_row:
            fallback_key = ("", episode_id, market_family, surface_name)
            time_row = time_lookup.get(fallback_key, {})
        adapter_row = adapter_lookup.get((market_family, surface_name), {})

        action_target = _to_text(row.get("aligned_action_target") or row.get("surface_action_bias"))
        continuation_target = _to_text(row.get("aligned_continuation_target") or row.get("continuation_support_label"))
        protect_target = _to_text(row.get("exit_management_support_label"))
        hold_target = ""
        if surface_name == "continuation_hold_surface":
            hold_target = "HOLD_RUNNER"
        training_weight = _training_weight("manual_label", _to_text(row.get("supervision_strength")), _to_text(row.get("review_status")))
        rows.append(
            {
                "preview_row_id": f"multi_surface_preview::manual::{idx:04d}",
                "source_kind": "manual_label",
                "annotation_id": annotation_id,
                "episode_id": episode_id,
                "symbol": _to_text(row.get("symbol")).upper(),
                "market_family": market_family,
                "surface_name": surface_name,
                "surface_state": surface_state,
                "action_target": action_target,
                "continuation_target": continuation_target,
                "hold_target": hold_target,
                "protect_target": protect_target,
                "failure_label": _to_text(row.get("failure_label")),
                "supervision_strength": _to_text(row.get("supervision_strength")),
                "review_status": _to_text(row.get("review_status")),
                "training_weight": training_weight,
                "time_axis_phase": _to_text(time_row.get("time_axis_phase")),
                "time_axis_quality": _to_text(time_row.get("time_axis_quality")),
                "time_since_breakout_minutes": round(_to_float(time_row.get("time_since_breakout_minutes")), 6),
                "time_since_entry_minutes": round(_to_float(time_row.get("time_since_entry_minutes")), 6),
                "bars_in_state": round(_to_float(time_row.get("bars_in_state")), 6),
                "momentum_decay": round(_to_float(time_row.get("momentum_decay")), 6),
                "adapter_mode": _to_text(adapter_row.get("adapter_mode")),
                "recommended_bias_action": _to_text(adapter_row.get("recommended_bias_action")),
                "objective_key": _to_text(adapter_row.get("objective_key")),
                "positive_ev_proxy": _to_text(adapter_row.get("positive_ev_proxy")),
                "do_nothing_ev_proxy": _to_text(adapter_row.get("do_nothing_ev_proxy")),
                "false_positive_cost_proxy": _to_text(adapter_row.get("false_positive_cost_proxy")),
                "current_focus": _to_text(adapter_row.get("current_focus")),
            }
        )
    return rows


def _continuation_hold_candidate_rows(
    failure_payload: Mapping[str, Any] | None,
    adapter_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    adapter_lookup = _adapter_lookup(adapter_payload)
    harvest_rows = _json_loads_rows(failure_payload)
    idx = 0
    for row in harvest_rows:
        surface_name = _to_text(row.get("surface_label_family"))
        if surface_name != "continuation_hold_surface":
            continue
        idx += 1
        market_family = _to_text(row.get("market_family") or row.get("symbol")).upper()
        adapter_row = adapter_lookup.get((market_family, surface_name), {})
        failure_label = _to_text(row.get("failure_label"))
        hold_target = "HOLD_RUNNER" if failure_label == "early_exit_regret" else "LOCK_PROFIT"
        rows.append(
            {
                "preview_row_id": f"multi_surface_preview::failure::{idx:04d}",
                "source_kind": "failure_candidate",
                "annotation_id": "",
                "episode_id": _to_text(row.get("source_observation_id")),
                "symbol": _to_text(row.get("symbol")).upper(),
                "market_family": market_family,
                "surface_name": surface_name,
                "surface_state": _to_text(row.get("surface_label_state"), "runner_preservation_candidate"),
                "action_target": "",
                "continuation_target": "",
                "hold_target": hold_target,
                "protect_target": "",
                "failure_label": failure_label,
                "supervision_strength": _to_text(row.get("harvest_strength")),
                "review_status": _to_text(row.get("harvest_source")),
                "training_weight": _training_weight("failure_candidate", _to_text(row.get("harvest_strength")), _to_text(row.get("harvest_source"))),
                "time_axis_phase": _to_text(row.get("time_axis_phase")),
                "time_axis_quality": "harvest_candidate",
                "time_since_breakout_minutes": round(_to_float(row.get("time_since_breakout_minutes")), 6),
                "time_since_entry_minutes": round(_to_float(row.get("time_since_entry_minutes")), 6),
                "bars_in_state": round(_to_float(row.get("bars_in_state")), 6),
                "momentum_decay": round(_to_float(row.get("momentum_decay")), 6),
                "adapter_mode": _to_text(adapter_row.get("adapter_mode")),
                "recommended_bias_action": _to_text(adapter_row.get("recommended_bias_action")),
                "objective_key": _to_text(adapter_row.get("objective_key")),
                "positive_ev_proxy": _to_text(adapter_row.get("positive_ev_proxy")),
                "do_nothing_ev_proxy": _to_text(adapter_row.get("do_nothing_ev_proxy")),
                "false_positive_cost_proxy": _to_text(adapter_row.get("false_positive_cost_proxy")),
                "current_focus": _to_text(adapter_row.get("current_focus")),
            }
        )
    return rows


def _dataset_summary(frame: pd.DataFrame, *, target_column: str) -> dict[str, Any]:
    if frame.empty:
        return {"rows": 0, "symbol_counts": {}, "target_counts": {}}
    target_series = frame[target_column].fillna("").astype(str).str.strip() if target_column in frame.columns else pd.Series(dtype=str)
    target_series = target_series.replace("", pd.NA).dropna()
    return {
        "rows": int(len(frame)),
        "symbol_counts": frame["symbol"].value_counts().to_dict() if "symbol" in frame.columns else {},
        "target_counts": target_series.value_counts().to_dict() if not target_series.empty else {},
    }


def build_multi_surface_preview_dataset_export(
    check_color_payload: Mapping[str, Any] | None,
    surface_time_axis_payload: Mapping[str, Any] | None,
    failure_label_payload: Mapping[str, Any] | None,
    market_adapter_layer_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any], list[dict[str, Any]]]:
    corpus_rows = _manual_corpus_rows(check_color_payload, surface_time_axis_payload, market_adapter_layer_payload)
    corpus_rows.extend(_continuation_hold_candidate_rows(failure_label_payload, market_adapter_layer_payload))
    corpus = pd.DataFrame(corpus_rows, columns=MULTI_SURFACE_PREVIEW_CORPUS_COLUMNS)

    initial_entry = corpus.loc[corpus["surface_name"] == "initial_entry_surface"].copy()
    initial_entry["enter_now_binary"] = initial_entry["action_target"].map(_enter_now_binary)
    initial_entry_dataset = initial_entry[INITIAL_ENTRY_DATASET_COLUMNS].copy()

    follow_through = corpus.loc[corpus["surface_name"] == "follow_through_surface"].copy()
    follow_through["continuation_positive_binary"] = follow_through["continuation_target"].map(_continuation_positive_binary)
    follow_through_dataset = follow_through[FOLLOW_THROUGH_DATASET_COLUMNS].copy()

    continuation_hold = corpus.loc[corpus["surface_name"] == "continuation_hold_surface"].copy()
    continuation_hold["hold_runner_binary"] = continuation_hold["hold_target"].map(_hold_runner_binary)
    continuation_hold_dataset = continuation_hold[CONTINUATION_HOLD_DATASET_COLUMNS].copy()

    protective_exit = corpus.loc[corpus["surface_name"] == "protective_exit_surface"].copy()
    protective_exit["protect_exit_binary"] = protective_exit["protect_target"].map(_protect_exit_binary)
    protective_exit_dataset = protective_exit[PROTECTIVE_EXIT_DATASET_COLUMNS].copy()

    datasets = {
        "initial_entry": initial_entry_dataset,
        "follow_through": follow_through_dataset,
        "continuation_hold": continuation_hold_dataset,
        "protective_exit": protective_exit_dataset,
    }
    summary = {
        "multi_surface_preview_dataset_export_version": MULTI_SURFACE_PREVIEW_DATASET_EXPORT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "corpus_row_count": int(len(corpus)),
        "surface_counts": corpus["surface_name"].value_counts().to_dict() if not corpus.empty else {},
        "symbol_counts": corpus["symbol"].value_counts().to_dict() if not corpus.empty else {},
        "dataset_summaries": {
            "initial_entry": _dataset_summary(initial_entry_dataset, target_column="action_target"),
            "follow_through": _dataset_summary(follow_through_dataset, target_column="continuation_target"),
            "continuation_hold": _dataset_summary(continuation_hold_dataset, target_column="hold_target"),
            "protective_exit": _dataset_summary(protective_exit_dataset, target_column="protect_target"),
        },
        "recommended_next_action": "proceed_to_mf16_symbol_surface_preview_evaluation",
    }
    return corpus, datasets, summary, corpus.to_dict(orient="records")


def render_multi_surface_preview_dataset_export_markdown(summary: Mapping[str, Any], corpus: pd.DataFrame) -> str:
    dataset_summaries = dict(summary.get("dataset_summaries", {}) or {}) if isinstance(summary, Mapping) else {}
    lines = [
        "# Multi-Surface Preview Dataset Export",
        "",
        f"- version: `{summary.get('multi_surface_preview_dataset_export_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- corpus_row_count: `{summary.get('corpus_row_count', 0)}`",
        f"- surface_counts: `{summary.get('surface_counts', {})}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
        "## Datasets",
        "",
    ]
    for dataset_key in ("initial_entry", "follow_through", "continuation_hold", "protective_exit"):
        dataset_summary = dict(dataset_summaries.get(dataset_key, {}) or {})
        lines.extend(
            [
                f"### {dataset_key}",
                "",
                f"- rows: `{dataset_summary.get('rows', 0)}`",
                f"- symbol_counts: `{dataset_summary.get('symbol_counts', {})}`",
                f"- target_counts: `{dataset_summary.get('target_counts', {})}`",
                "",
            ]
        )
    if not corpus.empty:
        lines.extend(["## Sample Rows", ""])
        for row in corpus.head(10).to_dict(orient="records"):
            lines.append(
                "- "
                + f"{row.get('symbol', '')} | {row.get('surface_name', '')} | "
                + f"{row.get('surface_state', '')} | target={row.get('action_target') or row.get('continuation_target') or row.get('hold_target') or row.get('protect_target') or 'NONE'} | "
                + f"adapter={row.get('adapter_mode', '')}"
            )
    return "\n".join(lines).rstrip() + "\n"


def _try_write_parquet(frame: pd.DataFrame, path: Path) -> bool:
    try:
        frame.to_parquet(path, index=False)
        return True
    except Exception:
        return False


def write_multi_surface_preview_dataset_export(
    *,
    check_color_payload: Mapping[str, Any] | None,
    surface_time_axis_payload: Mapping[str, Any] | None,
    failure_label_payload: Mapping[str, Any] | None,
    market_adapter_layer_payload: Mapping[str, Any] | None,
    analysis_csv_path: str | Path | None = None,
    analysis_json_path: str | Path | None = None,
    analysis_md_path: str | Path | None = None,
    dataset_dir: str | Path | None = None,
) -> dict[str, Any]:
    corpus, datasets, summary, corpus_rows = build_multi_surface_preview_dataset_export(
        check_color_payload,
        surface_time_axis_payload,
        failure_label_payload,
        market_adapter_layer_payload,
    )
    analysis_root = DEFAULT_ANALYSIS_ROOT
    dataset_root = Path(dataset_dir) if dataset_dir is not None else DEFAULT_DATASET_DIR
    if not dataset_root.is_absolute():
        dataset_root = PROJECT_ROOT / dataset_root
    dataset_root.mkdir(parents=True, exist_ok=True)

    csv_path = Path(analysis_csv_path) if analysis_csv_path is not None else analysis_root / "multi_surface_preview_dataset_export_latest.csv"
    json_path = Path(analysis_json_path) if analysis_json_path is not None else analysis_root / "multi_surface_preview_dataset_export_latest.json"
    md_path = Path(analysis_md_path) if analysis_md_path is not None else analysis_root / "multi_surface_preview_dataset_export_latest.md"
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path
    if not json_path.is_absolute():
        json_path = PROJECT_ROOT / json_path
    if not md_path.is_absolute():
        md_path = PROJECT_ROOT / md_path
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    corpus.to_csv(csv_path, index=False, encoding="utf-8-sig")
    markdown = render_multi_surface_preview_dataset_export_markdown(summary, corpus)

    dataset_outputs: dict[str, dict[str, Any]] = {}
    for dataset_key, frame in datasets.items():
        csv_dataset_path = dataset_root / f"{dataset_key}_dataset.csv"
        frame.to_csv(csv_dataset_path, index=False, encoding="utf-8-sig")
        parquet_dataset_path = dataset_root / f"{dataset_key}_dataset.parquet"
        parquet_written = _try_write_parquet(frame, parquet_dataset_path)
        dataset_outputs[dataset_key] = {
            "csv_path": str(csv_dataset_path),
            "parquet_path": str(parquet_dataset_path) if parquet_written else "",
            "parquet_written": parquet_written,
            "row_count": int(len(frame)),
        }

    payload = {
        "summary": summary,
        "dataset_outputs": dataset_outputs,
        "corpus_rows": corpus_rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return {
        "analysis_csv_path": str(csv_path),
        "analysis_json_path": str(json_path),
        "analysis_md_path": str(md_path),
        "dataset_outputs": dataset_outputs,
        "summary": summary,
    }
