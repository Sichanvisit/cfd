from __future__ import annotations

import argparse
import csv
import json
import time
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = "_lab_runs"
DEFAULT_SINCE_MIN = 30
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3010"
DEFAULT_MAX_UNKNOWN_RATIO = 0.7
DEFAULT_MIN_CLOSED_ROWS = 20

OPEN_REQUIRED_COLUMNS = {
    "ticket",
    "symbol",
    "direction",
    "open_time",
    "status",
}

CLOSED_REQUIRED_COLUMNS = {
    "ticket",
    "symbol",
    "direction",
    "open_time",
    "close_time",
    "profit",
    "status",
}

UNKNOWN_REASON_SET = {"", "UNKNOWN", "MANUAL/UNKNOWN", "MANUAL", "NONE", "NULL", "N/A"}


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class LabRunner:
    def __init__(
        self,
        since_min: int,
        base_url: str,
        run_dir: str,
        max_unknown_ratio: float,
        min_closed_rows: int,
        strict_trading_check: bool,
        frontend_url: str,
    ):
        self.since_min = int(max(1, since_min))
        self.base_url = str(base_url).rstrip("/")
        self.max_unknown_ratio = max(0.0, min(1.0, float(max_unknown_ratio)))
        self.min_closed_rows = int(max(1, min_closed_rows))
        self.strict_trading_check = bool(strict_trading_check)
        self.frontend_url = str(frontend_url).rstrip("/")
        self.started_at = datetime.now()
        self.stale_cutoff = self.started_at - timedelta(minutes=self.since_min)
        self.run_stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        self.run_root = (PROJECT_ROOT / run_dir / self.run_stamp).resolve()
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.summary: dict[str, Any] = {
            "run_id": self.run_stamp,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "since_min": self.since_min,
            "base_url": self.base_url,
            "max_unknown_ratio": self.max_unknown_ratio,
            "min_closed_rows": self.min_closed_rows,
            "strict_trading_check": self.strict_trading_check,
            "frontend_url": self.frontend_url,
            "steps": [],
            "smoke": {},
            "logcheck": {},
            "overall_status": "FAIL",
            "failure_reasons": [],
            "artifacts": {
                "summary_json": str(self.run_root / "summary.json"),
                "summary_md": str(self.run_root / "summary.md"),
                "plan_md": str(self.run_root / "plan.md"),
            },
        }

    def run(self) -> int:
        self._print_header("RUN")
        self._step_plan()

        smoke_ok = self.step_smoke()
        if not smoke_ok:
            self._record_failure("smoke_failed")
            return self._finalize_and_exit()

        log_ok = self.step_logcheck()
        if not log_ok:
            self._record_failure("logcheck_failed")

        return self._finalize_and_exit()

    def smoke_only(self) -> int:
        self._print_header("SMOKE")
        ok = self.step_smoke()
        if not ok:
            self._record_failure("smoke_failed")
        return self._finalize_and_exit()

    def logcheck_only(self) -> int:
        self._print_header("LOGCHECK")
        ok = self.step_logcheck()
        if not ok:
            self._record_failure("logcheck_failed")
        return self._finalize_and_exit()

    def watch(self, interval_sec: float, iterations: int, fail_fast: bool) -> int:
        interval_sec = max(1.0, float(interval_sec))
        iterations = int(max(0, iterations))
        fail_fast = bool(fail_fast)
        self._print_header("WATCH")
        self._step_plan()

        watch_log_path = self.run_root / "watch_log.jsonl"
        watch_state = {"status": "PASS", "ticks": []}
        tick = 0
        self._print_info(
            f"watch started: interval={interval_sec:.1f}s iterations={'infinite' if iterations == 0 else iterations}"
        )
        self._print_info(f"watch targets: api={self.base_url}, frontend={self.frontend_url}")
        while True:
            tick += 1
            snap = self._watch_tick(tick=tick)
            watch_state["ticks"].append(snap)
            if snap.get("status") == "FAIL":
                watch_state["status"] = "FAIL"
                self._record_failure(f"watch_tick_{tick}_failed")
            with watch_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(snap, ensure_ascii=False) + "\n")

            if snap.get("status") == "PASS":
                self._print_ok(
                    f"tick#{tick}: api={snap.get('api_status')} frontend={snap.get('frontend_status')} "
                    f"runtime_recent={snap.get('runtime_recent')} events_recent={snap.get('events_recent')}"
                )
            else:
                self._print_fail(
                    f"tick#{tick}: api={snap.get('api_status')} frontend={snap.get('frontend_status')} "
                    f"runtime_recent={snap.get('runtime_recent')} events_recent={snap.get('events_recent')} "
                    f"reason={snap.get('reason')}"
                )
                if fail_fast:
                    break

            if iterations > 0 and tick >= iterations:
                break
            time.sleep(interval_sec)

        self.summary["watch"] = watch_state
        self.summary["steps"].append(
            {
                "name": "watch",
                "status": watch_state["status"],
                "detail": f"ticks={tick} log={watch_log_path}",
            }
        )
        return self._finalize_and_exit()

    def _step_plan(self) -> None:
        content = [
            f"# Lab Run Plan ({self.run_stamp})",
            "",
            "Execution order:",
            "1. plan",
            "2. smoke tests",
            "3. logcheck",
            "4. summary",
            "",
            f"- since_min: {self.since_min}",
            f"- base_url: {self.base_url}",
        ]
        plan_path = self.run_root / "plan.md"
        plan_path.write_text("\n".join(content) + "\n", encoding="utf-8")
        self.summary["steps"].append({"name": "plan", "status": "PASS", "detail": str(plan_path)})
        self._print_ok(f"plan written: {plan_path}")

    def step_smoke(self) -> bool:
        tests: list[tuple[str, list[str]]] = [
            (
                "pytest_ops_readiness_gate",
                [sys.executable, "-m", "pytest", "-q", "tests/unit/test_ops_readiness_gate.py"],
            ),
            (
                "pytest_file_observability_adapter",
                [sys.executable, "-m", "pytest", "-q", "tests/unit/test_file_observability_adapter.py"],
            ),
            (
                "pytest_trade_sqlite_regression",
                [sys.executable, "-m", "pytest", "-q", "tests/integration/test_trade_sqlite_regression.py"],
            ),
        ]

        smoke_result: dict[str, Any] = {"checks": [], "status": "PASS"}
        self._print_info("running smoke tests...")
        for name, cmd in tests:
            result = self._run_cmd(name, cmd)
            smoke_result["checks"].append(self._command_to_dict(result))
            if not result.ok:
                smoke_result["status"] = "FAIL"
                smoke_result["failed_at"] = name
                self.summary["smoke"] = smoke_result
                self.summary["steps"].append({"name": "smoke", "status": "FAIL", "detail": name})
                self._print_fail(f"{name} failed (exit={result.returncode})")
                return False
            self._print_ok(f"{name} passed")

        predeploy_result = self._run_optional_predeploy()
        smoke_result["checks"].append(predeploy_result)
        if predeploy_result.get("status") == "FAIL":
            smoke_result["status"] = "FAIL"
            smoke_result["failed_at"] = "predeploy_ops_check"
            self.summary["smoke"] = smoke_result
            self.summary["steps"].append({"name": "smoke", "status": "FAIL", "detail": "predeploy_ops_check"})
            return False

        self.summary["smoke"] = smoke_result
        self.summary["steps"].append({"name": "smoke", "status": "PASS", "detail": "all smoke checks passed"})
        return True

    def _run_optional_predeploy(self) -> dict[str, Any]:
        script = PROJECT_ROOT / "scripts" / "predeploy_ops_check.py"
        health_url = f"{self.base_url}/health"

        if not script.exists():
            self._print_info("predeploy check skipped: script missing")
            return {
                "name": "predeploy_ops_check",
                "status": "SKIP",
                "reason": "script_missing",
                "script": str(script),
            }

        if not self._is_fastapi_alive(health_url):
            self._print_info(f"predeploy check skipped: API not reachable ({health_url})")
            return {
                "name": "predeploy_ops_check",
                "status": "SKIP",
                "reason": "api_not_reachable",
                "health_url": health_url,
            }

        cmd = [sys.executable, str(script), "--base-url", self.base_url]
        result = self._run_cmd("predeploy_ops_check", cmd)
        if not result.ok:
            self._print_fail(f"predeploy_ops_check failed (exit={result.returncode})")
            return self._command_to_dict(result)
        self._print_ok("predeploy_ops_check passed")
        return self._command_to_dict(result)

    def step_logcheck(self) -> bool:
        checks = {
            "trade_history_csv": self._check_csv_file(
                PROJECT_ROOT / "data" / "trades" / "trade_history.csv",
                OPEN_REQUIRED_COLUMNS,
            ),
            "trade_closed_history_csv": self._check_csv_file(
                PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv",
                CLOSED_REQUIRED_COLUMNS,
            ),
            "runtime_status_json": self._check_json_file(
                PROJECT_ROOT / "data" / "runtime_status.json",
            ),
            "observability_events_jsonl": self._check_jsonl_file(
                PROJECT_ROOT / "data" / "observability" / "events.jsonl",
            ),
            "api_bundle": self._check_api_bundle(),
        }
        if self.strict_trading_check:
            checks["trading_logic_bundle"] = self._check_trading_logic_bundle()

        failed = [k for k, v in checks.items() if v.get("status") == "FAIL"]
        log_status = "FAIL" if failed else "PASS"
        self.summary["logcheck"] = {
            "status": log_status,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "since_min": self.since_min,
            "files": checks,
            "failed_items": failed,
        }
        self.summary["steps"].append(
            {
                "name": "logcheck",
                "status": log_status,
                "detail": ", ".join(failed) if failed else "all log checks passed",
            }
        )

        for key, row in checks.items():
            if row.get("status") == "PASS":
                self._print_ok(f"{key}: PASS")
            elif row.get("status") == "SKIP":
                self._print_info(f"{key}: SKIP ({row.get('reason', '')})")
            else:
                self._print_fail(f"{key}: FAIL ({row.get('reason', 'unknown')})")

        return log_status == "PASS"

    def _check_csv_file(self, path: Path, required_columns: set[str]) -> dict[str, Any]:
        base = self._file_meta(path)
        if not base["exists"]:
            base["status"] = "FAIL"
            base["reason"] = "missing_file"
            return base

        data: list[dict[str, str]] = []
        used_encoding = ""
        decode_error = ""
        for enc in ("utf-8-sig", "cp949"):
            try:
                with path.open("r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                    header = list(reader.fieldnames or [])
                used_encoding = enc
                break
            except UnicodeError as exc:
                decode_error = str(exc)
                continue
            except Exception as exc:
                base["status"] = "FAIL"
                base["reason"] = f"csv_read_error: {exc}"
                return base
        else:
            base["status"] = "FAIL"
            base["reason"] = f"csv_decode_failed: {decode_error}"
            return base

        present_cols = set(header)
        missing_cols = sorted([c for c in required_columns if c not in present_cols])
        base["encoding"] = used_encoding
        base["row_count"] = int(len(data))
        base["column_count"] = int(len(header))
        base["columns"] = header
        base["required_columns_missing"] = missing_cols
        base["stale"] = not bool(base["updated_recently"])
        if missing_cols:
            base["status"] = "FAIL"
            base["reason"] = f"missing_required_columns: {', '.join(missing_cols)}"
            return base

        if path.name.lower() == "trade_closed_history.csv":
            quality = self._analyze_closed_quality(data)
            base["quality"] = quality
            if quality.get("status") == "FAIL":
                base["status"] = "FAIL"
                base["reason"] = str(quality.get("reason", "closed_quality_failed"))
                return base

        base["status"] = "PASS"
        base["reason"] = ""
        return base

    def _check_json_file(self, path: Path) -> dict[str, Any]:
        base = self._file_meta(path)
        if not base["exists"]:
            base["status"] = "FAIL"
            base["reason"] = "missing_file"
            return base
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            base["status"] = "FAIL"
            base["reason"] = f"json_parse_error: {exc}"
            return base

        status_block = payload.get("status", payload) if isinstance(payload, dict) else {}
        active_alerts = 0
        rollback_count = 0
        warning_total = 0
        if isinstance(status_block, dict):
            alerts = status_block.get("alerts", {})
            if isinstance(alerts, dict):
                active_alerts = int(alerts.get("active_count", 0) or 0)
            pol = status_block.get("policy_snapshot", {})
            if isinstance(pol, dict):
                pol_runtime = pol.get("policy_runtime", {})
                if isinstance(pol_runtime, dict):
                    rollback_count = int(pol_runtime.get("rollback_count", 0) or 0)
            warn_map = status_block.get("runtime_warning_counters", {})
            if isinstance(warn_map, dict):
                for row in warn_map.values():
                    if isinstance(row, dict):
                        warning_total += int(row.get("count", 0) or 0)

        base["record_type"] = "json"
        base["row_count"] = 1
        base["stale"] = not bool(base["updated_recently"])
        base["runtime"] = {
            "active_alerts": active_alerts,
            "policy_rollback_count": rollback_count,
            "warning_total": warning_total,
        }
        gate = self._runtime_gate(
            active_alerts=active_alerts,
            rollback_count=rollback_count,
            warning_total=warning_total,
            updated_recently=bool(base["updated_recently"]),
        )
        base["runtime_gate"] = gate
        if gate["grade"] == "fail":
            base["status"] = "FAIL"
            base["reason"] = f"runtime_gate_fail: {', '.join(gate.get('reasons', []))}"
            return base
        base["status"] = "PASS"
        base["reason"] = ""
        return base

    def _runtime_gate(self, active_alerts: int, rollback_count: int, warning_total: int, updated_recently: bool) -> dict[str, Any]:
        reasons: list[str] = []
        if int(active_alerts) > 0:
            reasons.append("active_alerts")
        if bool(updated_recently) and int(rollback_count) > 0:
            reasons.append("policy_rollback_recent")
        if reasons:
            return {"grade": "fail", "reasons": reasons}
        if int(warning_total) > 0:
            return {"grade": "warn", "reasons": ["runtime_warnings"]}
        return {"grade": "pass", "reasons": []}

    def _check_jsonl_file(self, path: Path) -> dict[str, Any]:
        base = self._file_meta(path)
        if not base["exists"]:
            base["status"] = "FAIL"
            base["reason"] = "missing_file"
            return base

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            base["status"] = "FAIL"
            base["reason"] = f"jsonl_read_error: {exc}"
            return base

        valid = 0
        invalid = 0
        for line in lines:
            s = str(line).strip()
            if not s:
                continue
            try:
                json.loads(s)
                valid += 1
            except Exception:
                invalid += 1

        base["record_type"] = "jsonl"
        base["row_count"] = int(valid)
        base["invalid_row_count"] = int(invalid)
        base["stale"] = not bool(base["updated_recently"])
        if invalid > 0:
            base["status"] = "FAIL"
            base["reason"] = f"invalid_jsonl_rows={invalid}"
            return base
        base["status"] = "PASS"
        base["reason"] = ""
        return base

    def _check_api_bundle(self) -> dict[str, Any]:
        health_url = f"{self.base_url}/health"
        if not self._is_fastapi_alive(health_url):
            return {
                "status": "SKIP",
                "reason": "api_not_reachable",
                "base_url": self.base_url,
                "health_url": health_url,
            }

        endpoints = [
            "/health",
            "/ops/readiness",
            "/trades/summary",
            "/trades/closed_recent?limit=5",
        ]
        checks: list[dict[str, Any]] = []
        for ep in endpoints:
            url = f"{self.base_url}{ep}"
            row = {"endpoint": ep, "url": url, "status": "PASS", "http_status": 200, "reason": ""}
            try:
                req = urlrequest.Request(url=url, method="GET")
                with urlrequest.urlopen(req, timeout=5.0) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    row["http_status"] = int(resp.status)
                payload = json.loads(raw) if raw.strip() else {}
                if ep == "/ops/readiness":
                    gate = dict(payload.get("release_gate", {}) or {})
                    grade = str(gate.get("grade", "")).lower()
                    row["release_gate"] = gate
                    if grade == "fail":
                        row["status"] = "FAIL"
                        row["reason"] = "ops_readiness_gate_fail"
                if ep.startswith("/trades/summary"):
                    if not isinstance(payload, dict):
                        row["status"] = "FAIL"
                        row["reason"] = "invalid_summary_payload"
            except Exception as exc:
                row["status"] = "FAIL"
                row["reason"] = str(exc)
                row["http_status"] = 0
            checks.append(row)

        failed = [x for x in checks if x.get("status") == "FAIL"]
        return {
            "status": "FAIL" if failed else "PASS",
            "reason": "api_check_failed" if failed else "",
            "base_url": self.base_url,
            "checks": checks,
        }

    def _check_frontend_bundle(self) -> dict[str, Any]:
        url = self.frontend_url
        row = {
            "status": "PASS",
            "reason": "",
            "url": url,
            "http_status": 200,
            "looks_like_html": False,
        }
        try:
            req = urlrequest.Request(url=url, method="GET")
            with urlrequest.urlopen(req, timeout=5.0) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                row["http_status"] = int(resp.status)
            body = str(raw).lower()
            row["looks_like_html"] = ("<html" in body) or ("<!doctype html" in body)
            if int(row["http_status"]) < 200 or int(row["http_status"]) >= 400:
                row["status"] = "FAIL"
                row["reason"] = f"http_status={row['http_status']}"
                return row
            if not row["looks_like_html"]:
                row["status"] = "FAIL"
                row["reason"] = "non_html_response"
                return row
            return row
        except Exception as exc:
            row["status"] = "FAIL"
            row["reason"] = str(exc)
            row["http_status"] = 0
            return row

    def _watch_tick(self, tick: int) -> dict[str, Any]:
        at = datetime.now().isoformat(timespec="seconds")
        api = self._check_api_bundle()
        fe = self._check_frontend_bundle()
        runtime = self._file_meta(PROJECT_ROOT / "data" / "runtime_status.json")
        events = self._file_meta(PROJECT_ROOT / "data" / "observability" / "events.jsonl")
        closed = self._file_meta(PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv")

        reasons = []
        if api.get("status") == "FAIL":
            reasons.append("api_fail")
        if api.get("status") == "SKIP":
            reasons.append("api_unreachable")
        if fe.get("status") == "FAIL":
            reasons.append("frontend_fail")
        if not bool(runtime.get("updated_recently")):
            reasons.append("runtime_stale")
        if not bool(events.get("updated_recently")):
            reasons.append("events_stale")
        if not bool(closed.get("exists")):
            reasons.append("closed_csv_missing")

        status = "FAIL" if reasons else "PASS"
        return {
            "tick": int(tick),
            "at": at,
            "status": status,
            "reason": ",".join(reasons),
            "api_status": api.get("status"),
            "frontend_status": fe.get("status"),
            "runtime_recent": bool(runtime.get("updated_recently")),
            "events_recent": bool(events.get("updated_recently")),
            "closed_exists": bool(closed.get("exists")),
            "api": api,
            "frontend": fe,
            "runtime_status_file": runtime,
            "events_file": events,
            "closed_csv_file": closed,
        }

    def _check_trading_logic_bundle(self) -> dict[str, Any]:
        closed_path = PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv"
        open_path = PROJECT_ROOT / "data" / "trades" / "trade_history.csv"
        learning_script = PROJECT_ROOT / "scripts" / "learning_kpi_report.py"

        out: dict[str, Any] = {
            "status": "PASS",
            "reason": "",
            "entry_wait": {},
            "exit_wait": {},
            "learning": {},
        }
        failed_reasons: list[str] = []

        rows_open, _, open_err = self._load_csv_rows(open_path)
        rows_closed, _, closed_err = self._load_csv_rows(closed_path)
        if open_err:
            failed_reasons.append(f"open_csv_read_error({open_err})")
        if closed_err:
            failed_reasons.append(f"closed_csv_read_error({closed_err})")
        if failed_reasons:
            out["status"] = "FAIL"
            out["reason"] = "; ".join(failed_reasons)
            return out

        closed_only = []
        for r in rows_closed:
            status = str(r.get("status", "")).strip().upper()
            if status == "CLOSED":
                closed_only.append(r)

        entry_stage_missing = 0
        wait_label_missing = 0
        loss_label_missing = 0
        recent_activity_count = 0
        recent_cutoff = datetime.now() - timedelta(minutes=self.since_min)
        for r in closed_only:
            entry_stage = str(r.get("entry_stage", "")).strip()
            wait_label = str(r.get("wait_quality_label", "")).strip().upper()
            loss_label = str(r.get("loss_quality_label", "")).strip().upper()
            if not entry_stage:
                entry_stage_missing += 1
            if wait_label in UNKNOWN_REASON_SET:
                wait_label_missing += 1
            if loss_label in UNKNOWN_REASON_SET:
                loss_label_missing += 1
            dt = self._parse_row_dt(r)
            if dt is not None and dt >= recent_cutoff:
                recent_activity_count += 1

        closed_count = len(closed_only)
        wait_missing_ratio = float(wait_label_missing / closed_count) if closed_count else 1.0
        loss_missing_ratio = float(loss_label_missing / closed_count) if closed_count else 1.0
        stage_missing_ratio = float(entry_stage_missing / closed_count) if closed_count else 1.0

        out["entry_wait"] = {
            "closed_count": int(closed_count),
            "recent_activity_count": int(recent_activity_count),
            "entry_stage_missing_count": int(entry_stage_missing),
            "wait_quality_unknown_count": int(wait_label_missing),
            "loss_quality_unknown_count": int(loss_label_missing),
            "entry_stage_missing_ratio": round(stage_missing_ratio, 4),
            "wait_quality_unknown_ratio": round(wait_missing_ratio, 4),
            "loss_quality_unknown_ratio": round(loss_missing_ratio, 4),
        }

        if closed_count < self.min_closed_rows:
            failed_reasons.append(f"trading_closed_count_low({closed_count}<{self.min_closed_rows})")
        if wait_missing_ratio > self.max_unknown_ratio:
            failed_reasons.append(
                f"wait_quality_unknown_ratio_high({wait_missing_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            )
        if loss_missing_ratio > self.max_unknown_ratio:
            failed_reasons.append(
                f"loss_quality_unknown_ratio_high({loss_missing_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            )

        close_stage_missing = 0
        close_reason_missing = 0
        temporal_anomaly_count = 0
        for r in closed_only:
            exit_stage = str(r.get("exit_policy_stage", "")).strip()
            exit_reason = str(r.get("exit_reason", "")).strip().upper()
            if not exit_stage:
                close_stage_missing += 1
            if exit_reason in UNKNOWN_REASON_SET:
                close_reason_missing += 1
            try:
                open_ts = int(float(str(r.get("open_ts", "0") or "0")))
                close_ts = int(float(str(r.get("close_ts", "0") or "0")))
                if open_ts > 0 and close_ts > 0 and close_ts < open_ts:
                    temporal_anomaly_count += 1
            except Exception:
                pass

        exit_stage_missing_ratio = float(close_stage_missing / closed_count) if closed_count else 1.0
        exit_reason_missing_ratio = float(close_reason_missing / closed_count) if closed_count else 1.0
        temporal_anomaly_ratio = float(temporal_anomaly_count / closed_count) if closed_count else 1.0
        out["exit_wait"] = {
            "closed_count": int(closed_count),
            "exit_stage_missing_count": int(close_stage_missing),
            "exit_reason_unknown_count": int(close_reason_missing),
            "temporal_anomaly_count": int(temporal_anomaly_count),
            "exit_stage_missing_ratio": round(exit_stage_missing_ratio, 4),
            "exit_reason_unknown_ratio": round(exit_reason_missing_ratio, 4),
            "temporal_anomaly_ratio": round(temporal_anomaly_ratio, 4),
        }

        if exit_stage_missing_ratio > self.max_unknown_ratio:
            failed_reasons.append(
                f"exit_stage_missing_ratio_high({exit_stage_missing_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            )
        if exit_reason_missing_ratio > self.max_unknown_ratio:
            failed_reasons.append(
                f"exit_reason_unknown_ratio_high({exit_reason_missing_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            )
        if temporal_anomaly_count > 0:
            failed_reasons.append(f"temporal_anomaly_detected(count={temporal_anomaly_count})")

        model_files = {
            "metrics_json": PROJECT_ROOT / "models" / "metrics.json",
            "deploy_state_json": PROJECT_ROOT / "models" / "deploy_state.json",
            "ai_models_joblib": PROJECT_ROOT / "models" / "ai_models.joblib",
        }
        learning_files: dict[str, Any] = {}
        missing_learning_files = []
        for key, path in model_files.items():
            meta = self._file_meta(path)
            learning_files[key] = meta
            if not meta.get("exists"):
                missing_learning_files.append(key)
        out["learning"]["model_artifacts"] = learning_files
        if missing_learning_files:
            failed_reasons.append("missing_learning_artifacts(" + ",".join(missing_learning_files) + ")")

        if learning_script.exists():
            probe_cmd = [sys.executable, str(learning_script), "--n", "200", "--json"]
            probe = self._run_cmd("learning_kpi_probe", probe_cmd)
            probe_payload = {}
            if probe.ok:
                try:
                    probe_payload = json.loads(probe.stdout) if probe.stdout.strip() else {}
                except Exception as exc:
                    failed_reasons.append(f"learning_kpi_json_parse_error({exc})")
            else:
                failed_reasons.append(f"learning_kpi_probe_failed(exit={probe.returncode})")
            out["learning"]["kpi_probe"] = {
                "name": "learning_kpi_probe",
                "status": "PASS" if probe.ok else "FAIL",
                "returncode": probe.returncode,
                "payload": probe_payload,
                "stderr": probe.stderr,
            }
        else:
            out["learning"]["kpi_probe"] = {
                "name": "learning_kpi_probe",
                "status": "SKIP",
                "reason": "script_missing",
            }

        out["learning"]["open_row_count"] = int(len(rows_open))
        out["learning"]["closed_row_count"] = int(len(rows_closed))
        if failed_reasons:
            out["status"] = "FAIL"
            out["reason"] = "; ".join(failed_reasons)
        return out

    @staticmethod
    def _load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str], str]:
        decode_error = ""
        for enc in ("utf-8-sig", "cp949"):
            try:
                with path.open("r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    header = list(reader.fieldnames or [])
                return rows, header, ""
            except UnicodeError as exc:
                decode_error = str(exc)
                continue
            except Exception as exc:
                return [], [], str(exc)
        return [], [], f"csv_decode_failed: {decode_error}"

    def _analyze_closed_quality(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        closed_rows = []
        for r in rows:
            status = str(r.get("status", "")).strip().upper()
            if status == "CLOSED":
                closed_rows.append(r)

        closed_count = int(len(closed_rows))
        if closed_count < self.min_closed_rows:
            return {
                "status": "FAIL",
                "reason": f"closed_row_count_below_min({closed_count}<{self.min_closed_rows})",
                "closed_count": closed_count,
            }

        unknown_entry = 0
        unknown_exit = 0
        recent_closed_count = 0
        now = datetime.now()
        recent_cutoff = now - timedelta(minutes=self.since_min)

        for r in closed_rows:
            er = str(r.get("entry_reason", "")).strip().upper()
            xr = str(r.get("exit_reason", "")).strip().upper()
            if er in UNKNOWN_REASON_SET:
                unknown_entry += 1
            if xr in UNKNOWN_REASON_SET:
                unknown_exit += 1

            dt = self._parse_row_dt(r)
            if dt is not None and dt >= recent_cutoff:
                recent_closed_count += 1

        entry_ratio = float(unknown_entry / closed_count) if closed_count else 0.0
        exit_ratio = float(unknown_exit / closed_count) if closed_count else 0.0
        quality = {
            "status": "PASS",
            "reason": "",
            "closed_count": closed_count,
            "recent_closed_count": int(recent_closed_count),
            "unknown_entry_count": int(unknown_entry),
            "unknown_exit_count": int(unknown_exit),
            "unknown_entry_ratio": round(entry_ratio, 4),
            "unknown_exit_ratio": round(exit_ratio, 4),
            "max_unknown_ratio": self.max_unknown_ratio,
        }
        if entry_ratio > self.max_unknown_ratio:
            quality["status"] = "FAIL"
            quality["reason"] = f"unknown_entry_ratio_high({entry_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            return quality
        if exit_ratio > self.max_unknown_ratio:
            quality["status"] = "FAIL"
            quality["reason"] = f"unknown_exit_ratio_high({exit_ratio:.4f}>{self.max_unknown_ratio:.4f})"
            return quality
        return quality

    @staticmethod
    def _parse_row_dt(row: dict[str, str]) -> datetime | None:
        close_ts_raw = str(row.get("close_ts", "")).strip()
        if close_ts_raw:
            try:
                ts = int(float(close_ts_raw))
                if ts > 0:
                    return datetime.fromtimestamp(ts)
            except Exception:
                pass
        close_time = str(row.get("close_time", "")).strip()
        if close_time:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(close_time[:19], fmt)
                except Exception:
                    continue
        return None

    def _file_meta(self, path: Path) -> dict[str, Any]:
        out: dict[str, Any] = {
            "path": str(path.resolve()),
            "exists": path.exists(),
            "mtime": None,
            "mtime_iso": None,
            "age_minutes": None,
            "updated_recently": False,
        }
        if not path.exists():
            return out

        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age_minutes = (datetime.now() - mtime).total_seconds() / 60.0
        out["mtime"] = mtime.timestamp()
        out["mtime_iso"] = mtime.isoformat(timespec="seconds")
        out["age_minutes"] = round(float(age_minutes), 3)
        out["updated_recently"] = mtime >= self.stale_cutoff
        return out

    def _run_cmd(self, name: str, cmd: list[str]) -> CommandResult:
        self._print_info(f"exec: {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return CommandResult(
            name=name,
            command=cmd,
            returncode=int(proc.returncode),
            stdout=str(proc.stdout or ""),
            stderr=str(proc.stderr or ""),
        )

    def _is_fastapi_alive(self, health_url: str) -> bool:
        try:
            req = urlrequest.Request(url=health_url, method="GET")
            with urlrequest.urlopen(req, timeout=2.0) as resp:
                return int(resp.status) == 200
        except (urlerror.URLError, TimeoutError, ValueError):
            return False
        except Exception:
            return False

    @staticmethod
    def _command_to_dict(result: CommandResult) -> dict[str, Any]:
        return {
            "name": result.name,
            "status": "PASS" if result.ok else "FAIL",
            "returncode": result.returncode,
            "command": result.command,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def _record_failure(self, reason: str) -> None:
        reasons: list[str] = self.summary.setdefault("failure_reasons", [])
        if reason not in reasons:
            reasons.append(reason)

    def _finalize_and_exit(self) -> int:
        overall = "PASS"
        for step in self.summary.get("steps", []):
            if step.get("status") == "FAIL":
                overall = "FAIL"
                break
        if self.summary.get("failure_reasons"):
            overall = "FAIL"
        self.summary["overall_status"] = overall
        self.summary["finished_at"] = datetime.now().isoformat(timespec="seconds")

        self._write_summary_files()
        self._print_info(f"summary.json: {self.run_root / 'summary.json'}")
        self._print_info(f"summary.md: {self.run_root / 'summary.md'}")
        return 0 if overall == "PASS" else 1

    def _write_summary_files(self) -> None:
        summary_json = self.run_root / "summary.json"
        summary_md = self.run_root / "summary.md"
        summary_json.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(self._build_markdown_summary(), encoding="utf-8")

    def _build_markdown_summary(self) -> str:
        lines: list[str] = []
        lines.append(f"# Lab Summary ({self.run_stamp})")
        lines.append("")
        lines.append(f"- overall: **{self.summary.get('overall_status', 'FAIL')}**")
        lines.append(f"- started_at: {self.summary.get('started_at', '')}")
        lines.append(f"- finished_at: {self.summary.get('finished_at', '')}")
        lines.append(f"- since_min: {self.since_min}")
        lines.append(f"- base_url: {self.base_url}")
        lines.append(f"- max_unknown_ratio: {self.max_unknown_ratio}")
        lines.append(f"- min_closed_rows: {self.min_closed_rows}")
        lines.append(f"- strict_trading_check: {self.strict_trading_check}")
        lines.append(f"- frontend_url: {self.frontend_url}")
        lines.append("")

        lines.append("## Steps")
        for s in self.summary.get("steps", []):
            lines.append(f"- {s.get('name')}: {s.get('status')} ({s.get('detail', '')})")
        lines.append("")

        smoke = self.summary.get("smoke", {})
        if smoke:
            lines.append("## Smoke")
            lines.append(f"- status: {smoke.get('status', '')}")
            for chk in smoke.get("checks", []):
                lines.append(
                    f"- {chk.get('name', '')}: {chk.get('status', '')} "
                    f"(exit={chk.get('returncode', '-')})"
                )
            lines.append("")

        logcheck = self.summary.get("logcheck", {})
        if logcheck:
            lines.append("## Logcheck")
            lines.append(f"- status: {logcheck.get('status', '')}")
            files = logcheck.get("files", {})
            if isinstance(files, dict):
                for key, row in files.items():
                    lines.append(
                        f"- {key}: {row.get('status', '')}, mtime={row.get('mtime_iso', 'N/A')}, "
                        f"row_count={row.get('row_count', 'N/A')}, updated_recently={row.get('updated_recently', False)}"
                    )
            lines.append("")

        failures = self.summary.get("failure_reasons", [])
        watch = self.summary.get("watch", {})
        if watch:
            lines.append("## Watch")
            lines.append(f"- status: {watch.get('status', '')}")
            ticks = watch.get("ticks", [])
            lines.append(f"- tick_count: {len(ticks) if isinstance(ticks, list) else 0}")
            if isinstance(ticks, list) and ticks:
                last = ticks[-1]
                lines.append(
                    f"- last_tick: #{last.get('tick')} status={last.get('status')} "
                    f"api={last.get('api_status')} frontend={last.get('frontend_status')} reason={last.get('reason')}"
                )
            lines.append("")

        lines.append("## Failures")
        if failures:
            for f in failures:
                lines.append(f"- {f}")
        else:
            lines.append("- none")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _print_header(name: str) -> None:
        print(f"\n[LAB] ===== {name} =====")

    @staticmethod
    def _print_info(msg: str) -> None:
        print(f"[LAB][INFO] {msg}")

    @staticmethod
    def _print_ok(msg: str) -> None:
        print(f"[LAB][PASS] {msg}")

    @staticmethod
    def _print_fail(msg: str) -> None:
        print(f"[LAB][FAIL] {msg}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project lab orchestrator")
    parser.add_argument("command", choices=["run", "smoke", "logcheck", "watch"], help="execution command")
    parser.add_argument("--since-min", type=int, default=DEFAULT_SINCE_MIN, help="stale cutoff minutes")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="base URL used for optional predeploy ops check",
    )
    parser.add_argument(
        "--frontend-url",
        default=DEFAULT_FRONTEND_URL,
        help="frontend base URL used for frontend health checks",
    )
    parser.add_argument(
        "--max-unknown-ratio",
        type=float,
        default=DEFAULT_MAX_UNKNOWN_RATIO,
        help="fail if unknown entry/exit ratio exceeds this threshold",
    )
    parser.add_argument(
        "--min-closed-rows",
        type=int,
        default=DEFAULT_MIN_CLOSED_ROWS,
        help="minimum CLOSED rows required in trade_closed_history.csv",
    )
    parser.add_argument(
        "--strict-trading-check",
        action="store_true",
        help="enable stricter trading logic and learning readiness checks",
    )
    parser.add_argument(
        "--watch-interval-sec",
        type=float,
        default=10.0,
        help="watch interval seconds",
    )
    parser.add_argument(
        "--watch-iterations",
        type=int,
        default=0,
        help="watch iterations (0 means infinite)",
    )
    parser.add_argument(
        "--watch-fail-fast",
        action="store_true",
        help="stop watch immediately on first failed tick",
    )
    parser.add_argument("--run-dir", default=DEFAULT_RUN_DIR, help="result directory root")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = LabRunner(
        since_min=args.since_min,
        base_url=args.base_url,
        run_dir=args.run_dir,
        max_unknown_ratio=args.max_unknown_ratio,
        min_closed_rows=args.min_closed_rows,
        strict_trading_check=args.strict_trading_check,
        frontend_url=args.frontend_url,
    )
    if args.command == "run":
        return runner.run()
    if args.command == "smoke":
        return runner.smoke_only()
    if args.command == "watch":
        return runner.watch(
            interval_sec=args.watch_interval_sec,
            iterations=args.watch_iterations,
            fail_fast=args.watch_fail_fast,
        )
    return runner.logcheck_only()


if __name__ == "__main__":
    raise SystemExit(main())
