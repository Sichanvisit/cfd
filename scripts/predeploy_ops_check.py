"""Pre-deploy gate check using /ops/readiness."""

from __future__ import annotations

import argparse
import json
import time
import sys
import urllib.error
import urllib.request
from typing import Any


def _http_get_json(url: str, timeout_sec: float) -> dict[str, Any]:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return dict(json.loads(raw or "{}"))


def _evaluate(readiness: dict[str, Any], allow_warn: bool) -> tuple[int, str]:
    gate = readiness.get("release_gate", {})
    grade = str(gate.get("grade", "") or "").lower()
    reasons = gate.get("reasons", [])
    reason_text = ", ".join([str(x) for x in reasons]) if isinstance(reasons, list) else str(reasons)

    if grade == "pass":
        return 0, f"PASS: release_gate=pass"
    if grade == "warn":
        if allow_warn:
            return 0, f"PASS_WITH_WARN: release_gate=warn ({reason_text})"
        return 2, f"FAIL: release_gate=warn ({reason_text})"
    return 2, f"FAIL: release_gate={grade or 'unknown'} ({reason_text})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-deploy readiness gate checker")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="FastAPI base URL")
    parser.add_argument("--timeout-sec", type=float, default=8.0, help="HTTP timeout seconds")
    parser.add_argument("--wait-sec", type=float, default=0.0, help="Total wait time for API readiness")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Retry interval during wait")
    parser.add_argument("--allow-warn", action="store_true", help="Allow warn grade to pass")
    parser.add_argument("--print-json", action="store_true", help="Print full readiness JSON")
    args = parser.parse_args()

    url = str(args.base_url).rstrip("/") + "/ops/readiness"
    timeout_sec = float(args.timeout_sec)
    wait_sec = max(0.0, float(args.wait_sec))
    interval_sec = max(0.2, float(args.interval_sec))
    started = time.time()
    last_exc: Exception | None = None
    readiness: dict[str, Any] | None = None

    while True:
        try:
            readiness = _http_get_json(url, timeout_sec=timeout_sec)
            break
        except urllib.error.HTTPError as exc:
            print(f"[PRECHECK][FAIL] HTTP {exc.code} {exc.reason} for {url}")
            return 3
        except Exception as exc:
            last_exc = exc
            if (time.time() - started) >= wait_sec:
                print(f"[PRECHECK][FAIL] request error: {exc}")
                return 3
            print(f"[PRECHECK][WAIT] API not ready yet: {exc} (retry in {interval_sec:.1f}s)")
            time.sleep(interval_sec)

    if readiness is None:
        print(f"[PRECHECK][FAIL] request error: {last_exc or 'unknown'}")
        return 3

    if args.print_json:
        print(json.dumps(readiness, ensure_ascii=False, indent=2))

    code, msg = _evaluate(readiness, allow_warn=bool(args.allow_warn))
    print(f"[PRECHECK] {msg}")

    docs = readiness.get("docs", {})
    runtime = readiness.get("runtime", {})
    if isinstance(docs, dict):
        missing = [k for k, v in docs.items() if not bool(v)]
        if missing:
            print(f"[PRECHECK] missing_docs={', '.join(missing)}")
    if isinstance(runtime, dict):
        print(
            "[PRECHECK] runtime active_alerts={0} rollback_count={1} warning_total={2}".format(
                int(runtime.get("active_alerts", 0) or 0),
                int(runtime.get("policy_rollback_count", 0) or 0),
                int(runtime.get("warning_total", 0) or 0),
            )
        )

    return int(code)


if __name__ == "__main__":
    sys.exit(main())
