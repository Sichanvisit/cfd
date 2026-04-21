# Manual Trade Episode Truth Model v1

## Purpose

This document fixes the next manual-truth direction as:

`storage = episode-first`
`operations = wait-first`

The goal is not to discard the existing `manual_wait_teacher` work.
The goal is to preserve the current wait-first operating loop while making the truth structure
expand naturally into:

- entry truth
- wait truth
- exit truth

inside a single annotated trade episode.

## Why This Model Is Needed

The current manual truth layer already captures:

- anchor
- idealized entry point
- idealized exit point
- wait label

But today those entry/exit coordinates are structurally subordinate to a single
`manual_wait_teacher_label`.

That is good enough for Barrier wait-bias correction,
but it is not enough for long-term truth reuse when:

- entry owner opens
- exit owner opens
- episode-level quality needs to be compared across entry / wait / exit

So the adopted direction is:

- keep `manual_wait_teacher` as the first operational truth surface
- change the storage model so one row means one `episode`
- let entry/exit become first-class truth candidates even before they are operational labels

## Core Principle

The system should now be read as:

- `manual_wait_teacher` = first operational truth channel
- `manual_entry_teacher` = nullable truth candidate
- `manual_exit_teacher` = nullable truth candidate

This means:

- importer v1 stays wait-first
- schema becomes episode-centric
- importer v2/v3 may later materialize entry / exit truth separately

## Episode Unit

The minimum annotation unit is no longer "one wait label row".
It is now "one anchor-based judgment episode".

One episode may contain:

- where the decision context started
- where the ideal entry would have been
- what the waiting character was
- where the ideal exit would have been

## Episode Common Fields

The common episode backbone should contain:

- `episode_id`
- `symbol`
- `timeframe`
- `scene_id` or compatible runtime anchor key
- `anchor_time`
- `anchor_price`
- `anchor_side`
- `annotation_author`
- `annotation_created_at`
- `annotation_note`
- `manual_teacher_confidence`

These fields exist to keep entry / wait / exit truth tied to one reviewable object.

## Entry Truth Channel

Entry truth is first-class in storage, even if not yet first-class in operations.

Recommended fields:

- `ideal_entry_time`
- `ideal_entry_price`
- `manual_entry_teacher_label`
- `manual_entry_teacher_confidence`
- `manual_entry_teacher_note`

Recommended early rule:

- coordinates first
- labels optional

Early example labels:

- `good_entry_immediate`
- `good_entry_after_wait`
- `good_entry_after_relief`
- `no_good_entry`
- `late_entry_only`

## Wait Truth Channel

This remains the primary operational truth channel in the current stage.

Current fields:

- `manual_wait_teacher_label`
- `manual_wait_teacher_polarity`
- `manual_wait_teacher_family`
- `manual_wait_teacher_subtype`
- `manual_wait_teacher_usage_bucket`
- `manual_wait_teacher_confidence`
- `manual_wait_teacher_note`

Current labels remain valid:

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

## Exit Truth Channel

Exit truth should also be stored as a first-class candidate before it becomes an operating label.

Recommended fields:

- `ideal_exit_time`
- `ideal_exit_price`
- `manual_exit_teacher_label`
- `manual_exit_teacher_confidence`
- `manual_exit_teacher_note`

Recommended early rule:

- coordinates first
- labels optional

Early example labels:

- `good_exit_protective`
- `good_exit_reversal_escape`
- `good_exit_target_hit`
- `good_exit_reduce_first`
- `no_clear_exit_edge`

## Transition From The Current Manual-Wait Schema

The current schema should not be thrown away.

Instead, reinterpret it like this:

- `annotated_entry_time` -> semantic target: `ideal_entry_time`
- `annotated_entry_price` -> semantic target: `ideal_entry_price`
- `annotated_exit_time` -> semantic target: `ideal_exit_time`
- `annotated_exit_price` -> semantic target: `ideal_exit_price`

Meaning:

- these are no longer "supporting evidence only"
- these are now episode-level truth coordinates

Minimum additive fields for the next schema step:

- `episode_id`
- `manual_entry_teacher_label` nullable
- `manual_entry_teacher_confidence` nullable
- `manual_exit_teacher_label` nullable
- `manual_exit_teacher_confidence` nullable

## Importer Strategy

### Importer v1

Read episode-shaped annotations, but backfill only:

- `manual_wait_teacher_*`

Current canonical working file:

- `data/manual_annotations/manual_wait_teacher_annotations.csv`
- current intake seed set: recent manual episodes from NAS / XAU / BTC

Working rule:

- append NAS / XAU / BTC episode rows into the same canonical file
- keep one row = one episode
- allow partially-filled rows while coordinates are still being confirmed
- prefer running importer dry-run before any write-back

Why:

- Barrier bias correction is still wait-first
- current compare/diagnostic loops are still centered on wait-family
- manual truth is currently best used as a standalone answer key, not as a mandatory replay match

### Importer v2

When entry-owner work starts, begin backfilling:

- `manual_entry_teacher_*`
- `ideal_entry_*`

### Importer v3

When exit-owner work starts, begin backfilling:

- `manual_exit_teacher_*`
- `ideal_exit_*`

## Annotation Burden Rule

Do not require the annotator to fill every channel completely at the beginning.

### Required

- `anchor_time`
- `anchor_price`
- `manual_wait_teacher_label`

### Strongly Recommended

- `ideal_entry_time`
- `ideal_entry_price`
- `ideal_exit_time`
- `ideal_exit_price`

### Optional

- `manual_entry_teacher_label`
- `manual_exit_teacher_label`

This keeps the initial human workload manageable while preserving long-term truth value.

## Recommended Path

1. keep the current `manual_wait_teacher` operational surface
2. widen the schema into `episode-first`
3. preserve entry/exit coordinates as first-class truth coordinates
4. keep importer v1 wait-only
5. expand entry/exit import only when those owners are opened

## Short Conclusion

The adopted direction is:

- not `wait-only forever`
- not `full 3-channel operations immediately`

It is:

`episode-centric truth storage with wait-first operations`

That gives the project the least short-term disruption and the best long-term reuse.
