from backend.fastapi.runtime_market_view import build_current_market_view


def _payload_for(symbol: str, *, primary_label: str, reason: str, action: str = "WAIT", side: str = ""):
    return {
        "updated_at": "2026-03-12T14:47:02+09:00",
        "symbols": [symbol],
        "latest_signal_by_symbol": {
            symbol: {
                "market_mode": "RANGE",
                "liquidity_state": "GOOD",
                "position_snapshot_v2": {
                    "zones": {
                        "box_zone": "LOWER",
                        "bb20_zone": "MIDDLE",
                        "bb44_zone": "MIDDLE",
                    },
                    "interpretation": {
                        "primary_label": primary_label,
                        "bias_label": "LOWER_BIAS",
                        "secondary_context_label": "LOWER_CONTEXT",
                    },
                    "energy": {
                        "lower_position_force": 0.31,
                        "upper_position_force": 0.02,
                        "middle_neutrality": 0.0,
                    },
                },
                "current_entry_context_v1": {
                    "metadata": {
                        "preflight_allowed_action_raw": "BOTH",
                        "state_raw_snapshot_v1": {
                            "market_mode": "RANGE",
                            "liquidity_state": "GOOD",
                        },
                        "observe_confirm_v2": {
                            "state": "OBSERVE",
                            "action": action,
                            "side": side,
                            "reason": reason,
                        },
                    }
                },
            }
        },
    }


def test_runtime_market_view_builds_lower_observe_summary():
    payload = _payload_for(
        "NAS100",
        primary_label="LOWER_BIAS",
        reason="lower_edge_observe",
        action="WAIT",
        side="BUY",
    )

    view = build_current_market_view(payload)

    assert view["updated_at"] == "2026-03-12T14:47:02+09:00"
    assert len(view["items"]) == 1
    item = view["items"][0]
    assert item["symbol"] == "NAS100"
    assert item["action_badge"] == "BUY 관찰"
    assert "하단 컨텍스트" in item["decision_summary"]
    assert "박스 하단" in item["location_summary"]
    assert any(log["label"] == "게이트" for log in item["logs"])


def test_runtime_market_view_builds_middle_wait_summary():
    payload = _payload_for(
        "XAUUSD",
        primary_label="ALIGNED_MIDDLE",
        reason="middle_wait",
        action="WAIT",
        side="",
    )

    view = build_current_market_view(payload)
    item = view["items"][0]

    assert item["action_badge"] == "중립 대기"
    assert "중앙 구간" in item["position_summary"]
    assert "지지/저항 anchor" in item["next_trigger"]
