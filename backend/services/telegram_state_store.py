from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


TELEGRAM_STATE_STORE_CONTRACT_VERSION = "telegram_state_store_v0"
CHECK_GROUP_STATUSES = ("pending", "approved", "rejected", "held", "expired", "applied", "cancelled")
CHECK_ACTION_TYPES = ("approve", "reject", "hold", "apply", "refresh", "reopen", "expire", "cancel")
MESSAGE_KINDS = (
    "check_prompt",
    "check_audit",
    "review_report",
    "report_entry",
    "report_exit",
    "pnl_summary",
)


def default_telegram_state_store_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "runtime" / "telegram_hub.db"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _normalize_status(value: object, default: str = "pending") -> str:
    status = _to_text(value, default).lower()
    return status if status in CHECK_GROUP_STATUSES else str(default)


def _normalize_action(value: object, default: str = "hold") -> str:
    action = _to_text(value, default).lower()
    return action if action in CHECK_ACTION_TYPES else str(default)


def _normalize_message_kind(value: object, default: str = "check_prompt") -> str:
    kind = _to_text(value, default).lower()
    return kind if kind in MESSAGE_KINDS else str(default)


def _payload_json(payload: Mapping[str, Any] | None) -> str:
    return json.dumps(dict(payload or {}), ensure_ascii=False, sort_keys=True)


class TelegramStateStore:
    def __init__(self, *, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else default_telegram_state_store_path()
        self._lock = threading.Lock()
        self._ensure_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def upsert_check_group(
        self,
        *,
        group_key: str,
        status: str = "pending",
        priority: str = "normal",
        symbol: str = "",
        side: str = "",
        strategy_key: str = "",
        check_kind: str = "",
        action_target: str = "",
        reason_fingerprint: str = "",
        reason_summary: str = "",
        review_type: str = "",
        approval_id: str = "",
        scope_key: str = "",
        trace_id: str = "",
        scope_note: str = "",
        decision_deadline_ts: str = "",
        apply_job_key: str = "",
        supersedes_approval_id: str = "",
        first_event_ts: str = "",
        last_event_ts: str = "",
        pending_count: int | None = None,
        approved_by: str = "",
        approved_at: str = "",
        rejected_by: str = "",
        rejected_at: str = "",
        held_by: str = "",
        held_at: str = "",
        expires_at: str = "",
    ) -> dict[str, Any]:
        group_key_text = _to_text(group_key)
        if not group_key_text:
            raise ValueError("group_key_required")
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT * FROM check_groups WHERE group_key = ?", (group_key_text,)).fetchone()
            now = _now_iso()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO check_groups (
                        group_key, status, priority, symbol, side, strategy_key, check_kind,
                        action_target, reason_fingerprint, reason_summary, review_type, approval_id, scope_key,
                        trace_id, scope_note, decision_deadline_ts, apply_job_key, supersedes_approval_id,
                        first_event_ts, last_event_ts, pending_count,
                        last_prompt_message_id, last_prompt_chat_id, last_prompt_topic_id,
                        approved_by, approved_at, rejected_by, rejected_at, held_by, held_at, expires_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group_key_text,
                        _normalize_status(status),
                        _to_text(priority, "normal"),
                        _to_text(symbol).upper(),
                        _to_text(side).upper(),
                        _to_text(strategy_key),
                        _to_text(check_kind),
                        _to_text(action_target),
                        _to_text(reason_fingerprint),
                        _to_text(reason_summary),
                        _to_text(review_type),
                        _to_text(approval_id),
                        _to_text(scope_key),
                        _to_text(trace_id),
                        _to_text(scope_note),
                        _to_text(decision_deadline_ts),
                        _to_text(apply_job_key),
                        _to_text(supersedes_approval_id),
                        _to_text(first_event_ts, now),
                        _to_text(last_event_ts, first_event_ts or now),
                        max(0, _to_int(pending_count, 0)),
                        _to_text(approved_by),
                        _to_text(approved_at),
                        _to_text(rejected_by),
                        _to_text(rejected_at),
                        _to_text(held_by),
                        _to_text(held_at),
                        _to_text(expires_at),
                        now,
                        now,
                    ),
                )
            else:
                current = self._row_to_dict(existing)
                conn.execute(
                    """
                    UPDATE check_groups
                    SET status = ?, priority = ?, symbol = ?, side = ?, strategy_key = ?, check_kind = ?,
                        action_target = ?, reason_fingerprint = ?, reason_summary = ?, review_type = ?, approval_id = ?,
                        scope_key = ?, trace_id = ?, scope_note = ?, decision_deadline_ts = ?,
                        apply_job_key = ?, supersedes_approval_id = ?, first_event_ts = ?, last_event_ts = ?,
                        pending_count = ?, approved_by = ?, approved_at = ?, rejected_by = ?, rejected_at = ?,
                        held_by = ?, held_at = ?, expires_at = ?, updated_at = ?
                    WHERE group_key = ?
                    """,
                    (
                        _normalize_status(status, current.get("status", "pending")),
                        _to_text(priority, current.get("priority", "normal")),
                        _to_text(symbol, current.get("symbol", "")).upper(),
                        _to_text(side, current.get("side", "")).upper(),
                        _to_text(strategy_key, current.get("strategy_key", "")),
                        _to_text(check_kind, current.get("check_kind", "")),
                        _to_text(action_target, current.get("action_target", "")),
                        _to_text(reason_fingerprint, current.get("reason_fingerprint", "")),
                        _to_text(reason_summary, current.get("reason_summary", "")),
                        _to_text(review_type, current.get("review_type", "")),
                        _to_text(approval_id, current.get("approval_id", "")),
                        _to_text(scope_key, current.get("scope_key", "")),
                        _to_text(trace_id, current.get("trace_id", "")),
                        _to_text(scope_note, current.get("scope_note", "")),
                        _to_text(decision_deadline_ts, current.get("decision_deadline_ts", "")),
                        _to_text(apply_job_key, current.get("apply_job_key", "")),
                        _to_text(supersedes_approval_id, current.get("supersedes_approval_id", "")),
                        _to_text(first_event_ts, current.get("first_event_ts", "")),
                        _to_text(last_event_ts, current.get("last_event_ts", "")),
                        max(0, _to_int(pending_count, current.get("pending_count", 0))),
                        _to_text(approved_by, current.get("approved_by", "")),
                        _to_text(approved_at, current.get("approved_at", "")),
                        _to_text(rejected_by, current.get("rejected_by", "")),
                        _to_text(rejected_at, current.get("rejected_at", "")),
                        _to_text(held_by, current.get("held_by", "")),
                        _to_text(held_at, current.get("held_at", "")),
                        _to_text(expires_at, current.get("expires_at", "")),
                        now,
                        group_key_text,
                    ),
                )
            row = conn.execute("SELECT * FROM check_groups WHERE group_key = ?", (group_key_text,)).fetchone()
            return self._row_to_dict(row)

    def get_check_group(self, *, group_id: int | None = None, group_key: str | None = None) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            if group_id is not None:
                row = conn.execute("SELECT * FROM check_groups WHERE group_id = ?", (int(group_id),)).fetchone()
            elif group_key is not None:
                row = conn.execute("SELECT * FROM check_groups WHERE group_key = ?", (_to_text(group_key),)).fetchone()
            else:
                row = None
            return self._row_to_dict(row)

    def list_check_groups(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM check_groups WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (_normalize_status(status), max(1, int(limit))),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM check_groups ORDER BY updated_at DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def append_check_event(
        self,
        *,
        group_id: int,
        source_type: str,
        source_ref: str = "",
        symbol: str = "",
        side: str = "",
        payload: Mapping[str, Any] | None = None,
        event_ts: str = "",
        trace_id: str = "",
        increment_pending: bool = True,
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            now = _now_iso()
            cursor = conn.execute(
                """
                INSERT INTO check_events (
                    group_id, source_type, source_ref, symbol, side, payload_json, event_ts, trace_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(group_id),
                    _to_text(source_type),
                    _to_text(source_ref),
                    _to_text(symbol).upper(),
                    _to_text(side).upper(),
                    _payload_json(payload),
                    _to_text(event_ts, now),
                    _to_text(trace_id),
                    now,
                ),
            )
            if increment_pending:
                conn.execute(
                    """
                    UPDATE check_groups
                    SET pending_count = pending_count + 1, last_event_ts = ?, updated_at = ?
                    WHERE group_id = ?
                    """,
                    (_to_text(event_ts, now), now, int(group_id)),
                )
            row = conn.execute("SELECT * FROM check_events WHERE event_id = ?", (int(cursor.lastrowid),)).fetchone()
            return self._row_to_dict(row)

    def list_check_events(self, *, group_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM check_events WHERE group_id = ? ORDER BY event_id DESC LIMIT ?",
                (int(group_id), max(1, int(limit))),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def append_check_action(
        self,
        *,
        group_id: int,
        telegram_user_id: str | int,
        action: str,
        telegram_username: str = "",
        note: str = "",
        callback_query_id: str = "",
        approval_id: str = "",
        trace_id: str = "",
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            now = _now_iso()
            cursor = conn.execute(
                """
                INSERT INTO check_actions (
                    group_id, telegram_user_id, telegram_username, action, note,
                    callback_query_id, approval_id, trace_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(group_id),
                    _to_text(telegram_user_id),
                    _to_text(telegram_username),
                    _normalize_action(action),
                    _to_text(note),
                    _to_text(callback_query_id),
                    _to_text(approval_id),
                    _to_text(trace_id),
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM check_actions WHERE action_id = ?", (int(cursor.lastrowid),)).fetchone()
            return self._row_to_dict(row)

    def get_check_action_by_callback_query_id(self, *, callback_query_id: str) -> dict[str, Any]:
        callback_id = _to_text(callback_query_id)
        if not callback_id:
            return {}
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM check_actions WHERE callback_query_id = ? ORDER BY action_id DESC LIMIT 1",
                (callback_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def list_check_actions(self, *, group_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM check_actions WHERE group_id = ? ORDER BY action_id ASC LIMIT ?",
                (int(group_id), max(1, int(limit))),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def list_recent_check_actions(
        self,
        *,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            if action:
                rows = conn.execute(
                    "SELECT * FROM check_actions WHERE action = ? ORDER BY action_id DESC LIMIT ?",
                    (_normalize_action(action), max(1, int(limit))),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM check_actions ORDER BY action_id DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def update_check_group(
        self,
        *,
        group_id: int,
        status: str | None = None,
        approval_id: str | None = None,
        pending_count: int | None = None,
        approved_by: str | None = None,
        approved_at: str | None = None,
        rejected_by: str | None = None,
        rejected_at: str | None = None,
        held_by: str | None = None,
        held_at: str | None = None,
        expires_at: str | None = None,
        last_event_ts: str | None = None,
        last_prompt_message_id: str | None = None,
        last_prompt_chat_id: str | None = None,
        last_prompt_topic_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT * FROM check_groups WHERE group_id = ?", (int(group_id),)).fetchone()
            current = self._row_to_dict(existing)
            if not current:
                return {}
            now = _now_iso()
            conn.execute(
                """
                UPDATE check_groups
                SET status = ?, approval_id = ?, pending_count = ?, approved_by = ?, approved_at = ?,
                    rejected_by = ?, rejected_at = ?, held_by = ?, held_at = ?, expires_at = ?,
                    last_event_ts = ?, last_prompt_message_id = ?, last_prompt_chat_id = ?,
                    last_prompt_topic_id = ?, updated_at = ?
                WHERE group_id = ?
                """,
                (
                    _normalize_status(status, current.get("status", "pending")),
                    _to_text(approval_id, current.get("approval_id", "")),
                    max(0, _to_int(pending_count, current.get("pending_count", 0))),
                    _to_text(approved_by, current.get("approved_by", "")),
                    _to_text(approved_at, current.get("approved_at", "")),
                    _to_text(rejected_by, current.get("rejected_by", "")),
                    _to_text(rejected_at, current.get("rejected_at", "")),
                    _to_text(held_by, current.get("held_by", "")),
                    _to_text(held_at, current.get("held_at", "")),
                    _to_text(expires_at, current.get("expires_at", "")),
                    _to_text(last_event_ts, current.get("last_event_ts", "")),
                    _to_text(last_prompt_message_id, current.get("last_prompt_message_id", "")),
                    _to_text(last_prompt_chat_id, current.get("last_prompt_chat_id", "")),
                    _to_text(last_prompt_topic_id, current.get("last_prompt_topic_id", "")),
                    now,
                    int(group_id),
                ),
            )
            row = conn.execute("SELECT * FROM check_groups WHERE group_id = ?", (int(group_id),)).fetchone()
            return self._row_to_dict(row)

    def upsert_telegram_message(
        self,
        *,
        entity_type: str,
        entity_id: str,
        route_key: str,
        chat_id: str | int,
        topic_id: str | int | None,
        telegram_message_id: str | int,
        message_kind: str,
        content_hash: str = "",
        is_editable: bool = True,
    ) -> dict[str, Any]:
        entity_type_text = _to_text(entity_type)
        entity_id_text = _to_text(entity_id)
        route_key_text = _to_text(route_key)
        kind = _normalize_message_kind(message_kind)
        if not entity_type_text or not entity_id_text or not route_key_text:
            raise ValueError("entity_and_route_required")
        with self._lock, self._connect() as conn:
            now = _now_iso()
            existing = conn.execute(
                """
                SELECT * FROM telegram_messages
                WHERE entity_type = ? AND entity_id = ? AND route_key = ? AND message_kind = ?
                """,
                (entity_type_text, entity_id_text, route_key_text, kind),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO telegram_messages (
                        entity_type, entity_id, route_key, chat_id, topic_id, telegram_message_id,
                        message_kind, content_hash, is_editable, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_type_text,
                        entity_id_text,
                        route_key_text,
                        _to_text(chat_id),
                        _to_text(topic_id),
                        _to_text(telegram_message_id),
                        kind,
                        _to_text(content_hash),
                        1 if _to_bool(is_editable, True) else 0,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE telegram_messages
                    SET chat_id = ?, topic_id = ?, telegram_message_id = ?, content_hash = ?,
                        is_editable = ?, updated_at = ?
                    WHERE entity_type = ? AND entity_id = ? AND route_key = ? AND message_kind = ?
                    """,
                    (
                        _to_text(chat_id),
                        _to_text(topic_id),
                        _to_text(telegram_message_id),
                        _to_text(content_hash),
                        1 if _to_bool(is_editable, True) else 0,
                        now,
                        entity_type_text,
                        entity_id_text,
                        route_key_text,
                        kind,
                    ),
                )
            row = conn.execute(
                """
                SELECT * FROM telegram_messages
                WHERE entity_type = ? AND entity_id = ? AND route_key = ? AND message_kind = ?
                """,
                (entity_type_text, entity_id_text, route_key_text, kind),
            ).fetchone()
            return self._row_to_dict(row)

    def get_telegram_message(
        self,
        *,
        entity_type: str,
        entity_id: str,
        route_key: str,
        message_kind: str,
    ) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM telegram_messages
                WHERE entity_type = ? AND entity_id = ? AND route_key = ? AND message_kind = ?
                """,
                (_to_text(entity_type), _to_text(entity_id), _to_text(route_key), _normalize_message_kind(message_kind)),
            ).fetchone()
            return self._row_to_dict(row)

    def set_poller_offset(self, *, stream_key: str, last_update_id: int) -> dict[str, Any]:
        stream_key_text = _to_text(stream_key)
        if not stream_key_text:
            raise ValueError("stream_key_required")
        with self._lock, self._connect() as conn:
            now = _now_iso()
            conn.execute(
                """
                INSERT INTO poller_offsets (stream_key, last_update_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(stream_key) DO UPDATE SET
                    last_update_id = excluded.last_update_id,
                    updated_at = excluded.updated_at
                """,
                (stream_key_text, int(last_update_id), now),
            )
            row = conn.execute("SELECT * FROM poller_offsets WHERE stream_key = ?", (stream_key_text,)).fetchone()
            return self._row_to_dict(row)

    def get_poller_offset(self, *, stream_key: str) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM poller_offsets WHERE stream_key = ?", (_to_text(stream_key),)).fetchone()
            return self._row_to_dict(row)

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS check_groups (
                    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    strategy_key TEXT NOT NULL,
                    check_kind TEXT NOT NULL,
                    action_target TEXT NOT NULL,
                    reason_fingerprint TEXT NOT NULL,
                    reason_summary TEXT NOT NULL,
                    review_type TEXT NOT NULL,
                    approval_id TEXT NOT NULL DEFAULT '',
                    scope_key TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    scope_note TEXT NOT NULL,
                    decision_deadline_ts TEXT NOT NULL,
                    apply_job_key TEXT NOT NULL,
                    supersedes_approval_id TEXT NOT NULL,
                    first_event_ts TEXT NOT NULL,
                    last_event_ts TEXT NOT NULL,
                    pending_count INTEGER NOT NULL DEFAULT 0,
                    last_prompt_message_id TEXT NOT NULL DEFAULT '',
                    last_prompt_chat_id TEXT NOT NULL DEFAULT '',
                    last_prompt_topic_id TEXT NOT NULL DEFAULT '',
                    approved_by TEXT NOT NULL DEFAULT '',
                    approved_at TEXT NOT NULL DEFAULT '',
                    rejected_by TEXT NOT NULL DEFAULT '',
                    rejected_at TEXT NOT NULL DEFAULT '',
                    held_by TEXT NOT NULL DEFAULT '',
                    held_at TEXT NOT NULL DEFAULT '',
                    expires_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS check_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    event_ts TEXT NOT NULL,
                    trace_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES check_groups(group_id)
                );

                CREATE TABLE IF NOT EXISTS check_actions (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    telegram_user_id TEXT NOT NULL,
                    telegram_username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    note TEXT NOT NULL,
                    callback_query_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL DEFAULT '',
                    trace_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES check_groups(group_id)
                );

                CREATE TABLE IF NOT EXISTS telegram_messages (
                    message_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    route_key TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    telegram_message_id TEXT NOT NULL,
                    message_kind TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    is_editable INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entity_type, entity_id, route_key, message_kind)
                );

                CREATE TABLE IF NOT EXISTS poller_offsets (
                    stream_key TEXT PRIMARY KEY,
                    last_update_id INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                """
            )
            self._ensure_additive_columns(conn)
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_check_groups_status_updated_at ON check_groups(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_check_groups_scope_key ON check_groups(scope_key);
                CREATE INDEX IF NOT EXISTS idx_check_groups_approval_id ON check_groups(approval_id);
                CREATE INDEX IF NOT EXISTS idx_check_events_group_id ON check_events(group_id);
                CREATE INDEX IF NOT EXISTS idx_check_actions_group_id ON check_actions(group_id);
                CREATE INDEX IF NOT EXISTS idx_check_actions_callback_query_id ON check_actions(callback_query_id);
                CREATE INDEX IF NOT EXISTS idx_messages_entity_route ON telegram_messages(entity_type, entity_id, route_key);
                """
            )
            conn.commit()

    def _ensure_additive_columns(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(check_groups)").fetchall()
        }
        if "approval_id" not in existing_columns:
            conn.execute("ALTER TABLE check_groups ADD COLUMN approval_id TEXT NOT NULL DEFAULT ''")

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            return {}
        payload = {key: row[key] for key in row.keys()}
        if "pending_count" in payload:
            payload["pending_count"] = _to_int(payload.get("pending_count"))
        if "last_update_id" in payload:
            payload["last_update_id"] = _to_int(payload.get("last_update_id"))
        if "is_editable" in payload:
            payload["is_editable"] = bool(payload.get("is_editable"))
        return payload
