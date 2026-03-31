"""Runtime interaction ports for entry/exit services."""

from __future__ import annotations

from typing import Any, Protocol

from ports.broker_port import BrokerPort


class ExecutionPort(Protocol):
    broker: BrokerPort
    last_order_error: str

    def execute_order(self, symbol: str, action: str, lot: float) -> Any:
        ...

    def close_position(self, ticket: int, reason: str = "Exit") -> bool:
        ...

    def close_position_partial(self, ticket: int, volume: float, reason: str = "Partial Exit") -> bool:
        ...

    def move_stop_to_break_even(self, ticket: int, be_price: float) -> bool:
        ...


class EntryAiPort(Protocol):
    ai_runtime: Any

    def append_ai_entry_trace(self, trace: dict[str, Any]) -> None:
        ...

    def entry_features(
        self,
        symbol: str,
        action: str,
        score: float,
        contra_score: float,
        reasons: list[str],
        regime: dict[str, Any] | None = None,
        indicators: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def score_adjustment(self, probability: float, weight: float) -> int:
        ...


class ExitAiPort(Protocol):
    def allow_ai_exit(
        self,
        symbol: str,
        direction: str,
        open_time: str,
        duration_sec: float,
        entry_score: float,
        contra_score: float,
        exit_score: float,
        entry_reason: str,
        exit_reason: str,
        regime: dict[str, Any] | None = None,
        trade_ctx: dict[str, Any] | None = None,
        stage_inputs: dict[str, Any] | None = None,
        live_metrics: dict[str, Any] | None = None,
    ) -> bool:
        ...

    def exit_reversal_ai_adjustment(
        self,
        symbol: str,
        direction: str,
        open_time: str,
        duration_sec: float,
        entry_score: float,
        contra_score: float,
        exit_score: float,
        entry_reason: str,
        regime: dict[str, Any] | None = None,
        trade_ctx: dict[str, Any] | None = None,
        stage_inputs: dict[str, Any] | None = None,
        live_metrics: dict[str, Any] | None = None,
    ) -> int:
        ...


class ReasonBuilderPort(Protocol):
    def build_scored_reasons(self, reasons: list[str], target_total: int, ai_adj: int = 0) -> list[str]:
        ...

    def build_exit_detail(
        self,
        opposite_reasons: list[str],
        exit_signal_score: float,
        trade_logger: Any,
        ticket: int,
    ) -> tuple[str, int]:
        ...


class EntryRuntimePort(ExecutionPort, EntryAiPort, ReasonBuilderPort, Protocol):
    last_entry_time: dict[str, float]
    latest_signal_by_symbol: dict[str, Any]

    def get_lot_size(self, symbol: str) -> float:
        ...

    def entry_indicator_snapshot(self, symbol: str, scorer: Any, df_all: dict[str, Any]) -> dict[str, Any]:
        ...

    def format_entry_message(
        self,
        symbol: str,
        action: str,
        score: int,
        price: float,
        lot: float,
        reasons: list[str],
        pos_count: int,
        max_pos: int,
    ) -> str:
        ...

    def notify(self, message: str) -> None:
        ...


class ExitRuntimePort(ExecutionPort, ExitAiPort, ReasonBuilderPort, Protocol):
    ...
