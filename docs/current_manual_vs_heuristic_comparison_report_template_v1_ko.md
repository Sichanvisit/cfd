# Manual vs Heuristic Comparison Report Template v2

## Purpose

This document upgrades the manual-vs-heuristic report from a simple review sheet into a
`priority-decision layer`.

Its job is no longer only:

- compare `manual teacher truth`
- compare `heuristic owner interpretation`

It must also decide:

- which mismatch families are `correction-worthy`
- which mismatch families are `freeze-worthy`
- which draft rows are safe to promote into canonical manual truth
- which mismatch family should be the next BCE correction target

In short:

- manual truth = answer key
- heuristic owners = judged layer
- comparison report = priority and correction control surface

## Position In The Roadmap

This report lives above the heuristic owner layer and above BCE diagnostics.

Read the stack like this:

- execution engine = actual behavior
- semantic owners = heuristic interpretation
- BCE / wait-family = heuristic refinement
- manual truth = answer key
- manual-vs-heuristic report = calibration, prioritization, and correction control

This report is not a runtime trading feature.
It is a `decision-support layer` for:

- calibration
- bias correction
- freeze / hold decisions
- canonical manual-truth promotion

## Core Interpretation Rule

The current manual corpus must be treated as:

- `standalone teacher corpus`
- `ideal / counterfactual answer key`

It must not be treated as:

- direct replay reconstruction
- mandatory closed-history backfill target
- baseline/candidate training seed by default

This means:

- matching to `trade_closed_history.csv` is optional
- matching failure is not a blocker
- perfect executed-trade alignment is not the success criterion

If a row is time-matched but heuristic semantic hints are blank, do not call that owner failure
immediately.

Recommended diagnostic order:

1. paired legacy detail fallback audit
2. global detail fallback audit across all `entry_decisions*.detail.jsonl`,
   especially rotated `entry_decisions.detail.rotate_*.jsonl`
3. recovered-case casebook for rows restored by rotate-detail fallback
4. recovered-case bias target extraction for repeated mismatch families
5. focused gap-aware audit for the remaining small mismatch families
6. current-rich manual collection queue for the latest hint-dense windows
7. only then decide whether the mismatch is:
   - `correction-worthy`
   - `freeze-worthy`
   - `needs_more_recent_truth`
   - `insufficient_evidence`

## Report Unit

The minimum comparison unit is:

- one `episode_id`

One row must answer:

- what did the manual teacher say?
- what did the heuristic owners say?
- how strong is the evidence on each side?
- is this a real correction target or a hold/freeze case?
- what should the next action be?

## Required Input Sources

### Manual Side

- `data/manual_annotations/manual_wait_teacher_annotations.csv`
- optional current-rich draft:
  `data/manual_annotations/manual_current_rich_seed_draft_latest.csv`

### Heuristic Side

Use whichever surfaces are available for the same episode or nearest compatible scene window:

- barrier outcome / wait-family interpretation
- forecast hint / overlay if relevant
- belief hint if relevant
- runtime summary / entry-decision summary if relevant
- global rotate-detail fallback reconstruction if direct CSV hints are sparse

Initial implementation may start with:

- barrier
- wait-family heuristic

and add forecast/belief later.

## Main Output Goals

The report should answer:

1. where barrier/wait-family agrees with manual truth
2. where it systematically misses good waits
3. where it over-neutralizes or over-blocks
4. where protective-exit or reversal interpretation is wrong
5. which repeated mismatch families are truly worth correction
6. which mismatch families should be frozen instead of edited
7. which current-rich draft rows are safe to promote into canonical truth

## Canonical Column Groups

### A. Episode Identity

- `comparison_id`
- `episode_id`
- `symbol`
- `timeframe`
- `scene_id`
- `chart_context`
- `box_regime_scope`
- `anchor_side`
- `anchor_time`
- `anchor_price`

Purpose:

- keep one review row tied to one manual truth episode

### B. Manual Truth Columns

- `manual_truth_source_bucket`
- `manual_truth_review_state`
- `manual_wait_teacher_label`
- `manual_wait_teacher_polarity`
- `manual_wait_teacher_family`
- `manual_wait_teacher_subtype`
- `manual_wait_teacher_usage_bucket`
- `manual_wait_teacher_confidence`
- `ideal_entry_time`
- `ideal_entry_price`
- `ideal_exit_time`
- `ideal_exit_price`
- `manual_teacher_confidence`
- `manual_annotation_note`

Purpose:

- preserve the teacher answer key as the comparison anchor
- distinguish canonical truth from review-needed current-rich draft

### C. Heuristic Barrier / Wait Columns

- `heuristic_barrier_main_label`
- `heuristic_barrier_confidence_tier`
- `heuristic_barrier_outcome_family`
- `heuristic_wait_family`
- `heuristic_wait_subtype`
- `heuristic_wait_usage_bucket`
- `heuristic_counterfactual_family`
- `heuristic_counterfactual_cost_delta_r`
- `heuristic_drift_status`
- `heuristic_barrier_reason_summary`

Purpose:

- show how barrier and wait-family interpreted the same situation

### D. Optional Forecast / Belief Alignment Columns

- `heuristic_forecast_family`
- `heuristic_forecast_reason_summary`
- `heuristic_belief_family`
- `heuristic_belief_reason_summary`

Purpose:

- let the report grow into cross-owner comparison later

### E. Evidence Quality Columns

- `heuristic_evidence_source_kind`
- `heuristic_evidence_recoverability_grade`
- `heuristic_evidence_quality`
- `evidence_gap_minutes`
- `current_rich_overlap_flag`
- `current_rich_proxy_support`

Recommended values:

- `source_kind`
  - `current_csv`
  - `legacy_csv`
  - `global_detail_fallback`
  - `manual_only`
- `recoverability_grade`
  - `high`
  - `medium`
  - `low`
  - `none`
- `heuristic_evidence_quality`
  - `rich`
  - `usable`
  - `thin`
  - `missing`
- `current_rich_overlap_flag`
  - `yes`
  - `no`
- `current_rich_proxy_support`
  - `supports_shift`
  - `supports_hold`
  - `mixed`
  - `not_checked`

Purpose:

- prevent far-gap legacy matches from driving aggressive rule edits

### F. Comparison Verdict Columns

- `manual_vs_barrier_match`
- `manual_vs_wait_family_match`
- `manual_vs_forecast_alignment`
- `manual_vs_belief_alignment`
- `overall_alignment_grade`

Recommended values:

- `match`
- `partial_match`
- `mismatch`
- `unknown`

### G. Mismatch Typing Columns

- `miss_type`
- `mismatch_severity`
- `primary_correction_target`
- `repeated_case_signature`

Recommended early `miss_type` values:

- `missed_good_wait`
- `false_avoided_loss`
- `overly_neutral_wait`
- `wrong_protective_interpretation`
- `wrong_reversal_escape_interpretation`
- `wrong_failed_wait_interpretation`
- `insufficient_heuristic_evidence`

Recommended `primary_correction_target` values:

- `barrier_bias_rule`
- `wait_family_mapping`
- `protective_exit_interpretation`
- `reversal_escape_interpretation`
- `manual_truth_needs_review`
- `insufficient_owner_coverage`

### H. Priority / Freeze Decision Columns

- `correction_worthiness_class`
- `freeze_worthiness_class`
- `rule_change_readiness`
- `correction_priority_tier`
- `recommended_next_action`
- `mismatch_disposition`

Recommended values:

- `correction_worthiness_class`
  - `correction_worthy`
  - `candidate_correction`
  - `not_correction_worthy`
- `freeze_worthiness_class`
  - `freeze_worthy`
  - `hold_for_more_truth`
  - `not_freeze_worthy`
- `rule_change_readiness`
  - `ready`
  - `needs_more_recent_truth`
  - `needs_manual_recheck`
  - `insufficient_evidence`
- `correction_priority_tier`
  - `P1`
  - `P2`
  - `P3`
  - `hold`
- `mismatch_disposition`
  - `edit_rule_now`
  - `collect_current_rich_truth`
  - `freeze_and_monitor`
  - `keep_as_casebook_only`

Purpose:

- turn the report into a true correction-control surface

### I. Scoring Columns

- `frequency_score`
- `severity_score`
- `current_rich_reproducibility_score`
- `evidence_quality_score`
- `correction_cost_score`
- `correction_priority_score`
- `freeze_risk_score`

Scoring guidance:

- `frequency_score`
  - `3` = repeated family already visible in multiple rows or symbols
  - `2` = repeated within one family or one symbol
  - `1` = isolated row
- `severity_score`
  - `3` = clearly changes interpretation of good wait / protective exit / major miss
  - `2` = meaningful but not dominant bias
  - `1` = small local mismatch
- `current_rich_reproducibility_score`
  - `3` = repeated in current-rich windows too
  - `2` = mixed
  - `1` = only old legacy evidence
- `evidence_quality_score`
  - `3` = current-rich or strong recovered detail
  - `2` = usable recovered evidence
  - `1` = thin or partially missing evidence
- `correction_cost_score`
  - `3` = low risk to change
  - `2` = moderate risk
  - `1` = high collateral-risk change

Recommended derived rules:

- `correction_priority_score`
  - `frequency + severity + reproducibility + evidence_quality + correction_cost`
- `freeze_risk_score`
  - high when:
    - evidence is thin
    - gap is large
    - current-rich support is mixed or absent
    - correction cost is high

### J. Canonical Promotion Columns

- `canonical_promotion_readiness`
- `canonical_promotion_reason`
- `canonical_promotion_recommendation`

Recommended values:

- `canonical_promotion_readiness`
  - `ready`
  - `review_needed`
  - `hold_current_rich_only`
  - `insufficient_episode_detail`
- `canonical_promotion_recommendation`
  - `promote_to_canonical`
  - `keep_in_current_rich_draft`
  - `reject_from_manual_truth`

Purpose:

- prevent review-needed current-rich rows from silently polluting canonical truth

### K. Review Ops Columns

- `comparison_status`
- `review_round`
- `review_owner`
- `review_comment`
- `created_at`
- `updated_at`
- `comparison_version`

Recommended early `comparison_status` values:

- `draft`
- `reviewed`
- `accepted`
- `needs_manual_recheck`

## Initial Matching Rule

At the current stage, do not require perfect executed-trade matching.

Recommended comparison priority:

1. exact `episode_id` if heuristic side is manually linked
2. nearest compatible symbol + time window + side
3. recovered semantic hints through rotate-detail fallback
4. casebook-only row if no reliable heuristic link exists yet

This is intentional.

The report should still exist even when the episode is:

- ideal
- counterfactual
- not represented by an executed trade

## Priority-Decision Rules

### Rule 1. Correction-Worthy

Call a mismatch `correction_worthy` only when:

- it repeats
- it materially changes interpretation
- it appears again in current-rich evidence or strong recovered detail
- the correction cost is not too high

### Rule 2. Freeze-Worthy

Call a mismatch `freeze_worthy` when:

- sample is very small
- evidence is mostly far-gap legacy
- current-rich support is mixed or missing
- pushing the rule risks contaminating many valid waits

### Rule 3. Hold For More Truth

Use `hold_for_more_truth` when:

- the pattern is plausible
- but current-rich confirmation is not yet sufficient
- or manual review is still incomplete

### Rule 4. Canonical Promotion Guardrail

Current-rich draft rows must not enter canonical truth unless they satisfy all of:

- manual review completed
- confidence at least `medium`
- episode coordinates sufficiently filled
- meaningful calibration value
- stable interpretation under re-review

## Initial Summary Views

The first useful priority-decision report should summarize:

- `total_comparisons`
- `barrier_match_rate`
- `wait_family_match_rate`
- `top_miss_types`
- `top_symbols_with_mismatch`
- `top_repeated_case_signatures`
- `correction_worthy_family_counts`
- `freeze_worthy_family_counts`
- `current_rich_promotion_ready_count`
- `next_mismatch_family_ranking`

## Follow-On Outputs

After the first comparison report is available, the next operational outputs should be:

### Recovered Casebook

- isolate rows restored via `global_detail_fallback`
- inspect repeated mismatch signatures
- separate `match / partial_match / mismatch` inside the recovered subset

### Bias Targets

- group recovered mismatches into repeated target families
- map each target family to a practical BCE correction step
- highlight `P1 / P2 / P3 / hold` priorities

### Current-Rich Collection Queue

- scan the latest current `entry_decisions.csv` window
- identify recent hint-rich windows after the latest manual anchor
- build a per-symbol queue so new manual truth is collected where heuristic evidence is dense
- use the queue before editing rules still supported only by far-gap legacy matches

### Current-Rich Canonical Promotion Review

- review draft rows before canonical merge
- reject rows that are pretty but not calibration-useful
- keep canonical truth and review-needed draft clearly separated

### Freeze-Worthy Mismatch Audit

- isolate the remaining low-sample or far-gap families
- explain why they are frozen
- prevent future rule drift caused by overreaction

## Initial Working Rules

### Rule 1

Manual truth is the answer key.
Heuristic output is what gets judged.

### Rule 2

Do not feed comparison rows directly into baseline/candidate training.

### Rule 3

Use this report first for:

- calibration
- bias correction
- freeze / hold decisions
- canonical promotion control

### Rule 4

Closed-history matching is optional.
It is not the primary success criterion.

### Rule 5

Do not edit a rule only because a mismatch exists.
Edit only when the mismatch is `correction-worthy`.

## Suggested First Use Cases

1. `good_wait_better_entry` vs barrier `avoided_loss`
2. `good_wait_protective_exit` vs heuristic `neutral_wait`
3. `bad_wait_missed_move` vs heuristic `failed_wait`
4. `neutral_wait_small_value` vs overly strong heuristic claim
5. `wrong_failed_wait_interpretation` triage into:
   - `correction_worthy`
   - `freeze_worthy`
   - `needs_more_recent_truth`

## Short Conclusion

This report should now be treated as:

- the first formal calibration layer between manual truth and heuristic owners
- the place where correction priorities are chosen
- the place where freeze decisions are justified
- the gatekeeper for current-rich draft promotion into canonical truth

Its job is no longer only:

- `where are we wrong?`

It must answer:

- `which wrongness is worth correcting now, which one should be frozen, and what should we do next?`
