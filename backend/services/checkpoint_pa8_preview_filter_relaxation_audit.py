from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.services.checkpoint_pa8_post_activation_root_cause_audit import (
    default_checkpoint_pa8_post_activation_root_cause_audit_json_path,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import _symbol_profile


CHECKPOINT_PA8_PREVIEW_FILTER_RELAXATION_AUDIT_CONTRACT_VERSION = (
    "checkpoint_pa8_preview_filter_relaxation_audit_v1"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa8_preview_filter_relaxation_audit_json_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_preview_filter_relaxation_audit_latest.json"


def default_checkpoint_pa8_preview_filter_relaxation_audit_markdown_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_preview_filter_relaxation_audit_latest.md"


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


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


def _profile_scope(symbol: str) -> dict[str, list[str]]:
    symbol_upper = _text(symbol).upper()
    if symbol_upper not in {"BTCUSD", "XAUUSD"}:
        return {}
    profile = _symbol_profile(symbol_upper)
    return {
        "surface_name": [_text(profile.get("surface_name"))],
        "checkpoint_type": [str(item).upper() for item in list(profile.get("checkpoint_type_allowlist") or []) if _text(item)],
        "checkpoint_rule_family_hint": [str(item).lower() for item in list(profile.get("family_allowlist") or []) if _text(item)],
        "baseline_action_label": [str(item).upper() for item in list(profile.get("baseline_action_allowlist") or []) if _text(item)],
        "source": [_text(item) for item in list(profile.get("source_allowlist") or []) if _text(item)],
        "position_side": [str(item).upper() for item in list(profile.get("position_side_allowlist") or []) if _text(item)],
    }


def _sorted_scope_candidates(
    counts: Mapping[str, Any] | None,
    *,
    current_scope: list[str] | None = None,
    normalize: Callable[[str], str] | None = None,
    limit: int = 3,
) -> list[str]:
    current = {str(item) for item in list(current_scope or []) if _text(item)}
    rows = []
    for raw_key, raw_count in _mapping(counts).items():
        key = _text(raw_key)
        if not key:
            continue
        normalized = normalize(key) if normalize else key
        if normalized in current:
            continue
        rows.append((key, _to_int(raw_count)))
    rows.sort(key=lambda item: (-item[1], item[0]))
    return [key for key, _ in rows[:limit]]


RELAXATION_REASON_RULES: dict[str, dict[str, Any]] = {
    "preview_surface_out_of_scope": {
        "candidate_code": "expand_surface_scope_review",
        "candidate_label_ko": "surface 범위 확장 검토",
        "counts_field": "surface_counts",
        "scope_field": "surface_name",
        "normalize": lambda value: value,
        "caution_ko": "surface를 넓혀도 action preview precision은 별도로 다시 확인해야 합니다.",
    },
    "preview_checkpoint_out_of_scope": {
        "candidate_code": "expand_checkpoint_type_review",
        "candidate_label_ko": "checkpoint type 범위 확장 검토",
        "counts_field": "checkpoint_type_counts",
        "scope_field": "checkpoint_type",
        "normalize": lambda value: value.upper(),
        "caution_ko": "checkpoint type 완화는 sample floor보다 먼저 review casebook으로만 확인해야 합니다.",
    },
    "preview_family_out_of_scope": {
        "candidate_code": "expand_family_scope_review",
        "candidate_label_ko": "family 범위 확장 검토",
        "counts_field": "family_counts",
        "scope_field": "checkpoint_rule_family_hint",
        "normalize": lambda value: value.lower(),
        "caution_ko": "family를 넓히면 성격이 다른 장면이 섞일 수 있어 observe-only review가 우선입니다.",
    },
    "preview_baseline_action_out_of_scope": {
        "candidate_code": "expand_baseline_action_review",
        "candidate_label_ko": "baseline action 범위 확장 검토",
        "counts_field": "baseline_action_counts",
        "scope_field": "baseline_action_label",
        "normalize": lambda value: value.upper(),
        "caution_ko": "baseline action allowlist는 candidate precision 저하 가능성이 커서 마지막에 검토하는 편이 안전합니다.",
    },
    "preview_source_out_of_scope": {
        "candidate_code": "expand_source_scope_review",
        "candidate_label_ko": "source 범위 확장 검토",
        "counts_field": "source_counts",
        "scope_field": "source",
        "normalize": lambda value: value,
        "caution_ko": "source 확대는 data provenance가 섞이므로 observe-only canary로만 먼저 봐야 합니다.",
    },
    "preview_position_side_out_of_scope": {
        "candidate_code": "inspect_position_side_scope",
        "candidate_label_ko": "position side 범위 재검토",
        "counts_field": "position_side_counts",
        "scope_field": "position_side",
        "normalize": lambda value: value.upper(),
        "caution_ko": "position side가 바뀌면 preview 의미 자체가 바뀔 수 있어 가장 보수적으로 다뤄야 합니다.",
    },
}


def _build_relaxation_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    row_map = _mapping(row)
    symbol = _text(row_map.get("symbol")).upper()
    if _text(row_map.get("root_cause_code")) != "preview_filter_rejection_dominant":
        return []
    current_scope = _profile_scope(symbol)
    post_activation_row_count = max(1, _to_int(row_map.get("post_activation_row_count"), 0))
    preview_reason_counts = {
        _text(key): _to_int(value)
        for key, value in _mapping(row_map.get("preview_reason_counts")).items()
        if _to_int(value) > 0
    }
    candidates: list[dict[str, Any]] = []
    for reason_code, rejected_row_count in preview_reason_counts.items():
        rule = _mapping(RELAXATION_REASON_RULES.get(reason_code))
        if not rule:
            continue
        scope_field = _text(rule.get("scope_field"))
        counts_field = _text(rule.get("counts_field"))
        current_scope_values = list(current_scope.get(scope_field) or [])
        suggested_scope_values = _sorted_scope_candidates(
            _mapping(row_map.get(counts_field)),
            current_scope=current_scope_values,
            normalize=rule.get("normalize"),
        )
        rejected_share_pct = round((float(rejected_row_count) / float(post_activation_row_count)) * 100.0, 1)
        review_priority_score = round(rejected_share_pct + (5.0 if suggested_scope_values else 0.0), 1)
        candidates.append(
            {
                "candidate_code": _text(rule.get("candidate_code")),
                "candidate_label_ko": _text(rule.get("candidate_label_ko")),
                "reason_code": reason_code,
                "rejected_row_count": rejected_row_count,
                "rejected_share_pct": rejected_share_pct,
                "current_scope_values": current_scope_values,
                "suggested_scope_values": suggested_scope_values,
                "review_priority_score": review_priority_score,
                "why_now_ko": (
                    f"{symbol} 활성화 이후 row {post_activation_row_count}건 중 "
                    f"{rejected_row_count}건({rejected_share_pct}%)이 `{reason_code}`로 걸렸습니다."
                ),
                "caution_ko": _text(rule.get("caution_ko")),
                "recommended_next_action": (
                    "live threshold를 낮추기 전에 이 scope만 action-only preview casebook으로 좁게 재검토합니다."
                ),
            }
        )
    candidates.sort(
        key=lambda item: (
            -_to_float(item.get("review_priority_score"), 0.0),
            -_to_int(item.get("rejected_row_count"), 0),
            _text(item.get("candidate_code")),
        )
    )
    for index, item in enumerate(candidates, start=1):
        item["recommended_review_order"] = index
    return candidates


def build_checkpoint_pa8_preview_filter_relaxation_audit(
    *,
    root_cause_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _mapping(root_cause_payload) or _load_json(
        default_checkpoint_pa8_post_activation_root_cause_audit_json_path()
    )
    source_rows = list(_mapping(payload).get("rows") or [])
    rows: list[dict[str, Any]] = []
    symbols_needing_review: list[str] = []
    candidate_code_counts: dict[str, int] = {}
    for raw_row in source_rows:
        row = _mapping(raw_row)
        symbol = _text(row.get("symbol")).upper()
        candidates = _build_relaxation_candidates(row)
        if candidates:
            symbols_needing_review.append(symbol)
            for item in candidates:
                candidate_code = _text(item.get("candidate_code"))
                if candidate_code:
                    candidate_code_counts[candidate_code] = candidate_code_counts.get(candidate_code, 0) + 1
        rows.append(
            {
                "symbol": symbol,
                "root_cause_code": _text(row.get("root_cause_code")),
                "root_cause_ko": _text(row.get("root_cause_ko")),
                "post_activation_row_count": _to_int(row.get("post_activation_row_count")),
                "preview_changed_row_count": _to_int(row.get("preview_changed_row_count")),
                "recommended_next_action": _text(row.get("recommended_next_action")),
                "current_profile_scope": _profile_scope(symbol),
                "preview_reason_counts": _mapping(row.get("preview_reason_counts")),
                "relaxation_candidates": candidates,
            }
        )

    return {
        "summary": {
            "contract_version": CHECKPOINT_PA8_PREVIEW_FILTER_RELAXATION_AUDIT_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol_count": len(rows),
            "symbols_needing_scope_review": symbols_needing_review,
            "candidate_code_counts": candidate_code_counts,
            "recommended_next_action": (
                "review scope relaxation candidates before changing PA8 thresholds or sample floors"
                if symbols_needing_review
                else "keep current PA8 preview filter and continue collecting live rows"
            ),
        },
        "rows": rows,
    }


def render_checkpoint_pa8_preview_filter_relaxation_audit_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows") or [])
    lines = [
        "# PA8 Preview Filter Relaxation Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- symbols_needing_scope_review: `{json.dumps(summary.get('symbols_needing_scope_review', []), ensure_ascii=False)}`",
        f"- candidate_code_counts: `{json.dumps(summary.get('candidate_code_counts', {}), ensure_ascii=False, sort_keys=True)}`",
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
                f"- root_cause: `{_text(row.get('root_cause_ko'))}`",
                f"- post_activation_row_count: `{_to_int(row.get('post_activation_row_count'))}`",
                f"- preview_changed_row_count: `{_to_int(row.get('preview_changed_row_count'))}`",
                f"- current_profile_scope: `{json.dumps(_mapping(row.get('current_profile_scope')), ensure_ascii=False, sort_keys=True)}`",
                f"- preview_reason_counts: `{json.dumps(_mapping(row.get('preview_reason_counts')), ensure_ascii=False, sort_keys=True)}`",
            ]
        )
        candidates = list(row.get("relaxation_candidates") or [])
        if not candidates:
            lines.extend(["- relaxation_candidates: `[]`", ""])
            continue
        lines.append("- relaxation_candidates:")
        for item in candidates[:5]:
            candidate = _mapping(item)
            lines.append(
                "  - "
                f"{_to_int(candidate.get('recommended_review_order'))}. "
                f"{_text(candidate.get('candidate_label_ko'))} "
                f"(rows={_to_int(candidate.get('rejected_row_count'))}, "
                f"share={_to_float(candidate.get('rejected_share_pct')):.1f}%, "
                f"suggested={json.dumps(candidate.get('suggested_scope_values', []), ensure_ascii=False)})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_pa8_preview_filter_relaxation_audit_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    _write_json(
        json_output_path or default_checkpoint_pa8_preview_filter_relaxation_audit_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_checkpoint_pa8_preview_filter_relaxation_audit_markdown_path(),
        render_checkpoint_pa8_preview_filter_relaxation_audit_markdown(payload),
    )
