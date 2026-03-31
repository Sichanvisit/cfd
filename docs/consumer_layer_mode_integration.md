# Consumer Layer Mode Integration

`consumer_layer_mode_integration_v1` freezes how consumer layers read `layer_mode_policy_v1`.

## Objective

Consumer keeps canonical trade identity in `observe_confirm_v2`.
`layer_mode_policy_v1` is read as the official policy input that sits above that identity.

## Principle

- `observe_confirm_v2` owns `archetype_id` and `side`
- `layer_mode_policy_v1` may shape readiness, suppression, and policy interpretation
- consumer must not go around `layer_mode_policy_v1` by directly re-reading semantic vectors

## Official Helpers

- `resolve_consumer_layer_mode_policy_resolution(...)`
- `resolve_consumer_layer_mode_policy_input(...)`

## Consumer Boundary

- `SetupDetector` keeps naming rooted in canonical observe-confirm identity
- `EntryService` treats `layer_mode_policy_v1` as the official policy overlay input
- `Exit` and `ReEntry` may read overlay context later, but never use it as an identity source
