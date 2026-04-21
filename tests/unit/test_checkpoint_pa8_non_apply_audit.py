from backend.services.checkpoint_pa8_non_apply_audit import (
    build_checkpoint_pa8_non_apply_audit,
    render_checkpoint_pa8_non_apply_audit_markdown,
)


def test_pa8_non_apply_audit_marks_missing_live_rows_as_primary_reason():
    payload = build_checkpoint_pa8_non_apply_audit(
        board_payload={
            "summary": {
                "generated_at": "2026-04-13T17:39:16+09:00",
                "recommended_next_action": "wait_for_market_reopen_and_refresh_canary_windows",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 2,
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
            "refreshed_payloads": {
                "NAS100": {
                    "first_window": {
                        "summary": {
                            "seed_reference_row_count": 82,
                            "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                        }
                    },
                    "closeout": {
                        "summary": {
                            "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                            "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                            "live_observation_ready": False,
                            "observed_window_row_count": 0,
                            "sample_floor": 50,
                            "active_trigger_count": 2,
                            "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                        },
                        "active_triggers": [
                            "runtime_proxy_match_rate_drop_below_baseline",
                            "partial_then_hold_quality_regression",
                        ],
                    },
                }
            },
        }
    )

    summary = payload["summary"]
    row = payload["rows"][0]

    assert summary["dominant_non_apply_reason_code"] == "no_post_activation_live_rows"
    assert row["primary_non_apply_reason_code"] == "no_post_activation_live_rows"
    assert row["seed_reference_row_count"] == 82
    assert row["sample_floor"] == 50
    assert row["active_trigger_labels_ko"] == [
        "runtime proxy match rate가 baseline 아래로 내려감",
        "partial-then-hold 품질이 baseline보다 나빠짐",
    ]


def test_pa8_non_apply_markdown_renders_symbol_summary():
    markdown = render_checkpoint_pa8_non_apply_audit_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T17:39:16+09:00",
                "active_symbol_count": 1,
                "live_observation_ready_count": 0,
                "dominant_non_apply_reason_ko": "활성화 이후 live row가 아직 쌓이지 않음",
                "recommended_next_action": "keep_canary_active_and_wait_for_post_activation_rows",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "primary_non_apply_reason_ko": "활성화 이후 live row가 아직 쌓이지 않음",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "seed_reference_row_count": 82,
                    "sample_floor": 50,
                    "progress_pct": 0.0,
                    "active_trigger_count": 2,
                    "active_trigger_labels_ko": ["partial-then-hold 품질이 baseline보다 나빠짐"],
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
        }
    )

    assert "PA8 Non-Apply Audit" in markdown
    assert "NAS100" in markdown
    assert "활성화 이후 live row가 아직 쌓이지 않음" in markdown
