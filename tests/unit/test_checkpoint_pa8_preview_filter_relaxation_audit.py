from backend.services.checkpoint_pa8_preview_filter_relaxation_audit import (
    build_checkpoint_pa8_preview_filter_relaxation_audit,
)


def test_pa8_preview_filter_relaxation_audit_extracts_scope_review_candidates() -> None:
    payload = build_checkpoint_pa8_preview_filter_relaxation_audit(
        root_cause_payload={
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "root_cause_code": "preview_filter_rejection_dominant",
                    "post_activation_row_count": 40,
                    "preview_changed_row_count": 0,
                    "preview_reason_counts": {
                        "preview_surface_out_of_scope": 20,
                        "preview_checkpoint_out_of_scope": 8,
                    },
                    "surface_counts": {
                        "follow_through_surface": 14,
                        "protective_exit_surface": 6,
                    },
                    "checkpoint_type_counts": {
                        "RUNNER_CHECK": 5,
                        "RECLAIM_CHECK": 3,
                    },
                }
            ]
        }
    )

    row = payload["rows"][0]
    assert row["symbol"] == "BTCUSD"
    assert len(row["relaxation_candidates"]) >= 2
    candidate_codes = {item["candidate_code"] for item in row["relaxation_candidates"]}
    assert "expand_surface_scope_review" in candidate_codes
    assert "expand_checkpoint_type_review" in candidate_codes
    assert "BTCUSD" in payload["summary"]["symbols_needing_scope_review"]
