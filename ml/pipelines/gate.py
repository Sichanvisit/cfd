"""Quality gate utilities for staged training pipeline."""

from __future__ import annotations

import math
from typing import Any


def evaluate_metrics_gate(
    metrics: dict[str, Any],
    min_entry_auc: float,
    min_exit_auc: float,
    min_test_samples: int,
    min_entry_acc_when_auc_nan: float,
    min_exit_acc_when_auc_nan: float,
) -> tuple[bool, str]:
    em = metrics.get("entry_metrics", {}) or {}
    xm = metrics.get("exit_metrics", {}) or {}
    e_auc = em.get("auc")
    x_auc = xm.get("auc")
    e_n = int(em.get("samples", 0) or 0)
    x_n = int(xm.get("samples", 0) or 0)

    if e_n < min_test_samples or x_n < min_test_samples:
        return False, f"insufficient test samples entry={e_n}, exit={x_n}"

    e_auc_nan = (e_auc is None) or math.isnan(float(e_auc))
    x_auc_nan = (x_auc is None) or math.isnan(float(x_auc))
    e_acc = float(em.get("accuracy", 0.0) or 0.0)
    x_acc = float(xm.get("accuracy", 0.0) or 0.0)

    if e_auc_nan:
        if e_acc < float(min_entry_acc_when_auc_nan):
            return False, f"entry auc nan and acc {e_acc:.3f} < {min_entry_acc_when_auc_nan:.3f}"
    elif float(e_auc) < min_entry_auc:
        return False, f"entry auc {float(e_auc):.3f} < {min_entry_auc:.3f}"

    if x_auc_nan:
        if x_acc < float(min_exit_acc_when_auc_nan):
            return False, f"exit auc nan and acc {x_acc:.3f} < {min_exit_acc_when_auc_nan:.3f}"
    elif float(x_auc) < min_exit_auc:
        return False, f"exit auc {float(x_auc):.3f} < {min_exit_auc:.3f}"

    return True, "pass"

