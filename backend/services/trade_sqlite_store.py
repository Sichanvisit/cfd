"""
SQLite mirror store for trade read/write acceleration.
CSV remains append/log source, SQLite serves query workloads.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df, read_csv_resilient, text_to_kst_epoch


class TradeSqliteStore:
    def __init__(self, db_path: Path, trade_csv: Path, closed_trade_csv: Path):
        self.db_path = Path(db_path)
        self.trade_csv = Path(trade_csv)
        self.closed_trade_csv = Path(closed_trade_csv)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        # Keep API read path responsive under write-lock contention.
        conn = sqlite3.connect(str(self.db_path), timeout=3, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=3000;")
        return conn

    def _ensure_schema(self) -> None:
        cols = ",\n".join([f"{c} TEXT" for c in TRADE_COLUMNS])
        with self._connect() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS open_trades (
                    {cols},
                    ticket_int INTEGER NOT NULL DEFAULT 0,
                    row_ts INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (ticket_int)
                )
                """
            )
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS closed_trades (
                    {cols},
                    ticket_int INTEGER NOT NULL DEFAULT 0,
                    row_ts INTEGER NOT NULL DEFAULT 0,
                    dedup_key TEXT NOT NULL,
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (dedup_key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mirror_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_open_symbol_ts ON open_trades(symbol, row_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_closed_symbol_ts ON closed_trades(symbol, row_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_closed_ticket ON closed_trades(ticket_int)")
            self._ensure_table_columns(conn, "open_trades")
            self._ensure_table_columns(conn, "closed_trades")
            conn.commit()

    @staticmethod
    def _ensure_table_columns(conn: sqlite3.Connection, table_name: str) -> None:
        existing = {str(r["name"]) for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        for col in TRADE_COLUMNS:
            if col in existing:
                continue
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} TEXT")

    @staticmethod
    def _to_text(v):
        if v is None:
            return ""
        if isinstance(v, float) and pd.isna(v):
            return ""
        if pd.isna(v):
            return ""
        return str(v)

    @staticmethod
    def _file_mtime_ns(path: Path) -> int:
        try:
            return int(path.stat().st_mtime_ns)
        except Exception:
            return -1

    @staticmethod
    def _read_csv_resilient(path: Path) -> tuple[pd.DataFrame, bool]:
        return read_csv_resilient(path, expected_columns=TRADE_COLUMNS)

    def _meta_get(self, key: str) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM mirror_meta WHERE key = ?", (str(key),)).fetchone()
            return str(row["value"]) if row else ""

    def _meta_set_many(self, kv: dict[str, str]) -> None:
        rows = [(str(k), str(v)) for k, v in kv.items()]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO mirror_meta(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                rows,
            )
            conn.commit()

    @staticmethod
    def _with_row_ts(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = normalize_trade_df(df.copy())
        out["open_ts"] = pd.to_numeric(out.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
        out["close_ts"] = pd.to_numeric(out.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
        if "open_time" in out.columns:
            parsed_open = out["open_time"].map(text_to_kst_epoch)
            out.loc[out["open_ts"] <= 0, "open_ts"] = pd.to_numeric(parsed_open, errors="coerce").fillna(0).astype(int)
        if "close_time" in out.columns:
            parsed_close = out["close_time"].map(text_to_kst_epoch)
            out.loc[out["close_ts"] <= 0, "close_ts"] = pd.to_numeric(parsed_close, errors="coerce").fillna(0).astype(int)
        out["row_ts"] = out["close_ts"].where(out["close_ts"] > 0, out["open_ts"]).fillna(0).astype(int)
        out["ticket_int"] = pd.to_numeric(out.get("ticket", 0), errors="coerce").fillna(0).astype(int)
        out["symbol_upper"] = out.get("symbol", "").fillna("").astype(str).str.upper().str.strip()
        out["dedup_key"] = out["ticket_int"].astype(str) + "|" + out["symbol_upper"] + "|" + out["close_ts"].astype(str)
        return out

    def sync_from_csv(self, force: bool = False) -> bool:
        open_mtime = self._file_mtime_ns(self.trade_csv)
        closed_mtime = self._file_mtime_ns(self.closed_trade_csv)
        meta_open = int(self._meta_get("open_mtime_ns") or -2)
        meta_closed = int(self._meta_get("closed_mtime_ns") or -2)
        if (not force) and meta_open == open_mtime and meta_closed == closed_mtime:
            return False

        open_df = pd.DataFrame(columns=TRADE_COLUMNS)
        closed_df = pd.DataFrame(columns=TRADE_COLUMNS)
        if self.trade_csv.exists():
            raw, open_ok = self._read_csv_resilient(self.trade_csv)
            if not open_ok:
                return False
            try:
                raw = normalize_trade_df(raw)
                open_df = raw[raw["status"].astype(str).str.upper() == "OPEN"].copy()
                legacy_closed = raw[raw["status"].astype(str).str.upper() == "CLOSED"].copy()
                if not legacy_closed.empty:
                    if closed_df.empty:
                        closed_df = legacy_closed.copy()
                    else:
                        closed_df = pd.concat([closed_df, legacy_closed], ignore_index=True, sort=False)
            except Exception:
                return False
        if self.closed_trade_csv.exists():
            raw_closed, closed_ok = self._read_csv_resilient(self.closed_trade_csv)
            if not closed_ok:
                return False
            try:
                raw_closed = normalize_trade_df(raw_closed)
                if raw_closed is not None and not raw_closed.empty:
                    if closed_df.empty:
                        closed_df = raw_closed.copy()
                    else:
                        closed_df = pd.concat([closed_df, raw_closed], ignore_index=True, sort=False)
            except Exception:
                return False

        self.replace_open_rows(open_df)
        if not closed_df.empty:
            self.replace_closed_rows(closed_df)
        else:
            with self._connect() as conn:
                conn.execute("DELETE FROM closed_trades")
                conn.commit()

        self._meta_set_many(
            {
                "open_mtime_ns": str(open_mtime),
                "closed_mtime_ns": str(closed_mtime),
                "last_sync_epoch": str(int(time.time())),
            }
        )
        return True

    def replace_open_rows(self, rows_df: pd.DataFrame) -> None:
        src = self._with_row_ts(rows_df if rows_df is not None else pd.DataFrame(columns=TRADE_COLUMNS))
        src = src[src["status"].astype(str).str.upper() == "OPEN"].copy() if not src.empty else src
        if not src.empty:
            src = src.sort_values(["ticket_int", "row_ts"]).drop_duplicates(subset=["ticket_int"], keep="last")
        now_ts = int(time.time())
        values = []
        for _, row in src.iterrows():
            trade_vals = [self._to_text(row.get(c, "")) for c in TRADE_COLUMNS]
            values.append(tuple(trade_vals + [int(row.get("ticket_int", 0)), int(row.get("row_ts", 0)), now_ts]))
        with self._connect() as conn:
            conn.execute("DELETE FROM open_trades")
            if values:
                placeholders = ",".join(["?"] * (len(TRADE_COLUMNS) + 3))
                cols = ",".join(TRADE_COLUMNS + ["ticket_int", "row_ts", "updated_at"])
                conn.executemany(f"INSERT INTO open_trades({cols}) VALUES({placeholders})", values)
            conn.commit()

    def upsert_open_rows(self, rows_df: pd.DataFrame) -> None:
        src = self._with_row_ts(rows_df if rows_df is not None else pd.DataFrame(columns=TRADE_COLUMNS))
        if src.empty:
            return
        src = src[src["status"].astype(str).str.upper() == "OPEN"].copy()
        if src.empty:
            return
        src = src.sort_values(["ticket_int", "row_ts"]).drop_duplicates(subset=["ticket_int"], keep="last")
        now_ts = int(time.time())
        cols = TRADE_COLUMNS + ["ticket_int", "row_ts", "updated_at"]
        update_cols = [c for c in cols if c != "ticket_int"]
        placeholders = ",".join(["?"] * len(cols))
        assign_sql = ",".join([f"{c}=excluded.{c}" for c in update_cols])
        sql = f"""
            INSERT INTO open_trades({",".join(cols)}) VALUES({placeholders})
            ON CONFLICT(ticket_int) DO UPDATE SET {assign_sql}
        """
        values = []
        for _, row in src.iterrows():
            trade_vals = [self._to_text(row.get(c, "")) for c in TRADE_COLUMNS]
            values.append(tuple(trade_vals + [int(row.get("ticket_int", 0)), int(row.get("row_ts", 0)), now_ts]))
        with self._connect() as conn:
            conn.executemany(sql, values)
            conn.commit()

    def replace_closed_rows(self, rows_df: pd.DataFrame) -> None:
        src = self._with_row_ts(rows_df if rows_df is not None else pd.DataFrame(columns=TRADE_COLUMNS))
        src = src[src["status"].astype(str).str.upper() == "CLOSED"].copy() if not src.empty else src
        if not src.empty:
            src["profit"] = pd.to_numeric(src.get("profit", 0.0), errors="coerce").fillna(0.0)
            src = src.sort_values(["dedup_key", "row_ts"]).drop_duplicates(subset=["dedup_key"], keep="last")
        now_ts = int(time.time())
        values = []
        for _, row in src.iterrows():
            trade_vals = [self._to_text(row.get(c, "")) for c in TRADE_COLUMNS]
            values.append(
                tuple(
                    trade_vals
                    + [
                        int(row.get("ticket_int", 0)),
                        int(row.get("row_ts", 0)),
                        self._to_text(row.get("dedup_key", "")),
                        now_ts,
                    ]
                )
            )
        with self._connect() as conn:
            conn.execute("DELETE FROM closed_trades")
            if values:
                placeholders = ",".join(["?"] * (len(TRADE_COLUMNS) + 4))
                cols = ",".join(TRADE_COLUMNS + ["ticket_int", "row_ts", "dedup_key", "updated_at"])
                conn.executemany(f"INSERT INTO closed_trades({cols}) VALUES({placeholders})", values)
            conn.commit()
        self.prune_closed_per_symbol(limit_per_symbol=100)

    def upsert_closed_rows(self, rows_df: pd.DataFrame) -> None:
        src = self._with_row_ts(rows_df if rows_df is not None else pd.DataFrame(columns=TRADE_COLUMNS))
        if src.empty:
            return
        src = src[src["status"].astype(str).str.upper() == "CLOSED"].copy()
        if src.empty:
            return
        src["profit"] = pd.to_numeric(src.get("profit", 0.0), errors="coerce").fillna(0.0)
        src = src.sort_values(["dedup_key", "row_ts"]).drop_duplicates(subset=["dedup_key"], keep="last")
        now_ts = int(time.time())
        cols = TRADE_COLUMNS + ["ticket_int", "row_ts", "dedup_key", "updated_at"]
        update_cols = [c for c in cols if c != "dedup_key"]
        placeholders = ",".join(["?"] * len(cols))
        assign_sql = ",".join([f"{c}=excluded.{c}" for c in update_cols])
        sql = f"""
            INSERT INTO closed_trades({",".join(cols)}) VALUES({placeholders})
            ON CONFLICT(dedup_key) DO UPDATE SET {assign_sql}
        """
        values = []
        for _, row in src.iterrows():
            trade_vals = [self._to_text(row.get(c, "")) for c in TRADE_COLUMNS]
            values.append(
                tuple(
                    trade_vals
                    + [
                        int(row.get("ticket_int", 0)),
                        int(row.get("row_ts", 0)),
                        self._to_text(row.get("dedup_key", "")),
                        now_ts,
                    ]
                )
            )
        with self._connect() as conn:
            conn.executemany(sql, values)
            conn.commit()
        self.prune_closed_per_symbol(limit_per_symbol=100)

    def prune_closed_per_symbol(self, limit_per_symbol: int = 100) -> int:
        lim = max(1, int(limit_per_symbol or 100))
        sql = """
            WITH ranked AS (
                SELECT
                    dedup_key,
                    CASE
                        WHEN UPPER(symbol) LIKE '%BTC%' THEN 'BTCUSD'
                        WHEN UPPER(symbol) LIKE '%NAS%' OR UPPER(symbol) LIKE '%US100%' OR UPPER(symbol) LIKE '%USTEC%' THEN 'NAS100'
                        WHEN UPPER(symbol) LIKE '%XAU%' OR UPPER(symbol) LIKE '%GOLD%' THEN 'XAUUSD'
                        ELSE ''
                    END AS canonical_symbol,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            CASE
                                WHEN UPPER(symbol) LIKE '%BTC%' THEN 'BTCUSD'
                                WHEN UPPER(symbol) LIKE '%NAS%' OR UPPER(symbol) LIKE '%US100%' OR UPPER(symbol) LIKE '%USTEC%' THEN 'NAS100'
                                WHEN UPPER(symbol) LIKE '%XAU%' OR UPPER(symbol) LIKE '%GOLD%' THEN 'XAUUSD'
                                ELSE ''
                            END
                        ORDER BY row_ts DESC, ticket_int DESC
                    ) AS rn
                FROM closed_trades
            )
            DELETE FROM closed_trades
            WHERE dedup_key IN (
                SELECT dedup_key
                FROM ranked
                WHERE canonical_symbol IN ('BTCUSD','NAS100','XAUUSD')
                  AND rn > ?
            )
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (lim,))
            conn.commit()
            return int(getattr(cur, "rowcount", 0) or 0)

    def _rows_to_df(self, rows) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=TRADE_COLUMNS)
        data = []
        for r in rows:
            item = {}
            for c in TRADE_COLUMNS:
                item[c] = r[c]
            data.append(item)
        return normalize_trade_df(pd.DataFrame(data))

    def read_open_df(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT {','.join(TRADE_COLUMNS)} FROM open_trades").fetchall()
        return self._rows_to_df(rows)

    def read_closed_df(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT {','.join(TRADE_COLUMNS)} FROM closed_trades").fetchall()
        return self._rows_to_df(rows)

    def query_latest_open(self, symbol: str = "", limit: int = 1) -> pd.DataFrame:
        lim = max(1, min(1000, int(limit)))
        sym = str(symbol or "").upper().strip()
        sql = f"""
            SELECT {','.join(TRADE_COLUMNS)}
            FROM open_trades
            WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
            ORDER BY row_ts DESC, ticket_int DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (sym, sym, lim)).fetchall()
        return self._rows_to_df(rows)

    def get_open_trade_context(self, ticket: int) -> dict[str, object] | None:
        ticket_int = int(ticket or 0)
        if ticket_int <= 0:
            return None
        sql = f"""
            SELECT {','.join(TRADE_COLUMNS)}
            FROM open_trades
            WHERE ticket_int = ?
            LIMIT 1
        """
        with self._connect() as conn:
            row = conn.execute(sql, (ticket_int,)).fetchone()
        if row is None:
            return None
        return {str(column): row[column] for column in TRADE_COLUMNS}

    def query_latest_closed(self, symbol: str = "", limit: int = 1) -> pd.DataFrame:
        lim = max(1, min(1000, int(limit)))
        sym = str(symbol or "").upper().strip()
        sql = f"""
            SELECT {','.join(TRADE_COLUMNS)}
            FROM closed_trades
            WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
            ORDER BY row_ts DESC, ticket_int DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (sym, sym, lim)).fetchall()
        return self._rows_to_df(rows)

    def query_rows(self, status: str = "ALL", symbol: str = "", since_ts: int = 0, limit: int = 1000) -> pd.DataFrame:
        status_norm = str(status or "ALL").upper().strip()
        if status_norm not in {"ALL", "OPEN", "CLOSED"}:
            status_norm = "ALL"
        sym = str(symbol or "").upper().strip()
        since = max(0, int(since_ts or 0))
        lim = max(1, min(5000, int(limit)))

        if status_norm == "OPEN":
            sql = f"""
                SELECT {','.join(TRADE_COLUMNS)}
                FROM open_trades
                WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
                  AND row_ts > ?
                ORDER BY row_ts DESC, ticket_int DESC
                LIMIT ?
            """
            params = (sym, sym, since, lim)
        elif status_norm == "CLOSED":
            sql = f"""
                SELECT {','.join(TRADE_COLUMNS)}
                FROM closed_trades
                WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
                  AND row_ts > ?
                ORDER BY row_ts DESC, ticket_int DESC
                LIMIT ?
            """
            params = (sym, sym, since, lim)
        else:
            sql = f"""
                SELECT {','.join(TRADE_COLUMNS)}
                FROM (
                    SELECT {','.join(TRADE_COLUMNS)}, row_ts, ticket_int
                    FROM open_trades
                    WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
                      AND row_ts > ?
                    UNION ALL
                    SELECT {','.join(TRADE_COLUMNS)}, row_ts, ticket_int
                    FROM closed_trades
                    WHERE (? = '' OR UPPER(symbol) LIKE '%' || ? || '%')
                      AND row_ts > ?
                )
                ORDER BY row_ts DESC, ticket_int DESC
                LIMIT ?
            """
            params = (sym, sym, since, sym, sym, since, lim)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._rows_to_df(rows)

    def get_change_token(self) -> str:
        with self._connect() as conn:
            o = conn.execute(
                "SELECT COUNT(*) AS cnt, COALESCE(MAX(row_ts),0) AS max_ts, COALESCE(MAX(updated_at),0) AS max_u FROM open_trades"
            ).fetchone()
            c = conn.execute(
                "SELECT COUNT(*) AS cnt, COALESCE(MAX(row_ts),0) AS max_ts, COALESCE(MAX(updated_at),0) AS max_u FROM closed_trades"
            ).fetchone()
        return (
            f"o:{int(o['cnt'])}:{int(o['max_ts'])}:{int(o['max_u'])}"
            f"|c:{int(c['cnt'])}:{int(c['max_ts'])}:{int(c['max_u'])}"
        )
