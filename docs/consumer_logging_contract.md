# Consumer Logging Contract

`consumer_logging_contract_v1` freezes canonical consumer audit fields.

## Objective

Consumer logs must show which `observe_confirm` handoff field was consumed, which canonical ids were passed through, and why the consumer passed or blocked the action.

## Canonical Fields

- `consumer_input_observe_confirm_field`
- `consumer_input_contract_version`
- `consumer_archetype_id`
- `consumer_invalidation_id`
- `consumer_management_profile_id`
- `consumer_setup_id`
- `consumer_guard_result`
- `consumer_effective_action`
- `consumer_block_reason`
- `consumer_block_kind`
- `consumer_block_source_layer`
- `consumer_handoff_contract_version`

Supplemental fields:

- `consumer_block_is_execution`
- `consumer_block_is_semantic_non_action`

## Guard Result Values

- `PASS`
- `SEMANTIC_NON_ACTION`
- `EXECUTION_BLOCK`

## Resolution Rules

- consumed handoff field comes from `resolve_consumer_observe_confirm_resolution`
- input contract version comes from `consumer_input_contract_v1`
- handoff contract version comes from `observe_confirm_output_contract_v2`
- `consumer_setup_id` mirrors `setup_id`

## Principle

`consumer_guard_result` is a compact summary.
`consumer_block_reason`, `consumer_block_kind`, and `consumer_block_source_layer` explain the detailed cause without collapsing semantic non-action and execution block into the same bucket.
