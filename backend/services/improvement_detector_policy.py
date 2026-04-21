from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


IMPROVEMENT_DETECTOR_POLICY_CONTRACT_VERSION = "improvement_detector_policy_v1"

DETECTOR_SCENE_AWARE = "scene_aware"
DETECTOR_CANDLE_WEIGHT = "candle_weight"
DETECTOR_REVERSE_PATTERN = "reverse_pattern"

DETECTOR_KEYS = (
    DETECTOR_SCENE_AWARE,
    DETECTOR_CANDLE_WEIGHT,
    DETECTOR_REVERSE_PATTERN,
)

DETECTOR_DAILY_SURFACE_LIMITS = {
    DETECTOR_SCENE_AWARE: 3,
    DETECTOR_CANDLE_WEIGHT: 5,
    DETECTOR_REVERSE_PATTERN: 2,
}

DETECTOR_MIN_REPEAT_SAMPLES = {
    DETECTOR_SCENE_AWARE: 3,
    DETECTOR_CANDLE_WEIGHT: 5,
    DETECTOR_REVERSE_PATTERN: 3,
}

DETECTOR_TOTAL_DAILY_SURFACE_LIMIT = 10

DETECTOR_LABELS_KO = {
    DETECTOR_SCENE_AWARE: "scene-aware detector",
    DETECTOR_CANDLE_WEIGHT: "candle/weight detector",
    DETECTOR_REVERSE_PATTERN: "reverse pattern detector",
}


@dataclass(frozen=True, slots=True)
class DetectorPolicyRow:
    detector_key: str
    label_ko: str
    daily_surface_limit: int
    min_repeat_sample: int
    notes_ko: str


def build_improvement_detector_policy_baseline() -> dict[str, Any]:
    rows = [
        asdict(
            DetectorPolicyRow(
                detector_key=detector_key,
                label_ko=DETECTOR_LABELS_KO[detector_key],
                daily_surface_limit=int(DETECTOR_DAILY_SURFACE_LIMITS[detector_key]),
                min_repeat_sample=int(DETECTOR_MIN_REPEAT_SAMPLES[detector_key]),
                notes_ko={
                    DETECTOR_SCENE_AWARE: "scene trace 부재/scene disagreement 누적을 log-only로 surface하고, 상하단 방향 오판 가능성도 함께 관찰한다.",
                    DETECTOR_CANDLE_WEIGHT: "상단/하단/캔들/박스 위치 해석 불일치 후보를 weight patch review preview와 함께 surface한다.",
                    DETECTOR_REVERSE_PATTERN: "reverse-ready miss/blocked 패턴을 관찰 보고서로만 남긴다.",
                }[detector_key],
            )
        )
        for detector_key in DETECTOR_KEYS
    ]
    return {
        "contract_version": IMPROVEMENT_DETECTOR_POLICY_CONTRACT_VERSION,
        "daily_surface_limit_total": DETECTOR_TOTAL_DAILY_SURFACE_LIMIT,
        "rows": rows,
    }


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_improvement_detector_policy_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "improvement_detector_policy_baseline_latest.json",
        directory / "improvement_detector_policy_baseline_latest.md",
    )


def render_improvement_detector_policy_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Improvement Detector Policy Baseline",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        f"- daily_surface_limit_total: `{payload.get('daily_surface_limit_total', '-')}`",
        "",
        "## Detector Rows",
    ]
    for row in payload.get("rows", []):
        lines.extend(
            [
                f"- `{row['detector_key']}` | {row['label_ko']}",
                f"  daily_surface_limit: `{row['daily_surface_limit']}`",
                f"  min_repeat_sample: `{row['min_repeat_sample']}`",
                f"  notes: {row['notes_ko']}",
            ]
        )
    return "\n".join(lines)


def write_improvement_detector_policy_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_improvement_detector_policy_baseline()
    default_json_path, default_markdown_path = default_improvement_detector_policy_baseline_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    resolved_markdown_path.write_text(render_improvement_detector_policy_markdown(payload), encoding="utf-8")
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
