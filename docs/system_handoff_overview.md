# CFD System Handoff Overview

## Purpose
This document is the single handoff guide for another thread or agent to understand:

- what the current architecture is,
- which layers are already implemented,
- what each layer means,
- where `Forecast` ends and `Observe / Confirm / Action` begins,
- what `OutcomeLabeler` does,
- and what the next meaningful work should be.

This is not a speculative roadmap. It is a practical summary of the current system shape and the contracts already introduced in the codebase.

---

## One-Screen Architecture

```text
Market Data
-> Context Normalization
-> Position
-> Response Raw
-> Response Vector
-> State Vector
-> Evidence
-> Belief
-> Barrier
-> Forecast Features
-> Transition Forecast / Trade Management Forecast
-> Observe / Confirm / Action
-> Consumer

Offline in parallel:
Semantic + Forecast snapshots
-> OutcomeLabeler
-> Validation Report / Replay Dataset Builder
-> Rule vs Model comparison
```

The system is now split into two different paths:

1. Live decision path
- semantic layers
- forecast
- `Observe / Confirm / Action`
- consumer

2. Offline evaluation path
- semantic layers
- forecast
- `OutcomeLabeler`
- validation / dataset / future model training

These paths are related, but they are not the same thing.

---

## Current Layer Meaning

### Position
Role:
- says where price is

Important outputs:
- `PositionSnapshot`
- `PositionInterpretation`
- `PositionEnergySnapshot`

Meaning:
- no direction decision
- no entry/exit decision
- only location, alignment, conflict, and location energy

Implementation:
- `backend/trading/engine/position/*`
- `backend/trading/engine/core/models.py`

Status:
- implemented and treated as semantic foundation

### Response
Role:
- says what transition response is happening at that location

Important outputs:
- `ResponseRawSnapshot`
- `ResponseVectorV2`

Canonical response axes:
- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

Meaning:
- pattern names are not the final decision unit
- patterns act as amplifiers on canonical axes

Implementation:
- `backend/trading/engine/response/*`

Status:
- implemented and treated as semantic foundation

### State
Role:
- says how much the current response should be trusted

Important outputs:
- `StateRawSnapshot`
- `StateVectorV2`

Canonical state coefficients:
- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`

Meaning:
- state does not create direction
- state modulates interpretation strength

Implementation:
- `backend/trading/engine/state/*`

Status:
- implemented and treated as semantic foundation

### Evidence
Role:
- summarizes immediate decision-friendly proof from Position + Response + State

Important outputs:
- `EvidenceVector`

Canonical fields:
- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_continuation_evidence`
- `sell_continuation_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

Meaning:
- not future prediction
- only current immediate proof

Implementation:
- `backend/trading/engine/core/evidence_engine.py`

Status:
- implemented and treated as semantic foundation

### Belief
Role:
- accumulates evidence over time

Important outputs:
- `BeliefState`

Canonical fields:
- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

Meaning:
- separates one-bar spike from multi-bar persistence
- does not re-read Position/Response/State directly

Implementation:
- `backend/trading/engine/core/belief_engine.py`

Status:
- implemented and treated as semantic foundation

### Barrier
Role:
- says why action should be delayed or blocked even if evidence exists

Important outputs:
- `BarrierState`

Canonical fields:
- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

Meaning:
- conflict/chop/policy/liquidity friction
- does not create direction
- does not re-interpret raw semantic inputs

Implementation:
- `backend/trading/engine/core/barrier_engine.py`

Status:
- implemented and treated as semantic foundation

---

## Semantic Foundation Freeze

The following layers are now treated as the semantic feature foundation:

- Position
- Response
- State
- Evidence
- Belief
- Barrier

What this means:
- they stay even if ML/DL is introduced later
- they are the feature layer, not the final live action layer
- they should only receive bug fixes, acceptance corrections, and contract clarification
- they should not be rebuilt from scratch for each new idea

This is important because future `ForecastRuleV1`, `ForecastModelV1`, and later sequence models should all sit on top of the same semantic foundation.

---

## Forecast Layer

### ForecastFeaturesV1
Role:
- packages semantic layers into a single forecast-ready input contract

Important fields:
- `position_primary_label`
- `position_bias_label`
- `position_secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

Implementation:
- `backend/trading/engine/core/forecast_features.py`

### TransitionForecastV1
Role:
- predicts what near-term transition is more likely before/around entry

Important fields:
- `p_buy_confirm`
- `p_sell_confirm`
- `p_false_break`
- `p_reversal_success`
- `p_continuation_success`

Meaning:
- not calibrated probability
- scenario score

Implementation:
- `backend/trading/engine/core/forecast_engine.py`

### TradeManagementForecastV1
Role:
- predicts what trade management scenario is more likely after entry

Important fields:
- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`
- `p_better_reentry_if_cut`

Meaning:
- also scenario score
- used to reason about hold/cut/recover/re-entry

Implementation:
- `backend/trading/engine/core/forecast_engine.py`

### Forecast Interface
Current design intent:
- forecast must be replaceable
- current implementation is rule-based baseline
- future ML/DL model should emit the same contracts

Current implementation:
- `ForecastRuleV1`

Future:
- `ForecastModelV1`
- `ForecastSequenceModelV1`

---

## Forecast Calibration Status

Forecast calibration was introduced because the first live behavior showed weak confidence separation.

Main calibration problem:
- `confirm` and `false_break` were too close
- `continue_favor` and `fail_now` were too close
- some `WAIT/OBSERVE` contexts still showed overly high confirm scores

Calibration work already added:
- separation metrics
- competition-aware scoring
- multiplicative compression reduction
- transition-specific calibration
- management-specific calibration
- forecast metadata and gap logging

Important calibration metrics now available:
- `side_separation`
- `confirm_fake_gap`
- `reversal_continuation_gap`
- `continue_fail_gap`
- `recover_reentry_gap`

Important interpretation:
- forecast direction is broadly useful
- transition-side calibration is much closer to usable
- management-side validation still depends on better future outcome labeling

This is the key reason `OutcomeLabeler` matters.

---

## The Missing Middle: Forecast to Observe / Confirm / Action

Another thread must not assume that `Forecast` directly equals `Observe / Confirm / Action`.

There is a necessary translation layer in between.

The conceptual gap looks like this:

```text
Forecast
-> Decision Translation
-> Observe / Confirm / Action Contract
-> Consumer
```

What this middle layer must do:

1. choose dominant side
- `BUY`
- `SELL`
- `BALANCED`

2. choose dominant path
- `REVERSAL`
- `CONTINUATION`
- `UNRESOLVED`

3. compare confirm vs fake
- strong confirm is not enough
- confirm must also beat fake pressure

4. compare continue vs fail
- hold bias must beat failure pressure

5. decide lifecycle state
- `WAIT`
- `OBSERVE`
- `CONFIRM`
- `ACTION`

This means:
- `Forecast` is still predictive
- `Observe / Confirm / Action` is still policy/lifecycle
- they are related, but they are not the same layer

---

## Observe / Confirm / Action

This is the live decision layer.

Role:
- convert semantic + forecast state into lifecycle state

It should eventually consume:
- semantic foundation
- transition forecast
- trade management forecast

It should output:
- lifecycle state
- side
- confidence
- archetype
- invalidation id
- management profile id

It should not:
- re-interpret raw position coordinates
- re-read raw response detector fields
- directly invent forecast semantics

Current project reality:
- contracts and docs are already heavily prepared
- the full forecast-to-OCA consumption path is the next major structural connection

Related docs:
- `docs/observe_confirm_input_contract.md`
- `docs/observe_confirm_output_contract.md`
- `docs/observe_confirm_routing_policy.md`
- `docs/observe_confirm_confidence_semantics.md`
- `docs/observe_confirm_archetype_taxonomy.md`
- `docs/observe_confirm_invalidation_taxonomy.md`
- `docs/observe_confirm_management_profile_taxonomy.md`

---

## Consumer

Consumer is not the semantic layer and not the forecast layer.

Role:
- execute what the decision layer already decided

Main parts:
- `SetupDetector`
- `EntryService`
- exit/re-entry execution paths

Correct responsibility:
- `SetupDetector` labels a confirmed archetype
- `EntryService` applies guards and executes
- exit/re-entry should consume management profile + forecast, not recreate semantics

Incorrect responsibility:
- re-reading box/band meaning
- making a second direction engine
- rebuilding lifecycle meaning from raw features

Current project direction:
- consumer has been progressively reduced toward execution-only responsibility
- it should stay that way

---

## OutcomeLabeler: Why It Exists

`OutcomeLabeler` is not part of the live action path.

It belongs to the offline validation / ML-preparation path.

Role:
- take semantic + forecast snapshots from a past row
- look into future outcomes
- assign labels that answer: "Was that forecast actually right?"

Without this:
- management forecast cannot be truly validated
- rule forecast cannot become a strong shadow baseline
- ML/DL cannot be trained on reliable labels

In short:
- forecast predicts
- outcome labeler grades

---

## OutcomeLabeler 7~9: What They Actually Mean

This was the confusing part in the roadmap, so it is worth stating very directly.

### L7. Ambiguity / Censoring Rules
This means:
- if the future evidence is not sufficient, do not force a bad label

Typical statuses:
- `INSUFFICIENT_FUTURE_BARS`
- `NO_EXIT_CONTEXT`
- `NO_POSITION_CONTEXT`
- `AMBIGUOUS`
- `CENSORED`

Why this matters:
- if the labeler always forces `0` or `1`
- bad labels pollute later validation and model training

So `L7` is:
- not “make more labels”
- but “avoid making bad labels”

### L8. Outcome Signal Source Definition
This means:
- define exactly which files and keys are used to judge future outcome

Typical sources:
- `entry_decisions.csv`
- `trade_closed_history.csv`
- optional lifecycle or exit logs

Typical keys:
- `symbol`
- row timestamp
- `signal_bar_ts`
- `ticket` or position id
- side/action/setup context

Why this matters:
- without deterministic source mapping, future outcome matching becomes noisy and unreliable

So `L8` is:
- not label semantics
- but source-of-truth and matching semantics

### L9. Labeler Engine Implementation
This is the actual offline engine that applies the rules.

It is responsible for:
- anchor resolution
- future window selection
- positive/negative/unknown/censored determination
- metadata and reason generation

It is offline only.

It is not:
- a live decision layer
- a replacement for forecast

So if someone asks “what are 7~9?”:

- `L7` = quality control for labels
- `L8` = data source and matching contract
- `L9` = the actual implementation engine

---

## OutcomeLabeler Current Status

OutcomeLabeler is not just a roadmap item anymore.

It is already materially present in the codebase.

Main implementation files:
- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/services/outcome_labeler_contract.py`
- `backend/trading/engine/offline/outcome_label_validation_report.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`

Related docs already exist in `docs/`:
- `outcome_labeler_labeling_philosophy.md`
- `outcome_labeler_anchor_definition.md`
- `outcome_labeler_horizon_definition.md`
- `outcome_labeler_transition_label_rules.md`
- `outcome_labeler_management_label_rules.md`
- `outcome_labeler_ambiguity_censoring_rules.md`
- `outcome_labeler_outcome_signal_source.md`
- `outcome_labeler_label_metadata.md`
- `outcome_labeler_shadow_output.md`
- `outcome_labeler_dataset_builder_bridge.md`
- `outcome_labeler_validation_report.md`

That means:
- this is already beyond idea stage
- it is closer to implemented-v1-plus-validation than to pure roadmap

---

## What Is Implemented vs What Still Needs Stronger Acceptance

### Implemented and broadly stable
- semantic foundation
- forecast feature packaging
- transition forecast
- trade management forecast
- forecast calibration logging
- outcome labeler contracts and implementation
- validation report path
- replay dataset builder path

### Still needing stronger acceptance or follow-through
- full `Forecast -> Observe / Confirm / Action` policy bridge
- management forecast validation on real future outcomes
- shadow compare readiness for rule baseline vs later ML model
- consumer final adoption without semantic re-interpretation

---

## Recommended Reading Order for Another Thread

If another thread needs to continue from here, the fastest order is:

1. this file
2. `docs/observe_confirm_output_contract.md`
3. `docs/observe_confirm_routing_policy.md`
4. `docs/outcome_labeler_labeling_philosophy.md`
5. `docs/outcome_labeler_anchor_definition.md`
6. `docs/outcome_labeler_ambiguity_censoring_rules.md`
7. `backend/trading/engine/core/forecast_engine.py`
8. `backend/trading/engine/offline/outcome_labeler.py`

If the next task is live-decision stabilization:
- focus on `Forecast -> OCA -> Consumer`

If the next task is ML-readiness:
- focus on `OutcomeLabeler -> Validation Report -> Replay Dataset Builder`

---

## Practical Next-Step Map

### If the goal is better live decision quality
Next work:
- build the forecast-to-OCA translation layer
- finalize lifecycle gating
- keep consumer execution-only

### If the goal is ML/DL readiness
Next work:
- tighten outcome labels
- expand validation report coverage
- build shadow compare baseline
- prepare dataset builder outputs for model training

### If the goal is cross-thread collaboration
Use this document as the entry point and treat:
- semantic foundation as frozen
- forecast as calibrated baseline
- outcome labeler as offline grader

---

## Short Final Summary

The current system is no longer just:

```text
Position -> Response -> State -> decision
```

It is now:

```text
Semantic Foundation
(Position / Response / State / Evidence / Belief / Barrier)
-> Forecast
-> Observe / Confirm / Action
-> Consumer

Offline in parallel:
Semantic + Forecast
-> OutcomeLabeler
-> Validation / Dataset / Model readiness
```

The important distinction is:
- `Forecast` predicts
- `Observe / Confirm / Action` decides
- `Consumer` executes
- `OutcomeLabeler` grades

That distinction should remain stable across future threads.
