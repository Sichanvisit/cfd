"""Telegram ops service for runtime DM, periodic PnL digests, and checkpoint approvals."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from backend.core.config import Config
from backend.integrations import notifier
from backend.services.checkpoint_improvement_telegram_runtime import (
    CheckpointImprovementTelegramRuntime,
    build_checkpoint_improvement_telegram_runtime,
)
from backend.services.checkpoint_improvement_master_board import (
    default_checkpoint_improvement_master_board_json_path,
)
from backend.services.improvement_readiness_surface import (
    build_pnl_readiness_digest_lines,
)
from backend.services.improvement_log_only_detector import (
    DEFAULT_DETECT_RECENT_LIMIT,
    MANUAL_DETECT_COMMAND,
    build_default_improvement_log_only_detector_snapshot,
    write_improvement_log_only_detector_snapshot,
)
from backend.services.improvement_detector_feedback_runtime import (
    MANUAL_DETECT_FEEDBACK_COMMAND,
    build_detector_confusion_snapshot,
    build_detector_feedback_entry,
    build_detector_feedback_snapshot,
    detector_feedback_verdict_label_ko,
    find_detect_issue_ref,
    normalize_detector_feedback_verdict,
    write_detector_confusion_snapshot,
    write_detector_feedback_snapshot,
)
from backend.services.path_checkpoint_context import default_checkpoint_rows_path
from backend.services.telegram_pnl_digest_formatter import build_telegram_pnl_digest_message
from backend.services.telegram_route_ownership_policy import (
    OWNER_BOOTSTRAP_PROBE,
    OWNER_LEGACY_LIVE_CHECK_CARD,
    OWNER_IMPROVEMENT_CHECK_INBOX,
    OWNER_IMPROVEMENT_REPORT_TOPIC,
    OWNER_PNL_DIGEST,
    validate_telegram_route_ownership,
)
from backend.services.trade_feedback_runtime import (
    DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT,
    MANUAL_PROPOSE_COMMAND,
    build_manual_trade_proposal_snapshot,
    build_pnl_lesson_comment_lines,
    write_manual_trade_proposal_snapshot,
)

logger = logging.getLogger(__name__)
KST = ZoneInfo(str(getattr(Config, "TIMEZONE", "Asia/Seoul") or "Asia/Seoul"))

TELEGRAM_OPS_STATE_CONTRACT_VERSION = "telegram_ops_state_v1"
TELEGRAM_OPS_BOOTSTRAP_VERSION = "telegram_ops_bootstrap_v1"
TELEGRAM_PNL_WINDOWS = ("15m", "1H", "4H", "1D", "1W", "1M")
TELEGRAM_CHECK_DECISIONS = {"approve": "APPROVED", "reject": "REJECTED", "hold": "HELD"}
TELEGRAM_CHECK_ACTION_MAP = {
    "REBUY": ("ENTRY", "ENTER", "재진입 허용 검토"),
    "FULL_EXIT": ("EXIT", "EXIT", "전량 청산 검토"),
    "PARTIAL_EXIT": ("MANAGE", "REDUCE", "부분 청산 검토"),
    "PARTIAL_THEN_HOLD": ("MANAGE", "REDUCE", "일부 축소 후 보유 검토"),
}


TELEGRAM_CHECK_ACTION_MAP = {
    "REBUY": ("ENTRY", "ENTER", "재진입 후보입니다."),
    "FULL_EXIT": ("EXIT", "EXIT", "전량 청산 후보입니다."),
    "PARTIAL_EXIT": ("MANAGE", "REDUCE", "부분 청산 후보입니다."),
    "PARTIAL_THEN_HOLD": ("MANAGE", "REDUCE", "일부 축소 후 보유 후보입니다."),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_telegram_ops_state_path() -> Path:
    raw = str(getattr(Config, "TG_OPS_STATE_PATH", "") or "").strip()
    path = Path(raw) if raw else Path(r"data\runtime\telegram_ops_state.json")
    if not path.is_absolute():
        path = _repo_root() / path
    return path.resolve()


def default_telegram_ops_decision_log_path() -> Path:
    return default_telegram_ops_state_path().with_name("telegram_ops_decisions.jsonl")


def _now_kst() -> datetime:
    return datetime.now(KST)


def _safe_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _safe_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_kst_datetime(value: object) -> datetime | None:
    if value in ("", None):
        return None
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except Exception:
        return None
    if pd.isna(parsed):
        return None
    if getattr(parsed, "tzinfo", None) is None:
        return parsed.to_pydatetime().replace(tzinfo=KST)
    return parsed.to_pydatetime().astimezone(KST)


def _fmt_money(value: float) -> str:
    return f"{value:+.2f} USD"


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _fmt_dt(value: datetime) -> str:
    return value.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def _window_label(window_code: str) -> str:
    mapping = {
        "15m": "15분",
        "1H": "1시간",
        "4H": "4시간",
        "1D": "1일",
        "1W": "1주",
        "1M": "1달",
    }
    return mapping.get(str(window_code or "").strip(), str(window_code or "").strip() or "구간")


def _strength_label(strength: object) -> str:
    mapping = {
        "HIGH": "높음",
        "MEDIUM": "보통",
        "LOW": "낮음",
    }
    return mapping.get(_safe_text(strength).upper(), _safe_text(strength, "-"))


def _kind_label(kind: object) -> str:
    mapping = {
        "ENTRY": "진입 검토",
        "EXIT": "청산 검토",
        "MANAGE": "관리 검토",
        "CHECK": "체크 검토",
    }
    return mapping.get(_safe_text(kind).upper(), _safe_text(kind, "-"))


def _status_label(status: object) -> str:
    mapping = {
        "PENDING": "대기",
        "APPROVED": "승인",
        "HELD": "보류",
        "REJECTED": "거부",
        "EXPIRED": "만료",
        "APPLIED": "적용 완료",
    }
    return mapping.get(_safe_text(status).upper(), _safe_text(status, "-"))


def _recommended_action_label(action: object) -> str:
    mapping = {
        "ENTER": "진입",
        "EXIT": "전량 청산",
        "REDUCE": "부분 축소",
        "WAIT": "대기 유지",
    }
    return mapping.get(_safe_text(action).upper(), _safe_text(action, "-"))


def _month_start(dt: datetime) -> datetime:
    return dt.astimezone(KST).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _week_start(dt: datetime) -> datetime:
    base = dt.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return base - timedelta(days=base.weekday())


def resolve_completed_window(window_code: str, now: datetime | None = None) -> tuple[datetime, datetime, str]:
    current = (now or _now_kst()).astimezone(KST)
    code = str(window_code or "").strip()
    if code == "15m":
        bucket_end = current.replace(minute=(current.minute // 15) * 15, second=0, microsecond=0)
        bucket_start = bucket_end - timedelta(minutes=15)
    elif code == "1H":
        bucket_end = current.replace(minute=0, second=0, microsecond=0)
        bucket_start = bucket_end - timedelta(hours=1)
    elif code == "4H":
        bucket_end = current.replace(hour=(current.hour // 4) * 4, minute=0, second=0, microsecond=0)
        bucket_start = bucket_end - timedelta(hours=4)
    elif code == "1D":
        bucket_end = current.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket_start = bucket_end - timedelta(days=1)
    elif code == "1W":
        bucket_end = _week_start(current)
        bucket_start = bucket_end - timedelta(days=7)
    elif code == "1M":
        bucket_end = _month_start(current)
        bucket_start = _month_start(bucket_end - timedelta(days=1))
    else:
        raise ValueError(f"Unsupported window code: {window_code}")
    bucket_key = bucket_end.isoformat()
    return bucket_start, bucket_end, bucket_key


def _choose_pnl_column(frame: pd.DataFrame) -> str:
    if "net_pnl_after_cost" in frame.columns:
        series = pd.to_numeric(frame["net_pnl_after_cost"], errors="coerce").fillna(0.0)
        if float(series.abs().sum()) > 0.0:
            return "net_pnl_after_cost"
    if "profit" in frame.columns:
        return "profit"
    return "profit"


def _prepare_closed_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    closed = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    if closed.empty:
        return closed
    for col in ("symbol", "entry_reason", "exit_reason", "close_time"):
        if col not in closed.columns:
            closed[col] = ""
    if "close_ts" not in closed.columns:
        closed["close_ts"] = 0
    closed["close_dt"] = pd.to_datetime(closed["close_time"], errors="coerce")
    close_ts = pd.to_numeric(closed.get("close_ts", 0), errors="coerce").fillna(0)
    has_ts = close_ts > 0
    if bool(has_ts.any()):
        ts_dt = pd.to_datetime(close_ts.where(has_ts), unit="s", errors="coerce", utc=True).dt.tz_convert(KST)
        closed.loc[has_ts, "close_dt"] = closed.loc[has_ts, "close_dt"].fillna(ts_dt)
    closed = closed[closed["close_dt"].notna()].copy()
    if closed.empty:
        return closed
    closed["close_dt"] = closed["close_dt"].map(
        lambda dt: dt.tz_localize(KST) if getattr(dt, "tzinfo", None) is None else dt.tz_convert(KST)
    )
    pnl_column = _choose_pnl_column(closed)
    closed["realized_pnl"] = pd.to_numeric(closed.get(pnl_column, 0.0), errors="coerce").fillna(0.0)
    closed["symbol"] = closed["symbol"].fillna("").astype(str).str.upper()
    closed["entry_reason"] = closed["entry_reason"].fillna("").astype(str)
    closed["exit_reason"] = closed["exit_reason"].fillna("").astype(str)
    return closed.sort_values("close_dt").reset_index(drop=True)


def build_pnl_digest_message(window_code: str, closed_frame: pd.DataFrame | None, *, start: datetime, end: datetime) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()
    pnl_sum = float(pd.to_numeric(scoped.get("realized_pnl", 0.0), errors="coerce").fillna(0.0).sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    wins = int((scoped["realized_pnl"] > 0).sum()) if trades else 0
    losses = int((scoped["realized_pnl"] < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0
    max_drawdown = 0.0
    best_trade = None
    worst_trade = None
    symbol_lines: list[str] = []
    entry_reason_lines: list[str] = []
    exit_reason_lines: list[str] = []
    if trades:
        scoped = scoped.sort_values("close_dt").reset_index(drop=True)
        equity_curve = scoped["realized_pnl"].cumsum()
        drawdown = equity_curve - equity_curve.cummax()
        max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
        best_trade = scoped.loc[scoped["realized_pnl"].idxmax()]
        worst_trade = scoped.loc[scoped["realized_pnl"].idxmin()]
        symbol_summary = (
            scoped.groupby("symbol", dropna=False)["realized_pnl"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(3)
        )
        for symbol, row in symbol_summary.iterrows():
            symbol_lines.append(f"- {symbol or 'UNKNOWN'} {float(row['sum']):+.2f} ({int(row['count'])})")
        for column_name, target_lines in (("entry_reason", entry_reason_lines), ("exit_reason", exit_reason_lines)):
            series = (
                scoped[column_name].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().head(2)
            )
            for label, count in series.items():
                target_lines.append(f"- {label[:72]} ({int(count)})")
    lines = [
        f"[PnL {window_code}]",
        f"window: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"realized: {_fmt_money(pnl_sum)}",
        f"trades: {trades} (win {wins} / loss {losses})",
        f"win rate: {_fmt_pct(win_rate)}",
        f"max drawdown: {_fmt_money(max_drawdown)}",
    ]
    if best_trade is not None:
        lines.append(f"best: {_safe_text(best_trade.get('symbol'), 'UNKNOWN')} {_fmt_money(_safe_float(best_trade.get('realized_pnl'), 0.0))}")
    if worst_trade is not None:
        lines.append(f"worst: {_safe_text(worst_trade.get('symbol'), 'UNKNOWN')} {_fmt_money(_safe_float(worst_trade.get('realized_pnl'), 0.0))}")
    if symbol_lines:
        lines.append("symbols:")
        lines.extend(symbol_lines)
    if entry_reason_lines:
        lines.append("entry reasons:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("exit reasons:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("note: closed trade 없음")
    lines.append(f"updated: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)


_ENTRY_REASON_EXACT_DISPLAY_V5 = {
    "reclaim": "리클레임 진입",
    "breakout": "돌파 진입",
    "probe": "탐색 진입",
    "retest": "재테스트 진입",
    "bounce": "반등 진입",
    "late": "지연 진입",
    "pullback": "눌림 진입",
    "continuation": "지속 진입",
    "reversal": "반전 진입",
}

_EXIT_REASON_EXACT_DISPLAY_V5 = {
    "target": "목표가 도달 청산",
    "runner": "러너 정리 청산",
    "stop": "손절 청산",
    "cut": "위험 차단 청산",
    "timeout": "시간 만료 청산",
    "trail": "추적 청산",
    "partial_exit": "부분 청산",
    "full_exit": "전량 청산",
}

_ENTRY_REASON_FEATURE_V5 = {
    "flat": "플랫",
    "reclaim": "리클레임",
    "reentry": "재진입",
    "ready": "준비",
    "breakout": "돌파",
    "retest": "재테스트",
    "probe": "탐색",
    "bounce": "반등",
    "pullback": "눌림",
    "continuation": "지속",
    "trend": "추세",
    "reversal": "반전",
    "entry": "진입",
    "long": "매수",
    "short": "매도",
}

_EXIT_REASON_FEATURE_V5 = {
    "target": "목표가",
    "runner": "러너",
    "stop": "손절",
    "timeout": "시간만료",
    "cut": "컷",
    "trail": "추적",
    "shock": "충격",
    "protective": "보호",
    "loss": "손실",
    "profit": "수익",
    "hold": "보유",
    "wait": "대기",
    "exit": "청산",
    "partial": "부분",
    "full": "전량",
    "reverse": "반전",
}

_ENTRY_REASON_SENTENCE_V5 = {
    "flat_reclaim_reentry_ready": "플랫 상태에서 리클레임 재진입 준비",
}

_EXIT_REASON_SENTENCE_V5 = {
    "protective_loss_exit": "손실 보호 목적 청산",
}


def _format_reason_display_v5(value: object, *, reason_kind: str) -> str:
    raw = _safe_text(value)
    if not raw:
        return "-"
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if reason_kind == "entry":
        exact_map = _ENTRY_REASON_EXACT_DISPLAY_V5
        feature_map = _ENTRY_REASON_FEATURE_V5
        sentence_map = _ENTRY_REASON_SENTENCE_V5
    else:
        exact_map = _EXIT_REASON_EXACT_DISPLAY_V5
        feature_map = _EXIT_REASON_FEATURE_V5
        sentence_map = _EXIT_REASON_SENTENCE_V5

    if normalized in sentence_map:
        sentence = sentence_map[normalized]
    elif normalized in exact_map:
        sentence = exact_map[normalized]
    else:
        tokens = [token for token in normalized.split("_") if token][:4]
        translated = [feature_map.get(token, token) for token in tokens]
        sentence = " / ".join(translated) if translated else raw

    tokens = [token for token in normalized.split("_") if token][:4]
    feature_labels = [feature_map.get(token, token) for token in tokens]
    feature_labels = [label for label in feature_labels if label and label != sentence]
    if feature_labels:
        return f"{sentence} ({', '.join(feature_labels)})"
    return sentence


def _build_reason_top_lines_v5(
    scoped: pd.DataFrame,
    column_name: str,
    *,
    reason_kind: str,
    limit: int = 5,
) -> list[str]:
    if scoped.empty or column_name not in scoped.columns:
        return []
    working = scoped.copy()
    working["_reason_value"] = working[column_name].fillna("").astype(str).str.strip()
    working = working[working["_reason_value"] != ""].copy()
    if working.empty:
        return []

    summary = (
        working.groupby("_reason_value", dropna=False)
        .agg(
            count=("realized_pnl", "size"),
            net_pnl=("realized_pnl", "sum"),
            win_count=("realized_pnl", lambda series: int((series > 0).sum())),
        )
        .sort_values(["count", "net_pnl"], ascending=[False, False])
        .head(limit)
    )

    total = int(summary["count"].sum()) if not summary.empty else 0
    lines: list[str] = []
    for reason_value, row in summary.iterrows():
        count = int(row["count"])
        share = (count / total) if total else 0.0
        win_rate = (int(row["win_count"]) / count) if count else 0.0
        lines.append(
            f"- {_format_reason_display_v5(reason_value, reason_kind=reason_kind)} | {count}건 | "
            f"비중 {_fmt_pct(share)} | 승률 {_fmt_pct(win_rate)} | 순손익 {_fmt_money(float(row['net_pnl']))}"
        )
    return lines


def _estimate_window_balance_lines_v5(
    prepared_frame: pd.DataFrame,
    scoped_frame: pd.DataFrame,
    *,
    end: datetime,
    current_balance: float | None,
) -> list[str]:
    if current_balance is None:
        return ["잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다."]

    future_pnl = 0.0
    if not prepared_frame.empty:
        future_scope = prepared_frame[prepared_frame["close_dt"] >= end]
        future_pnl = float(_safe_numeric_series(future_scope, "realized_pnl").sum()) if not future_scope.empty else 0.0
    window_pnl = float(_safe_numeric_series(scoped_frame, "realized_pnl").sum()) if not scoped_frame.empty else 0.0
    end_balance = float(current_balance) - future_pnl
    start_balance = end_balance - window_pnl
    return [
        f"구간 시작 잔고(추정): {_fmt_unsigned_money(start_balance)}",
        f"구간 종료 잔고(추정): {_fmt_unsigned_money(end_balance)}",
        "잔고 기준: 현재 계좌 잔고에서 이후 실현손익을 역산한 추정치입니다.",
    ]


def build_pnl_digest_message(
    window_code: str,
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None = None,
) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()

    net_pnl_sum = float(_safe_numeric_series(scoped, "realized_pnl").sum()) if not scoped.empty else 0.0
    gross_pnl_sum = float(_safe_numeric_series(scoped, "gross_pnl").sum()) if not scoped.empty else net_pnl_sum
    total_cost = float(_safe_numeric_series(scoped, "cost_total").sum()) if not scoped.empty else 0.0
    total_lot = float(_safe_numeric_series(scoped, "lot").sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    entries = trades
    wins = int((_safe_numeric_series(scoped, "realized_pnl") > 0).sum()) if trades else 0
    losses = int((_safe_numeric_series(scoped, "realized_pnl") < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0

    entry_reason_lines = _build_reason_top_lines_v5(scoped, "entry_reason", reason_kind="entry", limit=5)
    exit_reason_lines = _build_reason_top_lines_v5(scoped, "exit_reason", reason_kind="exit", limit=5)
    balance_lines = _estimate_window_balance_lines_v5(
        frame,
        scoped,
        end=end,
        current_balance=current_balance,
    )

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"순손익 합계: {_fmt_money(net_pnl_sum)}",
        f"총손익(비용 전): {_fmt_money(gross_pnl_sum)}",
        f"총 비용: {_fmt_unsigned_money(abs(total_cost))}",
        f"진입 횟수(마감 기준): {entries}회",
        f"총 진입 랏: {_fmt_lot(total_lot)}",
        f"승/패: {wins} / {losses} (승률 {_fmt_pct(win_rate)})",
    ]
    lines.extend(balance_lines)

    if entry_reason_lines:
        lines.append("진입 사유 TOP 5:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("청산 사유 TOP 5:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("메모: 이 구간에 마감된 거래가 없어 손익과 사유 통계가 비어 있습니다.")
    lines.append(f"기준 시각: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)


_ENTRY_REASON_EXACT_DISPLAY_V4 = {
    "reclaim": "리클레임 진입",
    "breakout": "돌파 진입",
    "probe": "탐색 진입",
    "retest": "재테스트 진입",
    "bounce": "반등 진입",
    "late": "지연 진입",
    "pullback": "눌림 진입",
    "continuation": "지속 진입",
    "reversal": "반전 진입",
}

_EXIT_REASON_EXACT_DISPLAY_V4 = {
    "target": "목표가 도달 청산",
    "runner": "러너 정리 청산",
    "stop": "손절 청산",
    "cut": "위험 차단 청산",
    "timeout": "시간 만료 청산",
    "trail": "추적 청산",
    "partial_exit": "부분 청산",
    "full_exit": "전량 청산",
}

_ENTRY_REASON_FEATURE_V4 = {
    "flat": "플랫",
    "reclaim": "리클레임",
    "reentry": "재진입",
    "ready": "준비",
    "breakout": "돌파",
    "retest": "재테스트",
    "probe": "탐색",
    "bounce": "반등",
    "pullback": "눌림",
    "continuation": "지속",
    "trend": "추세",
    "reversal": "반전",
    "entry": "진입",
    "long": "매수",
    "short": "매도",
}

_EXIT_REASON_FEATURE_V4 = {
    "target": "목표가",
    "runner": "러너",
    "stop": "손절",
    "timeout": "시간만료",
    "cut": "컷",
    "trail": "추적",
    "shock": "충격",
    "protective": "보호",
    "loss": "손실",
    "profit": "수익",
    "hold": "보유",
    "wait": "대기",
    "exit": "청산",
    "partial": "부분",
    "full": "전량",
    "reverse": "반전",
}

_ENTRY_REASON_SENTENCE_V4 = {
    "flat_reclaim_reentry_ready": "플랫 상태에서 리클레임 재진입 준비",
}

_EXIT_REASON_SENTENCE_V4 = {
    "protective_loss_exit": "손실 보호 목적 청산",
}


def _format_reason_display_v4(value: object, *, reason_kind: str) -> str:
    raw = _safe_text(value)
    if not raw:
        return "-"
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if reason_kind == "entry":
        exact_map = _ENTRY_REASON_EXACT_DISPLAY_V4
        feature_map = _ENTRY_REASON_FEATURE_V4
        sentence_map = _ENTRY_REASON_SENTENCE_V4
    else:
        exact_map = _EXIT_REASON_EXACT_DISPLAY_V4
        feature_map = _EXIT_REASON_FEATURE_V4
        sentence_map = _EXIT_REASON_SENTENCE_V4

    if normalized in sentence_map:
        sentence = sentence_map[normalized]
    elif normalized in exact_map:
        sentence = exact_map[normalized]
    else:
        tokens = [token for token in normalized.split("_") if token][:4]
        translated = [feature_map.get(token, token) for token in tokens]
        sentence = " / ".join(translated) if translated else raw

    tokens = [token for token in normalized.split("_") if token][:4]
    feature_labels = [feature_map.get(token, token) for token in tokens]
    feature_labels = [label for label in feature_labels if label and label != sentence]
    if feature_labels:
        return f"{sentence} ({', '.join(feature_labels)})"
    return sentence


def _build_reason_top_lines_v4(
    scoped: pd.DataFrame,
    column_name: str,
    *,
    reason_kind: str,
    limit: int = 5,
) -> list[str]:
    if scoped.empty or column_name not in scoped.columns:
        return []
    working = scoped.copy()
    working["_reason_value"] = working[column_name].fillna("").astype(str).str.strip()
    working = working[working["_reason_value"] != ""].copy()
    if working.empty:
        return []

    summary = (
        working.groupby("_reason_value", dropna=False)
        .agg(
            count=("realized_pnl", "size"),
            net_pnl=("realized_pnl", "sum"),
            win_count=("realized_pnl", lambda series: int((series > 0).sum())),
        )
        .sort_values(["count", "net_pnl"], ascending=[False, False])
        .head(limit)
    )

    total = int(summary["count"].sum()) if not summary.empty else 0
    lines: list[str] = []
    for reason_value, row in summary.iterrows():
        count = int(row["count"])
        share = (count / total) if total else 0.0
        win_rate = (int(row["win_count"]) / count) if count else 0.0
        lines.append(
            f"- {_format_reason_display_v4(reason_value, reason_kind=reason_kind)} | {count}건 | "
            f"비중 {_fmt_pct(share)} | 승률 {_fmt_pct(win_rate)} | 순손익 {_fmt_money(float(row['net_pnl']))}"
        )
    return lines


def _estimate_window_balance_lines_v4(
    prepared_frame: pd.DataFrame,
    scoped_frame: pd.DataFrame,
    *,
    end: datetime,
    current_balance: float | None,
) -> list[str]:
    if current_balance is None:
        return ["잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다."]

    future_pnl = 0.0
    if not prepared_frame.empty:
        future_scope = prepared_frame[prepared_frame["close_dt"] >= end]
        future_pnl = float(_safe_numeric_series(future_scope, "realized_pnl").sum()) if not future_scope.empty else 0.0
    window_pnl = float(_safe_numeric_series(scoped_frame, "realized_pnl").sum()) if not scoped_frame.empty else 0.0
    end_balance = float(current_balance) - future_pnl
    start_balance = end_balance - window_pnl
    return [
        f"구간 시작 잔고(추정): {_fmt_unsigned_money(start_balance)}",
        f"구간 종료 잔고(추정): {_fmt_unsigned_money(end_balance)}",
        "잔고 기준: 현재 계좌 잔고에서 이후 실현손익을 역산한 추정치입니다.",
    ]


def build_pnl_digest_message(
    window_code: str,
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None = None,
) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()

    net_pnl_sum = float(_safe_numeric_series(scoped, "realized_pnl").sum()) if not scoped.empty else 0.0
    gross_pnl_sum = float(_safe_numeric_series(scoped, "gross_pnl").sum()) if not scoped.empty else net_pnl_sum
    total_cost = float(_safe_numeric_series(scoped, "cost_total").sum()) if not scoped.empty else 0.0
    total_lot = float(_safe_numeric_series(scoped, "lot").sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    entries = trades
    wins = int((_safe_numeric_series(scoped, "realized_pnl") > 0).sum()) if trades else 0
    losses = int((_safe_numeric_series(scoped, "realized_pnl") < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0

    entry_reason_lines = _build_reason_top_lines_v4(scoped, "entry_reason", reason_kind="entry", limit=5)
    exit_reason_lines = _build_reason_top_lines_v4(scoped, "exit_reason", reason_kind="exit", limit=5)
    balance_lines = _estimate_window_balance_lines_v4(
        frame,
        scoped,
        end=end,
        current_balance=current_balance,
    )

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"순손익 합계: {_fmt_money(net_pnl_sum)}",
        f"총손익(비용 전): {_fmt_money(gross_pnl_sum)}",
        f"총 비용: {_fmt_unsigned_money(abs(total_cost))}",
        f"진입 횟수(마감 기준): {entries}회",
        f"총 진입 랏: {_fmt_lot(total_lot)}",
        f"승/패: {wins} / {losses} (승률 {_fmt_pct(win_rate)})",
    ]
    lines.extend(balance_lines)

    if entry_reason_lines:
        lines.append("진입 사유 TOP 5:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("청산 사유 TOP 5:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("메모: 이 구간에 마감된 거래가 없어 손익과 사유 통계가 비어 있습니다.")
    lines.append(f"기준 시각: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)


_ENTRY_REASON_EXACT_KO_LABELS_V3 = {
    "reclaim": "리클레임 진입",
    "breakout": "돌파 진입",
    "probe": "탐색 진입",
    "retest": "재테스트 진입",
    "bounce": "반등 진입",
    "late": "지연 진입",
    "pullback": "눌림 진입",
    "continuation": "지속 진입",
    "reversal": "반전 진입",
}

_EXIT_REASON_EXACT_KO_LABELS_V3 = {
    "target": "목표가 청산",
    "runner": "러너 청산",
    "stop": "손절 청산",
    "cut": "컷 청산",
    "timeout": "시간 청산",
    "trail": "추적 청산",
    "partial_exit": "부분 청산",
    "full_exit": "전량 청산",
}

_ENTRY_REASON_TOKEN_KO_LABELS_V3 = {
    "flat": "플랫",
    "reclaim": "리클레임",
    "reentry": "재진입",
    "ready": "준비",
    "breakout": "돌파",
    "retest": "재테스트",
    "probe": "탐색",
    "bounce": "반등",
    "pullback": "눌림",
    "continuation": "지속",
    "trend": "추세",
    "reversal": "반전",
    "entry": "진입",
    "long": "매수",
    "short": "매도",
}

_EXIT_REASON_TOKEN_KO_LABELS_V3 = {
    "target": "목표가",
    "runner": "러너",
    "stop": "손절",
    "timeout": "시간만료",
    "cut": "컷",
    "trail": "추적",
    "shock": "충격",
    "protective": "보호",
    "loss": "손실",
    "profit": "수익",
    "hold": "보유",
    "wait": "대기",
    "exit": "청산",
    "partial": "부분",
    "full": "전량",
    "reverse": "반전",
}


def _humanize_reason_label_v3(value: object, *, reason_kind: str) -> str:
    raw = _safe_text(value)
    if not raw:
        return "-"
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if reason_kind == "entry":
        exact_map = _ENTRY_REASON_EXACT_KO_LABELS_V3
        token_map = _ENTRY_REASON_TOKEN_KO_LABELS_V3
    else:
        exact_map = _EXIT_REASON_EXACT_KO_LABELS_V3
        token_map = _EXIT_REASON_TOKEN_KO_LABELS_V3
    if normalized in exact_map:
        return exact_map[normalized]
    tokens = [token for token in normalized.split("_") if token][:4]
    translated = [token_map.get(token, token) for token in tokens]
    joined = " / ".join(translated).strip()
    if not joined:
        return raw
    if joined == raw:
        return joined
    return f"{joined} [{raw[:36]}]"


def _build_reason_top_lines_v3(
    scoped: pd.DataFrame,
    column_name: str,
    *,
    reason_kind: str,
    limit: int = 5,
) -> list[str]:
    if scoped.empty or column_name not in scoped.columns:
        return []
    working = scoped.copy()
    working["_reason_value"] = working[column_name].fillna("").astype(str).str.strip()
    working = working[working["_reason_value"] != ""].copy()
    if working.empty:
        return []

    summary = (
        working.groupby("_reason_value", dropna=False)
        .agg(
            count=("realized_pnl", "size"),
            net_pnl=("realized_pnl", "sum"),
            win_count=("realized_pnl", lambda series: int((series > 0).sum())),
        )
        .sort_values(["count", "net_pnl"], ascending=[False, False])
        .head(limit)
    )

    total = int(summary["count"].sum()) if not summary.empty else 0
    lines: list[str] = []
    for reason_value, row in summary.iterrows():
        count = int(row["count"])
        share = (count / total) if total else 0.0
        win_rate = (int(row["win_count"]) / count) if count else 0.0
        lines.append(
            f"- {_humanize_reason_label_v3(reason_value, reason_kind=reason_kind)} | {count}건 | "
            f"비중 {_fmt_pct(share)} | 승률 {_fmt_pct(win_rate)} | 순손익 {_fmt_money(float(row['net_pnl']))}"
        )
    return lines


def _estimate_window_balance_lines_v3(
    prepared_frame: pd.DataFrame,
    scoped_frame: pd.DataFrame,
    *,
    end: datetime,
    current_balance: float | None,
) -> list[str]:
    if current_balance is None:
        return ["잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다."]

    future_pnl = 0.0
    if not prepared_frame.empty:
        future_scope = prepared_frame[prepared_frame["close_dt"] >= end]
        future_pnl = float(_safe_numeric_series(future_scope, "realized_pnl").sum()) if not future_scope.empty else 0.0
    window_pnl = float(_safe_numeric_series(scoped_frame, "realized_pnl").sum()) if not scoped_frame.empty else 0.0
    end_balance = float(current_balance) - future_pnl
    start_balance = end_balance - window_pnl
    return [
        f"구간 시작 잔고(추정): {_fmt_unsigned_money(start_balance)}",
        f"구간 종료 잔고(추정): {_fmt_unsigned_money(end_balance)}",
        "잔고 기준: 현재 계좌 잔고에서 이후 실현손익을 역산한 추정치입니다.",
    ]


def build_pnl_digest_message(
    window_code: str,
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None = None,
) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()

    net_pnl_sum = float(_safe_numeric_series(scoped, "realized_pnl").sum()) if not scoped.empty else 0.0
    gross_pnl_sum = float(_safe_numeric_series(scoped, "gross_pnl").sum()) if not scoped.empty else net_pnl_sum
    total_cost = float(_safe_numeric_series(scoped, "cost_total").sum()) if not scoped.empty else 0.0
    total_lot = float(_safe_numeric_series(scoped, "lot").sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    entries = trades
    wins = int((_safe_numeric_series(scoped, "realized_pnl") > 0).sum()) if trades else 0
    losses = int((_safe_numeric_series(scoped, "realized_pnl") < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0

    entry_reason_lines = _build_reason_top_lines_v3(scoped, "entry_reason", reason_kind="entry", limit=5)
    exit_reason_lines = _build_reason_top_lines_v3(scoped, "exit_reason", reason_kind="exit", limit=5)
    balance_lines = _estimate_window_balance_lines_v3(
        frame,
        scoped,
        end=end,
        current_balance=current_balance,
    )

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"순손익 합계: {_fmt_money(net_pnl_sum)}",
        f"총손익(비용 전): {_fmt_money(gross_pnl_sum)}",
        f"총 비용: {_fmt_unsigned_money(abs(total_cost))}",
        f"진입 횟수(마감 기준): {entries}회",
        f"총 진입 랏: {_fmt_lot(total_lot)}",
        f"승/패: {wins} / {losses} (승률 {_fmt_pct(win_rate)})",
    ]
    lines.extend(balance_lines)

    if entry_reason_lines:
        lines.append("진입 사유 TOP 5:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("청산 사유 TOP 5:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("메모: 이 구간에 마감된 거래가 없어 손익과 사유 통계가 비어 있습니다.")
    lines.append(f"기준 시각: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)


def _strength_from_confidence(confidence: float) -> str:
    if confidence >= 0.78:
        return "HIGH"
    if confidence >= 0.58:
        return "MEDIUM"
    return "LOW"


def _priority_icon(kind: str, strength: str) -> str:
    if kind == "EXIT" and strength == "HIGH":
        return "🔴"
    if strength == "HIGH":
        return "🟡"
    return "🔵"


def _card_deadline(generated_at: datetime, kind: str) -> datetime:
    if kind == "EXIT":
        return generated_at + timedelta(minutes=5)
    if kind == "MANAGE":
        return generated_at + timedelta(minutes=10)
    return generated_at + timedelta(minutes=15)


def build_check_candidate_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    payload = dict(row or {})
    management_action = _safe_text(payload.get("management_action_label")).upper()
    position_side = _safe_text(payload.get("position_side"), "FLAT").upper()
    if management_action not in TELEGRAM_CHECK_ACTION_MAP:
        return None
    if position_side == "FLAT" and management_action != "REBUY":
        return None
    if position_side != "FLAT" and management_action == "REBUY":
        return None
    kind, recommended_action, recommended_note = TELEGRAM_CHECK_ACTION_MAP[management_action]
    confidence = _safe_float(payload.get("management_action_confidence"), 0.0)
    strength = _strength_from_confidence(confidence)
    evidence_quality = _strength_from_confidence(max(confidence - 0.08, 0.0))
    symbol = _safe_text(payload.get("symbol")).upper()
    direction = _safe_text(payload.get("observe_side") or payload.get("action") or payload.get("leg_direction")).upper()
    generated_at = _to_kst_datetime(payload.get("generated_at")) or _now_kst()
    checkpoint_id = _safe_text(payload.get("checkpoint_id"))
    checkpoint_type = _safe_text(payload.get("checkpoint_type")).upper()
    coarse_family = _safe_text(payload.get("runtime_scene_coarse_family"))
    fine_label = _safe_text(payload.get("runtime_scene_fine_label"))
    management_reason = _safe_text(payload.get("management_action_reason"))
    blocked_by = _safe_text(payload.get("blocked_by"))
    current_profit = _safe_float(payload.get("current_profit"), 0.0)
    giveback_ratio = _safe_float(payload.get("giveback_ratio"), 0.0)
    unrealized_pnl_state = _safe_text(payload.get("unrealized_pnl_state")).upper()
    surface_name = _safe_text(payload.get("surface_name"))
    score_reason = _safe_text(payload.get("runtime_score_reason"))
    decision_deadline = _card_deadline(generated_at, kind)
    trigger_summary = _safe_text(
        payload.get("checkpoint_transition_reason")
        or management_reason
        or surface_name
        or checkpoint_type
    )
    approval_key = "|".join([symbol, checkpoint_id, checkpoint_type, management_action, position_side, direction])
    card_id = hashlib.sha1(f"{approval_key}|{generated_at.isoformat()}".encode("utf-8")).hexdigest()[:16]
    evidence_lines: list[str] = []
    if checkpoint_type:
        evidence_lines.append(f"checkpoint: {checkpoint_type}")
    if surface_name:
        evidence_lines.append(f"surface: {surface_name}")
    if fine_label or coarse_family:
        evidence_lines.append(f"scene: {fine_label or coarse_family}")
    if management_reason:
        evidence_lines.append(f"reason: {management_reason}")
    elif score_reason:
        evidence_lines.append(f"reason: {score_reason}")
    risk_lines: list[str] = []
    if unrealized_pnl_state == "OPEN_LOSS":
        risk_lines.append("open loss 상태")
    if giveback_ratio > 0.0:
        risk_lines.append(f"giveback: {_fmt_pct(giveback_ratio)}")
    if current_profit < 0.0:
        risk_lines.append(f"current profit: {_fmt_money(current_profit)}")
    if blocked_by:
        risk_lines.append(f"blocked_by: {blocked_by}")
    if not risk_lines:
        risk_lines.append("즉시 리스크 메모 없음")
    return {
        "card_id": card_id,
        "approval_key": approval_key,
        "status": "PENDING",
        "kind": kind,
        "priority_icon": _priority_icon(kind, strength),
        "symbol": symbol,
        "direction": direction or ("BUY" if position_side == "FLAT" else position_side),
        "checkpoint_id": checkpoint_id,
        "checkpoint_type": checkpoint_type,
        "scene_family": coarse_family,
        "scene_label": fine_label,
        "recommended_action": recommended_action,
        "recommended_action_note": recommended_note,
        "action_strength": strength,
        "evidence_quality": evidence_quality,
        "trigger_summary": trigger_summary,
        "scope_note": "이번 checkpoint 1건 기준",
        "decision_deadline_ts": decision_deadline.isoformat(),
        "generated_at": generated_at.isoformat(),
        "management_action_label": management_action,
        "management_action_confidence": confidence,
        "management_action_reason": management_reason,
        "current_profit": current_profit,
        "giveback_ratio": giveback_ratio,
        "position_side": position_side,
        "ticket": _safe_int(payload.get("ticket"), 0),
        "evidence_lines": evidence_lines[:4],
        "risk_lines": risk_lines[:4],
        "leg_id": _safe_text(payload.get("leg_id")),
    }


def build_check_card_text(
    card: dict[str, Any],
    *,
    status_override: str | None = None,
    decision_meta: dict[str, Any] | None = None,
) -> str:
    payload = dict(card or {})
    status = _safe_text(status_override or payload.get("status"), "PENDING").upper()
    decision = dict(decision_meta or {})
    lines = [
        f"{_safe_text(payload.get('priority_icon'), '🔵')} {payload.get('recommended_action', 'WAIT')} ({payload.get('action_strength', 'LOW')}) | {payload.get('kind', 'CHECK')} | {status}",
        f"{payload.get('symbol', '')} {payload.get('direction', '')} | {payload.get('checkpoint_type', '')}",
    ]
    scene_label = _safe_text(payload.get("scene_label") or payload.get("scene_family"))
    if scene_label:
        lines.append(f"scene: {scene_label}")
    lines.append(f"trigger: {payload.get('trigger_summary', '')}")
    lines.append("근거:")
    for line in list(payload.get("evidence_lines", []) or []):
        lines.append(f"- {line}")
    lines.append("리스크:")
    for line in list(payload.get("risk_lines", []) or []):
        lines.append(f"- {line}")
    lines.append("운영:")
    lines.append(f"- note: {payload.get('recommended_action_note', '')}")
    lines.append(f"- evidence quality: {payload.get('evidence_quality', 'LOW')}")
    lines.append(f"- scope: {payload.get('scope_note', '')}")
    lines.append(f"- deadline: {_safe_text(payload.get('decision_deadline_ts'))}")
    if status in {"APPROVED", "REJECTED", "HELD"}:
        lines.append("처리:")
        lines.append(f"- by: {_safe_text(decision.get('decided_by_label') or payload.get('decided_by_label'), 'unknown')}")
        lines.append(f"- at: {_safe_text(decision.get('decided_at') or payload.get('decided_at'))}")
    return "\n".join(lines)


def build_check_reply_markup(card_id: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "승인", "callback_data": f"tgops:approve:{card_id}"},
                {"text": "거부", "callback_data": f"tgops:reject:{card_id}"},
                {"text": "보류", "callback_data": f"tgops:hold:{card_id}"},
            ]
        ]
    }


class TelegramOpsService:
    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        checkpoint_rows_path: str | Path | None = None,
    ):
        self.state_path = Path(state_path or default_telegram_ops_state_path())
        self.decision_log_path = default_telegram_ops_decision_log_path()
        self.checkpoint_rows_path = Path(checkpoint_rows_path or default_checkpoint_rows_path())
        self.enabled = bool(getattr(Config, "TG_OPS_ENABLED", True) and getattr(Config, "TG_TOKEN", ""))
        self.callback_poll_sec = max(1.0, _safe_float(getattr(Config, "TG_OPS_CALLBACK_POLL_SEC", 2.0), 2.0))
        self.pnl_scan_sec = max(5.0, _safe_float(getattr(Config, "TG_OPS_PNL_SCAN_SEC", 15.0), 15.0))
        self.check_scan_sec = max(2.0, _safe_float(getattr(Config, "TG_OPS_CHECK_SCAN_SEC", 5.0), 5.0))
        self.bootstrap_enabled = bool(getattr(Config, "TG_OPS_BOOTSTRAP_ENABLED", True))
        self.check_max_pending = max(1, _safe_int(getattr(Config, "TG_OPS_CHECK_MAX_PENDING", 5), 5))
        self.check_min_confidence = _safe_float(getattr(Config, "TG_OPS_CHECK_MIN_CONFIDENCE", 0.58), 0.58)
        self.live_check_approvals_enabled = bool(
            getattr(Config, "TG_OPS_LIVE_CHECK_APPROVALS_ENABLED", False)
        )
        self.state = self._load_state()
        self._last_callback_poll_at = 0.0
        self._last_pnl_scan_at = 0.0
        self._last_check_scan_at = 0.0
        self._checkpoint_improvement_runtime: CheckpointImprovementTelegramRuntime | None = None

    def _default_state(self) -> dict[str, Any]:
        return {
            "contract_version": TELEGRAM_OPS_STATE_CONTRACT_VERSION,
            "updated_at": "",
            "bootstrap_sent_versions": [],
            "telegram_update_offset": 0,
            "pnl_last_sent": {},
            "checkpoint_last_signature": "",
            "checkpoint_seen_signatures": [],
            "check_cards": {},
            "latest_detect_issue_refs": {},
            "latest_detect_result": {},
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            state = self._default_state()
            state.update(payload if isinstance(payload, dict) else {})
            if not isinstance(state.get("check_cards"), dict):
                state["check_cards"] = {}
            if not isinstance(state.get("pnl_last_sent"), dict):
                state["pnl_last_sent"] = {}
            if not isinstance(state.get("checkpoint_seen_signatures"), list):
                state["checkpoint_seen_signatures"] = []
            if not isinstance(state.get("bootstrap_sent_versions"), list):
                state["bootstrap_sent_versions"] = []
            if not isinstance(state.get("latest_detect_issue_refs"), dict):
                state["latest_detect_issue_refs"] = {}
            if not isinstance(state.get("latest_detect_result"), dict):
                state["latest_detect_result"] = {}
            return state
        except Exception:
            logger.exception("Failed to load telegram ops state: %s", self.state_path)
            return self._default_state()

    def _save_state(self) -> None:
        self.state["updated_at"] = _now_kst().isoformat()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_decision_log(self, record: dict[str, Any]) -> None:
        self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.decision_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _current_pending_cards(self) -> list[dict[str, Any]]:
        cards = []
        for payload in dict(self.state.get("check_cards", {}) or {}).values():
            card = dict(payload or {})
            if _safe_text(card.get("status")).upper() == "PENDING":
                cards.append(card)
        return cards

    def _cleanup_card_state(self) -> None:
        check_cards = dict(self.state.get("check_cards", {}) or {})
        recent_items = sorted(
            check_cards.items(),
            key=lambda item: _safe_text((item[1] or {}).get("generated_at")),
            reverse=True,
        )
        trimmed = recent_items[:100]
        self.state["check_cards"] = {key: value for key, value in trimmed}
        seen = list(self.state.get("checkpoint_seen_signatures", []) or [])
        self.state["checkpoint_seen_signatures"] = seen[-300:]

    def _ensure_checkpoint_improvement_runtime(self) -> CheckpointImprovementTelegramRuntime:
        if self._checkpoint_improvement_runtime is None:
            self._checkpoint_improvement_runtime = build_checkpoint_improvement_telegram_runtime()
        return self._checkpoint_improvement_runtime

    def _bootstrap_test_messages(self) -> None:
        if not self.bootstrap_enabled:
            return
        sent_versions = list(self.state.get("bootstrap_sent_versions", []) or [])
        if TELEGRAM_OPS_BOOTSTRAP_VERSION in sent_versions:
            return
        runtime_msg = "[telegram ops bootstrap]\nroute: runtime DM\nstatus: ready"
        check_msg = "[telegram ops bootstrap]\nroute: check room\nstatus: ready"
        report_msg = "[telegram ops bootstrap]\nroute: pnl/report room\nwindow: 15m\nstatus: ready"
        validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="runtime")
        validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="check")
        validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="report")
        notifier.send_runtime_telegram(runtime_msg)
        notifier.send_check_telegram(check_msg, parse_mode=None)
        notifier.send_report_telegram(report_msg, parse_mode=None)
        sent_versions.append(TELEGRAM_OPS_BOOTSTRAP_VERSION)
        self.state["bootstrap_sent_versions"] = sent_versions[-12:]
        self._save_state()

    def _read_closed_trade_frame(self, trade_logger) -> pd.DataFrame:
        reader = getattr(trade_logger, "read_closed_df", None)
        if callable(reader):
            try:
                return reader()
            except Exception:
                logger.exception("Failed to read closed trade frame for telegram PnL")
                return pd.DataFrame()
        return pd.DataFrame()

    def _emit_due_pnl(self, trade_logger) -> None:
        closed_frame = self._read_closed_trade_frame(trade_logger)
        current_balance = self._resolve_current_account_balance(trade_logger)
        pnl_last_sent = dict(self.state.get("pnl_last_sent", {}) or {})
        state_changed = False
        for window_code in TELEGRAM_PNL_WINDOWS:
            start, end, bucket_key = resolve_completed_window(window_code)
            if _safe_text(pnl_last_sent.get(window_code)) == bucket_key:
                continue
            system_status_lines = self._build_daily_readiness_digest_lines(window_code)
            lesson_lines = self._build_daily_lesson_lines(
                window_code,
                closed_frame=closed_frame,
                start=start,
                end=end,
            )
            message = build_telegram_pnl_digest_message(
                window_code,
                closed_frame,
                start=start,
                end=end,
                current_balance=current_balance,
                timezone=KST,
                system_status_lines=system_status_lines,
            )
            if lesson_lines:
                message = "\n".join([message, *lesson_lines])
            validate_telegram_route_ownership(owner_key=OWNER_PNL_DIGEST, route="pnl")
            ok = notifier.send_pnl_telegram(window_code, message, parse_mode=None)
            if ok:
                pnl_last_sent[window_code] = bucket_key
                state_changed = True
        if state_changed:
            self.state["pnl_last_sent"] = pnl_last_sent
            self._save_state()

    def _build_daily_readiness_digest_lines(self, window_code: str) -> list[str]:
        if _safe_text(window_code).upper() != "1D":
            return []
        board_path = default_checkpoint_improvement_master_board_json_path()
        if not board_path.exists():
            return []
        try:
            payload = json.loads(board_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to read master board for daily readiness digest")
            return []
        readiness_state = dict(payload.get("readiness_state") or {})
        if not readiness_state:
            return []
        return build_pnl_readiness_digest_lines(readiness_state)

    def _build_daily_lesson_lines(
        self,
        window_code: str,
        *,
        closed_frame: pd.DataFrame | None,
        start: datetime,
        end: datetime,
    ) -> list[str]:
        if _safe_text(window_code).upper() != "1D":
            return []
        try:
            return build_pnl_lesson_comment_lines(
                closed_frame,
                start=start,
                end=end,
                timezone=KST,
            )
        except Exception:
            logger.exception("Failed to build daily lesson lines")
            return []

    def _resolve_current_account_balance(self, trade_logger) -> float | None:
        try:
            from backend.services.mt5_snapshot_service import Mt5SnapshotService

            trade_csv_path = Path(getattr(trade_logger, "filepath", "") or "").resolve()
            if not trade_csv_path.name:
                trade_csv_path = (_repo_root() / "data" / "trades" / "trade_history.csv").resolve()
            snapshot_service = Mt5SnapshotService(trade_csv=trade_csv_path, trade_logger=trade_logger)
            mt5_status = snapshot_service.get_mt5_status()
            account = dict(mt5_status.get("account") or {})
            balance = account.get("balance")
            if balance in (None, ""):
                balance = account.get("equity")
            if balance in (None, ""):
                return None
            return _safe_float(balance, 0.0)
        except Exception:
            logger.debug("Failed to resolve current account balance for Telegram PnL digest", exc_info=True)
            return None

    def _load_checkpoint_frame(self) -> pd.DataFrame:
        if not self.checkpoint_rows_path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(self.checkpoint_rows_path, encoding="utf-8-sig")
        except Exception:
            logger.exception("Failed to load checkpoint rows for telegram ops: %s", self.checkpoint_rows_path)
            return pd.DataFrame()

    def _row_signature(self, row: dict[str, Any]) -> str:
        token = "|".join(
            [
                _safe_text(row.get("generated_at")),
                _safe_text(row.get("symbol")).upper(),
                _safe_text(row.get("checkpoint_id")),
                _safe_text(row.get("checkpoint_type")).upper(),
                _safe_text(row.get("management_action_label")).upper(),
                _safe_text(row.get("source")),
                _safe_text(row.get("outcome")),
                _safe_text(row.get("ticket")),
            ]
        )
        return hashlib.sha1(token.encode("utf-8")).hexdigest()[:24]

    def _can_send_check_candidate(self, candidate: dict[str, Any]) -> bool:
        if _safe_float(candidate.get("management_action_confidence"), 0.0) < float(self.check_min_confidence):
            return False
        if len(self._current_pending_cards()) >= int(self.check_max_pending):
            return False
        approval_key = _safe_text(candidate.get("approval_key"))
        for card in dict(self.state.get("check_cards", {}) or {}).values():
            existing = dict(card or {})
            if _safe_text(existing.get("approval_key")) != approval_key:
                continue
            if _safe_text(existing.get("status")).upper() == "PENDING":
                return False
        return True

    def _send_check_card(self, candidate: dict[str, Any]) -> bool:
        card_text = build_check_card_text(candidate)
        validate_telegram_route_ownership(
            owner_key=OWNER_LEGACY_LIVE_CHECK_CARD,
            route="check",
        )
        response = notifier.send_telegram_sync(
            card_text,
            route="check",
            parse_mode=None,
            reply_markup=build_check_reply_markup(_safe_text(candidate.get("card_id"))),
        )
        result = dict((response or {}).get("result", {}) or {})
        message_id = _safe_int(result.get("message_id"), 0)
        if message_id <= 0:
            return False
        candidate["chat_id"] = _safe_text(((result.get("chat") or {}).get("id")))
        candidate["message_id"] = message_id
        candidate["thread_id"] = _safe_int(result.get("message_thread_id"), 0)
        candidate["rendered_text"] = card_text
        self.state.setdefault("check_cards", {})[_safe_text(candidate.get("card_id"))] = candidate
        return True

    def _scan_checkpoint_cards(self) -> None:
        if not self.live_check_approvals_enabled:
            return
        frame = self._load_checkpoint_frame()
        if frame.empty:
            return
        frame = frame.tail(200).copy()
        rows = frame.to_dict(orient="records")
        signatures = [self._row_signature(dict(row or {})) for row in rows]
        last_signature = _safe_text(self.state.get("checkpoint_last_signature"))
        seen_signatures = set(self.state.get("checkpoint_seen_signatures", []) or [])
        if not last_signature:
            self.state["checkpoint_last_signature"] = signatures[-1] if signatures else ""
            self.state["checkpoint_seen_signatures"] = list(signatures[-50:])
            self._save_state()
            return
        start_index = 0
        if last_signature in signatures:
            start_index = signatures.index(last_signature) + 1
        pending_rows = rows[start_index:]
        pending_signatures = signatures[start_index:]
        state_changed = False
        for row, signature in zip(pending_rows, pending_signatures):
            if signature in seen_signatures:
                continue
            candidate = build_check_candidate_from_row(dict(row or {}))
            seen_signatures.add(signature)
            if candidate is None:
                continue
            if not self._can_send_check_candidate(candidate):
                continue
            if self._send_check_card(candidate):
                state_changed = True
        if signatures:
            self.state["checkpoint_last_signature"] = signatures[-1]
        self.state["checkpoint_seen_signatures"] = list(seen_signatures)[-300:]
        if state_changed:
            self._cleanup_card_state()
        self._save_state()

    def _parse_callback_data(self, callback_data: str) -> tuple[str, str] | None:
        text = _safe_text(callback_data)
        parts = text.split(":", 2)
        if len(parts) != 3 or parts[0] != "tgops":
            return None
        decision = parts[1].lower()
        card_id = parts[2]
        if decision not in TELEGRAM_CHECK_DECISIONS:
            return None
        return decision, card_id

    def _is_bridge_callback(self, callback_data: str) -> bool:
        return _safe_text(callback_data).startswith("tgbridge:")

    def _is_allowed_user(self, user_id: int) -> bool:
        allowed = tuple(getattr(Config, "TG_ALLOWED_USER_IDS", ()) or ())
        if not allowed:
            return True
        return int(user_id) in {int(item) for item in allowed}

    def _handle_callback_query(self, callback_query: dict[str, Any]) -> bool:
        callback_id = _safe_text(callback_query.get("id"))
        callback_data = _safe_text(callback_query.get("data"))
        parsed = self._parse_callback_data(callback_data)
        if parsed is None and self._is_bridge_callback(callback_data):
            runtime = self._ensure_checkpoint_improvement_runtime()
            result = runtime.telegram_update_poller.handle_callback_query(callback_query)
            return _to_bool(dict(result.get("summary") or {}).get("handled"), False)
        if parsed is None:
            notifier.answer_callback_query(callback_id, text="지원하지 않는 버튼입니다.")
            return False
        if not self.live_check_approvals_enabled:
            notifier.answer_callback_query(
                callback_id,
                text="live execution approval route is disabled",
                show_alert=True,
            )
            return False
        decision, card_id = parsed
        from_user = dict(callback_query.get("from") or {})
        user_id = _safe_int(from_user.get("id"), 0)
        user_label = _safe_text(from_user.get("username")) or _safe_text(from_user.get("first_name")) or str(user_id)
        if user_label and not user_label.startswith("@") and _safe_text(from_user.get("username")):
            user_label = f"@{user_label}"
        if not self._is_allowed_user(user_id):
            notifier.answer_callback_query(callback_id, text="이 버튼 권한이 없습니다.", show_alert=True)
            return False

        cards = dict(self.state.get("check_cards", {}) or {})
        card = dict(cards.get(card_id, {}) or {})
        if not card:
            notifier.answer_callback_query(callback_id, text="이미 만료되었거나 찾을 수 없습니다.")
            return False

        current_status = _safe_text(card.get("status"), "PENDING").upper()
        if current_status != "PENDING":
            notifier.answer_callback_query(callback_id, text=f"이미 {current_status} 처리되었습니다.")
            return False

        resolved_status = TELEGRAM_CHECK_DECISIONS[decision]
        decided_at = _now_kst().isoformat()
        card["status"] = resolved_status
        card["decision"] = decision.upper()
        card["decided_by_user_id"] = user_id
        card["decided_by_label"] = user_label
        card["decided_at"] = decided_at
        cards[card_id] = card
        self.state["check_cards"] = cards

        edited_text = build_check_card_text(
            card,
            status_override=resolved_status,
            decision_meta={"decided_by_label": user_label, "decided_at": decided_at},
        )
        notifier.edit_telegram_message_text(
            chat_id=_safe_text(card.get("chat_id")),
            message_id=_safe_int(card.get("message_id"), 0),
            text=edited_text,
            thread_id=_safe_int(card.get("thread_id"), 0),
            parse_mode=None,
        )
        notifier.answer_callback_query(callback_id, text=f"{resolved_status} 처리되었습니다.")
        self._append_decision_log(
            {
                "contract_version": TELEGRAM_OPS_STATE_CONTRACT_VERSION,
                "card_id": card_id,
                "decision": decision.upper(),
                "status": resolved_status,
                "decided_at": decided_at,
                "decided_by_user_id": user_id,
                "decided_by_label": user_label,
                "checkpoint_id": _safe_text(card.get("checkpoint_id")),
                "symbol": _safe_text(card.get("symbol")),
                "recommended_action": _safe_text(card.get("recommended_action")),
            }
        )
        self._cleanup_card_state()
        self._save_state()
        return True

    def _parse_message_command(self, message: dict[str, Any]) -> dict[str, Any] | None:
        text = _safe_text(message.get("text") or message.get("caption"))
        if not text.startswith("/"):
            return None
        first_token, *rest = text.split()
        normalized = first_token.split("@", 1)[0].lower()
        if normalized == MANUAL_PROPOSE_COMMAND:
            recent_trade_limit = DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT
            if rest:
                try:
                    recent_trade_limit = max(10, min(200, int(rest[0])))
                except Exception:
                    recent_trade_limit = DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT
            return {
                "command": "propose",
                "recent_trade_limit": recent_trade_limit,
            }
        if normalized == MANUAL_DETECT_COMMAND:
            recent_trade_limit = DEFAULT_DETECT_RECENT_LIMIT
            if rest:
                try:
                    recent_trade_limit = max(10, min(200, int(rest[0])))
                except Exception:
                    recent_trade_limit = DEFAULT_DETECT_RECENT_LIMIT
            return {
                "command": "detect",
                "recent_trade_limit": recent_trade_limit,
            }
        if normalized == MANUAL_DETECT_FEEDBACK_COMMAND:
            issue_ref = _safe_text(rest[0]) if len(rest) >= 1 else ""
            verdict_token = _safe_text(rest[1]) if len(rest) >= 2 else ""
            note = " ".join(rest[2:]).strip() if len(rest) >= 3 else ""
            return {
                "command": "detect_feedback",
                "issue_ref": issue_ref,
                "verdict": verdict_token,
                "note": note,
            }
        return None

    def _send_message_command_reply(
        self,
        *,
        chat_id: str | int,
        thread_id: int | None,
        text: str,
    ) -> None:
        notifier.send_telegram_sync(
            text,
            chat_id=chat_id,
            thread_id=thread_id,
            parse_mode=None,
        )

    def _store_latest_detect_issue_refs(self, payload: dict[str, Any]) -> None:
        envelope = dict(payload.get("proposal_envelope") or {})
        latest_result = {
            "generated_at": _safe_text(payload.get("generated_at")),
            "proposal_id": _safe_text(envelope.get("proposal_id")),
            "summary_ko": _safe_text(envelope.get("summary_ko")),
            "readiness_status": _safe_text(envelope.get("readiness_status")),
            "surfaced_detector_count": _safe_int(payload.get("surfaced_detector_count"), 0),
            "feedback_issue_ref_count": len(list(payload.get("feedback_issue_refs") or [])),
        }
        self.state["latest_detect_result"] = latest_result

        refs = list(payload.get("feedback_issue_refs") or [])
        current_latest_refs = dict(self.state.get("latest_detect_issue_refs") or {})
        if refs:
            self.state["latest_detect_issue_refs"] = {
                "generated_at": latest_result["generated_at"],
                "proposal_id": latest_result["proposal_id"],
                "items": refs,
            }
        elif not current_latest_refs:
            self.state["latest_detect_issue_refs"] = {
                "generated_at": latest_result["generated_at"],
                "proposal_id": latest_result["proposal_id"],
                "items": [],
            }
        self._save_state()
        self._write_detector_feedback_snapshot_from_state()
        self._write_detector_feedback_confusion_snapshot_from_state()

    def _append_detector_feedback_entry(self, entry: dict[str, Any]) -> None:
        history = list(self.state.get("detect_feedback_history") or [])
        history.append(dict(entry))
        self.state["detect_feedback_history"] = history[-500:]
        self._save_state()

    def _write_detector_feedback_snapshot_from_state(self) -> dict[str, Any]:
        latest_refs_payload = dict(self.state.get("latest_detect_issue_refs") or {})
        payload = build_detector_feedback_snapshot(
            list(self.state.get("detect_feedback_history") or []),
            list(latest_refs_payload.get("items") or []),
            now_ts=_now_kst().isoformat(),
        )
        write_detector_feedback_snapshot(payload)
        return payload

    def _write_detector_feedback_confusion_snapshot_from_state(self) -> dict[str, Any]:
        latest_refs_payload = dict(self.state.get("latest_detect_issue_refs") or {})
        payload = build_detector_confusion_snapshot(
            list(self.state.get("detect_feedback_history") or []),
            list(latest_refs_payload.get("items") or []),
            now_ts=_now_kst().isoformat(),
        )
        write_detector_confusion_snapshot(payload)
        return payload

    def _detect_previous_snapshot_path(self) -> Path:
        return self.state_path.with_name("improvement_log_only_detector_latest.json")

    def _write_detect_previous_snapshot(self, payload: dict[str, Any]) -> None:
        path = self._detect_previous_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")

    def _format_detect_feedback_refs_reply(self, payload: dict[str, Any]) -> str:
        refs = list(payload.get("feedback_issue_refs") or [])
        if not refs:
            return "- 피드백 대상 detector 없음"
        lines = []
        for row in refs[:5]:
            row_map = dict(row or {})
            lines.append(
                f"- {_safe_text(row_map.get('feedback_ref'))}: {_safe_text(row_map.get('summary_ko'))}"
            )
        return "\n".join(lines)

    def _handle_detect_feedback_command(
        self,
        *,
        message: dict[str, Any],
        issue_ref: str,
        verdict: str,
        note: str,
    ) -> bool:
        chat = dict(message.get("chat") or {})
        thread_id = _safe_int(message.get("message_thread_id"), 0) or None
        normalized_verdict = normalize_detector_feedback_verdict(verdict)
        if not issue_ref or not normalized_verdict:
            self._send_message_command_reply(
                chat_id=_safe_text(chat.get("id")),
                thread_id=thread_id,
                text=(
                    "/detect_feedback 사용법:\n"
                    "- /detect_feedback D1 맞았음\n"
                    "- /detect_feedback D2 과민했음\n"
                    "- /detect_feedback D3 놓쳤음 메모\n"
                    "- verdict: 맞았음 / 과민했음 / 놓쳤음 / 애매함"
                ),
            )
            return True

        latest_refs_payload = dict(self.state.get("latest_detect_issue_refs") or {})
        latest_refs = list(latest_refs_payload.get("items") or [])
        issue = find_detect_issue_ref(latest_refs, issue_ref)
        if not issue:
            self._send_message_command_reply(
                chat_id=_safe_text(chat.get("id")),
                thread_id=thread_id,
                text="최근 /detect 기준으로 찾을 수 없는 detector 번호입니다. 먼저 /detect를 다시 실행해 주세요.",
            )
            return True

        from_user = dict(message.get("from") or {})
        username = _safe_text(from_user.get("username")) or _safe_text(from_user.get("first_name"))
        if username and _safe_text(from_user.get("username")) and not username.startswith("@"):
            username = f"@{username}"
        entry = build_detector_feedback_entry(
            issue_ref=issue,
            verdict=normalized_verdict,
            user_id=from_user.get("id"),
            username=username,
            note=note,
            proposal_id=latest_refs_payload.get("proposal_id"),
            now_ts=_now_kst().isoformat(),
        )
        self._append_detector_feedback_entry(entry)
        feedback_snapshot = self._write_detector_feedback_snapshot_from_state()
        confusion_snapshot = self._write_detector_feedback_confusion_snapshot_from_state()

        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_CHECK_INBOX, route="check")
        notifier.send_check_telegram(
            "\n".join(
                [
                    "[detector 피드백]",
                    f"대상: {_safe_text(issue.get('feedback_ref'))} / {_safe_text(issue.get('summary_ko'))}",
                    f"판정: {detector_feedback_verdict_label_ko(normalized_verdict)}",
                    f"누적 피드백: {_safe_int(feedback_snapshot.get('feedback_entry_count'), 0)}건",
                    (
                        f"confusion: 맞음 {_safe_int(dict(confusion_snapshot.get('verdict_totals') or {}).get('confirmed'), 0)} / "
                        f"과민 {_safe_int(dict(confusion_snapshot.get('verdict_totals') or {}).get('oversensitive'), 0)} / "
                        f"놓침 {_safe_int(dict(confusion_snapshot.get('verdict_totals') or {}).get('missed'), 0)}"
                    ),
                ]
            ),
            parse_mode=None,
        )

        self._send_message_command_reply(
            chat_id=_safe_text(chat.get("id")),
            thread_id=thread_id,
            text=(
                f"detector 피드백을 기록했습니다.\n"
                f"- 대상: {_safe_text(issue.get('feedback_ref'))} / {_safe_text(issue.get('summary_ko'))}\n"
                f"- 판정: {detector_feedback_verdict_label_ko(normalized_verdict)}\n"
                f"- 누적: {_safe_int(feedback_snapshot.get('feedback_entry_count'), 0)}건"
            ),
        )
        return True

    def _handle_propose_command(
        self,
        *,
        message: dict[str, Any],
        trade_logger,
        recent_trade_limit: int,
    ) -> bool:
        closed_frame = self._read_closed_trade_frame(trade_logger)
        payload = build_manual_trade_proposal_snapshot(
            closed_frame,
            recent_trade_limit=recent_trade_limit,
            timezone=KST,
            now_ts=_now_kst().isoformat(),
            detector_feedback_entries=list(self.state.get("detect_feedback_history") or []),
            detector_latest_issue_refs=list((self.state.get("latest_detect_issue_refs") or {}).get("items") or []),
        )
        write_manual_trade_proposal_snapshot(payload)

        envelope = dict(payload.get("proposal_envelope") or {})
        report_lines = list(payload.get("report_lines_ko") or [])
        report_message = "\n".join(
            [f"[{_safe_text(payload.get('report_title_ko'), '수동 제안 분석')}]", *[line for line in report_lines if _safe_text(line)]]
        )
        check_message = "\n".join(
            [
                _safe_text(payload.get("inbox_summary_ko"), "[수동 제안 분석]"),
                f"제안 상태: {_safe_text(envelope.get('proposal_stage'), '-')}",
                f"준비 상태: {_safe_text(envelope.get('readiness_status'), '-')}",
                f"요약: {_safe_text(envelope.get('summary_ko'), '-')}",
            ]
        )

        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_REPORT_TOPIC, route="report")
        notifier.send_report_telegram(report_message, parse_mode=None)
        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_CHECK_INBOX, route="check")
        notifier.send_check_telegram(check_message, parse_mode=None)

        chat = dict(message.get("chat") or {})
        self._send_message_command_reply(
            chat_id=_safe_text(chat.get("id")),
            thread_id=_safe_int(message.get("message_thread_id"), 0) or None,
            text=(
                f"/propose 분석을 체크/보고서 topic에 올렸습니다.\n"
                f"- 분석 거래 수: {_safe_int(payload.get('analyzed_trade_count'), 0)}건\n"
                f"- surface 문제 패턴: {len(list(payload.get('surfaced_problem_patterns') or []))}건\n"
                f"- feedback-aware 우선 검토: {_safe_int(payload.get('feedback_promotion_count'), 0)}건"
            ),
        )
        return True

    def _handle_detect_command(
        self,
        *,
        message: dict[str, Any],
        trade_logger,
        recent_trade_limit: int,
    ) -> bool:
        closed_frame = self._read_closed_trade_frame(trade_logger)
        payload = build_default_improvement_log_only_detector_snapshot(
            closed_frame=closed_frame,
            feedback_history=list(self.state.get("detect_feedback_history") or []),
            recent_trade_limit=recent_trade_limit,
            timezone=KST,
            now_ts=_now_kst().isoformat(),
            previous_snapshot_path=self._detect_previous_snapshot_path(),
        )
        write_improvement_log_only_detector_snapshot(payload)
        self._write_detect_previous_snapshot(payload)
        self._store_latest_detect_issue_refs(payload)

        envelope = dict(payload.get("proposal_envelope") or {})
        report_lines = list(payload.get("report_lines_ko") or [])
        report_message = "\n".join(
            [f"[{_safe_text(payload.get('report_title_ko'), 'log-only detector 관찰 보고')}]", *[line for line in report_lines if _safe_text(line)]]
        )
        check_message = "\n".join(
            [
                _safe_text(payload.get("inbox_summary_ko"), "[detector 관찰]"),
                f"단계: {_safe_text(envelope.get('proposal_stage'), '-')}",
                f"준비: {_safe_text(envelope.get('readiness_status'), '-')}",
                f"요약: {_safe_text(envelope.get('summary_ko'), '-')}",
            ]
        )

        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_REPORT_TOPIC, route="report")
        notifier.send_report_telegram(report_message, parse_mode=None)
        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_CHECK_INBOX, route="check")
        notifier.send_check_telegram(check_message, parse_mode=None)

        chat = dict(message.get("chat") or {})
        self._send_message_command_reply(
            chat_id=_safe_text(chat.get("id")),
            thread_id=_safe_int(message.get("message_thread_id"), 0) or None,
            text=(
                f"/detect 관찰 보고를 체크/보고서 topic에 올렸습니다.\n"
                f"- 분석 거래 수: {recent_trade_limit}건 기준\n"
                f"- surface detector: {_safe_int(payload.get('surfaced_detector_count'), 0)}건\n"
                f"{self._format_detect_feedback_refs_reply(payload)}\n"
                f"- 피드백 예시: /detect_feedback D1 맞았음"
            ),
        )
        return True

    def _handle_message_command(self, message: dict[str, Any], trade_logger) -> bool:
        parsed = self._parse_message_command(message)
        if parsed is None:
            return False
        from_user = dict(message.get("from") or {})
        user_id = _safe_int(from_user.get("id"), 0)
        chat = dict(message.get("chat") or {})
        thread_id = _safe_int(message.get("message_thread_id"), 0) or None
        if not self._is_allowed_user(user_id):
            self._send_message_command_reply(
                chat_id=_safe_text(chat.get("id")),
                thread_id=thread_id,
                text="이 명령을 실행할 권한이 없습니다.",
            )
            return True
        if _safe_text(parsed.get("command")) == "propose":
            return self._handle_propose_command(
                message=message,
                trade_logger=trade_logger,
                recent_trade_limit=_safe_int(parsed.get("recent_trade_limit"), DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT),
            )
        if _safe_text(parsed.get("command")) == "detect":
            return self._handle_detect_command(
                message=message,
                trade_logger=trade_logger,
                recent_trade_limit=_safe_int(parsed.get("recent_trade_limit"), DEFAULT_DETECT_RECENT_LIMIT),
            )
        if _safe_text(parsed.get("command")) == "detect_feedback":
            return self._handle_detect_feedback_command(
                message=message,
                issue_ref=_safe_text(parsed.get("issue_ref")),
                verdict=_safe_text(parsed.get("verdict")),
                note=_safe_text(parsed.get("note")),
            )
        return False

    def _poll_telegram_updates(self, trade_logger) -> None:
        offset = _safe_int(self.state.get("telegram_update_offset"), 0)
        updates = notifier.get_telegram_updates(
            offset=offset or None,
            timeout=0,
            allowed_updates=["callback_query", "message"],
        )
        if not updates:
            return
        max_update_id = offset
        for update in updates:
            update_id = _safe_int(update.get("update_id"), 0)
            max_update_id = max(max_update_id, update_id + 1)
            callback_query = dict(update.get("callback_query") or {})
            if callback_query:
                try:
                    self._handle_callback_query(callback_query)
                except Exception:
                    logger.exception("Failed to handle telegram callback query")
            message = dict(update.get("message") or {})
            if message:
                try:
                    self._handle_message_command(message, trade_logger)
                except Exception:
                    logger.exception("Failed to handle telegram message command")
        self.state["telegram_update_offset"] = max_update_id
        self._save_state()

    def tick(self, trade_logger) -> None:
        if not self.enabled:
            return
        now_ts = _now_kst().timestamp()
        self._bootstrap_test_messages()
        if now_ts - float(self._last_callback_poll_at) >= float(self.callback_poll_sec):
            self._poll_telegram_updates(trade_logger)
            self._last_callback_poll_at = now_ts
        if now_ts - float(self._last_pnl_scan_at) >= float(self.pnl_scan_sec):
            self._emit_due_pnl(trade_logger)
            self._last_pnl_scan_at = now_ts
        if now_ts - float(self._last_check_scan_at) >= float(self.check_scan_sec):
            self._scan_checkpoint_cards()
            self._last_check_scan_at = now_ts


def _priority_icon(kind: str, strength: str) -> str:
    if kind == "EXIT" and strength == "HIGH":
        return "[긴급]"
    if strength == "HIGH":
        return "[우선]"
    return "[일반]"


def build_pnl_digest_message(window_code: str, closed_frame: pd.DataFrame | None, *, start: datetime, end: datetime) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()
    pnl_sum = float(pd.to_numeric(scoped.get("realized_pnl", 0.0), errors="coerce").fillna(0.0).sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    wins = int((scoped["realized_pnl"] > 0).sum()) if trades else 0
    losses = int((scoped["realized_pnl"] < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0
    max_drawdown = 0.0
    best_trade = None
    worst_trade = None
    symbol_lines: list[str] = []
    entry_reason_lines: list[str] = []
    exit_reason_lines: list[str] = []

    if trades:
        scoped = scoped.sort_values("close_dt").reset_index(drop=True)
        equity_curve = scoped["realized_pnl"].cumsum()
        drawdown = equity_curve - equity_curve.cummax()
        max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
        best_trade = scoped.loc[scoped["realized_pnl"].idxmax()]
        worst_trade = scoped.loc[scoped["realized_pnl"].idxmin()]
        symbol_summary = (
            scoped.groupby("symbol", dropna=False)["realized_pnl"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(3)
        )
        for symbol, row in symbol_summary.iterrows():
            symbol_lines.append(f"- {symbol or 'UNKNOWN'} {_fmt_money(float(row['sum']))} ({int(row['count'])}건)")
        for column_name, target_lines in (("entry_reason", entry_reason_lines), ("exit_reason", exit_reason_lines)):
            series = (
                scoped[column_name].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().head(2)
            )
            for label, count in series.items():
                target_lines.append(f"- {label[:72]} ({int(count)}건)")

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"실현손익: {_fmt_money(pnl_sum)}",
        f"마감 거래: {trades}건",
        f"승/패: {wins} / {losses}",
        f"승률: {_fmt_pct(win_rate)}",
        f"구간 최대낙폭: {_fmt_money(max_drawdown)}",
    ]
    if best_trade is not None:
        lines.append(
            f"최고 거래: {_safe_text(best_trade.get('symbol'), 'UNKNOWN')} "
            f"{_fmt_money(_safe_float(best_trade.get('realized_pnl'), 0.0))}"
        )
    if worst_trade is not None:
        lines.append(
            f"최저 거래: {_safe_text(worst_trade.get('symbol'), 'UNKNOWN')} "
            f"{_fmt_money(_safe_float(worst_trade.get('realized_pnl'), 0.0))}"
        )
    if symbol_lines:
        lines.append("심볼별 요약:")
        lines.extend(symbol_lines)
    if entry_reason_lines:
        lines.append("진입 사유 상위:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("청산 사유 상위:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("메모: 이 구간에 마감 거래가 없습니다.")
    lines.append(f"기준 시각: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)


def build_check_candidate_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    payload = dict(row or {})
    management_action = _safe_text(payload.get("management_action_label")).upper()
    position_side = _safe_text(payload.get("position_side"), "FLAT").upper()
    if management_action not in TELEGRAM_CHECK_ACTION_MAP:
        return None
    if position_side == "FLAT" and management_action != "REBUY":
        return None
    if position_side != "FLAT" and management_action == "REBUY":
        return None

    kind, recommended_action, recommended_note = TELEGRAM_CHECK_ACTION_MAP[management_action]
    confidence = _safe_float(payload.get("management_action_confidence"), 0.0)
    strength = _strength_from_confidence(confidence)
    evidence_quality = _strength_from_confidence(max(confidence - 0.08, 0.0))
    symbol = _safe_text(payload.get("symbol")).upper()
    direction = _safe_text(payload.get("observe_side") or payload.get("action") or payload.get("leg_direction")).upper()
    generated_at = _to_kst_datetime(payload.get("generated_at")) or _now_kst()
    checkpoint_id = _safe_text(payload.get("checkpoint_id"))
    checkpoint_type = _safe_text(payload.get("checkpoint_type")).upper()
    coarse_family = _safe_text(payload.get("runtime_scene_coarse_family"))
    fine_label = _safe_text(payload.get("runtime_scene_fine_label"))
    management_reason = _safe_text(payload.get("management_action_reason"))
    blocked_by = _safe_text(payload.get("blocked_by"))
    current_profit = _safe_float(payload.get("current_profit"), 0.0)
    giveback_ratio = _safe_float(payload.get("giveback_ratio"), 0.0)
    unrealized_pnl_state = _safe_text(payload.get("unrealized_pnl_state")).upper()
    surface_name = _safe_text(payload.get("surface_name"))
    score_reason = _safe_text(payload.get("runtime_score_reason"))
    decision_deadline = _card_deadline(generated_at, kind)
    trigger_summary = _safe_text(
        payload.get("checkpoint_transition_reason")
        or management_reason
        or surface_name
        or checkpoint_type
    )
    approval_key = "|".join([symbol, checkpoint_id, checkpoint_type, management_action, position_side, direction])
    card_id = hashlib.sha1(f"{approval_key}|{generated_at.isoformat()}".encode("utf-8")).hexdigest()[:16]

    evidence_lines: list[str] = []
    if checkpoint_type:
        evidence_lines.append(f"체크포인트: {checkpoint_type}")
    if surface_name:
        evidence_lines.append(f"관찰 면: {surface_name}")
    if fine_label or coarse_family:
        evidence_lines.append(f"장면: {fine_label or coarse_family}")
    if management_reason:
        evidence_lines.append(f"판단 사유: {management_reason}")
    elif score_reason:
        evidence_lines.append(f"내부 기준: {score_reason}")

    risk_lines: list[str] = []
    if unrealized_pnl_state == "OPEN_LOSS":
        risk_lines.append("현재 손실 구간입니다.")
    if giveback_ratio > 0.0:
        risk_lines.append(f"되밀림 비율: {_fmt_pct(giveback_ratio)}")
    if current_profit < 0.0:
        risk_lines.append(f"현재 손익: {_fmt_money(current_profit)}")
    if blocked_by:
        risk_lines.append(f"차단 사유: {blocked_by}")
    if not risk_lines:
        risk_lines.append("즉시 눈에 띄는 리스크 메모는 없습니다.")

    return {
        "card_id": card_id,
        "approval_key": approval_key,
        "status": "PENDING",
        "kind": kind,
        "priority_icon": _priority_icon(kind, strength),
        "symbol": symbol,
        "direction": direction or ("BUY" if position_side == "FLAT" else position_side),
        "checkpoint_id": checkpoint_id,
        "checkpoint_type": checkpoint_type,
        "scene_family": coarse_family,
        "scene_label": fine_label,
        "recommended_action": recommended_action,
        "recommended_action_note": recommended_note,
        "action_strength": strength,
        "evidence_quality": evidence_quality,
        "trigger_summary": trigger_summary,
        "scope_note": "이번 checkpoint 1건 기준",
        "decision_deadline_ts": decision_deadline.isoformat(),
        "generated_at": generated_at.isoformat(),
        "management_action_label": management_action,
        "management_action_confidence": confidence,
        "confidence_display": f"{confidence:.2f}",
        "management_action_reason": management_reason,
        "current_profit": current_profit,
        "giveback_ratio": giveback_ratio,
        "position_side": position_side,
        "ticket": _safe_int(payload.get("ticket"), 0),
        "evidence_lines": evidence_lines[:4],
        "risk_lines": risk_lines[:4],
        "leg_id": _safe_text(payload.get("leg_id")),
    }


def build_check_card_text(
    card: dict[str, Any],
    *,
    status_override: str | None = None,
    decision_meta: dict[str, Any] | None = None,
) -> str:
    payload = dict(card or {})
    status = _safe_text(status_override or payload.get("status"), "PENDING").upper()
    decision = dict(decision_meta or {})
    recommended_action_label = _recommended_action_label(payload.get("recommended_action"))
    strength_label = _strength_label(payload.get("action_strength"))
    evidence_label = _strength_label(payload.get("evidence_quality"))
    confidence_display = _safe_text(payload.get("confidence_display"))
    lines = [
        f"{_safe_text(payload.get('priority_icon'), '[일반]')} {recommended_action_label} | {_kind_label(payload.get('kind'))} | 상태 {_status_label(status)}",
        f"{payload.get('symbol', '')} {payload.get('direction', '')} | {payload.get('checkpoint_type', '')}",
    ]
    scene_label = _safe_text(payload.get("scene_label") or payload.get("scene_family"))
    if scene_label:
        lines.append(f"장면: {scene_label}")
    lines.append(f"트리거: {payload.get('trigger_summary', '')}")
    lines.append("근거:")
    for line in list(payload.get("evidence_lines", []) or []):
        lines.append(f"- {line}")
    lines.append("리스크/주의:")
    for line in list(payload.get("risk_lines", []) or []):
        lines.append(f"- {line}")
    lines.append("권장 조치:")
    lines.append(f"- 제안 동작: {recommended_action_label}")
    lines.append(f"- 설명: {payload.get('recommended_action_note', '')}")
    lines.append(f"- 판단 강도: {strength_label} (confidence {confidence_display or '-'})")
    lines.append(f"- 근거 수준: {evidence_label}")
    lines.append(f"- 범위: {payload.get('scope_note', '')}")
    lines.append(f"- 결정 기한: {_safe_text(payload.get('decision_deadline_ts'))}")
    if status in {"APPROVED", "REJECTED", "HELD"}:
        lines.append("처리 결과:")
        lines.append(f"- 담당: {_safe_text(decision.get('decided_by_label') or payload.get('decided_by_label'), 'unknown')}")
        lines.append(f"- 시각: {_safe_text(decision.get('decided_at') or payload.get('decided_at'))}")
    return "\n".join(lines)


def build_check_reply_markup(card_id: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "승인", "callback_data": f"tgops:approve:{card_id}"},
                {"text": "거부", "callback_data": f"tgops:reject:{card_id}"},
                {"text": "보류", "callback_data": f"tgops:hold:{card_id}"},
            ]
        ]
    }


def _telegram_ops_bootstrap_test_messages_v2(self: TelegramOpsService) -> None:
    if not self.bootstrap_enabled:
        return
    sent_versions = list(self.state.get("bootstrap_sent_versions", []) or [])
    if TELEGRAM_OPS_BOOTSTRAP_VERSION in sent_versions:
        return
    runtime_msg = "[텔레그램 운영 부트스트랩]\n경로: 실시간 DM\n상태: 준비됨"
    check_msg = "[텔레그램 운영 부트스트랩]\n경로: 승인 체크방\n상태: 준비됨"
    report_msg = "[텔레그램 운영 부트스트랩]\n경로: 손익 보고방\n주기: 15분\n상태: 준비됨"
    validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="runtime")
    validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="check")
    validate_telegram_route_ownership(owner_key=OWNER_BOOTSTRAP_PROBE, route="report")
    notifier.send_runtime_telegram(runtime_msg)
    notifier.send_check_telegram(check_msg, parse_mode=None)
    notifier.send_report_telegram(report_msg, parse_mode=None)
    sent_versions.append(TELEGRAM_OPS_BOOTSTRAP_VERSION)
    self.state["bootstrap_sent_versions"] = sent_versions[-12:]
    self._save_state()


def _telegram_ops_handle_callback_query_v2(self: TelegramOpsService, callback_query: dict[str, Any]) -> bool:
    callback_id = _safe_text(callback_query.get("id"))
    callback_data = _safe_text(callback_query.get("data"))
    parsed = self._parse_callback_data(callback_data)
    if parsed is None and self._is_bridge_callback(callback_data):
        runtime = self._ensure_checkpoint_improvement_runtime()
        result = runtime.telegram_update_poller.handle_callback_query(callback_query)
        return _to_bool(dict(result.get("summary") or {}).get("handled"), False)
    if parsed is None:
        notifier.answer_callback_query(callback_id, text="지원하지 않는 버튼입니다.")
        return False
    if not self.live_check_approvals_enabled:
        notifier.answer_callback_query(
            callback_id,
            text="실시간 진입/청산 승인 경로는 비활성 상태입니다.",
            show_alert=True,
        )
        return False

    decision, card_id = parsed
    from_user = dict(callback_query.get("from") or {})
    user_id = _safe_int(from_user.get("id"), 0)
    user_label = _safe_text(from_user.get("username")) or _safe_text(from_user.get("first_name")) or str(user_id)
    if user_label and not user_label.startswith("@") and _safe_text(from_user.get("username")):
        user_label = f"@{user_label}"
    if not self._is_allowed_user(user_id):
        notifier.answer_callback_query(callback_id, text="이 버튼을 누를 권한이 없습니다.", show_alert=True)
        return False

    cards = dict(self.state.get("check_cards", {}) or {})
    card = dict(cards.get(card_id, {}) or {})
    if not card:
        notifier.answer_callback_query(callback_id, text="이미 만료됐거나 찾을 수 없는 카드입니다.")
        return False

    current_status = _safe_text(card.get("status"), "PENDING").upper()
    if current_status != "PENDING":
        notifier.answer_callback_query(callback_id, text=f"이미 {_status_label(current_status)} 처리된 카드입니다.")
        return False

    resolved_status = TELEGRAM_CHECK_DECISIONS[decision]
    decided_at = _now_kst().isoformat()
    card["status"] = resolved_status
    card["decision"] = decision.upper()
    card["decided_by_user_id"] = user_id
    card["decided_by_label"] = user_label
    card["decided_at"] = decided_at
    cards[card_id] = card
    self.state["check_cards"] = cards

    edited_text = build_check_card_text(
        card,
        status_override=resolved_status,
        decision_meta={"decided_by_label": user_label, "decided_at": decided_at},
    )
    notifier.edit_telegram_message_text(
        chat_id=_safe_text(card.get("chat_id")),
        message_id=_safe_int(card.get("message_id"), 0),
        text=edited_text,
        thread_id=_safe_int(card.get("thread_id"), 0),
        parse_mode=None,
    )
    notifier.answer_callback_query(callback_id, text=f"{_status_label(resolved_status)} 처리했습니다.")
    self._append_decision_log(
        {
            "contract_version": TELEGRAM_OPS_STATE_CONTRACT_VERSION,
            "card_id": card_id,
            "decision": decision.upper(),
            "status": resolved_status,
            "decided_at": decided_at,
            "decided_by_user_id": user_id,
            "decided_by_label": user_label,
            "checkpoint_id": _safe_text(card.get("checkpoint_id")),
            "symbol": _safe_text(card.get("symbol")),
            "recommended_action": _safe_text(card.get("recommended_action")),
        }
    )
    self._cleanup_card_state()
    self._save_state()
    return True


TelegramOpsService._bootstrap_test_messages = _telegram_ops_bootstrap_test_messages_v2
TelegramOpsService._handle_callback_query = _telegram_ops_handle_callback_query_v2


_REASON_EXACT_KO_LABELS = {
    "reclaim": "리클레임 진입",
    "breakout": "돌파 진입",
    "probe": "탐색 진입",
    "retest": "재테스트 진입",
    "bounce": "반등 진입",
    "late": "지연 진입",
    "pullback": "눌림 진입",
    "continuation": "추세 지속 진입",
    "reversal": "반전 진입",
    "target": "목표가 청산",
    "runner": "러너 청산",
    "stop": "손절 청산",
    "cut": "컷 청산",
    "timeout": "시간 청산",
    "trail": "추적 청산",
}

_REASON_TOKEN_KO_LABELS = {
    "flat": "플랫",
    "reclaim": "리클레임",
    "reentry": "재진입",
    "ready": "준비",
    "breakout": "돌파",
    "retest": "재테스트",
    "probe": "탐색",
    "bounce": "반등",
    "pullback": "눌림",
    "continuation": "지속",
    "trend": "추세",
    "reversal": "반전",
    "target": "목표가",
    "runner": "러너",
    "stop": "손절",
    "timeout": "시간만료",
    "cut": "컷",
    "shock": "충격",
    "protective": "보호",
    "loss": "손실",
    "profit": "수익",
    "hold": "보유",
    "wait": "대기",
    "exit": "청산",
    "entry": "진입",
}


def _fmt_unsigned_money(value: float) -> str:
    return f"{value:.2f} USD"


def _fmt_lot(value: float) -> str:
    return f"{value:.2f} lot"


def _safe_numeric_series(frame: pd.DataFrame, column_name: str) -> pd.Series:
    if column_name not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column_name], errors="coerce").fillna(0.0)


def _humanize_reason_label(value: object) -> str:
    raw = _safe_text(value)
    if not raw:
        return "-"
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in _REASON_EXACT_KO_LABELS:
        return _REASON_EXACT_KO_LABELS[normalized]
    tokens = [token for token in normalized.split("_") if token][:4]
    translated = [_REASON_TOKEN_KO_LABELS.get(token, token) for token in tokens]
    joined = " / ".join(translated).strip()
    if not joined:
        return raw
    if joined == raw:
        return joined
    return f"{joined} [{raw[:36]}]"


def _build_reason_top_lines(scoped: pd.DataFrame, column_name: str, *, limit: int = 5) -> list[str]:
    if scoped.empty or column_name not in scoped.columns:
        return []
    working = scoped.copy()
    working["_reason_value"] = working[column_name].fillna("").astype(str).str.strip()
    working = working[working["_reason_value"] != ""].copy()
    if working.empty:
        return []

    summary = (
        working.groupby("_reason_value", dropna=False)
        .agg(
            count=("realized_pnl", "size"),
            net_pnl=("realized_pnl", "sum"),
            win_count=("realized_pnl", lambda series: int((series > 0).sum())),
        )
        .sort_values(["count", "net_pnl"], ascending=[False, False])
        .head(limit)
    )

    total = int(summary["count"].sum()) if not summary.empty else 0
    lines: list[str] = []
    for reason_value, row in summary.iterrows():
        count = int(row["count"])
        share = (count / total) if total else 0.0
        win_rate = (int(row["win_count"]) / count) if count else 0.0
        lines.append(
            f"- {_humanize_reason_label(reason_value)} | {count}건 | 비중 {_fmt_pct(share)} | "
            f"승률 {_fmt_pct(win_rate)} | 순손익 {_fmt_money(float(row['net_pnl']))}"
        )
    return lines


def _estimate_window_balance_lines(
    prepared_frame: pd.DataFrame,
    scoped_frame: pd.DataFrame,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None,
) -> list[str]:
    if current_balance is None:
        return ["잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다."]

    future_pnl = 0.0
    if not prepared_frame.empty:
        future_scope = prepared_frame[prepared_frame["close_dt"] >= end]
        future_pnl = float(_safe_numeric_series(future_scope, "realized_pnl").sum()) if not future_scope.empty else 0.0
    window_pnl = float(_safe_numeric_series(scoped_frame, "realized_pnl").sum()) if not scoped_frame.empty else 0.0
    end_balance = float(current_balance) - future_pnl
    start_balance = end_balance - window_pnl
    return [
        f"구간 시작 잔고(추정): {_fmt_unsigned_money(start_balance)}",
        f"구간 종료 잔고(추정): {_fmt_unsigned_money(end_balance)}",
        "잔고 기준: 현재 계좌 잔고에서 이후 실현손익을 역산한 추정치입니다.",
    ]


def build_pnl_digest_message(
    window_code: str,
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None = None,
) -> str:
    frame = _prepare_closed_frame(closed_frame)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()

    net_pnl_sum = float(_safe_numeric_series(scoped, "realized_pnl").sum()) if not scoped.empty else 0.0
    gross_pnl_sum = float(_safe_numeric_series(scoped, "gross_pnl").sum()) if not scoped.empty else net_pnl_sum
    total_cost = float(_safe_numeric_series(scoped, "cost_total").sum()) if not scoped.empty else 0.0
    total_lot = float(_safe_numeric_series(scoped, "lot").sum()) if not scoped.empty else 0.0
    trades = int(len(scoped))
    entries = trades
    wins = int((_safe_numeric_series(scoped, "realized_pnl") > 0).sum()) if trades else 0
    losses = int((_safe_numeric_series(scoped, "realized_pnl") < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0

    entry_reason_lines = _build_reason_top_lines(scoped, "entry_reason", limit=5)
    exit_reason_lines = _build_reason_top_lines(scoped, "exit_reason", limit=5)
    balance_lines = _estimate_window_balance_lines(
        frame,
        scoped,
        start=start,
        end=end,
        current_balance=current_balance,
    )

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start)} ~ {_fmt_dt(end)} KST",
        f"순손익 합계: {_fmt_money(net_pnl_sum)}",
        f"총손익(비용 전): {_fmt_money(gross_pnl_sum)}",
        f"총 비용: {_fmt_unsigned_money(abs(total_cost))}",
        f"진입 횟수(마감 기준): {entries}회",
        f"총 진입 랏: {_fmt_lot(total_lot)}",
        f"승/패: {wins} / {losses} (승률 {_fmt_pct(win_rate)})",
    ]
    lines.extend(balance_lines)

    if entry_reason_lines:
        lines.append("진입 사유 TOP 5:")
        lines.extend(entry_reason_lines)
    if exit_reason_lines:
        lines.append("청산 사유 TOP 5:")
        lines.extend(exit_reason_lines)
    if not trades:
        lines.append("메모: 이 구간에 마감된 거래가 없어 손익과 사유 통계가 비어 있습니다.")
    lines.append(f"기준 시각: {_fmt_dt(_now_kst())} KST")
    return "\n".join(lines)
