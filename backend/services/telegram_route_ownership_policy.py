from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


TELEGRAM_ROUTE_OWNERSHIP_POLICY_CONTRACT_VERSION = "telegram_route_ownership_policy_v1"

OWNER_RUNTIME_EXECUTION = "runtime_execution"
OWNER_IMPROVEMENT_CHECK_INBOX = "improvement_check_inbox"
OWNER_IMPROVEMENT_REPORT_TOPIC = "improvement_report_topic"
OWNER_PNL_DIGEST = "pnl_digest"
OWNER_BOOTSTRAP_PROBE = "bootstrap_probe"
OWNER_LEGACY_LIVE_CHECK_CARD = "legacy_live_check_card"


@dataclass(frozen=True, slots=True)
class TelegramRouteOwnerPolicy:
    owner_key: str
    layer_name: str
    allowed_routes: tuple[str, ...]
    allowed_message_kinds: tuple[str, ...]
    enabled_by_default: bool
    notes_ko: str


OWNER_POLICIES: dict[str, TelegramRouteOwnerPolicy] = {
    OWNER_RUNTIME_EXECUTION: TelegramRouteOwnerPolicy(
        owner_key=OWNER_RUNTIME_EXECUTION,
        layer_name="실시간 자동매매 런타임",
        allowed_routes=("runtime",),
        allowed_message_kinds=("entry", "wait", "exit", "reverse"),
        enabled_by_default=True,
        notes_ko="실시간 진입/대기/청산/반전 알림만 DM으로 보낸다.",
    ),
    OWNER_IMPROVEMENT_CHECK_INBOX: TelegramRouteOwnerPolicy(
        owner_key=OWNER_IMPROVEMENT_CHECK_INBOX,
        layer_name="checkpoint improvement check inbox",
        allowed_routes=("check",),
        allowed_message_kinds=("proposal_inbox", "readiness_summary", "status_update"),
        enabled_by_default=True,
        notes_ko="개선안 inbox와 readiness 요약만 체크 topic으로 보낸다.",
    ),
    OWNER_IMPROVEMENT_REPORT_TOPIC: TelegramRouteOwnerPolicy(
        owner_key=OWNER_IMPROVEMENT_REPORT_TOPIC,
        layer_name="checkpoint improvement report topic",
        allowed_routes=("report",),
        allowed_message_kinds=("proposal_report", "review_packet", "apply_packet"),
        enabled_by_default=True,
        notes_ko="원문 보고서와 review/apply packet만 보고서 topic으로 보낸다.",
    ),
    OWNER_PNL_DIGEST: TelegramRouteOwnerPolicy(
        owner_key=OWNER_PNL_DIGEST,
        layer_name="PnL digest loop",
        allowed_routes=("pnl",),
        allowed_message_kinds=("pnl_digest", "lesson_comment", "readiness_summary"),
        enabled_by_default=True,
        notes_ko="손익 요약과 교훈, readiness 요약만 PnL forum으로 보낸다.",
    ),
    OWNER_BOOTSTRAP_PROBE: TelegramRouteOwnerPolicy(
        owner_key=OWNER_BOOTSTRAP_PROBE,
        layer_name="telegram bootstrap probe",
        allowed_routes=("runtime", "check", "report", "pnl"),
        allowed_message_kinds=("bootstrap_probe", "route_probe"),
        enabled_by_default=True,
        notes_ko="배선 확인용 probe만 예외적으로 여러 route에 보낼 수 있다.",
    ),
    OWNER_LEGACY_LIVE_CHECK_CARD: TelegramRouteOwnerPolicy(
        owner_key=OWNER_LEGACY_LIVE_CHECK_CARD,
        layer_name="legacy live check card",
        allowed_routes=("check",),
        allowed_message_kinds=("legacy_check_card",),
        enabled_by_default=False,
        notes_ko="구형 실시간 체크 카드는 기본 비활성이고, check topic에만 제한한다.",
    ),
}


def get_telegram_route_owner_policy(owner_key: str) -> TelegramRouteOwnerPolicy:
    normalized = str(owner_key or "").strip()
    if normalized not in OWNER_POLICIES:
        raise KeyError(f"unknown_telegram_route_owner::{normalized}")
    return OWNER_POLICIES[normalized]


def validate_telegram_route_ownership(
    *,
    owner_key: str,
    route: str,
) -> TelegramRouteOwnerPolicy:
    policy = get_telegram_route_owner_policy(owner_key)
    normalized_route = str(route or "").strip().lower()
    if normalized_route not in policy.allowed_routes:
        raise ValueError(
            f"telegram_route_ownership_violation::{owner_key}::{normalized_route}"
        )
    return policy


def build_telegram_route_ownership_baseline() -> dict[str, Any]:
    return {
        "contract_version": TELEGRAM_ROUTE_OWNERSHIP_POLICY_CONTRACT_VERSION,
        "owners": [asdict(policy) for policy in OWNER_POLICIES.values()],
    }


def render_telegram_route_ownership_baseline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Telegram Route Ownership Baseline",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        "",
        "## Owners",
    ]
    for row in payload.get("owners", []):
        lines.extend(
            [
                f"- `{row['owner_key']}` | {row['layer_name']}",
                f"  allowed_routes: `{', '.join(row.get('allowed_routes', []))}`",
                f"  enabled_by_default: `{row.get('enabled_by_default')}`",
                f"  message_kinds: `{', '.join(row.get('allowed_message_kinds', []))}`",
                f"  notes: {row.get('notes_ko', '-')}",
            ]
        )
    return "\n".join(lines)


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_telegram_route_ownership_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "telegram_route_ownership_baseline_latest.json",
        directory / "telegram_route_ownership_baseline_latest.md",
    )


def write_telegram_route_ownership_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_telegram_route_ownership_baseline()
    default_json_path, default_markdown_path = default_telegram_route_ownership_baseline_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_telegram_route_ownership_baseline_markdown(payload),
        encoding="utf-8",
    )
    return {
        "contract_version": payload["contract_version"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
