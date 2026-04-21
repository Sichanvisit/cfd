# Manual Trade Episode Truth Implementation Roadmap

## Purpose

This roadmap turns the manual-truth direction into an executable sequence without losing the
current wait-first operating loop.

The fixed rule is:

- storage = episode-first
- operations = wait-first

## Scope

The roadmap covers only the manual truth layer.

It does not change:

- barrier main labels
- wait-family heuristic overlay
- compare/gate authority

It prepares future truth reuse for:

- entry owner
- wait owner / barrier bias correction
- exit owner

## ET0. Scope Lock

Lock the operating principle:

- `manual_wait_teacher` remains the first active truth channel
- entry/exit truth is added as episode-level coordinates first
- entry/exit labels remain nullable until those owners open

Output:

- one canonical episode-centric truth model document
- one implementation roadmap document

## ET1. Episode Backbone

Add or reinterpret the shared episode backbone:

- `episode_id`
- `symbol`
- `timeframe`
- `scene_id` or runtime-compatible anchor key
- `anchor_time`
- `anchor_price`
- `anchor_side`
- `annotation_author`
- `annotation_created_at`
- `annotation_note`
- `manual_teacher_confidence`

Rule:

- one row = one anchor-based manual review episode

Current status (2026-04-06):

- implemented in `backend/services/manual_wait_teacher_annotation_schema.py`
- `episode_id`, `anchor_side`, `scene_id`, `annotation_author`, `annotation_created_at`,
  `manual_teacher_confidence` are now part of the canonical annotation schema

## ET2. Coordinate Promotion

Promote current coordinates from "supporting evidence" to "episode truth coordinates".

Semantic targets:

- `annotated_entry_time` -> `ideal_entry_time`
- `annotated_entry_price` -> `ideal_entry_price`
- `annotated_exit_time` -> `ideal_exit_time`
- `annotated_exit_price` -> `ideal_exit_price`

Rule:

- alias-compatible migration first
- no immediate breakage for current template users

Current status (2026-04-06):

- implemented
- canonical fields are now `ideal_entry_*`, `ideal_exit_*`
- legacy `annotated_entry_*`, `annotated_exit_*` are still accepted as input aliases

## ET3. Wait-Channel Stability

Preserve the current wait channel as-is:

- `manual_wait_teacher_label`
- `manual_wait_teacher_polarity`
- `manual_wait_teacher_family`
- `manual_wait_teacher_subtype`
- `manual_wait_teacher_usage_bucket`
- `manual_wait_teacher_confidence`

Rule:

- wait-first operations stay active
- barrier bias correction continues to consume wait truth first

Current status (2026-04-06):

- implemented
- existing wait-family and manual wait label flow remains unchanged at operation level

## ET4. Entry Truth Candidate Fields

Open nullable entry truth candidates:

- `manual_entry_teacher_label`
- `manual_entry_teacher_confidence`
- `manual_entry_teacher_note`

Rule:

- coordinates first
- labels optional

Current status (2026-04-06):

- implemented at schema/template level
- still nullable and not yet consumed by importer v1

## ET5. Exit Truth Candidate Fields

Open nullable exit truth candidates:

- `manual_exit_teacher_label`
- `manual_exit_teacher_confidence`
- `manual_exit_teacher_note`

Rule:

- coordinates first
- labels optional

Current status (2026-04-06):

- implemented at schema/template level
- still nullable and not yet consumed by importer v1

## ET6. Importer v1

Build the first importer around episode rows, but backfill only:

- `manual_wait_teacher_*`

Read but do not yet operationalize:

- `ideal_entry_*`
- `ideal_exit_*`
- `manual_entry_teacher_*`
- `manual_exit_teacher_*`

Current status (2026-04-06):

- implemented as closed-history wait-only backfill
- service: `backend/services/manual_wait_teacher_seed_enrichment.py`
- script: `scripts/backfill_manual_wait_teacher_truth.py`
- current write target remains `manual_wait_teacher_*`
- `manual_wait_teacher_episode_id` is now stored on trade rows for episode linkage
- canonical intake file: `data/manual_annotations/manual_wait_teacher_annotations.csv`
- current seed rows: NAS / XAU / BTC recent manual episodes
- next expansion path: keep appending cross-asset episode rows into the same intake file and improve coordinate quality for matching

## ET7. Entry / Exit Expansion

When entry owner opens:

- importer v2 starts backfilling `manual_entry_teacher_*`

When exit owner opens:

- importer v3 starts backfilling `manual_exit_teacher_*`

## ET8. Manual vs Heuristic Comparison Report

Build a comparison layer above the manual corpus and heuristic owner outputs.

Purpose:

- treat manual truth as a standalone answer key
- compare manual truth against barrier / wait-family heuristic interpretation
- use the result for calibration, bias correction, and casebook review
- upgrade the report into a `priority-decision surface`
- decide which mismatch families are:
  - `correction-worthy`
  - `freeze-worthy`
  - `needs_more_recent_truth`
  - `insufficient_evidence`

Current status (2026-04-06):

- template document added:
  `docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md`
- canonical table header added:
  `data/manual_annotations/manual_vs_heuristic_comparison_template.csv`
- comparison template now expanded to a priority-decision v2 structure
- recommended next implementation:
  build and maintain comparison rows as a correction/freeze decision tool, not only as a
  descriptive report

Current shadow bridge extension (2026-04-08):

- ET8r now has a real preview-shadow bridge path:
  - manual truth / comparison / ranking / correction discipline
  - -> semantic shadow training corpus
  - -> proxy dataset materialization
  - -> preview bundle training
  - -> offline shadow activation / execution evaluation
  - -> SA5 correction loop / SA6 decision recommendation
- current shadow status:
  - preview bundle bootstrap is `preview_bundle_ready`
  - offline preview runtime activation succeeds on `64` test rows
  - current SA5/SA6 outcome is `accept_preview_candidate -> APPLY_CANDIDATE`
  - bounded gate is `ALLOW_BOUNDED_LIVE_CANDIDATE`
  - active runtime readiness is `candidate_stage_ready`
  - bounded candidate stage is `candidate_runtime_staged`
  - current approval workflow state is `approved_pending_activation`
  - active runtime activation has been force-run once as `activated_candidate_runtime_forced`
  - runtime now reports `semantic_shadow_loaded = true` and `shadow_runtime_reason = loaded`
  - semantic live rollout has now been switched from `disabled` to bounded `log_only`
  - recent `entry_decisions` rows now record `semantic_live_rollout_mode = log_only`
  - current bounded observation result is still conservative:
    - `threshold_applied_total = 0`
    - `partial_live_total = 0`
    - `recent_threshold_would_apply_count = 0`
    - `recent_partial_live_would_apply_count = 0`
    - `rollout_promotion_readiness = blocked_no_eligible_rows`
    - `recommended_next_action = retain_log_only_and_improve_baseline_action_or_semantic_quality`
  - SA9 knowledge base is now open:
    - `data/analysis/shadow_auto/correction_knowledge_base.csv`
- worker hygiene has been tightened:
  - `manage_cfd.bat` now matches bare `main.py` command lines
  - duplicate `main.py` workers have been de-duped back to `1`
- next strategic layer after ET8r:
  - `docs/current_execution_authority_integration_design_ko.md`
  - `docs/current_execution_authority_integration_implementation_roadmap_ko.md`
  - interpretation:
    - calibration and shadow are now mature enough
    - the next blocker is no longer just model quality
    - the remaining blocker is that live execution authority still remains in the rule-policy orchestrator

### ET8a. Heuristic Evidence Recovery Audit

After the first comparison pass, audit whether historical heuristic evidence can be recovered when
the matched `entry_decisions` row comes from an old legacy CSV schema.

Purpose:

- separate comparison-logic issues from historical logging-coverage issues
- test paired-source detail fallback first
- if paired fallback is sparse, test global detail fallback across all historical
  `entry_decisions*.detail.jsonl`, especially rotated
  `entry_decisions.detail.rotate_*.jsonl`

Rule:

- treat closed-history matching as optional
- treat legacy detail fallback as a diagnostic recovery path under ET8, not as a new owner rollout

Current status (2026-04-06):

- comparison v0 implemented
- paired legacy detail fallback audit implemented
- global detail fallback audit implemented as the next ET8 diagnostic branch
- current finding: old legacy CSV snapshots often miss barrier / wait / forecast / belief columns, so
  ET8 now includes evidence-recovery diagnostics before any bias-interpretation claim

### ET8b. Recovered-Case Bias Target Extraction

After ET8a restores a meaningful subset of historical heuristic evidence, extract explicit
barrier-bias correction targets from the recovered mismatch set.

Purpose:

- turn recovered manual-vs-heuristic mismatches into concrete BCE action items
- separate repeated `false_avoided_loss` patterns from `wrong_failed_wait_interpretation`
- attach each repeated mismatch family to a recommended BCE correction step

Current status (2026-04-06):

- recovered-case casebook implemented
- bias-target extraction implemented
- current top repeated target families are `false_avoided_loss` and
  `wrong_failed_wait_interpretation`

### ET8c. Current-Rich Manual Collection Queue

Build a collection queue for the latest hint-rich current `entry_decisions.csv` window so that new
manual answer-key episodes can be gathered where heuristic evidence is already dense.

Purpose:

- avoid collecting manual truth blindly
- prioritize recent windows where barrier / wait / forecast / belief hints are already present
- keep a per-symbol capture queue for NAS / XAU / BTC

Current status (2026-04-06):

- current-rich queue implemented
- queue currently covers `2026-04-06T16:37:53` -> `2026-04-07T00:45:00`
- first queue snapshot contains 12 high-priority windows, 4 per symbol
- assistant current-rich seed draft implemented as a separate review-needed intake, not yet merged into the canonical answer-key corpus

### ET8d. Wrong Failed-Wait Gap-Aware Audit

Before shifting the remaining `wrong_failed_wait_interpretation` rows into
`failed_wait / missed_profit`, run a focused gap-aware audit on the recovered mismatch subset.

Purpose:

- isolate only the remaining `wrong_failed_wait_interpretation` rows
- separate pattern meaning from poor historical time matching
- avoid overfitting barrier bias rules to far-gap legacy matches

Rule:

- if the recovered row comes from a far or very-far historical gap, prefer collecting closer
  current-rich manual truth before editing the barrier rule
- if the row is near-gap but still numerically favors waiting, keep the current wait bias until
  recent manual truth confirms the shift

Current status (2026-04-06):

- focused audit implemented
- current remaining cases: `3`
- result:
  - `2` rows are `needs_closer_manual_truth`
  - `1` row is `keep_wait_bias_until_recent_verified`
- current conclusion: do not shift the remaining three rows directly into
  `failed_wait / missed_profit` yet; collect closer current-rich manual truth first
- current-rich proxy review implemented on the first P1 follow-up set
- review result:
  - `8` focused follow-up rows were reviewed against current `entry_decisions.csv`
  - `4` rows were explicitly kept out of canonical failed-wait promotion
  - `2` rows became `hold_review_needed` because the newest `00:00` windows still need direct chart
    confirmation
  - `2` rows remained control-only references
  - current proxy evidence still supports `correct_wait / relief_watch / wait_bias`, not an
    immediate failed-wait shift

### ET8e. Priority-Decision Hardening

Upgrade the comparison layer so that it does not stop at `match / mismatch`.

Purpose:

- classify each mismatch family into:
  - `correction_worthy`
  - `candidate_correction`
  - `freeze_worthy`
  - `hold_for_more_truth`
- score the next correction target using:
  - `frequency`
  - `severity`
  - `current-rich reproducibility`
  - `evidence quality`
  - `correction cost`
- produce a practical `P1 / P2 / P3 / hold` priority output

Rule:

- do not edit a rule only because a mismatch exists
- edit only when the mismatch remains meaningful after evidence-quality and current-rich checks

Current status (2026-04-06):

- implemented in the comparison template and live comparison outputs
- comparison template and latest comparison outputs now include:
  - evidence-quality columns
  - correction/freeze classification columns
  - scoring columns
  - recommended next-action columns
- family-ranking output is now implemented as:
  - `data/manual_annotations/manual_vs_heuristic_family_ranking_latest.*`
- current comparison is now used as a practical decision surface instead of a descriptive table only

### ET8f. Current-Rich Draft Canonical Promotion Gate

Define an explicit promotion gate between the review-needed current-rich draft and the canonical
manual answer-key corpus.

Purpose:

- prevent automatic draft-to-canonical leakage
- keep the canonical corpus stable
- promote only rows that are useful for calibration and reliably reviewed

Promotion conditions:

- manual review complete
- confidence at least `medium`
- episode coordinates sufficiently filled
- interpretation stable under re-review
- real calibration value against heuristic output

Current status (2026-04-06):

- implemented as an explicit gate report:
  - `data/manual_annotations/manual_current_rich_promotion_gate_latest.*`
- implemented review workflow companion:
  - `data/manual_annotations/manual_current_rich_review_workflow_latest.*`
- implemented review trace companion for the highest-priority batch:
  - `data/manual_annotations/manual_current_rich_review_trace_latest.*`
- current-rich draft remains separate from canonical truth
- no automatic canonical merge is allowed
- gate output now combines:
  - draft row review status
  - current-rich queue value
  - follow-up review results
  - episode detail completeness
- current rule remains:
  - `review-needed` draft rows do not auto-promote
  - follow-up review can explicitly reject canonical promotion
- gate outputs now also carry:
  - review priority tier
  - promotion decision reason
  - promotion reviewer / reviewed-at trace when available
  - blocking reason and follow-up-needed fields for canonical promotion review
- review workflow now groups those rows into explicit human-review batches and makes required trace
  fields visible before any canonical merge action
- review trace sheet now materializes the current `review_batch_p1` (or highest available batch) into
  a fillable trace scaffold before any promotion decision is applied

### ET8g. Next Mismatch Family Selection

Choose the next BCE correction target by explicit scoring rather than intuition.

Purpose:

- stop hopping between mismatch families by feel
- rank the next target using repeatability, severity, evidence quality, and correction cost
- keep freeze-worthy families from repeatedly re-opening rule edits

Selection rule:

- pick the highest-ranking `correction_worthy` family first
- keep `freeze_worthy` families documented but not edited

Current status (2026-04-06):

- `wrong_failed_wait_interpretation` is currently treated as `freeze / hold`
- next-family selection framework adopted at roadmap level and exposed in comparison scoring fields
- family-level ranking is now implemented as:
  - `data/manual_annotations/manual_vs_heuristic_family_ranking_latest.*`
- selection is now based on actual grouped outputs instead of only row-level comparison scores
- ranking outputs now expose score decomposition, including:
  - frequency
  - severity
  - evidence
  - current-rich reproducibility
  - correction cost
  - freeze-risk penalty

### ET8h. Manage CFD Calibration Watch Wiring

Wire the manual-truth calibration outputs into the main runtime supervisor so that leaving
`manage_cfd.bat` running also refreshes the calibration layer continuously.

Purpose:

- keep `barrier_outcome_bridge`, `manual_vs_heuristic_comparison`, recovered casebook, bias
  targets, current-rich queue, and assistant seed draft fresh while the engine runs
- make the answer-key calibration layer evolve alongside the runtime, instead of only by ad hoc
  manual script execution
- refresh derived review queues/results without auto-promoting review-needed draft rows into the
  canonical manual truth corpus

Rule:

- refresh comparison and bias outputs automatically
- do not auto-merge `review-needed` draft rows into canonical answer-key truth
- keep manual truth collection/review human-gated even when downstream reports refresh

Current status (2026-04-06):

- implemented as `scripts/manual_truth_calibration_watch.py`
- wired into `manage_cfd.bat` start/start_core/status/stop lifecycle
- runs every 15 minutes with the same runtime-fresh guard used by the candidate watch
- uses mixed cadence so that heavy diagnostics do not block the live loop:
  - every cycle: comparison, recovered casebook, bias targets, current-rich queue, seed draft,
    wrong-failed-wait audit/review queue/review results
  - every 4 cycles: barrier outcome bridge refresh
  - every 24 cycles: archive scan and global detail fallback audit
- current auto-refresh scope:
  - `barrier_outcome_bridge_latest.*`
  - `manual_vs_heuristic_archive_scan_latest.*`
  - `manual_vs_heuristic_global_detail_fallback_audit_latest.*`
  - `manual_vs_heuristic_comparison_latest.*`
  - `manual_vs_heuristic_family_ranking_latest.*`
  - `manual_vs_heuristic_recovered_casebook_latest.*`
  - `manual_vs_heuristic_bias_targets_latest.*`
  - `manual_vs_heuristic_current_rich_queue_latest.*`
  - `manual_current_rich_seed_draft_latest.csv`
  - `manual_current_rich_promotion_gate_latest.*`
  - `manual_current_rich_review_workflow_latest.*`
  - `manual_current_rich_review_trace_latest.*`
  - `manual_truth_corpus_freshness_latest.*`
  - `manual_truth_corpus_coverage_latest.*`
  - `manual_vs_heuristic_bias_sandbox_latest.*`
  - `manual_vs_heuristic_wrong_failed_wait_audit_latest.*`
  - `manual_current_rich_wrong_failed_wait_review_queue_latest.*`
  - `manual_current_rich_wrong_failed_wait_review_results_latest.*`
- this loop refreshes the calibration outputs, not the canonical answer-key truth itself

### ET8i. Manual Truth Corpus Freshness Audit

Measure whether the canonical manual corpus and current-rich draft stay close enough to the live
heuristic window to remain useful for calibration.

Purpose:

- make "manual truth freshness" visible by symbol
- distinguish:
  - `canonical_recent`
  - `current_rich_ready`
  - `needs_current_rich_review`
  - `stale`
- guide where more answer-key collection is needed next

Current status (2026-04-06):

- implemented as:
  - `data/manual_annotations/manual_truth_corpus_freshness_latest.*`
- calibration watch now refreshes the freshness audit automatically
- the freshness audit does not auto-promote draft rows; it only shows where review/collection
  pressure is building

### ET8j. Manual Truth Coverage Map

Expand freshness-only monitoring into a wait-family / pattern coverage map.

Purpose:

- show where canonical truth is fresh but still pattern-thin
- distinguish:
  - `dense`
  - `usable`
  - `thin`
  - `missing`
- show review pressure by family / subtype, not only by symbol time window
- guide where to:
  - review current-rich draft first
  - collect more truth
  - monitor only

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_truth_corpus_coverage_latest.*`
- coverage map now tracks:
  - canonical reviewed rows
  - assistant inferred canonical rows
  - current-rich draft rows
  - review-needed pressure
  - family/subtype pattern density
- calibration watch now refreshes the coverage map automatically

### ET8k. Bias Correction Sandbox Loop

Convert next-family ranking into a correction sandbox loop before any real BCE rule edit.

Purpose:

- turn ranked families into explicit sandbox candidates
- standardize:
  - patch hypothesis
  - patch scope
  - precheck requirements
  - validation plan
  - adoption / rejection gates
- keep `collect_more_truth` and `freeze_candidate` families inside an operational loop rather than
  leaving them as notes only

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_vs_heuristic_bias_sandbox_latest.*`
- current sandbox output now distinguishes:
  - `draft_patch_ready`
  - `review_patch_hypothesis`
  - `collect_more_truth_before_patch`
  - `freeze_track_only`
  - `casebook_monitor_only`
- calibration watch now refreshes the sandbox loop automatically

### ET8l. Patch Draft Template Layer

Turn sandbox decisions into explicit patch-draft templates before any BCE rule change is proposed.

Purpose:

- standardize the transition from sandbox ranking into a human-readable patch draft
- make `collect_more_truth_before_patch` and `freeze_track_only` operationally explicit
- keep the system from jumping directly from ranking into rule editing

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_vs_heuristic_patch_draft_latest.*`
- the top draft currently remains:
  - `truth_collection_before_patch`
  - for `wrong_failed_wait_interpretation|barrier_bias_rule|failed_wait|timing_improvement|correct_wait`
- calibration watch now refreshes the patch-draft layer automatically

### ET8m. Correction Loop Screening Log

Turn ranked families and patch drafts into explicit correction-loop candidates and run logs before
any BCE edit is accepted.

Purpose:

- standardize `candidate selection -> run decision -> before/after comparison snapshot`
- record `hold_for_more_truth`, `reject`, and future `accept` outcomes with the same schema
- keep patch readiness visible without auto-editing the live BCE rules

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_vs_heuristic_correction_candidates_latest.csv`
  - `data/manual_annotations/manual_vs_heuristic_correction_runs_latest.*`
- the current top correction loop remains:
  - `hold_for_more_truth`
  - for `wrong_failed_wait_interpretation|barrier_bias_rule|failed_wait|timing_improvement|correct_wait`
- calibration watch now refreshes the correction-loop layer automatically

### ET8n. Post-Promotion Audit Queue

Audit current-rich rows after they are promoted toward canonical so that promotion is not treated
as the end of review.

Purpose:

- schedule short/long follow-up audits after promotion
- overlay canonical rows with comparison evidence after promotion
- record `keep_canonical`, `needs_relabel`, `needs_note_update`, or `demote_from_canonical`

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_current_rich_post_promotion_audit_entries.csv`
  - `data/manual_annotations/manual_current_rich_post_promotion_audit_latest.*`
- the current queue is still empty because no current-rich row has been promoted into canonical yet
- calibration watch now refreshes the post-promotion audit layer automatically

### ET8o. Ranking Retrospective

Measure whether family-ranking priorities were actually useful after follow-up actions are taken.

Purpose:

- turn family ranking into a scored decision system with retrospective feedback
- record whether a ranked family was a `correct_priority`, `false_priority`, or `needed_more_truth`
- expose ranking precision and false-priority rates

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_vs_heuristic_family_ranking_retrospective_entries.csv`
  - `data/manual_annotations/manual_vs_heuristic_family_ranking_history_latest.csv`
  - `data/manual_annotations/manual_vs_heuristic_family_ranking_retrospective_latest.*`
- current v0 derives retrospective results from correction-run decisions when explicit review
  entries are still empty
- calibration watch now refreshes the ranking retrospective layer automatically

### ET8p. Draft / Validated / Canonical Promotion Discipline

Separate current-rich rows into `draft`, `validated`, and `canonical` states before and after merge.

Purpose:

- add an explicit validated layer between raw draft and canonical answer key
- make canonical merge trace fields first-class operational data
- keep merge timing, reviewer identity, and merge batch reasons visible

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_current_rich_canonical_merge_entries.csv`
  - `data/manual_annotations/manual_current_rich_promotion_discipline_latest.*`
- current rows mostly remain `validated_not_merged` or `draft_only` because no current-rich row has
  been merged into canonical yet
- calibration watch now refreshes the promotion-discipline layer automatically

### ET8q. Manual Calibration Approval Log

Collect promotion, correction-loop, and post-promotion audit decisions into one approval log.

Purpose:

- keep human-in-the-loop decisions traceable across the full calibration workflow
- show why rows were held, rejected, or accepted for follow-up
- prepare the ground for future semi-automatic approval queues without auto-editing rules

Current status (2026-04-07):

- implemented as:
  - `data/manual_annotations/manual_calibration_approval_log.csv`
  - `data/manual_annotations/manual_calibration_approval_log_latest.md`
- current rows are dominated by:
  - `promotion_gate_review`
  - `correction_loop_accept_reject`
- no post-promotion audit approval event exists yet because no current-rich row has reached canonical
- calibration watch now refreshes the approval-log layer automatically

### ET8r. Shadow Auto Transition Bridge

Use the completed calibration surfaces as the input layer for a non-live shadow automation system.

Purpose:

- keep calibration outputs actionable without directly editing live rules
- run correction candidates in shadow first
- compare baseline vs shadow before any bounded apply discussion
- preserve the human approval gate while increasing automation quality

Rule:

- shadow automation may auto-run
- live execution may not be directly altered from shadow results
- bounded promotion remains explicit and human-reviewed

Current status (2026-04-07):

- adopted as the next strategic layer
- detailed design added:
  - `docs/current_shadow_auto_system_design_ko.md`
- implementation roadmap added:
  - `docs/current_shadow_auto_system_implementation_roadmap_ko.md`
- SA1 runtime mode contract implemented:
  - `data/analysis/shadow_auto/shadow_runtime_modes_latest.csv`
- SA2 calibration-to-shadow candidate bridge implemented:
  - `data/analysis/shadow_auto/shadow_candidates_latest.csv`
- SA3 baseline-vs-shadow storage implemented:
  - `data/analysis/shadow_auto/shadow_vs_baseline_latest.csv`
- SA4 shadow evaluation implemented:
  - `data/analysis/shadow_auto/shadow_evaluation_latest.csv`
- SA4a/SA4b semantic training bridge adapter implemented:
  - `data/analysis/shadow_auto/semantic_shadow_training_bridge_adapter_latest.csv`
  - `data/analysis/shadow_auto/semantic_shadow_bundle_bootstrap_latest.csv`
- the current calibration system should be treated as the prerequisite layer for shadow rollout

## ET9. Annotation Burden Guardrail

Keep the human workflow lightweight.

Required:

- `anchor_time`
- `anchor_price`
- `manual_wait_teacher_label`

Strongly recommended:

- `ideal_entry_time`
- `ideal_entry_price`
- `ideal_exit_time`
- `ideal_exit_price`

Optional:

- `manual_entry_teacher_label`
- `manual_exit_teacher_label`

## Recommended Order

1. `ET0 Scope Lock`
2. `ET1 Episode Backbone`
3. `ET2 Coordinate Promotion`
4. `ET3 Wait-Channel Stability`
5. `ET4 Entry Truth Candidate Fields`
6. `ET5 Exit Truth Candidate Fields`
7. `ET6 Importer v1`
8. `ET7 Entry / Exit Expansion`
9. `ET8 Manual vs Heuristic Comparison Report`
10. `ET8a Heuristic Evidence Recovery Audit`
11. `ET8b Recovered-Case Bias Target Extraction`
12. `ET8c Current-Rich Manual Collection Queue`
13. `ET8d Wrong Failed-Wait Gap-Aware Audit`
14. `ET8e Priority-Decision Hardening`
15. `ET8f Current-Rich Draft Canonical Promotion Gate`
16. `ET8g Next Mismatch Family Selection`
17. `ET8h Manage CFD Calibration Watch Wiring`
18. `ET8i Manual Truth Corpus Freshness Audit`
19. `ET8j Manual Truth Coverage Map`
20. `ET8k Bias Correction Sandbox Loop`
21. `ET8l Patch Draft Template Layer`
22. `ET8m Correction Loop Screening Log`
23. `ET8n Post-Promotion Audit Queue`
24. `ET8o Ranking Retrospective`
25. `ET8p Draft / Validated / Canonical Promotion Discipline`
26. `ET8q Manual Calibration Approval Log`
27. `ET8r Shadow Auto Transition Bridge`

## Stop Conditions

Stop and re-evaluate if:

- the wait-first loop becomes ambiguous
- annotation burden rises too quickly
- importer v1 starts depending on entry/exit labels to function
- current manual wait truth can no longer be interpreted cleanly

## Short Conclusion

The roadmap does not replace manual wait truth.

It gives manual wait truth a durable home inside a larger episode model so that future
entry/exit truth can grow without rebuilding the dataset from scratch, while also giving
the current heuristic owners an answer-key comparison layer.
