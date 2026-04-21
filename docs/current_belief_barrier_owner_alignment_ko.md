# Belief / Barrier 처음부터 다시 정리

## 목적

이 문서는 `Belief`와 `Barrier`를 `state25`, `forecast`, `wait_quality`, `economic_target`과 같은 급의 owner로 다시 정리하기 위한 기준 문서다.

핵심은 두 가지다.

1. `Belief`는 `증거가 시간축에서 유지되는가`를 맡는 owner다.
2. `Barrier`는 `좋아 보여도 지금 막아야 하는가`를 맡는 owner다.

즉 이 둘은 서로 비슷한 이름의 보조 점수가 아니라, 서로 다른 질문을 맡는 별도 semantic owner다.

## 한 줄 정의

| Owner | 핵심 질문 | 출력 | 진짜 역할 |
| --- | --- | --- | --- |
| `Belief` | `이 증거가 계속 유지되는가` | `BeliefState` | 증거의 시간축 누적, persistence, reconfirmation, flip 준비도 |
| `Barrier` | `좋아 보여도 지금 막아야 하는가` | `BarrierState` | 구조적 차단, friction, conflict, chop, liquidity, policy block |

## Belief

### Belief가 맡는 질문

`Belief`는 방향을 새로 예측하는 owner가 아니다.

`Belief`가 맡는 질문은 이것이다.

- 지금 나온 증거가 잠깐 반짝이는 것인지
- 같은 thesis가 몇 step 동안 유지되고 있는지
- 반대 thesis로 flip될 준비가 되어 있는지
- 지금 confirm 쪽으로 더 기울어도 되는지, wait를 더 두어야 하는지

즉 `Belief`는 `증거의 시간축 해석` owner다.

### Belief의 실제 출력

코드 기준 출력은 `BeliefState`다.

핵심 필드는 다음 계열이다.

- `buy_belief`, `sell_belief`
- `buy_persistence`, `sell_persistence`
- `belief_spread`
- `flip_readiness`
- `belief_instability`
- `dominant_side`, `dominant_mode`
- `buy_streak`, `sell_streak`
- `transition_age`

즉 `Belief`는 단순 방향 점수가 아니라, `지속성 + 전환 준비도 + 불안정성`을 같이 본다.

### Belief가 하면 안 되는 일

`Belief`는 아래 일을 하면 안 된다.

- `position`을 다시 정의하기
- `response`를 다시 정의하기
- `state25` scene 자체를 다시 정의하기
- `forecast`처럼 다음 branch를 직접 예측하기
- `Barrier`처럼 구조 차단을 계산하기
- 최종 entry action을 직접 결정하기

즉 `Belief`는 `지속성 owner`이지 `행동 owner`가 아니다.

### 현재 코드 위치

- 생성: [belief_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py)
- 런타임 조립: [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- wait bias 소비: [entry_wait_belief_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_wait_belief_bias_policy.py)
- forecast 입력 소비: [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

코드 owner 계약도 이미 분명하다.

- `belief_thesis_persistence_only_v1`
- `Belief measures thesis persistence and reconfirmation over time.`

즉 Belief는 이미 코드상으로도 `persistence owner`로 선언돼 있다.

## Barrier

### Barrier가 맡는 질문

`Barrier`는 방향을 맞히는 owner가 아니다.

`Barrier`가 맡는 질문은 이것이다.

- 지금 thesis가 좋아 보여도 실제로 행동해도 되는지
- middle chop이 심해서 지금은 막아야 하는지
- conflict가 커서 wait/observe가 맞는지
- liquidity나 execution friction 때문에 지금은 불리한지
- direction policy가 현재 장면에서 막는 쪽인지

즉 `Barrier`는 `행동 차단 / relief` owner다.

### Barrier의 실제 출력

코드 기준 출력은 `BarrierState`다.

핵심 필드는 다음 계열이다.

- `buy_barrier`, `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

metadata 쪽에는 다음 같은 relief/block 이유가 같이 붙는다.

- `edge_turn_relief_score`
- `breakout_fade_barrier_score`
- `execution_friction_barrier_score`
- `event_risk_barrier_score`

즉 `Barrier`는 방향 예측이 아니라, `좋은 thesis라도 지금은 막아야 하는 이유`를 구조적으로 모아준다.

### Barrier가 하면 안 되는 일

`Barrier`는 아래 일을 하면 안 된다.

- 새로운 방향 thesis를 만들기
- `state25` scene owner 역할을 가져가기
- `Belief`처럼 persistence를 계산하기
- `Forecast`처럼 다음 branch를 해석하기
- 최종 entry candidate를 새로 만들기

즉 `Barrier`는 `차단 owner`이지 `판단 전체를 대신하는 owner`가 아니다.

### 현재 코드 위치

- 생성: [barrier_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/barrier_engine.py)
- 런타임 조립: [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- forecast 입력 소비: [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

코드 owner 계약도 이미 분명하다.

- `barrier_blocking_only_v1`
- `Barrier is not the layer that finds entries. Barrier decides whether the current candidate should be blocked now.`

즉 Barrier는 이미 코드상으로도 `blocking owner`로 선언돼 있다.

## Belief와 Barrier의 차이

둘은 비슷해 보이지만 완전히 다른 축이다.

### Belief

- 질문: `이 thesis가 계속 유지되는가`
- 시간축: 강함
- 대표 역할: persistence, reconfirmation, flip readiness
- 판단 효과: `confirm 쪽으로 더 가도 되는가 / wait를 더 해야 하는가`

### Barrier

- 질문: `지금 행동을 막아야 하는가`
- 시간축: 약하고 구조축이 강함
- 대표 역할: block, relief, friction, chop, liquidity
- 판단 효과: `좋아 보여도 지금은 막아야 하는가`

한 줄로 줄이면:

- `Belief`는 thesis의 `지속성`
- `Barrier`는 행동의 `차단`

이다.

## state25 / Forecast / Wait / Economic과의 연결

이 둘을 `state25`와 같은 급으로 맞춘다는 건, `state25` 안으로 흡수한다는 뜻이 아니다.

역할을 분리한 채 bridge로 묶는다는 뜻이다.

### state25와의 관계

- `state25`는 scene owner다.
- 지금 장면이 어떤 구조인지 정리한다.
- `Belief`와 `Barrier`는 그 장면 위에서 각각
  - thesis가 유지되는지
  - 행동을 막아야 하는지
  를 덧붙인다.

즉 `state25`가 장면을 정하고, `Belief/Barrier`가 장면 위의 지속성과 차단을 보강한다.

### Forecast와의 관계

- `Forecast`는 branch owner다.
- `Forecast`는 `BeliefState`, `BarrierState`를 입력으로 소비한다.
- `Forecast`는 이 둘을 새로 만들지 않는다.

즉 관계는 이렇다.

`state25 scene -> belief persistence / barrier blocking -> forecast branch`

### Wait / Economic과의 관계

- `wait_quality`는 결과적으로 기다림이 좋았는지 평가한다.
- `economic_target`은 실제로 돈이 되었는지 평가한다.

여기서

- `Belief`는 `왜 더 기다렸는지 / 왜 confirm release를 줬는지`
- `Barrier`는 `왜 막았는지 / 왜 relief를 줬는지`

를 설명하는 upstream owner가 된다.

즉 이 둘이 제대로 bridge되면

- 더 좋은 진입
- 더 좋은 기다림
- 더 좋은 청산

을 설명하는 기반으로 올라간다.

## 왜 지금 다시 맞춰야 하나

현재 런타임에서는 `Belief`와 `Barrier`가 이미 쓰이고 있다.

- `Belief`는 wait bias와 forecast에 들어간다.
- `Barrier`는 observe/confirm과 guard 판단에 들어간다.

하지만 아직 `state25`처럼 학습 루프와 문서 중심축으로 완전히 승격된 상태는 아니다.

그래서 지금 필요한 건:

1. `Belief / Barrier`의 owner 경계를 다시 고정하고
2. `state25 / forecast / wait / economic`과 bridge 계약을 만들고
3. learning seed / replay / baseline / candidate 루프 안으로 승격하는 것

이다.

## 앞으로 같은 급으로 맞출 때 필요한 일

다음 단계는 보통 이 순서가 맞다.

1. `Belief / Barrier bridge contract`
- runtime direct-use field
- replay/learning-only field
- no-leakage boundary

2. `Belief-State25 learning bridge`
- 어떤 scene에서 어떤 persistence가 나왔는지
- 그 persistence가 좋은 wait / 좋은 entry / 좋은 exit로 이어졌는지

3. `Barrier-State25 learning bridge`
- 어떤 scene에서 어떤 block/relief가 나왔는지
- 그 block이 손실 회피였는지, 기회 손실이었는지

4. `seed / baseline / candidate 연결`
- auxiliary task
- bridge report
- log-only overlay

## 최종 정리 표

| Owner | 질문 | 출력 | 지금 맡아야 하는 역할 | 맡으면 안 되는 역할 |
| --- | --- | --- | --- | --- |
| `Belief` | `이 증거가 계속 유지되는가` | `BeliefState` | persistence, reconfirmation, flip readiness, instability | barrier 계산, scene 재정의, 직접 entry 결정 |
| `Barrier` | `좋아 보여도 지금 막아야 하는가` | `BarrierState` | blocking, relief, friction, chop, liquidity, policy block | 방향 예측, persistence 계산, 새 candidate 생성 |

## 한 줄 결론

`Belief`는 `증거의 지속성 owner`, `Barrier`는 `행동의 차단 owner`다.

이 둘은 `state25`에 흡수될 대상이 아니라, `state25 / forecast / wait / economic`과 같은 급의 별도 owner로 남긴 채 bridge로 묶어야 한다.
