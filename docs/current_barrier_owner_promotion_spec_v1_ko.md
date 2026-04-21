# Barrier Owner Promotion Spec v1

## 2026-04-04 Post-BCE7 Follow-up

Barrier is no longer only in coverage bootstrap mode.
The next detailed work is now `bias correction` inside the BCE track.

This means:

- do not lower readiness thresholds first
- keep `strict / usable / skip` usage boundaries stable
- correct `avoided_loss` over-concentration before asking for more live authority
- refine action normalization before over-reading drift mismatch

Detailed follow-up:

- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)
- [current_wait_family_label_structure_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wait_family_label_structure_v1_ko.md)
- [current_manual_wait_teacher_truth_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_wait_teacher_truth_spec_v1_ko.md)
- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)

### Wait-Family Overlay Rule

Barrier main labels stay as the primary outcome surface:

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`
- `relief_success`
- `relief_failure`

Bias correction follow-up may add `wait-family` as a diagnostic overlay, but not as a replacement.

- `missed_profit_leaning` -> `failed_wait / wait_but_missed_move`
- `zero_entry_gain_no_continuation` -> `failed_wait / wait_without_timing_edge`
- `small_continuation_avoided_loss` -> `neutral_wait / small_value_wait`

The wait-family overlay is initially `diagnostic/usable` only and should not be used as a hard gate.

### Manual Good-Wait Teacher Truth Rule

Barrier heuristics should not be stretched first to manufacture `good wait`.
When a human chart review is available, keep it as a separate teacher-truth layer:

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

This layer does not replace:

- barrier main labels
- wait-family diagnostic overlay

It exists as a human-defined truth surface for later bias correction and teacher review.

### Manual Answer-Key Calibration Layer

The manual truth layer should now be interpreted as:

- a standalone teacher corpus
- an ideal / counterfactual answer key
- an external calibration surface for barrier and wait-family heuristics

This means:

- closed-history matching is optional
- matching failure is not a barrier-owner blocker
- the next meaningful artifact is a manual-vs-heuristic comparison report

Reference:

- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

### Episode-First Manual Truth Note

Barrier should consume manual truth in a wait-first way for now,
but the storage model should already preserve one full `trade episode`.

That episode may later expose:

- entry truth
- wait truth
- exit truth

without rebuilding older annotations.

## 2026-04-04 Coverage Engineering Update

`BR0~BR6` means the promotion chain is connected.
It does not mean barrier is ready for live authority.

The next bottleneck is:

- low usable label coverage
- unclear top skip reasons
- unstable `correct_wait` vs `overblock` boundary
- missing counterfactual audit against the actual engine

Immediate detailed follow-up:

- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)

### Barrier Label Usage Boundary

Barrier outcome confidence should now be operationally read as:

- `high` / `medium`: strict rows, compare/gate usable
- `weak_usable`: baseline/diagnostic usable
- `low_skip`: replay-only / coverage-only

Barrier coverage work should grow usable rows without relaxing no-leakage rules.

## 2026-04-04 BR0/BR1 Checklist

- `BR0 scope freeze`
  - `Barrier = blocking / relief / veto cost owner`로 고정
  - runtime direct-use field와 learning-only field를 분리
  - future outcome / closed-history label은 runtime direct-use field에 섞지 않음
- `BR1 runtime bridge`
  - `barrier_state25_runtime_bridge_v1`
  - `barrier_runtime_summary_v1`
  - `barrier_input_trace_v1`
- 이번 단계는 nested bridge 배선까지만 포함한다
  - flat live hint/action field는 아직 열지 않음
  - `log_only -> canary -> bounded_live`는 BR6 이후 단계에서 다룸

## 목적

이 문서는 `Barrier`를 runtime blocking owner에서
`replay / seed / baseline / candidate / log_only`까지 닫히는 learning owner로 승격하기 위한
실무 명세서다.

핵심 목표는 세 가지다.

1. `Barrier`가 맡는 질문과 금지 범위를 고정한다.
2. `avoided_loss / missed_profit / correct_wait / overblock / relief_success / relief_failure`
   라벨을 수식 수준으로 정의한다.
3. `차단 이유`보다 더 중요한 `차단 비용`을 결과 라벨과 같이 남긴다.

## 현재 owner 계약

현재 코드 기준 `Barrier`의 역할은 이미 분명하다.

- 생성: [barrier_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/barrier_engine.py)
- 출력 타입: [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py#L425)
- 런타임 조립: [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py#L1533)

코드상 계약:

- semantic contract: `barrier_blocking_only_v1`
- role statement: `Barrier decides whether the current candidate should be blocked now.`

즉 `Barrier`는 이미 코드상으로도 `blocking and relief only owner`다.

## Barrier가 맡는 질문

`Barrier`는 아래 질문만 맡는다.

1. 지금 thesis가 좋아 보여도 실제 행동을 막아야 하는가
2. 지금 막는 이유가 conflict / middle chop / liquidity / direction policy / event risk 중 무엇인가
3. 지금 relief를 주어도 되는가
4. 이 block 또는 relief가 결과적으로 좋은 veto였는가, 과잉 veto였는가

한 줄로 줄이면:

`Barrier = blocking / relief / veto cost owner`

## Barrier가 하면 안 되는 일

아래는 금지다.

1. `scene`을 새로 정의하기
2. `forecast`처럼 앞으로의 branch를 예측하기
3. `belief`처럼 thesis persistence를 계산하기
4. 직접 방향 thesis를 만들기
5. 최종 action을 단독으로 결정하기
6. future outcome을 runtime direct-use field로 직접 쓰기

즉 `Barrier`는 entry creator가 아니라 veto owner다.

## 현재 runtime canonical fields

현재 런타임에서 직접 쓰는 canonical field는 아래로 고정한다.

- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

metadata에서 현재 직접 참조 가능한 보조 필드는 아래로 본다.

- `edge_turn_relief_score`
- `breakout_fade_barrier_score`
- `execution_friction_barrier_score`
- `event_risk_barrier_score`

이 필드들은 [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py#L425) 와
[barrier_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/barrier_engine.py) 기준으로 현재 코드와 일치한다.

## learning-only derived fields

아래 필드는 replay/seed용 파생 필드다.

- `barrier_anchor_side`
- `barrier_anchor_context`
- `barrier_total`
- `barrier_relief_total`
- `barrier_blocked_flag`
- `barrier_relief_executed`
- `barrier_cost_loss_avoided_r`
- `barrier_cost_profit_missed_r`
- `barrier_cost_wait_value_r`
- `barrier_outcome_label`
- `barrier_label_confidence`
- `barrier_horizon_bars`
- `barrier_outcome_reason`
- `barrier_conflict_margin_score`

주의:

- 이 필드들은 runtime decision feature로 직접 넣지 않는다.
- replay / seed / candidate compare / log-only trace 전용이다.

## anchor와 판정 단위

Barrier 라벨은 `barrier audit snapshot` 단위로 찍는다.

각 snapshot은 아래 5개로 고정한다.

- `scene_id`
- `signal_bar_ts` 또는 `decision_ts`
- `barrier_anchor_side`
- `barrier_anchor_context`
- `barrier_blocked_flag`

### barrier_anchor_side

- `BUY`
- `SELL`

### barrier_anchor_context

- `entry_block`
  - 새 entry candidate를 직접 막은 상황
- `wait_block`
  - 바로 진입 대신 기다리게 만든 상황
- `relief_release`
  - 기존 barrier를 완화하거나 release한 상황

## lookahead horizon 규칙

Barrier 라벨은 아래 고정 horizon을 사용한다.

- `short_horizon = 3 bars`
- `mid_horizon = 6 bars`
- `long_horizon = 12 bars`

v1 기본 판정 horizon은 `mid_horizon = 6 bars`로 한다.

### horizon 사용 원칙

1. 기본 판정은 anchor 이후 `6 bars`까지만 본다.
2. trade가 그 전에 종료되면 종료 시점까지만 본다.
3. `6 bars`를 넘는 미래 데이터는 v1 판정에 쓰지 않는다.
4. 미래 bar coverage가 `70%` 미만이면 `low confidence` 또는 `skip` 처리한다.

## leakage 금지 규칙

아래 규칙은 강제다.

1. `closed trade final pnl`, `wait_quality final label`, `economic_target final label`은
   runtime direct-use field로 쓰지 않는다.
2. Barrier 라벨 생성은 anchor 이후 `6 bars` 이내 미래 데이터만 쓴다.
3. `6 bars`를 넘는 장기 결과는 v1 barrier label 생성에 쓰지 않는다.
4. `label_confidence = low`인 row는 candidate compare 기본 집계에서 제외한다.

한 줄로 줄이면:

`Barrier outcome은 미래를 써서 평가할 수 있지만, 현재 barrier feature로 직접 넣을 수는 없다.`

## reference unit 정의

Barrier 판정도 절대 가격 차보다 정규화된 move를 쓴다.

v1 reference unit `R`은 아래 우선순위로 정의한다.

1. `expected_adverse_depth`
2. `signal_bar_range`
3. `instrument_min_runtime_range floor`

모든 cost는 `R-multiple`로 환산한다.

예:

- `CF_F_6 = blocked side 기준 6 bars 내 favorable move / R`
- `CF_A_6 = blocked side 기준 6 bars 내 adverse move / R`

## 핵심 파생 지표

각 anchor snapshot에서 아래 파생값을 계산한다.

- `CF_F_3`, `CF_F_6`
- `CF_A_3`, `CF_A_6`
- `BetterEntryGain_6`
- `Release_F_6`
- `Release_A_6`
- `BarrierStay_3`
- `BarrierRelease_3`

### CF 정의

`CF`는 counterfactual move다.

- block이 없었다면 anchor side로 진입했다고 가정하고
- 그 방향 기준 favorable/adverse excursion을 계산한다.

### BetterEntryGain_6 정의

Barrier가 즉시 진입을 막고 기다리게 한 경우,
나중에 더 좋은 가격이 나왔는지를 `R` 기준으로 계산한다.

- `BUY`: `anchor_price - better_later_entry_price`
- `SELL`: `better_later_entry_price - anchor_price`

이를 `R`로 나눈 값을 `BetterEntryGain_6`로 둔다.

### Release_F_6 / Release_A_6 정의

Barrier relief가 실제로 발생한 경우,
release 시점 이후 6 bars 내 favorable / adverse excursion을 측정한다.

## cost 개념

Barrier는 이유만 기록하면 안 되고, 비용도 기록해야 한다.

v1에서는 아래 세 cost를 남긴다.

- `barrier_cost_loss_avoided_r`
- `barrier_cost_profit_missed_r`
- `barrier_cost_wait_value_r`

### cost 계산식

#### loss_avoided_r

```text
loss_avoided_r = max(0, CF_A_6 - 0.40)
```

의미:

- 막지 않았다면 최소 `0.40R` 이상은 불편한 adverse가 나온 구간을
  loss avoided 후보로 본다.

#### profit_missed_r

```text
profit_missed_r = max(0, CF_F_6 - max(0.40, CF_A_6 * 0.50))
```

의미:

- favorable move가 컸고 adverse가 상대적으로 얕았으면
  barrier가 profit을 놓친 비용으로 본다.

#### wait_value_r

```text
wait_value_r = max(0, BetterEntryGain_6 - 0.15)
```

의미:

- barrier가 즉시 entry를 막았지만, 결과적으로 더 좋은 entry 가격을 만들었으면
  wait value로 본다.

## 라벨 도메인

Barrier 라벨은 모든 row에 찍지 않는다.

### block-family 라벨 후보

아래 조건일 때만 평가:

- `barrier_anchor_context = entry_block` 또는 `wait_block`
- `barrier_blocked_flag = true`

대상 라벨:

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`

### relief-family 라벨 후보

아래 조건일 때만 평가:

- `barrier_anchor_context = relief_release`
  또는
- `barrier_relief_executed = true`

대상 라벨:

- `relief_success`
- `relief_failure`

## 라벨 판정 규칙

아래 규칙은 v1 고정 규칙이다.

### 1. avoided_loss

다음 조건을 모두 만족하면 `avoided_loss`.

- `CF_A_6 >= 1.00`
- `CF_F_6 < 0.50`
- `BetterEntryGain_6 < 0.35`
- `barrier_blocked_flag = true`

추가 강화 조건:

- `CF_A_3 >= 0.80` and `CF_F_6 < 0.30`면 `high confidence`

### 2. correct_wait

다음 조건을 모두 만족하면 `correct_wait`.

- `barrier_blocked_flag = true`
- `CF_A_3 >= 0.50`
- `BetterEntryGain_6 >= 0.35`
- later same-thesis re-entry 또는 relief가 관측됨
- 이후 favorable continuation이 `0.60R` 이상

추가 강화 조건:

- `BetterEntryGain_6 >= 0.50` and later favorable continuation `>= 0.80R`면 `high confidence`

### 3. missed_profit

다음 조건을 모두 만족하면 `missed_profit`.

- `barrier_blocked_flag = true`
- `CF_F_6 >= 1.00`
- `CF_A_6 <= 0.50`
- `BetterEntryGain_6 < 0.25`

추가 강화 조건:

- `CF_F_6 >= 1.25` and `CF_A_6 <= 0.35`면 `high confidence`

### 4. overblock

다음 조건을 모두 만족하면 `overblock`.

- `barrier_blocked_flag = true`
- `barrier_total >= 0.65`
- `CF_F_6 >= 1.25`
- `CF_A_6 <= 0.40`
- `BetterEntryGain_6 < 0.20`

추가 강화 조건:

- `barrier_total >= 0.75` and `CF_F_6 >= 1.50`면 `high confidence`

### 5. relief_success

다음 조건을 모두 만족하면 `relief_success`.

- `barrier_relief_executed = true`
- `Release_F_6 >= 0.75`
- `Release_A_6 <= 0.60`

추가 강화 조건:

- `Release_F_6 >= 1.00` and `Release_A_6 <= 0.40`면 `high confidence`

### 6. relief_failure

다음 조건을 모두 만족하면 `relief_failure`.

- `barrier_relief_executed = true`
- `Release_A_6 >= 0.80`
- `Release_F_6 < 0.50`

추가 강화 조건:

- `Release_A_6 >= 1.00` and `Release_F_6 < 0.30`면 `high confidence`

## 충돌 해결 규칙

Barrier 라벨은 하나만 남긴다.

기본 precedence는 아래로 고정한다.

1. `relief_failure`
2. `relief_success`
3. `overblock`
4. `missed_profit`
5. `correct_wait`
6. `avoided_loss`

### conflict margin score

같은 family 안에서 두 라벨이 동시에 가까우면 아래 margin score를 같이 본다.

#### score_avoided_loss

```text
score_avoided_loss = CF_A_6 - CF_F_6
```

#### score_missed_profit

```text
score_missed_profit = CF_F_6 - CF_A_6
```

#### score_correct_wait

```text
score_correct_wait = BetterEntryGain_6 + min(CF_A_3, 0.75) - max(0, CF_A_6 - CF_A_3)
```

#### score_overblock

```text
score_overblock = score_missed_profit + max(0, barrier_total - 0.65)
```

#### score_relief_success

```text
score_relief_success = Release_F_6 - Release_A_6
```

#### score_relief_failure

```text
score_relief_failure = Release_A_6 - Release_F_6
```

### 적용 원칙

1. 먼저 precedence를 본다.
2. 같은 family에서 두 라벨이 모두 만족하고 gap이 `0.15R` 미만이면 margin score로 결정한다.
3. margin score도 근접하면 `low confidence`로 내리고 skip 가능하다.

## confidence 규칙

### high

- 핵심 조건 충족
- 반대 라벨 margin이 충분히 큼
- future bar coverage `>= 90%`

### medium

- 핵심 조건 충족
- future bar coverage `>= 70%`
- competing label과 gap이 좁지만 precedence가 명확

### low

- coverage 부족
- competing label이 동시 근접
- `R` 계산 불안정
- barrier_total / relief metadata 누락

### skip 규칙

아래는 `skip_candidate = true`로 둔다.

- `barrier_label_confidence = low`
- coverage `< 70%`
- `R` 계산 실패
- `barrier_anchor_side` 불명확
- `barrier_total` 또는 relief trace 누락

## edge case 규칙

### 1. session close / market halt

- horizon 안에 장이 닫히면 `coverage shortfall`
- 기본은 `low confidence`
- 심하면 skip

### 2. later relief but no execution

- relief signal이 있었어도 실제 실행 후보가 안 생기면 `correct_wait` 확정으로 보지 않는다
- `wait_only_unconfirmed_relief` reason을 남기고 medium 이하로 제한

### 3. strong barrier + external policy block

- 외부 정책 강제 block이 있으면 Barrier owner 단독 성공/실패로 보지 않는다
- `external_policy_block` reason을 남기고 low confidence 또는 skip 처리 가능

### 4. multi-barrier overlap

- `conflict_barrier`, `liquidity_barrier`, `direction_policy_barrier`가 동시에 높으면
  component attribution을 metadata에 남긴다
- 라벨은 하나만 찍되, `barrier_outcome_reason`에는 top 2 component를 기록한다

## 실패 모드

Barrier owner의 핵심 실패 모드는 아래로 고정한다.

- `overblock`
  - 좋은 move를 과하게 막음
- `underblock`
  - 막았어야 할 손실을 못 막음
- `false_relief`
  - 너무 이른 relief
- `late_relief`
  - release가 늦어 기회를 놓침

이 실패 모드는 라벨과 1:1 매핑은 아니지만 replay report에서 같이 본다.

## 최소 관측 지표

Barrier 승격 중 최소로 봐야 하는 지표는 아래다.

- `overblock_ratio`
- `avoided_loss_rate`
- `missed_profit_rate`
- `correct_wait_rate`
- `relief_failure_rate`
- `loss_avoided_r_mean`
- `profit_missed_r_mean`
- `component_skew_by_scene`

## 승격 중단 조건

아래는 hard stop 조건이다.

1. `low confidence share > 0.35`
2. `overblock_ratio`가 baseline 대비 `20%` 이상 급증
3. `avoided_loss_rate`는 올랐는데 `profit_missed_r_mean`이 더 크게 증가
4. `relief_failure_rate > 0.25`
5. `component_skew_by_scene`가 특정 scene과 component에 과도하게 쏠림

## Bridge / Seed / Baseline / Candidate / Overlay 설계

### BR0. Scope Freeze

- owner 역할 고정
- direct-use / learning-only field 분리
- leakage 규칙 고정

### BR1. Runtime Bridge

산출물:

- `barrier_state25_runtime_bridge_v1`
- `barrier_runtime_summary_v1`

포함:

- scene 힌트
- barrier canonical field
- anchor side
- anchor context
- top component reason

### BR2. Replay / Outcome Bridge

산출물:

- `barrier_outcome_bridge_v1`

포함:

- `CF_F_3 / CF_F_6 / CF_A_3 / CF_A_6`
- `BetterEntryGain_6`
- `Release_F_6 / Release_A_6`
- cost estimate
- 라벨
- confidence
- reason

### BR3. Closed-History Seed Enrichment

추가 seed 컬럼 초안:

- `barrier_outcome_label`
- `barrier_label_confidence`
- `barrier_primary_component`
- `barrier_cost_loss_avoided_r`
- `barrier_cost_profit_missed_r`
- `barrier_cost_wait_value_r`
- `barrier_anchor_context`
- `barrier_outcome_reason`

### BR4. Baseline Auxiliary Task

목표:

- current scene/state/evidence/belief/forecast로 `barrier_outcome_label` 예측

skip 조건:

- high/medium confidence 유효 row < `40`
- class support min < `8`

### BR5. Candidate Compare Integration

compare summary에 최소 반영:

- `overblock_ratio_delta`
- `avoided_loss_rate_delta`
- `missed_profit_rate_delta`
- `relief_failure_rate_delta`
- `profit_missed_r_mean_delta`

candidate 판정 원칙:

- Barrier는 v1에서 hard blocker보다 warning/soft blocker 위주
- 단 `overblock` 급증과 `relief_failure` 급증은 hard stop 가능

### BR6. Log-only Overlay

live 행동을 바꾸지 않고 아래 trace만 남긴다.

- `barrier_recommended_action_family`
  - `block_bias`
  - `wait_bias`
  - `relief_watch`
  - `relief_release_bias`
- `barrier_overlay_reason_codes`
- `barrier_overlay_confidence`
- `barrier_overlay_cost_hint`

## v1 완료 기준

아래가 되면 Barrier owner v1은 닫힌 것으로 본다.

1. 라벨 규칙이 문서와 코드에서 일치한다
2. `barrier_outcome_bridge_v1`가 실제 로그를 생성한다
3. closed-history에 seed 컬럼이 backfill된다
4. baseline auxiliary가 sparse/ready를 구분해 돈다
5. candidate compare가 Barrier 구조 KPI를 읽는다
6. live에는 `log_only` trace까지만 붙는다

## 한 줄 결론

Barrier owner v1의 핵심은 `왜 막았는가`를 넘어서,
`막아서 무엇을 지켰고 무엇을 놓쳤는지`를 정규화된 비용과 결과 라벨로 고정하는 것이다.
