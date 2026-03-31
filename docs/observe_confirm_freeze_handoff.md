# Observe / Confirm Freeze / Handoff

`observe_confirm_freeze_handoff_v1` closes the Observe / Confirm / Action contract and defines the consumer handoff boundary.

## Acceptance Criteria

- router may not read raw detector scores directly
- `ObserveConfirmSnapshot v2` is the canonical contract, test, and log payload
- `archetype_id`, `invalidation_id`, and `management_profile_id` are canonical handoff ids
- consumers read `observe_confirm_v2` first and use `observe_confirm_v1` only as migration fallback

## Consumer Rule

- `SetupDetector` and `EntryService` resolve observe/confirm through the shared handoff helper
- consumers may read only observe/confirm payload fields
- consumers may not reinterpret semantic layer vectors or depend on legacy pattern-shaped state ids
