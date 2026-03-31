import sys
import types
import shutil
from pathlib import Path
from uuid import uuid4

import _pytest.pathlib as pytest_pathlib
import _pytest.tmpdir as pytest_tmpdir
import pytest


_orig_cleanup_dead_symlinks = pytest_pathlib.cleanup_dead_symlinks


def _safe_cleanup_dead_symlinks(root):
    """Ignore Windows ACL errors during pytest temp cleanup."""
    try:
        _orig_cleanup_dead_symlinks(root)
    except PermissionError:
        return


pytest_pathlib.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks
pytest_tmpdir.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks


@pytest.fixture
def tmp_path():
    """
    Custom tmp path fixture to bypass Windows ACL issues from pytest's default
    tmp_path_factory scanning logic in this environment.
    """
    base = Path(".tmp_manual")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


try:
    import MetaTrader5 as _mt5  # noqa: F401
except Exception:
    mt5_stub = types.SimpleNamespace(
        # Deal entry types
        DEAL_ENTRY_OUT=1,
        DEAL_ENTRY_OUT_BY=2,
        DEAL_TYPE_BUY=0,
        DEAL_TYPE_SELL=1,
        # Order types
        ORDER_TYPE_BUY=0,
        ORDER_TYPE_SELL=1,
        ORDER_TIME_GTC=0,
        ORDER_FILLING_IOC=1,
        # Trade actions
        TRADE_ACTION_DEAL=1,
        TRADE_RETCODE_DONE=10009,
        # Timeframes
        TIMEFRAME_M1=1,
        TIMEFRAME_M5=5,
        TIMEFRAME_M15=15,
        TIMEFRAME_M30=30,
        TIMEFRAME_H1=16385,
        TIMEFRAME_H4=16388,
        TIMEFRAME_D1=16408,
        TIMEFRAME_W1=32769,
        # Functions
        history_deals_get=lambda *args, **kwargs: [],
        positions_get=lambda *args, **kwargs: [],
        symbol_info=lambda *args, **kwargs: None,
        symbol_info_tick=lambda *args, **kwargs: None,
        copy_rates_from_pos=lambda *args, **kwargs: None,
        account_info=lambda *args, **kwargs: None,
        order_send=lambda *args, **kwargs: types.SimpleNamespace(retcode=10009, order=0, comment="test"),
        initialize=lambda *args, **kwargs: True,
        login=lambda *args, **kwargs: True,
        shutdown=lambda *args, **kwargs: None,
        last_error=lambda *args, **kwargs: (0, "No error"),
    )
    sys.modules['MetaTrader5'] = mt5_stub
