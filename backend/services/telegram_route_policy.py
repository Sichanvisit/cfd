from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.core.config import Config


TELEGRAM_ROUTE_POLICY_CONTRACT_VERSION = "telegram_route_policy_v1"
PNL_WINDOW_CODES = ("15M", "1H", "4H", "1D", "1W", "1M")


def _coerce_text(value: object) -> str:
    text = str(value or "").strip()
    return text


def _coerce_topic_id(value: object) -> str | None:
    text = _coerce_text(value)
    if not text or text == "0":
        return None
    return text


def _normalize_window_code(window_code: str | None) -> str:
    code = str(window_code or "").strip()
    if not code:
        return ""
    if code in {"15m", "15M"}:
        return "15M"
    if code == "1m":
        return ""
    lowered = code.lower()
    if lowered == "1h":
        return "1H"
    if lowered == "4h":
        return "4H"
    if lowered == "1d":
        return "1D"
    if lowered == "1w":
        return "1W"
    if code == "1M":
        return "1M"
    return ""


@dataclass(frozen=True, slots=True)
class TelegramRouteTarget:
    route_key: str
    role_ko: str
    chat_id: str
    topic_id: str | None
    is_forum_topic: bool
    allowed_message_kinds: tuple[str, ...]
    notes_ko: str


@dataclass(frozen=True, slots=True)
class TelegramRouteIssue:
    severity: str
    code: str
    message_ko: str


@dataclass(slots=True)
class TelegramRouteBaseline:
    contract_version: str
    runtime_dm: TelegramRouteTarget
    check_topic: TelegramRouteTarget
    report_topic: TelegramRouteTarget
    pnl_topics: dict[str, TelegramRouteTarget] = field(default_factory=dict)
    issues: list[TelegramRouteIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "runtime_dm": asdict(self.runtime_dm),
            "check_topic": asdict(self.check_topic),
            "report_topic": asdict(self.report_topic),
            "pnl_topics": {key: asdict(value) for key, value in self.pnl_topics.items()},
            "issues": [asdict(issue) for issue in self.issues],
        }


def _build_runtime_target() -> TelegramRouteTarget:
    return TelegramRouteTarget(
        route_key="runtime",
        role_ko="실시간 실행 DM",
        chat_id=_coerce_text(getattr(Config, "TG_CHAT_ID", "")),
        topic_id=None,
        is_forum_topic=False,
        allowed_message_kinds=("entry", "wait", "exit", "reverse"),
        notes_ko="실시간 진입/대기/청산/반전 전용. 승인 카드 금지.",
    )


def _build_check_target() -> TelegramRouteTarget:
    topic_id = _coerce_topic_id(getattr(Config, "TG_CHECK_TOPIC_ID", 0))
    return TelegramRouteTarget(
        route_key="check",
        role_ko="개선안 체크 inbox",
        chat_id=_coerce_text(getattr(Config, "TG_CHECK_CHAT_ID", "")),
        topic_id=topic_id,
        is_forum_topic=bool(topic_id),
        allowed_message_kinds=("proposal_inbox", "readiness_summary", "status_update"),
        notes_ko="짧은 backlog / inbox 전용. 원문 보고서 금지.",
    )


def _build_report_target() -> TelegramRouteTarget:
    topic_id = _coerce_topic_id(getattr(Config, "TG_REPORT_TOPIC_ID", 0))
    return TelegramRouteTarget(
        route_key="report",
        role_ko="원문 보고서 topic",
        chat_id=_coerce_text(getattr(Config, "TG_REPORT_CHAT_ID", "")),
        topic_id=topic_id,
        is_forum_topic=bool(topic_id),
        allowed_message_kinds=("proposal_report", "review_packet", "apply_packet"),
        notes_ko="상세 보고서 / 승인 카드 전용. 실시간 실행 메시지 금지.",
    )


def _build_pnl_targets() -> dict[str, TelegramRouteTarget]:
    mapping = {
        "15M": getattr(Config, "TG_PNL_TOPIC_15M_ID", 0),
        "1H": getattr(Config, "TG_PNL_TOPIC_1H_ID", 0),
        "4H": getattr(Config, "TG_PNL_TOPIC_4H_ID", 0),
        "1D": getattr(Config, "TG_PNL_TOPIC_1D_ID", 0),
        "1W": getattr(Config, "TG_PNL_TOPIC_1W_ID", 0),
        "1M": getattr(Config, "TG_PNL_TOPIC_1M_ID", 0),
    }
    chat_id = _coerce_text(getattr(Config, "TG_PNL_FORUM_CHAT_ID", ""))
    targets: dict[str, TelegramRouteTarget] = {}
    for window_code, topic_value in mapping.items():
        topic_id = _coerce_topic_id(topic_value)
        targets[window_code] = TelegramRouteTarget(
            route_key=f"pnl:{window_code.lower()}",
            role_ko=f"PnL {window_code} topic",
            chat_id=chat_id,
            topic_id=topic_id,
            is_forum_topic=bool(topic_id),
            allowed_message_kinds=("pnl_digest", "lesson_comment", "readiness_summary"),
            notes_ko=f"{window_code} 손익 요약과 교훈 코멘트 전용.",
        )
    return targets


def _validate_route_baseline(
    *,
    runtime_dm: TelegramRouteTarget,
    check_topic: TelegramRouteTarget,
    report_topic: TelegramRouteTarget,
    pnl_topics: dict[str, TelegramRouteTarget],
) -> list[TelegramRouteIssue]:
    issues: list[TelegramRouteIssue] = []

    if not runtime_dm.chat_id:
        issues.append(TelegramRouteIssue("ERROR", "runtime_chat_missing", "실시간 DM chat_id가 비어 있습니다."))
    if not check_topic.chat_id:
        issues.append(TelegramRouteIssue("ERROR", "check_chat_missing", "체크 topic chat_id가 비어 있습니다."))
    if not report_topic.chat_id:
        issues.append(TelegramRouteIssue("ERROR", "report_chat_missing", "보고서 topic chat_id가 비어 있습니다."))

    if check_topic.chat_id and report_topic.chat_id:
        if check_topic.chat_id == report_topic.chat_id and check_topic.topic_id == report_topic.topic_id:
            issues.append(
                TelegramRouteIssue(
                    "ERROR",
                    "check_report_topic_conflict",
                    "체크 topic과 보고서 topic이 같은 목적지를 가리킵니다.",
                )
            )

    if runtime_dm.chat_id and runtime_dm.chat_id in {check_topic.chat_id, report_topic.chat_id}:
        issues.append(
            TelegramRouteIssue(
                "WARN",
                "runtime_shared_with_control_plane",
                "실시간 DM이 개선안/보고서 방과 같은 chat_id를 사용하고 있습니다.",
            )
        )

    for window_code, route in pnl_topics.items():
        if not route.chat_id:
            issues.append(
                TelegramRouteIssue(
                    "ERROR",
                    f"pnl_chat_missing_{window_code.lower()}",
                    f"PnL {window_code} forum chat_id가 비어 있습니다.",
                )
            )
            continue
        if not route.topic_id:
            issues.append(
                TelegramRouteIssue(
                    "ERROR",
                    f"pnl_topic_missing_{window_code.lower()}",
                    f"PnL {window_code} topic_id가 비어 있습니다.",
                )
            )
    return issues


def build_telegram_route_baseline() -> TelegramRouteBaseline:
    runtime_dm = _build_runtime_target()
    check_topic = _build_check_target()
    report_topic = _build_report_target()
    pnl_topics = _build_pnl_targets()
    issues = _validate_route_baseline(
        runtime_dm=runtime_dm,
        check_topic=check_topic,
        report_topic=report_topic,
        pnl_topics=pnl_topics,
    )
    return TelegramRouteBaseline(
        contract_version=TELEGRAM_ROUTE_POLICY_CONTRACT_VERSION,
        runtime_dm=runtime_dm,
        check_topic=check_topic,
        report_topic=report_topic,
        pnl_topics=pnl_topics,
        issues=issues,
    )


def resolve_telegram_route_destination(
    *,
    route: str | None = None,
    window_code: str | None = None,
    chat_id: str | int | None = None,
    thread_id: str | int | None = None,
) -> tuple[str, str | None]:
    if chat_id is not None and str(chat_id).strip():
        return str(chat_id).strip(), _coerce_topic_id(thread_id)

    baseline = build_telegram_route_baseline()
    route_name = str(route or "runtime").strip().lower()
    if route_name in {"runtime", "default", "dm", "trading_bot"}:
        return baseline.runtime_dm.chat_id, _coerce_topic_id(thread_id)
    if route_name == "check":
        return baseline.check_topic.chat_id, _coerce_topic_id(thread_id) or baseline.check_topic.topic_id
    if route_name == "report":
        return baseline.report_topic.chat_id, _coerce_topic_id(thread_id) or baseline.report_topic.topic_id
    if route_name == "pnl":
        normalized = _normalize_window_code(window_code)
        if not normalized:
            return "", None
        target = baseline.pnl_topics.get(normalized)
        if not target:
            return "", None
        return target.chat_id, _coerce_topic_id(thread_id) or target.topic_id
    return baseline.runtime_dm.chat_id, _coerce_topic_id(thread_id)


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_telegram_route_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "telegram_route_baseline_latest.json",
        directory / "telegram_route_baseline_latest.md",
    )


def render_telegram_route_baseline_markdown(baseline: TelegramRouteBaseline) -> str:
    lines = [
        "# Telegram Route Baseline",
        "",
        f"- contract_version: `{baseline.contract_version}`",
        "",
        "## Runtime DM",
        f"- chat_id: `{baseline.runtime_dm.chat_id or '-'}`",
        f"- topic_id: `{baseline.runtime_dm.topic_id or '-'}`",
        f"- role: {baseline.runtime_dm.role_ko}",
        f"- notes: {baseline.runtime_dm.notes_ko}",
        "",
        "## Improvement Control",
        f"- check: `{baseline.check_topic.chat_id or '-'} / {baseline.check_topic.topic_id or '-'}` -> {baseline.check_topic.role_ko}",
        f"- report: `{baseline.report_topic.chat_id or '-'} / {baseline.report_topic.topic_id or '-'}` -> {baseline.report_topic.role_ko}",
        "",
        "## PnL Topics",
    ]
    for window_code in PNL_WINDOW_CODES:
        route = baseline.pnl_topics.get(window_code)
        if not route:
            continue
        lines.append(
            f"- {window_code}: `{route.chat_id or '-'} / {route.topic_id or '-'}` -> {route.role_ko}"
        )
    lines.extend(["", "## Issues"])
    if not baseline.issues:
        lines.append("- none")
    else:
        for issue in baseline.issues:
            lines.append(f"- [{issue.severity}] {issue.code}: {issue.message_ko}")
    return "\n".join(lines)


def write_telegram_route_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    baseline = build_telegram_route_baseline()
    default_json_path, default_markdown_path = default_telegram_route_baseline_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(baseline.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_telegram_route_baseline_markdown(baseline),
        encoding="utf-8",
    )
    return {
        "contract_version": baseline.contract_version,
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
        "issues": [asdict(issue) for issue in baseline.issues],
    }
