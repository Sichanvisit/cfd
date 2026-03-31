"""Setup-aware exit profile and recovery policy routing."""

from __future__ import annotations

from backend.services.exit_lifecycle_profile_policy import apply_exit_lifecycle_profile_v1
from backend.services.exit_profile_identity_policy import resolve_exit_profile_identity_v1
from backend.services.exit_recovery_base_policy import resolve_exit_recovery_base_policy_v1
from backend.services.exit_recovery_temperament_policy import (
    apply_exit_recovery_temperament_v1,
    resolve_exit_recovery_temperament_bundle_v1,
)


def resolve_exit_profile(
    *,
    management_profile_id: str = "",
    invalidation_id: str = "",
    entry_setup_id: str = "",
    fallback_profile: str = "neutral",
) -> str:
    identity = resolve_exit_profile_identity_v1(
        management_profile_id=management_profile_id,
        invalidation_id=invalidation_id,
        entry_setup_id=entry_setup_id,
        fallback_profile=fallback_profile,
    )
    return str(identity.get("profile_id", "neutral") or "neutral")


def apply_range_lifecycle_profile(*, base_profile: str, regime_name: str, current_box_state: str = "") -> str:
    lifecycle = apply_exit_lifecycle_profile_v1(
        base_profile=base_profile,
        regime_name=regime_name,
        current_box_state=current_box_state,
    )
    return str(lifecycle.get("profile_id", "neutral") or "neutral")


def resolve_recovery_policy(
    *,
    symbol: str = "",
    management_profile_id: str = "",
    invalidation_id: str = "",
    entry_setup_id: str = "",
    state_vector_v2: dict | None = None,
    state_metadata: dict | None = None,
    belief_state_v1: dict | None = None,
    entry_direction: str = "",
    default_be_max_loss_usd: float,
    default_tp1_max_loss_usd: float,
    default_max_wait_seconds: int,
    default_reverse_score_gap: int,
) -> dict:
    policy = resolve_exit_recovery_base_policy_v1(
        symbol=symbol,
        management_profile_id=management_profile_id,
        invalidation_id=invalidation_id,
        entry_setup_id=entry_setup_id,
        default_be_max_loss_usd=default_be_max_loss_usd,
        default_tp1_max_loss_usd=default_tp1_max_loss_usd,
        default_max_wait_seconds=default_max_wait_seconds,
        default_reverse_score_gap=default_reverse_score_gap,
    )
    temperament_bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol=symbol,
        entry_setup_id=entry_setup_id,
        entry_direction=entry_direction,
        state_vector_v2=state_vector_v2,
        state_metadata=state_metadata,
        belief_state_v1=belief_state_v1,
    )
    return apply_exit_recovery_temperament_v1(
        base_policy=policy,
        temperament_bundle=temperament_bundle,
        default_be_max_loss_usd=default_be_max_loss_usd,
        default_tp1_max_loss_usd=default_tp1_max_loss_usd,
        default_max_wait_seconds=default_max_wait_seconds,
        default_reverse_score_gap=default_reverse_score_gap,
    )
