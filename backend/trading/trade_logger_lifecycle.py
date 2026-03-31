# 한글 설명: TradeLogger의 포지션 종료 감지 및 오픈 트레이드 재조정 라이프사이클 로직을 분리한 모듈입니다.
"""Lifecycle helpers extracted from TradeLogger."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def _resolve_startup_reconcile_profile_path(trade_logger) -> Path | None:
    raw_path = str(getattr(trade_logger, "startup_reconcile_profile_path", "") or "").strip()
    if raw_path:
        try:
            path = Path(raw_path)
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[2] / path
            return path.resolve()
        except Exception:
            return None
    raw_trade_path = str(getattr(trade_logger, "filepath", "") or "").strip()
    if not raw_trade_path:
        return None
    try:
        return Path(raw_trade_path).resolve().with_name("startup_reconcile_latest.json")
    except Exception:
        return None


def _persist_startup_reconcile_profile(trade_logger, profile: dict) -> None:
    try:
        trade_logger.startup_reconcile_profile = dict(profile or {})
    except Exception:
        pass
    profile_path = _resolve_startup_reconcile_profile_path(trade_logger)
    if profile_path is None:
        return
    try:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(profile or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.exception("Failed to persist startup reconcile profile: %s", exc)


def _safe_count(frame) -> int:
    try:
        return int(len(frame))
    except Exception:
        return 0


def _read_open_rows_light(trade_logger) -> pd.DataFrame:
    raw_trade_path = str(getattr(trade_logger, "filepath", "") or "").strip()
    if not raw_trade_path:
        return pd.DataFrame(columns=["ticket", "status", "open_time", "symbol"])
    path = Path(raw_trade_path)
    if not path.exists():
        return pd.DataFrame(columns=["ticket", "status", "open_time", "symbol"])
    wanted_columns = {"ticket", "status", "open_time", "symbol"}
    try:
        df = pd.read_csv(
            path,
            encoding="utf-8-sig",
            usecols=lambda col: str(col or "").strip() in wanted_columns,
        )
    except ValueError:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=["ticket", "status", "open_time", "symbol"])

    for column in ("ticket", "status", "open_time", "symbol"):
        if column not in df.columns:
            df[column] = ""

    df["ticket"] = pd.to_numeric(df["ticket"], errors="coerce").fillna(0).astype(int)
    df["status"] = df["status"].fillna("").astype(str).str.strip().str.upper()
    df["open_time"] = df["open_time"].fillna("").astype(str).str.strip()
    df["symbol"] = df["symbol"].fillna("").astype(str).str.strip().str.upper()
    df = df[df["ticket"] > 0]
    return df[df["status"] == "OPEN"].copy()


def check_closed_trades(trade_logger):
    if not trade_logger.active_tickets:
        return []

    messages = []
    positions = trade_logger.broker.positions_get()
    if positions is None:
        return []
    current_tickets = {int(p.ticket) for p in positions}
    closed_tickets = trade_logger.active_tickets - current_tickets
    if not closed_tickets:
        return []

    now = datetime.now()
    date_from = now - timedelta(days=2)
    if trade_logger.last_history_check > date_from:
        date_from = trade_logger.last_history_check - timedelta(minutes=5)

    history = trade_logger.broker.history_deals_get(date_from=date_from, date_to=now) or []
    trade_logger.last_history_check = now

    for ticket in closed_tickets:
        t = int(ticket)
        try:
            still_open = trade_logger.broker.positions_get(ticket=t) or []
        except Exception:
            still_open = []
        if still_open:
            trade_logger.closed_pending_since.pop(t, None)
            trade_logger.closed_pending_checks.pop(t, None)
            continue

        exit_deal = trade_logger._find_latest_exit_deal(history, ticket)
        if exit_deal is None:
            exit_deal = trade_logger._find_latest_exit_deal_direct(ticket)

        if exit_deal:
            msg = trade_logger._update_closed_trade(ticket, exit_deal)
            if msg:
                messages.append(msg)
            trade_logger.active_tickets.remove(ticket)
            trade_logger.closed_pending_since.pop(t, None)
            trade_logger.closed_pending_checks.pop(t, None)
        else:
            now_dt = datetime.now()
            first = trade_logger.closed_pending_since.get(t)
            if first is None:
                trade_logger.closed_pending_since[t] = now_dt
                trade_logger.closed_pending_checks[t] = 1
                continue
            trade_logger.closed_pending_checks[t] = int(trade_logger.closed_pending_checks.get(t, 0)) + 1
            elapsed = (now_dt - first).total_seconds()
            if elapsed < 15.0 or int(trade_logger.closed_pending_checks.get(t, 0)) < 3:
                continue
            exit_deal = trade_logger._find_latest_exit_deal_direct(ticket)
            if exit_deal:
                msg = trade_logger._update_closed_trade(ticket, exit_deal)
                if msg:
                    messages.append(msg)
                trade_logger.active_tickets.remove(ticket)
                trade_logger.closed_pending_since.pop(t, None)
                trade_logger.closed_pending_checks.pop(t, None)
                continue
            if elapsed < 120.0:
                continue
            live_meta = trade_logger.live_exit_context.pop(t, None)
            reason = "Manual/Unknown"
            score = 0
            if live_meta:
                lr = str(live_meta.get("reason", "") or "").strip()
                ld = str(live_meta.get("detail", "") or "").strip()
                reason = f"{lr}, {ld}" if lr and ld else (lr or ld or reason)
                score = int(live_meta.get("exit_score", 0) or 0)
            if score <= 0:
                score = int(trade_logger._estimate_reason_points(reason))
            ok = trade_logger._force_close_unknown(ticket=t, reason=reason, exit_score=score)
            if ok:
                messages.append(f"WARN [Exit Fallback: delayed] ticket={t} reason={reason} score={score}")
                trade_logger.active_tickets.remove(ticket)
                trade_logger.closed_pending_since.pop(t, None)
                trade_logger.closed_pending_checks.pop(t, None)

    return messages


def reconcile_open_trades(trade_logger, lookback_days=30, *, light_mode=False, profile=False):
    started_at = time.perf_counter()
    trace = {
        "contract_version": "startup_reconcile_profile_v1",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "lookback_days": int(lookback_days),
        "light_mode_requested": bool(light_mode),
        "light_mode_applied": False,
        "profile_enabled": bool(profile),
        "status": "started",
        "timings_ms": {},
        "counts": {},
        "steps": [],
        "error": "",
    }

    def _mark_timing(name: str, step_started_at: float) -> None:
        trace["timings_ms"][str(name)] = round((time.perf_counter() - step_started_at) * 1000.0, 3)

    def _push_step(name: str, **extra) -> None:
        payload = {"name": str(name)}
        for key, value in extra.items():
            payload[str(key)] = value
        trace["steps"].append(payload)

    try:
        if light_mode:
            trace["light_mode_applied"] = True
            step_started_at = time.perf_counter()
            open_rows = _read_open_rows_light(trade_logger)
            _mark_timing("read_open_rows_light", step_started_at)
            trace["counts"]["raw_rows"] = _safe_count(open_rows)
            trace["counts"]["normalized_rows"] = _safe_count(open_rows)
            trace["counts"]["open_rows"] = _safe_count(open_rows)
            _push_step("read_open_rows_light", rows=_safe_count(open_rows))
        else:
            step_started_at = time.perf_counter()
            df = trade_logger._read_open_df_safe()
            _mark_timing("read_open_df", step_started_at)
            trace["counts"]["raw_rows"] = _safe_count(df)
            _push_step("read_open_df", rows=_safe_count(df))

            step_started_at = time.perf_counter()
            df = trade_logger._normalize_dataframe(df)
            _mark_timing("normalize_dataframe", step_started_at)
            trace["counts"]["normalized_rows"] = _safe_count(df)
            _push_step("normalize_dataframe", rows=_safe_count(df))

            step_started_at = time.perf_counter()
            open_rows = df[df["status"] == "OPEN"]
            _mark_timing("filter_open_rows", step_started_at)
            trace["counts"]["open_rows"] = _safe_count(open_rows)
            _push_step("filter_open_rows", rows=_safe_count(open_rows))

        if open_rows.empty:
            trace["status"] = "no_open_rows"
            return 0, 0, 0

        step_started_at = time.perf_counter()
        positions = trade_logger.broker.positions_get() or []
        _mark_timing("positions_get", step_started_at)
        current_tickets = {int(p.ticket) for p in positions}
        trace["counts"]["live_positions"] = int(len(current_tickets))
        _push_step("positions_get", live_positions=int(len(current_tickets)))

        if light_mode:
            deferred_candidates = [
                int(ticket)
                for ticket in pd.to_numeric(open_rows["ticket"], errors="coerce").fillna(0).astype(int).tolist()
                if int(ticket) > 0 and int(ticket) not in current_tickets
            ]
            trace["counts"]["history_deals"] = 0
            trace["counts"]["closed_with_deal"] = 0
            trace["counts"]["force_closed_unknown"] = 0
            trace["counts"]["deferred_non_live_open_rows"] = int(len(deferred_candidates))
            trace["status"] = "ok_light"
            _push_step(
                "light_mode_defer",
                scanned_open_rows=int(len(open_rows)),
                deferred_non_live_open_rows=int(len(deferred_candidates)),
            )
            return int(len(open_rows)), 0, 0

        now = datetime.now()
        date_from = now - timedelta(days=max(2, int(lookback_days)))

        step_started_at = time.perf_counter()
        if "open_time" in open_rows.columns:
            open_times = pd.to_datetime(open_rows["open_time"], errors="coerce")
            if open_times.notna().any():
                earliest = open_times.min().to_pydatetime() - timedelta(days=1)
                if earliest < date_from:
                    date_from = earliest
        _mark_timing("resolve_history_window", step_started_at)
        trace["history_window_start"] = date_from.isoformat(timespec="seconds")
        trace["history_window_end"] = now.isoformat(timespec="seconds")

        step_started_at = time.perf_counter()
        history = trade_logger.broker.history_deals_get(date_from=date_from, date_to=now) or []
        _mark_timing("history_deals_get", step_started_at)
        trace["counts"]["history_deals"] = int(len(history))
        _push_step("history_deals_get", history_deals=int(len(history)))
        closed_with_deal = 0
        force_closed_unknown = 0

        step_started_at = time.perf_counter()
        for ticket in open_rows["ticket"].tolist():
            ticket = int(ticket)
            if ticket in current_tickets:
                continue

            exit_deal = trade_logger._find_latest_exit_deal(history, ticket)
            if exit_deal is None:
                exit_deal = trade_logger._find_latest_exit_deal_direct(ticket)
            if exit_deal is not None:
                trade_logger._update_closed_trade(ticket, exit_deal, fallback_reason="Manual/Unknown")
                closed_with_deal += 1
                trade_logger.active_tickets.discard(ticket)
                continue
        _mark_timing("ticket_scan", step_started_at)
        trace["counts"]["closed_with_deal"] = int(closed_with_deal)
        trace["counts"]["force_closed_unknown"] = int(force_closed_unknown)
        trace["status"] = "ok"
        _push_step(
            "ticket_scan",
            scanned_open_rows=int(len(open_rows)),
            closed_with_deal=int(closed_with_deal),
            force_closed_unknown=int(force_closed_unknown),
        )

        return int(len(open_rows)), closed_with_deal, force_closed_unknown
    except Exception as exc:
        trace["status"] = "error"
        trace["error"] = str(exc)
        return 0, 0, 0
    finally:
        trace["timings_ms"]["total"] = round((time.perf_counter() - started_at) * 1000.0, 3)
        if profile:
            _persist_startup_reconcile_profile(trade_logger, trace)
        if trace["status"] != "started":
            logger.info(
                "startup reconcile: status=%s light_mode_requested=%s total_ms=%s open_rows=%s closed_with_deal=%s",
                str(trace.get("status", "")),
                bool(trace.get("light_mode_requested", False)),
                trace["timings_ms"].get("total", 0.0),
                trace["counts"].get("open_rows", 0),
                trace["counts"].get("closed_with_deal", 0),
            )
