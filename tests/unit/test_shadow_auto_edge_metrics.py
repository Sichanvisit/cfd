import pandas as pd

from backend.services import shadow_auto_edge_metrics as edge_metrics


def test_load_manual_truth_frame_includes_reviewed_shadow_overlap(monkeypatch, tmp_path) -> None:
    manual_path = tmp_path / "manual_wait_teacher_annotations.csv"
    shadow_path = tmp_path / "shadow_manual_overlap_seed_draft_latest.csv"

    pd.DataFrame(
        [
            {
                "annotation_id": "manual_1",
                "episode_id": "manual_1",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-04T13:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "manual_teacher_confidence": "medium",
                "annotation_source": "chart_annotated",
                "review_status": "accepted_coarse",
            }
        ]
    ).to_csv(manual_path, index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "annotation_id": "shadow_manual_seed::BTCUSD::2026-04-04T14:00:00::threshold::0.35",
                "episode_id": "shadow_manual_seed::BTCUSD::2026-04-04T14:00:00::threshold::0.35",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-04T14:00:00+09:00",
                "manual_wait_teacher_label": "neutral_wait_small_value",
                "manual_wait_teacher_confidence": "low",
                "manual_teacher_confidence": "low",
                "annotation_source": "assistant_shadow_overlap_reviewed",
                "review_status": "accepted_coarse",
            }
        ]
    ).to_csv(shadow_path, index=False, encoding="utf-8-sig")

    monkeypatch.setattr(edge_metrics, "DEFAULT_SHADOW_OVERLAP_REVIEWED_DRAFT_PATH", shadow_path)

    frame = edge_metrics.load_manual_truth_frame(manual_path)

    assert len(frame) == 2
    assert frame["annotation_source"].str.contains("shadow_overlap").any()


def test_attach_manual_truth_uses_shadow_overlap_window_bounds() -> None:
    frame = pd.DataFrame(
        [
            {"bridge_decision_time": "2026-04-04T14:10:00+09:00", "symbol": "BTCUSD"},
            {"bridge_decision_time": "2026-04-04T14:45:00+09:00", "symbol": "BTCUSD"},
        ]
    )
    manual_truth = pd.DataFrame(
        [
            {
                "annotation_id": "shadow_1",
                "episode_id": "shadow_1",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-04T14:00:00+09:00",
                "ideal_exit_time": "2026-04-04T14:30:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_confidence": "medium",
                "annotation_source": "assistant_shadow_overlap_reviewed",
                "review_status": "accepted_coarse",
            }
        ]
    )

    attached = edge_metrics.attach_manual_truth(frame, manual_truth, time_column="bridge_decision_time")

    assert bool(attached.iloc[0]["manual_reference_found"]) is True
    assert bool(attached.iloc[1]["manual_reference_found"]) is False


def test_resolve_wait_better_entry_premium_prefers_manual_then_bridge() -> None:
    premium = edge_metrics.resolve_wait_better_entry_premium(
        {
            "effective_target_action_variant": "wait_better_entry",
            "manual_target_action_variant": "wait_better_entry",
            "manual_wait_teacher_confidence": "high",
            "manual_wait_teacher_anchor_price": 100.0,
            "manual_wait_teacher_ideal_entry_price": 100.04,
            "mapped_target_action_variant": "wait_better_entry",
            "target_entry_quality_margin": 50.0,
        }
    )

    assert premium > 0.0
    assert premium <= edge_metrics.WAIT_BETTER_ENTRY_PREMIUM_MAX


def test_resolve_shadow_value_proxy_adds_wait_better_entry_premium() -> None:
    value = edge_metrics.resolve_shadow_value_proxy(
        baseline_realized_value=0.03,
        shadow_action_variant="wait_better_entry",
        effective_target_action_variant="wait_better_entry",
        wait_better_entry_premium=0.002,
    )

    assert value == 0.032
