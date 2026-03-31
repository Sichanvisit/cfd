# SetupDetector Responsibility Freeze

`setup_detector_responsibility_v1` freezes `SetupDetector` as a naming-only consumer.

## Role

- read canonical `archetype_id`, `side`, `reason`, and `market_mode`
- map them into `setup_id`
- follow `setup_mapping_contract_v1` for canonical archetype-to-setup rules
- preserve upstream handoff identity

## Not Its Job

- re-decide confirm vs wait
- choose action direction
- score trigger strength
- gate entries
- reinterpret semantic or forecast layers
