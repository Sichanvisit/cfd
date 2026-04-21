import pandas as pd

from backend.services.manual_truth_corpus_freshness import (
    build_manual_truth_corpus_freshness,
)


def test_manual_truth_corpus_freshness_flags_recent_draft_vs_stale_symbol() -> None:
    canonical = pd.DataFrame(
        [
            {
                "episode_id": "canon_nas",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T17:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
            },
            {
                "episode_id": "canon_xau",
                "symbol": "XAUUSD",
                "anchor_time": "2026-04-05T10:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
            },
        ]
    )
    draft = pd.DataFrame(
        [
            {
                "episode_id": "draft_nas",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T18:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "queue_id": "current_rich::NAS100::2026-04-06T18:00:00",
                "symbol": "NAS100",
                "window_start": "2026-04-06T18:00:00",
            }
        ]
    )
    current_entry = pd.DataFrame(
        [
            {"symbol": "NAS100", "heuristic_time": pd.Timestamp("2026-04-06T19:00:00+09:00")},
            {"symbol": "XAUUSD", "heuristic_time": pd.Timestamp("2026-04-06T19:00:00+09:00")},
        ]
    )

    freshness, summary = build_manual_truth_corpus_freshness(canonical, draft, queue, current_entry)

    nas = freshness[freshness["symbol"] == "NAS100"].iloc[0]
    xau = freshness[freshness["symbol"] == "XAUUSD"].iloc[0]
    assert nas["freshness_class"] == "current_rich_ready"
    assert xau["freshness_class"] == "stale"
    assert summary["symbol_count"] == 2
