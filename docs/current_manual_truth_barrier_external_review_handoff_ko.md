# Current Manual Truth / Barrier External Review Handoff

## Purpose

This document is a compact external-review handoff for the current project state.

It explains:

- where the total roadmap currently sits
- how the project reached this point
- what has already been fixed or frozen
- what is still open
- what questions are worth asking another model now

The goal is not to restate every implementation detail.
The goal is to give another reviewer the minimum accurate context needed to advise on the next step.

## One-Line Summary

The project is no longer primarily in the "build new semantic owners" phase.

It is now in the phase of:

- using manual truth as a higher answer-key layer
- comparing that answer key against heuristic barrier / wait-family interpretation
- deciding which heuristic mismatches deserve real rule edits and which should be held until newer evidence exists

## Overall Roadmap Position

The full project can be read in four layers.

### 1. Execution Layer

- the legacy execution engine still owns live entry / wait / exit
- this remains the actual live execution owner

### 2. Semantic Owner Layer

- `state25`
- `forecast`
- `belief`
- `barrier`

These have been raised on the common promotion path:

`runtime -> replay/outcome -> seed enrichment -> baseline auxiliary -> candidate compare/gate -> log_only`

### 3. Barrier Bias / Wait-Family Layer

Barrier is already beyond its initial owner-promotion stage.

The project has already gone through:

- `BR0~BR6` owner promotion
- `BCE0~BCE13` core coverage / audit / readiness work
- `wait-family` diagnostic opening

Barrier is no longer missing structure.
The current issue is interpretation quality and answer-key comparison.

### 4. Manual Truth / Answer-Key Layer

This is the newest major layer.

Manual truth is treated as:

- a standalone answer key
- not replay reconstruction
- not direct training seed by default

This layer exists to judge heuristic owners from above.

## Current Roadmap Status

### Semantic Owner Track

Current interpretation:

- owner promotion is substantially advanced
- this is not the main current bottleneck

Practical status:

- `BR0~BR6` can be considered done
- `barrier` already has runtime/replay/seed/baseline/candidate/log-only continuity

### Barrier Bias Correction Track

Current interpretation:

- the barrier structure is already in place
- the current task is not "build barrier"
- the current task is "measure and correct heuristic interpretation using manual truth"

Practical status:

- `BCE8~BCE16` direction has already been formalized
- comparison, recovery, bias-target extraction, and current-rich collection are active

### Manual Truth Track

Current interpretation:

- storage = `episode-first`
- operations = `wait-first`

Practical status:

- `manual_wait_teacher` is the first active truth channel
- entry/exit coordinates already exist as episode-level truth coordinates
- full `manual_entry_teacher` / `manual_exit_teacher` operations are still deferred

This means:

- future expansion is prepared
- but current operations stay focused on wait / barrier correction

## How The Project Reached This Point

The recent path matters because the current conclusions are the result of several narrowing steps.

### Step 1. Barrier structure was completed first

The project did not jump from structure into live tuning.

Instead, it first completed:

- runtime bridge
- replay bridge
- seed enrichment
- baseline auxiliary
- compare/gate integration
- log-only hint path

This established barrier as a real owner, not just a score.

### Step 2. Coverage and audit work exposed a deeper issue

After the barrier wiring was complete, the next bottleneck was not missing architecture.

It was:

- weak label coverage
- skipped interpretation
- strong `avoided_loss` bias
- weak `correct_wait` presence

That led to BCE coverage engineering and then bias correction.

### Step 3. Wait-family was opened instead of force-expanding `correct_wait`

Instead of making `correct_wait` artificially wide, the system opened a separate diagnostic layer:

- `timing_improvement`
- `protective_exit`
- `reversal_escape`
- `neutral_wait`
- `failed_wait`

This preserved the original barrier labels while creating a better diagnostic surface.

### Step 4. Manual truth was opened above the heuristic layer

The project then recognized that some waits are easier to judge from charts than from heuristic rules alone.

That led to:

- episode-first storage
- wait-first operations
- manual wait truth corpus

This was a major conceptual shift.
Manual truth stopped being treated like replay reconstruction and became an answer key.

### Step 5. Comparison and evidence-recovery work narrowed the mismatch set

The project built:

- manual vs heuristic comparison
- paired legacy detail fallback audit
- global detail fallback audit
- archive scan
- recovered-case casebook
- bias targets

That revealed that many "unknown" comparisons were not logic failures.
They were historical evidence coverage problems in old CSV schemas.

Rotate-detail fallback recovered enough evidence to make a meaningful subset review possible.

### Step 6. The remaining P1 mismatch family was isolated

After the earlier `false_avoided_loss` and protective-interpretation issues were reduced, the main remaining family became:

- `wrong_failed_wait_interpretation`

That family was then audited separately.

### Step 7. The remaining failed-wait shift was deliberately held

The project did not rush another barrier rule change.

Instead, it:

- ran a gap-aware audit on the remaining 3 cases
- collected current-rich follow-up candidates
- reviewed the nearest current-rich proxies

Result:

- the remaining direct rule shift was not justified yet
- the current evidence still leaned toward `correct_wait / relief_watch / wait_bias`
- this track was frozen rather than over-tuned

## Current Artifacts And Counts

### Manual Truth Corpus

Canonical corpus:

- file: `data/manual_annotations/manual_wait_teacher_annotations.csv`
- total episodes: `105`
- symbols:
  - `NAS100 = 35`
  - `XAUUSD = 35`
  - `BTCUSD = 35`

Current interpretation:

- this is a manual answer-key corpus
- not actual replay reconstruction

### Comparison Layer

Current output:

- `manual_vs_heuristic_comparison_latest.*`

Current headline numbers:

- total manual episodes: `105`
- time-matched heuristic rows: `26`
- unmatched because of heuristic gap limit: `79`
- recovered through global rotate-detail fallback: `15`

Current comparison result:

- barrier / wait-family `match = 9`
- `mismatch = 6`
- `unknown = 90`

This means:

- the comparison surface is working
- but historical heuristic evidence is still sparse outside the recovered subset

### Current-Rich Collection

Current output:

- `manual_vs_heuristic_current_rich_queue_latest.*`
- `manual_current_rich_seed_draft_latest.csv`

Current window:

- `2026-04-06T16:37:53 -> 2026-04-07T00:45:00`

Current queue:

- 12 high-priority windows
- 4 windows per symbol

Important rule:

- the seed draft is review-needed
- it is not merged into canonical answer-key truth by default

## Current Locked Conclusions

These are the conclusions currently treated as fixed unless new evidence appears.

### 1. Manual truth is an answer key, not replay reconstruction

This is the most important current interpretation rule.

Implications:

- failed closed-history matching is not the main blocker
- comparison can exist even when executed-trade reconstruction is incomplete

### 2. Episode-first / wait-first remains the correct operating shape

Implications:

- wait stays the first operational truth channel
- entry/exit stay available as episode coordinates and future truth candidates

### 3. Barrier is not missing structure

Implications:

- current problems are interpretation and calibration problems
- not owner-promotion plumbing problems

### 4. The remaining `wrong_failed_wait_interpretation` track is currently frozen

This is the newest practical lock.

Current review result:

- the 3 recovered cases did not justify another immediate rule push
- the nearest current-rich proxies also did not justify promoting those cases into
  canonical failed-wait truth

Current practical meaning:

- do not move the barrier further toward `failed_wait / missed_profit` just because of those 3 rows
- hold the rule where it is for now

## What Has Already Been Tried

The following things have already been done and should not be proposed again as if they were still missing.

### Already Done

- episode-first manual truth schema
- wait-only importer v1
- manual truth corpus build-up
- manual vs heuristic comparison report v0
- paired legacy detail fallback audit
- global detail fallback audit
- archive scan for other historical semantic detail stores
- rotate-detail global fallback reconstruction inside the comparison service
- recovered mismatch casebook
- bias target extraction
- current-rich queue creation
- wrong-failed-wait gap-aware audit
- current-rich wrong-failed-wait follow-up review

### Already Tested And Held

- pushing the remaining failed-wait family further immediately

Current result:

- not enough evidence
- held / frozen for now

## What Is Open Now

These are the real open questions, not already-closed branches.

### Open Question 1

What should become the next main mismatch family after the current `wrong_failed_wait` freeze?

Possible directions:

- reopen the broader recovered mismatch set
- move to other barrier/wait-family misalignment classes
- focus on newer current-rich windows first

### Open Question 2

When should current-rich seed rows be promoted into canonical manual truth?

Current rule:

- not automatically
- review first

But the project still needs a stable operating rule for:

- promotion threshold
- confidence threshold
- whether chart confirmation is always required

### Open Question 3

Should the next priority be:

- more current-rich manual truth collection
- another barrier bias family
- broader heuristic evidence reconstruction
- or a higher-level evaluation pass?

## What Should Not Be Done Next

The following are currently considered bad next moves.

### 1. Do not push another failed-wait rule change immediately

The current evidence does not support it.

### 2. Do not merge review-needed current-rich seed rows into canonical truth automatically

They still need review discipline.

### 3. Do not treat closed-history matching as the primary success criterion

That is a secondary path here.

## Recommended Next Questions For External Review

If asking another model for advice, the most useful questions are:

1. Is the project right to treat manual truth as an answer-key layer above heuristic owners rather than as replay reconstruction?
2. After freezing `wrong_failed_wait_interpretation`, what mismatch family should become the next barrier bias target?
3. What promotion rule should decide whether current-rich seed rows can become canonical manual truth?
4. Should the next priority be more current-rich collection, broader comparison, or a different owner-level audit?

## Short Conclusion

The project has already moved beyond basic semantic owner construction.

It is now operating in a higher phase:

- manual answer-key construction
- heuristic comparison
- evidence recovery
- selective bias correction

The latest important decision is:

- the remaining `wrong_failed_wait` mismatch family was reviewed
- the nearest current-rich proxies did not justify another barrier rule shift
- that branch is currently frozen

So the next external advice should focus less on "how to build manual truth" and more on:

- how to use the answer key to choose the next correction target without overfitting
