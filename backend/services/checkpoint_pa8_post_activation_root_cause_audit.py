from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.path_checkpoint_pa8_action_preview import (
    build_nas100_profit_hold_bias_action_preview,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    build_checkpoint_pa8_symbol_action_preview,
)


CHECKPOINT_PA8_POST_ACTIVATION_ROOT_CAUSE_AUDIT_CONTRACT_VERSION = (
    "checkpoint_pa8_post_activation_root_cause_audit_v1"
)

SYMBOLS = ("NAS100", "BTCUSD", "XAUUSD")

ROOT_CAUSE_LABELS_KO = {
    "no_post_activation_rows": "활성화 이후 checkpoint row 자체가 없음",
    "preview_filter_rejection_dominant": "활성화 이후 row는 있으나 preview 후보 규칙에 거의 걸리지 않음",
    "preview_candidate_available": "활성화 이후 row 중 preview 후보가 실제로 존재함",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa8_post_activation_root_cause_audit_json_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_post_activation_root_cause_audit_latest.json"


def default_checkpoint_pa8_post_activation_root_cause_audit_markdown_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_post_activation_root_cause_audit_latest.md"


def _default_resolved_dataset_path() -> Path:
    return _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"


def _activation_payload_path(symbol: str) -> Path:
    return _shadow_auto_dir() / f"checkpoint_pa8_{symbol.lower()}_action_only_canary_activation_apply_latest.json"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _load_resolved_dataset(path: str | Path | None = None) -> pd.DataFrame:
    file_path = Path(path) if path else _default_resolved_dataset_path()
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _post_activation_subset(
    resolved_dataset: pd.DataFrame,
    *,
    symbol: str,
    activated_at: str,
) -> pd.DataFrame:
    if resolved_dataset.empty or not activated_at:
        return pd.DataFrame()
    frame = resolved_dataset.copy()
    if "symbol" not in frame.columns or "generated_at" not in frame.columns:
        return pd.DataFrame()
    times = pd.to_datetime(frame["generated_at"], errors="coerce")
    threshold = pd.to_datetime(activated_at, errors="coerce")
    if pd.isna(threshold):
        return pd.DataFrame()
    return frame.loc[
        (frame["symbol"].astype(str).str.upper() == symbol.upper()) & (times >= threshold)
    ].copy()


def _top_counts(series: pd.Series, limit: int = 5) -> dict[str, int]:
    counts = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(limit)
        .to_dict()
    )
    return {str(key): int(value) for key, value in counts.items()}


def _preview_for_symbol(symbol: str, subset: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if symbol.upper() == "NAS100":
        return build_nas100_profit_hold_bias_action_preview(subset)
    return build_checkpoint_pa8_symbol_action_preview(subset, symbol=symbol)


def _root_cause_code(post_activation_row_count: int, preview_changed_row_count: int) -> str:
    if post_activation_row_count <= 0:
        return "no_post_activation_rows"
    if preview_changed_row_count <= 0:
        return "preview_filter_rejection_dominant"
    return "preview_candidate_available"


def build_checkpoint_pa8_post_activation_root_cause_audit(
    *,
    resolved_dataset: pd.DataFrame | None = None,
    activation_payloads: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    dataset = resolved_dataset.copy() if resolved_dataset is not None else _load_resolved_dataset()
    rows: list[dict[str, Any]] = []
    cause_counts: Counter[str] = Counter()

    payload_map = {str(key).upper(): _mapping(value) for key, value in _mapping(activation_payloads).items()}
    for symbol in SYMBOLS:
        activation_payload = payload_map.get(symbol) or _load_json(_activation_payload_path(symbol))
        activated_at = _text(_mapping(activation_payload.get("active_state")).get("activated_at"))
        subset = _post_activation_subset(dataset, symbol=symbol, activated_at=activated_at)
        preview_frame, preview_summary = _preview_for_symbol(symbol, subset)
        preview_reason_counts = (
            _top_counts(preview_frame["preview_reason"]) if "preview_reason" in preview_frame.columns else {}
        )
        surface_counts = (
            _top_counts(preview_frame["surface_name"]) if "surface_name" in preview_frame.columns else {}
        )
        family_counts = (
            _top_counts(preview_frame["checkpoint_rule_family_hint"])
            if "checkpoint_rule_family_hint" in preview_frame.columns
            else {}
        )
        checkpoint_type_counts = (
            _top_counts(preview_frame["checkpoint_type"]) if "checkpoint_type" in preview_frame.columns else {}
        )
        baseline_action_counts = (
            _top_counts(preview_frame["baseline_action_label"]) if "baseline_action_label" in preview_frame.columns else {}
        )
        source_counts = (
            _top_counts(preview_frame["source"]) if "source" in preview_frame.columns else {}
        )
        position_side_counts = (
            _top_counts(preview_frame["position_side"]) if "position_side" in preview_frame.columns else {}
        )
        preview_changed_row_count = _to_int(preview_summary.get("preview_changed_row_count"))
        cause_code = _root_cause_code(len(subset), preview_changed_row_count)
        cause_counts[cause_code] += 1
        changed_samples: list[dict[str, Any]] = []
        if not preview_frame.empty and "preview_changed" in preview_frame.columns:
            changed_samples = (
                preview_frame.loc[preview_frame["preview_changed"].astype(bool)]
                .head(5)
                .to_dict(orient="records")
            )
        rows.append(
            {
                "symbol": symbol,
                "activated_at": activated_at,
                "post_activation_row_count": int(len(subset)),
                "preview_changed_row_count": preview_changed_row_count,
                "eligible_row_count": _to_int(preview_summary.get("eligible_row_count")),
                "recommended_next_action": _text(preview_summary.get("recommended_next_action")),
                "root_cause_code": cause_code,
                "root_cause_ko": ROOT_CAUSE_LABELS_KO.get(cause_code, cause_code),
                "preview_reason_counts": preview_reason_counts,
                "surface_counts": surface_counts,
                "family_counts": family_counts,
                "checkpoint_type_counts": checkpoint_type_counts,
                "baseline_action_counts": baseline_action_counts,
                "source_counts": source_counts,
                "position_side_counts": position_side_counts,
                "changed_samples": changed_samples,
            }
        )

    dominant_root_cause = ""
    if cause_counts:
        dominant_root_cause = sorted(
            cause_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]

    return {
        "summary": {
            "contract_version": CHECKPOINT_PA8_POST_ACTIVATION_ROOT_CAUSE_AUDIT_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol_count": len(rows),
            "dominant_root_cause_code": dominant_root_cause,
            "dominant_root_cause_ko": ROOT_CAUSE_LABELS_KO.get(dominant_root_cause, dominant_root_cause),
            "root_cause_counts": dict(cause_counts),
            "recommended_next_action": "inspect_preview_filter_scope_before_lowering_pa8_thresholds"
            if dominant_root_cause == "preview_filter_rejection_dominant"
            else "inspect_post_activation_capture_pipeline",
        },
        "rows": rows,
    }


def render_checkpoint_pa8_post_activation_root_cause_audit_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines = [
        "# PA8 Post-Activation Root Cause Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- dominant_root_cause: `{_text(summary.get('dominant_root_cause_ko'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
        "## Symbol Rows",
        "",
    ]
    for raw_row in rows:
        row = _mapping(raw_row)
        lines.extend(
            [
                f"### {_text(row.get('symbol'))}",
                "",
                f"- activated_at: `{_text(row.get('activated_at'))}`",
                f"- post_activation_row_count: `{_to_int(row.get('post_activation_row_count'))}`",
                f"- preview_changed_row_count: `{_to_int(row.get('preview_changed_row_count'))}`",
                f"- eligible_row_count: `{_to_int(row.get('eligible_row_count'))}`",
                f"- root_cause: `{_text(row.get('root_cause_ko'))}`",
                f"- preview_reason_counts: `{json.dumps(_mapping(row.get('preview_reason_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- surface_counts: `{json.dumps(_mapping(row.get('surface_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- family_counts: `{json.dumps(_mapping(row.get('family_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- checkpoint_type_counts: `{json.dumps(_mapping(row.get('checkpoint_type_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- baseline_action_counts: `{json.dumps(_mapping(row.get('baseline_action_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- source_counts: `{json.dumps(_mapping(row.get('source_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- position_side_counts: `{json.dumps(_mapping(row.get('position_side_counts')), ensure_ascii=False, sort_keys=True)}`",
                f"- recommended_next_action: `{_text(row.get('recommended_next_action'))}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_pa8_post_activation_root_cause_audit_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    _write_json(
        json_output_path or default_checkpoint_pa8_post_activation_root_cause_audit_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_checkpoint_pa8_post_activation_root_cause_audit_markdown_path(),
        render_checkpoint_pa8_post_activation_root_cause_audit_markdown(payload),
    )
