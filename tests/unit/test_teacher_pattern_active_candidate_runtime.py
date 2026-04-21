import json

from backend.services.teacher_pattern_active_candidate_runtime import (
    build_state25_candidate_entry_log_only_trace_v1,
    build_state25_candidate_size_surface_v1,
    build_state25_candidate_threshold_surface_v1,
    build_state25_candidate_weight_surface_v1,
    load_state25_candidate_runtime_state,
    render_state25_teacher_weight_override_lines_ko,
    resolve_state25_candidate_live_threshold_adjustment_v1,
    resolve_state25_candidate_live_weight_overrides_v1,
)


def test_load_state25_candidate_runtime_state_uses_missing_fallback(tmp_path):
    state = load_state25_candidate_runtime_state(
        tmp_path / "missing_active_candidate_state.json"
    )

    assert state["available"] is False
    assert state["state_source_status"] == "missing_fallback"
    assert state["active_policy_source"] == "current_baseline"
    assert state["current_rollout_phase"] == "disabled"
    assert state["current_binding_mode"] == "disabled"


def test_load_state25_candidate_runtime_state_detects_change_and_normalizes_patch(
    tmp_path,
):
    state_path = tmp_path / "active_candidate_state.json"
    state_path.write_text(
        json.dumps(
            {
                "active_candidate_id": "candidate_42",
                "active_policy_source": "state25_candidate",
                "current_rollout_phase": "log_only",
                "current_binding_mode": "log_only",
                "desired_runtime_patch": {
                    "apply_now": True,
                    "state25_execution_bind_mode": "log_only",
                    "state25_execution_symbol_allowlist": ["BTCUSD", "", "NAS100"],
                    "state25_execution_entry_stage_allowlist": ["READY", "PROBE"],
                    "state25_threshold_log_only_enabled": True,
                    "state25_threshold_log_only_max_adjustment_abs": 6,
                    "state25_size_log_only_enabled": True,
                    "state25_size_log_only_min_multiplier": 0.8,
                    "state25_size_log_only_max_multiplier": 1.2,
                    "state25_weight_log_only_enabled": True,
                    "state25_teacher_weight_overrides": {
                        "upper_wick_weight": 0.6,
                        "candle_body_weight": 1.2,
                        "unknown_weight": 5.0,
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    first = load_state25_candidate_runtime_state(state_path)
    second = load_state25_candidate_runtime_state(state_path, current_state=first)

    assert first["state_source_status"] == "loaded"
    assert first["changed_since_last_refresh"] is True
    assert first["active_candidate_id"] == "candidate_42"
    assert first["desired_runtime_patch"]["state25_execution_symbol_allowlist"] == [
        "BTCUSD",
        "NAS100",
    ]
    assert first["desired_runtime_patch"]["state25_teacher_weight_overrides"] == {
        "upper_wick_weight": 0.6,
        "candle_body_weight": 1.2,
    }
    assert first["pending_apply_action"] == "promote_log_only"
    assert first["last_apply_at"] != ""
    assert first["last_apply_reason"] == "promote_log_only"
    assert second["changed_since_last_refresh"] is False
    assert second["state_fingerprint"] == first["state_fingerprint"]
    assert second["pending_apply_action"] == "none"


def test_load_state25_candidate_runtime_state_marks_rollback_events(tmp_path):
    state_path = tmp_path / "active_candidate_state.json"
    state_path.write_text(
        json.dumps(
            {
                "active_candidate_id": "",
                "active_policy_source": "current_baseline",
                "current_rollout_phase": "disabled",
                "current_binding_mode": "disabled",
                "last_event": "rollback_disable",
                "desired_runtime_patch": {
                    "apply_now": True,
                    "state25_execution_bind_mode": "disabled",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    state = load_state25_candidate_runtime_state(state_path)

    assert state["pending_apply_action"] == "rollback_disable"
    assert state["last_rollback_at"] != ""
    assert state["last_rollback_reason"] == "rollback_disable"


def test_candidate_runtime_surfaces_reflect_log_only_patch():
    runtime_state = {
        "current_binding_mode": "log_only",
        "apply_requested": True,
        "desired_runtime_patch": {
            "state25_execution_symbol_allowlist": ["BTCUSD", "XAUUSD"],
            "state25_execution_entry_stage_allowlist": ["READY"],
            "state25_threshold_log_only_enabled": True,
            "state25_threshold_log_only_max_adjustment_abs": 5,
            "state25_size_log_only_enabled": True,
            "state25_size_log_only_min_multiplier": 0.9,
            "state25_size_log_only_max_multiplier": 1.1,
        },
    }

    threshold = build_state25_candidate_threshold_surface_v1(
        runtime_state,
        baseline_entry_threshold=45,
    )
    size = build_state25_candidate_size_surface_v1(runtime_state)
    weight = build_state25_candidate_weight_surface_v1(
        runtime_state,
        symbol="BTCUSD",
        entry_stage="READY",
    )

    assert threshold["enabled"] is True
    assert threshold["mode"] == "log_only"
    assert threshold["baseline_entry_threshold"] == 45.0
    assert threshold["max_adjustment_abs"] == 5
    assert size["enabled"] is True
    assert size["mode"] == "log_only"
    assert size["candidate_log_only_min_multiplier"] == 0.9
    assert size["candidate_log_only_max_multiplier"] == 1.1
    assert weight["enabled"] is False


def test_build_state25_candidate_entry_log_only_trace_v1_computes_hypothetical_values():
    trace = build_state25_candidate_entry_log_only_trace_v1(
        {
            "state_source_status": "loaded",
            "active_candidate_id": "candidate_77",
            "active_policy_source": "state25_candidate",
            "current_rollout_phase": "log_only",
            "current_binding_mode": "log_only",
            "desired_runtime_patch": {
                "state25_execution_symbol_allowlist": ["BTCUSD", "NAS100"],
                "state25_execution_entry_stage_allowlist": ["READY", "PROBE"],
                "state25_threshold_log_only_enabled": True,
                "state25_threshold_log_only_max_adjustment_abs": 4,
                "state25_size_log_only_enabled": True,
                "state25_size_log_only_min_multiplier": 0.75,
                "state25_size_log_only_max_multiplier": 1.0,
                "state25_weight_log_only_enabled": True,
                "state25_teacher_weight_overrides": {
                    "upper_wick_weight": 0.75,
                    "compression_weight": 1.25,
                },
            },
        },
        symbol="BTCUSD",
        entry_stage="ready",
        actual_effective_entry_threshold=52,
        actual_size_multiplier=1.25,
    )

    assert trace["threshold_log_only_enabled"] is True
    assert trace["candidate_effective_entry_threshold"] == 48.0
    assert trace["candidate_entry_threshold_delta"] == -4.0
    assert trace["size_log_only_enabled"] is True
    assert trace["candidate_size_multiplier"] == 1.0
    assert trace["candidate_size_multiplier_delta"] == -0.25
    assert trace["weight_log_only_enabled"] is True
    assert trace["teacher_weight_override_count"] == 2
    assert trace["teacher_weight_override_keys"] == [
        "upper_wick_weight",
        "compression_weight",
    ]


def test_build_state25_candidate_entry_log_only_trace_v1_disables_out_of_scope_stage():
    trace = build_state25_candidate_entry_log_only_trace_v1(
        {
            "current_rollout_phase": "log_only",
            "current_binding_mode": "log_only",
            "desired_runtime_patch": {
                "state25_execution_symbol_allowlist": ["BTCUSD"],
                "state25_execution_entry_stage_allowlist": ["PROBE"],
                "state25_threshold_log_only_enabled": True,
                "state25_threshold_log_only_max_adjustment_abs": 5,
                "state25_size_log_only_enabled": True,
                "state25_size_log_only_min_multiplier": 0.75,
                "state25_size_log_only_max_multiplier": 1.0,
            },
        },
        symbol="BTCUSD",
        entry_stage="ready",
        actual_effective_entry_threshold=50,
        actual_size_multiplier=0.9,
    )

    assert trace["threshold_symbol_scope_hit"] is True
    assert trace["threshold_stage_scope_hit"] is False
    assert trace["threshold_log_only_enabled"] is False
    assert trace["candidate_effective_entry_threshold"] == 50.0
    assert trace["size_log_only_enabled"] is True


def test_build_state25_candidate_weight_surface_and_korean_lines():
    surface = build_state25_candidate_weight_surface_v1(
        {
            "current_binding_mode": "log_only",
            "desired_runtime_patch": {
                "state25_execution_symbol_allowlist": ["BTCUSD"],
                "state25_execution_entry_stage_allowlist": ["READY"],
                "state25_weight_log_only_enabled": True,
                "state25_teacher_weight_overrides": {
                    "upper_wick_weight": 0.7,
                    "lower_wick_weight": 1.2,
                },
            },
        },
        symbol="BTCUSD",
        entry_stage="READY",
    )

    lines = render_state25_teacher_weight_override_lines_ko(
        surface["teacher_weight_overrides"]
    )

    assert surface["enabled"] is True
    assert surface["weight_override_count"] == 2
    assert len(lines) == 2


def test_candidate_runtime_surfaces_reflect_bounded_live_patch():
    runtime_state = {
        "current_binding_mode": "bounded_live",
        "apply_requested": True,
        "desired_runtime_patch": {
            "state25_execution_symbol_allowlist": ["BTCUSD"],
            "state25_execution_entry_stage_allowlist": ["READY"],
            "state25_threshold_bounded_live_enabled": True,
            "state25_threshold_bounded_live_delta_points": 4,
            "state25_threshold_bounded_live_direction": "HARDEN",
            "state25_threshold_bounded_live_reason_keys": ["AGAINST_HTF"],
            "state25_weight_bounded_live_enabled": True,
            "state25_teacher_weight_overrides": {
                "reversal_risk_weight": 0.82,
                "directional_bias_weight": 1.12,
            },
        },
    }

    threshold = build_state25_candidate_threshold_surface_v1(
        runtime_state,
        baseline_entry_threshold=45,
    )
    weight = build_state25_candidate_weight_surface_v1(
        runtime_state,
        symbol="BTCUSD",
        entry_stage="READY",
    )

    assert threshold["enabled"] is True
    assert threshold["bounded_live_enabled"] is True
    assert threshold["actual_live_entry_threshold"] == 49.0
    assert threshold["bounded_live_reason_keys"] == ["AGAINST_HTF"]
    assert weight["enabled"] is True
    assert weight["bounded_live_enabled"] is True
    assert weight["live_teacher_weight_overrides"] == {
        "reversal_risk_weight": 0.82,
        "directional_bias_weight": 1.12,
    }
    assert weight["log_only_teacher_weight_overrides"] == {}


def test_resolve_live_helpers_return_only_bounded_live_values():
    runtime_state = {
        "current_binding_mode": "bounded_live",
        "desired_runtime_patch": {
            "state25_execution_symbol_allowlist": ["BTCUSD"],
            "state25_execution_entry_stage_allowlist": ["READY"],
            "state25_threshold_bounded_live_enabled": True,
            "state25_threshold_bounded_live_delta_points": 3,
            "state25_threshold_bounded_live_direction": "HARDEN",
            "state25_threshold_bounded_live_reason_keys": [
                "AGAINST_PREV_BOX_AND_HTF"
            ],
            "state25_weight_bounded_live_enabled": True,
            "state25_teacher_weight_overrides": {
                "reversal_risk_weight": 0.85,
                "directional_bias_weight": 1.10,
            },
        },
    }

    threshold_live = resolve_state25_candidate_live_threshold_adjustment_v1(
        runtime_state,
        symbol="BTCUSD",
        entry_stage="READY",
        baseline_entry_threshold=40,
    )
    weight_live = resolve_state25_candidate_live_weight_overrides_v1(
        runtime_state,
        symbol="BTCUSD",
        entry_stage="READY",
    )

    assert threshold_live["enabled"] is True
    assert threshold_live["candidate_effective_entry_threshold"] == 43.0
    assert threshold_live["threshold_delta_points"] == 3.0
    assert threshold_live["threshold_delta_reason_keys"] == [
        "AGAINST_PREV_BOX_AND_HTF"
    ]
    assert weight_live == {
        "reversal_risk_weight": 0.85,
        "directional_bias_weight": 1.1,
    }
