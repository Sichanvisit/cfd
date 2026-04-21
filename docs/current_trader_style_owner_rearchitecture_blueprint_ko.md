# Trader-Style Owner Re-architecture Blueprint

## 2026-04-04 Reinforcement

### Immediate Bottleneck Update

The next constraint is not additional philosophy but `coverage engineering`.

- `forecast`: scaffold is in place; outcome coverage needs `full / partial / insufficient` visibility
- `belief`: owner contract is strong; usable labels need `high / medium / weak_usable / low_skip` separation

### Action Integration Reminder

Unified action remains a later stage:

`scene -> forecast -> evidence -> belief -> barrier -> action utility shadow -> canary -> bounded_live`

Current `log_only` owner surfaces should be treated as explanation and audit layers first, not live override layers.

### Coverage / Audit / Wiring Priority

The next project priority is not new abstract architecture but operational maturity.

That means:

- `coverage`: usable labeled rows must grow
- `audit`: log-only recommendations must be compared against actual engine behavior
- `wiring`: owner payload assembly must stop being a hidden crash risk

Operational reading:

- `forecast`: structure is mostly ready, coverage is thin
- `belief`: semantics are strong, usable labels are still expensive
- `barrier`: live trace is connected, but outcome usability is still sparse

### Execution Guardrail

Until counterfactual audit and usable coverage improve, these remain true:

- existing engine stays the execution owner
- `state25 / forecast / belief / barrier` stay explanation-first `log_only` owners
- `canary` requires observed drift and audit evidence, not just a completed bridge chain

### Barrier Coverage Engineering as the Next Detailed Program

The next practical work item is not another owner philosophy document.
It is `Barrier coverage engineering`, which should answer:

- why rows become `low_skip`
- how `correct_wait` and `overblock` are separated
- how `loss_avoided_r / profit_missed_r / wait_value_r` stabilize
- how log-only barrier hints compare with actual engine decisions

Detailed references:

- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)

### Barrier Bias-Correction Extension

Barrier should now be read as:

- structure: sufficiently connected
- coverage: materially improved
- interpretation: still at risk of `avoided_loss` over-concentration

So the next practical work item is not new barrier philosophy.
It is bias correction and action-resolution refinement inside the existing BCE track.

Detailed follow-up:

- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)

## 목적

이 문서는 최근에 나온 외부 조언을 그대로 복사하는 대신, 현재 CFD 코드베이스 기준으로 무엇을 채택하고 무엇을 보류할지, 그리고 어떤 순서로 `실전 트레이더의 사고를 흉내내는 운영형 시스템`으로 끌어올릴지를 정리한 실행 문서다.

핵심 문제의식은 분명하다.

- `state25 / wait_quality / economic_target / candidate-gate-AI6`는 이미 많이 올라왔다.
- 반면 `forecast / evidence / belief / barrier`는 아직 runtime 의미에 비해 learning/outcome 연결이 약한 owner가 남아 있다.
- 따라서 지금부터의 작업은 점수 상수를 더 늘리는 것이 아니라, 각 owner를 `결과(outcome)`와 닫아 주는 것이다.

## 한 줄 진단

현재 시스템은 `자동매매 점수 시스템`을 넘어서기 직전까지 왔지만, 아직 `트레이더의 사고 체인` 전체가 outcome 학습 루프로 닫힌 상태는 아니다.

정확한 현재 상태는 이렇다.

- scene owner: 강함
- wait/economic owner: 강함
- candidate/gate/AI6 운영층: 강함
- forecast owner: 반쯤 닫힘
- evidence/belief/barrier owner: runtime core로는 중요하지만 learning owner로는 아직 부족함

즉 지금부터의 목표는 `판단 고도화`가 아니라 `판단 책임(owner) + 결과 감사(outcome audit) + seed/candidate/live 연결`이다.

## 외부 조언에서 채택할 것

아래 방향은 현재 코드베이스에도 그대로 맞다.

### 1. 판단 단위를 점수보다 결정 체인으로 본다

`entry_score`, `exit_score`, `wait_score`를 각각 독립 게임처럼 보는 대신 아래 체인으로 본다.

```text
scene -> forecast -> evidence -> belief -> barrier -> action
```

이 말은 기존 점수 필드를 당장 지우자는 뜻이 아니라, 앞으로의 주 판단 owner를 이 체인 위에 올리자는 뜻이다.

### 2. entry / wait / exit를 하나의 사고 체인으로 묶는다

실전 트레이더는 아래 세 질문을 같은 뿌리에서 판단한다.

- 지금 들어가야 하는가
- 아직 기다려야 하는가
- 내 가정이 깨졌으니 줄이거나 나와야 하는가

따라서 앞으로는 `행동(action)`만 다르고, 판단 근거는 같은 owner 체인을 공유하게 만들어야 한다.

### 3. forecast / evidence / belief / barrier를 각각 outcome과 연결한다

이 부분이 가장 중요하다.

- `forecast`는 왜 틀렸는지
- `evidence`는 진짜 신호였는지 가짜였는지
- `belief`는 버텨야 했는지 뒤집어야 했는지
- `barrier`는 잘 막은 것인지 과하게 막은 것인지

가 outcome label로 남아야 한다.

### 4. candidate 승격 기준을 경제성과 오류 안정성으로 옮긴다

앞으로의 승격 기준은 단순 accuracy가 아니라 아래 계열이어야 한다.

- net pnl
- drawdown 악화 여부
- giveback ratio
- overblock ratio
- wrong_hold ratio
- regime_miss ratio
- late_entry ratio

즉 `얼마나 잘 맞췄냐`보다 `얼마나 덜 망가지고 얼마나 더 돈이 되는 방향이냐`가 중심이 된다.

## 외부 조언에서 바로 적용하면 안 되는 것

외부 조언은 방향은 좋지만, 아래는 현재 코드베이스에 그대로 적용하면 과하다.

### 1. 점수 체계를 바로 삭제하는 것

지금은 `entry_score / exit_score / wait_score`를 지우면 안 된다.

현재 코드에서는 이 값들이 여전히 아래 역할을 하고 있다.

- baseline/legacy guard surface
- 디버그/관측 축
- 회귀 추적 기준

따라서 지금은 `삭제`가 아니라 `legacy/debug surface로 내리기`가 맞다.

### 2. CSV/SQLite 컬럼을 한 번에 대량 확장하는 것

최종적으로는 많은 필드가 필요할 수 있다. 하지만 지금 당장은 아래 순서가 맞다.

1. runtime bridge
2. replay/outcome bridge
3. closed-history seed enrichment
4. baseline auxiliary task
5. candidate compare
6. log-only overlay

즉 bridge로 살아남는 필드만 seed/DB 컬럼으로 승격해야 한다.

### 3. action을 바로 `argmax utility` live 엔진으로 바꾸는 것

최종 목표는 맞지만, 지금은 위험하다.

먼저 해야 하는 것은:

- utility shadow 계산
- log-only trace
- candidate compare 반영
- canary evidence

그 다음에야 bounded live로 넘어갈 수 있다.

### 4. 서비스 파일을 지금 당장 대규모로 분리하는 것

현재 코드베이스는 이미 `context_classifier`, `entry_service`, `observe_confirm_router`, `forecast_*`, `teacher_pattern_*` 계열로 분화가 시작돼 있다.

지금 필요한 것은 대규모 파일 분리보다:

- owner contract 고정
- replay bridge 생성
- seed enrichment
- compare/gate 연결

이다.

## 최종 목표 아키텍처

현재 코드 기준으로 실전형 구조를 다시 정의하면 아래와 같다.

```text
[Layer A] Scene Owner
state25 / regime / session / volatility / liquidity

[Layer B] Forecast Owner
앞으로 어떤 경로(path)로 흘러야 유리한가

[Layer C] Evidence Owner
지금 그 경로를 지지하는 근거가 진짜냐 가짜냐

[Layer D] Belief Owner
이 가정을 얼마나 더 유지해도 되는가 / 뒤집을 준비가 되었는가

[Layer E] Barrier Owner
지금 막아야 하는가 / 이 block의 비용은 무엇인가

[Layer F] Action Owner
enter / wait / hold / reduce / exit / flip

[Layer G] Outcome Owner
wait_quality / economic_target / counterfactual / post-trade audit
```

이때 원칙은 아래와 같다.

- `scene`은 장면 정의 owner
- `forecast`는 전개 예측 owner
- `evidence`는 근거 조합 owner
- `belief`는 thesis 지속성 owner
- `barrier`는 행동 차단 owner
- `action`은 새 의미를 만들지 않고 최종 행동만 결정
- `outcome`은 사후 감사와 학습 owner

## owner별 현재 수준과 목표 수준

### 1. Scene (`state25`)

- 현재 수준: 높음
- 현재 역할: scene owner로 거의 고정됨
- 목표 수준: 유지/보강

해야 할 일:

- `scene_id`, `scene_family`, `regime_family`, `volatility_regime`, `liquidity_regime`를 모든 downstream bridge의 anchor로 유지
- 각 owner replay와 compare를 scene 단위로 끊어 보기

### 2. Forecast

- 현재 수준: `runtime bridge + outcome bridge + seed enrichment + baseline aux + candidate compare + log-only overlay`까지 scaffold 완료
- 목표 수준: outcome quality가 실제로 열릴 정도의 데이터 누적과 path/error contract 강화

지금 남은 핵심:

- `expected_path`
- `realized_path`
- `forecast_error_type`
- `forecast_path_match_score`

를 안정적으로 붙이는 것

즉 forecast는 새로 시작할 owner가 아니라, 이미 만든 FSB 체인을 실제로 강하게 작동시키는 단계다.

### 3. Evidence

- 현재 수준: runtime core로는 중요, learning owner로는 낮음
- 목표 수준: `true_signal / fake_signal / trap_signal / exhaustion_signal / late_signal` owner

필수 방향:

- `evidence_total`
- `evidence_continuation`
- `evidence_reversal`
- `evidence_exhaustion`
- `evidence_conflict`
- `evidence_fragility`
- `dominant_evidence_family`

를 bridge 기준으로 정리하고, outcome label을 붙여야 한다.

### 4. Belief

- 현재 수준: owner 정체성은 좋음, bridge는 약함
- 목표 수준: hold/flip audit owner

필수 라벨:

- `correct_hold`
- `wrong_hold`
- `correct_flip`
- `missed_flip`
- `premature_flip`

추가 필드:

- `belief_persistence`
- `belief_decay_rate`
- `flip_readiness`
- `belief_instability`
- `belief_break_signature`

### 5. Barrier

- 현재 수준: runtime 차단 owner로는 강함, learning owner로는 약함
- 목표 수준: `비용을 가진 veto owner`

필수 라벨:

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`
- `relief_success`
- `relief_failure`

추가 개념:

- `barrier_cost_estimate`
- `late_entry_barrier`
- `event_risk_barrier`

### 6. Action

- 현재 수준: observe/confirm/action과 entry/exit service가 분리돼 있으나 같은 owner 체인으로 완전히 닫히지 않음
- 목표 수준: 하나의 판단 체인을 소비하는 lifecycle/action layer

핵심 액션 종류:

- `enter`
- `wait`
- `hold`
- `reduce`
- `exit`
- `flip`

중요 원칙:

action layer는 새 semantic 의미를 만들지 않는다. 위 owner들의 결과를 받아 실행 행동만 정한다.

## 현재 코드베이스에서 실제로 바꿔야 하는 방식

### 원칙 1. 모든 owner는 같은 승격 패턴을 따른다

아래 패턴을 owner마다 반복한다.

1. owner contract freeze
2. runtime bridge
3. replay/outcome bridge
4. closed-history seed enrichment
5. baseline auxiliary task
6. candidate compare/gate integration
7. log-only overlay
8. canary / bounded live

이 패턴을 이미 `forecast`에 한 번 적용하고 있다.

### 원칙 2. direct-use field와 learning-only field를 분리한다

runtime에서 바로 읽는 필드:

- 현재 시점에서 계산 가능한 hint
- 현재 시점 forecast summary
- 현재 시점 belief/barrier/evidence compact summary

learning-only 필드:

- future outcome
- closed-history final labels
- post-trade audit labels
- counterfactual labels

### 원칙 3. action utility는 바로 live가 아니라 shadow부터 간다

최종적으로는 아래 utility 체계로 가는 게 맞다.

```text
utility_enter
utility_wait
utility_hold
utility_reduce
utility_exit
utility_flip
```

하지만 구현 순서는 아래여야 한다.

1. runtime trace로 남김
2. replay outcome으로 검증
3. baseline/candidate auxiliary에 반영
4. log-only overlay
5. canary
6. bounded live

## 실전 문제를 owner 관점으로 다시 분해

### 1. 청산이 음수로 자주 나는 문제

이건 exit threshold 하나의 문제가 아니다. 보통 아래 owner 문제로 분해된다.

- `Belief`: wrong_hold / premature_flip
- `Forecast`: timing_wrong / regime_miss / volatility_miss
- `Evidence`: fake_signal / late_signal / exhaustion_signal
- `Barrier`: should_have_blocked / relief_failure

즉 앞으로는 손실 청산을 아래 방식으로 진단해야 한다.

- belief를 늦게 버렸는가
- 아직 hold가 맞는데 noise에 털렸는가
- forecast path가 맞았는데 timing을 틀렸는가
- 가짜 신호를 진짜 신호로 오인했는가
- barrier가 막았어야 하는데 못 막았는가

### 2. 진입을 너무 안 하는 문제

이건 barrier만의 문제가 아니다.

- `Barrier`가 overblock인지
- `Forecast`가 지나치게 wait-biased인지
- `Evidence` conflict가 높게 잡히는지
- `Belief`가 instability를 과하게 주는지

를 같이 봐야 한다.

따라서 앞으로는 `차단 수가 많다`가 아니라 `왜 차단되었고 그 block이 결과적으로 맞았는지`를 봐야 한다.

### 3. 기다림이 애매한 문제

현재 wait_quality는 좋은 시작점이다. 하지만 더 나아가려면 wait도 action core로 승격해야 한다.

즉 wait는 보조가 아니라 아래 중 하나여야 한다.

- `better_entry_after_wait`
- `avoided_loss_by_wait`
- `missed_move_by_wait`
- `delayed_loss_after_wait`
- `neutral_wait`

그리고 belief/barrier/evidence/forecast가 이 라벨에 upstream 이유로 연결돼야 한다.

## 채택 / 보류 / 지금 바로 구현

### 채택

- decision chain 중심 사고
- owner별 outcome label
- candidate 승격 기준의 경제성 전환
- barrier를 veto owner로 재정의
- belief를 hold/flip audit owner로 승격
- forecast를 path/error owner로 강화

### 보류

- 점수 체계 즉시 삭제
- CSV/SQLite 대량 컬럼 확장
- 서비스 파일 즉시 대규모 분리
- argmax utility live 전면 교체
- full auto bounded live 조기 개방

### 지금 바로 구현

1. `Forecast`는 현재 FSB 체인을 유지하면서 데이터 누적 및 `expected_path / realized_path / error_type` 강화
2. `Belief`를 다음 owner 승격 1순위로 삼기
3. `Barrier`를 그 다음 owner 승격 2순위로 삼기
4. `Evidence`를 그 다음 owner 승격 3순위로 삼기
5. `Action utility shadow`를 그 다음 단계에서 도입하기

## 다음 문서 형식

지금부터는 철학 문서를 더 늘리기보다, owner별 `승격 명세서`로 내려가야 한다.

즉 다음 단계 문서는 아래 성격을 가져야 한다.

- 방향 설명 문서가 아니다
- 구현 명세 문서다
- 라벨 이름만 적는 문서가 아니다
- `라벨 판정 규칙 / 실패 모드 / 최소 관측 지표 / 승격 중단 조건`이 있어야 한다

이 원칙은 [current_owner_promotion_spec_rollout_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_owner_promotion_spec_rollout_roadmap_ko.md)에 별도 로드맵으로 정리했다.

## 다음 실무 문서

다음부터는 아래 순서로 owner별 승격 명세서를 만든다.

1. `Belief owner 승격 명세서`
2. `Barrier owner 승격 명세서`
3. `Evidence owner 승격 명세서`
4. `Response Raw owner 승격 명세서`
5. `Action Utility Shadow 명세서`

이 중 첫 문서는 `Belief owner 승격 명세서`가 맞다.

이유:

- 현재 음수 청산과 hold/flip 오류를 가장 직접적으로 친다
- 하지만 `exit 전용 owner`로 좁히지 않고 `thesis persistence owner`로 유지해야 한다
- 다음 Barrier/Evidence 문서의 기준점 역할도 한다

현재 초안:

- [current_belief_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_belief_owner_promotion_spec_v1_ko.md)
- [current_barrier_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_owner_promotion_spec_v1_ko.md)

Belief spec에 추가로 반영한 실무 원칙:

- `adaptive threshold / adaptive horizon`은 v1에 바로 넣지 않고 v2 항목으로 보류
- precedence는 deterministic 규칙을 먼저 쓰고, margin score는 `conflict resolver`로만 사용
- `belief_input_trace_v1 / belief_action_hint_v1`를 남겨 Belief가 forecast/evidence/barrier와 action shadow를 잇는 owner가 되게 함

## 실제 구현 우선순위

### Phase 1. Forecast 마무리

목표:

- FSB 체인 위에 path/error contract를 보강
- forecast auxiliary readiness가 실제로 열리게 데이터 누적

산출물:

- `expected_path`
- `realized_path`
- `forecast_error_type`
- `forecast_path_match_score`

### Phase 2. Belief 승격

목표:

- `Belief-State25 bridge`
- belief replay/outcome bridge
- seed enrichment
- baseline auxiliary task
- candidate compare
- log-only trace

핵심 라벨:

- `correct_hold`
- `wrong_hold`
- `correct_flip`
- `missed_flip`
- `premature_flip`

이 phase는 반드시 아래까지 내려가야 한다.

- 라벨 판정 규칙
- 실패 모드
- 최소 관측 지표
- 승격 중단 조건

### Phase 3. Barrier 승격

목표:

- `Barrier-State25 bridge`
- barrier replay/outcome bridge
- block cost 추정
- overblock 탐지
- log-only trace

핵심 라벨:

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`
- `relief_success`
- `relief_failure`

### Phase 4. Evidence 승격

목표:

- evidence family decomposition
- true/fake/trap/exhaustion labeling
- fragility/conflict replay report
- log-only trace

핵심 라벨:

- `true_signal`
- `fake_signal`
- `trap_signal`
- `exhaustion_signal`
- `late_signal`

### Phase 5. Action Utility Shadow

목표:

- `enter / wait / hold / reduce / exit / flip` utility를 shadow로 계산
- post-trade audit과 counterfactual 평가를 붙임

중요:

이 단계도 처음엔 live 의사결정이 아니라 trace/log-only여야 한다.

## 완료 기준

아래가 보이면 이 문서의 방향이 실제로 닫힌 것이다.

1. 각 owner마다 `runtime bridge -> replay bridge -> seed enrichment -> baseline aux -> candidate compare`가 존재한다.
2. 각 owner마다 `라벨 판정 규칙 / 실패 모드 / 최소 관측 지표 / 승격 중단 조건`이 존재한다.
3. candidate compare가 `accuracy`뿐 아니라 `wrong_hold / overblock / regime_miss / fake_signal` 같은 구조 KPI를 본다.
4. wait/entry/exit가 개별 점수 축이 아니라 같은 decision chain trace에서 설명된다.
5. log-only / canary / bounded live가 owner별 evidence를 바탕으로 순차 개방된다.

## 최종 결론

현재 CFD 시스템을 실전형으로 올리는 길은 `점수 엔진을 더 복잡하게 만드는 것`이 아니다.

정답은 아래다.

- owner별 판단 책임을 분명히 하고
- 각 owner를 outcome과 직접 연결하고
- 그 outcome을 seed/baseline/candidate/live로 단계적으로 승격하고
- 마지막에야 action을 하나의 decision chain으로 통합한다

즉 지금부터의 작업은 `새 점수 추가`가 아니라 `semantic owner를 결과 학습 루프로 닫는 작업`이다.
