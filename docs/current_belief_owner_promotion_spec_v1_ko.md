# Belief Owner Promotion Spec v1

## 2026-04-04 Reinforcement

### V1.1 Confidence Tier Clarification

Belief outcome confidence is now interpreted as four tiers:

- `high`
- `medium`
- `weak_usable`
- `low_skip`

Usage boundary:

- `high` / `medium`: strict rows, candidate-gate usable
- `weak_usable`: baseline/replay coverage rows, not for hard gate by default
- `low_skip`: replay diagnostic only

### Conflict Resolver Rule

- deterministic precedence stays primary
- precedence margin score is secondary and is used only to break near-ties
- v1 does not replace rule ordering with a pure score-max policy

### Trace / Hint Surface

`belief_input_trace_v1` and `belief_action_hint_v1` are first-class bridge artifacts.

- `belief_input_trace_v1`: explains which upstream scene / forecast / evidence / barrier context produced the belief state
- `belief_action_hint_v1`: exposes `hold_bias / wait_bias / reduce_alert / flip_alert` as log-only operational hints

### V2 Reserved Items

The following remain explicitly reserved for `v2`:

- adaptive threshold by volatility / regime
- adaptive horizon by symbol / timeframe / regime
- percentile-based calibration for confidence thresholds

### Label Utilization Policy

Belief labels must not be consumed uniformly.

- `high` / `medium`: compare/gate KPI rows
- `weak_usable`: baseline auxiliary, diagnostics, replay coverage
- `low_skip`: excluded from seed promotion by default

Recommended monitoring fields:

- `weak_usable_share`
- `weak_to_medium_conversion_rate`
- top `low_skip` reasons

### Counterfactual Audit Reminder

`belief_action_hint_v1` should not stop at recommendation logging.

The intended next audit layer is:

- actual engine action
- belief recommended family
- realized giveback / protection delta

Example questions:

- if `reduce_alert` had been followed, would giveback have decreased?
- if `wait_bias` had been followed, would adverse excursion have improved?

## 목적

이 문서는 `Belief`를 runtime persistence owner에서
`replay / seed / baseline / candidate / log_only`까지 닫히는 learning owner로 승격하기 위한
실무 명세서다.

이 문서의 목표는 세 가지다.

1. `Belief`가 무엇을 맡고 무엇을 맡지 않는지 고정한다.
2. `correct_hold / wrong_hold / correct_flip / missed_flip / premature_flip`
   라벨을 수식 수준으로 정의한다.
3. 다음 구현 단계인 `runtime bridge -> replay bridge -> seed enrichment -> baseline auxiliary -> candidate compare -> log_only trace`
   의 기준을 고정한다.

## 현재 owner 계약

현재 코드 기준 `Belief`의 역할은 이미 분명하다.

- 생성: [belief_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py)
- 출력 타입: [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py#L405)
- 런타임 조립: [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py#L1528)
- wait bias 소비: [entry_wait_belief_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_wait_belief_bias_policy.py)

코드상 계약:

- semantic contract: `belief_thesis_persistence_only_v1`
- role: `thesis_persistence_and_reconfirmation_only`

즉 `Belief`는 이미 코드상으로도 `thesis persistence owner`다.

## Belief가 맡는 질문

`Belief`는 아래 질문만 맡는다.

1. 지금 thesis가 시간축에서 유지되는가
2. confirm 쪽으로 더 가도 되는가
3. wait를 더 두는 것이 맞는가
4. 반대 thesis로 flip할 준비가 되었는가

한 줄로 줄이면:

`Belief = thesis persistence / decay / flip readiness owner`

## Belief가 하면 안 되는 일

아래는 금지다.

1. `scene` 자체를 다시 정의하기
2. `forecast`처럼 앞으로의 branch path를 새로 예측하기
3. `barrier`처럼 구조적 차단을 계산하기
4. `action`을 직접 결정하기
5. future outcome을 runtime direct-use field에 집어넣기

즉 `Belief`는 행동 owner가 아니라 persistence owner다.

## 현재 runtime canonical fields

현재 런타임에서 직접 쓰는 canonical field는 아래로 고정한다.

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `flip_readiness`
- `belief_instability`
- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`
- `transition_age`

이 필드들은 [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py#L405) 와
[belief_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py) 기준으로 현재 코드와 일치한다.

## learning-only derived fields

아래 필드는 replay/seed용 파생 필드로 사용한다.

- `belief_input_trace_v1`
- `belief_action_hint_v1`
- `belief_anchor_side`
- `belief_anchor_context`
- `active_belief`
- `active_persistence`
- `opposite_belief`
- `opposite_persistence`
- `belief_decay_rate`
- `belief_break_signature`
- `belief_outcome_label`
- `belief_label_confidence`
- `belief_horizon_bars`
- `belief_outcome_reason`

주의:

- 이 필드들은 runtime decision feature로 직접 넣지 않는다.
- replay / seed / candidate compare 전용이다.

## v1 / v2 경계

이 문서는 `v1` 기준을 고정하는 문서다.

### v1 원칙

- threshold는 고정값으로 시작한다
- horizon은 고정 `6 bars`로 시작한다
- precedence는 deterministic 규칙을 먼저 쓴다

즉 v1은 `보수적이고 재현 가능한 라벨 기준`을 먼저 세우는 단계다.

### v2 예약 항목

아래는 v2에서만 다룬다.

- `adaptive threshold`
- `adaptive horizon`
- regime / volatility percentile 기반 threshold 조정
- symbol/timeframe별 horizon ensemble

즉 `adaptive threshold/horizon`은 필요하지만, v1 라벨 규칙을 먼저 검증한 뒤 올린다.

## anchor와 판정 단위

Belief 라벨은 `belief audit snapshot` 단위로 찍는다.

각 snapshot은 아래 4개로 고정한다.

- `scene_id`
- `signal_bar_ts` 또는 `decision_ts`
- `belief_anchor_side`
- `belief_anchor_context`

### belief_anchor_side

- `BUY`
- `SELL`

### belief_anchor_context

- `entry_thesis`
  - 포지션이 없거나 add-on 직전이고, 같은 방향 진입 thesis를 보는 장면
- `hold_thesis`
  - 이미 같은 방향 포지션이 있고, 그대로 hold/reduce/exit를 고민하는 장면
- `flip_thesis`
  - 기존 thesis와 반대 방향 전환 가능성을 보는 장면

## lookahead horizon 규칙

Belief 라벨은 아래 고정 horizon을 사용한다.

- `short_horizon = 3 bars`
- `mid_horizon = 6 bars`
- `long_horizon = 12 bars`

v1 기본 판정 horizon은 `mid_horizon = 6 bars`로 한다.

### horizon 사용 원칙

1. 기본 판정은 anchor 이후 `6 bars`까지만 본다.
2. trade가 그 전에 종료되면 종료 시점까지만 본다.
3. `6 bars`를 넘는 미래 데이터는 v1 판정에 쓰지 않는다.
4. 미래 bar coverage가 `70%` 미만이면 `low confidence` 또는 `skip` 처리한다.

즉 v1은 hindsight를 줄이기 위해 `고정 horizon + 조기 종료 truncation`을 쓴다.

## leakage 금지 규칙

아래 규칙은 강제다.

1. `wait_quality`, `economic_target`, `closed trade final pnl`, `future forecast realized path`는
   runtime direct-use field로 쓰지 않는다.
2. Belief 라벨 생성은 anchor 이후 `6 bars` 이내 미래 데이터만 쓴다.
3. anchor 이후 `6 bars`를 넘는 결과나 trade close 이후 장기 결과는 v1 라벨 생성에 쓰지 않는다.
4. label confidence가 `low`인 row는 candidate compare 기본 집계에서 제외한다.

한 줄로 줄이면:

`future outcome은 Belief 라벨 생성에는 쓸 수 있지만, runtime feature로는 직접 못 쓴다.`

## reference unit 정의

Belief 판정은 절대 가격 차보다 정규화된 move로 본다.

v1 reference unit `R`은 아래 우선순위로 정의한다.

1. `expected_adverse_depth`가 있으면 그것을 사용
2. 없으면 `signal_bar_range`
3. 둘 다 없으면 `instrument_min_runtime_range floor`

모든 favorable/adverse excursion은 `R-multiple`로 정규화한다.

예:

- `F_6 = 6 bars 내 favorable move / R`
- `A_6 = 6 bars 내 adverse move / R`

## 핵심 파생 지표

각 anchor snapshot에서 아래 파생값을 계산한다.

- `F_3`, `F_6`
- `A_3`, `A_6`
- `OppConfirm_3`, `OppConfirm_6`
- `Reclaim_6`
- `belief_decay_rate`
- `belief_flip_triggered`
- `belief_flip_executed`

## belief_input_trace_v1

`Belief`를 독립 부품으로 두지 않기 위해, replay/seed에는 아래 입력 trace를 같이 남긴다.

- `scene_id`
- `state25_label`
- `state25_confidence`
- `forecast_expected_path`
- `forecast_confidence`
- `forecast_reason_codes`
- `dominant_evidence_family`
- `evidence_total`
- `evidence_conflict`
- `evidence_fragility`
- `barrier_total_hint`
- `barrier_primary_component`

원칙:

- `Belief`는 위 입력을 소비하는 owner이지, 이 입력의 의미를 다시 만들지 않는다.
- 이 trace는 replay/seed/candidate compare용이며 runtime direct-use feature로 승격하지 않는다.

### OppConfirm 정의

`OppConfirm_h = true` 조건:

1. anchor side 반대 방향이 `dominant_side`로 전환되고
2. 그 상태가 `2` snapshot 이상 유지되거나
3. 반대 방향 realized move가 `0.60R` 이상 발생

위 셋 중 하나라도 만족하면 `OppConfirm_h = true`로 본다.

### Reclaim 정의

`Reclaim_6`은 flip 이후 원래 방향이 다시 되살아난 정도다.

- flip 실행 이후 원래 thesis 방향의 favorable reclaim move / `R`

## 라벨 도메인

라벨은 모든 row에 찍지 않는다.

### hold-family 라벨 후보

아래 조건일 때만 평가:

- `belief_anchor_context`가 `entry_thesis` 또는 `hold_thesis`
- anchor side가 `BUY/SELL`

대상 라벨:

- `correct_hold`
- `wrong_hold`
- `missed_flip`

### flip-family 라벨 후보

아래 조건일 때만 평가:

- `belief_anchor_context = flip_thesis`
  또는
- `flip_readiness >= 0.55`

대상 라벨:

- `correct_flip`
- `premature_flip`

## 라벨 판정 규칙

아래 규칙은 v1 고정 규칙이다.

### 1. correct_hold

다음 조건을 모두 만족하면 `correct_hold`.

- `active_persistence >= 0.38`
- `belief_instability <= 0.45`
- `F_6 >= 0.75`
- `A_6 <= 0.60`
- `OppConfirm_6 = false`

추가 강화 조건:

- `F_6 >= 1.00` and `A_6 <= 0.40`면 `high confidence`

### 2. wrong_hold

다음 조건을 모두 만족하면 `wrong_hold`.

- `A_6 >= 1.00`
- `F_6 < 0.50`
- `OppConfirm_6 = false`
- hold 또는 same-thesis 유지가 실행/관찰된 상태

추가 강화 조건:

- `A_3 >= 0.80` and `F_6 < 0.30`면 `high confidence`

### 3. missed_flip

다음 조건을 모두 만족하면 `missed_flip`.

- `flip_readiness >= 0.55` 또는 `OppConfirm_3 = true`
- `belief_flip_executed = false`
- 반대 방향 realized move가 `0.75R` 이상
- 원래 thesis 기준 `A_6 >= 0.80`

추가 강화 조건:

- `OppConfirm_3 = true` and opposite-side move `>= 1.00R`면 `high confidence`

### 4. correct_flip

다음 조건을 모두 만족하면 `correct_flip`.

- `belief_flip_executed = true`
- flip 이후 반대 방향 move `>= 0.75R`
- `Reclaim_6 < 0.40`
- flip 이후 `OppConfirm_3 = true` 또는 반대 방향 dominance 유지

추가 강화 조건:

- flip 이후 반대 방향 move `>= 1.00R` and `Reclaim_6 < 0.25`면 `high confidence`

### 5. premature_flip

다음 조건을 모두 만족하면 `premature_flip`.

- `belief_flip_executed = true`
- flip 이후 반대 방향 move `< 0.50R`
- 원래 방향 reclaim `Reclaim_6 >= 0.75`

추가 강화 조건:

- `Reclaim_6 >= 1.00` and opposite-side move `< 0.30R`면 `high confidence`

## 충돌 해결 규칙

Belief 라벨은 하나만 남긴다.

우선순위는 아래로 고정한다.

1. `premature_flip`
2. `correct_flip`
3. `missed_flip`
4. `wrong_hold`
5. `correct_hold`

### 이유

- `premature_flip`은 flip-family 실패를 가장 직접적으로 설명하므로 최우선
- `missed_flip`은 단순 hold 실패보다 더 구체적인 오류
- `correct_hold`는 가장 일반적이므로 최하위

### 충돌 예시

- `wrong_hold`와 `missed_flip`이 동시에 뜨면 `missed_flip`
- `correct_flip`과 `premature_flip`이 동시에 뜨면 `premature_flip`
- `correct_hold`와 `wrong_hold`가 동시에 뜨면 `low confidence` 후 skip

### conflict resolver margin score

Belief는 deterministic precedence를 먼저 쓰되, 충돌이 가까울 때는 margin score를 같이 본다.

#### score_correct_hold

```text
score_correct_hold = F_6 - A_6 - max(0, flip_readiness - 0.55)
```

#### score_wrong_hold

```text
score_wrong_hold = A_6 - F_6
```

#### score_missed_flip

```text
score_missed_flip = max(0, opposite_move_6 - 0.75) + max(0, flip_readiness - 0.55)
```

#### score_correct_flip

```text
score_correct_flip = opposite_move_6 - Reclaim_6
```

#### score_premature_flip

```text
score_premature_flip = Reclaim_6 - opposite_move_6
```

### 적용 원칙

1. 먼저 기본 precedence를 본다.
2. 동시에 두 라벨이 만족하고 gap이 `0.15R` 미만이면 margin score를 conflict resolver로 사용한다.
3. margin score 차이도 작으면 `low confidence`로 내리고 skip 가능하다.

즉 margin score는 precedence 대체가 아니라 `conflict resolver`다.

## confidence 규칙

### high

- 핵심 라벨 조건을 모두 만족
- 반대 라벨 조건과 margin이 충분히 벌어짐
- 미래 bar coverage `>= 90%`

### medium

- 핵심 조건은 만족하지만 margin이 좁음
- 미래 bar coverage `>= 70%`

### low

- coverage 부족
- 충돌 라벨이 동시에 근접
- `R` 계산이 불안정
- 세션 종료/시장 중단으로 horizon이 심하게 잘림

### skip 규칙

아래는 `skip_candidate = true`로 둔다.

- `belief_label_confidence = low`
- coverage `< 70%`
- `R` 계산 실패
- `belief_anchor_side` 불명확

## edge case 규칙

### 1. 시장 중단 / session close

- horizon 안에 장이 닫히면 `coverage shortfall`
- 기본은 `low confidence`
- 심하면 skip

### 2. add-on / pyramid 상황

- 기존 포지션 위 add-on이면 `entry_thesis`로 보되
- `position already open` flag를 같이 남긴다
- v1 라벨은 동일 규칙을 쓰고, 나중에 add-on 전용 분리를 고려한다

### 3. immediate stop / forced exit

- 시스템 보호용 강제 청산은 Belief 단독 실패로 보지 않는다
- `belief_outcome_reason`에 `external_forced_exit`를 추가하고 low confidence 처리 가능

### 4. balanced belief

- `dominant_side = BALANCED`면 Belief 라벨 기본 대상에서 제외
- 다만 `flip_readiness`가 높고 반대 dominance가 명확히 생기면 flip-family만 제한적으로 평가

## 실패 모드

Belief owner의 핵심 실패 모드는 아래로 고정한다.

- `stale_hold`
  - thesis를 너무 늦게 버림
- `noise_exit`
  - 아직 살아 있는 thesis를 noise로 오판
- `delayed_flip`
  - flip readiness가 높았는데 전환이 늦음
- `false_flip`
  - 반대 thesis로 빨리 뒤집었지만 원래 방향이 재개됨

이 실패 모드는 라벨과 1:1 매핑은 아니지만, replay report에서 같이 본다.

## 최소 관측 지표

Belief 승격 중 최소로 봐야 하는 지표는 아래다.

- `wrong_hold_ratio`
- `premature_flip_ratio`
- `missed_flip_ratio`
- `high_confidence_share`
- `balanced_skip_rate`
- `belief_break_to_exit_lag`
- `scene_skew_by_label`

## 승격 중단 조건

아래는 hard stop 조건이다.

1. `low confidence share > 0.35`
2. `scene_skew_by_label`이 특정 scene에 과도하게 쏠림
3. `wrong_hold_ratio`는 줄었지만 `premature_flip_ratio`가 `20%` 이상 급증
4. `missed_flip_ratio`는 줄었지만 net pnl / expectancy가 악화
5. label precedence 충돌이 `5%` 이상 발생

## Bridge / Seed / Baseline / Candidate / Overlay 설계

### BO0. Scope Freeze

- owner 역할 고정
- direct-use / learning-only field 분리
- leakage 규칙 고정

### BO1. Runtime Bridge

산출물:

- `belief_state25_runtime_bridge_v1`
- `belief_runtime_summary_v1`
- `belief_input_trace_v1`

포함:

- scene 힌트
- belief canonical field
- acting side
- anchor context
- forecast / evidence / barrier compact input trace

### BO2. Replay / Outcome Bridge

산출물:

- `belief_outcome_bridge_v1`

포함:

- `F_3 / F_6 / A_3 / A_6`
- `OppConfirm_3 / OppConfirm_6`
- `Reclaim_6`
- 라벨
- confidence
- reason

### BO3. Closed-History Seed Enrichment

추가 seed 컬럼 초안:

- `belief_outcome_label`
- `belief_label_confidence`
- `belief_break_signature`
- `belief_anchor_context`
- `belief_horizon_bars`
- `belief_outcome_reason`

### BO4. Baseline Auxiliary Task

목표:

- current scene/state/evidence/forecast로 `belief_outcome_label` 예측

skip 조건:

- high/medium confidence 유효 row < `40`
- class support min < `8`

### BO5. Candidate Compare Integration

compare summary에 최소 반영:

- `wrong_hold_ratio_delta`
- `premature_flip_ratio_delta`
- `missed_flip_ratio_delta`
- `high_confidence_share_delta`

candidate 판정 원칙:

- Belief는 v1에서 hard blocker보다 warning/soft blocker 위주
- 단 `premature_flip` 급증은 hard stop 가능

### BO6. Log-only Overlay

live 행동을 바꾸지 않고 아래 trace만 남긴다.

- `belief_action_hint_v1`
- `belief_recommended_action_family`
  - `hold_bias`
  - `wait_bias`
  - `flip_alert`
  - `reduce_alert`
- `belief_overlay_reason_codes`
- `belief_overlay_confidence`

### belief_action_hint_v1

`belief_action_hint_v1`는 action engine을 직접 대체하지 않고, 아래 shadow hint만 남긴다.

- `recommended_family`
  - `hold_bias`
  - `wait_bias`
  - `flip_alert`
  - `reduce_alert`
- `supporting_label_candidate`
  - `correct_hold`
  - `wrong_hold`
  - `missed_flip`
  - `correct_flip`
  - `premature_flip`
- `supporting_trace_fields`
  - `active_persistence`
  - `belief_instability`
  - `flip_readiness`
  - `forecast_expected_path`
  - `dominant_evidence_family`
  - `barrier_total_hint`

## v1 완료 기준

아래가 되면 Belief owner v1은 닫힌 것으로 본다.

1. 라벨 규칙이 문서와 코드에서 일치한다
2. `belief_input_trace_v1`가 replay/seed에 함께 남는다
3. `belief_outcome_bridge_v1`가 실제 로그를 생성한다
4. closed-history에 seed 컬럼이 backfill된다
5. baseline auxiliary가 sparse/ready를 구분해 돈다
6. candidate compare가 Belief 구조 KPI를 읽는다
7. live에는 `belief_action_hint_v1`를 포함한 `log_only` trace까지만 붙는다

## 한 줄 결론

Belief owner v1의 핵심은 `exit를 잘하게 만드는 보조지표`가 아니라,
`같은 thesis를 계속 유지할지, 기다릴지, 줄일지, 뒤집을지를 설명하는 persistence owner`로
ground truth를 고정하는 것이다.
