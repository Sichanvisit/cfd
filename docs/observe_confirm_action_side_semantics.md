# Observe / Confirm / Action Action-Side Semantics

`observe_confirm_action_side_semantics_v2` freezes how `action` and `side` work together.

## Allowed Values

- `action`: `WAIT`, `BUY`, `SELL`, `NONE`
- `side`: `BUY`, `SELL`, `""`

## Pairing Rules

- `BUY` -> `side` must be `BUY`
- `SELL` -> `side` must be `SELL`
- `WAIT` -> `side` may be `BUY`, `SELL`, or `""`
- `NONE` -> `side` must be `""`

## Directional Observe

- `WAIT + BUY`
- `WAIT + SELL`

These are explicitly allowed. They mean the router is watching a directional archetype without granting execution confirmation yet.
