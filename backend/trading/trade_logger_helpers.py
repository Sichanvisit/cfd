"""Helper utilities extracted from TradeLogger to keep the class lean."""

from __future__ import annotations

import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.services.trade_csv_schema import (
    mt5_ts_to_kst_dt as schema_mt5_ts_to_kst_dt,
    now_kst_dt,
    text_to_kst_epoch as schema_text_to_kst_epoch,
)

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def normalize_entry_stage(value: str) -> str:
    s = str(value or "").strip().lower()
    if s in {"aggressive", "balanced", "conservative"}:
        return s
    return "balanced"


def normalize_exit_reason(reason: str) -> str:
    raw = str(reason or "").strip()
    if not raw:
        return ""
    head = raw.split(",")[0].strip()
    head = re.sub(r"\s*\([+-]?\d+[^)]*\)\s*$", "", head).strip()
    lo = head.lower()
    if "adverse reversal" in lo:
        return "Adverse Reversal"
    if "adverse stop" in lo:
        return "Adverse Stop"
    if "emergency stop" in lo:
        return "Emergency Stop"
    if "rsi scalp" in lo:
        return "RSI Scalp"
    if "bb scalp" in lo:
        return "BB Scalp"
    if "reversal" in lo:
        return "Reversal"
    if "target" in lo:
        return "Target"
    if "manual/unknown" in lo or lo in {"manual", "unknown"}:
        return "Manual/Unknown"
    return head


def estimate_reason_points(reason: str) -> int:
    s = str(reason or "").strip()
    if not s:
        return 0
    matches = re.findall(r"\(([+-]?\d+)[^)]*\)", s)
    if matches:
        try:
            total = sum(int(x) for x in matches)
            return int(abs(total))
        except Exception:
            return 0
    sl = s.lower()
    if "adverse reversal" in sl:
        return 220
    if "reversal" in sl:
        return 150
    if "adverse stop" in sl:
        return 70
    if "target" in sl:
        return 120
    if "rsi scalp" in sl:
        return 60
    if "bb scalp" in sl:
        return 60
    if "manual" in sl:
        return 30
    return 50


def now_kst_text() -> str:
    return now_kst_dt().strftime("%Y-%m-%d %H:%M:%S")


def ts_to_kst_dt(ts: int) -> datetime:
    return schema_mt5_ts_to_kst_dt(ts)


def text_to_kst_epoch(value: str) -> int:
    return schema_text_to_kst_epoch(value)


def lock_file_handle(fp, timeout_sec: float = 8.0) -> None:
    fp.seek(0)
    # Windows msvcrt byte-range lock can fail on empty files.
    # Ensure lock files have at least one byte before attempting lock.
    if os.name == "nt":
        try:
            cur = fp.tell()
            fp.seek(0, os.SEEK_END)
            if fp.tell() <= 0:
                fp.write(b"0")
                fp.flush()
            fp.seek(cur, os.SEEK_SET)
        except Exception:
            try:
                fp.seek(0)
                fp.write(b"0")
                fp.flush()
            except Exception:
                pass
        fp.seek(0)
    try:
        timeout_sec = float(os.getenv("TRADE_CSV_LOCK_TIMEOUT_SEC", str(timeout_sec)) or timeout_sec)
    except Exception:
        timeout_sec = float(timeout_sec)
    deadline = time.time() + float(timeout_sec)
    last_exc = None
    while time.time() < deadline:
        try:
            if os.name == "nt":
                msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.05)
    raise TimeoutError(f"CSV lock acquisition timed out for handle={fp.name}: {last_exc}")


def unlock_file_handle(fp) -> None:
    fp.seek(0)
    if os.name == "nt":
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


def atomic_write_df(target_path: str, df: pd.DataFrame) -> None:
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    try:
        retry_count = int(os.getenv("TRADE_CSV_REPLACE_RETRY_COUNT", "12") or "12")
    except Exception:
        retry_count = 12
    try:
        retry_sleep_ms = int(os.getenv("TRADE_CSV_REPLACE_RETRY_SLEEP_MS", "40") or "40")
    except Exception:
        retry_sleep_ms = 40
    retry_count = max(0, retry_count)
    retry_sleep_sec = max(1, retry_sleep_ms) / 1000.0
    try:
        df.to_csv(temp_path, index=False, encoding="utf-8-sig")
        last_exc = None
        for _ in range(retry_count + 1):
            try:
                os.replace(temp_path, path)
                last_exc = None
                break
            except PermissionError as exc:
                last_exc = exc
                time.sleep(retry_sleep_sec)
        if last_exc is not None:
            # Windows environments can deny os.replace() under transient file-handle contention.
            # Fallback to direct overwrite so logging does not stall.
            with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                df.to_csv(fp, index=False)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise
