from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def _safe_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _fmt_money(value: float) -> str:
    return f"{value:+.2f} USD"


def _fmt_unsigned_money(value: float) -> str:
    return f"{value:.2f} USD"


def _fmt_lot(value: float) -> str:
    return f"{value:.2f} lot"


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def _fmt_dt(value: datetime, *, timezone) -> str:
    return value.astimezone(timezone).strftime("%Y-%m-%d %H:%M")


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


def _safe_numeric_series(frame: pd.DataFrame, column_name: str) -> pd.Series:
    if column_name not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column_name], errors="coerce").fillna(0.0)


def _first_nonempty_text(series: pd.Series) -> str:
    for value in series.tolist():
        text = _safe_text(value)
        if text:
            return text
    return ""


def _resolve_effective_pnl_columns(closed: pd.DataFrame) -> pd.DataFrame:
    out = closed.copy()
    profit = _safe_numeric_series(out, "profit")
    gross = _safe_numeric_series(out, "gross_pnl")
    cost = _safe_numeric_series(out, "cost_total")
    net = _safe_numeric_series(out, "net_pnl_after_cost")

    profit_present = profit.abs() > 1e-12
    gross_missing = gross.abs() <= 1e-12
    cost_missing = cost.abs() <= 1e-12
    net_missing = net.abs() <= 1e-12

    # Older rows often have only `profit` populated. Treat that as net/gross fallback.
    missing_triplet = profit_present & gross_missing & cost_missing & net_missing
    gross = gross.where(~missing_triplet, profit)
    net = net.where(~missing_triplet, profit)

    net = net.where(~(net.abs() <= 1e-12) | ~profit_present, profit)
    gross = gross.where(~(gross.abs() <= 1e-12), net + cost)
    gross = gross.where(~(gross.abs() <= 1e-12) | ~profit_present, profit)

    derived_cost = gross - net
    cost = cost.where(~(cost.abs() <= 1e-12), derived_cost)

    out["profit"] = profit
    out["gross_pnl"] = gross
    out["cost_total"] = cost
    out["net_pnl_after_cost"] = net
    out["realized_pnl"] = net
    return out


def _dedupe_closed_frame(closed: pd.DataFrame) -> pd.DataFrame:
    subset = [
        column
        for column in (
            "dedup_key",
            "trade_link_key",
            "ticket",
            "ticket_int",
            "symbol",
            "close_ts",
            "close_time",
            "close_price",
            "lot",
            "profit",
        )
        if column in closed.columns
    ]
    if len(subset) < 4:
        return closed
    return closed.sort_values("close_dt").drop_duplicates(subset=subset, keep="last").reset_index(drop=True)


def _pick_trade_unit_column(scoped: pd.DataFrame) -> str:
    for column in ("trade_link_key", "decision_row_key", "replay_row_key", "ticket", "ticket_int"):
        if column not in scoped.columns:
            continue
        series = scoped[column].fillna("").astype(str).str.strip()
        if bool((series != "").any()):
            return column
    return ""


def _aggregate_trade_units(scoped: pd.DataFrame) -> pd.DataFrame:
    if scoped.empty:
        return scoped.copy()
    unit_column = _pick_trade_unit_column(scoped)
    if not unit_column:
        return scoped.copy().reset_index(drop=True)

    working = scoped.copy()
    unit_series = working[unit_column].fillna("").astype(str).str.strip()
    working["_trade_unit_id"] = unit_series.where(unit_series != "", working.index.map(lambda idx: f"row:{idx}"))
    aggregated = (
        working.groupby("_trade_unit_id", as_index=False)
        .agg(
            close_dt=("close_dt", "max"),
            symbol=("symbol", _first_nonempty_text),
            entry_reason=("entry_reason", _first_nonempty_text),
            exit_reason=("exit_reason", _first_nonempty_text),
            realized_pnl=("realized_pnl", "sum"),
            gross_pnl=("gross_pnl", "sum"),
            cost_total=("cost_total", "sum"),
            lot=("lot", "sum"),
        )
        .sort_values("close_dt")
        .reset_index(drop=True)
    )
    return aggregated


def _prepare_closed_frame(frame: pd.DataFrame | None, *, timezone) -> pd.DataFrame:
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
        ts_dt = pd.to_datetime(close_ts.where(has_ts), unit="s", errors="coerce", utc=True).dt.tz_convert(timezone)
        closed.loc[has_ts, "close_dt"] = closed.loc[has_ts, "close_dt"].fillna(ts_dt)
    closed = closed[closed["close_dt"].notna()].copy()
    if closed.empty:
        return closed
    closed["close_dt"] = closed["close_dt"].map(
        lambda dt: dt.tz_localize(timezone) if getattr(dt, "tzinfo", None) is None else dt.tz_convert(timezone)
    )
    closed["symbol"] = closed["symbol"].fillna("").astype(str).str.upper()
    closed["entry_reason"] = closed["entry_reason"].fillna("").astype(str)
    closed["exit_reason"] = closed["exit_reason"].fillna("").astype(str)
    closed = _resolve_effective_pnl_columns(closed)
    closed = _dedupe_closed_frame(closed)
    return closed.sort_values("close_dt").reset_index(drop=True)


_ENTRY_REASON_EXACT_DISPLAY = {
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

_EXIT_REASON_EXACT_DISPLAY = {
    "target": "목표가 도달 청산",
    "runner": "러너 정리 청산",
    "stop": "손절 청산",
    "cut": "위험 차단 청산",
    "timeout": "시간 만료 청산",
    "trail": "추적 청산",
    "partial_exit": "부분 청산",
    "full_exit": "전량 청산",
}

_ENTRY_REASON_FEATURE = {
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

_EXIT_REASON_FEATURE = {
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

_ENTRY_REASON_SENTENCE = {
    "flat_reclaim_reentry_ready": "플랫 상태에서 리클레임 재진입 준비",
}

_EXIT_REASON_SENTENCE = {
    "protective_loss_exit": "손실 보호 목적 청산",
}


def _format_reason_display(value: object, *, reason_kind: str) -> str:
    raw = _safe_text(value)
    if not raw:
        return "-"
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if reason_kind == "entry":
        exact_map = _ENTRY_REASON_EXACT_DISPLAY
        feature_map = _ENTRY_REASON_FEATURE
        sentence_map = _ENTRY_REASON_SENTENCE
    else:
        exact_map = _EXIT_REASON_EXACT_DISPLAY
        feature_map = _EXIT_REASON_FEATURE
        sentence_map = _EXIT_REASON_SENTENCE

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


def _build_reason_top_lines(
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
            f"- {_format_reason_display(reason_value, reason_kind=reason_kind)} | {count}건 | "
            f"비중 {_fmt_pct(share)} | 승률 {_fmt_pct(win_rate)} | 순손익 {_fmt_money(float(row['net_pnl']))}"
        )
    return lines


def _estimate_window_balance_lines(
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


def build_telegram_pnl_digest_message(
    window_code: str,
    closed_frame: pd.DataFrame | None,
    *,
    start: datetime,
    end: datetime,
    current_balance: float | None = None,
    timezone: Any,
    system_status_lines: list[str] | None = None,
) -> str:
    frame = _prepare_closed_frame(closed_frame, timezone=timezone)
    scoped = frame[(frame["close_dt"] >= start) & (frame["close_dt"] < end)].copy() if not frame.empty else pd.DataFrame()
    trade_units = _aggregate_trade_units(scoped)

    net_pnl_sum = float(_safe_numeric_series(trade_units, "realized_pnl").sum()) if not trade_units.empty else 0.0
    gross_pnl_sum = float(_safe_numeric_series(trade_units, "gross_pnl").sum()) if not trade_units.empty else net_pnl_sum
    total_cost = float(_safe_numeric_series(trade_units, "cost_total").sum()) if not trade_units.empty else 0.0
    total_lot = float(_safe_numeric_series(trade_units, "lot").sum()) if not trade_units.empty else 0.0
    trades = int(len(trade_units))
    entries = trades
    wins = int((_safe_numeric_series(trade_units, "realized_pnl") > 0).sum()) if trades else 0
    losses = int((_safe_numeric_series(trade_units, "realized_pnl") < 0).sum()) if trades else 0
    win_rate = (wins / trades) if trades else 0.0

    entry_reason_lines = _build_reason_top_lines(trade_units, "entry_reason", reason_kind="entry", limit=5)
    exit_reason_lines = _build_reason_top_lines(trade_units, "exit_reason", reason_kind="exit", limit=5)
    balance_lines = _estimate_window_balance_lines(
        frame,
        trade_units,
        end=end,
        current_balance=current_balance,
    )

    lines = [
        f"[손익 요약 | {_window_label(window_code)}]",
        f"구간: {_fmt_dt(start, timezone=timezone)} ~ {_fmt_dt(end, timezone=timezone)} KST",
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
    if system_status_lines:
        lines.extend([line for line in system_status_lines if _safe_text(line)])
    if not trades:
        lines.append("메모: 이 구간에 마감된 거래가 없어 손익과 사유 통계가 비어 있습니다.")
    lines.append(f"기준 시각: {_fmt_dt(datetime.now(timezone), timezone=timezone)} KST")
    return "\n".join(lines)
