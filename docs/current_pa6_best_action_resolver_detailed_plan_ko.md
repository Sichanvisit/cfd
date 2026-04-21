# Current PA6 Best Action Resolver Detailed Plan

## Purpose

This document fixes the PA6 implementation scope at the level of an actual runtime contract.

The goal of PA6 is not to immediately change live execution behavior.
The goal is to resolve a stable `management_action_label` on top of the existing checkpoint row,
store it in the checkpoint runtime stream, and expose a review artifact that can be compared against PA5 hindsight labels.

In short:

> PA5 made the checkpoint dataset and hindsight eval readable.
> PA6 makes the current best management action readable on the same checkpoint row.

---

## What PA6 Does

PA6 resolves one management action per checkpoint row.

The v1 action taxonomy is:

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

The resolver compares action candidates instead of hard-mapping a single score to a single action.

---

## What PA6 Does Not Do

PA6 does not:

- replace existing entry taxonomy
- directly change live execution authority
- remove PA5 hindsight labels
- merge entry action and management action into one contract

This stage is still log-only / analysis-first.

---

## Runtime Contract

Each checkpoint row can now carry:

- `management_action_label`
- `management_action_confidence`
- `management_action_reason`
- `management_action_score_gap`

These fields are written together with the existing checkpoint context and passive score layer.

They also propagate to the symbol runtime payload as prefixed checkpoint-management fields.

---

## Resolver Evidence

The resolver uses the checkpoint row as its evidence frame:

- structure proxy
  - continuation vs reversal
- management quality
  - hold quality
  - partial exit EV
  - full exit risk
  - rebuy readiness
- position state
  - flat vs active position
  - size fraction
  - runner secured
  - current profit state
- checkpoint type
  - reclaim / pullback vs late trend vs runner check

---

## Resolver Rules

The resolver compares candidate actions and then applies a small number of practical overrides.

Examples:

- strong reversal + strong full-exit risk -> `FULL_EXIT`
- runner secured or open profit + strong partial-and-hold mix -> `PARTIAL_THEN_HOLD`
- strong continuation + good hold quality -> `HOLD`
- reclaim/pullback + room to rebuild -> `REBUY`
- weak environment / flat environment -> `WAIT`

The point is not to predict the market from scratch.
The point is to choose the best management action for the current checkpoint.

---

## Files

### New service

- `backend/services/path_checkpoint_action_resolver.py`

### New builder

- `scripts/build_checkpoint_management_action_snapshot.py`

### New tests

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_build_checkpoint_management_action_snapshot.py`

---

## Integration

PA6 is attached inside `record_checkpoint_context(...)`.

The order is now:

1. build checkpoint context
2. compute passive checkpoint scores
3. resolve management action
4. append runtime checkpoint row
5. update latest symbol runtime payload

This keeps PA3/PA4/PA5 continuity intact.

---

## Output Artifact

PA6 adds:

- `data/analysis/shadow_auto/checkpoint_management_action_snapshot_latest.json`

The snapshot reports:

- per-symbol resolved action counts
- average management-action confidence
- latest checkpoint reference
- recommended review focus

---

## Completion Criteria

PA6 is complete when:

- checkpoint rows can be resolved into a stable management action
- the runtime checkpoint storage keeps those fields without breaking earlier PA stages
- the management-action snapshot artifact is produced
- targeted PA6 tests pass
- PA5 dataset/eval can reuse the same resolver output without duplicating logic

---

## Why This Stage Matters

PA5 answered:

> "What would hindsight say was best?"

PA6 answers:

> "What does the runtime management resolver currently prefer on this checkpoint?"

Once both exist on the same contract, the next stages can compare runtime management behavior against hindsight labels and decide where harvest/manual-exception/adoption should happen.
