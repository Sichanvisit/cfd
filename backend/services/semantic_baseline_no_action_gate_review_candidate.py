from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.semantic_baseline_no_action_sample_audit import (
    default_semantic_baseline_no_action_sample_audit_json_path,
)


SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_CANDIDATE_VERSION = (
    "semantic_baseline_no_action_gate_review_candidate_v1"
)

SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY = (
    "misread:semantic_gate_review_candidate"
)


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
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def default_semantic_baseline_no_action_gate_review_candidate_json_path() -> Path:
    return _shadow_auto_dir() / "semantic_baseline_no_action_gate_review_candidate_latest.json"


def default_semantic_baseline_no_action_gate_review_candidate_markdown_path() -> Path:
    return _shadow_auto_dir() / "semantic_baseline_no_action_gate_review_candidate_latest.md"


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _dominant_symbol(summary: Mapping[str, Any]) -> str:
    symbol_counts = {
        _text(key).upper(): _to_int(value)
        for key, value in _mapping(_mapping(summary).get("symbol_counts")).items()
        if _text(key)
    }
    if not symbol_counts:
        return "ALL"
    return sorted(symbol_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


REVIEW_RULES: dict[tuple[str, str], dict[str, Any]] = {
    ("blocked_by", "energy_soft_block"): {
        "candidate_code": "review_energy_soft_block_gate",
        "candidate_label_ko": "energy soft block gate 검토",
        "extra_evidence_registry_keys": ["misread:semantic_blocked_by"],
        "recommended_action_ko": "energy soft block가 너무 쉽게 observe 상태를 만들고 있는지 review backlog로 먼저 검토합니다.",
    },
    ("blocked_by", "outer_band_guard"): {
        "candidate_code": "review_outer_band_guard_scope",
        "candidate_label_ko": "outer band guard 범위 검토",
        "extra_evidence_registry_keys": ["misread:semantic_blocked_by"],
        "recommended_action_ko": "outer band guard가 현재 semantic observe를 과도하게 막는지 scope review로 먼저 확인합니다.",
    },
    ("action_none_reason", "execution_soft_blocked"): {
        "candidate_code": "review_execution_soft_block_gate",
        "candidate_label_ko": "execution soft block gate 검토",
        "extra_evidence_registry_keys": ["misread:semantic_action_none_reason"],
        "recommended_action_ko": "execution soft block 기준이 실제 semantic promotion을 너무 늦추는지 review합니다.",
    },
    ("action_none_reason", "probe_not_promoted"): {
        "candidate_code": "review_probe_promotion_gate",
        "candidate_label_ko": "probe promotion gate 검토",
        "extra_evidence_registry_keys": ["misread:semantic_action_none_reason"],
        "recommended_action_ko": "probe가 promotion 단계로 못 올라가는 이유를 semantic observe cluster와 함께 review합니다.",
    },
    ("semantic_shadow_trace_quality", "unavailable"): {
        "candidate_code": "review_trace_availability_lane",
        "candidate_label_ko": "semantic trace availability 검토",
        "extra_evidence_registry_keys": ["misread:semantic_shadow_trace_quality"],
        "recommended_action_ko": "semantic trace availability 자체가 gate를 막는지 먼저 확인합니다.",
    },
}


def _review_priority_score(*, count: int, share: float, cluster_count: int) -> float:
    score = min(60.0, float(count) * 2.0)
    score += min(25.0, share * 50.0)
    score += min(15.0, float(cluster_count) / 3.0)
    return round(score, 1)


def build_semantic_baseline_no_action_gate_review_candidates(
    *,
    sample_audit_payload: Mapping[str, Any] | None = None,
    minimum_count: int = 5,
    minimum_share: float = 0.20,
) -> list[dict[str, Any]]:
    payload = _mapping(sample_audit_payload) or _load_json(
        default_semantic_baseline_no_action_sample_audit_json_path()
    )
    summary = _mapping(payload.get("summary"))
    baseline_no_action_count = max(1, _to_int(summary.get("baseline_no_action_count"), 0))
    dominant_cluster = _text(summary.get("dominant_cluster"))
    dominant_cluster_count = _to_int(summary.get("dominant_cluster_count"), 0)
    symbol = _dominant_symbol(summary)

    counts_by_dimension = {
        "blocked_by": _mapping(summary.get("blocked_by_counts")),
        "action_none_reason": _mapping(summary.get("action_none_reason_counts")),
        "semantic_shadow_trace_quality": _mapping(summary.get("semantic_shadow_trace_quality_counts")),
    }

    rows: list[dict[str, Any]] = []
    for (dimension, value), rule in REVIEW_RULES.items():
        count = _to_int(_mapping(counts_by_dimension.get(dimension)).get(value), 0)
        share = float(count) / float(max(1, baseline_no_action_count))
        if count < int(minimum_count):
            continue
        if share < float(minimum_share):
            continue
        priority_score = _review_priority_score(
            count=count,
            share=share,
            cluster_count=dominant_cluster_count,
        )
        misread_confidence = round(min(0.92, 0.40 + share * 0.35 + min(0.17, count / 100.0)), 2)
        evidence_keys = [
            SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY,
            *list(rule.get("extra_evidence_registry_keys") or []),
        ]
        rows.append(
            {
                "contract_version": SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_CANDIDATE_VERSION,
                "candidate_code": _text(rule.get("candidate_code")),
                "candidate_label_ko": _text(rule.get("candidate_label_ko")),
                "symbol_scope": symbol,
                "dimension": dimension,
                "dimension_value": value,
                "baseline_no_action_count": baseline_no_action_count,
                "gate_count": count,
                "gate_share": round(share, 4),
                "dominant_cluster": dominant_cluster,
                "dominant_cluster_count": dominant_cluster_count,
                "summary_ko": f"{symbol} semantic gate review 후보",
                "why_now_ko": (
                    f"최근 baseline_no_action {baseline_no_action_count}건 중 "
                    f"`{dimension}={value}`가 {count}건({share * 100.0:.1f}%)으로 반복됩니다."
                ),
                "recommended_action_ko": _text(rule.get("recommended_action_ko")),
                "evidence_lines_ko": [
                    f"- dimension: {dimension}",
                    f"- dimension_value: {value}",
                    f"- gate_count: {count}",
                    f"- dominant_cluster: {dominant_cluster or '-'}",
                ],
                "registry_key": SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY,
                "primary_registry_key_override": SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY,
                "extra_evidence_registry_keys": evidence_keys,
                "result_type": "result_unresolved",
                "explanation_type": "explanation_gap",
                "misread_confidence": misread_confidence,
                "priority_score": priority_score,
            }
        )

    rows.sort(
        key=lambda row: (
            -_to_float(row.get("priority_score"), 0.0),
            -_to_int(row.get("gate_count"), 0),
            _text(row.get("candidate_code")),
        )
    )
    return rows


def render_semantic_baseline_no_action_gate_review_candidate_markdown(
    rows: list[Mapping[str, Any]] | None,
) -> str:
    items = list(rows or [])
    lines = [
        "# Semantic Baseline No-Action Gate Review Candidates",
        "",
        f"- candidate_count: `{len(items)}`",
        "",
    ]
    for row in items:
        lines.extend(
            [
                f"## {_text(row.get('candidate_label_ko'))}",
                "",
                f"- summary: `{_text(row.get('summary_ko'))}`",
                f"- why_now: `{_text(row.get('why_now_ko'))}`",
                f"- recommended_action: `{_text(row.get('recommended_action_ko'))}`",
                f"- gate_count: `{_to_int(row.get('gate_count'))}`",
                f"- gate_share: `{_to_float(row.get('gate_share')):.4f}`",
                f"- dominant_cluster: `{_text(row.get('dominant_cluster'))}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_semantic_baseline_no_action_gate_review_candidate_outputs(
    rows: list[Mapping[str, Any]],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    payload = {
        "summary": {
            "contract_version": SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_CANDIDATE_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "candidate_count": len(rows),
        },
        "rows": list(rows),
    }
    _write_json(
        json_output_path or default_semantic_baseline_no_action_gate_review_candidate_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_semantic_baseline_no_action_gate_review_candidate_markdown_path(),
        render_semantic_baseline_no_action_gate_review_candidate_markdown(rows),
    )
