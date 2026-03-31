# Layer Mode Identity Guard Freeze

`layer_mode_identity_guard_v1` freezes an always-on identity guard for `Belief`, `Barrier`, and `Forecast`.

## Protected Fields

- `archetype_id`
- `side`

These fields stay owned by the observe-confirm identity path.

## Allowed Adjustments

The guarded layers may still adjust:

- `confidence`
- `action readiness`
- `confirm -> wait`
- `block reason annotation`

## Forbidden Adjustments

The guarded layers may not:

- rewrite `archetype_id`
- rewrite `side`
- rename the setup identity downstream

`Forecast` is even tighter and may not take `execution_veto`.

## Routing Link

This guard follows:

- `observe_confirm_routing_policy_v2`
- `observe_confirm_confidence_semantics_v2`

It exists so later layer-mode rollout cannot silently bypass the identity rules already frozen in observe-confirm routing.
