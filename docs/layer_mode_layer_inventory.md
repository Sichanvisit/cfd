# Layer Mode Layer Inventory

`layer_mode_layer_inventory_v1` freezes the semantic layer targets that may receive Layer Mode policy.

## Canonical Layers

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`
- `Forecast`

## Principle

This inventory says which semantic outputs are mode-addressable.
It does not say how strongly they are applied yet.

`ObserveConfirm` and `Consumer` are downstream consumers of these layers, not members of the mode-owned semantic inventory.
