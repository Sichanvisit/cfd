import json

from backend.app.trading_application import TradingApplication
from backend.app.trading_application_runner import _build_runtime_reexec_argv
from backend.services.runtime_recycle import (
    build_runtime_recycle_state,
    build_runtime_recycle_drift_v1,
    build_runtime_recycle_health_v1,
    evaluate_runtime_recycle,
)


class _DummyBroker:
    pass


class _DummyNotifier:
    def send(self, message):
        return None

    def shutdown(self):
        return None


class _DummyObservability:
    def incr(self, name, amount=1):
        return None

    def event(self, name, level="info", payload=None):
        return None


def test_runtime_recycle_waits_for_flat_grace_before_log_only_trigger():
    state = build_runtime_recycle_state(
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=30,
        post_order_grace_sec=0,
        now_ts=100.0,
    )

    blocked_on_positions = evaluate_runtime_recycle(
        state,
        loop_count=3601,
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=30,
        post_order_grace_sec=0,
        open_positions_count=1,
        owned_open_positions_count=1,
        now_ts=3700.0,
    )
    assert blocked_on_positions["status"] == "blocked"
    assert blocked_on_positions["reason"] == "open_positions_present"
    assert blocked_on_positions["action"] == "none"

    blocked_on_grace = evaluate_runtime_recycle(
        blocked_on_positions["state"],
        loop_count=3602,
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=30,
        post_order_grace_sec=0,
        open_positions_count=0,
        owned_open_positions_count=0,
        now_ts=3705.0,
    )
    assert blocked_on_grace["status"] == "blocked"
    assert blocked_on_grace["reason"] == "flat_grace_active"
    assert blocked_on_grace["action"] == "none"

    triggered = evaluate_runtime_recycle(
        blocked_on_grace["state"],
        loop_count=3603,
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=30,
        post_order_grace_sec=0,
        open_positions_count=0,
        owned_open_positions_count=0,
        now_ts=3736.0,
    )
    assert triggered["status"] == "triggered"
    assert triggered["reason"] == "due_and_flat"
    assert triggered["action"] == "log_only"
    assert triggered["state"]["log_only_count"] == 1
    assert triggered["state"]["next_due_at_ts"] == 7336.0


def test_runtime_recycle_reexec_waits_for_post_order_grace():
    state = build_runtime_recycle_state(
        mode="reexec",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=90,
        now_ts=100.0,
    )

    blocked = evaluate_runtime_recycle(
        state,
        loop_count=5000,
        mode="reexec",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=90,
        open_positions_count=0,
        owned_open_positions_count=0,
        last_order_ts=3660.0,
        now_ts=3700.0,
    )
    assert blocked["status"] == "blocked"
    assert blocked["reason"] == "post_order_grace_active"
    assert blocked["action"] == "none"

    triggered = evaluate_runtime_recycle(
        blocked["state"],
        loop_count=5001,
        mode="reexec",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=90,
        open_positions_count=0,
        owned_open_positions_count=0,
        last_order_ts=3660.0,
        now_ts=3751.0,
    )
    assert triggered["status"] == "triggered"
    assert triggered["action"] == "reexec"
    assert triggered["state"]["reexec_count"] == 1


def test_runtime_recycle_blocks_when_health_and_drift_are_not_confirmed():
    state = build_runtime_recycle_state(
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        now_ts=100.0,
    )

    health = build_runtime_recycle_health_v1(
        recent_runtime_summary={"available": True, "reason": "ok"},
        default_recent_window={"row_count": 120},
        latest_signal_by_symbol={
            "BTCUSD": {"runtime_snapshot_generated_ts": 3695.0, "consumer_check_stage": "READY"},
            "XAUUSD": {"runtime_snapshot_generated_ts": 3696.0, "consumer_check_stage": "READY"},
        },
        now_ts=3700.0,
        signal_stale_sec=900,
    )
    drift = build_runtime_recycle_drift_v1(
        recent_runtime_summary={"available": True, "reason": "ok"},
        default_recent_window={
            "row_count": 120,
            "stage_counts": {"READY": 90, "OBSERVE": 30},
            "blocked_reason_counts": {"forecast_guard": 12},
            "display_ready_summary": {
                "display_ready_true": 80,
                "display_ready_false": 40,
                "entry_ready_true": 30,
                "entry_ready_false": 90,
                "blocked_row_count": 12,
            },
            "wait_state_decision_bridge_summary": {
                "bridge_row_count": 25,
                "state_to_decision_counts": {"OBSERVE->skip": 10, "PROBE_CANDIDATE->wait_soft_probe_candidate": 8},
            },
        },
        latest_signal_by_symbol={
            "BTCUSD": {"runtime_snapshot_generated_ts": 3695.0, "consumer_check_stage": "READY"},
            "XAUUSD": {"runtime_snapshot_generated_ts": 3696.0, "consumer_check_stage": "READY"},
        },
        min_rows=40,
        min_signal_count=2,
    )

    decision = evaluate_runtime_recycle(
        state,
        loop_count=5000,
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        open_positions_count=0,
        owned_open_positions_count=0,
        health_snapshot=health,
        drift_snapshot=drift,
        now_ts=3700.0,
    )

    assert decision["status"] == "blocked"
    assert decision["reason"] == "health_drift_not_confirmed"
    assert decision["action"] == "none"
    assert decision["state"]["last_health_state"] == "healthy"
    assert decision["state"]["last_drift_state"] == "stable"


def test_runtime_recycle_triggers_for_health_stale_even_without_drift():
    state = build_runtime_recycle_state(
        mode="reexec",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        now_ts=100.0,
    )

    health = build_runtime_recycle_health_v1(
        recent_runtime_summary={"available": True, "reason": "ok"},
        default_recent_window={"row_count": 120},
        latest_signal_by_symbol={
            "BTCUSD": {"runtime_snapshot_generated_ts": 2000.0},
            "XAUUSD": {"runtime_snapshot_generated_ts": 2001.0},
        },
        now_ts=3700.0,
        signal_stale_sec=900,
    )

    decision = evaluate_runtime_recycle(
        state,
        loop_count=5000,
        mode="reexec",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        open_positions_count=0,
        owned_open_positions_count=0,
        health_snapshot=health,
        drift_snapshot={"state": "stable", "reason": "drift_not_detected", "trigger_recommended": False},
        now_ts=3700.0,
    )

    assert health["state"] == "stale"
    assert decision["status"] == "triggered"
    assert decision["trigger_family"] == "health"
    assert decision["reason"] == "all_live_signal_rows_stale"
    assert decision["action"] == "reexec"


def test_runtime_recycle_triggers_for_drift_when_observe_lock_signals_stack():
    state = build_runtime_recycle_state(
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        now_ts=100.0,
    )

    drift = build_runtime_recycle_drift_v1(
        recent_runtime_summary={"available": True, "reason": "ok"},
        default_recent_window={
            "row_count": 120,
            "stage_counts": {"OBSERVE": 112, "READY": 8},
            "blocked_reason_counts": {"conflict_box_lower_bb20_upper_upper_dominant_observe": 92},
            "display_ready_summary": {
                "display_ready_true": 115,
                "display_ready_false": 5,
                "entry_ready_true": 0,
                "entry_ready_false": 120,
                "blocked_row_count": 92,
            },
            "wait_state_decision_bridge_summary": {
                "bridge_row_count": 105,
                "state_to_decision_counts": {"CENTER->skip": 96, "OBSERVE->skip": 9},
            },
        },
        latest_signal_by_symbol={
            "BTCUSD": {
                "runtime_snapshot_generated_ts": 3697.0,
                "consumer_check_stage": "OBSERVE",
                "consumer_check_display_ready": True,
                "consumer_check_entry_ready": False,
                "observe_action": "WAIT",
            },
            "XAUUSD": {
                "runtime_snapshot_generated_ts": 3697.0,
                "consumer_check_stage": "BLOCKED",
                "consumer_check_display_ready": True,
                "consumer_check_entry_ready": False,
                "blocked_by": "conflict_box_lower_bb20_upper_upper_dominant_observe",
            },
            "NAS100": {
                "runtime_snapshot_generated_ts": 3697.0,
                "consumer_check_stage": "OBSERVE",
                "consumer_check_display_ready": True,
                "consumer_check_entry_ready": False,
                "entry_wait_state": "CENTER",
            },
        },
        min_rows=40,
        stage_dominance_threshold=0.85,
        block_dominance_threshold=0.85,
        decision_dominance_threshold=0.90,
        min_signal_count=2,
    )

    decision = evaluate_runtime_recycle(
        state,
        loop_count=5000,
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=0,
        post_order_grace_sec=0,
        open_positions_count=0,
        owned_open_positions_count=0,
        health_snapshot={"state": "healthy", "reason": "fresh_live_signal_rows", "trigger_recommended": False},
        drift_snapshot=drift,
        now_ts=3700.0,
    )

    assert drift["state"] == "drifted"
    assert "stage_lock" in drift["signals"]
    assert "blocked_reason_lock" in drift["signals"]
    assert "entry_ready_zero" in drift["signals"]
    assert decision["status"] == "triggered"
    assert decision["trigger_family"] == "drift"
    assert decision["action"] == "log_only"


def test_runtime_status_exports_runtime_recycle_state(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.runtime_recycle_state = build_runtime_recycle_state(
        mode="log_only",
        interval_sec=3600,
        flat_grace_sec=30,
        post_order_grace_sec=90,
        now_ts=100.0,
    )

    app._write_runtime_status(
        loop_count=12,
        symbols={"BTCUSD": "BTCUSD"},
        entry_threshold=45,
        exit_threshold=150,
    )

    slim_payload = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail_payload = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert slim_payload["runtime_recycle"]["mode"] == "log_only"
    assert slim_payload["runtime_recycle"]["interval_sec"] == 3600
    assert slim_payload["runtime_recycle_health_v1"]["contract_version"] == "runtime_recycle_health_v1"
    assert slim_payload["runtime_recycle_drift_v1"]["contract_version"] == "runtime_recycle_drift_v1"
    assert detail_payload["runtime_recycle"]["flat_grace_sec"] == 30


def test_build_runtime_reexec_argv_prefixes_python_for_script(monkeypatch):
    monkeypatch.setattr("backend.app.trading_application_runner.sys.argv", ["main.py", "--demo"])
    monkeypatch.setattr("backend.app.trading_application_runner.sys.executable", r"C:\Python\python.exe")

    argv = _build_runtime_reexec_argv()

    assert argv[0] == r"C:\Python\python.exe"
    assert argv[1].endswith("main.py")
    assert argv[2:] == ["--demo"]
