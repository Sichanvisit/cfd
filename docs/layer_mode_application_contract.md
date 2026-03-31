# Layer Mode Layer-by-Layer Application Freeze

`layer_mode_application_contract_v1` freezes how each semantic layer is actually applied.

## Layer Policy

- `Position`: structural truth, almost always `enforce`, immediate veto on zone or side contradiction
- `Response`: core trigger candidate, primarily `enforce`
- `State`: starts as a regime filter in `assist`, may later graduate to `enforce`
- `Evidence`: setup-strength based, expected to act in `enforce`
- `Belief`: persistence or continuation bias starts in `assist`, with stronger suppression only later
- `Barrier`: suppression and risk centered, later `enforce`
- `Forecast`: may not rewrite archetype identity; only adjusts confidence, confirm-wait split, and management preference

## Important Constraint

This contract is not the same thing as the influence matrix.
It says how each layer should be applied in practice, including when a layer becomes semantically active and what kind of application role it owns.

## Trace

`layer_mode_application_trace_v1` records whether each layer is currently in:

- `standby`
- `assist_active`
- `enforce_active`

under the current default mode policy.
