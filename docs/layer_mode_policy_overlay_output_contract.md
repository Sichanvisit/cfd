# Layer Mode Policy Overlay Output Contract

`layer_mode_policy_overlay_output_v1` freezes the canonical payload that sits above raw semantic outputs and below execution.

## Canonical Output

- `layer_mode_policy_v1`

## Required Fields

- `layer_modes`
- `effective_influences`
- `suppressed_reasons`
- `confidence_adjustments`
- `hard_blocks`
- `mode_decision_trace`

## Meaning

`layer_mode_policy_v1` is the policy-applied view of the current layer-mode state.
It is emitted separately from raw semantic outputs such as `belief_state_v1` or `transition_forecast_v1`.
It does not replace those raw fields.

## Bridge Behavior

The current bridge is allowed to emit a no-delta overlay result.
That means:

- `suppressed_reasons` may be empty
- `confidence_adjustments` may be empty
- `hard_blocks` may be empty

This is still valid as long as the payload explains the current modes and active influence surface in `effective_influences` and `mode_decision_trace`.

## Identity Guard

`layer_mode_policy_v1` must preserve `archetype_id` and `side`.
Policy overlay may only shape readiness, suppression state, or block annotation in ways already allowed by `layer_mode_identity_guard_v1`.
