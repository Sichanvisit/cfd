"""Roll over trade CSV files to the current schema while preserving backups."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df, read_csv_resilient


MANIFEST_DIR = ROOT / "data" / "manifests" / "rollover"


def _resolve(path_like: str | Path) -> Path:
    path = Path(path_like)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _roll_one(path: Path, ts: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_before = 0
    backup_path = ""
    existed = path.exists()

    if existed:
        df_before, _ = read_csv_resilient(path, expected_columns=list(TRADE_COLUMNS))
        rows_before = int(len(df_before))
        backup = path.with_name(f"{path.stem}.legacy_{ts}{path.suffix}")
        shutil.move(str(path), str(backup))
        backup_path = str(backup)

    df_after = normalize_trade_df(pd.DataFrame(columns=list(TRADE_COLUMNS)) if not existed else df_before)
    df_after.to_csv(path, index=False, encoding="utf-8-sig")
    return {
        "path": str(path),
        "backup_path": str(backup_path),
        "rows_before": int(rows_before),
        "rows_after": int(len(df_after)),
        "columns_after": list(df_after.columns),
    }


def main() -> int:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    open_path = _resolve(getattr(Config, "TRADE_HISTORY_CSV_PATH", r"data\trades\trade_history.csv"))
    closed_path = open_path.with_name("trade_closed_history.csv")
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": ts,
        "open": _roll_one(open_path, ts),
        "closed": _roll_one(closed_path, ts),
    }
    out_path = MANIFEST_DIR / f"trade_history_rollover_{ts}.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
