from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.path_checkpoint_pa7_review_processor import (
    default_checkpoint_pa7_review_processor_path,
)


CHECKPOINT_IMPROVEMENT_PA7_NARROW_REVIEW_RUNTIME_CONTRACT_VERSION = (
    "checkpoint_improvement_pa7_narrow_review_runtime_v0"
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_improvement_pa7_narrow_review_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "checkpoint_improvement_pa7_narrow_review_latest.json",
        directory / "checkpoint_improvement_pa7_narrow_review_latest.md",
    )


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _lane_label_ko(disposition: str) -> str:
    if disposition == "mixed_wait_boundary_review":
        return "WAIT 경계 혼합 review"
    if disposition == "mixed_review":
        return "일반 혼합 review"
    return disposition or "-"


def _lane_reason_ko(row: Mapping[str, Any]) -> str:
    disposition = _text(row.get("review_disposition"))
    checkpoint_type = _text(row.get("checkpoint_type")).upper()
    baseline = _text(row.get("resolved_baseline_action_label")).upper()
    hindsight = _text(row.get("hindsight_best_management_action_label")).upper()
    if disposition == "mixed_wait_boundary_review":
        return (
            f"{checkpoint_type}에서 baseline={baseline} / hindsight={hindsight}가 WAIT 경계에서 갈려 "
            "first closeout 전에 좁게 다시 볼 가치가 있습니다."
        )
    return (
        f"{checkpoint_type}에서 baseline/hindsight 정렬이 완전히 닫히지 않아 "
        "mixed review watchlist로 계속 추적하는 편이 좋습니다."
    )


def _review_lens_ko(row: Mapping[str, Any]) -> str:
    disposition = _text(row.get("review_disposition"))
    if disposition == "mixed_wait_boundary_review":
        return "HOLD vs WAIT 경계, near-flat 손실, active_open_loss 재검토"
    return "FIRST_PULLBACK / PARTIAL_EXIT / WAIT 정렬 재검토"


def _severity_score(row: Mapping[str, Any]) -> float:
    disposition = _text(row.get("review_disposition"))
    row_count = _to_float(row.get("row_count"))
    avg_abs_profit = _to_float(row.get("avg_abs_current_profit"))
    base = 70.0 if disposition == "mixed_wait_boundary_review" else 50.0
    return round(base + row_count * 2.0 + avg_abs_profit * 10.0, 2)


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    rows = list(payload.get("rows", []) or [])
    lines = [
        "# Checkpoint Improvement PA7 Narrow Review",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "trigger_state",
        "status",
        "group_count",
        "mixed_wait_boundary_group_count",
        "mixed_review_group_count",
        "primary_symbol",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.extend(["", "## Rows", ""])
    for row in rows:
        row_map = _mapping(row)
        lines.extend(
            [
                f"- `{_text(row_map.get('symbol'))}` | {_text(row_map.get('lane_label_ko'))}",
                f"  key: `{_text(row_map.get('group_key'))}`",
                f"  severity_score: `{row_map.get('severity_score')}`",
                f"  lens: {_text(row_map.get('review_lens_ko'))}",
                f"  why: {_text(row_map.get('why_ko'))}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def build_checkpoint_improvement_pa7_narrow_review_runtime(
    *,
    master_board_payload: Mapping[str, Any] | None = None,
    pa7_review_processor_payload: Mapping[str, Any] | None = None,
    pa7_review_processor_path: str | Path | None = None,
    now_ts: object | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    json_path, markdown_path = default_checkpoint_improvement_pa7_narrow_review_paths()
    resolved_json_path = Path(output_json_path or json_path)
    resolved_markdown_path = Path(output_markdown_path or markdown_path)

    board = _mapping(master_board_payload)
    readiness_state = _mapping(board.get("readiness_state"))
    narrow_surface = _mapping(readiness_state.get("pa7_narrow_review_surface"))
    processor_payload = _mapping(
        pa7_review_processor_payload
        if pa7_review_processor_payload is not None
        else _load_json(pa7_review_processor_path or default_checkpoint_pa7_review_processor_path())
    )
    group_rows = list(processor_payload.get("group_rows", []) or [])

    rows: list[dict[str, Any]] = []
    for raw_row in group_rows:
        row = _mapping(raw_row)
        disposition = _text(row.get("review_disposition"))
        if disposition not in {"mixed_wait_boundary_review", "mixed_review"}:
            continue
        rows.append(
            {
                "group_key": _text(row.get("group_key")),
                "symbol": _text(row.get("symbol")).upper(),
                "surface_name": _text(row.get("surface_name")),
                "checkpoint_type": _text(row.get("checkpoint_type")).upper(),
                "review_disposition": disposition,
                "lane_label_ko": _lane_label_ko(disposition),
                "row_count": _to_int(row.get("row_count")),
                "avg_abs_current_profit": round(_to_float(row.get("avg_abs_current_profit")), 4),
                "avg_giveback_ratio": round(_to_float(row.get("avg_giveback_ratio")), 4),
                "resolved_baseline_action_label": _text(row.get("resolved_baseline_action_label")).upper(),
                "policy_replay_action_label": _text(row.get("policy_replay_action_label")).upper(),
                "hindsight_best_management_action_label": _text(row.get("hindsight_best_management_action_label")).upper(),
                "review_priority": _text(row.get("review_priority")),
                "review_reason": _text(row.get("review_reason")),
                "severity_score": _severity_score(row),
                "why_ko": _lane_reason_ko(row),
                "review_lens_ko": _review_lens_ko(row),
            }
        )
    rows.sort(key=lambda row: (row["severity_score"], row["row_count"]), reverse=True)

    summary = {
        "contract_version": CHECKPOINT_IMPROVEMENT_PA7_NARROW_REVIEW_RUNTIME_CONTRACT_VERSION,
        "generated_at": _text(now_ts, _now_iso()),
        "trigger_state": "PA7_NARROW_REVIEW_ANALYZED" if rows else "PA7_NARROW_REVIEW_CLEAR",
        "status": _text(narrow_surface.get("status"), "NOT_APPLICABLE"),
        "group_count": len(rows),
        "mixed_wait_boundary_group_count": sum(1 for row in rows if row["review_disposition"] == "mixed_wait_boundary_review"),
        "mixed_review_group_count": sum(1 for row in rows if row["review_disposition"] == "mixed_review"),
        "primary_group_key": _text(rows[0]["group_key"] if rows else narrow_surface.get("primary_group_key")),
        "primary_symbol": _text(rows[0]["symbol"] if rows else narrow_surface.get("primary_symbol")),
        "recommended_next_action": _text(
            narrow_surface.get("recommended_next_action")
            or processor_payload.get("summary", {}).get("recommended_next_action")
            or "continue_first_symbol_closeout_observation"
        ),
    }
    payload = {
        "summary": summary,
        "rows": rows[:5],
    }
    _write_json(resolved_json_path, payload)
    _write_text(resolved_markdown_path, _render_markdown(payload))
    return payload
