# Layer Mode Default Policy

`layer_mode_default_policy_v1` freezes the recommended starting mode per semantic layer and its migration target sequence.

## Policy Rows

- `Position`: current `enforce`, target `enforce`
- `Response`: current `enforce`, target `enforce`
- `State`: current `assist`, target `assist -> enforce`
- `Evidence`: current `enforce`, target `enforce`
- `Belief`: current `shadow`, target `shadow -> assist -> enforce`
- `Barrier`: current `shadow`, target `shadow -> assist -> enforce`
- `Forecast`: current `shadow`, target `shadow -> assist -> enforce`

## Principle

`current effective default` and `target sequence` are separate on purpose.
The policy may migrate over time without losing the current rollout baseline.
