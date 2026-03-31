# Consumer Test Contract

`consumer_test_contract_v1` freezes the required regression axes for the Observe / Confirm consumer layer.

## Objective

Consumer behavior must stay locked across naming, execution guards, migration fallback, canonical handoff ids, and blocked-row logging.

## Required Behavior Axes

- `setup_detector_naming_only`
- `entry_service_no_semantic_reinterpretation`
- `consumer_v2_canonical_v1_fallback`
- `handoff_ids_stable_per_archetype`
- `execution_guard_preserves_semantic_identity`
- `blocked_rows_keep_archetype_metadata`

## Primary Behavioral Test Files

- `tests/unit/test_setup_detector.py`
- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_consumer_scope_contract.py`

## Supporting Runtime / Log Test Files

- `tests/unit/test_context_classifier.py`
- `tests/unit/test_entry_engines.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_prs_engine.py`

## Principle

The freeze is not complete unless behavior tests, runtime metadata embedding, row logging, and source-level wiring all pass together.
