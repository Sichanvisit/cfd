from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


SEMANTIC_BASELINE_NO_ACTION_SAMPLE_AUDIT_CONTRACT_VERSION = (
    "semantic_baseline_no_action_sample_audit_v1"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def default_semantic_baseline_no_action_sample_audit_json_path() -> Path:
    return _shadow_auto_dir() / "semantic_baseline_no_action_sample_audit_latest.json"


def default_semantic_baseline_no_action_sample_audit_markdown_path() -> Path:
    return _shadow_auto_dir() / "semantic_baseline_no_action_sample_audit_latest.md"


def _default_entry_decisions_csv_path() -> Path:
    return _repo_root() / "data" / "trades" / "entry_decisions.csv"


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _load_entry_decisions(path: str | Path | None = None) -> pd.DataFrame:
    file_path = Path(path) if path else _default_entry_decisions_csv_path()
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _top_counts(frame: pd.DataFrame, column: str, limit: int = 10) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    counts = (
        frame[column]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(limit)
        .to_dict()
    )
    return {str(key): int(value) for key, value in counts.items()}


def _sort_recent(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    if "time" in frame.columns:
        frame = frame.copy()
        frame["time_sort"] = pd.to_datetime(frame["time"], errors="coerce")
        return frame.sort_values(by=["time_sort"], ascending=[False], kind="stable").head(limit).drop(columns=["time_sort"])
    return frame.tail(limit).copy()


def _cluster_counts(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {}
    counts: Counter[str] = Counter()
    for row in frame.to_dict(orient="records"):
        cluster_key = " | ".join(
            [
                _text(row.get("symbol")).upper(),
                _text(row.get("observe_reason")),
                _text(row.get("blocked_by")),
                _text(row.get("action_none_reason")),
            ]
        )
        if cluster_key.strip(" |"):
            counts[cluster_key] += 1
    return {str(key): int(value) for key, value in counts.most_common(10)}


def build_semantic_baseline_no_action_sample_audit(
    *,
    entry_decisions: pd.DataFrame | None = None,
    recent_limit: int = 200,
    sample_limit: int = 15,
) -> dict[str, Any]:
    frame = entry_decisions.copy() if entry_decisions is not None else _load_entry_decisions()
    recent = _sort_recent(frame, max(1, int(recent_limit)))
    if recent.empty:
        return {
            "summary": {
                "contract_version": SEMANTIC_BASELINE_NO_ACTION_SAMPLE_AUDIT_CONTRACT_VERSION,
                "generated_at": datetime.now().astimezone().isoformat(),
                "recent_row_count": 0,
                "baseline_no_action_count": 0,
                "recommended_next_action": "collect_entry_decision_rows_before_sample_audit",
            },
            "samples": [],
        }

    fallback_col = "semantic_live_fallback_reason"
    filtered = (
        recent.loc[recent[fallback_col].fillna("").astype(str).str.strip() == "baseline_no_action"].copy()
        if fallback_col in recent.columns
        else pd.DataFrame()
    )

    cluster_counts = _cluster_counts(filtered)
    sample_rows: list[dict[str, Any]] = []
    for row in filtered.head(sample_limit).to_dict(orient="records"):
        cluster_key = " | ".join(
            [
                _text(row.get("symbol")),
                _text(row.get("observe_reason")),
                _text(row.get("blocked_by")),
                _text(row.get("action_none_reason")),
            ]
        )
        sample_rows.append(
            {
                "time": _text(row.get("time")),
                "symbol": _text(row.get("symbol")).upper(),
                "action": _text(row.get("action")),
                "observe_reason": _text(row.get("observe_reason")),
                "blocked_by": _text(row.get("blocked_by")),
                "action_none_reason": _text(row.get("action_none_reason")),
                "semantic_shadow_available": _to_int(row.get("semantic_shadow_available")),
                "semantic_shadow_should_enter": _to_int(row.get("semantic_shadow_should_enter")),
                "semantic_shadow_trace_quality": _text(row.get("semantic_shadow_trace_quality")),
                "semantic_shadow_timing_probability": row.get("semantic_shadow_timing_probability"),
                "probe_state": _text(row.get("probe_state")),
                "setup_id": _text(row.get("setup_id")),
                "cluster_key": cluster_key,
            }
        )

    dominant_cluster = ""
    dominant_cluster_count = 0
    if cluster_counts:
        dominant_cluster, dominant_cluster_count = sorted(
            cluster_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]

    recommended_next_action = "inspect dominant baseline_no_action cluster before semantic threshold changes"
    if not sample_rows:
        recommended_next_action = "collect_more_recent baseline_no_action rows"

    return {
        "summary": {
            "contract_version": SEMANTIC_BASELINE_NO_ACTION_SAMPLE_AUDIT_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "recent_row_count": int(len(recent)),
            "baseline_no_action_count": int(len(filtered)),
            "symbol_counts": _top_counts(filtered, "symbol"),
            "observe_reason_counts": _top_counts(filtered, "observe_reason"),
            "blocked_by_counts": _top_counts(filtered, "blocked_by"),
            "action_none_reason_counts": _top_counts(filtered, "action_none_reason"),
            "probe_state_counts": _top_counts(filtered, "probe_state"),
            "semantic_shadow_trace_quality_counts": _top_counts(filtered, "semantic_shadow_trace_quality"),
            "cluster_counts": cluster_counts,
            "dominant_cluster": dominant_cluster,
            "dominant_cluster_count": int(dominant_cluster_count),
            "recommended_next_action": recommended_next_action,
        },
        "samples": sample_rows,
    }


def render_semantic_baseline_no_action_sample_audit_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = dict(payload or {})
    summary = dict(body.get("summary") or {})
    samples = list(body.get("samples", []) or [])
    lines = [
        "# Semantic Baseline No-Action Sample Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- recent_row_count: `{_to_int(summary.get('recent_row_count'))}`",
        f"- baseline_no_action_count: `{_to_int(summary.get('baseline_no_action_count'))}`",
        f"- dominant_cluster: `{_text(summary.get('dominant_cluster'))}`",
        f"- dominant_cluster_count: `{_to_int(summary.get('dominant_cluster_count'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
        f"- symbol_counts: `{json.dumps(summary.get('symbol_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- observe_reason_counts: `{json.dumps(summary.get('observe_reason_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- blocked_by_counts: `{json.dumps(summary.get('blocked_by_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- action_none_reason_counts: `{json.dumps(summary.get('action_none_reason_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- cluster_counts: `{json.dumps(summary.get('cluster_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Samples",
        "",
    ]
    for sample in samples:
        row = dict(sample or {})
        lines.extend(
            [
                f"### {_text(row.get('time'))} / {_text(row.get('symbol'))}",
                "",
                f"- observe_reason: `{_text(row.get('observe_reason'))}`",
                f"- blocked_by: `{_text(row.get('blocked_by'))}`",
                f"- action_none_reason: `{_text(row.get('action_none_reason'))}`",
                f"- semantic_shadow_available: `{_to_int(row.get('semantic_shadow_available'))}`",
                f"- semantic_shadow_should_enter: `{_to_int(row.get('semantic_shadow_should_enter'))}`",
                f"- semantic_shadow_trace_quality: `{_text(row.get('semantic_shadow_trace_quality'))}`",
                f"- probe_state: `{_text(row.get('probe_state'))}`",
                f"- cluster_key: `{_text(row.get('cluster_key'))}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_semantic_baseline_no_action_sample_audit_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    _write_json(
        json_output_path or default_semantic_baseline_no_action_sample_audit_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_semantic_baseline_no_action_sample_audit_markdown_path(),
        render_semantic_baseline_no_action_sample_audit_markdown(payload),
    )
