"""Runtime alerts builder for runtime status."""

from __future__ import annotations

from datetime import datetime


def build_runtime_alerts(*, KST, sqlite_mirror_status: dict, d_acceptance_snapshot: dict, exit_metrics: dict, policy_snapshot: dict):
    try:
        alert_items = []
        now_iso = datetime.now(KST).isoformat(timespec="seconds")
        if isinstance(sqlite_mirror_status, dict) and not bool(sqlite_mirror_status.get("healthy", True)):
            alert_items.append(
                {
                    "code": "sqlite_mirror_degraded",
                    "severity": "fail",
                    "message": f"sqlite mirror degraded: op={sqlite_mirror_status.get('last_failure_op','-')}",
                }
            )
        plus_check = str((d_acceptance_snapshot or {}).get("plus_to_minus_trend_check", "")).lower()
        adverse_check = str((d_acceptance_snapshot or {}).get("adverse_stop_trend_check", "")).lower()
        if plus_check in {"warn", "fail"}:
            alert_items.append(
                {
                    "code": "plus_to_minus_trend",
                    "severity": plus_check,
                    "message": f"plus_to_minus trend={plus_check}",
                }
            )
        if adverse_check in {"warn", "fail"}:
            alert_items.append(
                {
                    "code": "adverse_stop_trend",
                    "severity": adverse_check,
                    "message": f"adverse_stop trend={adverse_check}",
                }
            )
        blocked_cnt = int((exit_metrics or {}).get("regime_switch_blocked_count", 0) or 0)
        if blocked_cnt > 0:
            alert_items.append(
                {
                    "code": "regime_switch_blocked",
                    "severity": "warn",
                    "message": f"regime switch blocked count={blocked_cnt}",
                }
            )
        policy_rt = dict(((policy_snapshot or {}).get("policy_runtime", {}) or {}))
        rollback_count = int(policy_rt.get("rollback_count", 0) or 0)
        if rollback_count > 0:
            alert_items.append(
                {
                    "code": "policy_rollback",
                    "severity": "warn",
                    "message": f"policy rollback count={rollback_count}",
                }
            )
        return {
            "active_count": int(len(alert_items)),
            "items": alert_items,
            "last_transition_at": now_iso if alert_items else "",
        }
    except Exception:
        return {"active_count": 0, "items": [], "last_transition_at": ""}
