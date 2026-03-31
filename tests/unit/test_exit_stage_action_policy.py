from backend.services.exit_stage_action_policy import (
    resolve_exit_stage_action_candidate_v1,
)


def test_exit_stage_action_candidate_returns_protect_exit():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="protect",
        allow_short=True,
        green_hold_soft_exit=False,
        chosen_stage="protect",
        protect_streak=3,
        confirm_short=2,
        profit=0.02,
        min_target_profit=0.05,
        hold_strong=False,
        protect_score=80,
        lock_score=42,
        hold_score=10,
        exit_detail="detail",
        route_txt="route",
    )

    assert out["should_execute"] is True
    assert out["reason"] == "Protect Exit"
    assert "exit_protect" in list(out["metric_keys"])


def test_exit_stage_action_candidate_returns_adverse_recheck_lock():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="adverse_recheck",
        allow_short=True,
        profit=0.18,
        min_target_profit=0.05,
        min_net_guard=0.10,
        hold_strong=False,
        protect_score=70,
        lock_score=88,
        hold_score=20,
        exit_detail="detail",
        protect_now=False,
        lock_now=True,
    )

    assert out["should_execute"] is True
    assert out["reason"] == "Lock Exit"
    assert "adverse_recheck_hits" in list(out["metric_keys"])


def test_exit_stage_action_candidate_returns_time_stop():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="mid_stage",
        allow_mid=True,
        green_hold_soft_exit=False,
        chosen_stage="auto",
        lock_streak=0,
        confirm_mid=2,
        profit=0.01,
        min_target_profit=0.05,
        min_net_guard=0.10,
        hold_strong=False,
        protect_score=20,
        lock_score=20,
        hold_score=10,
        exit_detail="detail",
        route_txt="route",
        duration_sec=3600.0,
        dynamic_move_pct=0.0012,
        favorable_move_pct=0.0001,
        hard_profit_target=0.10,
        is_trend_mode=False,
    )

    assert out["should_execute"] is True
    assert out["candidate_kind"] == "time_stop"
    assert float(out["stale_threshold"]) > 0.0


def test_exit_stage_action_candidate_returns_lock_exit():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="mid_stage",
        allow_mid=True,
        green_hold_soft_exit=False,
        chosen_stage="lock",
        lock_streak=3,
        confirm_mid=2,
        profit=0.18,
        min_target_profit=0.05,
        min_net_guard=0.10,
        hold_strong=False,
        protect_score=55,
        lock_score=90,
        hold_score=12,
        exit_detail="detail",
        route_txt="route",
        duration_sec=120.0,
        dynamic_move_pct=0.0012,
        favorable_move_pct=0.0025,
        hard_profit_target=0.40,
        is_trend_mode=False,
    )

    assert out["should_execute"] is True
    assert out["candidate_kind"] == "lock_exit"


def test_exit_stage_action_candidate_returns_target_exit():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="mid_stage",
        allow_mid=True,
        green_hold_soft_exit=False,
        chosen_stage="auto",
        lock_streak=0,
        confirm_mid=2,
        profit=0.22,
        min_target_profit=0.12,
        min_net_guard=0.10,
        hold_strong=False,
        protect_score=30,
        lock_score=30,
        hold_score=10,
        exit_detail="detail",
        route_txt="route",
        duration_sec=120.0,
        dynamic_move_pct=0.0012,
        favorable_move_pct=0.0030,
        hard_profit_target=0.10,
        is_trend_mode=False,
    )

    assert out["should_execute"] is True
    assert out["candidate_kind"] == "target_exit"


def test_exit_stage_action_candidate_skips_target_under_trend_guard():
    out = resolve_exit_stage_action_candidate_v1(
        candidate_scope="mid_stage",
        allow_mid=True,
        green_hold_soft_exit=False,
        chosen_stage="auto",
        lock_streak=0,
        confirm_mid=2,
        profit=0.12,
        min_target_profit=0.10,
        min_net_guard=0.10,
        hold_strong=False,
        protect_score=30,
        lock_score=30,
        hold_score=10,
        exit_detail="detail",
        route_txt="route",
        duration_sec=120.0,
        dynamic_move_pct=0.0012,
        favorable_move_pct=0.0030,
        hard_profit_target=0.10,
        is_trend_mode=True,
    )

    assert out["should_execute"] is False
