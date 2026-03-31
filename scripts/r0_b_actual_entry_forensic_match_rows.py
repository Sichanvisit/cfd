from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.storage_compaction import is_generic_runtime_signal_row_key


DATA_TRADES = ROOT / "data" / "trades"
ENTRY_DECISIONS_ARCHIVE_ROOT = DATA_TRADES / "archive" / "entry_decisions"
ENTRY_DECISIONS_ARCHIVE_MANIFEST_ROOT = ROOT / "data" / "manifests" / "archive"
ENTRY_DECISIONS = DATA_TRADES / "entry_decisions.csv"
ENTRY_DECISIONS_DETAIL = DATA_TRADES / "entry_decisions.detail.jsonl"
DEFAULT_SAMPLE_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b1_adverse_entry_samples_latest.json"
)
OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
REPORT_VERSION = "r0_b2_decision_row_match_v1"
ARCHIVE_BATCH_SIZE = 5000
MATCH_ROW_FIELDS = (
    "time",
    "symbol",
    "action",
    "outcome",
    "setup_id",
    "observe_reason",
    "blocked_by",
    "action_none_reason",
    "quick_trace_state",
    "quick_trace_reason",
    "probe_plan_ready",
    "probe_plan_reason",
    "entry_wait_state",
    "entry_wait_reason",
    "consumer_check_stage",
    "consumer_check_entry_ready",
    "r0_non_action_family",
    "r0_semantic_runtime_state",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
)

_TICKET_COMPONENT_RE = re.compile(r"\|ticket=\d+")
_ENTERED_OUTCOMES = {"entered", "open", "filled", "submitted", "executed"}


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        if not text:
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_decision_sources(base_dir: Path = DATA_TRADES) -> list[Path]:
    sources: list[Path] = []
    active = base_dir / "entry_decisions.csv"
    if active.exists():
        sources.append(active)
    for path in sorted(base_dir.glob("entry_decisions.legacy_*.csv")):
        if path.exists():
            sources.append(path)
    return sources


def _resolve_archive_output_path(value: Any) -> Path | None:
    text = _coerce_text(value)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _load_archive_manifest_windows(
    manifest_root: Path = ENTRY_DECISIONS_ARCHIVE_MANIFEST_ROOT,
) -> dict[Path, tuple[datetime | None, datetime | None]]:
    windows: dict[Path, tuple[datetime | None, datetime | None]] = {}
    if not manifest_root.exists():
        return windows
    for path in sorted(manifest_root.glob("entry_decisions_archive_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        output_path = _resolve_archive_output_path(payload.get("output_path"))
        if output_path is None:
            continue
        windows[output_path] = (
            _parse_dt(payload.get("time_range_start")),
            _parse_dt(payload.get("time_range_end")),
        )
    return windows


def _parse_archive_partition_window(path: Path) -> tuple[datetime | None, datetime | None]:
    year_text = ""
    month_text = ""
    day_text = ""
    for parent in path.parents:
        name = parent.name
        if name.startswith("day="):
            day_text = name.split("=", 1)[1]
        elif name.startswith("month="):
            month_text = name.split("=", 1)[1]
        elif name.startswith("year="):
            year_text = name.split("=", 1)[1]
    if not (year_text and month_text and day_text):
        return None, None
    try:
        start_dt = datetime.strptime(f"{year_text}-{month_text}-{day_text}", "%Y-%m-%d")
    except Exception:
        return None, None
    return start_dt, start_dt + timedelta(days=1)


def discover_decision_archive_sources(
    *,
    archive_root: Path = ENTRY_DECISIONS_ARCHIVE_ROOT,
    archive_manifest_root: Path = ENTRY_DECISIONS_ARCHIVE_MANIFEST_ROOT,
    sample_open_times: list[datetime] | None = None,
    fallback_window_sec: float = 180.0,
) -> list[Path]:
    if not archive_root.exists():
        return []
    candidates = sorted(path for path in archive_root.rglob("*.parquet") if path.is_file())
    if not sample_open_times:
        return candidates

    manifest_windows = _load_archive_manifest_windows(archive_manifest_root)
    pad = timedelta(seconds=max(0.0, float(fallback_window_sec)))
    selected: list[Path] = []
    for path in candidates:
        start_dt, end_dt = manifest_windows.get(path, (None, None))
        if start_dt is None and end_dt is None:
            start_dt, end_dt = _parse_archive_partition_window(path)
        if start_dt is None and end_dt is None:
            selected.append(path)
            continue
        if start_dt is None:
            start_dt = end_dt
        if end_dt is None:
            end_dt = start_dt
        if start_dt is None or end_dt is None:
            selected.append(path)
            continue
        lower_bound = start_dt - pad
        upper_bound = end_dt + pad
        if any(lower_bound <= sample_dt <= upper_bound for sample_dt in sample_open_times):
            selected.append(path)
    return selected


def _read_first_detail_payload_time(path: Path) -> datetime | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline().strip()
        if not first_line:
            return None
        payload = json.loads(first_line)
        detail_payload = dict(payload.get("payload", {}) or {})
        return _parse_dt(detail_payload.get("time"))
    except Exception:
        return None


def _estimate_detail_source_end_time(path: Path) -> datetime | None:
    match = re.search(r"rotate_(\d{8})_(\d{6})_(\d+)", path.name)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S")
        except Exception:
            return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return None


def discover_decision_detail_sources(
    *,
    base_dir: Path = DATA_TRADES,
    sample_open_times: list[datetime] | None = None,
    fallback_window_sec: float = 180.0,
) -> list[Path]:
    candidates: list[Path] = []
    active = base_dir / "entry_decisions.detail.jsonl"
    if active.exists():
        candidates.append(active)
    for path in sorted(base_dir.glob("entry_decisions.legacy_*.detail.jsonl")):
        if path.exists():
            candidates.append(path)
    for path in sorted(base_dir.glob("entry_decisions.detail.rotate_*.jsonl")):
        if path.exists():
            candidates.append(path)

    if not sample_open_times:
        return candidates

    selected: list[Path] = []
    pad_sec = max(0.0, float(fallback_window_sec))
    for path in candidates:
        start_dt = _read_first_detail_payload_time(path)
        end_dt = _estimate_detail_source_end_time(path)
        if start_dt is None and end_dt is None:
            selected.append(path)
            continue
        if start_dt is None:
            start_dt = end_dt
        if end_dt is None:
            end_dt = start_dt
        if start_dt is None or end_dt is None:
            selected.append(path)
            continue
        lower_bound = start_dt.timestamp() - pad_sec
        upper_bound = end_dt.timestamp() + pad_sec
        if any(lower_bound <= sample_dt.timestamp() <= upper_bound for sample_dt in sample_open_times):
            selected.append(path)
    return selected


def _replace_ticket_with_zero(value: str) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    return _TICKET_COMPONENT_RE.sub("|ticket=0", text)


def _build_sample_index(report: dict[str, Any]) -> list[dict[str, Any]]:
    indexed: list[dict[str, Any]] = []
    for rank, sample in enumerate(list(report.get("top_samples", []) or []), start=1):
        direction = _coerce_text(sample.get("direction")).upper()
        open_dt = _parse_dt(sample.get("open_time"))
        decision_row_key = _coerce_text(sample.get("decision_row_key"))
        replay_row_key = _coerce_text(sample.get("replay_row_key"))
        indexed.append(
            {
                **sample,
                "_sample_rank": int(rank),
                "_symbol": _coerce_text(sample.get("symbol")).upper(),
                "_direction": direction,
                "_setup_id": _coerce_text(sample.get("entry_setup_id")),
                "_open_dt": open_dt,
                "_decision_row_key": decision_row_key,
                "_replay_row_key": replay_row_key,
                "_trade_link_key": _coerce_text(sample.get("trade_link_key")),
                "_runtime_snapshot_key": _coerce_text(sample.get("runtime_snapshot_key")),
                "_ticketless_decision_row_key": _replace_ticket_with_zero(decision_row_key),
                "_ticketless_replay_row_key": _replace_ticket_with_zero(replay_row_key),
            }
        )
    return indexed


def _candidate_score(
    *,
    strategy: str,
    sample: dict[str, Any],
    row: dict[str, Any],
    time_delta_sec: float | None,
) -> float:
    exact_scores = {
        "exact_decision_row_key": 100.0,
        "exact_replay_row_key": 98.0,
        "exact_trade_link_key": 96.0,
        "exact_runtime_snapshot_key": 90.0,
        "ticketless_decision_row_key": 88.0,
        "ticketless_replay_row_key": 86.0,
    }
    if strategy in exact_scores:
        return exact_scores[strategy]

    score = 40.0
    action = _coerce_text(row.get("action")).upper()
    outcome = _coerce_text(row.get("outcome")).lower()
    setup_id = _coerce_text(row.get("setup_id"))
    if action and action == sample["_direction"]:
        score += 15.0
    if setup_id and setup_id == sample["_setup_id"]:
        score += 15.0
    if outcome in _ENTERED_OUTCOMES:
        score += 10.0
    if time_delta_sec is not None:
        score += max(0.0, 20.0 - min(float(time_delta_sec), 600.0) / 30.0)
    return round(score, 4)


def _match_strategy_for_exact(sample: dict[str, Any], row: dict[str, Any]) -> str:
    row_decision_row_key = _coerce_text(row.get("decision_row_key"))
    row_replay_row_key = _coerce_text(row.get("replay_row_key"))
    row_trade_link_key = _coerce_text(row.get("trade_link_key"))
    row_runtime_snapshot_key = _coerce_text(row.get("runtime_snapshot_key"))

    if sample["_decision_row_key"] and row_decision_row_key == sample["_decision_row_key"]:
        return "exact_decision_row_key"
    if sample["_replay_row_key"] and row_replay_row_key == sample["_replay_row_key"]:
        return "exact_replay_row_key"
    if sample["_trade_link_key"] and row_trade_link_key == sample["_trade_link_key"]:
        return "exact_trade_link_key"
    if (
        sample["_runtime_snapshot_key"]
        and row_runtime_snapshot_key == sample["_runtime_snapshot_key"]
        and not is_generic_runtime_signal_row_key(sample["_runtime_snapshot_key"])
        and not is_generic_runtime_signal_row_key(row_runtime_snapshot_key)
    ):
        return "exact_runtime_snapshot_key"
    if sample["_ticketless_decision_row_key"] and row_decision_row_key == sample["_ticketless_decision_row_key"]:
        return "ticketless_decision_row_key"
    if sample["_ticketless_replay_row_key"] and row_replay_row_key == sample["_ticketless_replay_row_key"]:
        return "ticketless_replay_row_key"
    return ""


def _fallback_strategy(sample: dict[str, Any], row: dict[str, Any]) -> str:
    has_setup = bool(sample["_setup_id"] and _coerce_text(row.get("setup_id")) == sample["_setup_id"])
    has_action = bool(sample["_direction"] and _coerce_text(row.get("action")).upper() == sample["_direction"])
    if has_setup and has_action:
        return "fallback_symbol_action_setup_time"
    if has_action:
        return "fallback_symbol_action_time"
    return "fallback_symbol_time"


def _flatten_row(row: dict[str, Any], *, source_name: str) -> dict[str, Any]:
    return {
        "matched_source": source_name,
        "matched_time": _coerce_text(row.get("time")),
        "matched_symbol": _coerce_text(row.get("symbol")).upper(),
        "matched_action": _coerce_text(row.get("action")).upper(),
        "matched_outcome": _coerce_text(row.get("outcome")).lower(),
        "matched_setup_id": _coerce_text(row.get("setup_id")),
        "matched_observe_reason": _coerce_text(row.get("observe_reason")),
        "matched_blocked_by": _coerce_text(row.get("blocked_by")),
        "matched_action_none_reason": _coerce_text(row.get("action_none_reason")),
        "matched_quick_trace_state": _coerce_text(row.get("quick_trace_state")),
        "matched_quick_trace_reason": _coerce_text(row.get("quick_trace_reason")),
        "matched_probe_plan_ready": _coerce_text(row.get("probe_plan_ready")),
        "matched_probe_plan_reason": _coerce_text(row.get("probe_plan_reason")),
        "matched_entry_wait_state": _coerce_text(row.get("entry_wait_state")),
        "matched_entry_wait_reason": _coerce_text(row.get("entry_wait_reason")),
        "matched_consumer_check_stage": _coerce_text(row.get("consumer_check_stage")),
        "matched_consumer_check_entry_ready": _coerce_text(row.get("consumer_check_entry_ready")),
        "matched_r0_non_action_family": _coerce_text(row.get("r0_non_action_family")),
        "matched_r0_semantic_runtime_state": _coerce_text(row.get("r0_semantic_runtime_state")),
        "matched_decision_row_key": _coerce_text(row.get("decision_row_key")),
        "matched_runtime_snapshot_key": _coerce_text(row.get("runtime_snapshot_key")),
        "matched_trade_link_key": _coerce_text(row.get("trade_link_key")),
        "matched_replay_row_key": _coerce_text(row.get("replay_row_key")),
    }


def _consider_row_for_matches(
    *,
    row: dict[str, Any],
    source_name: str,
    samples: list[dict[str, Any]],
    exact_key_candidates: dict[str, list[int]],
    samples_by_symbol: dict[str, list[dict[str, Any]]],
    best_match_by_rank: dict[int, dict[str, Any]],
    fallback_window_sec: float,
) -> datetime | None:
    row_time = _parse_dt(row.get("time"))

    exact_sample_ranks: set[int] = set()
    for field in ("decision_row_key", "replay_row_key", "trade_link_key", "runtime_snapshot_key"):
        key_value = _coerce_text(row.get(field))
        if key_value and key_value in exact_key_candidates:
            exact_sample_ranks.update(exact_key_candidates[key_value])

    for sample_rank in exact_sample_ranks:
        sample = samples[sample_rank - 1]
        strategy = _match_strategy_for_exact(sample, row)
        if not strategy:
            continue
        score = _candidate_score(strategy=strategy, sample=sample, row=row, time_delta_sec=None)
        candidate = {
            "match_status": "exact",
            "match_strategy": strategy,
            "match_score": score,
            "time_delta_sec": None,
            **_flatten_row(row, source_name=source_name),
        }
        existing = best_match_by_rank.get(sample_rank)
        if existing is None or float(candidate["match_score"]) > float(existing["match_score"]):
            best_match_by_rank[sample_rank] = candidate

    symbol = _coerce_text(row.get("symbol")).upper()
    if not symbol or symbol not in samples_by_symbol:
        return row_time
    row_action = _coerce_text(row.get("action")).upper()
    row_setup = _coerce_text(row.get("setup_id"))
    for sample in samples_by_symbol[symbol]:
        sample_rank = int(sample["_sample_rank"])
        if sample_rank in best_match_by_rank and best_match_by_rank[sample_rank]["match_status"] == "exact":
            continue
        if sample["_open_dt"] is None or row_time is None:
            continue
        time_delta_sec = abs((row_time - sample["_open_dt"]).total_seconds())
        if time_delta_sec > float(fallback_window_sec):
            continue
        if sample["_direction"] and row_action and sample["_direction"] != row_action:
            continue
        if sample["_setup_id"] and row_setup and sample["_setup_id"] != row_setup:
            continue
        strategy = _fallback_strategy(sample, row)
        score = _candidate_score(
            strategy=strategy,
            sample=sample,
            row=row,
            time_delta_sec=time_delta_sec,
        )
        candidate = {
            "match_status": "fallback",
            "match_strategy": strategy,
            "match_score": score,
            "time_delta_sec": round(float(time_delta_sec), 3),
            **_flatten_row(row, source_name=source_name),
        }
        existing = best_match_by_rank.get(sample_rank)
        if existing is None:
            best_match_by_rank[sample_rank] = candidate
            continue
        if float(candidate["match_score"]) > float(existing["match_score"]):
            best_match_by_rank[sample_rank] = candidate
            continue
        if (
            float(candidate["match_score"]) == float(existing["match_score"])
            and candidate["time_delta_sec"] is not None
            and (
                existing.get("time_delta_sec") is None
                or float(candidate["time_delta_sec"]) < float(existing["time_delta_sec"])
            )
        ):
            best_match_by_rank[sample_rank] = candidate
    return row_time


def _iter_archive_rows(source: Path):
    parquet = pq.ParquetFile(source)
    available_columns = [column for column in MATCH_ROW_FIELDS if column in parquet.schema_arrow.names]
    if not available_columns:
        return
    for batch in parquet.iter_batches(columns=available_columns, batch_size=ARCHIVE_BATCH_SIZE):
        for row in batch.to_pylist():
            yield dict(row or {})


def build_actual_entry_forensic_match_report(
    *,
    sample_report_path: Path = DEFAULT_SAMPLE_REPORT,
    decision_sources: list[Path] | None = None,
    decision_detail_sources: list[Path] | None = None,
    decision_archive_sources: list[Path] | None = None,
    fallback_window_sec: float = 180.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sample_report = _load_json(sample_report_path)
    samples = _build_sample_index(sample_report)
    sample_open_times = [sample["_open_dt"] for sample in samples if sample["_open_dt"] is not None]
    resolved_decision_sources = discover_decision_sources() if decision_sources is None else decision_sources
    sources = [Path(path) for path in resolved_decision_sources if Path(path).exists()]
    resolved_detail_sources = (
        discover_decision_detail_sources(
            base_dir=DATA_TRADES,
            sample_open_times=sample_open_times,
            fallback_window_sec=float(fallback_window_sec),
        )
        if decision_detail_sources is None
        else decision_detail_sources
    )
    detail_sources = [Path(path) for path in resolved_detail_sources if Path(path).exists()]
    resolved_archive_sources = (
        discover_decision_archive_sources(
            archive_root=ENTRY_DECISIONS_ARCHIVE_ROOT,
            archive_manifest_root=ENTRY_DECISIONS_ARCHIVE_MANIFEST_ROOT,
            sample_open_times=sample_open_times,
            fallback_window_sec=float(fallback_window_sec),
        )
        if decision_archive_sources is None
        else decision_archive_sources
    )
    archive_sources = [Path(path) for path in resolved_archive_sources if Path(path).exists()]

    best_match_by_rank: dict[int, dict[str, Any]] = {}
    coverage_start: datetime | None = None
    coverage_end: datetime | None = None
    total_rows = 0

    exact_key_candidates: dict[str, list[int]] = defaultdict(list)
    for sample in samples:
        for key_name in (
            "_decision_row_key",
            "_replay_row_key",
            "_trade_link_key",
            "_runtime_snapshot_key",
            "_ticketless_decision_row_key",
            "_ticketless_replay_row_key",
        ):
            key_value = _coerce_text(sample.get(key_name))
            if key_value:
                exact_key_candidates[key_value].append(int(sample["_sample_rank"]))

    samples_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        if sample["_symbol"]:
            samples_by_symbol[sample["_symbol"]].append(sample)

    for source in sources:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                total_rows += 1
                row_time = _consider_row_for_matches(
                    row=row,
                    source_name=source.name,
                    samples=samples,
                    exact_key_candidates=exact_key_candidates,
                    samples_by_symbol=samples_by_symbol,
                    best_match_by_rank=best_match_by_rank,
                    fallback_window_sec=float(fallback_window_sec),
                )
                if row_time is not None:
                    coverage_start = row_time if coverage_start is None else min(coverage_start, row_time)
                    coverage_end = row_time if coverage_end is None else max(coverage_end, row_time)

    for source in detail_sources:
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                row = dict(payload.get("payload", {}) or {})
                if not row:
                    continue
                total_rows += 1
                row_time = _consider_row_for_matches(
                    row=row,
                    source_name=source.name,
                    samples=samples,
                    exact_key_candidates=exact_key_candidates,
                    samples_by_symbol=samples_by_symbol,
                    best_match_by_rank=best_match_by_rank,
                    fallback_window_sec=float(fallback_window_sec),
                )
                if row_time is not None:
                    coverage_start = row_time if coverage_start is None else min(coverage_start, row_time)
                    coverage_end = row_time if coverage_end is None else max(coverage_end, row_time)

    for source in archive_sources:
        for row in _iter_archive_rows(source):
            total_rows += 1
            row_time = _consider_row_for_matches(
                row=row,
                source_name=source.name,
                samples=samples,
                exact_key_candidates=exact_key_candidates,
                samples_by_symbol=samples_by_symbol,
                best_match_by_rank=best_match_by_rank,
                fallback_window_sec=float(fallback_window_sec),
            )
            if row_time is not None:
                coverage_start = row_time if coverage_start is None else min(coverage_start, row_time)
                coverage_end = row_time if coverage_end is None else max(coverage_end, row_time)

    matches: list[dict[str, Any]] = []
    strategy_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    for sample in samples:
        sample_rank = int(sample["_sample_rank"])
        match = best_match_by_rank.get(sample_rank, {})
        sample_open_dt = sample["_open_dt"]
        within_coverage = False
        if sample_open_dt is not None and coverage_start is not None and coverage_end is not None:
            within_coverage = bool(coverage_start <= sample_open_dt <= coverage_end)
        if match:
            status = str(match.get("match_status", "") or "")
        else:
            status = "unmatched_outside_coverage" if not within_coverage else "unmatched_no_candidate"
            match = {
                "match_status": status,
                "match_strategy": "",
                "match_score": 0.0,
                "time_delta_sec": None,
                "matched_source": "",
                "matched_time": "",
                "matched_symbol": "",
                "matched_action": "",
                "matched_outcome": "",
                "matched_setup_id": "",
                "matched_observe_reason": "",
                "matched_blocked_by": "",
                "matched_action_none_reason": "",
                "matched_quick_trace_state": "",
                "matched_quick_trace_reason": "",
                "matched_probe_plan_ready": "",
                "matched_probe_plan_reason": "",
                "matched_entry_wait_state": "",
                "matched_entry_wait_reason": "",
                "matched_consumer_check_stage": "",
                "matched_consumer_check_entry_ready": "",
                "matched_r0_non_action_family": "",
                "matched_r0_semantic_runtime_state": "",
                "matched_decision_row_key": "",
                "matched_runtime_snapshot_key": "",
                "matched_trade_link_key": "",
                "matched_replay_row_key": "",
            }

        strategy = str(match.get("match_strategy", "") or "")
        if strategy:
            strategy_counts[strategy] += 1
        status_counts[status] += 1
        matches.append(
            {
                "sample_rank": sample_rank,
                "ticket": int(_safe_float(sample.get("ticket"), 0)),
                "symbol": sample["_symbol"],
                "direction": sample["_direction"],
                "open_time": _coerce_text(sample.get("open_time")),
                "close_time": _coerce_text(sample.get("close_time")),
                "entry_setup_id": sample["_setup_id"],
                "resolved_pnl": round(_safe_float(sample.get("resolved_pnl")), 4),
                "hold_seconds": round(_safe_float(sample.get("hold_seconds")), 3),
                "priority_score": round(_safe_float(sample.get("priority_score")), 4),
                "forensic_ready": bool(sample.get("forensic_ready", False)),
                "within_decision_log_coverage": bool(within_coverage),
                "sample_decision_row_key": sample["_decision_row_key"],
                "sample_runtime_snapshot_key": sample["_runtime_snapshot_key"],
                "sample_trade_link_key": sample["_trade_link_key"],
                "sample_replay_row_key": sample["_replay_row_key"],
                "sample_adverse_signals": list(sample.get("adverse_signals", []) or []),
                **match,
            }
        )

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "sample_report_path": str(sample_report_path),
        "decision_sources": [str(path) for path in sources],
        "decision_detail_sources": [str(path) for path in detail_sources],
        "decision_archive_sources": [str(path) for path in archive_sources],
        "fallback_window_sec": float(fallback_window_sec),
        "coverage": {
            "earliest_time": coverage_start.isoformat(timespec="seconds") if coverage_start else "",
            "latest_time": coverage_end.isoformat(timespec="seconds") if coverage_end else "",
            "rows_scanned": int(total_rows),
            "source_count": int(len(sources) + len(detail_sources) + len(archive_sources)),
        },
        "summary": {
            "sample_rows": int(len(samples)),
            "matched_rows": int(sum(1 for item in matches if item["match_status"] in {"exact", "fallback"})),
            "exact_matches": int(sum(1 for item in matches if item["match_status"] == "exact")),
            "fallback_matches": int(sum(1 for item in matches if item["match_status"] == "fallback")),
            "unmatched_rows": int(sum(1 for item in matches if item["match_status"].startswith("unmatched"))),
            "unmatched_outside_coverage": int(sum(1 for item in matches if item["match_status"] == "unmatched_outside_coverage")),
            "forensic_ready_samples": int(sum(1 for sample in samples if bool(sample.get("forensic_ready", False)))),
        },
        "match_strategy_counts": dict(strategy_counts.most_common()),
        "match_status_counts": dict(status_counts.most_common()),
        "matches": matches,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("summary", {}) or {})
    lines = [
        "# R0-B2 Decision Row Matches",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- sample_rows: `{summary.get('sample_rows', 0)}`",
        f"- matched_rows: `{summary.get('matched_rows', 0)}`",
        f"- exact_matches: `{summary.get('exact_matches', 0)}`",
        f"- fallback_matches: `{summary.get('fallback_matches', 0)}`",
        f"- unmatched_outside_coverage: `{summary.get('unmatched_outside_coverage', 0)}`",
        f"- decision_archive_sources: `{len(list(report.get('decision_archive_sources', []) or []))}`",
        "",
        "## Match Strategies",
    ]
    strategy_counts = dict(report.get("match_strategy_counts", {}) or {})
    if strategy_counts:
        for key, value in strategy_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Top Match Rows"])
    for item in list(report.get("matches", []) or [])[:10]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"ticket={item.get('ticket', 0)}",
                    f"symbol={item.get('symbol', '')}",
                    f"setup={item.get('entry_setup_id', '')}",
                    f"status={item.get('match_status', '')}",
                    f"strategy={item.get('match_strategy', '')}",
                    f"score={item.get('match_score', 0.0)}",
                    f"delta={item.get('time_delta_sec', '')}",
                    f"matched_time={item.get('matched_time', '')}",
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_actual_entry_forensic_match_report(
    *,
    sample_report_path: Path = DEFAULT_SAMPLE_REPORT,
    output_dir: Path = OUT_DIR,
    decision_sources: list[Path] | None = None,
    decision_detail_sources: list[Path] | None = None,
    decision_archive_sources: list[Path] | None = None,
    fallback_window_sec: float = 180.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_actual_entry_forensic_match_report(
        sample_report_path=sample_report_path,
        decision_sources=decision_sources,
        decision_detail_sources=decision_detail_sources,
        decision_archive_sources=decision_archive_sources,
        fallback_window_sec=fallback_window_sec,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "r0_b2_decision_row_matches_latest.json"
    latest_csv = output_dir / "r0_b2_decision_row_matches_latest.csv"
    latest_md = output_dir / "r0_b2_decision_row_matches_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report.get("matches", []) or []).to_csv(latest_csv, index=False, encoding="utf-8-sig")
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-report", type=str, default=str(DEFAULT_SAMPLE_REPORT))
    parser.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    parser.add_argument("--fallback-window-sec", type=float, default=180.0)
    args = parser.parse_args(argv)
    result = write_actual_entry_forensic_match_report(
        sample_report_path=Path(args.sample_report),
        output_dir=Path(args.output_dir),
        fallback_window_sec=float(args.fallback_window_sec),
    )
    summary = dict(result["report"].get("summary", {}) or {})
    print(
        json.dumps(
            {
                "ok": True,
                "latest_json_path": result["latest_json_path"],
                "latest_csv_path": result["latest_csv_path"],
                "latest_markdown_path": result["latest_markdown_path"],
                "matched_rows": summary.get("matched_rows", 0),
                "exact_matches": summary.get("exact_matches", 0),
                "fallback_matches": summary.get("fallback_matches", 0),
                "unmatched_rows": summary.get("unmatched_rows", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
