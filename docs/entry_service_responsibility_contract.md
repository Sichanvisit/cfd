# EntryService Responsibility Freeze

`entry_service_responsibility_v1` freezes `EntryService` as an execution-guard-only consumer.

Entry block reasons are frozen separately in `entry_guard_contract_v1`.

## Role

- read canonical observe-confirm handoff and setup naming outputs
- apply execution guards such as cooldown, opposite lock, spread or liquidity, cluster guard, and order plumbing
- preserve canonical handoff ids while deciding whether execution is allowed

## Not Its Job

- rewrite `archetype_id`
- rewrite `setup_id`
- flip a confirmed buy into a sell, or a confirmed sell into a buy
- recompute invalidation or management profile ids
- reinterpret semantic or forecast layers
