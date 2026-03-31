"""
Core domain models.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SignalResult:
    symbol: str
    buy_score: int
    sell_score: int
    buy_reasons: List[str] = field(default_factory=list)
    sell_reasons: List[str] = field(default_factory=list)


@dataclass
class PositionState:
    ticket: int
    symbol: str
    side: str
    volume: float
    profit: float

