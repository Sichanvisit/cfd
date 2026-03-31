from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_ROOT = DATA_DIR / "manifests"


@dataclass(frozen=True)
class ActiveFilePolicy:
    path: str
    tier: str
    owner: str
    warning_bytes: int
    critical_bytes: int
    notes: str = ""


ACTIVE_FILE_POLICIES = [
    ActiveFilePolicy(
        path="trades/entry_decisions.csv",
        tier="hot",
        owner="entry_engine",
        warning_bytes=512 * 1024 * 1024,
        critical_bytes=1024 * 1024 * 1024,
        notes="Primary live append source. Must be rolled before multi-GB growth.",
    ),
    ActiveFilePolicy(
        path="trades/entry_decisions.detail.jsonl",
        tier="hot",
        owner="entry_engine_detail_sidecar",
        warning_bytes=128 * 1024 * 1024,
        critical_bytes=256 * 1024 * 1024,
        notes="Active forensic sidecar. Should rotate into compressed shards before multi-GB growth.",
    ),
    ActiveFilePolicy(
        path="trades/trade_history.csv",
        tier="hot",
        owner="trade_logger",
        warning_bytes=64 * 1024 * 1024,
        critical_bytes=256 * 1024 * 1024,
        notes="Open-trade append log backed by SQLite mirror.",
    ),
    ActiveFilePolicy(
        path="trades/trade_closed_history.csv",
        tier="hot",
        owner="trade_logger",
        warning_bytes=128 * 1024 * 1024,
        critical_bytes=512 * 1024 * 1024,
        notes="Closed-trade log used by current ML and offline validation.",
    ),
    ActiveFilePolicy(
        path="trades/trade_shock_events.csv",
        tier="hot",
        owner="trade_logger",
        warning_bytes=32 * 1024 * 1024,
        critical_bytes=128 * 1024 * 1024,
        notes="Shock-event forensic log.",
    ),
    ActiveFilePolicy(
        path="trades/trades.db",
        tier="hot",
        owner="trade_sqlite_store",
        warning_bytes=256 * 1024 * 1024,
        critical_bytes=1024 * 1024 * 1024,
        notes="SQLite mirror for read/query acceleration.",
    ),
    ActiveFilePolicy(
        path="trades/trades.db-wal",
        tier="hot",
        owner="trade_sqlite_store",
        warning_bytes=64 * 1024 * 1024,
        critical_bytes=256 * 1024 * 1024,
        notes="SQLite WAL growth should be monitored for checkpoint health.",
    ),
    ActiveFilePolicy(
        path="runtime_status.json",
        tier="hot",
        owner="trading_application",
        warning_bytes=5 * 1024 * 1024,
        critical_bytes=10 * 1024 * 1024,
        notes="Latest status should stay slim and not carry full detail payloads.",
    ),
    ActiveFilePolicy(
        path="runtime_loop_debug.json",
        tier="hot",
        owner="trading_application",
        warning_bytes=1 * 1024 * 1024,
        critical_bytes=5 * 1024 * 1024,
        notes="Loop debug file should remain tiny.",
    ),
    ActiveFilePolicy(
        path="observability/events.jsonl",
        tier="hot",
        owner="file_observability_adapter",
        warning_bytes=10 * 1024 * 1024,
        critical_bytes=25 * 1024 * 1024,
        notes="Append-only events stream; requires rollover and retention.",
    ),
    ActiveFilePolicy(
        path="observability/counters.json",
        tier="hot",
        owner="file_observability_adapter",
        warning_bytes=1 * 1024 * 1024,
        critical_bytes=5 * 1024 * 1024,
        notes="Counter snapshot should remain tiny.",
    ),
    ActiveFilePolicy(
        path="logs/bot.log",
        tier="hot",
        owner="trading_application_runner",
        warning_bytes=10 * 1024 * 1024,
        critical_bytes=20 * 1024 * 1024,
        notes="Bot log should be rotated before multi-file growth.",
    ),
]


FIELD_PACK_BASELINE: dict[str, list[str]] = {
    "hot_keep_pack": [
        "time",
        "signal_timeframe",
        "signal_bar_ts",
        "symbol",
        "action",
        "considered",
        "outcome",
        "blocked_by",
        "entry_score_raw",
        "contra_score_raw",
        "effective_entry_threshold",
        "base_entry_threshold",
        "entry_stage",
        "ai_probability",
        "size_multiplier",
        "core_reason",
        "core_pass",
        "core_allowed_action",
        "setup_id",
        "setup_side",
        "setup_status",
        "setup_trigger_state",
        "setup_score",
        "setup_entry_quality",
        "wait_score",
        "wait_conflict",
        "wait_noise",
        "wait_penalty",
        "entry_wait_state",
        "entry_wait_selected",
        "entry_wait_decision",
        "transition_side_separation",
        "transition_confirm_fake_gap",
        "transition_reversal_continuation_gap",
        "management_continue_fail_gap",
        "management_recover_reentry_gap",
        "preflight_regime",
        "preflight_liquidity",
        "preflight_allowed_action",
        "preflight_approach_mode",
        "consumer_archetype_id",
        "consumer_invalidation_id",
        "consumer_management_profile_id",
        "consumer_guard_result",
        "consumer_effective_action",
        "consumer_block_reason",
    ],
    "warm_metadata_pack": [
        "prs_contract_version",
        "prs_canonical_*_field",
        "*_contract_v1",
        "*_scope_contract_v1",
        "*_migration_*",
        "layer_mode_*",
        "shadow_*",
        "last_order_comment",
    ],
    "current_ml_promotion_pack": [
        "entry_setup_id",
        "management_profile_id",
        "invalidation_id",
        "entry_wait_state",
        "entry_quality",
        "entry_model_confidence",
        "entry_h1_context_score",
        "entry_m1_trigger_score",
        "entry_h1_gate_pass",
        "entry_topdown_gate_pass",
        "entry_topdown_align_count",
        "entry_topdown_conflict_count",
        "entry_session_name",
        "entry_atr_ratio",
        "entry_slippage_points",
        "net_pnl_after_cost",
        "exit_policy_stage",
        "exit_profile",
        "exit_confidence",
        "giveback_usd",
        "post_exit_mae",
        "post_exit_mfe",
        "shock_score",
        "shock_hold_delta_30",
        "wait_quality_label",
        "loss_quality_label",
    ],
    "semantic_compact_promotion_pack": [
        "position.vector.x_box",
        "position.vector.x_bb20",
        "position.vector.x_bb44",
        "position.vector.x_ma20",
        "position.vector.x_ma60",
        "position.interpretation.pos_composite",
        "position.interpretation.alignment_label",
        "position.interpretation.conflict_kind",
        "position.energy.lower_position_force",
        "position.energy.upper_position_force",
        "position.energy.position_conflict_score",
        "response.lower_break_down",
        "response.lower_hold_up",
        "response.mid_lose_down",
        "response.mid_reclaim_up",
        "response.upper_break_up",
        "response.upper_reject_down",
        "state.alignment_gain",
        "state.breakout_continuation_gain",
        "state.trend_pullback_gain",
        "state.range_reversal_gain",
        "state.conflict_damp",
        "state.noise_damp",
        "state.liquidity_penalty",
        "state.volatility_penalty",
        "state.countertrend_penalty",
        "evidence.buy_total_evidence",
        "evidence.buy_continuation_evidence",
        "evidence.buy_reversal_evidence",
        "evidence.sell_total_evidence",
        "evidence.sell_continuation_evidence",
        "evidence.sell_reversal_evidence",
        "forecast.position_primary_label",
        "forecast.position_secondary_context_label",
        "forecast.position_conflict_score",
        "forecast.middle_neutrality",
    ],
}


DIRECTORY_TARGETS = [
    "trades",
    "datasets",
    "logs",
    "observability",
    "analysis",
    "reports",
]


def _now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_manifest_dirs() -> dict[str, Path]:
    directories = {
        "baseline": MANIFEST_ROOT / "baseline",
        "rollover": MANIFEST_ROOT / "rollover",
        "archive": MANIFEST_ROOT / "archive",
        "export": MANIFEST_ROOT / "export",
        "retention": MANIFEST_ROOT / "retention",
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


def _to_mb(num_bytes: int) -> float:
    return round(float(num_bytes) / (1024.0 * 1024.0), 2)


def _status_for(size_bytes: int, warning_bytes: int, critical_bytes: int) -> str:
    if size_bytes >= critical_bytes:
        return "critical"
    if size_bytes >= warning_bytes:
        return "warning"
    return "ok"


def _scan_active_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy in ACTIVE_FILE_POLICIES:
        path = DATA_DIR / Path(policy.path)
        exists = path.exists()
        size_bytes = int(path.stat().st_size) if exists else 0
        rows.append(
            {
                "path": policy.path.replace("\\", "/"),
                "tier": policy.tier,
                "owner": policy.owner,
                "exists": exists,
                "size_bytes": size_bytes,
                "size_mb": _to_mb(size_bytes),
                "warning_bytes": policy.warning_bytes,
                "warning_mb": _to_mb(policy.warning_bytes),
                "critical_bytes": policy.critical_bytes,
                "critical_mb": _to_mb(policy.critical_bytes),
                "status": "missing" if not exists else _status_for(size_bytes, policy.warning_bytes, policy.critical_bytes),
                "notes": policy.notes,
            }
        )
    return rows


def _scan_directory_totals() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in DIRECTORY_TARGETS:
        path = DATA_DIR / rel
        total = 0
        file_count = 0
        if path.exists():
            for child in path.rglob("*"):
                if child.is_file():
                    total += int(child.stat().st_size)
                    file_count += 1
        out.append(
            {
                "path": rel.replace("\\", "/"),
                "file_count": file_count,
                "size_bytes": total,
                "size_mb": _to_mb(total),
            }
        )
    return out


def _scan_top_files(top_n: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in DATA_DIR.rglob("*"):
        if child.is_file():
            size_bytes = int(child.stat().st_size)
            rel = str(child.relative_to(DATA_DIR)).replace("\\", "/")
            rows.append(
                {
                    "path": rel,
                    "size_bytes": size_bytes,
                    "size_mb": _to_mb(size_bytes),
                }
            )
    rows.sort(key=lambda item: item["size_bytes"], reverse=True)
    return rows[:top_n]


def _build_report() -> dict[str, Any]:
    active_inventory = _scan_active_inventory()
    directory_totals = _scan_directory_totals()
    top_files = _scan_top_files()
    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "job_name": "ml_storage_step1_baseline",
        "schema_version": "ml_storage_baseline_v1",
        "project_root": str(PROJECT_ROOT),
        "data_root": str(DATA_DIR),
        "manifest_root": str(MANIFEST_ROOT),
        "active_inventory": active_inventory,
        "directory_totals": directory_totals,
        "top_files": top_files,
        "field_pack_baseline": FIELD_PACK_BASELINE,
        "field_pack_counts": {name: len(items) for name, items in FIELD_PACK_BASELINE.items()},
        "summary": {
            "active_file_count": len(active_inventory),
            "warning_or_critical_active_files": [
                row["path"]
                for row in active_inventory
                if row["status"] in {"warning", "critical"}
            ],
            "largest_active_file": max(active_inventory, key=lambda item: item["size_bytes"])["path"] if active_inventory else "",
            "largest_data_file": top_files[0]["path"] if top_files else "",
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# ML Storage Baseline")
    lines.append("")
    lines.append(f"- created_at: `{report['created_at']}`")
    lines.append(f"- schema_version: `{report['schema_version']}`")
    lines.append(f"- active_files: `{report['summary']['active_file_count']}`")
    lines.append("")
    lines.append("## Active Inventory")
    lines.append("")
    lines.append("| path | status | size_mb | warning_mb | critical_mb | owner |")
    lines.append("| --- | --- | ---: | ---: | ---: | --- |")
    for row in report["active_inventory"]:
        lines.append(
            f"| `{row['path']}` | `{row['status']}` | {row['size_mb']} | {row['warning_mb']} | {row['critical_mb']} | `{row['owner']}` |"
        )
    lines.append("")
    lines.append("## Directory Totals")
    lines.append("")
    lines.append("| path | file_count | size_mb |")
    lines.append("| --- | ---: | ---: |")
    for row in report["directory_totals"]:
        lines.append(f"| `{row['path']}` | {row['file_count']} | {row['size_mb']} |")
    lines.append("")
    lines.append("## Largest Files")
    lines.append("")
    lines.append("| path | size_mb |")
    lines.append("| --- | ---: |")
    for row in report["top_files"]:
        lines.append(f"| `{row['path']}` | {row['size_mb']} |")
    lines.append("")
    lines.append("## Field Pack Baseline")
    lines.append("")
    for name, items in FIELD_PACK_BASELINE.items():
        lines.append(f"### {name}")
        lines.append("")
        for item in items:
            lines.append(f"- `{item}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    dirs = _ensure_manifest_dirs()
    report = _build_report()
    timestamp = _now_slug()

    latest_json = dirs["baseline"] / "ml_storage_baseline_latest.json"
    stamped_json = dirs["baseline"] / f"ml_storage_baseline_{timestamp}.json"
    latest_md = dirs["baseline"] / "ml_storage_baseline_latest.md"
    stamped_md = dirs["baseline"] / f"ml_storage_baseline_{timestamp}.md"

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    markdown = _render_markdown(report)

    latest_json.write_text(payload, encoding="utf-8")
    stamped_json.write_text(payload, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")
    stamped_md.write_text(markdown, encoding="utf-8")

    print(f"wrote: {latest_json}")
    print(f"wrote: {stamped_json}")
    print(f"wrote: {latest_md}")
    print(f"wrote: {stamped_md}")


if __name__ == "__main__":
    main()
