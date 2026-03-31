"""
Strategy orchestration service.
"""


class StrategyService:
    def __init__(self, scorer):
        self.scorer = scorer

    def evaluate(self, symbol, tick, df_all):
        return self.scorer.get_score(symbol, tick, df_all)

