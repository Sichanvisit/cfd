from __future__ import annotations

from importlib import import_module

__all__ = [
    "EntryService",
    "ExitService",
    "PolicyService",
    "StrategyService",
]


def __getattr__(name: str):
    if name == "EntryService":
        return import_module("backend.services.entry_service").EntryService
    if name == "ExitService":
        return import_module("backend.services.exit_service").ExitService
    if name == "PolicyService":
        return import_module("backend.services.policy_service").PolicyService
    if name == "StrategyService":
        return import_module("backend.services.strategy_service").StrategyService
    raise AttributeError(name)
