"""
Runtime inference wrapper for entry/exit models.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import joblib
import pandas as pd


@dataclass
class InferenceDecision:
    probability: float
    decision: bool
    threshold: float


class AIModelRuntime:
    def __init__(self, model_path: str | Path):
        bundle = joblib.load(model_path)
        self.entry_model = bundle["entry_model"]
        self.exit_model = bundle["exit_model"]
        self.entry_feature_cols = bundle["entry_feature_cols"]
        self.exit_feature_cols = bundle["exit_feature_cols"]

    def _to_frame(self, feature_dict: Dict[str, Any], feature_cols) -> pd.DataFrame:
        row = {}
        for col in feature_cols:
            row[col] = feature_dict.get(col)
        return pd.DataFrame([row], columns=feature_cols)

    def predict_entry(self, feature_dict: Dict[str, Any], threshold: float = 0.58) -> InferenceDecision:
        x = self._to_frame(feature_dict, self.entry_feature_cols)
        prob = float(self.entry_model.predict_proba(x)[0, 1])
        return InferenceDecision(probability=prob, decision=(prob >= threshold), threshold=threshold)

    def predict_exit(self, feature_dict: Dict[str, Any], threshold: float = 0.55) -> InferenceDecision:
        x = self._to_frame(feature_dict, self.exit_feature_cols)
        prob = float(self.exit_model.predict_proba(x)[0, 1])
        return InferenceDecision(probability=prob, decision=(prob >= threshold), threshold=threshold)

