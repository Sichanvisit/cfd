# Consumer Input Contract

`consumer_input_contract_v1` freezes the official input boundary for Observe / Confirm consumers.

## Official Input

- `DecisionContext.metadata.observe_confirm_v2`
- migration fallback `DecisionContext.metadata.observe_confirm_v1`
- `DecisionContext.metadata.prs_log_contract_v2` for canonical/fallback resolution

## Resolution Rule

- consumer must resolve input through `resolve_consumer_observe_confirm_resolution`
- read order is `observe_confirm_v2 -> observe_confirm_v1`
- direct branching on raw `observe_confirm_v1` / `observe_confirm_v2` fields is not allowed in consumer runtime logic

## Allowed Runtime Support

- preflight execution fields such as allowed action, approach mode, regime, liquidity, and reason
- execution guard state
- position lock state
- symbol and tick price context

## Forbidden Direct Reads

- raw detector scores
- legacy rule branches
- response, state, evidence, belief, barrier, and forecast payloads
- direct semantic vector reinterpretation inside consumer code
