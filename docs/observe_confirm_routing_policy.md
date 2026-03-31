# Observe / Confirm / Action Routing Policy

`observe_confirm_routing_policy_v2` freezes how each semantic layer may influence the router.

## Layer Roles

- `PositionSnapshot + ResponseVector v2 -> archetype candidate generation`
- `StateVector v2 -> regime filter`
- `EvidenceVector -> setup strength`
- `BeliefState -> persistence bias`
- `BarrierState -> action suppression`
- `Forecast -> confidence modulation and confirm/wait split only`

## Identity Guard

- `archetype_id` and `side` are identity fields
- only `PositionSnapshot` and `ResponseVector v2` may create archetype identity
- `State`, `Evidence`, `Belief`, `Barrier`, and `Forecast` may not rename the archetype
- `Forecast` may not flip side without a new position/response candidate

## Confirm / Wait Split

- `Evidence`, `Belief`, `Barrier`, and `Forecast` may influence `confidence`
- `confidence` means execution readiness, not probability
- confirm vs wait is decided from candidate support, opposition, and suppression thresholds derived from the semantic bundle
- `Barrier` may suppress directional action into `WAIT`
- `Forecast` may keep a candidate in `WAIT` when confirm strength is not ready
- `Forecast` may not override the archetype chosen by `Position/Response`
- `buy_force`, `sell_force`, `net_force`, and `energy_snapshot_v1` are not valid routing branch bases

## Implementation Note

Current router implementation builds confirm readiness from `Position/Response/State` plus the semantic bundle (`Evidence`, `Belief`, `Barrier`, `Forecast`) through an internal semantic readiness bridge. `energy_snapshot_v1` is no longer a routing input, and `Energy` is not treated as a canonical identity source under this policy.
