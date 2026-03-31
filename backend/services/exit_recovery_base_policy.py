"""Base recovery policy resolution for exit management."""

from __future__ import annotations


def _normalize_text(value: str, *, uppercase: bool = False) -> str:
    text = str(value or "").strip()
    return text.upper() if uppercase else text.lower()


def resolve_exit_recovery_base_policy_v1(
    *,
    symbol: str = "",
    management_profile_id: str = "",
    invalidation_id: str = "",
    entry_setup_id: str = "",
    default_be_max_loss_usd: float,
    default_tp1_max_loss_usd: float,
    default_max_wait_seconds: int,
    default_reverse_score_gap: int,
) -> dict:
    symbol_u = _normalize_text(symbol, uppercase=True)
    management_profile = _normalize_text(management_profile_id)
    invalidation = _normalize_text(invalidation_id)
    setup_id = _normalize_text(entry_setup_id)

    policy = {
        "policy_id": "default",
        "symbol": symbol_u,
        "management_profile_id": management_profile,
        "invalidation_id": invalidation,
        "entry_setup_id": setup_id,
        "allow_wait_be": True,
        "allow_wait_tp1": False,
        "prefer_reverse": False,
        "be_max_loss_usd": float(default_be_max_loss_usd),
        "tp1_max_loss_usd": float(default_tp1_max_loss_usd),
        "max_wait_seconds": int(default_max_wait_seconds),
        "reverse_score_gap": int(default_reverse_score_gap),
    }

    if management_profile == "reversal_profile":
        if symbol_u == "BTCUSD":
            policy.update(
                {
                    "policy_id": "reversal_profile_btc_tight",
                    "allow_wait_be": False,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.18),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 45),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 26),
                }
            )
        else:
            policy.update(
                {
                    "policy_id": "reversal_profile",
                    "allow_wait_be": True,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.45),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 90),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 24),
                }
            )
    elif management_profile == "support_hold_profile" and not (
        symbol_u == "BTCUSD" and setup_id == "range_lower_reversal_buy"
    ):
        policy.update(
            {
                "policy_id": "support_hold_profile",
                "allow_wait_be": True,
                "allow_wait_tp1": True,
                "prefer_reverse": False,
                "be_max_loss_usd": max(0.10, float(default_be_max_loss_usd)),
                "tp1_max_loss_usd": max(0.10, float(default_tp1_max_loss_usd) + 0.10),
                "max_wait_seconds": min(int(default_max_wait_seconds), 180),
                "reverse_score_gap": max(10, int(default_reverse_score_gap) - 4),
            }
        )
    elif management_profile in {"breakout_hold_profile", "breakdown_hold_profile"}:
        policy.update(
            {
                "policy_id": management_profile,
                "allow_wait_be": False,
                "allow_wait_tp1": False,
                "prefer_reverse": True,
                "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.25),
                "tp1_max_loss_usd": 0.0,
                "max_wait_seconds": min(int(default_max_wait_seconds), 60),
                "reverse_score_gap": max(10, int(default_reverse_score_gap) - 6),
            }
        )
    elif management_profile in {"mid_reclaim_fast_exit_profile", "mid_lose_fast_exit_profile"}:
        policy.update(
            {
                "policy_id": management_profile,
                "allow_wait_be": False,
                "allow_wait_tp1": False,
                "prefer_reverse": False,
                "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.25),
                "tp1_max_loss_usd": 0.0,
                "max_wait_seconds": min(int(default_max_wait_seconds), 45),
                "reverse_score_gap": max(int(default_reverse_score_gap), 20),
            }
        )
    elif setup_id == "range_upper_reversal_sell":
        if symbol_u == "BTCUSD":
            policy.update(
                {
                    "policy_id": "range_upper_reversal_sell_btc_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.45),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 90),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 24),
                }
            )
        elif symbol_u == "NAS100":
            policy.update(
                {
                    "policy_id": "range_upper_reversal_sell_nas_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": True,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.60),
                    "tp1_max_loss_usd": min(float(default_tp1_max_loss_usd), 0.20),
                    "max_wait_seconds": min(int(default_max_wait_seconds), 120),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 26),
                }
            )
        else:
            policy.update(
                {
                    "policy_id": "range_upper_reversal_sell_tight",
                    "allow_wait_be": True,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.45),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 90),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 24),
                }
            )
    elif setup_id == "range_lower_reversal_buy":
        if symbol_u == "NAS100":
            policy.update(
                {
                    "policy_id": "range_lower_reversal_buy_nas_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": True,
                    "prefer_reverse": False,
                    "be_max_loss_usd": max(0.20, float(default_be_max_loss_usd)),
                    "tp1_max_loss_usd": max(0.18, float(default_tp1_max_loss_usd) + 0.12),
                    "max_wait_seconds": min(int(default_max_wait_seconds), 240),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 26),
                }
            )
        elif symbol_u == "XAUUSD":
            policy.update(
                {
                    "policy_id": "range_lower_reversal_buy_xau_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": True,
                    "prefer_reverse": False,
                    "be_max_loss_usd": max(0.20, float(default_be_max_loss_usd)),
                    "tp1_max_loss_usd": max(0.20, float(default_tp1_max_loss_usd) + 0.12),
                    "max_wait_seconds": max(int(default_max_wait_seconds), 255),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 26),
                }
            )
        elif symbol_u == "BTCUSD":
            policy.update(
                {
                    "policy_id": "range_lower_reversal_buy_btc_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": True,
                    "prefer_reverse": False,
                    "be_max_loss_usd": max(0.24, float(default_be_max_loss_usd)),
                    "tp1_max_loss_usd": max(0.24, float(default_tp1_max_loss_usd) + 0.16),
                    "max_wait_seconds": max(int(default_max_wait_seconds), 300),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 32),
                }
            )
        else:
            policy.update(
                {
                    "policy_id": "range_reversal",
                    "allow_wait_be": True,
                    "allow_wait_tp1": True,
                    "prefer_reverse": False,
                    "be_max_loss_usd": max(0.10, float(default_be_max_loss_usd)),
                    "tp1_max_loss_usd": max(0.10, float(default_tp1_max_loss_usd) + 0.10),
                    "max_wait_seconds": min(int(default_max_wait_seconds), 180),
                    "reverse_score_gap": max(10, int(default_reverse_score_gap) - 4),
                }
            )
    elif setup_id in {"trend_pullback_buy", "trend_pullback_sell"}:
        policy.update(
            {
                "policy_id": "trend_pullback",
                "allow_wait_be": True,
                "allow_wait_tp1": False,
                "prefer_reverse": False,
                "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.60),
                "tp1_max_loss_usd": min(float(default_tp1_max_loss_usd), 0.20),
                "max_wait_seconds": min(int(default_max_wait_seconds), 120),
                "reverse_score_gap": max(int(default_reverse_score_gap), 22),
            }
        )
    elif setup_id in {"breakout_retest_buy", "breakout_retest_sell"}:
        if symbol_u == "XAUUSD" and setup_id == "breakout_retest_sell":
            policy.update(
                {
                    "policy_id": "breakout_retest_xau_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.45),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 90),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 24),
                }
            )
        elif symbol_u == "NAS100" and setup_id == "breakout_retest_sell":
            policy.update(
                {
                    "policy_id": "breakout_retest_nas_balanced",
                    "allow_wait_be": True,
                    "allow_wait_tp1": False,
                    "prefer_reverse": False,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.55),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 120),
                    "reverse_score_gap": max(int(default_reverse_score_gap), 26),
                }
            )
        else:
            policy.update(
                {
                    "policy_id": "breakout_retest",
                    "allow_wait_be": False,
                    "allow_wait_tp1": False,
                    "prefer_reverse": True,
                    "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.25),
                    "tp1_max_loss_usd": 0.0,
                    "max_wait_seconds": min(int(default_max_wait_seconds), 60),
                    "reverse_score_gap": max(10, int(default_reverse_score_gap) - 6),
                }
            )
    elif invalidation in {"breakout_failure", "breakdown_failure"}:
        policy.update(
            {
                "policy_id": "breakout_failure",
                "allow_wait_be": False,
                "allow_wait_tp1": False,
                "prefer_reverse": True,
                "be_max_loss_usd": min(float(default_be_max_loss_usd), 0.25),
                "tp1_max_loss_usd": 0.0,
                "max_wait_seconds": min(int(default_max_wait_seconds), 60),
                "reverse_score_gap": max(10, int(default_reverse_score_gap) - 6),
            }
        )

    return policy
