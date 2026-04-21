"""AI2 latest summary for baseline-no-action candidate bridge coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.entry_candidate_bridge import (
    build_baseline_no_action_bridge,
    render_baseline_no_action_bridge_markdown,
)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def build_baseline_no_action_bridge_outputs(
    *,
    runtime_status_path: str | Path,
    entry_decisions_path: str | Path,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any], str]:
    frame, summary = build_baseline_no_action_bridge(
        _load_json(runtime_status_path),
        _load_csv(entry_decisions_path),
        recent_limit=int(recent_limit),
    )
    markdown = render_baseline_no_action_bridge_markdown(summary, frame)
    return frame, summary, markdown
