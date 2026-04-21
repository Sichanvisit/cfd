from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_pa9_handoff_runtime import (
    refresh_checkpoint_improvement_pa9_handoff_runtime,
)


def test_pa9_handoff_runtime_writes_all_scaffold_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = refresh_checkpoint_improvement_pa9_handoff_runtime(
        runtime_json_output_path=tmp_path / "runtime.json",
        runtime_markdown_output_path=tmp_path / "runtime.md",
        handoff_json_output_path=tmp_path / "handoff.json",
        handoff_markdown_output_path=tmp_path / "handoff.md",
        review_json_output_path=tmp_path / "review.json",
        review_markdown_output_path=tmp_path / "review.md",
        apply_json_output_path=tmp_path / "apply.json",
        apply_markdown_output_path=tmp_path / "apply.md",
    )

    assert payload["summary"]["trigger_state"] == "PA9_HANDOFF_RUNTIME_REFRESHED"
    assert (tmp_path / "runtime.json").exists()
    assert (tmp_path / "handoff.json").exists()
    assert (tmp_path / "review.json").exists()
    assert (tmp_path / "apply.json").exists()
