from pathlib import Path

import pandas as pd

from backend.core.config import Config
from backend.services.policy_service import PolicyService


class _DummyTradeLogger:
    def read_closed_df(self):
        return pd.DataFrame()

    def recommend_thresholds(self, entry_threshold, exit_threshold):
        return entry_threshold, exit_threshold, ""

    def recommend_exit_policy(self):
        return {"score_multiplier": {"Reversal": 1.0}, "profit_multiplier": {}, "stats": {}}, ""

    def recommend_adverse_policy(self, adverse_loss_usd, reverse_signal_threshold):
        return adverse_loss_usd, reverse_signal_threshold, ""


def test_policy_service_blocks_refresh_on_low_samples():
    svc = PolicyService(_DummyTradeLogger(), Config)
    notes = svc.maybe_refresh(loop_count=121)
    assert notes
    assert notes[0].startswith("policy guard: hard_guard_low_total_samples(")


def test_entry_exit_services_do_not_call_runtime_private_methods():
    root = Path(__file__).resolve().parents[2]
    entry_src = (root / "backend" / "services" / "entry_service.py").read_text(encoding="utf-8")
    exit_src = (root / "backend" / "services" / "exit_service.py").read_text(encoding="utf-8")
    forbidden_tokens = [
        "self.app._append_ai_entry_trace(",
        "self.app._build_scored_reasons(",
        "self.app._allow_ai_exit(",
        "self.app._exit_reversal_ai_adjustment(",
        "self.app._build_exit_detail(",
    ]
    joined = entry_src + "\n" + exit_src
    assert "self.app." not in joined
    for token in forbidden_tokens:
        assert token not in joined


def test_trading_application_uses_broker_terminal_info_not_mt5_direct():
    root = Path(__file__).resolve().parents[2]
    src = (root / "backend" / "app" / "trading_application.py").read_text(encoding="utf-8")
    assert "self.broker.terminal_info()" in src
    assert "mt5.terminal_info()" not in src
