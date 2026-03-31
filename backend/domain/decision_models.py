"""
Shared decision DTOs for entry/exit pipeline standardization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def _jsonable_map(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): _jsonable(v) for k, v in value.items()}


@dataclass
class DecisionContext:
    symbol: str
    phase: str
    market_mode: str = "UNKNOWN"
    direction_policy: str = "UNKNOWN"
    box_state: str = "UNKNOWN"
    bb_state: str = "UNKNOWN"
    liquidity_state: str = "UNKNOWN"
    regime_name: str = "UNKNOWN"
    regime_zone: str = "UNKNOWN"
    volatility_state: str = "UNKNOWN"
    raw_scores: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "DecisionContext":
        data = _jsonable_map(data)
        return cls(
            symbol=str(data.get("symbol", "")),
            phase=str(data.get("phase", "")),
            market_mode=str(data.get("market_mode", "UNKNOWN")),
            direction_policy=str(data.get("direction_policy", "UNKNOWN")),
            box_state=str(data.get("box_state", "UNKNOWN")),
            bb_state=str(data.get("bb_state", "UNKNOWN")),
            liquidity_state=str(data.get("liquidity_state", "UNKNOWN")),
            regime_name=str(data.get("regime_name", "UNKNOWN")),
            regime_zone=str(data.get("regime_zone", "UNKNOWN")),
            volatility_state=str(data.get("volatility_state", "UNKNOWN")),
            raw_scores=_jsonable_map(data.get("raw_scores")),
            thresholds=_jsonable_map(data.get("thresholds")),
            metadata=_jsonable_map(data.get("metadata")),
        )


@dataclass
class SetupCandidate:
    setup_id: str = ""
    side: str = ""
    status: str = "pending"
    trigger_state: str = "UNKNOWN"
    entry_quality: float = 0.0
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class WaitState:
    phase: str
    state: str = "NONE"
    hard_wait: bool = False
    score: float = 0.0
    conflict: float = 0.0
    noise: float = 0.0
    penalty: float = 0.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ExitProfile:
    profile_id: str = ""
    policy_stage: str = ""
    selector_stage: str = ""
    confirm_needed: int = 0
    regime_name: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PredictionBundle:
    entry: dict[str, Any] = field(default_factory=dict)
    wait: dict[str, Any] = field(default_factory=dict)
    exit: dict[str, Any] = field(default_factory=dict)
    reverse: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class DecisionResult:
    phase: str
    symbol: str
    action: str = ""
    outcome: str = ""
    blocked_by: str = ""
    reason: str = ""
    decision_rule_version: str = ""
    context: DecisionContext | None = None
    selected_setup: SetupCandidate | None = None
    wait_state: WaitState | None = None
    exit_profile: ExitProfile | None = None
    predictions: PredictionBundle | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        return payload
