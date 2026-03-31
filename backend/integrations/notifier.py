"""
Telegram notification helpers.
"""

import logging
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Thread

import requests

from backend.core.config import Config

logger = logging.getLogger(__name__)
_send_queue = Queue()
_stop_event = Event()
_worker = None


def _send_sync(message):
    if not Config.TG_TOKEN or not Config.TG_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{Config.TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": Config.TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }

    response = requests.post(url, data=payload, timeout=10)
    if response.status_code != 200:
        logger.warning(
            "Telegram send failed: status=%s body=%s",
            response.status_code,
            response.text[:300],
        )


def _worker_loop():
    while not _stop_event.is_set():
        try:
            message = _send_queue.get(timeout=0.5)
        except Empty:
            continue

        try:
            _send_sync(message)
        except requests.RequestException as exc:
            logger.exception("Telegram request failed: %s", exc)
        except Exception as exc:
            logger.exception("Unexpected notifier error: %s", exc)
        finally:
            _send_queue.task_done()


def _ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _stop_event.clear()
        _worker = Thread(target=_worker_loop, daemon=True, name="telegram-notifier")
        _worker.start()


def send_telegram(message):
    if not Config.TG_TOKEN or not Config.TG_CHAT_ID:
        return
    _ensure_worker()
    _send_queue.put(message)


def shutdown(timeout=2.0):
    if _worker is None:
        return
    try:
        _send_queue.join()
    except Exception:
        pass
    _stop_event.set()
    _worker.join(timeout=timeout)


def format_entry_message(symbol, action, score, price, lot, reasons, pos_count, max_pos):
    icon = "BUY" if action == "BUY" else "SELL"
    time_str = datetime.now().strftime("%H:%M:%S")
    reason_text = "\n".join([f"  - {r}" for r in reasons[:5]])

    msg = f"""
{icon} *Signal*
Time: {time_str}
Symbol: `{symbol}`
Price: {price:.5f}
Score: *{score}*
Volume: {lot} lot

*Reasons*
{reason_text}

Position: {pos_count}/{max_pos}
"""
    return msg.strip()


def format_exit_message(symbol, profit, points, entry_price, exit_price):
    icon = "PROFIT" if profit > 0 else "LOSS"
    time_str = datetime.now().strftime("%H:%M:%S")

    msg = f"""
{icon} *Exit*
Time: {time_str}
Symbol: `{symbol}`
PnL: *${profit:.2f}* ({int(points)} ticks)
Price: {entry_price:.5f} -> {exit_price:.5f}
"""
    return msg.strip()
