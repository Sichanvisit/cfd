from pathlib import Path

from backend.services.multi_surface_preview_dataset_export import (
    build_multi_surface_preview_dataset_export,
    render_multi_surface_preview_dataset_export_markdown,
    write_multi_surface_preview_dataset_export,
)


def test_multi_surface_preview_dataset_export_materializes_surface_datasets() -> None:
    check_color_payload = {
        "rows": [
            {
                "annotation_id": "ann-1",
                "episode_id": "ep-1",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_label_family": "initial_entry_surface",
                "surface_label_state": "initial_break",
                "aligned_action_target": "ENTER_NOW",
                "aligned_continuation_target": "CONTINUE_AFTER_BREAK",
                "exit_management_support_label": "",
                "failure_label": "",
                "supervision_strength": "strong",
                "review_status": "promoted_canonical",
            },
            {
                "annotation_id": "ann-2",
                "episode_id": "ep-2",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "pullback_resume",
                "aligned_action_target": "ENTER_NOW",
                "aligned_continuation_target": "PULLBACK_THEN_CONTINUE",
                "exit_management_support_label": "",
                "failure_label": "failed_follow_through",
                "supervision_strength": "weak",
                "review_status": "reviewed",
            },
            {
                "annotation_id": "ann-3",
                "episode_id": "ep-3",
                "symbol": "BTCUSD",
                "market_family": "BTCUSD",
                "surface_label_family": "protective_exit_surface",
                "surface_label_state": "protect_exit",
                "aligned_action_target": "EXIT_PROTECT",
                "aligned_continuation_target": "CONTINUE_THEN_PROTECT",
                "exit_management_support_label": "EXIT_PROTECT",
                "failure_label": "",
                "supervision_strength": "strong",
                "review_status": "reviewed",
            },
        ]
    }
    surface_time_axis_payload = {
        "rows": [
            {
                "annotation_id": "ann-1",
                "episode_id": "ep-1",
                "market_family": "XAUUSD",
                "surface_label_family": "initial_entry_surface",
                "time_axis_phase": "fresh_initial",
                "time_axis_quality": "entry_exit_direct",
                "time_since_breakout_minutes": 1.5,
                "time_since_entry_minutes": 2.0,
                "bars_in_state": 2,
                "momentum_decay": 0.1,
            },
            {
                "annotation_id": "ann-2",
                "episode_id": "ep-2",
                "market_family": "XAUUSD",
                "surface_label_family": "follow_through_surface",
                "time_axis_phase": "continuation_window",
                "time_axis_quality": "entry_exit_direct",
                "time_since_breakout_minutes": 3.0,
                "time_since_entry_minutes": 4.5,
                "bars_in_state": 4,
                "momentum_decay": 0.2,
            },
            {
                "annotation_id": "ann-3",
                "episode_id": "ep-3",
                "market_family": "BTCUSD",
                "surface_label_family": "protective_exit_surface",
                "time_axis_phase": "protect_late",
                "time_axis_quality": "entry_exit_direct",
                "time_since_breakout_minutes": 7.0,
                "time_since_entry_minutes": 10.0,
                "bars_in_state": 8,
                "momentum_decay": 0.55,
            },
        ]
    }
    failure_label_payload = {
        "rows": [
            {
                "source_observation_id": "obs-1",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_label_family": "continuation_hold_surface",
                "surface_label_state": "runner_preservation_candidate",
                "failure_label": "early_exit_regret",
                "harvest_strength": "diagnostic",
                "harvest_source": "runtime_candidate",
                "time_axis_phase": "continuation_window",
                "time_since_breakout_minutes": 4.0,
                "time_since_entry_minutes": 6.0,
                "bars_in_state": 5,
                "momentum_decay": 0.22,
            }
        ]
    }
    market_adapter_payload = {
        "rows": [
            {
                "market_family": "XAUUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "xau_initial_adapter",
                "recommended_bias_action": "bias_release_wait",
                "objective_key": "entry_forward_ev",
                "positive_ev_proxy": "entry_forward_ev_proxy",
                "do_nothing_ev_proxy": "do_nothing_ev_proxy",
                "false_positive_cost_proxy": "entry_false_positive_cost_proxy",
                "current_focus": "xau_initial_focus",
            },
            {
                "market_family": "XAUUSD",
                "surface_name": "follow_through_surface",
                "adapter_mode": "xau_follow_through_relief_adapter",
                "recommended_bias_action": "bias_probe_relief",
                "objective_key": "follow_through_extension_ev",
                "positive_ev_proxy": "follow_through_extension_ev_proxy",
                "do_nothing_ev_proxy": "wait_more_ev_proxy",
                "false_positive_cost_proxy": "late_follow_through_penalty_proxy",
                "current_focus": "xau_follow_through_focus",
            },
            {
                "market_family": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "adapter_mode": "xau_runner_preservation_adapter",
                "recommended_bias_action": "bias_runner_hold",
                "objective_key": "runner_hold_ev",
                "positive_ev_proxy": "runner_hold_ev_proxy",
                "do_nothing_ev_proxy": "lock_profit_now_ev_proxy",
                "false_positive_cost_proxy": "runner_giveback_cost_proxy",
                "current_focus": "xau_runner_focus",
            },
            {
                "market_family": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "adapter_mode": "btc_protective_adapter",
                "recommended_bias_action": "bias_protective_dampen",
                "objective_key": "protect_exit_loss_avoidance_ev",
                "positive_ev_proxy": "protect_exit_loss_avoidance_ev_proxy",
                "do_nothing_ev_proxy": "hold_and_absorb_risk_ev_proxy",
                "false_positive_cost_proxy": "false_cut_regret_proxy",
                "current_focus": "btc_protective_focus",
            },
        ]
    }

    corpus, datasets, summary, rows = build_multi_surface_preview_dataset_export(
        check_color_payload,
        surface_time_axis_payload,
        failure_label_payload,
        market_adapter_payload,
    )
    markdown = render_multi_surface_preview_dataset_export_markdown(summary, corpus)

    assert len(corpus) == 4
    assert len(rows) == 4
    assert summary["corpus_row_count"] == 4
    assert summary["dataset_summaries"]["initial_entry"]["rows"] == 1
    assert summary["dataset_summaries"]["follow_through"]["rows"] == 1
    assert summary["dataset_summaries"]["continuation_hold"]["rows"] == 1
    assert summary["dataset_summaries"]["protective_exit"]["rows"] == 1
    assert datasets["initial_entry"].iloc[0]["enter_now_binary"] == 1
    assert datasets["follow_through"].iloc[0]["continuation_positive_binary"] == 1
    assert datasets["continuation_hold"].iloc[0]["hold_runner_binary"] == 1
    assert datasets["protective_exit"].iloc[0]["protect_exit_binary"] == 1
    assert datasets["follow_through"].iloc[0]["adapter_mode"] == "xau_follow_through_relief_adapter"
    assert "Multi-Surface Preview Dataset Export" in markdown


def test_multi_surface_preview_dataset_export_writer_outputs_files(tmp_path: Path) -> None:
    result = write_multi_surface_preview_dataset_export(
        check_color_payload={
            "rows": [
                {
                    "annotation_id": "ann-1",
                    "episode_id": "ep-1",
                    "symbol": "XAUUSD",
                    "market_family": "XAUUSD",
                    "surface_label_family": "follow_through_surface",
                    "surface_label_state": "pullback_resume",
                    "aligned_action_target": "ENTER_NOW",
                    "aligned_continuation_target": "PULLBACK_THEN_CONTINUE",
                    "supervision_strength": "weak",
                    "review_status": "reviewed",
                }
            ]
        },
        surface_time_axis_payload={
            "rows": [
                {
                    "annotation_id": "ann-1",
                    "episode_id": "ep-1",
                    "market_family": "XAUUSD",
                    "surface_label_family": "follow_through_surface",
                    "time_axis_phase": "continuation_window",
                    "time_axis_quality": "entry_exit_direct",
                    "time_since_breakout_minutes": 2.5,
                    "time_since_entry_minutes": 4.0,
                    "bars_in_state": 3,
                    "momentum_decay": 0.15,
                }
            ]
        },
        failure_label_payload={"rows": []},
        market_adapter_layer_payload={
            "rows": [
                {
                    "market_family": "XAUUSD",
                    "surface_name": "follow_through_surface",
                    "adapter_mode": "xau_follow_through_relief_adapter",
                    "recommended_bias_action": "bias_probe_relief",
                    "objective_key": "follow_through_extension_ev",
                    "positive_ev_proxy": "follow_through_extension_ev_proxy",
                    "do_nothing_ev_proxy": "wait_more_ev_proxy",
                    "false_positive_cost_proxy": "late_follow_through_penalty_proxy",
                    "current_focus": "xau_follow_through_focus",
                }
            ]
        },
        analysis_csv_path=tmp_path / "multi_surface_preview_dataset_export_latest.csv",
        analysis_json_path=tmp_path / "multi_surface_preview_dataset_export_latest.json",
        analysis_md_path=tmp_path / "multi_surface_preview_dataset_export_latest.md",
        dataset_dir=tmp_path / "datasets",
    )

    assert Path(result["analysis_csv_path"]).exists()
    assert Path(result["analysis_json_path"]).exists()
    assert Path(result["analysis_md_path"]).exists()
    assert result["summary"]["corpus_row_count"] == 1
    follow_output = result["dataset_outputs"]["follow_through"]
    assert Path(follow_output["csv_path"]).exists()
    assert follow_output["row_count"] == 1
