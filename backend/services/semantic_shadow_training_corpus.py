"""Build a preview semantic-shadow training corpus from current + curated legacy bridges."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.forecast_state25_outcome_bridge import (
    write_forecast_state25_outcome_bridge_report,
)
from backend.services.trade_csv_schema import now_kst_dt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CURRENT_BRIDGE_PATH = (
    PROJECT_ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.json"
)
DEFAULT_LEGACY_OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "training_bridge_sources"
DEFAULT_LEGACY_ENTRY_PATHS = (
    PROJECT_ROOT / "data" / "trades" / "entry_decisions.legacy_20260404_152625.csv",
    PROJECT_ROOT / "data" / "trades" / "entry_decisions.legacy_20260404_153736.csv",
)

SEMANTIC_SHADOW_TRAINING_CORPUS_VERSION = "semantic_shadow_training_corpus_v0"
SEMANTIC_SHADOW_TRAINING_CORPUS_COLUMNS = [
    "corpus_row_id",
    "corpus_source_type",
    "corpus_source_id",
    "corpus_source_path",
    "symbol",
    "signal_bar_ts",
    "row_key",
    "bridge_quality_status",
    "entry_wait_quality_label",
    "learning_total_label",
    "learning_total_score",
    "loss_quality_label",
    "signed_exit_score",
    "profit",
    "transition_label_status",
    "management_label_status",
    "scene_family",
    "wait_bias_hint",
    "forecast_decision_hint",
]


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


def _to_float(value: Any, default: float | None = None) -> float | None:
    text = _to_text(value)
    if not text:
        return default
    try:
        return float(text)
    except Exception:
        return default


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _load_report_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _current_bridge_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _load_report_rows(path)
    return rows, {
        "source_type": "current_bridge",
        "source_id": path.stem,
        "source_path": str(path),
        "row_count": int(len(rows)),
    }


def _legacy_bridge_rows(entry_path: Path, *, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{entry_path.stem}_forecast_state25_outcome_bridge.json"
    report_md = report_json.with_suffix(".md")
    report = write_forecast_state25_outcome_bridge_report(
        entry_decision_path=entry_path,
        output_path=report_json,
        markdown_output_path=report_md,
    )
    rows = [dict(row) for row in report.get("rows", []) if isinstance(row, Mapping)]
    return rows, {
        "source_type": "legacy_bridge",
        "source_id": entry_path.stem,
        "source_path": str(entry_path),
        "report_path": str(report_json),
        "row_count": int(len(rows)),
        "full_outcome_eligible_rows": int(
            _as_mapping(report.get("summary")).get("full_outcome_eligible_rows", 0) or 0
        ),
    }


def _row_summary(
    row: Mapping[str, Any],
    *,
    corpus_row_id: str,
    source_type: str,
    source_id: str,
    source_path: str,
) -> dict[str, Any]:
    economic = _as_mapping(row.get("economic_target_summary"))
    compact = _as_mapping(row.get("outcome_label_compact_summary_v1"))
    state_hint = _as_mapping(row.get("state25_runtime_hint_v1"))
    forecast = _as_mapping(row.get("forecast_runtime_summary_v1"))
    return {
        "corpus_row_id": corpus_row_id,
        "corpus_source_type": source_type,
        "corpus_source_id": source_id,
        "corpus_source_path": source_path,
        "symbol": _to_text(row.get("symbol")).upper(),
        "signal_bar_ts": _to_text(row.get("signal_bar_ts")),
        "row_key": _to_text(row.get("row_key")),
        "bridge_quality_status": _to_text(row.get("bridge_quality_status")),
        "entry_wait_quality_label": _to_text(row.get("entry_wait_quality_label")),
        "learning_total_label": _to_text(economic.get("learning_total_label")).lower(),
        "learning_total_score": _to_float(economic.get("learning_total_score")),
        "loss_quality_label": _to_text(economic.get("loss_quality_label")).lower(),
        "signed_exit_score": _to_float(economic.get("signed_exit_score")),
        "profit": _to_float(economic.get("profit")),
        "transition_label_status": _to_text(compact.get("transition_label_status")).upper(),
        "management_label_status": _to_text(compact.get("management_label_status")).upper(),
        "scene_family": _to_text(state_hint.get("scene_family")).lower(),
        "wait_bias_hint": _to_text(state_hint.get("wait_bias_hint")).lower(),
        "forecast_decision_hint": _to_text(forecast.get("decision_hint")).upper(),
    }


def build_semantic_shadow_training_corpus(
    *,
    current_bridge_path: str | Path | None = None,
    legacy_entry_paths: Sequence[str | Path] | None = None,
    legacy_output_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    current_path = Path(current_bridge_path) if current_bridge_path is not None else DEFAULT_CURRENT_BRIDGE_PATH
    resolved_legacy_paths = DEFAULT_LEGACY_ENTRY_PATHS if legacy_entry_paths is None else legacy_entry_paths
    legacy_paths = tuple(Path(path) for path in resolved_legacy_paths)
    output_dir = Path(legacy_output_dir) if legacy_output_dir is not None else DEFAULT_LEGACY_OUTPUT_DIR

    source_summaries: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, Any]] = []
    flat_rows: list[dict[str, Any]] = []

    current_rows, current_summary = _current_bridge_rows(current_path)
    source_summaries.append(current_summary)
    for idx, row in enumerate(current_rows, start=1):
        enriched = dict(row)
        enriched["corpus_source_type"] = current_summary["source_type"]
        enriched["corpus_source_id"] = current_summary["source_id"]
        enriched["corpus_source_path"] = current_summary["source_path"]
        enriched["corpus_row_id"] = f"shadow_corpus::current::{idx:04d}"
        enriched_rows.append(enriched)
        flat_rows.append(
            _row_summary(
                row,
                corpus_row_id=enriched["corpus_row_id"],
                source_type=current_summary["source_type"],
                source_id=current_summary["source_id"],
                source_path=current_summary["source_path"],
            )
        )

    for legacy_path in legacy_paths:
        if not legacy_path.exists():
            source_summaries.append(
                {
                    "source_type": "legacy_bridge",
                    "source_id": legacy_path.stem,
                    "source_path": str(legacy_path),
                    "row_count": 0,
                    "status": "missing_source_csv",
                }
            )
            continue
        legacy_rows, legacy_summary = _legacy_bridge_rows(legacy_path, output_dir=output_dir)
        source_summaries.append(legacy_summary)
        for idx, row in enumerate(legacy_rows, start=1):
            enriched = dict(row)
            enriched["corpus_source_type"] = legacy_summary["source_type"]
            enriched["corpus_source_id"] = legacy_summary["source_id"]
            enriched["corpus_source_path"] = legacy_summary["source_path"]
            enriched["corpus_row_id"] = f"shadow_corpus::{legacy_path.stem}::{idx:04d}"
            enriched_rows.append(enriched)
            flat_rows.append(
                _row_summary(
                    row,
                    corpus_row_id=enriched["corpus_row_id"],
                    source_type=legacy_summary["source_type"],
                    source_id=legacy_summary["source_id"],
                    source_path=legacy_summary["source_path"],
                )
            )

    frame = pd.DataFrame(flat_rows, columns=SEMANTIC_SHADOW_TRAINING_CORPUS_COLUMNS)
    summary = {
        "semantic_shadow_training_corpus_version": SEMANTIC_SHADOW_TRAINING_CORPUS_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "source_count": int(len(source_summaries)),
        "symbol_counts": frame["symbol"].value_counts().to_dict() if not frame.empty else {},
        "bridge_quality_status_counts": frame["bridge_quality_status"].value_counts().to_dict() if not frame.empty else {},
        "learning_total_label_counts": frame["learning_total_label"].value_counts().to_dict() if not frame.empty else {},
        "entry_wait_quality_label_counts": frame["entry_wait_quality_label"].value_counts().to_dict() if not frame.empty else {},
        "source_summaries": source_summaries,
    }
    return frame, summary, enriched_rows


def render_semantic_shadow_training_corpus_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Semantic Shadow Training Corpus",
        "",
        f"- version: `{summary.get('semantic_shadow_training_corpus_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- source_count: `{summary.get('source_count', 0)}`",
        "",
        "## Aggregate",
        "",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- bridge_quality_status_counts: `{summary.get('bridge_quality_status_counts', {})}`",
        f"- learning_total_label_counts: `{summary.get('learning_total_label_counts', {})}`",
        f"- entry_wait_quality_label_counts: `{summary.get('entry_wait_quality_label_counts', {})}`",
        "",
        "## Sources",
        "",
    ]
    for source in summary.get("source_summaries", []):
        lines.append(
            "- "
            f"{source.get('source_id', '')}: type={source.get('source_type', '')}, "
            f"rows={source.get('row_count', 0)}, "
            f"path={source.get('source_path', '')}"
        )
    lines.extend(["", "## Sample Rows", ""])
    if frame.empty:
        lines.append("- no training corpus rows available")
        return "\n".join(lines) + "\n"
    for row in frame.head(10).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('corpus_row_id', '')}",
                "",
                f"- symbol: `{row.get('symbol', '')}`",
                f"- bridge_quality_status: `{row.get('bridge_quality_status', '')}`",
                f"- learning_total_label: `{row.get('learning_total_label', '')}`",
                f"- signed_exit_score: `{row.get('signed_exit_score', '')}`",
                f"- source: `{row.get('corpus_source_id', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
