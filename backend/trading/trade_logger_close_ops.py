# 한글 설명: TradeLogger의 강제 종료 처리와 종료 체결 반영(폐쇄 행 업데이트) 로직을 분리한 모듈입니다.
"""Close-path operation helpers extracted from TradeLogger."""

from __future__ import annotations

import logging

import pandas as pd

from backend.services.exit_profile_router import resolve_exit_profile


def _preserve_close_metadata(df: pd.DataFrame, row_idx: int) -> None:
    management_profile_id = (
        str(df.at[row_idx, "management_profile_id"] or "").strip().lower()
        if "management_profile_id" in df.columns
        else ""
    )
    invalidation_id = (
        str(df.at[row_idx, "invalidation_id"] or "").strip().lower()
        if "invalidation_id" in df.columns
        else ""
    )
    setup_id = str(df.at[row_idx, "entry_setup_id"] or "").strip().lower() if "entry_setup_id" in df.columns else ""
    exit_profile = str(df.at[row_idx, "exit_profile"] or "").strip().lower() if "exit_profile" in df.columns else ""
    if "management_profile_id" in df.columns:
        df.at[row_idx, "management_profile_id"] = management_profile_id
    if "invalidation_id" in df.columns:
        df.at[row_idx, "invalidation_id"] = invalidation_id
    if "entry_setup_id" in df.columns:
        df.at[row_idx, "entry_setup_id"] = setup_id
    if "exit_profile" in df.columns:
        df.at[row_idx, "exit_profile"] = exit_profile or resolve_exit_profile(
            management_profile_id=management_profile_id,
            invalidation_id=invalidation_id,
            entry_setup_id=setup_id,
            fallback_profile="neutral",
        )


def force_close_unknown(trade_logger, ticket, reason="Manual/Unknown", exit_score=0, logger: logging.Logger | None = None):
    log = logger or logging.getLogger(__name__)
    try:
        df = trade_logger._read_open_df_safe()
        df = trade_logger._normalize_dataframe(df)
        idx = df.index[df["ticket"] == ticket]
        if idx.empty:
            return False

        now_text = trade_logger._now_kst_text()
        now_ts = trade_logger._text_to_kst_epoch(now_text)
        shock_meta = trade_logger.resolve_shock_event_on_close(int(ticket), now_text, int(now_ts))
        for i in idx.tolist():
            if str(df.at[i, "status"]).upper() == "CLOSED":
                continue
            open_price = float(pd.to_numeric(df.at[i, "open_price"], errors="coerce") or 0.0)
            if not str(df.at[i, "close_time"]).strip():
                df.at[i, "close_time"] = now_text
            if int(pd.to_numeric(df.at[i, "close_ts"], errors="coerce") or 0) <= 0:
                df.at[i, "close_ts"] = int(now_ts)
            if float(pd.to_numeric(df.at[i, "close_price"], errors="coerce") or 0.0) == 0.0:
                df.at[i, "close_price"] = open_price
            close_px = float(pd.to_numeric(df.at[i, "close_price"], errors="coerce") or open_price)
            req_px = float(pd.to_numeric(df.at[i, "exit_request_price"], errors="coerce") or close_px)
            pt = max(1e-12, float(pd.to_numeric(df.at[i, "exit_slippage_points"], errors="coerce") or 0.0))
            if float(pd.to_numeric(df.at[i, "exit_request_price"], errors="coerce") or 0.0) <= 0.0:
                df.at[i, "exit_request_price"] = req_px
            df.at[i, "exit_fill_price"] = close_px
            if pt <= 0.0:
                df.at[i, "exit_slippage_points"] = 0.0
            if str(df.at[i, "exit_reason"]).strip() == "":
                df.at[i, "exit_reason"] = reason
            if int(pd.to_numeric(df.at[i, "exit_score"], errors="coerce") or 0) <= 0:
                s = int(exit_score or 0)
                if s <= 0:
                    s = int(trade_logger._estimate_reason_points(str(df.at[i, "exit_reason"])))
                df.at[i, "exit_score"] = s
            _preserve_close_metadata(df, i)
            if shock_meta:
                if float(pd.to_numeric(df.at[i, "shock_score"], errors="coerce") or 0.0) <= 0.0:
                    df.at[i, "shock_score"] = float(shock_meta.get("shock_score", 0.0) or 0.0)
                if "shock_hold_delta_10" in shock_meta and float(pd.to_numeric(df.at[i, "shock_hold_delta_10"], errors="coerce") or 0.0) == 0.0:
                    df.at[i, "shock_hold_delta_10"] = float(shock_meta.get("shock_hold_delta_10", 0.0) or 0.0)
                if "shock_hold_delta_30" in shock_meta and float(pd.to_numeric(df.at[i, "shock_hold_delta_30"], errors="coerce") or 0.0) == 0.0:
                    df.at[i, "shock_hold_delta_30"] = float(shock_meta.get("shock_hold_delta_30", 0.0) or 0.0)
            df.at[i, "status"] = "CLOSED"
        closed_rows = df.loc[idx.tolist()].copy()
        trade_logger._append_to_closed_file(closed_rows)
        df = df.drop(index=idx.tolist()).reset_index(drop=True)
        trade_logger._write_open_df(df)
        trade_logger._sync_open_rows_to_store(df[df["status"] == "OPEN"].copy())
        return True
    except Exception as exc:
        log.exception("Failed to force-close ticket %s: %s", ticket, exc)
        return False


def update_closed_trade(trade_logger, ticket, deal, fallback_reason="Manual/Unknown", logger: logging.Logger | None = None):
    log = logger or logging.getLogger(__name__)
    try:
        df = trade_logger._read_open_df_safe()
        df = trade_logger._normalize_dataframe(df)
        idx = df.index[df["ticket"] == ticket]
        if idx.empty:
            return None

        symbol_info = trade_logger.broker.symbol_info(deal.symbol)
        point = symbol_info.point if symbol_info else 0.00001
        profit = deal.profit + deal.swap + deal.commission
        agg_profit = trade_logger._sum_exit_profit_for_position(ticket)
        if agg_profit is not None and (abs(float(profit)) < 1e-9 or abs(float(agg_profit)) > abs(float(profit))):
            profit = float(agg_profit)
        close_text = trade_logger._ts_to_kst_text(int(deal.time))
        close_ts = int(trade_logger._ts_to_kst_dt(int(deal.time)).timestamp())
        t_int = int(ticket)
        shock_meta = trade_logger.resolve_shock_event_on_close(t_int, close_text, close_ts)
        exit_meta = trade_logger.pending_exit.pop(t_int, None)
        live_meta = trade_logger.live_exit_context.pop(t_int, None)
        deal_comment = str(getattr(deal, "comment", "") or "").strip()
        exit_reason = ""
        exit_score = 0
        pre_reason = ""
        pre_score = 0
        try:
            pre_reason = str(df.at[idx.tolist()[0], "exit_reason"] or "").strip()
            pre_score = int(pd.to_numeric(df.at[idx.tolist()[0], "exit_score"], errors="coerce") or 0)
        except Exception:
            pass
        if pre_reason and trade_logger._normalize_exit_reason(pre_reason).upper() not in {"MANUAL/UNKNOWN", "UNKNOWN"}:
            exit_reason = pre_reason
            exit_score = pre_score
        if exit_meta and not exit_reason:
            meta_reason = str(exit_meta.get("reason", "") or "").strip()
            meta_detail = str(exit_meta.get("detail", "") or "").strip()
            exit_reason = f"{meta_reason}, {meta_detail}" if meta_detail and meta_reason else (meta_reason or meta_detail)
            exit_score = int(exit_meta.get("exit_score", 0))
        if live_meta and not exit_reason:
            live_reason = str(live_meta.get("reason", "") or "").strip()
            live_detail = str(live_meta.get("detail", "") or "").strip()
            if live_reason:
                exit_reason = live_reason if not live_detail else f"{live_reason}, {live_detail}"
            exit_score = int(live_meta.get("exit_score", 0) or 0)
        if not exit_reason and deal_comment and deal_comment.upper() not in {"AUTOTRADE", "AUTO", "CLOSE"}:
            exit_reason = deal_comment
        if not exit_reason:
            exit_reason = str(fallback_reason or "Manual/Unknown").strip() or "Manual/Unknown"
        if int(exit_score or 0) <= 0:
            exit_score = int(trade_logger._estimate_reason_points(exit_reason))

        sample_i = idx.tolist()[0]
        sample_direction = str(df.at[sample_i, "direction"])
        sample_open_price = float(pd.to_numeric(df.at[sample_i, "open_price"], errors="coerce") or 0.0)
        points = (deal.price - sample_open_price) / point if sample_direction == "BUY" else (sample_open_price - deal.price) / point
        symbol = str(df.at[sample_i, "symbol"])

        for i in idx.tolist():
            direction = str(df.at[i, "direction"])
            open_price = float(pd.to_numeric(df.at[i, "open_price"], errors="coerce") or 0.0)
            points_i = (deal.price - open_price) / point if direction == "BUY" else (open_price - deal.price) / point
            df.at[i, "close_time"] = close_text
            df.at[i, "close_ts"] = int(close_ts)
            df.at[i, "close_price"] = deal.price
            req_px = float(pd.to_numeric(df.at[i, "exit_request_price"], errors="coerce") or 0.0)
            if req_px <= 0.0:
                req_px = float(deal.price)
                df.at[i, "exit_request_price"] = req_px
            df.at[i, "exit_fill_price"] = float(deal.price)
            slip_pts = abs(float(deal.price) - req_px) / max(1e-12, float(point))
            df.at[i, "exit_slippage_points"] = float(slip_pts)
            df.at[i, "profit"] = round(profit, 2)
            df.at[i, "points"] = round(points_i, 1)
            df.at[i, "exit_reason"] = exit_reason
            df.at[i, "exit_score"] = int(exit_score)
            _preserve_close_metadata(df, i)
            if shock_meta:
                if float(pd.to_numeric(df.at[i, "shock_score"], errors="coerce") or 0.0) <= 0.0:
                    df.at[i, "shock_score"] = float(shock_meta.get("shock_score", 0.0) or 0.0)
                if not str(df.at[i, "shock_level"]).strip():
                    df.at[i, "shock_level"] = str(shock_meta.get("shock_level", "") or "").strip().lower()
                if not str(df.at[i, "shock_reason"]).strip():
                    df.at[i, "shock_reason"] = str(shock_meta.get("shock_reason", "") or "").strip()
                if not str(df.at[i, "shock_action"]).strip():
                    df.at[i, "shock_action"] = str(shock_meta.get("shock_action", "") or "").strip().lower()
                if not str(df.at[i, "pre_shock_stage"]).strip():
                    df.at[i, "pre_shock_stage"] = str(shock_meta.get("pre_shock_stage", "") or "").strip().lower()
                if not str(df.at[i, "post_shock_stage"]).strip():
                    df.at[i, "post_shock_stage"] = str(shock_meta.get("post_shock_stage", "") or "").strip().lower()
                if float(pd.to_numeric(df.at[i, "shock_at_profit"], errors="coerce") or 0.0) == 0.0:
                    df.at[i, "shock_at_profit"] = float(shock_meta.get("shock_at_profit", 0.0) or 0.0)
                if "shock_hold_delta_10" in shock_meta and float(pd.to_numeric(df.at[i, "shock_hold_delta_10"], errors="coerce") or 0.0) == 0.0:
                    df.at[i, "shock_hold_delta_10"] = float(shock_meta.get("shock_hold_delta_10", 0.0) or 0.0)
                if "shock_hold_delta_30" in shock_meta and float(pd.to_numeric(df.at[i, "shock_hold_delta_30"], errors="coerce") or 0.0) == 0.0:
                    df.at[i, "shock_hold_delta_30"] = float(shock_meta.get("shock_hold_delta_30", 0.0) or 0.0)
            df.at[i, "status"] = "CLOSED"
        closed_rows = df.loc[idx.tolist()].copy()
        trade_logger._append_to_closed_file(closed_rows)
        df = df.drop(index=idx.tolist()).reset_index(drop=True)
        trade_logger._write_open_df(df)
        trade_logger._sync_open_rows_to_store(df[df["status"] == "OPEN"].copy())

        icon = "WIN" if profit > 0 else "LOSS"
        return (
            f"{icon} [Exit]\n"
            f"Symbol: {symbol}\n"
            f"PnL: ${profit:.2f} ({int(points)} ticks)\n"
            f"Entry: {open_price} -> Exit: {deal.price}"
        )
    except Exception as exc:
        log.exception("CSV update failed for ticket %s: %s", ticket, exc)
        return None
