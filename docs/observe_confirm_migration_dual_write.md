# Observe / Confirm Migration Dual-Write

`observe_confirm_migration_dual_write_v1` freezes the migration period where `observe_confirm_v1` and `observe_confirm_v2` are written together.

## Dual-Write Rule

- `observe_confirm_v2` is the canonical log field
- `observe_confirm_v1` remains the compatibility field for current consumers
- both fields must carry semantically equivalent `ObserveConfirmSnapshot` payloads during migration

## Consumer Rule

- consumers read `observe_confirm_v2` first and use `observe_confirm_v1` only as compatibility fallback
- consumer runtime logic resolves observe-confirm through the shared consumer helper
- logs and PRS canonical fielding must point to `observe_confirm_v2`
- compatibility shadow fields may remain v1-named during migration

## Recorder Rule

- if only `observe_confirm_v1` is present, recorder backfills `observe_confirm_v2`
- if only `observe_confirm_v2` is present, recorder backfills `observe_confirm_v1`
