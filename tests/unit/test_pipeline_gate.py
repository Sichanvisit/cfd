from ml.pipelines.gate import evaluate_metrics_gate


def test_pipeline_gate_passes_with_valid_auc():
    ok, reason = evaluate_metrics_gate(
        metrics={
            "entry_metrics": {"auc": 0.6, "accuracy": 0.7, "samples": 20},
            "exit_metrics": {"auc": 0.4, "accuracy": 0.65, "samples": 20},
        },
        min_entry_auc=0.35,
        min_exit_auc=0.20,
        min_test_samples=8,
        min_entry_acc_when_auc_nan=0.55,
        min_exit_acc_when_auc_nan=0.55,
    )
    assert ok is True
    assert reason == "pass"


def test_pipeline_gate_fails_on_low_samples():
    ok, reason = evaluate_metrics_gate(
        metrics={
            "entry_metrics": {"auc": 0.6, "accuracy": 0.7, "samples": 2},
            "exit_metrics": {"auc": 0.4, "accuracy": 0.65, "samples": 2},
        },
        min_entry_auc=0.35,
        min_exit_auc=0.20,
        min_test_samples=8,
        min_entry_acc_when_auc_nan=0.55,
        min_exit_acc_when_auc_nan=0.55,
    )
    assert ok is False
    assert "insufficient test samples" in reason

