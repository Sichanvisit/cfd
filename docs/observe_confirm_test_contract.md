# Observe / Confirm Test Contract

`observe_confirm_test_contract_v1` freezes the minimum router test cases for `ObserveConfirmSnapshot v2`.

## Required Scenarios

- deterministic replay: the same semantic input must produce the same `ObserveConfirmSnapshot v2`
- semantic bundle only route: router must work from canonical semantic inputs without raw detector payloads
- state/archetype separation: `state` stays lifecycle-only and `archetype_id` stays entry identity
- forecast identity guard: forecast may demote confirm into wait or reduce readiness, but may not rename the archetype
- barrier confirm suppression: barrier may demote directional confirm into directional observe while preserving archetype identity
- canonical handoff ids: `invalidation_id` and `management_profile_id` must attach deterministically from `archetype_id`

## Principles

- tests freeze semantic routing, not setup naming or execution guards
- tests compare canonical `observe_confirm_v2` semantics
- tests may not depend on raw detector scores or legacy pattern-shaped state strings
