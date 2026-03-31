# Exit Handoff Contract

`exit_handoff_contract_v1` freezes canonical exit inputs from entry consumer handoff.

## Official Input

- `management_profile_id`
- `invalidation_id`

## Legacy Fallback

- `entry_setup_id`
- `exit_profile`

## Canonical Management Profiles

- `reversal_profile`
- `breakout_hold_profile`
- `support_hold_profile`
- `breakdown_hold_profile`
- `mid_reclaim_fast_exit_profile`
- `mid_lose_fast_exit_profile`

## Rule

- exit reads canonical handoff first
- setup-based routing is fallback only
- `invalidation_id` passes through as canonical failure identity
