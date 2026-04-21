from __future__ import annotations

from backend.trading.trade_logger import TradeLogger


class _DummyStore:
    def __init__(self):
        self.calls: list[tuple[int, dict]] = []

    def patch_open_trade_fields(self, ticket: int, fields: dict[str, object] | None) -> bool:
        self.calls.append((int(ticket), dict(fields or {})))
        return True


class _FakeTradeLogger:
    def __init__(self):
        self._store = _DummyStore()
        self._pending_open_policy_context = {}
        self._committed_open_policy_context = {}
        self.success_ops: list[str] = []
        self.failure_ops: list[str] = []

    def _mark_store_success(self, op: str) -> None:
        self.success_ops.append(str(op))

    def _mark_store_failure(self, op: str, exc: Exception) -> None:
        self.failure_ops.append(str(op))

    def _read_open_df_safe(self):
        raise AssertionError("fallback CSV path should not be used in this test")

    def _normalize_dataframe(self, df):
        return df

    def _write_open_df(self, df) -> None:
        raise AssertionError("fallback CSV path should not be used in this test")

    def _sync_open_rows_to_store(self, df) -> None:
        raise AssertionError("fallback CSV path should not be used in this test")


def test_update_exit_policy_context_skips_identical_payload_rewrites():
    fake = _FakeTradeLogger()

    TradeLogger.update_exit_policy_context(
        fake,
        1001,
        {
            "exit_policy_stage": "protective_exit_surface",
            "exit_wait_bridge_status": "runner_preservation_active",
        },
    )
    TradeLogger.update_exit_policy_context(
        fake,
        1001,
        {
            "exit_policy_stage": "protective_exit_surface",
            "exit_wait_bridge_status": "runner_preservation_active",
        },
    )

    assert len(fake._store.calls) == 1
    assert fake._store.calls[0][0] == 1001
    assert fake._store.calls[0][1] == {
        "exit_policy_stage": "protective_exit_surface",
        "exit_wait_bridge_status": "runner_preservation_active",
    }


def test_update_exit_policy_context_only_patches_changed_fields_after_commit():
    fake = _FakeTradeLogger()

    TradeLogger.update_exit_policy_context(
        fake,
        1001,
        {
            "exit_policy_stage": "protective_exit_surface",
            "exit_wait_bridge_status": "runner_preservation_active",
        },
    )
    TradeLogger.update_exit_policy_context(
        fake,
        1001,
        {
            "exit_policy_stage": "continuation_hold_surface",
            "exit_wait_bridge_status": "runner_preservation_active",
        },
    )

    assert len(fake._store.calls) == 2
    assert fake._store.calls[1][1] == {
        "exit_policy_stage": "continuation_hold_surface",
    }
