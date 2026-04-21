# Barrier Coverage Engineering Design

## 2026-04-04 Bias Correction Extension

`BCE0~BCE7` closed the first coverage-engineering loop.
That does not mean Barrier is now done.

The next barrier problem is no longer bridge completeness.
It is:

- label distribution bias
- cost balance bias
- action normalization bias

Current read:

- `strict_rows` now exist in meaningful volume
- runtime / wiring stability is no longer the primary blocker
- readiness is still blocked because unresolved semantic area remains too large
- `avoided_loss` appears overrepresented relative to `missed_profit / overblock / correct_wait / relief`

So the next extension should stay inside the `BCE` program, not open a new architecture track.

Recommended next detailed references:

- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)

### Policy Separation Reminder

`pre_context_skip:max_positions_reached` remains outside barrier semantic quality.
It should stay excluded from barrier coverage denominators and be revisited later
as a separate capacity-policy audit when the whole phase-07 summary is assembled.

## 목적

이 문서는 `Barrier` owner가 `BR0~BR6`까지 구조적으로 연결된 뒤,
왜 아직 usable label이 거의 없고 대부분 `low_skip`에 머무는지 풀기 위한
`coverage engineering` 상세 설계다.

핵심 목표는 새 owner 철학을 더 추가하는 것이 아니라,
이미 만든 barrier scaffold 위에서 아래 4가지를 운영 가능하게 만드는 것이다.

1. usable row를 늘린다
2. skip 이유를 분해해서 보이게 만든다
3. `correct_wait / overblock / missed_profit / avoided_loss` 경계를 더 안정화한다
4. barrier log-only 추천과 실제 엔진 행동의 차이를 사후 감사한다

## 현재 해석

현재 barrier 상태는 다음처럼 읽는다.

- architecture: `BR0~BR6` 완료
- live observability: 완료
- candidate/gate wiring: 완료
- coverage maturity: 아직 낮음
- bottleneck: 설계 부족보다 usable coverage와 wiring 안정성

즉 barrier는 지금 `새 문서가 없는 owner`가 아니라
`문서는 충분한데 usable row가 부족한 owner`다.

## 범위

이 설계의 범위:

- barrier outcome coverage 대시보드
- skip reason taxonomy
- label utilization policy
- counterfactual audit
- drift audit
- wiring hardening 요구사항

이 설계의 비범위:

- live execution owner 변경
- barrier가 실제 진입/청산을 직접 override하도록 승격
- evidence / response raw 구현 시작

## 기본 원칙

### 1. execution owner는 유지

지금도 실제 진입/대기/청산은 기존 엔진이 맡는다.
Barrier는 `log_only` explanation / hint owner로 유지한다.

### 2. label quality와 rollout authority를 분리

- `high` / `medium`: strict rows, compare/gate usable
- `weak_usable`: baseline/diagnostic usable
- `low_skip`: replay-only / coverage-only

즉 row가 생겼다고 곧바로 candidate hard gate에 섞지 않는다.

### 3. flat은 운영용, nested는 재구성용

- flat field: 운영 대시보드, CSV, grep
- nested payload: replay, schema evolution, full reason trace

flat은 nested에서 deterministic하게 파생되어야 한다.

### 4. no-leakage 유지

coverage를 늘린다고 해서 future leakage를 허용하지 않는다.
미래 정보는 label 생성에만 사용하고, runtime direct-use field로는 올리지 않는다.

## Barrier Coverage 문제 정의

현재 barrier에서 자주 나오는 현상:

- `labeled_rows = 0` 또는 극소수
- `confidence_counts.low_skip` 비중이 매우 높음
- `correct_wait`와 `overblock`의 경계가 보수적으로 잡힘
- `relief_success / relief_failure`도 usable row가 적음

이 문제를 풀기 위해선 단순 threshold 완화보다,
`왜 skip되는지`, `어디까지는 weak row로 쓸지`, `실제 엔진과 뭐가 달랐는지`
를 먼저 보여주는 쪽이 맞다.

## Coverage 분류

Barrier coverage는 아래 3단으로 본다.

### strict rows

- confidence = `high` 또는 `medium`
- compare/gate KPI에 직접 사용 가능

### usable rows

- confidence = `weak_usable`
- baseline auxiliary, diagnostics, replay coverage에는 사용
- candidate hard gate에는 기본적으로 직접 사용하지 않음

### skip rows

- confidence = `low_skip`
- 구조적으로는 anchor가 있으나 판정 근거가 부족
- coverage와 skip taxonomy에만 남김

## Skip Reason Taxonomy

Barrier coverage engineering에서는 최소한 아래 reason을 분리해서 본다.

- `insufficient_future_bars`
- `low_move_magnitude`
- `ambiguous_cost_balance`
- `no_reentry_or_relief_observed`
- `side_conflict_unresolved`
- `overlapping_label_candidates`
- `release_window_not_mature`
- `counterfactual_anchor_too_weak`

원칙:

- skip는 하나의 bucket이 아니라 분해된 원인 집합이어야 한다
- top skip reason이 매일 보이지 않으면 coverage 개선이 안 된다

## Coverage Dashboard

Barrier coverage dashboard의 최소 출력은 아래와 같다.

- `total_anchor_rows`
- `strict_rows`
- `usable_rows`
- `skip_rows`
- `high_rows`
- `medium_rows`
- `weak_usable_rows`
- `low_skip_rows`
- `strict_share`
- `usable_share`
- top skip reasons
- label share:
  - `avoided_loss`
  - `missed_profit`
  - `correct_wait`
  - `overblock`
  - `relief_success`
  - `relief_failure`

추가로 비용 계열 평균도 같이 본다.

- `loss_avoided_r_mean`
- `profit_missed_r_mean`
- `wait_value_r_mean`

## Label Utilization Policy

Barrier label은 단계별로 다르게 쓴다.

### compare / gate

- `high` / `medium`만 기본 사용
- hard blocker는 `overblock`, `relief_failure` 급증에만 제한적으로 사용

### baseline auxiliary

- `high` / `medium` + `weak_usable` 사용 가능
- 단, `weak_usable` 비중은 따로 보고한다

### diagnostics / replay

- 모든 tier 사용 가능
- 단 `low_skip`는 label 품질 지표가 아니라 coverage 지표로만 읽는다

## Counterfactual Audit

Barrier log-only 추천은 단순 기록으로 끝나면 안 된다.
다음 질문을 사후에 자동으로 남겨야 한다.

- barrier가 `wait_bias`였는데 실제 엔진은 entry했다: 결과적으로 `avoided_loss`였나 `missed_profit`이었나
- barrier가 `relief_watch`였는데 실제 엔진은 계속 wait했다: release 이후 더 좋은 기회가 있었나
- barrier가 `block_bias`였는데 실제 엔진은 hold/entry를 유지했다: adverse excursion이 실제로 커졌나

최소 counterfactual audit surface:

- `actual_engine_action_family`
- `barrier_recommended_family`
- `counterfactual_outcome_family`
- `counterfactual_cost_delta_r`
- `counterfactual_reason_summary`

## Drift Audit

Barrier owner와 기존 엔진의 차이는 action engine 통합 전 핵심 자료다.

최소 drift surface:

- `actual_enter_vs_barrier_wait_bias`
- `actual_enter_vs_barrier_block_bias`
- `actual_wait_vs_barrier_relief_release_bias`
- `actual_hold_vs_barrier_block_bias`

이 drift는 symbol, scene family, barrier family별로 누적해서 본다.

## Wiring Hardening Requirement

최근 owner flat field 배선에서 runtime crash가 실제로 발생했기 때문에,
coverage engineering과 같이 wiring hardening도 요구사항으로 둔다.

최소 요구:

- owner payload builder 함수 분리
- optional field safe-get wrapper
- owner injection unit test
- runtime/detail row assembly에서 필수/선택 field 경계 명시

원칙:

- owner를 더 붙일수록 의미 설계보다 조립 안정성이 먼저 깨질 수 있다
- coverage engineering은 audit만이 아니라 wiring 안정성 강화도 포함한다

## 성공 조건

Barrier coverage engineering 1차 성공 조건은 아래다.

1. `strict / usable / skip`가 매일 보고된다
2. top skip reasons가 분해되어 보인다
3. `weak_usable`이 baseline diagnostics에 실제로 쓰인다
4. `correct_wait / overblock` 경계가 별도 reason과 cost로 설명된다
5. barrier hint와 실제 엔진 행동의 drift가 보고된다

## 중단 조건

아래 중 하나가 나오면 coverage 확대를 멈추고 규칙을 다시 본다.

- `weak_usable`만 늘고 `high / medium`은 계속 0에 가까움
- `overblock` 비율이 급증하는데 `avoided_loss`는 늘지 않음
- cost 평균이 불안정해서 label 해석이 매일 바뀜
- wiring 변경 때문에 runtime heartbeat가 흔들림

## 다음 문서

이 설계를 실제 작업 단위로 쪼갠 구현 순서는 아래를 따른다.

- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)
