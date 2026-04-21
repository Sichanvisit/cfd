import pandas as pd

from backend.services.shadow_auto_runtime_mode import build_shadow_auto_runtime_mode_contract


def test_build_shadow_auto_runtime_mode_contract_has_two_modes():
    contract, summary = build_shadow_auto_runtime_mode_contract()

    assert isinstance(contract, pd.DataFrame)
    assert summary["runtime_mode_count"] == 2
    assert set(contract["mode"].tolist()) == {"baseline", "shadow_auto"}
    assert bool(contract.loc[contract["mode"] == "baseline", "live_execution_authority"].iloc[0]) is True
    assert bool(contract.loc[contract["mode"] == "shadow_auto", "live_trade_mutation_allowed"].iloc[0]) is False
