# Layer Mode Influence Semantics Freeze

`layer_mode_influence_semantics_v1` freezes how each mode may affect execution.

## Global Meaning

- `shadow`: metadata and trace only
- `assist`: soft influence only
- `enforce`: hard execution influence is allowed, but only when the layer matrix permits it

## Layer-Specific Matrix

- `Position.enforce`: structural contradiction gate, execution veto
- `Response.enforce`: trigger-validity gate, action downgrade
- `State.assist`: regime hint, confidence modulation, soft warning
- `State.enforce`: regime gate, action downgrade
- `Evidence.enforce`: setup-strength gate
- `Belief.assist`: persistence bias, confidence modulation
- `Belief.enforce`: downgrade or confirm-to-observe suppression
- `Barrier.enforce`: suppression, hard block, execution veto
- `Forecast.assist`: confidence modulation, priority boost, reason annotation
- `Forecast.enforce`: action downgrade, confirm-to-observe suppression

## Important Constraint

Layer-specific effects differ.
`Barrier.enforce` is suppression-centered.
`Forecast.assist` is readiness-centered.
`Forecast.enforce` does not get `execution_veto`.

## Trace

`layer_mode_influence_trace_v1` records the currently active influence types under the current default mode policy, so replay can show which layers were only logging, which were assisting, and which were allowed to block or suppress.
