from backend.services.manual_vs_heuristic_recent_window_audit import (
    build_manual_vs_heuristic_recent_window_audit,
)


def test_recent_window_audit_reports_overlap_counts(tmp_path) -> None:
    manual_path = tmp_path / "manual.csv"
    manual_path.write_text(
        "episode_id,symbol,anchor_time,manual_wait_teacher_label\n"
        "ep1,NAS100,2026-04-06T15:00:00+09:00,good_wait_better_entry\n"
        "ep2,BTCUSD,2026-04-06T09:00:00+09:00,bad_wait_missed_move\n",
        encoding="utf-8-sig",
    )
    current_path = tmp_path / "entry_decisions.csv"
    current_path.write_text(
        "time,symbol,barrier_candidate_recommended_family,belief_candidate_recommended_family,forecast_assist_v1,entry_wait_decision\n"
        "2026-04-06T14:00:00,NAS100,block_bias,buy_bias,{\"decision_hint\":\"OBSERVE_FAVOR\"},wait\n"
        "2026-04-06T16:00:00,BTCUSD,block_bias,buy_bias,{\"decision_hint\":\"OBSERVE_FAVOR\"},wait\n",
        encoding="utf-8-sig",
    )

    summary = build_manual_vs_heuristic_recent_window_audit(manual_path, current_path)

    assert summary["manual_episode_count"] == 2
    assert summary["recent_overlap_episode_count"] == 1
    assert summary["recent_overlap_symbol_counts"]["NAS100"] == 1
