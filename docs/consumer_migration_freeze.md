# Consumer Migration Freeze

`consumer_migration_freeze_v1` freezes observe-confirm migration behavior inside consumer code.

## Objective

Consumers must resolve observe-confirm input through one shared helper and stop mixing direct `v1` and `v2` reads inside runtime logic.

## Fixed Read Order

1. canonical `observe_confirm_v2`
2. compatibility fallback `observe_confirm_v1`

Resolution helper:

- `resolve_consumer_observe_confirm_resolution`
- `resolve_consumer_observe_confirm_input`

## Rules

- consumer runtime logic may not read `observe_confirm_v1` or `observe_confirm_v2` directly
- `SetupDetector`, `EntryService`, and `Exit` must use the shared resolver path
- consumer logging must record which observe-confirm field was actually consumed
- `observe_confirm_v1` remains compatibility-only and can be removed after fallback dependence disappears

## Removal Readiness

- all consumer entry points resolve through the shared helper
- logs show no `observe_confirm_v1` fallback dependence
- no direct consumer runtime reads of legacy observe-confirm fields remain
