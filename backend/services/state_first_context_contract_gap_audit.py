from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.services.trade_csv_schema import now_kst_dt


STATE_FIRST_CONTEXT_CONTRACT_GAP_AUDIT_CONTRACT_VERSION = "state_first_context_contract_gap_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _default_runtime_status_detail_path() -> Path:
    return _repo_root() / "data" / "runtime_status.detail.json"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore")


def _load_runtime_status_detail_payload(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else _default_runtime_status_detail_path()
    if not target.exists():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_source_text_by_relpath(relpaths: Sequence[str] | None = None) -> dict[str, str]:
    repo_root = _repo_root()
    selected = list(relpaths or _SOURCE_REL_PATHS)
    loaded: dict[str, str] = {}
    for relpath in selected:
        path = repo_root / relpath
        loaded[relpath] = _read_text(path) if path.exists() else ""
    return loaded


def _collect_latest_signal_rows(runtime_status_payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    payload = dict(runtime_status_payload or {})
    latest = payload.get("latest_signal_by_symbol")
    if not isinstance(latest, Mapping):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for symbol, row in latest.items():
        if isinstance(row, Mapping):
            rows[str(symbol)] = dict(row)
    return rows


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _count_direct_field_presence(rows: Mapping[str, Mapping[str, Any]], field: str) -> tuple[int, int, list[str]]:
    declared = 0
    present = 0
    examples: list[str] = []
    for symbol, row in rows.items():
        if field in row:
            declared += 1
            if _nonempty(row.get(field)):
                present += 1
                examples.append(str(symbol))
    return declared, present, examples


def _count_related_proxy_presence(
    rows: Mapping[str, Mapping[str, Any]], proxy_fields: Sequence[str]
) -> tuple[int, list[str], list[str]]:
    present = 0
    symbol_examples: list[str] = []
    matched_fields: list[str] = []
    for symbol, row in rows.items():
        row_matches = [field for field in proxy_fields if _nonempty(row.get(field))]
        if row_matches:
            present += 1
            symbol_examples.append(str(symbol))
            for field in row_matches:
                if field not in matched_fields:
                    matched_fields.append(field)
    return present, symbol_examples, matched_fields


def _match_source_tokens(
    source_text_by_relpath: Mapping[str, str],
    source_refs: Sequence[Mapping[str, Any]],
) -> tuple[int, list[str], list[str]]:
    matched_files: list[str] = []
    matched_tokens: list[str] = []
    for ref in source_refs:
        relpath = str(ref.get("file") or "").strip()
        tokens = list(ref.get("tokens") or [])
        text = str(source_text_by_relpath.get(relpath, "") or "")
        file_matched = False
        for token in tokens:
            token_text = str(token or "").strip()
            if token_text and token_text in text:
                if token_text not in matched_tokens:
                    matched_tokens.append(token_text)
                file_matched = True
        if file_matched and relpath and relpath not in matched_files:
            matched_files.append(relpath)
    return len(matched_tokens), matched_files, matched_tokens


def _state_rank(state: str) -> int:
    return {
        "DIRECT_PRESENT": 0,
        "DECLARED_BUT_EMPTY": 1,
        "ALREADY_COMPUTED_BUT_NOT_PROMOTED": 2,
        "NOT_COMPUTED_YET": 3,
    }.get(str(state).upper(), 9)


def _recommended_next_step(group_counts: Mapping[str, Mapping[str, int]]) -> str:
    htf_missing = int(group_counts.get("HTF", {}).get("gap_like_count", 0))
    previous_box_missing = int(group_counts.get("PREVIOUS_BOX", {}).get("gap_like_count", 0))
    conflict_missing = int(group_counts.get("CONFLICT", {}).get("gap_like_count", 0))
    share_missing = int(group_counts.get("SHARE", {}).get("gap_like_count", 0))
    if htf_missing > 0:
        return "start_ST1_htf_cache_first"
    if previous_box_missing > 0:
        return "start_ST2_previous_box_calculator"
    if conflict_missing > 0:
        return "start_ST3_context_state_builder"
    if share_missing > 0:
        return "start_ST6_share_state"
    return "ready_for_state_bridge"


def _field_catalog() -> list[dict[str, Any]]:
    htf_sources = [
        {
            "file": "backend/app/trading_application.py",
            "tokens": [
                "TIMEFRAME_H1",
                "TIMEFRAME_H4",
                "TIMEFRAME_D1",
                "copy_rates_from_pos",
                "mtf_ma_big_map_v1",
                "mtf_trendline_map_v1",
            ],
        },
        {
            "file": "backend/services/mt5_snapshot_service.py",
            "tokens": ["TIMEFRAME_H1", "TIMEFRAME_D1", "copy_rates_from_pos"],
        },
    ]
    previous_box_sources = [
        {
            "file": "backend/services/context_classifier.py",
            "tokens": [
                "box_low",
                "box_high",
                "session_position",
                "session_expansion_progress",
            ],
        },
        {
            "file": "backend/app/trading_application.py",
            "tokens": [
                "swing_high_retest_count_20",
                "swing_low_retest_count_20",
                "box_state",
            ],
        },
    ]
    share_sources = [
        {
            "file": "backend/services/semantic_baseline_no_action_cluster_candidate.py",
            "tokens": ["cluster_share", "cluster_symbol_share"],
        },
        {
            "file": "backend/services/trade_feedback_runtime.py",
            "tokens": ["semantic_cluster_candidate_count", "cluster_share"],
        },
    ]
    conflict_runtime_proxy = [
        "active_action_conflict_detected",
        "active_action_conflict_directional_state",
        "active_action_conflict_reason_summary",
        "active_action_conflict_resolution_state",
        "active_action_conflict_warning_count",
    ]
    late_chase_runtime_proxy = [
        "box_state",
        "checkpoint_bars_since_leg_start",
        "checkpoint_index_in_leg",
        "checkpoint_surface_name",
        "checkpoint_runtime_continuation_odds",
        "checkpoint_runtime_reversal_odds",
    ]
    catalog: list[dict[str, Any]] = [
        {
            "context_group": "HTF",
            "state_layer": "raw",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": ["mtf_ma_big_map_v1", "mtf_trendline_map_v1", "mtf_trendline_bar_map_v1"],
            "source_refs": htf_sources,
            "recommended_next_action": "promote_via_ST1_htf_cache",
            "notes_ko": "상위 시간축 방향/강도 raw 필드",
        }
        for field in [
            "trend_15m_direction",
            "trend_1h_direction",
            "trend_4h_direction",
            "trend_1d_direction",
            "trend_15m_strength",
            "trend_1h_strength",
            "trend_4h_strength",
            "trend_1d_strength",
            "trend_15m_strength_score",
            "trend_1h_strength_score",
            "trend_4h_strength_score",
            "trend_1d_strength_score",
        ]
    ]
    catalog += [
        {
            "context_group": "HTF",
            "state_layer": "interpreted",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": ["mtf_ma_big_map_v1", "mtf_trendline_map_v1", *conflict_runtime_proxy],
            "source_refs": htf_sources,
            "recommended_next_action": "build_in_ST3_context_state_builder",
            "notes_ko": "상위 추세 해석 필드",
        }
        for field in [
            "htf_alignment_state",
            "htf_alignment_detail",
            "htf_against_severity",
            "trend_1h_quality",
            "trend_4h_quality",
            "trend_1d_quality",
        ]
    ]
    catalog += [
        {
            "context_group": "HTF",
            "state_layer": "meta",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": [],
            "source_refs": [],
            "recommended_next_action": "add_meta_in_ST3_context_state_builder",
            "notes_ko": "상위 추세 버전/메타 필드",
        }
        for field in ["htf_context_version"]
    ]
    catalog += [
        {
            "context_group": "PREVIOUS_BOX",
            "state_layer": "raw",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": [
                "box_state",
                "position_in_session_box",
                "session_expansion_progress",
                "session_position_bias",
                "micro_swing_high_retest_count_20",
                "micro_swing_low_retest_count_20",
            ],
            "source_refs": previous_box_sources,
            "recommended_next_action": "promote_via_ST2_previous_box_calculator",
            "notes_ko": "직전 박스 raw 필드",
        }
        for field in [
            "previous_box_high",
            "previous_box_low",
            "previous_box_mid",
            "previous_box_mode",
            "previous_box_confidence",
            "previous_box_lifecycle",
            "previous_box_is_consolidation",
            "distance_from_previous_box_high_pct",
            "distance_from_previous_box_low_pct",
        ]
    ]
    catalog += [
        {
            "context_group": "PREVIOUS_BOX",
            "state_layer": "interpreted",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": [
                "box_state",
                "position_in_session_box",
                "session_expansion_progress",
            ],
            "source_refs": previous_box_sources,
            "recommended_next_action": "build_in_ST3_context_state_builder",
            "notes_ko": "직전 박스 해석 필드",
        }
        for field in ["previous_box_relation", "previous_box_break_state"]
    ]
    catalog += [
        {
            "context_group": "PREVIOUS_BOX",
            "state_layer": "meta",
            "target_field": "previous_box_context_version",
            "direct_runtime_fields": ["previous_box_context_version"],
            "related_proxy_fields": [],
            "source_refs": [],
            "recommended_next_action": "add_meta_in_ST3_context_state_builder",
            "notes_ko": "직전 박스 version meta",
        }
    ]
    catalog += [
        {
            "context_group": "SHARE",
            "state_layer": "raw" if "band" not in field and "label" not in field else "interpreted",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": [],
            "source_refs": share_sources,
            "recommended_next_action": "promote_via_ST6_share_state",
            "notes_ko": "semantic cluster share 관련 필드",
        }
        for field in [
            "cluster_share_global",
            "cluster_share_symbol",
            "cluster_share_symbol_band",
            "share_context_label_ko",
        ]
    ]
    catalog += [
        {
            "context_group": "CONFLICT",
            "state_layer": "interpreted",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": conflict_runtime_proxy,
            "source_refs": [],
            "recommended_next_action": "build_in_ST3_context_state_builder",
            "notes_ko": "맥락 충돌 해석 필드",
        }
        for field in [
            "context_conflict_state",
            "context_conflict_flags",
            "context_conflict_intensity",
            "context_conflict_score",
            "context_conflict_label_ko",
        ]
    ]
    catalog += [
        {
            "context_group": "CONFLICT",
            "state_layer": "interpreted",
            "target_field": field,
            "direct_runtime_fields": [field],
            "related_proxy_fields": late_chase_runtime_proxy,
            "source_refs": [],
            "recommended_next_action": "build_in_ST3_context_state_builder",
            "notes_ko": "late chase risk 해석/메타 필드",
        }
        for field in [
            "late_chase_risk_state",
            "late_chase_reason",
            "late_chase_confidence",
            "late_chase_trigger_count",
        ]
    ]
    catalog += [
        {
            "context_group": "CONFLICT",
            "state_layer": "meta",
            "target_field": "conflict_context_version",
            "direct_runtime_fields": ["conflict_context_version"],
            "related_proxy_fields": [],
            "source_refs": [],
            "recommended_next_action": "add_meta_in_ST3_context_state_builder",
            "notes_ko": "conflict context version meta",
        },
        {
            "context_group": "META",
            "state_layer": "meta",
            "target_field": "context_state_version",
            "direct_runtime_fields": ["context_state_version"],
            "related_proxy_fields": [],
            "source_refs": [],
            "recommended_next_action": "add_meta_in_ST3_context_state_builder",
            "notes_ko": "전체 context state version meta",
        },
    ]
    return catalog


_SOURCE_REL_PATHS = [
    "backend/app/trading_application.py",
    "backend/services/context_classifier.py",
    "backend/services/mt5_snapshot_service.py",
    "backend/services/semantic_baseline_no_action_cluster_candidate.py",
    "backend/services/trade_feedback_runtime.py",
]


def build_state_first_context_contract_gap_audit(
    runtime_status_payload: Mapping[str, Any] | None = None,
    *,
    source_text_by_relpath: Mapping[str, str] | None = None,
    field_catalog: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    generated_at = now_kst_dt().isoformat()
    runtime_payload = dict(runtime_status_payload or _load_runtime_status_detail_payload())
    latest_rows = _collect_latest_signal_rows(runtime_payload)
    source_map = dict(source_text_by_relpath or _load_source_text_by_relpath())
    catalog = list(field_catalog or _field_catalog())

    field_rows: list[dict[str, Any]] = []
    for item in catalog:
        target_field = str(item.get("target_field") or "").strip()
        direct_fields = [str(v) for v in list(item.get("direct_runtime_fields") or []) if str(v).strip()]
        proxy_fields = [str(v) for v in list(item.get("related_proxy_fields") or []) if str(v).strip()]
        source_refs = list(item.get("source_refs") or [])

        direct_declared = 0
        direct_present = 0
        direct_symbols: list[str] = []
        matched_direct_fields: list[str] = []
        for field in direct_fields:
            declared_count, present_count, symbols = _count_direct_field_presence(latest_rows, field)
            if declared_count > 0:
                direct_declared += declared_count
                matched_direct_fields.append(field)
            if present_count > 0:
                direct_present += present_count
                for symbol in symbols:
                    if symbol not in direct_symbols:
                        direct_symbols.append(symbol)

        proxy_present, proxy_symbols, matched_proxy_fields = _count_related_proxy_presence(latest_rows, proxy_fields)
        source_token_match_count, matched_source_files, matched_source_tokens = _match_source_tokens(source_map, source_refs)

        if direct_present > 0:
            audit_state = "DIRECT_PRESENT"
            evidence_level = "DIRECT_FIELD"
        elif direct_declared > 0:
            audit_state = "DECLARED_BUT_EMPTY"
            evidence_level = "DIRECT_DECLARED_EMPTY"
        elif proxy_present > 0:
            audit_state = "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
            evidence_level = "RUNTIME_RELATED_PROXY"
        elif source_token_match_count > 0:
            audit_state = "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
            evidence_level = "SOURCE_TOKEN_ONLY"
        else:
            audit_state = "NOT_COMPUTED_YET"
            evidence_level = "NONE"

        field_rows.append(
            {
                "context_group": str(item.get("context_group") or ""),
                "state_layer": str(item.get("state_layer") or ""),
                "target_field": target_field,
                "audit_state": audit_state,
                "proxy_evidence_level": evidence_level,
                "runtime_direct_declared_count": int(direct_declared),
                "runtime_direct_present_count": int(direct_present),
                "runtime_direct_symbol_examples": list(direct_symbols),
                "runtime_related_proxy_count": int(proxy_present),
                "runtime_related_proxy_symbol_examples": list(proxy_symbols),
                "matched_direct_fields": matched_direct_fields,
                "matched_runtime_proxy_fields": matched_proxy_fields,
                "source_token_match_count": int(source_token_match_count),
                "matched_source_files": matched_source_files,
                "matched_source_tokens": matched_source_tokens,
                "recommended_next_action": str(item.get("recommended_next_action") or ""),
                "notes_ko": str(item.get("notes_ko") or ""),
            }
        )

    ordered_rows = sorted(
        field_rows,
        key=lambda row: (
            {"HTF": 0, "PREVIOUS_BOX": 1, "CONFLICT": 2, "SHARE": 3, "META": 4}.get(str(row.get("context_group")), 9),
            _state_rank(str(row.get("audit_state"))),
            str(row.get("target_field")),
        ),
    )

    group_summary: list[dict[str, Any]] = []
    group_counts: dict[str, dict[str, int]] = {}
    for group in ["HTF", "PREVIOUS_BOX", "CONFLICT", "SHARE", "META"]:
        rows = [row for row in ordered_rows if row.get("context_group") == group]
        if not rows:
            continue
        counts = {
            "field_count": len(rows),
            "direct_present_count": sum(1 for row in rows if row.get("audit_state") == "DIRECT_PRESENT"),
            "declared_but_empty_count": sum(1 for row in rows if row.get("audit_state") == "DECLARED_BUT_EMPTY"),
            "already_computed_but_not_promoted_count": sum(
                1 for row in rows if row.get("audit_state") == "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
            ),
            "not_computed_yet_count": sum(1 for row in rows if row.get("audit_state") == "NOT_COMPUTED_YET"),
        }
        counts["gap_like_count"] = int(
            counts["declared_but_empty_count"]
            + counts["already_computed_but_not_promoted_count"]
            + counts["not_computed_yet_count"]
        )
        group_counts[group] = counts
        group_summary.append(
            {
                "context_group": group,
                **counts,
            }
        )

    summary = {
        "contract_version": STATE_FIRST_CONTEXT_CONTRACT_GAP_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": str(runtime_payload.get("updated_at") or ""),
        "latest_signal_symbol_count": int(len(latest_rows)),
        "target_field_count": int(len(ordered_rows)),
        "direct_present_count": int(sum(1 for row in ordered_rows if row.get("audit_state") == "DIRECT_PRESENT")),
        "declared_but_empty_count": int(sum(1 for row in ordered_rows if row.get("audit_state") == "DECLARED_BUT_EMPTY")),
        "already_computed_but_not_promoted_count": int(
            sum(1 for row in ordered_rows if row.get("audit_state") == "ALREADY_COMPUTED_BUT_NOT_PROMOTED")
        ),
        "not_computed_yet_count": int(sum(1 for row in ordered_rows if row.get("audit_state") == "NOT_COMPUTED_YET")),
        "recommended_next_step": _recommended_next_step(group_counts),
    }

    return {
        "contract_version": STATE_FIRST_CONTEXT_CONTRACT_GAP_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": str(runtime_payload.get("updated_at") or ""),
        "latest_signal_symbol_count": int(len(latest_rows)),
        "summary": summary,
        "group_summary": group_summary,
        "field_rows": ordered_rows,
        "already_computed_but_not_promoted": [
            row for row in ordered_rows if row.get("audit_state") == "ALREADY_COMPUTED_BUT_NOT_PROMOTED"
        ],
        "not_computed_yet": [row for row in ordered_rows if row.get("audit_state") == "NOT_COMPUTED_YET"],
        "direct_present": [row for row in ordered_rows if row.get("audit_state") == "DIRECT_PRESENT"],
    }


def render_state_first_context_contract_gap_audit_markdown(payload: Mapping[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    group_summary = list(payload.get("group_summary") or [])
    top_gap_rows = list(payload.get("already_computed_but_not_promoted") or [])[:12]
    not_computed_rows = list(payload.get("not_computed_yet") or [])[:12]

    lines = [
        "# ST0 Current State Audit",
        "",
        f"- generated_at: {summary.get('generated_at', payload.get('generated_at', ''))}",
        f"- runtime_updated_at: {summary.get('runtime_updated_at', payload.get('runtime_updated_at', ''))}",
        f"- latest_signal_symbol_count: {summary.get('latest_signal_symbol_count', payload.get('latest_signal_symbol_count', 0))}",
        f"- target_field_count: {summary.get('target_field_count', 0)}",
        f"- direct_present_count: {summary.get('direct_present_count', 0)}",
        f"- declared_but_empty_count: {summary.get('declared_but_empty_count', 0)}",
        f"- already_computed_but_not_promoted_count: {summary.get('already_computed_but_not_promoted_count', 0)}",
        f"- not_computed_yet_count: {summary.get('not_computed_yet_count', 0)}",
        f"- recommended_next_step: {summary.get('recommended_next_step', '')}",
        "",
        "## Group Summary",
        "",
    ]
    for row in group_summary:
        lines.append(
            f"- {row.get('context_group')}: direct {row.get('direct_present_count')} / "
            f"computed-not-promoted {row.get('already_computed_but_not_promoted_count')} / "
            f"not-computed {row.get('not_computed_yet_count')}"
        )
    lines.extend(["", "## Already Computed But Not Promoted", ""])
    for row in top_gap_rows:
        lines.append(
            f"- {row.get('context_group')} | {row.get('target_field')} | "
            f"{row.get('proxy_evidence_level')} | next={row.get('recommended_next_action')}"
        )
    lines.extend(["", "## Not Computed Yet", ""])
    for row in not_computed_rows:
        lines.append(
            f"- {row.get('context_group')} | {row.get('target_field')} | next={row.get('recommended_next_action')}"
        )
    return "\n".join(lines).strip() + "\n"


def write_state_first_context_contract_gap_audit(
    runtime_status_payload: Mapping[str, Any] | None = None,
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    source_text_by_relpath: Mapping[str, str] | None = None,
    field_catalog: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = build_state_first_context_contract_gap_audit(
        runtime_status_payload,
        source_text_by_relpath=source_text_by_relpath,
        field_catalog=field_catalog,
    )
    target_json = Path(json_path) if json_path is not None else _shadow_auto_dir() / "state_first_context_contract_gap_audit_latest.json"
    target_md = Path(markdown_path) if markdown_path is not None else _shadow_auto_dir() / "state_first_context_contract_gap_audit_latest.md"
    target_json.parent.mkdir(parents=True, exist_ok=True)
    target_md.parent.mkdir(parents=True, exist_ok=True)
    target_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    target_md.write_text(render_state_first_context_contract_gap_audit_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    write_state_first_context_contract_gap_audit()
