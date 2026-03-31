"""Read-only port for closed-trade history access."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class ClosedTradeReadPort(Protocol):
    def read_closed_df(self) -> pd.DataFrame:
        ...
