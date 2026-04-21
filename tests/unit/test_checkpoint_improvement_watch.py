from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_watch import (
    _default_governance_board_loader,
    run_checkpoint_improvement_watch_heavy_cycle,
    run_checkpoint_improvement_watch_governance_cycle,
    run_checkpoint_improvement_watch_light_cycle,
)
from backend.services.event_bus import (
    EventBus,
    GovernanceActionNeeded,
    LightRefreshCompleted,
    SystemPhaseChanged,
    WatchError,
)
from backend.services.system_state_manager import SystemStateManager


def _write_rows(path: Path, rows: list[str]) -> None:
    path.write_text(
        "generated_at,symbol\n" + "\n".join(rows) + ("\n" if rows else ""),
        encoding="utf-8-sig",
    )


def test_light_cycle_skips_when_checkpoint_rows_are_missing(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    bus = EventBus()

    payload = run_checkpoint_improvement_watch_light_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=tmp_path / "missing.csv",
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
    )

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "checkpoint_rows_missing"
    assert manager.get_state()["phase"] == "STARTING"
    assert bus.pending_count() == 0
    assert (tmp_path / "watch_report.json").exists()
    assert (tmp_path / "watch_report.md").exists()


def test_light_cycle_first_tick_refreshes_and_publishes_events(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(
        rows_path,
        [
            "2026-04-11T10:00:00+09:00,BTCUSD",
            "2026-04-11T10:01:00+09:00,NAS100",
        ],
    )
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(LightRefreshCompleted, lambda event: seen_events.append(event.event_type))
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _refresh_stub(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "trigger_state": "REFRESHED",
                "recommended_next_action": "ok",
                "row_count_after": 2,
                "row_delta": 2,
            }
        }

    payload = run_checkpoint_improvement_watch_light_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:05:00+09:00",
        refresh_function=_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "LIGHT_CYCLE_REFRESHED"
    assert state["phase"] == "RUNNING"
    assert state["row_count_since_boot"] == 2
    assert state["last_row_ts"] == "2026-04-11T10:01:00+09:00"
    assert state["light_last_run"] == "2026-04-11T10:05:00+09:00"
    assert bus.pending_count() == 2

    bus.drain()
    assert seen_events == ["SystemPhaseChanged", "LightRefreshCompleted"]


def test_light_cycle_skips_during_cooldown_without_refresh(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(
        rows_path,
        [
            "2026-04-11T10:00:00+09:00,BTCUSD",
            "2026-04-11T10:01:00+09:00,BTCUSD",
            "2026-04-11T10:02:00+09:00,BTCUSD",
        ],
    )
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.record_row_observation(
        last_row_ts="2026-04-11T09:59:00+09:00",
        row_count_increment=1,
    )
    manager.mark_cycle_run("light", run_at="2026-04-11T10:00:00+09:00")
    bus = EventBus()
    refresh_calls: list[str] = []

    def _refresh_stub(**_: object) -> dict[str, object]:
        refresh_calls.append("called")
        return {"summary": {"trigger_state": "REFRESHED"}}

    payload = run_checkpoint_improvement_watch_light_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:02:00+09:00",
        refresh_function=_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "cooldown_active"
    assert refresh_calls == []
    assert bus.pending_count() == 0
    assert state["row_count_since_boot"] == 1
    assert state["light_last_run"] == "2026-04-11T10:00:00+09:00"


def test_light_cycle_degrades_and_publishes_watch_error_on_exception(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, ["2026-04-11T10:00:00+09:00,XAUUSD"])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(WatchError, lambda event: seen_events.append(event.event_type))
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _refresh_stub(**_: object) -> dict[str, object]:
        raise RuntimeError("boom")

    payload = run_checkpoint_improvement_watch_light_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:05:00+09:00",
        refresh_function=_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "WATCH_ERROR"
    assert state["phase"] == "DEGRADED"
    assert state["last_error"] == "light_cycle_error::RuntimeError"
    assert bus.pending_count() == 2

    bus.drain()
    assert seen_events == ["WatchError", "SystemPhaseChanged"]


def test_governance_cycle_skips_without_active_canary_or_backlog(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    bus = EventBus()

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        governance_board_payload={"summary": {}, "rows": []},
    )

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "no_active_canary_or_backlog"
    assert bus.pending_count() == 0
    assert manager.get_state()["governance_last_run"] == ""


def test_governance_cycle_emits_rollback_candidate_and_updates_symbol_state(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.set_pa8_symbol_state("BTCUSD", canary_active=True, live_window_ready=False)
    bus = EventBus()
    seen_candidates: list[dict[str, object]] = []
    bus.subscribe(GovernanceActionNeeded, lambda event: seen_candidates.append(dict(event.payload)))

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        now_ts="2026-04-11T11:00:00+09:00",
        governance_board_payload={
            "summary": {
                "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
                "active_symbol_count": 3,
                "live_observation_ready_count": 1,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
                    "closeout_state": "ROLLBACK_REQUIRED",
                    "live_observation_ready": True,
                    "observed_window_row_count": 12,
                    "active_trigger_count": 2,
                    "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
                }
            ],
        },
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "GOVERNANCE_CANDIDATES_EMITTED"
    assert payload["governance_summary"]["candidate_count"] == 1
    assert state["governance_last_run"] == "2026-04-11T11:00:00+09:00"
    assert state["pa8_symbols"]["BTCUSD"]["canary_active"] is True
    assert state["pa8_symbols"]["BTCUSD"]["live_window_ready"] is True
    assert bus.pending_count() == 1

    bus.drain()
    assert seen_candidates == [
        {
            "review_type": "CANARY_ROLLBACK_REVIEW",
            "governance_action": "rollback_review",
            "scope_key": "BTCUSD::action_only_canary::rollback",
            "symbol": "BTCUSD",
            "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
            "closeout_state": "ROLLBACK_REQUIRED",
            "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
            "live_observation_ready": True,
            "observed_window_row_count": 12,
            "active_trigger_count": 2,
            "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
        }
    ]


def test_governance_cycle_uses_board_active_canary_state_before_due_decision(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    bus = EventBus()

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=0,
        now_ts="2026-04-11T11:01:00+09:00",
        governance_board_payload={
            "summary": {
                "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
                "active_symbol_count": 3,
                "live_observation_ready_count": 0,
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 0,
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
        },
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "GOVERNANCE_NO_ACTION_NEEDED"
    assert payload["cycle_decision"]["active_pa8_symbol_count"] == 1
    assert state["pa8_symbols"]["NAS100"]["canary_active"] is True


def test_governance_cycle_marks_run_even_when_no_candidate_is_needed(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.set_pa8_symbol_state("XAUUSD", canary_active=True, live_window_ready=False)
    bus = EventBus()

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        now_ts="2026-04-11T11:03:00+09:00",
        governance_board_payload={
            "summary": {
                "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
                "active_symbol_count": 3,
                "live_observation_ready_count": 0,
            },
            "rows": [
                {
                    "symbol": "XAUUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 0,
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
        },
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "GOVERNANCE_NO_ACTION_NEEDED"
    assert payload["governance_summary"]["candidate_count"] == 0
    assert state["governance_last_run"] == "2026-04-11T11:03:00+09:00"
    assert bus.pending_count() == 0


def test_governance_cycle_recovers_from_degraded_on_success(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    manager.transition(
        "DEGRADED",
        reason="governance_cycle_error::PermissionError",
        occurred_at="2026-04-11T11:00:00+09:00",
    )
    manager.set_pa8_symbol_state("BTCUSD", canary_active=True, live_window_ready=False)
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        now_ts="2026-04-11T11:04:00+09:00",
        governance_board_payload={
            "summary": {
                "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
                "active_symbol_count": 1,
                "live_observation_ready_count": 0,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 4,
                    "active_trigger_count": 0,
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
        },
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "GOVERNANCE_NO_ACTION_NEEDED"
    assert state["phase"] == "RUNNING"
    assert state["last_error"] == ""
    bus.drain()
    assert seen_events == ["SystemPhaseChanged"]


def test_governance_cycle_degrades_on_loader_exception(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.set_pa8_symbol_state("NAS100", canary_active=True, live_window_ready=False)
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(WatchError, lambda event: seen_events.append(event.event_type))
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _loader() -> dict[str, object]:
        raise RuntimeError("governance_loader_boom")

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        now_ts="2026-04-11T11:05:00+09:00",
        governance_board_loader=_loader,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "WATCH_ERROR"
    assert state["phase"] == "DEGRADED"
    assert state["last_error"] == "governance_cycle_error::RuntimeError"
    assert bus.pending_count() == 2

    bus.drain()
    assert seen_events == ["WatchError", "SystemPhaseChanged"]


def test_governance_cycle_emits_closeout_candidate_when_ready_for_pa9_handoff(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.set_pa8_symbol_state("NAS100", canary_active=True, live_window_ready=True)
    bus = EventBus()
    seen_candidates: list[dict[str, object]] = []
    bus.subscribe(GovernanceActionNeeded, lambda event: seen_candidates.append(dict(event.payload)))
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_watch.refresh_checkpoint_improvement_pa9_handoff_runtime",
        lambda: {
            "summary": {
                "handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "apply_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW",
                "recommended_next_action": "review_prepared_pa9_action_baseline_handoff_packet",
            },
            "review_packet": {
                "rows": [
                    {
                        "symbol": "NAS100",
                        "activation_apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                        "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                        "handoff_review_candidate": True,
                        "handoff_apply_candidate": True,
                        "handoff_apply_recommended_next_action": "approve_and_apply_pa9_action_baseline_handoff_when_review_is_confirmed",
                    }
                ]
            },
        },
    )

    payload = run_checkpoint_improvement_watch_governance_cycle(
        system_state_manager=manager,
        event_bus=bus,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        row_delta=1,
        now_ts="2026-04-11T11:06:00+09:00",
        governance_board_payload={
            "summary": {
                "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
                "active_symbol_count": 3,
                "live_observation_ready_count": 1,
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
                    "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                    "live_observation_ready": True,
                    "observed_window_row_count": 82,
                    "active_trigger_count": 0,
                    "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
                }
            ],
        },
    )

    assert payload["summary"]["trigger_state"] == "GOVERNANCE_CANDIDATES_EMITTED"
    assert payload["governance_summary"]["pa9_handoff_state"] == "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW"
    assert (
        payload["governance_summary"]["pa9_review_state"]
        == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW"
    )
    assert (
        payload["governance_summary"]["pa9_apply_state"]
        == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW"
    )

    bus.drain()
    assert seen_candidates == [
        {
            "review_type": "CANARY_CLOSEOUT_REVIEW",
            "governance_action": "closeout_review",
            "scope_key": "NAS100::action_only_canary::closeout",
            "symbol": "NAS100",
            "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
            "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
            "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
            "live_observation_ready": True,
            "observed_window_row_count": 82,
            "active_trigger_count": 0,
            "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
        },
        {
            "review_type": "PA9_ACTION_BASELINE_HANDOFF_REVIEW",
            "governance_action": "pa9_action_baseline_handoff_review",
            "scope_key": "NAS100::pa9_action_baseline_handoff::review",
            "symbol": "NAS100",
            "handoff_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
            "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
            "handoff_review_candidate": True,
            "handoff_apply_candidate": True,
            "runtime_review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
            "runtime_apply_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW",
            "recommended_next_action": "approve_and_apply_pa9_action_baseline_handoff_when_review_is_confirmed",
        },
    ]


def test_default_governance_board_loader_rebuilds_board_before_returning(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _load_dataset_stub(path: object = None) -> object:
        seen["resolved_dataset_path"] = path
        return {"rows": 1}

    def _build_stub(resolved_dataset: object) -> dict[str, object]:
        seen["build_input"] = resolved_dataset
        return {"summary": {"contract_version": "checkpoint_pa8_canary_refresh_board_v1"}, "rows": []}

    def _write_stub(payload: object) -> None:
        seen["written_payload"] = payload

    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_watch.load_checkpoint_pa8_canary_refresh_resolved_dataset",
        _load_dataset_stub,
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_watch.build_checkpoint_pa8_canary_refresh_board",
        _build_stub,
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_watch.write_checkpoint_pa8_canary_refresh_outputs",
        _write_stub,
    )

    payload = _default_governance_board_loader()

    assert payload["summary"]["contract_version"] == "checkpoint_pa8_canary_refresh_board_v1"
    assert seen["build_input"] == {"rows": 1}
    assert seen["written_payload"] == payload


def test_heavy_cycle_skips_when_sample_floor_is_not_met(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, ["2026-04-11T10:00:00+09:00,BTCUSD"] * 50)
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    bus = EventBus()

    payload = run_checkpoint_improvement_watch_heavy_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:05:00+09:00",
    )

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "sample_floor_not_met"
    assert manager.get_state()["heavy_last_run"] == ""
    assert bus.pending_count() == 0


def test_heavy_cycle_refreshes_and_marks_heavy_last_run(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, [f"2026-04-11T10:{index:02d}:00+09:00,BTCUSD" for index in range(120)])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    bus = EventBus()

    def _heavy_refresh_stub(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "trigger_state": "REFRESHED",
                "recommended_next_action": "use_fresh_reports_and_keep_refresh_chain_running",
            },
            "chain": {
                "deep_scene_review_refreshed": True,
                "pa7_review_processor_summary": {
                    "processed_group_count": 6,
                    "recommended_next_action": "work_through_pa7_review_groups_before_pa8",
                },
                "pa78_review_packet_summary": {
                    "pa7_unresolved_review_group_count": 2,
                    "pa7_review_state": "READY_FOR_REVIEW",
                    "pa8_review_state": "HOLD_ACTION_BASELINE_ALIGNMENT",
                    "scene_bias_review_state": "HOLD_SCENE_ALIGNMENT",
                    "recommended_next_action": "work_through_pa7_review_groups_before_pa8",
                },
                "scene_disagreement_summary": {
                    "high_conf_scene_disagreement_count": 12,
                    "expected_action_alignment_rate": 0.88,
                },
                "scene_bias_preview_summary": {
                    "preview_changed_row_count": 3,
                    "improved_row_count": 2,
                    "worsened_row_count": 0,
                },
            },
        }

    payload = run_checkpoint_improvement_watch_heavy_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:20:00+09:00",
        heavy_refresh_function=_heavy_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "HEAVY_CYCLE_REFRESHED"
    assert payload["heavy_summary"]["deep_scene_review_refreshed"] is True
    assert payload["heavy_summary"]["pa7_processed_group_count"] == 6
    assert payload["heavy_summary"]["high_conf_scene_disagreement_count"] == 12
    assert payload["heavy_summary"]["preview_changed_row_count"] == 3
    assert state["heavy_last_run"] == "2026-04-11T10:20:00+09:00"
    assert bus.pending_count() == 0


def test_heavy_cycle_recovers_from_degraded_on_success(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, [f"2026-04-11T10:{index:02d}:00+09:00,BTCUSD" for index in range(120)])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    manager.transition(
        "DEGRADED",
        reason="heavy_cycle_error::RuntimeError",
        occurred_at="2026-04-11T10:15:00+09:00",
    )
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _heavy_refresh_stub(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "trigger_state": "REFRESHED",
                "recommended_next_action": "use_fresh_reports_and_keep_refresh_chain_running",
            },
            "chain": {},
        }

    payload = run_checkpoint_improvement_watch_heavy_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:20:00+09:00",
        heavy_refresh_function=_heavy_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "HEAVY_CYCLE_REFRESHED"
    assert state["phase"] == "RUNNING"
    assert state["last_error"] == ""
    bus.drain()
    assert seen_events == ["SystemPhaseChanged"]


def test_heavy_cycle_skips_during_cooldown(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, [f"2026-04-11T10:{index:02d}:00+09:00,NAS100" for index in range(140)])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    manager.mark_cycle_run("heavy", run_at="2026-04-11T10:00:00+09:00")
    bus = EventBus()
    refresh_calls: list[str] = []

    def _heavy_refresh_stub(**_: object) -> dict[str, object]:
        refresh_calls.append("called")
        return {"summary": {"trigger_state": "REFRESHED"}}

    payload = run_checkpoint_improvement_watch_heavy_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:05:00+09:00",
        heavy_refresh_function=_heavy_refresh_stub,
    )

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "cooldown_active"
    assert refresh_calls == []


def test_heavy_cycle_degrades_and_publishes_watch_error_on_exception(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, [f"2026-04-11T10:{index:02d}:00+09:00,XAUUSD" for index in range(120)])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(WatchError, lambda event: seen_events.append(event.event_type))
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _heavy_refresh_stub(**_: object) -> dict[str, object]:
        raise RuntimeError("heavy_boom")

    payload = run_checkpoint_improvement_watch_heavy_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:25:00+09:00",
        heavy_refresh_function=_heavy_refresh_stub,
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "WATCH_ERROR"
    assert state["phase"] == "DEGRADED"
    assert state["last_error"] == "heavy_cycle_error::RuntimeError"
    assert bus.pending_count() == 2

    bus.drain()
    assert seen_events == ["WatchError", "SystemPhaseChanged"]


def test_light_cycle_recovers_from_degraded_on_success(tmp_path: Path) -> None:
    rows_path = tmp_path / "checkpoint_rows.csv"
    _write_rows(rows_path, [f"2026-04-11T10:{index:02d}:00+09:00,BTCUSD" for index in range(30)])
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T09:50:00+09:00",
    )
    manager.transition(
        "DEGRADED",
        reason="light_cycle_error::RuntimeError",
        occurred_at="2026-04-11T10:00:00+09:00",
    )
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))
    bus.subscribe(LightRefreshCompleted, lambda event: seen_events.append(event.event_type))

    payload = run_checkpoint_improvement_watch_light_cycle(
        system_state_manager=manager,
        event_bus=bus,
        checkpoint_rows_path=rows_path,
        report_path=tmp_path / "watch_report.json",
        markdown_path=tmp_path / "watch_report.md",
        now_ts="2026-04-11T10:05:00+09:00",
        refresh_function=lambda **_: {"summary": {"trigger_state": "REFRESHED"}},
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "LIGHT_CYCLE_REFRESHED"
    assert state["phase"] == "RUNNING"
    assert state["last_error"] == ""
    bus.drain()
    assert seen_events == ["SystemPhaseChanged", "LightRefreshCompleted"]
