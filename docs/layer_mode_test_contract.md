# Layer Mode Test Contract

`layer_mode_test_contract_v1` freezes the regression axes that must stay stable while Layer Mode moves from `shadow` to `assist` to `enforce`.

## Required Axes

- same semantic input plus same mode configuration must produce the same projected output
- `shadow` must not change action or identity
- `assist` may change confidence or priority, but not `archetype_id` or `side`
- `enforce` may project a block or suppression, but identity must stay intact
- `Forecast.enforce` may split `CONFIRM -> WAIT`, but may not rewrite archetype identity
- `Barrier.enforce` may suppress `CONFIRM` into `OBSERVE`
- raw and effective payloads must remain dual-written together

## Official Helper

`build_layer_mode_test_projection(...)` is the canonical pure helper for these regression checks.
