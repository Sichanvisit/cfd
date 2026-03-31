import json
from pathlib import Path

from backend.core.config import Config
from backend.services.p7_guarded_size_overlay import resolve_p7_guarded_size_overlay_v1


def _write_overlay(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_resolve_p7_guarded_size_overlay_dry_run_does_not_apply(monkeypatch, tmp_path):
    source_path = tmp_path / "overlay.json"
    _write_overlay(
        source_path,
        {
            "report_version": "profitability_operations_p7_guarded_size_overlay_v1",
            "guarded_size_overlay_by_symbol": {
                "XAUUSD": {
                    "symbol": "XAUUSD",
                    "target_multiplier": 0.25,
                    "size_action": "hard_reduce",
                    "health_state": "stressed",
                }
            },
        },
    )

    monkeypatch.setattr(Config, "ENABLE_P7_GUARDED_SIZE_OVERLAY", True)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MODE", "dry_run")
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH", str(source_path))
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MAX_STEP", 0.10)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST", ())

    out = resolve_p7_guarded_size_overlay_v1(
        symbol="XAUUSD",
        action="BUY",
        entry_stage="balanced",
        base_lot=0.10,
        proposed_lot=0.10,
        min_lot=0.01,
    )

    assert out["matched"] is True
    assert out["apply_allowed"] is False
    assert out["gate_reason"] == "dry_run_only"
    assert out["candidate_multiplier"] == 0.9
    assert out["effective_multiplier"] == 1.0


def test_resolve_p7_guarded_size_overlay_apply_caps_step(monkeypatch, tmp_path):
    source_path = tmp_path / "overlay.json"
    _write_overlay(
        source_path,
        {
            "report_version": "profitability_operations_p7_guarded_size_overlay_v1",
            "guarded_size_overlay_by_symbol": {
                "NAS100": {
                    "symbol": "NAS100",
                    "target_multiplier": 0.43,
                    "size_action": "hard_reduce",
                    "health_state": "stressed",
                }
            },
        },
    )

    monkeypatch.setattr(Config, "ENABLE_P7_GUARDED_SIZE_OVERLAY", True)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MODE", "apply")
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH", str(source_path))
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MAX_STEP", 0.10)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST", ())

    out = resolve_p7_guarded_size_overlay_v1(
        symbol="NAS100",
        action="SELL",
        entry_stage="balanced",
        base_lot=0.10,
        proposed_lot=0.10,
        min_lot=0.01,
    )

    assert out["matched"] is True
    assert out["apply_allowed"] is True
    assert out["applied"] is True
    assert out["gate_reason"] == "passed"
    assert out["candidate_multiplier"] == 0.9
    assert out["effective_multiplier"] == 0.9
    assert out["effective_lot"] == 0.09
