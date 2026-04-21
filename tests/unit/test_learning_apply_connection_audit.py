from __future__ import annotations

from backend.services.learning_apply_connection_audit import (
    build_learning_apply_connection_audit,
    render_learning_apply_connection_audit_markdown,
)


def _check_by_code(payload: dict, code: str) -> dict:
    for row in payload.get("checks", []):
        if str(row.get("code")) == code:
            return dict(row)
    raise AssertionError(f"check not found: {code}")


def test_learning_apply_connection_audit_core_links_pass() -> None:
    payload = build_learning_apply_connection_audit()

    assert payload["contract_version"] == "learning_apply_connection_audit_v1"
    assert payload["overall_status"] in {"PASS", "WARN"}

    assert _check_by_code(payload, "registry_snapshot_present")["status"] == "PASS"
    assert _check_by_code(payload, "state25_weight_registry_coverage")["status"] == "PASS"
    assert _check_by_code(payload, "detector_to_propose_connection")["status"] == "PASS"
    assert _check_by_code(payload, "feedback_promotion_connection")["status"] == "PASS"
    assert _check_by_code(payload, "review_bridge_connection")["status"] == "PASS"
    assert _check_by_code(payload, "state25_apply_connection")["status"] == "PASS"
    assert _check_by_code(payload, "planned_binding_registry_coverage")["status"] == "PASS"


def test_learning_apply_connection_audit_registry_binding_is_visible() -> None:
    payload = build_learning_apply_connection_audit()
    binding_check = _check_by_code(payload, "registry_direct_runtime_binding")
    binding_progress = dict(payload.get("summary", {}).get("binding_progress", {}) or {})

    assert binding_check["status"] in {"PASS", "WARN"}
    assert "bound_service_files" in binding_check
    assert "binding_version" in binding_progress
    assert "binding_rate_pct" in binding_progress
    assert float(binding_progress["binding_rate_pct"]) >= 0.0
    if binding_check["status"] == "WARN":
        assert "단계적으로 수렴" in binding_check["message_ko"]


def test_learning_apply_connection_audit_markdown_contains_checks() -> None:
    payload = build_learning_apply_connection_audit()
    markdown = render_learning_apply_connection_audit_markdown(payload)

    assert "# Learning Apply Connection Audit" in markdown
    assert "registry_snapshot_present" in markdown
    assert "state25_apply_connection" in markdown
