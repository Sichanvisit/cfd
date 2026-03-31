# 한글 설명: TradeLogger의 임계치/익시트 정책/어드버스 정책 추천 계산을 담당하는 분리 모듈입니다.
"""Recommendation helpers extracted from TradeLogger."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import pandas as pd

from backend.services.trade_csv_schema import add_signed_exit_score


def recommend_thresholds(read_closed_df, default_entry: int, default_exit: int, logger: logging.Logger) -> Tuple[int, int, Optional[str]]:
    try:
        closed = read_closed_df()
        if len(closed) < 8:
            return default_entry, default_exit, None

        closed["profit"] = pd.to_numeric(closed["profit"], errors="coerce").fillna(0.0)
        closed["entry_score"] = pd.to_numeric(closed["entry_score"], errors="coerce").fillna(0)
        closed["exit_score"] = pd.to_numeric(closed["exit_score"], errors="coerce").fillna(0)
        closed = add_signed_exit_score(closed)

        wins = closed[closed["profit"] > 0]
        losses = closed[closed["profit"] <= 0]

        if len(wins) >= 10:
            new_entry = int(wins["entry_score"].quantile(0.35))
            new_entry = max(90, min(260, new_entry))
        else:
            new_entry = int(closed["entry_score"].quantile(0.70))
            new_entry = max(90, min(240, new_entry))

        losing_exits = losses[losses["signed_exit_score"] < 0]["signed_exit_score"].abs()
        if len(losing_exits) >= 10:
            new_exit = int(losing_exits.quantile(0.30))
            new_exit = max(80, min(300, new_exit))
        else:
            base_exit = int(closed["signed_exit_score"].abs().quantile(0.55))
            new_exit = max(70, min(220, base_exit))

        note = f"adaptive thresholds: entry={new_entry}, exit={new_exit}, closed={len(closed)}"
        return new_entry, new_exit, note
    except Exception as exc:
        logger.exception("Failed to recommend thresholds: %s", exc)
        return default_entry, default_exit, None


def recommend_exit_policy(read_closed_df, normalize_exit_reason, logger: logging.Logger):
    default_policy = {
        "score_multiplier": {"Reversal": 1.0},
        "profit_multiplier": {"RSI Scalp": 1.0, "BB Scalp": 1.0},
        "stats": {},
    }
    try:
        closed = read_closed_df()
        if len(closed) < 20:
            return default_policy, None

        closed["profit"] = pd.to_numeric(closed["profit"], errors="coerce").fillna(0.0)
        closed["exit_reason"] = closed["exit_reason"].astype(str).fillna("").str.strip()
        closed["exit_reason_norm"] = closed["exit_reason"].map(normalize_exit_reason)
        unknown_reasons = {"", "UNKNOWN", "MANUAL/UNKNOWN", "MANUAL", "NONE", "NULL", "N/A"}
        closed = closed[~closed["exit_reason_norm"].str.upper().isin(unknown_reasons)]
        if closed.empty:
            return default_policy, None

        profit_scale = max(1.0, float(closed["profit"].abs().median()))
        min_samples = 8
        policy = {
            "score_multiplier": {"Reversal": 1.0},
            "profit_multiplier": {"RSI Scalp": 1.0, "BB Scalp": 1.0},
            "stats": {},
        }

        for reason in ["Reversal", "RSI Scalp", "BB Scalp"]:
            reason_df = closed[closed["exit_reason_norm"] == reason].copy()
            n = len(reason_df)
            if n == 0:
                continue

            profits = reason_df["profit"].astype(float)
            q_low = profits.quantile(0.10)
            q_high = profits.quantile(0.90)
            trimmed = profits[(profits >= q_low) & (profits <= q_high)]
            if trimmed.empty:
                trimmed = profits

            win_rate = float((profits > 0).mean())
            expectancy = float(trimmed.mean())
            gross_profit = float(profits[profits > 0].sum())
            gross_loss = float((-profits[profits < 0]).sum())
            profit_factor = gross_profit / max(1e-9, gross_loss)
            avg_win = float(profits[profits > 0].mean()) if (profits > 0).any() else 0.0
            avg_loss = float((-profits[profits < 0]).mean()) if (profits < 0).any() else 0.0
            payoff_ratio = avg_win / max(1e-9, avg_loss)
            exp_norm = max(-1.0, min(1.0, expectancy / profit_scale))
            pf_norm = max(-1.0, min(1.0, (profit_factor - 1.0) / 1.5))
            payoff_norm = max(-1.0, min(1.0, (payoff_ratio - 1.0) / 1.5))
            quality = (win_rate - 0.5) * 1.0 + exp_norm * 0.45 + pf_norm * 0.35 + payoff_norm * 0.20
            quality = max(-1.0, min(1.0, quality))

            multiplier = round(max(0.75, min(1.25, 1.0 - (0.25 * quality))), 2)
            if n < min_samples:
                multiplier = 1.0

            policy["stats"][reason] = {
                "count": int(n),
                "win_rate": round(win_rate, 3),
                "expectancy": round(expectancy, 3),
                "profit_factor": round(profit_factor, 3),
                "payoff_ratio": round(payoff_ratio, 3),
                "multiplier": multiplier,
            }

            if reason == "Reversal":
                policy["score_multiplier"]["Reversal"] = multiplier
            else:
                policy["profit_multiplier"][reason] = multiplier

        if not policy["stats"]:
            return default_policy, None

        parts = []
        for reason, stat in policy["stats"].items():
            parts.append(
                f"{reason}:n={stat['count']},wr={stat['win_rate']:.2f},exp={stat['expectancy']:.2f},x{stat['multiplier']:.2f}"
            )
        summary = "exit policy: " + " | ".join(parts)
        return policy, summary
    except Exception as exc:
        logger.exception("Failed to recommend exit policy: %s", exc)
        return default_policy, None


def recommend_adverse_policy(read_closed_df, normalize_exit_reason, default_loss_usd: float, default_reverse_score: int, logger: logging.Logger):
    try:
        closed = read_closed_df()
        if len(closed) < 30:
            return float(default_loss_usd), int(default_reverse_score), None

        closed["profit"] = pd.to_numeric(closed["profit"], errors="coerce").fillna(0.0)
        closed["entry_score"] = pd.to_numeric(closed["entry_score"], errors="coerce").fillna(0.0)
        closed["exit_score"] = pd.to_numeric(closed["exit_score"], errors="coerce").fillna(0.0)
        closed = add_signed_exit_score(closed)
        closed["exit_reason"] = closed["exit_reason"].astype(str).fillna("")
        closed["exit_reason_norm"] = closed["exit_reason"].map(normalize_exit_reason)

        losses = closed[closed["profit"] < 0]["profit"].abs()
        new_loss_usd = float(default_loss_usd)
        if len(losses) >= 15:
            q35 = float(losses.quantile(0.35))
            q50 = float(losses.quantile(0.50))
            candidate = max(0.5, min(10.0, (q35 * 0.6) + (q50 * 0.4)))
            new_loss_usd = round(candidate, 2)

        adverse = closed[closed["exit_reason_norm"].isin(["Adverse Reversal", "Adverse Stop"])].copy()
        new_reverse = int(default_reverse_score)
        stats = {}
        if len(adverse) >= 12:
            rev = adverse[adverse["exit_reason_norm"] == "Adverse Reversal"]
            stop = adverse[adverse["exit_reason_norm"] == "Adverse Stop"]
            if len(rev) >= 6:
                good_rev = rev[rev["profit"] > 0]
                base = float(rev["signed_exit_score"].abs().quantile(0.45))
                if len(good_rev) >= 3:
                    base = float(good_rev["signed_exit_score"].abs().quantile(0.35))
                rev_expect = float(rev["profit"].mean()) if len(rev) > 0 else 0.0
                stop_expect = float(stop["profit"].mean()) if len(stop) > 0 else 0.0
                bias = 15 if rev_expect <= stop_expect else -10
                new_reverse = int(max(120, min(450, round(base + bias))))

            stats = {
                "adverse_rev_count": int(len(rev)),
                "adverse_stop_count": int(len(stop)),
                "adverse_rev_win_rate": round(float((rev["profit"] > 0).mean()), 3) if len(rev) > 0 else 0.0,
                "adverse_rev_exp": round(float(rev["profit"].mean()), 3) if len(rev) > 0 else 0.0,
                "adverse_stop_exp": round(float(stop["profit"].mean()), 3) if len(stop) > 0 else 0.0,
            }

        note = (
            f"adverse policy: loss_usd={new_loss_usd:.2f}, reverse_score={new_reverse}, "
            f"closed={len(closed)}, stats={stats}"
        )
        return new_loss_usd, new_reverse, note
    except Exception as exc:
        logger.exception("Failed to recommend adverse policy: %s", exc)
        return float(default_loss_usd), int(default_reverse_score), None
