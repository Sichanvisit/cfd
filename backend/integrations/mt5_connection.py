"""
MT5 connection helpers.
"""

import threading

import MetaTrader5 as mt5

from backend.core.config import Config

_MT5_SESSION_LOCK = threading.RLock()
_MT5_SESSION_USERS = 0


def connect_to_mt5() -> bool:
    """
    Connect/login to MT5 with a bounded timeout.
    Returns True when an active session is available.
    """
    global _MT5_SESSION_USERS
    with _MT5_SESSION_LOCK:
        try:
            if mt5.account_info() is not None:
                _MT5_SESSION_USERS += 1
                return True
        except Exception:
            pass

        timeout_ms = int(getattr(Config, "MT5_CONNECT_TIMEOUT_MS", 4000) or 4000)

        try:
            initialized = mt5.initialize(path=Config.TERMINAL_PATH, timeout=timeout_ms)
        except TypeError:
            initialized = mt5.initialize(path=Config.TERMINAL_PATH)
        if not initialized:
            print("[ERROR] MT5 initialization failed")
            print(f"   path: {Config.TERMINAL_PATH}")
            print(f"   error: {mt5.last_error()}")
            return False

        try:
            authorized = mt5.login(
                login=Config.MT5_LOGIN,
                password=Config.MT5_PASSWORD,
                server=Config.MT5_SERVER,
                timeout=timeout_ms,
            )
        except TypeError:
            authorized = mt5.login(
                login=Config.MT5_LOGIN,
                password=Config.MT5_PASSWORD,
                server=Config.MT5_SERVER,
            )

        if authorized:
            _MT5_SESSION_USERS += 1
            return True

        print(f"[ERROR] MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False


def disconnect_mt5() -> None:
    """Shutdown MT5 session."""
    global _MT5_SESSION_USERS
    with _MT5_SESSION_LOCK:
        if _MT5_SESSION_USERS > 0:
            _MT5_SESSION_USERS -= 1
        if _MT5_SESSION_USERS == 0:
            try:
                mt5.shutdown()
            except Exception:
                pass
