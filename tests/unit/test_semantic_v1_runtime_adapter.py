import numpy as np

from ml.semantic_v1.runtime_adapter import (
    SemanticShadowRuntime,
    build_semantic_shadow_feature_row,
    resolve_semantic_shadow_compare_label,
    resolve_trace_quality_state,
)


def test_build_semantic_shadow_feature_row_extracts_contract_scalars():
    row = build_semantic_shadow_feature_row(
        runtime_snapshot_row={
            "symbol": "BTCUSD",
            "runtime_snapshot_key": "snap-1",
            "signal_age_sec": 4.0,
            "bar_age_sec": 4.0,
            "decision_latency_ms": 120,
            "missing_feature_count": 1,
            "data_completeness_ratio": 0.96,
            "used_fallback_count": 1,
            "compatibility_mode": "hybrid",
            "snapshot_payload_bytes": 320,
        },
        position_snapshot_v2={
            "vector": {
                "x_box": 0.12,
                "x_bb20": 0.21,
            },
            "interpretation": {
                "alignment_label": "aligned",
                "bias_label": "buy_bias",
                "conflict_kind": "none",
            },
            "energy": {
                "lower_position_force": 0.81,
                "position_conflict_score": 0.08,
            },
        },
        response_vector_v2={"mid_reclaim_up": 0.74},
        state_vector_v2={"alignment_gain": 0.62, "noise_damp": 0.15},
        evidence_vector_v1={"buy_total_evidence": 0.88},
        forecast_features_v1={
            "position_primary_label": "lower_buy_zone",
            "position_secondary_context_label": "range_reversal",
            "position_conflict_score": 0.11,
            "management_horizon_bars": 6,
            "signal_timeframe": "M1",
        },
        signal_timeframe="M1",
        setup_id="range_lower_reversal_buy",
        setup_side="BUY",
        entry_stage="aggressive",
        preflight_regime="range",
        preflight_liquidity="high",
    )

    assert row["symbol"] == "BTCUSD"
    assert row["setup_id"] == "range_lower_reversal_buy"
    assert row["position_x_box"] == 0.12
    assert row["position_alignment_label"] == "aligned"
    assert row["response_mid_reclaim_up"] == 0.74
    assert row["state_alignment_gain"] == 0.62
    assert row["evidence_buy_total"] == 0.88
    assert row["forecast_position_primary_label"] == "lower_buy_zone"
    assert row["signal_age_sec"] == 4.0
    assert row["snapshot_payload_bytes"] == 320


def test_semantic_shadow_runtime_predicts_and_labels(monkeypatch):
    probabilities = {
        "timing": 0.78,
        "entry_quality": 0.66,
        "exit_management": 0.41,
    }

    def fake_predict_bundle_proba(bundle, _frame):
        return np.asarray([probabilities[bundle["dataset_key"]]], dtype=float)

    monkeypatch.setattr(
        "ml.semantic_v1.runtime_adapter.predict_bundle_proba",
        fake_predict_bundle_proba,
    )

    runtime = SemanticShadowRuntime(
        bundles={
            "timing": {"dataset_key": "timing", "feature_columns": ["position_x_box"]},
            "entry_quality": {"dataset_key": "entry_quality", "feature_columns": ["position_x_box"]},
            "exit_management": {"dataset_key": "exit_management", "feature_columns": ["position_x_box"]},
        }
    )

    prediction = runtime.predict_shadow(
        {
            "symbol": "BTCUSD",
            "position_x_box": 0.12,
            "data_completeness_ratio": 1.0,
            "missing_feature_count": 0,
            "used_fallback_count": 0,
            "compatibility_mode": "",
        },
        action_hint="BUY",
        timing_threshold=0.55,
        entry_quality_threshold=0.60,
    )

    assert prediction["available"] is True
    assert prediction["availability_state"] == "available"
    assert prediction["availability_reason"] == ""
    assert prediction["recommendation"] == "enter_now"
    assert prediction["should_enter"] is True
    assert prediction["timing"]["probability"] == 0.78
    assert prediction["entry_quality"]["probability"] == 0.66
    assert prediction["trace_quality_state"] == "clean"
    assert (
        resolve_semantic_shadow_compare_label(
            prediction,
            baseline_outcome="skipped",
            blocked_by="entry_wait",
        )
        == "semantic_earlier_enter"
    )
    assert (
        resolve_semantic_shadow_compare_label(
            prediction,
            baseline_outcome="entered",
            baseline_action="BUY",
        )
        == "agree_enter"
    )


def test_semantic_shadow_runtime_unavailable_prediction_exposes_reason():
    prediction = SemanticShadowRuntime.unavailable_prediction(
        reason="model_files_missing",
        action_hint="BUY",
    )

    assert prediction["available"] is False
    assert prediction["availability_state"] == "unavailable"
    assert prediction["availability_reason"] == "model_files_missing"
    assert prediction["reason"] == "model_files_missing"


def test_semantic_shadow_runtime_emits_wait_better_entry_when_quality_passes_but_timing_fails(monkeypatch):
    probabilities = {
        "timing": 0.32,
        "entry_quality": 0.74,
        "exit_management": 0.22,
    }

    def fake_predict_bundle_proba(bundle, _frame):
        return np.asarray([probabilities[bundle["dataset_key"]]], dtype=float)

    monkeypatch.setattr(
        "ml.semantic_v1.runtime_adapter.predict_bundle_proba",
        fake_predict_bundle_proba,
    )

    runtime = SemanticShadowRuntime(
        bundles={
            "timing": {"dataset_key": "timing", "feature_columns": ["position_x_box"]},
            "entry_quality": {"dataset_key": "entry_quality", "feature_columns": ["position_x_box"]},
            "exit_management": {"dataset_key": "exit_management", "feature_columns": ["position_x_box"]},
        }
    )

    prediction = runtime.predict_shadow(
        {
            "symbol": "BTCUSD",
            "position_x_box": 0.12,
            "data_completeness_ratio": 1.0,
            "missing_feature_count": 0,
            "used_fallback_count": 0,
            "compatibility_mode": "",
        },
        action_hint="WAIT",
        timing_threshold=0.55,
        entry_quality_threshold=0.60,
    )

    assert prediction["available"] is True
    assert prediction["should_enter"] is False
    assert prediction["recommendation"] == "wait_better_entry"
    assert (
        resolve_semantic_shadow_compare_label(
            prediction,
            baseline_outcome="entered",
            baseline_action="BUY",
        )
        == "semantic_wait_for_better_entry"
    )


def test_resolve_trace_quality_state_distinguishes_degraded_rows():
    assert resolve_trace_quality_state({"data_completeness_ratio": 1.0}) == "clean"
    assert (
        resolve_trace_quality_state(
            {
                "data_completeness_ratio": 0.88,
                "missing_feature_count": 4,
            }
        )
        == "incomplete"
    )
    assert (
        resolve_trace_quality_state(
            {
                "data_completeness_ratio": 0.97,
                "missing_feature_count": 1,
                "used_fallback_count": 2,
            }
        )
        == "fallback_heavy"
    )
