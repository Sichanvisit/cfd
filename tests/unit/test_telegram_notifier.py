from backend.integrations import notifier


def test_resolve_runtime_destination_uses_existing_dm(monkeypatch):
    monkeypatch.setattr(notifier.Config, "TG_CHAT_ID", "7210042241", raising=False)
    chat_id, thread_id = notifier._resolve_destination(route="runtime")
    assert chat_id == "7210042241"
    assert thread_id is None


def test_resolve_report_destination_uses_report_topic(monkeypatch):
    monkeypatch.setattr(notifier.Config, "TG_REPORT_CHAT_ID", "-1003749911122", raising=False)
    monkeypatch.setattr(notifier.Config, "TG_REPORT_TOPIC_ID", 32, raising=False)
    chat_id, thread_id = notifier._resolve_destination(route="report")
    assert chat_id == "-1003749911122"
    assert thread_id == "32"


def test_resolve_pnl_destination_by_window_code(monkeypatch):
    monkeypatch.setattr(notifier.Config, "TG_PNL_FORUM_CHAT_ID", "-1003749911122", raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_15M_ID", 32, raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_1H_ID", 30, raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_4H_ID", 3, raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_1D_ID", 5, raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_1W_ID", 7, raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_1M_ID", 9, raising=False)

    chat_id, thread_id = notifier._resolve_destination(route="pnl", window_code="15m")
    assert chat_id == "-1003749911122"
    assert thread_id == "32"

    chat_id, thread_id = notifier._resolve_destination(route="pnl", window_code="1H")
    assert chat_id == "-1003749911122"
    assert thread_id == "30"


def test_resolve_pnl_destination_rejects_runtime_1m_window(monkeypatch):
    monkeypatch.setattr(notifier.Config, "TG_PNL_FORUM_CHAT_ID", "-1003749911122", raising=False)
    monkeypatch.setattr(notifier.Config, "TG_PNL_TOPIC_1M_ID", 9, raising=False)
    chat_id, thread_id = notifier._resolve_destination(route="pnl", window_code="1m")
    assert chat_id == ""
    assert thread_id is None


def test_build_flow_shadow_zone_line_summarizes_zone_and_chart_override():
    line = notifier._build_flow_shadow_zone_line(
        {
            "flow_shadow_entry_zone_state_v1": "OPPOSITE_EDGE_CHASE",
            "flow_shadow_chart_event_final_kind_v1": "BUY_WAIT",
            "flow_shadow_caution_flags_v1": ["OPPOSITE_EDGE_CHASE", "TURN_RISK_RISING"],
        }
    )
    assert "OPPOSITE_EDGE_CHASE" in line
    assert "BUY_WAIT" in line
    assert "TURN_RISK_RISING" in line


def test_format_entry_message_mentions_runtime_and_side():
    message = notifier.format_entry_message(
        symbol="BTCUSD",
        action="BUY",
        score=381,
        price=83210.5,
        lot=0.05,
        reasons=["lower rebound confirm", "bb20 reclaim"],
        pos_count=1,
        max_pos=3,
        row={
            "runtime_scene_fine_label": "pullback_continuation",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence_band": "high",
            "position_energy_surface_v1": {
                "energy": {
                    "lower_position_force": 0.18,
                    "upper_position_force": 0.02,
                    "middle_neutrality": 0.00,
                }
            },
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "LOWER",
                    }
                }
            },
        },
    )
    assert "*진입*" in message
    assert "방향: *BUY*" in message
    assert "주도축:" in message
    assert "핵심리스크:" in message
    assert "강도:" in message
    assert "위/아래 힘:" in message
    assert "구조 정합:" in message
    assert "정합 ✅" in message
    assert "장면:" in message
    assert "게이트: 없음" in message
    assert "확신: 높음" in message
    assert "사유:" in message
    assert "Score:" not in message
    assert "진입 근거" not in message


def test_format_entry_message_breakout_scene_marks_buy_upper_as_aligned():
    message = notifier.format_entry_message(
        symbol="NAS100",
        action="BUY",
        score=221,
        price=24921.3,
        lot=0.05,
        reasons=["breakout", "bb20 reclaim"],
        pos_count=1,
        max_pos=3,
        row={
            "runtime_scene_fine_label": "breakout_retest_hold",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence_band": "medium",
            "position_energy_surface_v1": {
                "energy": {
                    "lower_position_force": 0.04,
                    "upper_position_force": 0.31,
                    "middle_neutrality": 0.01,
                }
            },
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
        },
    )
    assert "구조 정합:" in message
    assert "돌파/리클레임 계열 기준 정합 ✅" in message


def test_format_exit_message_mentions_runtime_result():
    message = notifier.format_exit_message(
        symbol="BTCUSD",
        profit=44.2,
        points=61,
        entry_price=83210.5,
        exit_price=83652.3,
        exit_reason="protective_loss_exit",
        review_context={
            "shock_level": "watch",
            "shock_reason": "opposite_score_spike",
            "pre_shock_stage": "runner_hold",
            "post_shock_stage": "fast_exit",
        },
    )
    assert "*청산*" in message
    assert "결과: *이익*" in message
    assert "손익: *+44.20 USD*" in message
    assert "청산사유:" in message
    assert "복기힌트: 쇼크 주의 대응 복기 / runner_hold->fast_exit" in message


def test_format_wait_message_mentions_wait_and_context():
    message = notifier.format_wait_message(
        symbol="BTCUSD",
        action="SELL",
        price=73144.4,
        pos_count=1,
        max_pos=3,
        reason="forecast_guard",
        row={
            "entry_wait_state": "HARD_WAIT",
            "entry_wait_decision": "wait",
            "forecast_state25_runtime_bridge_v1": {
                "forecast_runtime_summary_v1": {
                    "available": True,
                    "decision_hint": "WAIT_BIASED",
                    "confirm_side": "SELL",
                }
            },
            "belief_state25_runtime_bridge_v1": {
                "belief_runtime_summary_v1": {
                    "available": True,
                    "acting_side": "SELL",
                    "persistence_hint": "STABLE",
                }
            },
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "available": True,
                    "blocking_bias": "WAIT_BLOCK",
                    "top_component": "conflict_barrier",
                    "top_component_reason": "conflict_barrier",
                },
                "state25_runtime_hint_v1": {
                    "available": True,
                    "scene_pattern_name": "trend_exhaustion",
                    "confidence": 0.67,
                },
            },
            "position_energy_surface_v1": {
                "energy": {
                    "lower_position_force": 0.00,
                    "upper_position_force": 0.36,
                    "middle_neutrality": 0.01,
                }
            },
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
        },
    )
    assert "*대기*" in message
    assert "방향: *SELL*" in message
    assert "대기이유:" in message
    assert "해제조건:" in message
    assert "위/아래 힘:" in message
    assert "구조 정합:" in message
    assert "정합 ✅" in message
    assert "장면:" in message
    assert "게이트: 주의" in message
    assert "베리어:" in message
    assert "빌리프:" in message
    assert "포리캐스트:" in message


def test_format_reverse_message_mentions_reverse_state():
    message = notifier.format_reverse_message(
        symbol="BTCUSD",
        action="BUY",
        score=262,
        price=73144.4,
        reasons=["opposite_score_spike", "volatility_spike"],
        pos_count=1,
        max_pos=3,
        pending=True,
        row={
            "runtime_scene_fine_label": "trend_exhaustion",
            "runtime_scene_gate_label": "caution",
            "runtime_scene_confidence_band": "medium",
            "runtime_scene_transition_from": "runner_healthy",
            "runtime_scene_transition_bars": 2,
            "htf_alignment_state": "AGAINST_HTF",
            "htf_alignment_detail": "AGAINST_HTF_DOWN",
            "htf_against_severity": "MEDIUM",
            "previous_box_break_state": "BREAKOUT_HELD",
            "late_chase_risk_state": "HIGH",
            "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
            "position_energy_surface_v1": {
                "energy": {
                    "lower_position_force": 0.03,
                    "upper_position_force": 0.29,
                    "middle_neutrality": 0.00,
                }
            },
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
        },
    )
    assert "*반전*" in message
    assert "방향: *BUY*" in message
    assert "상태:" in message
    assert "주도축:" in message
    assert "핵심리스크:" in message
    assert "강도:" in message
    assert "위/아래 힘:" in message
    assert "구조 정합:" in message
    assert "엇갈림 ⚠️" in message
    assert "장면:" in message
    assert "전이:" in message
    assert "사유:" in message
    assert "반대 점수 급변" in message or "변동성 급등" in message


def test_format_reverse_message_includes_context_line_when_runtime_context_exists():
    message = notifier.format_reverse_message(
        symbol="NAS100",
        action="SELL",
        score=245,
        price=25031.3,
        reasons=["opposite_score_spike"],
        pos_count=1,
        max_pos=3,
        pending=False,
        row={
            "runtime_scene_fine_label": "trend_exhaustion",
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
            "htf_alignment_state": "AGAINST_HTF",
            "htf_alignment_detail": "AGAINST_HTF_UP",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "late_chase_risk_state": "HIGH",
            "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        },
    )
    assert "맥락:" in message
    assert "현재만 하락 역행" in message
    assert "직전 박스 상단 돌파 유지" in message


def test_build_runtime_context_line_summarizes_state_first_context():
    line = notifier._build_runtime_context_line(
        {
            "htf_alignment_state": "AGAINST_HTF",
            "htf_alignment_detail": "AGAINST_HTF_UP",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "late_chase_risk_state": "HIGH",
            "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        }
    )
    assert "현재만 하락 역행" in line
    assert "직전 박스 상단 돌파 유지" in line
    assert "늦은 추격 위험 높음" in line


def test_format_entry_message_includes_context_line_when_runtime_context_exists():
    message = notifier.format_entry_message(
        symbol="NAS100",
        action="SELL",
        score=245,
        price=25031.3,
        lot=0.05,
        reasons=["upper_break_fail_confirm"],
        pos_count=1,
        max_pos=3,
        row={
            "runtime_scene_fine_label": "breakout_retest_hold",
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
            "htf_alignment_state": "AGAINST_HTF",
            "htf_alignment_detail": "AGAINST_HTF_UP",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "late_chase_risk_state": "HIGH",
            "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        },
    )
    assert "맥락:" in message
    assert "현재만 하락 역행" in message
    assert "직전 박스 상단 돌파 유지" in message


def test_format_wait_message_includes_context_line_when_runtime_context_exists():
    message = notifier.format_wait_message(
        symbol="NAS100",
        action="SELL",
        price=25031.3,
        pos_count=1,
        max_pos=3,
        reason="forecast_guard",
        row={
            "entry_wait_state": "HARD_WAIT",
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
            "htf_alignment_state": "AGAINST_HTF",
            "htf_alignment_detail": "AGAINST_HTF_UP",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "late_chase_risk_state": "EARLY_WARNING",
            "late_chase_reason": "EXTENDED_ABOVE_PREV_BOX",
        },
    )
    assert "맥락:" in message
    assert "현재만 하락 역행" in message
    assert "직전 박스 상단 돌파 유지" in message


def test_build_runtime_force_alignment_line_returns_neutral_when_scene_unknown():
    line = notifier._build_runtime_force_alignment_line(
        "BUY",
        {
            "runtime_scene_fine_label": "unresolved",
            "position_snapshot_v2": {
                "energy": {
                    "metadata": {
                        "position_dominance": "UPPER",
                    }
                }
            },
        },
    )
    assert "장면 미확정" in line
    assert "중립 ➖" in line


def test_build_wait_message_signature_changes_when_reason_changes():
    base_row = {
        "entry_wait_state": "HARD_WAIT",
        "entry_wait_decision": "wait",
    }
    first = notifier.build_wait_message_signature(
        "BTCUSD",
        "SELL",
        reason="forecast_guard",
        row=base_row,
    )
    second = notifier.build_wait_message_signature(
        "BTCUSD",
        "SELL",
        reason="entry_cooldown",
        row=base_row,
    )
    assert first
    assert second
    assert first != second


def test_build_reverse_message_signature_changes_when_pending_changes():
    first = notifier.build_reverse_message_signature(
        "BTCUSD",
        "BUY",
        262,
        ["opposite_score_spike"],
        pending=False,
    )
    second = notifier.build_reverse_message_signature(
        "BTCUSD",
        "BUY",
        262,
        ["opposite_score_spike"],
        pending=True,
    )
    assert first
    assert second
    assert first != second


def test_format_wait_message_includes_flow_shadow_axes_and_start_line():
    message = notifier.format_wait_message(
        symbol="BTCUSD",
        action="BUY",
        price=74008.5,
        pos_count=0,
        max_pos=3,
        reason="lower_rebound_probe_observe",
        row={
            "consumer_check_side": "BUY",
            "flow_shadow_continuation_persistence_prob_v1": 0.52,
            "flow_shadow_entry_quality_prob_v1": 0.21,
            "flow_shadow_reversal_risk_prob_v1": 0.44,
            "flow_shadow_start_marker_state_v1": "FALLBACK_START_WATCH",
            "flow_shadow_start_marker_event_kind_v1": "BUY_WATCH",
        },
    )
    assert "Shadow: 지속 52% / 진입 21% / 반전 44%" in message
    assert "FlowStart: BUY_WATCH" in message
