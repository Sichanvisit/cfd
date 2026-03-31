"""Predictor interfaces for shadow scoring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.domain.decision_models import DecisionContext, ExitProfile, SetupCandidate, WaitState


class EntryPredictor(ABC):
    @abstractmethod
    def predict(
        self,
        *,
        context: DecisionContext,
        setup: SetupCandidate,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class WaitPredictor(ABC):
    @abstractmethod
    def predict_entry_wait(
        self,
        *,
        context: DecisionContext,
        setup: SetupCandidate | None,
        wait_state: WaitState,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def predict_exit_wait(
        self,
        *,
        context: DecisionContext,
        wait_state: WaitState,
        exit_profile: ExitProfile | None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class ExitPredictor(ABC):
    @abstractmethod
    def predict(
        self,
        *,
        context: DecisionContext,
        wait_state: WaitState,
        exit_profile: ExitProfile,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
