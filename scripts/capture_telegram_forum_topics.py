from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.integrations import notifier


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture Telegram forum topic message_thread_id values from live message updates.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=25,
        help="Long-poll timeout per request.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of polling rounds before exit.",
    )
    parser.add_argument(
        "--chat-id",
        type=str,
        default="",
        help="Optional target forum chat_id filter.",
    )
    return parser


def _extract_summary(update: dict[str, Any]) -> dict[str, Any]:
    message = dict(update.get("message") or update.get("edited_message") or {})
    chat = dict(message.get("chat") or {})
    return {
        "update_id": update.get("update_id"),
        "chat_id": chat.get("id"),
        "chat_title": chat.get("title"),
        "chat_type": chat.get("type"),
        "is_forum": chat.get("is_forum"),
        "message_id": message.get("message_id"),
        "message_thread_id": message.get("message_thread_id"),
        "text": message.get("text"),
        "date": message.get("date"),
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    target_chat_id = str(args.chat_id or "").strip()
    print("[capture] waiting for Telegram forum topic messages...")
    print("[capture] send a message like '/start@sichan_trading_bot check-topic' in each topic you want to map.")
    print(
        json.dumps(
            {
                "timeout_sec": int(args.timeout_sec),
                "rounds": int(args.rounds),
                "chat_id_filter": target_chat_id or None,
            },
            ensure_ascii=False,
        )
    )

    seen_update_ids: set[int] = set()
    for round_index in range(1, int(args.rounds) + 1):
        try:
            updates = notifier.get_telegram_updates(
                timeout=max(0, int(args.timeout_sec)),
                allowed_updates=["message", "edited_message"],
            )
        except Exception as exc:
            print(json.dumps({"round": round_index, "error": str(exc)}, ensure_ascii=False))
            time.sleep(1.0)
            continue

        matched = 0
        for update in updates:
            update_id = int(update.get("update_id") or 0)
            if update_id in seen_update_ids:
                continue
            seen_update_ids.add(update_id)
            summary = _extract_summary(dict(update or {}))
            if target_chat_id and str(summary.get("chat_id")) != target_chat_id:
                continue
            matched += 1
            print(json.dumps(summary, ensure_ascii=False))

        if matched == 0:
            print(json.dumps({"round": round_index, "matched": 0}, ensure_ascii=False))

    print("[capture] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
