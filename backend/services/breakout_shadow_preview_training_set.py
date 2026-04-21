"""Build breakout-specific preview training corpora from canonical aligned seeds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_PATH = PROJECT_ROOT / "data" / "analysis" / "breakout_event" / "breakout_aligned_training_seed_latest.csv"
DEFAULT_ANALYSIS_ROOT = PROJECT_ROOT / "data" / "analysis" / "shadow_auto"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "datasets" / "breakout_shadow_preview"

BREAKOUT_SHADOW_PREVIEW_TRAINING_SET_VERSION = "breakout_shadow_preview_training_set_v1"
BREAKOUT_SHADOW_PREVIEW_CORPUS_COLUMNS = [
    "preview_row_id",
    "episode_id",
    "symbol",
    "action_target",
    "continuation_target",
    "matched_job_id",
    "matched_decision_time",
    "seed_grade",
    "training_weight",
    "timing_target_now_vs_wait",
    "continuation_target_binary",
    "exit_target_protect",
    "transition_label_status",
    "management_label_status",
    "transition_hit_rate",
    "management_hit_rate",
    "p_buy_confirm",
    "actual_buy_confirm",
    "p_continuation_success",
    "actual_continuation_success",
    "p_false_break",
    "actual_false_break",
    "p_continue_favor",
    "actual_continue_favor",
    "p_fail_now",
    "actual_fail_now",
    "p_opposite_edge_reach",
    "actual_opposite_edge_reach",
]

BREAKOUT_TIMING_DATASET_COLUMNS = [
    "preview_row_id",
    "episode_id",
    "symbol",
    "seed_grade",
    "training_weight",
    "p_buy_confirm",
    "p_continuation_success",
    "p_false_break",
    "transition_hit_rate",
    "management_hit_rate",
    "timing_target_now_vs_wait",
]

BREAKOUT_CONTINUATION_DATASET_COLUMNS = [
    "preview_row_id",
    "episode_id",
    "symbol",
    "seed_grade",
    "training_weight",
    "p_buy_confirm",
    "p_continuation_success",
    "p_false_break",
    "p_continue_favor",
    "p_fail_now",
    "p_opposite_edge_reach",
    "transition_hit_rate",
    "management_hit_rate",
    "actual_buy_confirm",
    "actual_continuation_success",
    "actual_false_break",
    "actual_continue_favor",
    "actual_fail_now",
    "actual_opposite_edge_reach",
    "continuation_target_binary",
]

BREAKOUT_EXIT_DATASET_COLUMNS = [
    "preview_row_id",
    "episode_id",
    "symbol",
    "seed_grade",
    "training_weight",
    "p_continue_favor",
    "p_fail_now",
    "p_opposite_edge_reach",
    "management_hit_rate",
    "actual_continue_favor",
    "actual_fail_now",
    "actual_opposite_edge_reach",
    "exit_target_protect",
]


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_float(value: object, default: float = 0.0) -> float:
    text = _to_text(value)
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _to_int_binary(value: object) -> int | None:
    text = _to_text(value, "")
    if text == "":
        return None
    if text in {"1", "true", "True"}:
        return 1
    if text in {"0", "false", "False"}:
        return 0
    return None


def _training_weight(seed_grade: str) -> float:
    grade = _to_text(seed_grade, "").lower()
    if grade == "strict":
        return 1.0
    if grade == "good":
        return 0.85
    if grade == "coarse_review":
        return 0.6
    if grade == "loose_review":
        return 0.35
    return 0.0


def _load_seed_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=BREAKOUT_SHADOW_PREVIEW_CORPUS_COLUMNS)
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(path, low_memory=False)


def _build_corpus_frame(seed_frame: pd.DataFrame) -> pd.DataFrame:
    if seed_frame.empty:
        return pd.DataFrame(columns=BREAKOUT_SHADOW_PREVIEW_CORPUS_COLUMNS)
    promoted = seed_frame[seed_frame.get("promote_to_training", False).astype(str).str.lower().isin({"true", "1"})].copy()
    if promoted.empty:
        return pd.DataFrame(columns=BREAKOUT_SHADOW_PREVIEW_CORPUS_COLUMNS)

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(promoted.to_dict("records"), start=1):
        action_target = _to_text(row.get("action_target"), "").upper()
        continuation_target = _to_text(row.get("continuation_target"), "").upper()
        timing_target = None
        if action_target == "ENTER_NOW":
            timing_target = 1
        elif action_target == "WAIT_MORE":
            timing_target = 0

        continuation_binary = 1 if continuation_target in {"CONTINUE_AFTER_BREAK", "PULLBACK_THEN_CONTINUE"} else 0
        exit_target = 1 if action_target == "EXIT_PROTECT" else 0
        rows.append(
            {
                "preview_row_id": f"breakout_preview::{idx:04d}",
                "episode_id": _to_text(row.get("episode_id"), ""),
                "symbol": _to_text(row.get("symbol"), "").upper(),
                "action_target": action_target,
                "continuation_target": continuation_target,
                "matched_job_id": _to_text(row.get("matched_job_id"), ""),
                "matched_decision_time": _to_text(row.get("matched_decision_time"), ""),
                "seed_grade": _to_text(row.get("seed_grade"), ""),
                "training_weight": _training_weight(_to_text(row.get("seed_grade"), "")),
                "timing_target_now_vs_wait": timing_target,
                "continuation_target_binary": continuation_binary,
                "exit_target_protect": exit_target,
                "transition_label_status": _to_text(row.get("transition_label_status"), ""),
                "management_label_status": _to_text(row.get("management_label_status"), ""),
                "transition_hit_rate": _to_float(row.get("transition_hit_rate"), 0.0),
                "management_hit_rate": _to_float(row.get("management_hit_rate"), 0.0),
                "p_buy_confirm": _to_float(row.get("p_buy_confirm"), 0.0),
                "actual_buy_confirm": _to_int_binary(row.get("actual_buy_confirm")),
                "p_continuation_success": _to_float(row.get("p_continuation_success"), 0.0),
                "actual_continuation_success": _to_int_binary(row.get("actual_continuation_success")),
                "p_false_break": _to_float(row.get("p_false_break"), 0.0),
                "actual_false_break": _to_int_binary(row.get("actual_false_break")),
                "p_continue_favor": _to_float(row.get("p_continue_favor"), 0.0),
                "actual_continue_favor": _to_int_binary(row.get("actual_continue_favor")),
                "p_fail_now": _to_float(row.get("p_fail_now"), 0.0),
                "actual_fail_now": _to_int_binary(row.get("actual_fail_now")),
                "p_opposite_edge_reach": _to_float(row.get("p_opposite_edge_reach"), 0.0),
                "actual_opposite_edge_reach": _to_int_binary(row.get("actual_opposite_edge_reach")),
            }
        )
    return pd.DataFrame(rows, columns=BREAKOUT_SHADOW_PREVIEW_CORPUS_COLUMNS)


def _dataset_summary(frame: pd.DataFrame, *, target_column: str) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "symbol_counts": {},
            "target_counts": {},
        }
    target_series = frame[target_column].dropna() if target_column in frame.columns else pd.Series(dtype="int64")
    return {
        "rows": int(len(frame)),
        "symbol_counts": frame["symbol"].value_counts().to_dict() if "symbol" in frame.columns else {},
        "target_counts": target_series.astype(str).value_counts().to_dict() if not target_series.empty else {},
    }


def build_breakout_shadow_preview_training_set(
    *,
    seed_csv_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any], list[dict[str, Any]]]:
    seed_path = _resolve_path(seed_csv_path, DEFAULT_SEED_PATH)
    seed_frame = _load_seed_frame(seed_path)
    corpus = _build_corpus_frame(seed_frame)

    timing_dataset = corpus[corpus["timing_target_now_vs_wait"].notna()].copy()
    timing_dataset = timing_dataset[BREAKOUT_TIMING_DATASET_COLUMNS].copy()

    continuation_dataset = corpus[BREAKOUT_CONTINUATION_DATASET_COLUMNS].copy()

    exit_dataset = corpus[BREAKOUT_EXIT_DATASET_COLUMNS].copy()

    datasets = {
        "timing": timing_dataset,
        "breakout_continuation": continuation_dataset,
        "exit_management": exit_dataset,
    }
    summary = {
        "breakout_shadow_preview_training_set_version": BREAKOUT_SHADOW_PREVIEW_TRAINING_SET_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "seed_csv_path": str(seed_path),
        "corpus_row_count": int(len(corpus)),
        "symbol_counts": corpus["symbol"].value_counts().to_dict() if not corpus.empty else {},
        "action_target_counts": corpus["action_target"].value_counts().to_dict() if not corpus.empty else {},
        "continuation_target_counts": corpus["continuation_target"].value_counts().to_dict() if not corpus.empty else {},
        "dataset_summaries": {
            "timing": _dataset_summary(timing_dataset, target_column="timing_target_now_vs_wait"),
            "breakout_continuation": _dataset_summary(continuation_dataset, target_column="continuation_target_binary"),
            "exit_management": _dataset_summary(exit_dataset, target_column="exit_target_protect"),
        },
    }
    return corpus, datasets, summary, corpus.to_dict(orient="records")


def render_breakout_shadow_preview_training_set_markdown(
    summary: Mapping[str, Any],
    corpus: pd.DataFrame,
) -> str:
    lines = [
        "# Breakout Shadow Preview Training Set",
        "",
        f"- version: `{summary.get('breakout_shadow_preview_training_set_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- corpus_row_count: `{summary.get('corpus_row_count', 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- action_target_counts: `{summary.get('action_target_counts', {})}`",
        "",
        "## Datasets",
        "",
    ]
    dataset_summaries = summary.get("dataset_summaries", {}) if isinstance(summary, Mapping) else {}
    for dataset_key in ("timing", "breakout_continuation", "exit_management"):
        dataset_summary = dataset_summaries.get(dataset_key, {}) if isinstance(dataset_summaries, Mapping) else {}
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
                f"{row.get('episode_id', '')} | {row.get('symbol', '')} | "
                f"{row.get('action_target', '')} | {row.get('continuation_target', '')} | "
                f"weight={row.get('training_weight', 0)}"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_shadow_preview_training_set(
    *,
    seed_csv_path: str | Path | None = None,
    analysis_csv_path: str | Path | None = None,
    analysis_json_path: str | Path | None = None,
    analysis_md_path: str | Path | None = None,
    dataset_dir: str | Path | None = None,
) -> dict[str, Any]:
    analysis_csv = _resolve_path(analysis_csv_path, DEFAULT_ANALYSIS_ROOT / "breakout_shadow_preview_training_set_latest.csv")
    analysis_json = _resolve_path(analysis_json_path, DEFAULT_ANALYSIS_ROOT / "breakout_shadow_preview_training_set_latest.json")
    analysis_md = _resolve_path(analysis_md_path, DEFAULT_ANALYSIS_ROOT / "breakout_shadow_preview_training_set_latest.md")
    dataset_root = _resolve_path(dataset_dir, DEFAULT_DATASET_DIR)

    corpus, datasets, summary, enriched_rows = build_breakout_shadow_preview_training_set(seed_csv_path=seed_csv_path)

    analysis_csv.parent.mkdir(parents=True, exist_ok=True)
    corpus.to_csv(analysis_csv, index=False, encoding="utf-8-sig")
    analysis_json.write_text(json.dumps({"summary": summary, "rows": enriched_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis_md.write_text(render_breakout_shadow_preview_training_set_markdown(summary, corpus), encoding="utf-8")

    dataset_root.mkdir(parents=True, exist_ok=True)
    dataset_artifacts: dict[str, dict[str, Any]] = {}
    for dataset_key, frame in datasets.items():
        parquet_path = dataset_root / f"{dataset_key}_dataset.parquet"
        summary_path = dataset_root / f"{dataset_key}_dataset.parquet.summary.json"
        frame.to_parquet(parquet_path, index=False)
        target_column = {
            "timing": "timing_target_now_vs_wait",
            "breakout_continuation": "continuation_target_binary",
            "exit_management": "exit_target_protect",
        }[dataset_key]
        dataset_summary = _dataset_summary(frame, target_column=target_column)
        summary_path.write_text(json.dumps(dataset_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        dataset_artifacts[dataset_key] = {
            "dataset_path": str(parquet_path),
            "summary_path": str(summary_path),
            **dataset_summary,
        }

    payload = {
        "summary": {**summary, "dataset_artifacts": dataset_artifacts},
        "rows": enriched_rows,
        "analysis_csv_path": str(analysis_csv),
        "analysis_json_path": str(analysis_json),
        "analysis_md_path": str(analysis_md),
        "dataset_dir": str(dataset_root),
    }
    analysis_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
