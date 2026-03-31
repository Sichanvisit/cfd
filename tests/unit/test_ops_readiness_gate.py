from backend.fastapi.app import _classify_release_gate


def test_ops_readiness_gate_fail_on_alerts_or_rollbacks():
    out1 = _classify_release_gate(active_alerts=1, rollback_count=0, warning_total=0)
    out2 = _classify_release_gate(active_alerts=0, rollback_count=2, warning_total=0)

    assert out1["grade"] == "fail"
    assert out2["grade"] == "fail"


def test_ops_readiness_gate_warn_and_pass():
    warn = _classify_release_gate(active_alerts=0, rollback_count=0, warning_total=3)
    ok = _classify_release_gate(active_alerts=0, rollback_count=0, warning_total=0)

    assert warn["grade"] == "warn"
    assert ok["grade"] == "pass"

