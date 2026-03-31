# Observe / Confirm / Action State Semantics

`observe_confirm_state_semantics_v2` freezes `state` as a lifecycle field only.

## Allowed Values

- `OBSERVE`
- `CONFIRM`
- `CONFLICT_OBSERVE`
- `NO_TRADE`
- `INVALIDATED`

## Principles

- `state` describes routing lifecycle only
- pattern identity does not live in `state`
- legacy pattern-shaped router ids move to `archetype_id`
- downstream setup naming consumes `archetype_id`, not lifecycle state text

## Compatibility Bridge

- `shadow_state_v1` remains a compatibility field
- when `archetype_id` is present, compatibility shadow fields mirror `archetype_id`
- `observe_confirm_v1.state` is reserved for lifecycle semantics only
