# Semantic Owner Maturity Alignment Map

## 2026-04-04 Reinforcement

### Maturity Interpretation Update

- `forecast`: architecture maturity is high, but label coverage maturity is still mid-stage
- `belief`: owner semantics are now strong, but usable label coverage is still early-stage

This means the immediate work is:

1. keep the owner contract stable
2. grow `strict / usable / skip` visibility
3. avoid promoting sparse owners directly into live execution

### Coverage-First Read

For `forecast` and `belief`, the correct reading is now:

- structure: mostly ready
- coverage: not yet deep enough
- rollout status: `log_only` and audit-first

### Cross-Cutting Risk Update

The cross-cutting risk is no longer only semantic ambiguity.
It is now also:

- sparse usable coverage
- insufficient counterfactual audit
- trace assembly / payload wiring fragility

This means maturity should now be read on two axes:

- owner architecture maturity
- coverage and rollout maturity

### Current Practical Priority

Immediate practical priority is:

1. keep `forecast / belief / barrier` contracts stable
2. improve `strict / usable / skip` visibility
3. grow audit evidence before live authority
4. harden payload assembly before adding more owners

### Recommended Next Read

- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)
- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)

### Barrier Maturity Read Update

Barrier should now be read as:

- architecture maturity: high enough for audit and readiness work
- coverage maturity: materially improved
- interpretation maturity: still biased toward `avoided_loss`

This means the next barrier work is not a new owner contract.
It is bias correction and action-resolution refinement inside the existing BCE track.

## 왜 이 문서가 필요한가

지금까지 `state25`, `forecast`, `wait_quality`, `economic_target`, `candidate/gate/AI6` 쪽은 많이 끌어올렸고,
그 과정에서 `Position / Response Raw / Response / State / Evidence / Belief / Barrier / Forecast / Observe-Confirm / Consumer` 사이에 **급 차이**가 생겼다.

즉 지금 필요한 건

- 어떤 축은 이미 많이 끌어올려졌는지
- 어떤 축은 아직 runtime 사용 수준에 머물러 있는지
- 어떤 축은 같은 급으로 맞추려면 어떤 아이디어가 더 들어가야 하는지

를 한 번에 보는 기준표다.

이 문서는 그 기준표다.

## 이 문서에서 말하는 “급”

여기서는 각 owner/layer를 아래 6단계로 본다.

| 단계 | 이름 | 의미 |
| --- | --- | --- |
| `L0` | inventory only | 코드에 존재하지만 owner 경계나 역할이 정리되지 않음 |
| `L1` | owner frozen | 이 층이 무슨 질문을 맡는지, 무엇을 하면 안 되는지 정리됨 |
| `L2` | runtime canonical | canonical field와 runtime 소비 위치가 정리됨 |
| `L3` | replay / outcome bridge | 나중 결과와 붙여서 좋았는지/나빴는지 다시 볼 수 있음 |
| `L4` | learning loop | seed / baseline / candidate 루프에 올라감 |
| `L5` | live rollout | log-only / canary / bounded live까지 이어질 수 있음 |

한 줄로 줄이면:

- `L1~L2`는 “의미 정리”
- `L3~L4`는 “학습 정리”
- `L5`는 “실운영 연결”

이다.

## 현재 전체 지형

### 이미 높은 급까지 올라온 축

- `state25`
- `wait_quality`
- `economic_target`
- `candidate / gate / AI6`

### 중간까지 올라왔지만 아직 반쯤인 축

- `forecast`
- `Position`
- `Response`
- `State`

### 매우 중요하지만 아직 최근 체계로는 덜 손본 축

- `Response Raw`
- `Evidence`
- `Belief`
- `Barrier`

### 마지막에 정리해야 하는 소비층

- `Observe/Confirm/Action`
- `Consumer`

이 둘은 새 owner를 만드는 곳이 아니라, 위에서 만든 의미를 다시 망치지 않게 소비하는 층이다.

## 축별 maturity 정리

### 1. state25

- 현재 수준: `L5 가까운 L4+`
- 지금까지 한 일:
  - scene/labeling owner로 재정의
  - seed / QA / backfill / tuning / candidate 비교 / gate / AI6까지 연결
  - `log_only` overlay와 candidate watch까지 연결
- 이미 들어간 아이디어:
  - `scene owner`
  - `teacher pattern compact schema`
  - `Step9 watch`
  - `AI3~AI6`
- 아직 남은 것:
  - `canary -> bounded live`
  - seed 더 누적

정리:

`state25`는 지금 시스템에서 가장 많이 끌어올려진 축이다.

### 2. wait_quality

- 현재 수준: `L4`
- 지금까지 한 일:
  - replay bridge
  - closed-history enrichment
  - baseline auxiliary task 연결
- 이미 들어간 아이디어:
  - `better_entry_after_wait`
  - `avoided_loss_by_wait`
  - `missed_move_by_wait`
  - `delayed_loss_after_wait`
- 아직 남은 것:
  - 표본 누적
  - task readiness 확보
  - state25 / forecast와 joint auxiliary 강화

정리:

`wait_quality`는 구조는 거의 됐지만 표본이 아직 얇다.

### 3. economic_target

- 현재 수준: `L4`
- 지금까지 한 일:
  - economic target contract 정리
  - seed report 연결
  - pilot baseline auxiliary task 연결
- 이미 들어간 아이디어:
  - `learning_total_label`
  - `loss_quality_label`
  - `signed_exit_score`
- 아직 남은 것:
  - candidate 품질에 더 직접 반영
  - canary 판단과 연결

정리:

`economic_target`은 wait_quality보다 한 발 더 앞서 있고, 실제 학습 보조 과제까지 올라온 상태다.

### 4. candidate / gate / AI6

- 현재 수준: `L5`
- 지금까지 한 일:
  - retrain / compare / promotion gate
  - execution integration recommendation
  - auto-promote live actuator
  - active candidate runtime consumption
  - 실제 `log_only` rollout 활성화
- 이미 들어간 아이디어:
  - `hold_offline`
  - `log_only_ready`
  - `promote_log_only_ready`
  - `active_candidate_state.json`
- 아직 남은 것:
  - `canary`
  - `bounded live`
  - rollback 실효성 누적 검증

정리:

`candidate / gate / AI6`는 구조적으로 가장 성숙한 운영축이다.

### 5. forecast

- 현재 수준: `L4-`
- 지금까지 한 일:
  - runtime forecast는 이미 오래전부터 존재
  - `forecast-state25 runtime bridge`
  - `FSB2 replay / outcome bridge`
  - `FSB3 closed-history seed enrichment`
  - `FSB4 baseline auxiliary task`
  - `FSB5 candidate compare integration`
  - `FSB6 log_only overlay scaffold`
- 이미 들어간 아이디어:
  - `forecast_state25_runtime_bridge_v1`
  - `forecast_state25_outcome_bridge_v1`
  - `forecast_state25_*` seed enrichment 컬럼
  - baseline auxiliary task
  - candidate compare summary
  - forecast-state25 log-only overlay trace
- 아직 안 된 것:
  - outcome coverage 확충
  - `expected_path / realized_path / forecast_error_type` 안정화
  - auxiliary task readiness 실제 개방
  - live overlay gate 개방

같은 급으로 맞추려면 필요한 아이디어:

- `scene -> forecast -> realized outcome` 체인 고정
- `forecast가 맞았는지`를 `state25 scene` 단위로 재평가
- `entry / wait / exit`를 forecast 기준으로 따로 보지 않고 하나의 체인으로 묶기

정리:

`forecast`는 scaffold는 거의 닫혔고, 이제 남은 건 표본과 판정 품질을 실제로 여는 단계다.

### 6. Position

- 현재 수준: `L2~L3`
- 지금까지 한 일:
  - snapshot / interpretation / energy 쪽이 많이 정리됨
  - runtime canonical field가 꽤 명확함
- 이미 들어간 아이디어:
  - `PositionSnapshot`
  - `PositionInterpretation`
  - `PositionEnergySnapshot`
- 아직 부족한 것:
  - state25 / outcome 쪽으로 직접 이어지는 learning bridge는 약함

같은 급으로 맞추려면 필요한 아이디어:

- position zone / edge / middle neutrality가 실제로 좋은 entry/wait/exit로 이어졌는지 결과 브리지
- position-energy와 economic target의 직접 연결

정리:

`Position`은 의미 정리는 많이 됐지만, 아직 state25처럼 학습 owner로 크게 승격된 건 아니다.

### 7. Response

- 현재 수준: `L2~L3`
- 지금까지 한 일:
  - `ResponseVectorV2` 중심으로 전이 의미가 많이 정리됨
- 이미 들어간 아이디어:
  - raw event를 transition vector로 압축
  - state/evidence/forecast upstream으로 사용
- 아직 부족한 것:
  - 어떤 transition이 실제로 좋은 wait/entry/exit로 이어졌는지 replay/learning bridge가 약함

같은 급으로 맞추려면 필요한 아이디어:

- transition family별 outcome replay
- response-state25 scene bridge
- response family auxiliary task

정리:

`Response`는 semantic 중간축으로는 꽤 정리됐지만, 아직 독립 learning owner로는 덜 올라왔다.

### 8. State

- 현재 수준: `L2~L3`
- 지금까지 한 일:
  - `StateVectorV2`와 advanced state input이 꽤 손봐진 상태
- 이미 들어간 아이디어:
  - regime / liquidity / policy-adjusted state
- 아직 부족한 것:
  - state가 결과적으로 어떤 wait/exit quality를 만들었는지 브리지 부족

같은 급으로 맞추려면 필요한 아이디어:

- state regime family별 outcome replay
- state25와 state vector의 explicit bridge
- state confidence vs realized utility audit

정리:

`State`는 runtime core로는 중요하지만, learning bridge 쪽은 아직 약하다.

### 9. Response Raw

- 현재 수준: `L1.5`
- 현재 상태:
  - 매우 중요하게 쓰인다
  - 하지만 최근 체계로는 거의 안 손본 축이다
- 지금 코드 역할:
  - raw 이벤트를 모아 `ResponseRawSnapshot` 생성
  - 그 뒤 곧바로 `ResponseVector` / `ResponseVectorV2`로 넘어감
- 이미 있는 것:
  - canonical field는 존재
  - raw 반응 inventory는 풍부함
- 아직 부족한 것:
  - owner 경계 재정리
  - raw event family 결과 브리지
  - state25 / wait / economic과의 learning 연결

같은 급으로 맞추려면 필요한 아이디어:

- `raw event owner`를 명시적으로 고정
- `raw event -> transition -> outcome` 추적
- raw motif / candle / structure subsystem별 replay report
- response raw seed enrichment

정리:

`Response Raw`는 핵심인데 아직 최근 체계로는 거의 재정의되지 않았다.

### 10. Evidence

- 현재 수준: `L1.5~L2`
- 현재 상태:
  - runtime에서는 핵심이다
  - 하지만 최근 체계로는 거의 안 손본 축이다
- 지금 코드 역할:
  - `position + response + state`를 합쳐 현재 증거 강도를 만든다
- 이미 있는 것:
  - `EvidenceVector`
  - reversal / continuation / total evidence 구조
- 아직 부족한 것:
  - owner 경계 재고정
  - state25 scene과의 bridge
  - evidence tension이 좋은 wait/entry/exit로 이어졌는지 결과 브리지

같은 급으로 맞추려면 필요한 아이디어:

- evidence family / dominant-support split replay
- `scene -> evidence composition -> realized outcome` chain
- evidence auxiliary task

정리:

`Evidence`는 지금도 매우 중요하지만, recent state25급 재구성에서는 거의 안 만진 축이다.

### 11. Belief

- 현재 수준: `L1.5~L2`
- 현재 상태:
  - owner 경계는 코드상 이미 분명하다
  - runtime 소비도 된다
  - 하지만 learning bridge는 아직 없다
- 이미 있는 것:
  - persistence owner 계약
  - `buy_belief`, `sell_belief`
  - `buy_persistence`, `sell_persistence`
  - `flip_readiness`
  - `belief_instability`
- 아직 부족한 것:
  - state25 scene bridge
  - wait/economic outcome bridge
  - baseline/candidate auxiliary task

같은 급으로 맞추려면 필요한 아이디어:

- `Belief-State25 bridge`
- persistence가 좋은 wait / confirm release로 이어졌는지 audit
- belief flip readiness와 realized reversal 연결

정리:

`Belief`는 owner 정체성은 좋지만 아직 학습 owner로는 반쯤만 올라온 상태다.

### 12. Barrier

- 현재 수준: `L1.5~L2`
- 현재 상태:
  - owner 경계는 코드상 이미 분명하다
  - runtime 소비도 된다
  - 하지만 learning bridge는 아직 없다
- 이미 있는 것:
  - blocking owner 계약
  - `buy_barrier`, `sell_barrier`
  - `conflict_barrier`
  - `middle_chop_barrier`
  - `direction_policy_barrier`
  - `liquidity_barrier`
- 아직 부족한 것:
  - 어떤 barrier가 손실 회피였는지
  - 어떤 barrier가 기회 손실이었는지
  - state25 / wait / economic과의 replay 연결

같은 급으로 맞추려면 필요한 아이디어:

- `Barrier-State25 bridge`
- `avoided_loss_by_block`
- `missed_move_by_block`
- `correct_relief`
- `false_relief`

정리:

`Barrier`는 runtime 차단 owner로는 강하지만, 아직 learning owner로는 거의 시작 전이다.

### 13. Observe / Confirm / Action

- 현재 수준: `L2`
- 현재 상태:
  - lifecycle 결정층으로 이미 매우 중요하다
  - 하지만 여기서 새 의미를 만들면 안 된다
- 이 층의 목표:
  - 위 owner들 결과를 받아 lifecycle만 결정
  - 재해석 최소화

같은 급으로 맞추려면 필요한 아이디어:

- 새 semantic owner를 만들지 않게 contract 강화
- decision trace 정리
- bridge/log-only 비교 surface 강화

정리:

`Observe/Confirm/Action`은 승격보다는 “다른 의미를 다시 만들지 않게 정리”가 핵심이다.

### 14. Consumer

- 현재 수준: `L2`
- 현재 상태:
  - 실행/라벨/관리 payload 소비층
  - 의미를 재정의하면 안 되는 층

같은 급으로 맞추려면 필요한 아이디어:

- consumer reinterpretation 금지 contract 강화
- canonical input contract 유지
- downstream audit만 강화

정리:

`Consumer`는 semantic 승격 대상이라기보다, semantic 오염 방지 대상이다.

## 지금 기준 “된 것”과 “안 된 것”

### 거의 된 것

- `state25`
- `wait_quality`
- `economic_target`
- `candidate / gate / AI6`

이쪽은 이미 `L4~L5`에 가깝다.

### 반쯤 된 것

- `forecast`
- `Position`
- `Response`
- `State`

이쪽은 runtime 의미는 강하지만 learning loop가 아직 덜 닫혔다.

### 이제부터 본격적으로 같은 급으로 맞춰야 하는 것

- `Response Raw`
- `Evidence`
- `Belief`
- `Barrier`

이쪽은 지금 시스템에서 중요도는 높은데, state25급 운영/학습 루프까지는 아직 못 올라왔다.

## 어떤 순서로 맞추는 게 좋은가

추천 순서는 이렇다.

1. `forecast`
- 이미 FSB scaffold가 닫혔다
- 지금은 새 설계보다 운영 누적과 품질 안정화가 우선이다

2. `Belief`
- persistence owner
- wait/confirm release와 바로 연결된다

3. `Barrier`
- block/relief owner
- 손실 회피와 직접 연결된다

4. `Evidence`
- 중간 핵심층
- scene/evidence/outcome chain으로 승격해야 한다

5. `Response Raw`
- raw event owner
- 너무 이르게 건드리면 범위가 커지므로 Evidence 뒤가 낫다

6. `Observe/Confirm/Consumer`
- 마지막에 정리
- 의미 재정의 금지 contract 강화

## 다음 문서 단위

이 문서 다음부터는 owner마다 `승격 명세서`로 내려간다.

즉 이제 필요한 것은 추상 조언이 아니라 아래 항목이 들어간 문서다.

- 라벨 판정 규칙
- 실패 모드
- 최소 관측 지표
- 승격 중단 조건
- replay bridge
- seed enrichment
- baseline auxiliary
- candidate compare
- log-only trace

이 실행 순서는 [current_owner_promotion_spec_rollout_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_owner_promotion_spec_rollout_roadmap_ko.md)에 정리했다.

다음 1순위는 `Belief owner 승격 명세서`다.

현재 문서:

- [current_belief_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_belief_owner_promotion_spec_v1_ko.md)
- [current_barrier_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_owner_promotion_spec_v1_ko.md)

현재 Belief spec에 이미 반영한 보강:

- `adaptive threshold / adaptive horizon`은 v2 항목으로 분리
- precedence margin은 Belief 고정 precedence를 보조하는 `conflict resolver`로 제한
- `belief_input_trace_v1 / belief_action_hint_v1`를 명시

## 한 줄 결론

지금 시스템은 `state25 / wait_quality / economic_target / candidate-ai6`는 높은 급까지 올라왔고,
`forecast`는 반쯤 올라왔으며,
`Response Raw / Evidence / Belief / Barrier`는 매우 중요하지만 아직 recent 체계로는 덜 손본 상태다.

즉 다음 핵심은 `덜 손본 핵심 owner들을 state25급 bridge / replay / seed / baseline / candidate 루프로 끌어올리는 것`이다.
