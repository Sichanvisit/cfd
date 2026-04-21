# Barrier Coverage Engineering Implementation Roadmap

## 2026-04-04 Bias Correction Extension

`BCE0~BCE7` should now be read as the first completed barrier coverage loop.
The next extension remains part of `BCE`, not a separate program.

Recommended follow-up sequence:

1. `BCE8 Bias Baseline Report`
2. `BCE9 Missed-Profit / Overblock / Correct-Wait / Relief Recovery`
3. `BCE10 Action Normalization Refinement`
4. `BCE11 Reducible / Irreducible Skip Split`
5. `BCE12 Readiness Sensitivity Review`

Detailed references:

- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)

## 목적

이 문서는 [Barrier coverage engineering 상세 설계](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)를
실제 구현 직전 작업 단위로 자른 로드맵이다.

전제:

- `BR0~BR6`는 이미 연결되어 있다
- 지금 할 일은 새 bridge를 더 만드는 것이 아니라 usable coverage와 audit을 키우는 것이다
- execution owner는 계속 기존 엔진으로 유지한다

## 작업 원칙

1. live override 금지
2. coverage surface 먼저
3. weak label은 hard gate와 분리
4. wiring hardening을 coverage 작업과 같이 진행

## BCE0. Scope Freeze

목표:

- barrier coverage engineering의 범위와 비범위를 고정한다

해야 할 일:

- `strict / usable / skip` 분류 고정
- `high / medium / weak_usable / low_skip` 사용 경계 고정
- counterfactual audit은 log-only 사후 감사로만 사용한다고 명시
- live decision override는 범위 밖이라고 못 박기

출력:

- coverage usage policy
- rollout stop conditions

완료 기준:

- barrier spec와 coverage design에서 같은 usage boundary를 읽을 수 있음

## BCE1. Coverage Dashboard

목표:

- barrier usable coverage를 숫자로 바로 볼 수 있게 만든다

해야 할 일:

- report JSON/MD에 아래 추가
  - `total_anchor_rows`
  - `strict_rows`
  - `usable_rows`
  - `skip_rows`
  - `high / medium / weak_usable / low_skip`
  - top skip reasons
  - label share
  - cost mean

출력:

- `barrier_coverage_latest.json`
- `barrier_coverage_latest.md`

완료 기준:

- “barrier가 왜 안 쓰이는지”를 한 번에 읽을 수 있음

## BCE2. Skip Reason Taxonomy

목표:

- `low_skip`를 한 덩어리 bucket이 아니라 원인별로 분해한다

해야 할 일:

- skip reason enum/strings 정리
- `insufficient_future_bars`
- `low_move_magnitude`
- `ambiguous_cost_balance`
- `no_reentry_or_relief_observed`
- `side_conflict_unresolved`
- `overlapping_label_candidates`
- `release_window_not_mature`
- `counterfactual_anchor_too_weak`

출력:

- 분해된 skip reason counts

완료 기준:

- top-3 skip reason을 기준으로 다음 완화 우선순위를 정할 수 있음

## BCE3. Weak/Strict Utilization Split

목표:

- `weak_usable`을 baseline/diagnostic에만 쓰고, compare hard gate와는 분리한다

해야 할 일:

- baseline report에 weak usage surface 추가
- candidate compare는 `high/medium` 우선 유지
- `weak_usable_share`와 `weak_to_medium_conversion_rate` 추가

출력:

- baseline / compare usage policy surface

완료 기준:

- weak coverage를 늘려도 hard gate가 오염되지 않음

## BCE4. Counterfactual Audit Surface

목표:

- barrier 추천과 실제 엔진 행동의 결과 차이를 사후 감사한다

해야 할 일:

- `actual_engine_action_family`
- `barrier_recommended_family`
- `counterfactual_outcome_family`
- `counterfactual_cost_delta_r`
- `counterfactual_reason_summary`
  를 report surface에 추가

출력:

- barrier counterfactual audit JSON/MD

완료 기준:

- barrier의 `wait_bias / block_bias / relief_watch`가 실제로 맞았는지 비교 가능

## BCE5. Drift Audit

목표:

- 기존 엔진과 barrier log-only hint의 차이를 누적 추적한다

해야 할 일:

- action family mismatch 집계
- symbol / scene family / barrier family별 drift 집계
- repeated mismatch top cases 출력

출력:

- barrier drift audit JSON/MD

완료 기준:

- 이후 canary를 논할 때 “기존 엔진과 얼마나 다른지”를 수치로 설명 가능

## BCE6. Wiring Hardening

목표:

- owner가 더 늘어나도 trace assembly가 main loop를 깨지 않게 만든다

해야 할 일:

- barrier payload builder 함수 분리
- optional field safe-get wrapper 도입
- runtime/detail row injection test 보강
- entry row flat-field persistence test 보강

출력:

- owner injection tests
- safer payload assembly path

완료 기준:

- barrier 관련 field 추가/변경이 바로 main loop crash로 이어지지 않음

## BCE7. Readiness Gate

목표:

- coverage engineering 후 Evidence spec 구현으로 넘어갈지 판단한다

봐야 할 지표:

- `strict_rows > 0`가 안정적으로 반복되는지
- `usable_rows / total_anchor_rows`가 개선되는지
- `overblock_ratio`가 과증가하지 않는지
- `counterfactual_cost_delta_r`가 방향성을 보이는지
- wiring issue 없이 runtime heartbeat가 안정적인지

완료 기준:

- Barrier는 “구조만 있는 owner”에서 “coverage가 보이는 owner”로 올라옴
- 그 다음 `Evidence` 구현을 시작할 근거가 생김

## 구현 전 최종 메모

이번 로드맵의 끝은 “구현 완료”가 아니라 “구현 시작 준비 완료”다.

즉 다음 턴부터는 위 순서대로:

1. `BCE0~BCE2`를 먼저 코드/리포트에 반영
2. 그 다음 `BCE4~BCE6` audit/wiring
3. 마지막에 `BCE7` readiness 판단

으로 들어가면 된다.
