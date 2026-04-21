from __future__ import annotations

from pathlib import Path

from scripts.build_checkpoint_pa8_historical_replay_board import main


def test_build_checkpoint_pa8_historical_replay_board_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_path = tmp_path / "resolved.csv"
    dataset_path.write_text("symbol,generated_at\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def _fake_write(payload):
        captured["payload"] = payload

    monkeypatch.setattr(
        "scripts.build_checkpoint_pa8_historical_replay_board.write_checkpoint_pa8_historical_replay_outputs",
        _fake_write,
    )

    exit_code = main(["--resolved-dataset-path", str(dataset_path)])

    assert exit_code == 0
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["summary"]["symbol_count"] == 3
