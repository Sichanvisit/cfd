from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_STATUS = ROOT / "data" / "runtime_status.json"
DEFAULT_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OUT_DIR = ROOT / "data" / "analysis"


def _now() -> datetime:
    return datetime.now()


def _stamp() -> str:
    return _now().strftime("%Y%m%d_%H%M%S")


def _parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = _safe_text(value)
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def _pick_dict(*candidates: Any) -> dict[str, Any]:
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate
        parsed = _parse_json_value(candidate)
        if isinstance(parsed, dict) and parsed:
            return parsed
    return {}


def _pick_nested_dict(container: dict[str, Any], *paths: tuple[str, ...]) -> dict[str, Any]:
    for path in paths:
        cur: Any = container
        ok = True
        for key in path:
            if not isinstance(cur, dict):
                ok = False
                break
            cur = cur.get(key)
        if not ok:
            continue
        picked = _pick_dict(cur)
        if picked:
            return picked
    return {}


def _position_family(primary_label: str, secondary_context_label: str = "") -> str:
    primary = _safe_text(primary_label).upper()
    secondary = _safe_text(secondary_context_label).upper()
    if "CONFLICT" in primary:
        return "conflict"
    if primary == "UNRESOLVED_POSITION":
        if "LOWER" in secondary:
            return "unresolved_lower_context"
        if "UPPER" in secondary:
            return "unresolved_upper_context"
        return "unresolved"
    if "ALIGNED_MIDDLE" in primary or primary == "MIDDLE":
        return "middle"
    if "LOWER" in primary:
        return "lower"
    if "UPPER" in primary:
        return "upper"
    if "MIDDLE" in primary:
        return "middle"
    return "unknown"


def _position_action_relation(action: str, family: str) -> str:
    side = _safe_text(action).upper()
    if side not in {"BUY", "SELL"}:
        return "no_action"
    if family == "lower":
        return "lower_reversal_like" if side == "BUY" else "lower_continuation_like"
    if family == "upper":
        return "upper_continuation_like" if side == "BUY" else "upper_reversal_like"
    if family == "middle":
        return "middle_ambiguous"
    if family == "conflict":
        return "conflict_ambiguous"
    if family.startswith("unresolved"):
        return "unresolved_ambiguous"
    return "unknown_relation"


def _extract_position_summary(position_snapshot: dict[str, Any]) -> dict[str, Any]:
    interpretation = _pick_dict(position_snapshot.get("interpretation"))
    energy = _pick_dict(position_snapshot.get("energy"))
    zones = _pick_dict(position_snapshot.get("zones"))
    return {
        "primary_label": _safe_text(interpretation.get("primary_label")),
        "bias_label": _safe_text(interpretation.get("bias_label")),
        "secondary_context_label": _safe_text(interpretation.get("secondary_context_label")),
        "conflict_kind": _safe_text(interpretation.get("conflict_kind")),
        "pos_composite": _safe_float(interpretation.get("pos_composite"), 0.0),
        "box_zone": _safe_text(zones.get("box_zone")),
        "bb20_zone": _safe_text(zones.get("bb20_zone")),
        "bb44_zone": _safe_text(zones.get("bb44_zone")),
        "middle_neutrality": _safe_float(energy.get("middle_neutrality"), 0.0),
        "position_conflict_score": _safe_float(energy.get("position_conflict_score"), 0.0),
        "lower_position_force": _safe_float(energy.get("lower_position_force"), 0.0),
        "upper_position_force": _safe_float(energy.get("upper_position_force"), 0.0),
    }


def _extract_runtime_events(
    runtime_obj: dict[str, Any],
    symbols: set[str],
    seen: set[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    updated_at = _safe_text(runtime_obj.get("updated_at"))
    latest = runtime_obj.get("latest_signal_by_symbol", {})
    if not isinstance(latest, dict):
        return events
    for symbol, row in latest.items():
        sym = _safe_text(symbol).upper()
        if symbols and sym not in symbols:
            continue
        if not isinstance(row, dict):
            continue
        signature = ("runtime", updated_at, sym)
        if signature in seen:
            continue
        seen.add(signature)

        ctx = _pick_dict(row.get("current_entry_context_v1"))
        meta = _pick_dict(ctx.get("metadata"))
        position_snapshot = _pick_dict(
            row.get("position_snapshot_v2"),
            ctx.get("position_snapshot_v2"),
            meta.get("position_snapshot_v2"),
        )
        position = _extract_position_summary(position_snapshot)
        family = _position_family(position["primary_label"], position["secondary_context_label"])

        events.append(
            {
                "event_type": "runtime_signal",
                "captured_at": _now().isoformat(timespec="seconds"),
                "runtime_updated_at": updated_at,
                "symbol": sym,
                "box_state": _safe_text(row.get("box_state")),
                "bb_state": _safe_text(row.get("bb_state")),
                "market_mode": _safe_text(row.get("market_mode")),
                "direction_policy": _safe_text(row.get("direction_policy")),
                "preflight_allowed_action": _safe_text(meta.get("preflight_allowed_action_raw")),
                "buy_score": _safe_float(row.get("buy_score"), 0.0),
                "sell_score": _safe_float(row.get("sell_score"), 0.0),
                "wait_score": _safe_float(row.get("wait_score"), 0.0),
                "wait_reasons": row.get("wait_reasons", []),
                "position_family": family,
                "position": position,
            }
        )
    return events


def _extract_decision_events(
    decisions_path: Path,
    symbols: set[str],
    seen: set[tuple[str, ...]],
    started_at: datetime,
    entered_only: bool,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in _read_csv_rows(decisions_path):
        symbol = _safe_text(row.get("symbol")).upper()
        if symbols and symbol not in symbols:
            continue
        row_dt = _parse_dt(row.get("time", ""))
        if row_dt is None or row_dt < started_at:
            continue
        outcome = _safe_text(row.get("outcome")).lower()
        if entered_only and outcome != "entered":
            continue
        signature = (
            "decision",
            _safe_text(row.get("time")),
            symbol,
            _safe_text(row.get("action")),
            outcome,
            _safe_text(row.get("setup_id")),
            _safe_text(row.get("entry_wait_reason")),
            _safe_text(row.get("blocked_by")),
        )
        if signature in seen:
            continue
        seen.add(signature)

        position_snapshot = _pick_dict(row.get("position_snapshot_v2"))
        observe_confirm = _pick_dict(row.get("observe_confirm_v2"))
        position = _extract_position_summary(position_snapshot)
        family = _position_family(position["primary_label"], position["secondary_context_label"])
        action = _safe_text(row.get("action")).upper()

        events.append(
            {
                "event_type": "entry_decision",
                "captured_at": _now().isoformat(timespec="seconds"),
                "decision_time": _safe_text(row.get("time")),
                "signal_bar_ts": _safe_text(row.get("signal_bar_ts")),
                "symbol": symbol,
                "action": action,
                "outcome": outcome,
                "blocked_by": _safe_text(row.get("blocked_by")),
                "entry_stage": _safe_text(row.get("entry_stage")),
                "entry_wait_reason": _safe_text(row.get("entry_wait_reason")),
                "entry_wait_state": _safe_text(row.get("entry_wait_state")),
                "entry_wait_decision": _safe_text(row.get("entry_wait_decision")),
                "setup_id": _safe_text(row.get("setup_id")),
                "setup_status": _safe_text(row.get("setup_status")),
                "setup_trigger_state": _safe_text(row.get("setup_trigger_state")),
                "box_state": _safe_text(row.get("box_state")),
                "bb_state": _safe_text(row.get("bb_state")),
                "direction_policy": _safe_text(row.get("direction_policy")),
                "preflight_allowed_action": _safe_text(row.get("preflight_allowed_action")),
                "entry_score_raw": _safe_float(row.get("entry_score_raw"), 0.0),
                "contra_score_raw": _safe_float(row.get("contra_score_raw"), 0.0),
                "wait_score": _safe_float(row.get("wait_score"), 0.0),
                "observe_confirm_action": _safe_text(observe_confirm.get("action")),
                "observe_confirm_side": _safe_text(observe_confirm.get("side")),
                "position_family": family,
                "position_action_relation": _position_action_relation(action, family),
                "position": position,
            }
        )
    events.sort(key=lambda item: (_safe_text(item.get("decision_time")), _safe_text(item.get("symbol"))))
    return events


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "runtime_signal_count": 0,
        "entry_decision_count": 0,
        "decision_outcomes": Counter(),
        "decision_position_families": Counter(),
        "decision_position_relations": Counter(),
        "entered_by_symbol": Counter(),
        "wait_by_symbol": Counter(),
        "entered_relations": Counter(),
        "position_labels": Counter(),
        "symbol_outcome_position": defaultdict(Counter),
    }
    for event in events:
        event_type = _safe_text(event.get("event_type"))
        if event_type == "runtime_signal":
            summary["runtime_signal_count"] += 1
            continue
        if event_type != "entry_decision":
            continue
        summary["entry_decision_count"] += 1
        symbol = _safe_text(event.get("symbol")).upper()
        outcome = _safe_text(event.get("outcome")).lower()
        family = _safe_text(event.get("position_family"))
        relation = _safe_text(event.get("position_action_relation"))
        position = event.get("position", {}) if isinstance(event.get("position"), dict) else {}
        primary_label = _safe_text(position.get("primary_label"))

        summary["decision_outcomes"][outcome] += 1
        summary["decision_position_families"][family] += 1
        summary["decision_position_relations"][relation] += 1
        summary["position_labels"][primary_label] += 1
        summary["symbol_outcome_position"][f"{symbol}:{outcome}"][primary_label] += 1
        if outcome == "entered":
            summary["entered_by_symbol"][symbol] += 1
            summary["entered_relations"][relation] += 1
        if outcome == "wait":
            summary["wait_by_symbol"][symbol] += 1

    return {
        "runtime_signal_count": int(summary["runtime_signal_count"]),
        "entry_decision_count": int(summary["entry_decision_count"]),
        "decision_outcomes": dict(summary["decision_outcomes"]),
        "decision_position_families": dict(summary["decision_position_families"]),
        "decision_position_relations": dict(summary["decision_position_relations"]),
        "entered_by_symbol": dict(summary["entered_by_symbol"]),
        "wait_by_symbol": dict(summary["wait_by_symbol"]),
        "entered_relations": dict(summary["entered_relations"]),
        "position_labels": dict(summary["position_labels"]),
        "symbol_outcome_position": {
            key: dict(counter) for key, counter in summary["symbol_outcome_position"].items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch live runtime signals and entry decisions through the Position lens.")
    parser.add_argument("--runtime-status", default=str(DEFAULT_RUNTIME_STATUS))
    parser.add_argument("--decisions", default=str(DEFAULT_DECISIONS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--symbols", default="NAS100,XAUUSD,BTCUSD")
    parser.add_argument("--interval-sec", type=float, default=5.0)
    parser.add_argument("--duration-min", type=float, default=2.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--entered-only", action="store_true")
    args = parser.parse_args()

    runtime_status = Path(args.runtime_status).resolve()
    decisions_path = Path(args.decisions).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    symbols = {s.strip().upper() for s in str(args.symbols).split(",") if s.strip()}
    run_id = _stamp()
    jsonl_path = out_dir / f"position_entry_watch_{run_id}.jsonl"
    summary_path = out_dir / f"position_entry_watch_summary_{run_id}.json"

    started_at = _now()
    deadline = time.time() + max(5.0, float(args.duration_min) * 60.0)
    max_cycles = max(0, int(args.max_cycles))
    seen_runtime: set[tuple[str, str, str]] = set()
    seen_decisions: set[tuple[str, ...]] = set()
    collected: list[dict[str, Any]] = []
    cycles = 0

    while True:
        runtime_events = _extract_runtime_events(_read_json(runtime_status), symbols, seen_runtime)
        decision_events = _extract_decision_events(
            decisions_path=decisions_path,
            symbols=symbols,
            seen=seen_decisions,
            started_at=started_at,
            entered_only=bool(args.entered_only),
        )
        for event in runtime_events + decision_events:
            collected.append(event)
            _append_jsonl(jsonl_path, event)
            print(json.dumps(event, ensure_ascii=False))

        cycles += 1
        if max_cycles > 0 and cycles >= max_cycles:
            break
        if time.time() >= deadline:
            break
        time.sleep(max(0.5, float(args.interval_sec)))

    summary = {
        "generated_at": _now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "runtime_status": str(runtime_status),
        "decisions": str(decisions_path),
        "jsonl_path": str(jsonl_path),
        "symbols": sorted(symbols),
        "entered_only": bool(args.entered_only),
        "window_started_at": started_at.isoformat(timespec="seconds"),
        "stats": _summarize(collected),
        "note": "position_action_relation is a monitoring hint for T1-1 Position only, not semantic ownership.",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "summary": str(summary_path), "events": len(collected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
