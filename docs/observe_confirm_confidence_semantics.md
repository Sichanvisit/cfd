# Observe / Confirm / Action Confidence Semantics

`observe_confirm_confidence_semantics_v2` freezes the meaning of `confidence` as an execution readiness score.

## Meaning

- `confidence` is a bounded readiness score in `[0, 1]`
- `confidence` is not a calibrated probability of future success
- `confidence` is not a substitute for `archetype_id`

## Identity Separation

- `archetype_id` and `side` define identity
- `confidence` does not rename the archetype
- `Barrier` and `Forecast` may lower readiness and keep the same archetype in `WAIT`
- `WAIT` does not imply the archetype disappeared

## Action Relationship

- higher readiness may support `BUY` or `SELL`
- lower readiness may keep the same archetype in `WAIT`
- `NONE` is reserved for no-trade output, not low-confidence identity retention
