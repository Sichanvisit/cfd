from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_STATUS = ROOT / "data" / "runtime_status.json"
DEFAULT_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OUT_DIR = ROOT / "data" / "analysis"

LOWER_ZONES = {"BELOW", "LOWER_EDGE", "LOWER"}
UPPER_ZONES = {"ABOVE", "UPPER_EDGE", "UPPER"}
EDGE_ZONES = {"BELOW", "LOWER_EDGE", "UPPER_EDGE", "ABOVE"}


@dataclass
class PositionCase:
    symbol: str
    updated_at: str
    primary_label: str
    bias_label: str
    secondary_context_label: str
    raw_alignment_label: str
    softening_reason: str
    box_zone: str
    bb20_zone: str
    bb44_zone: str
    lower_force: float
    upper_force: float
    middle_neutrality: float
    conflict_score: float
    position_seed: str
    position_phase: str
    human_summary: str
    latest_action: str
    latest_outcome: str
    latest_reason: str


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _read_csv_tail_rows(path: Path, row_limit: int = 16) -> list[dict[str, str]]:
    if not path.exists():
        return []
    chunk_size = 1024 * 1024
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                position = handle.tell()
                buffer = b""
                needed_newlines = row_limit + 2
                while position > 0 and buffer.count(b"\n") < needed_newlines:
                    read_size = min(chunk_size, position)
                    position -= read_size
                    handle.seek(position)
                    buffer = handle.read(read_size) + buffer
            text = buffer.decode(encoding, errors="ignore")
            lines = [line for line in text.splitlines() if line.strip()]
            if len(lines) <= 1:
                continue
            header = lines[0]
            tail_lines = list(deque(lines[1:], maxlen=row_limit))
            csv_text = "\n".join([header, *tail_lines]) + "\n"
            return list(csv.DictReader(StringIO(csv_text)))
        except Exception:
            continue
    return []


def _parse_json_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = _safe_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _zone_side(zone: str) -> str:
    label = _safe_text(zone).upper()
    if label in LOWER_ZONES:
        return "LOWER"
    if label in UPPER_ZONES:
        return "UPPER"
    return "MIDDLE"


def _find_position_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    candidates = [
        row.get("position_snapshot_v2"),
        ((row.get("current_entry_context_v1") or {}).get("position_snapshot_v2")),
        (((row.get("current_entry_context_v1") or {}).get("metadata") or {}).get("position_snapshot_v2")),
    ]
    for candidate in candidates:
        payload = _parse_json_value(candidate)
        if payload:
            return payload
    return {}


def _latest_decisions_by_symbol(path: Path) -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    for row in _read_csv_tail_rows(path, row_limit=48):
        symbol = _safe_text(row.get("symbol")).upper()
        timestamp = _safe_text(row.get("time"))
        if not symbol or not timestamp:
            continue
        prev = latest.get(symbol)
        if prev is None or timestamp >= _safe_text(prev.get("time")):
            latest[symbol] = row
    return latest


def _classify_position_only(
    *,
    primary_label: str,
    bias_label: str,
    secondary_context_label: str,
    box_zone: str,
    bb20_zone: str,
    bb44_zone: str,
) -> tuple[str, str, str]:
    box_side = _zone_side(box_zone)
    bb20_side = _zone_side(bb20_zone)
    bb44_side = _zone_side(bb44_zone)
    sides = [box_side, bb20_side, bb44_side]
    upper_count = sum(1 for side in sides if side == "UPPER")
    lower_count = sum(1 for side in sides if side == "LOWER")
    middle_count = sum(1 for side in sides if side == "MIDDLE")

    if "CONFLICT" in primary_label.upper() or (upper_count > 0 and lower_count > 0):
        return (
            "대기",
            "혼합 구간",
            (
                f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}가 서로 섞여 있다. "
                "이 자리는 Position 혼자 방향을 확정하면 안 되고, 뒤 레이어로 넘겨야 한다."
            ),
        )

    if upper_count >= 2 and lower_count == 0:
        if bb44_side == "UPPER":
            return (
                "매도 씨앗",
                "상단 앵커",
                (
                    f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}. "
                    "Position 기준으로는 상단 자리이므로 기본 방향 씨앗은 매도다."
                ),
            )
        return (
            "매도 씨앗",
            "상단 bias, 아직 확정 전",
            (
                f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}. "
                "상단 쪽은 맞지만, 아직 완전한 상단 정렬은 아니라서 반응 확인이 더 필요하다."
            ),
        )

    if lower_count >= 2 and upper_count == 0:
        if bb44_side == "LOWER":
            return (
                "매수 씨앗",
                "하단 앵커",
                (
                    f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}. "
                    "Position 기준으로는 하단 자리이므로 기본 방향 씨앗은 매수다."
                ),
            )
        return (
            "매수 씨앗",
            "하단 bias, 아직 확정 전",
            (
                f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}. "
                "하단 쪽은 맞지만, 아직 완전한 하단 정렬은 아니라서 반응 확인이 더 필요하다."
            ),
        )

    if middle_count >= 2 or "MIDDLE" in primary_label.upper() or "MIDDLE" in bias_label.upper():
        return (
            "대기",
            "중앙 handoff",
            (
                f"box={box_zone}, bb20={bb20_zone}, bb44={bb44_zone}. "
                "중앙 성격이 강해서 Position이 방향을 세게 말하면 안 된다."
            ),
        )

    if "UPPER" in secondary_context_label.upper():
        return (
            "매도 씨앗",
            "컨텍스트 상단 bias",
            "보조 컨텍스트는 상단 쪽이지만, 아직 Position만으로 강하게 확정할 정도는 아니다.",
        )
    if "LOWER" in secondary_context_label.upper():
        return (
            "매수 씨앗",
            "컨텍스트 하단 bias",
            "보조 컨텍스트는 하단 쪽이지만, 아직 Position만으로 강하게 확정할 정도는 아니다.",
        )

    return (
        "대기",
        "미해결 handoff",
        "Position만으로는 방향이 깨끗하게 안 나온다. Response와 그 뒤 레이어가 이어받아야 한다.",
    )


def _ko_label(value: str, *, kind: str) -> str:
    text = _safe_text(value)
    upper = text.upper()
    if not text:
        return "없음"
    zone_map = {
        "BELOW": "박스/밴드 아래",
        "LOWER_EDGE": "하단 끝",
        "LOWER": "하단",
        "MIDDLE": "중앙",
        "MID": "중앙",
        "UPPER": "상단",
        "UPPER_EDGE": "상단 끝",
        "ABOVE": "박스/밴드 위",
    }
    reason_map = {
        "WEAK_ALIGNMENT_REQUIRES_BB44_SIDE_SUPPORT": "bb44가 아직 같은 방향까지 못 와서 약정렬을 bias로 낮춤",
        "ALIGNMENT_NOT_SOFTENED": "정렬 약화 없음",
    }
    if kind == "zone":
        return zone_map.get(upper, text)
    if kind == "softening":
        return reason_map.get(upper, text)
    return text


def _build_cases(
    runtime_status: dict[str, Any],
    latest_decisions: dict[str, dict[str, str]],
    symbols: set[str],
) -> list[PositionCase]:
    cases: list[PositionCase] = []
    updated_at = _safe_text(runtime_status.get("updated_at"))
    latest = runtime_status.get("latest_signal_by_symbol", {})
    if not isinstance(latest, dict):
        return cases

    for symbol, row in latest.items():
        sym = _safe_text(symbol).upper()
        if symbols and sym not in symbols:
            continue
        position_snapshot = _find_position_snapshot(row if isinstance(row, dict) else {})
        interpretation = _parse_json_value(position_snapshot.get("interpretation"))
        zones = _parse_json_value(position_snapshot.get("zones"))
        energy = _parse_json_value(position_snapshot.get("energy"))
        metadata = _parse_json_value(interpretation.get("metadata"))
        softening = _parse_json_value(metadata.get("alignment_softening"))

        primary_label = _safe_text(interpretation.get("primary_label"))
        bias_label = _safe_text(interpretation.get("bias_label"))
        secondary_context_label = _safe_text(interpretation.get("secondary_context_label"))
        raw_alignment_label = _safe_text(metadata.get("raw_alignment_label"))
        softening_reason = _safe_text(softening.get("reason"))
        box_zone = _safe_text(zones.get("box_zone"))
        bb20_zone = _safe_text(zones.get("bb20_zone"))
        bb44_zone = _safe_text(zones.get("bb44_zone"))

        position_seed, position_phase, human_summary = _classify_position_only(
            primary_label=primary_label,
            bias_label=bias_label,
            secondary_context_label=secondary_context_label,
            box_zone=box_zone,
            bb20_zone=bb20_zone,
            bb44_zone=bb44_zone,
        )

        latest_decision = latest_decisions.get(sym, {})
        latest_reason = _safe_text(latest_decision.get("blocked_by")) or _safe_text(
            latest_decision.get("entry_wait_reason")
        ) or _safe_text(((_parse_json_value(latest_decision.get("observe_confirm_v2"))).get("reason")))

        cases.append(
            PositionCase(
                symbol=sym,
                updated_at=updated_at,
                primary_label=primary_label,
                bias_label=bias_label,
                secondary_context_label=secondary_context_label,
                raw_alignment_label=raw_alignment_label,
                softening_reason=softening_reason,
                box_zone=box_zone,
                bb20_zone=bb20_zone,
                bb44_zone=bb44_zone,
                lower_force=_safe_float(energy.get("lower_position_force")),
                upper_force=_safe_float(energy.get("upper_position_force")),
                middle_neutrality=_safe_float(energy.get("middle_neutrality")),
                conflict_score=_safe_float(energy.get("position_conflict_score")),
                position_seed=position_seed,
                position_phase=position_phase,
                human_summary=human_summary,
                latest_action=_safe_text(latest_decision.get("action")).upper(),
                latest_outcome=_safe_text(latest_decision.get("outcome")).lower(),
                latest_reason=latest_reason,
            )
        )
    return sorted(cases, key=lambda item: item.symbol)


def _render_markdown(cases: list[PositionCase]) -> str:
    lines: list[str] = []
    lines.append("# Position 전용 해석 리포트")
    lines.append("")
    lines.append("이 리포트는 `Position`만 떼어 보고, 아래 3가지만 확인한다.")
    lines.append("")
    lines.append("- 지금 가격이 `box / bb20 / bb44` 어디에 있는가")
    lines.append("- Position만 보면 기본 방향 씨앗이 `매수`인지 `매도`인지")
    lines.append("- 아니면 아직 애매해서 뒤 레이어로 넘겨야 하는가")
    lines.append("")
    for case in cases:
        lines.append(f"## {case.symbol}")
        lines.append("")
        lines.append(f"- 기준 시각: `{case.updated_at}`")
        lines.append(f"- Position 최종 판정: `{case.primary_label or 'NONE'}`")
        lines.append(f"- Position bias: `{case.bias_label or 'NONE'}`")
        lines.append(f"- 보조 컨텍스트: `{case.secondary_context_label or 'NONE'}`")
        lines.append(
            f"- 위치 해석: `box={_ko_label(case.box_zone, kind='zone')}`, `bb20={_ko_label(case.bb20_zone, kind='zone')}`, `bb44={_ko_label(case.bb44_zone, kind='zone')}`"
        )
        lines.append(
            f"- 힘의 크기: `하단={case.lower_force:.3f}`, `상단={case.upper_force:.3f}`, `충돌={case.conflict_score:.3f}`, `중앙중립={case.middle_neutrality:.3f}`"
        )
        lines.append(f"- Position만 봤을 때 기본 씨앗: `{case.position_seed}`")
        lines.append(f"- 현재 단계 해석: `{case.position_phase}`")
        if case.raw_alignment_label:
            lines.append(f"- 약화 전 원래 정렬: `{case.raw_alignment_label}`")
        if case.softening_reason:
            lines.append(f"- 정렬 약화 이유: `{_ko_label(case.softening_reason, kind='softening')}`")
        lines.append(f"- 쉬운 설명: {case.human_summary}")
        if case.latest_action or case.latest_outcome or case.latest_reason:
            lines.append(
                f"- 최근 decision 참고: `action={case.latest_action or 'NONE'}`, `outcome={case.latest_outcome or 'none'}`, `reason={case.latest_reason or 'none'}`"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a simple position-only meaning report.")
    parser.add_argument("--runtime-status", type=Path, default=DEFAULT_RUNTIME_STATUS)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--symbols", nargs="*", default=[])
    args = parser.parse_args()

    runtime_status = _read_json(args.runtime_status)
    latest_decisions = _latest_decisions_by_symbol(args.decisions)
    symbols = {str(symbol or "").upper() for symbol in args.symbols if str(symbol or "").strip()}
    cases = _build_cases(runtime_status, latest_decisions, symbols)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    md_path = args.out_dir / f"position_only_report_{stamp}.md"
    json_path = args.out_dir / f"position_only_report_{stamp}.json"

    markdown = _render_markdown(cases)
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps([case.__dict__ for case in cases], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(str(md_path))
    print(str(json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
