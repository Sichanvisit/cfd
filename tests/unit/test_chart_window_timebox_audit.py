import json

from backend.services.chart_window_timebox_audit import (
    build_chart_window_timebox_audit,
    generate_and_write_chart_window_timebox_audit,
)


def test_build_chart_window_timebox_audit_summarizes_rows_and_phases(tmp_path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    rows = [
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-14T16:36:00",
                "symbol": "NAS100",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "trend_resume_watch",
                "outcome": "skipped",
            },
        },
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-14T16:40:00",
                "symbol": "NAS100",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "PROBE",
                "consumer_check_reason": "trend_resume_probe",
                "outcome": "skipped",
            },
        },
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-14T16:44:00",
                "symbol": "NAS100",
                "action": "BUY",
                "outcome": "entered",
            },
        },
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-14T16:48:00",
                "symbol": "NAS100",
                "consumer_check_side": "SELL",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "wrong_side_sell_watch",
                "outcome": "skipped",
            },
        },
    ]
    detail_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    report = build_chart_window_timebox_audit(
        detail_path,
        [
            {
                "window_id": "nas_resume",
                "symbol": "NAS100",
                "label": "NAS trend resume",
                "anchor_note": "16:36 breakout base",
                "start": "2026-04-14T16:35:00",
                "end": "2026-04-14T16:50:00",
                "expected_phases": [
                    {
                        "name": "trend_resume",
                        "start": "2026-04-14T16:35:00",
                        "end": "2026-04-14T16:50:00",
                        "preferred_families": ["BUY_WATCH", "BUY_PROBE", "BUY_ENTER"],
                        "forbidden_families": ["SELL_WATCH", "SELL_ENTER"],
                        "note": "should stay buy-side",
                    }
                ],
            }
        ],
    )

    assert report["windows"][0]["row_count"] == 4
    assert report["windows"][0]["top_actual_family_counts"][0][0] == "BUY_WATCH"
    phase = report["windows"][0]["expected_phase_reports"][0]
    assert phase["preferred_hit_count"] == 3
    assert phase["forbidden_hit_count"] == 1
    assert phase["alignment_state"] == "MIXED"


def test_generate_and_write_chart_window_timebox_audit_writes_artifacts(tmp_path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "payload": {
                    "time": "2026-04-14T17:32:00",
                    "symbol": "XAUUSD",
                    "consumer_check_side": "SELL",
                    "consumer_check_stage": "PROBE",
                    "consumer_check_reason": "down_continuation_probe",
                    "outcome": "skipped",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = generate_and_write_chart_window_timebox_audit(
        detail_path,
        [
            {
                "window_id": "xau_downturn",
                "symbol": "XAUUSD",
                "label": "XAU down turn",
                "start": "2026-04-14T17:30:00",
                "end": "2026-04-14T17:40:00",
            }
        ],
        shadow_auto_dir=tmp_path,
        output_stem="nas_xau_window_audit_latest",
    )

    assert (tmp_path / "nas_xau_window_audit_latest.json").exists()
    assert (tmp_path / "nas_xau_window_audit_latest.md").exists()
    assert report["artifact_paths"]["json_path"].endswith("nas_xau_window_audit_latest.json")
