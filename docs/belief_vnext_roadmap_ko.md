# Belief vNext Roadmap

## 1. 목적

이 문서는 현재 시스템에서 `Belief`가 무엇을 의미해야 하는지, 현재 어디까지 구현되어 있는지, 무엇이 약하고 무엇이 꼭 추가되어야 하는지, 그리고 어떤 순서로 손봐야 하는지를 정리한 로드맵이다.

핵심 정의는 이 한 문장으로 고정한다.

`Belief = 현재 thesis가 시간축에서 얼마나 유지되고 재확인되고 있는지를 나타내는 누적 확신 레이어`

더 짧게 쓰면:

`Belief = 근거의 지속성`

---

## 2. PRSEB 큰 그림에서 Belief의 자리

### Position

- 현재 가격이 어디에 있는가
- 예: `box lower`, `bb upper`, `15M support 근처`, `trendline proximity`

즉:

- `Position = 위치`

### Response

- 지금 무슨 사건이 벌어졌는가
- 예: `lower_hold_up`, `upper_reject_down`, `mid_reclaim_up`, `failed_breakdown_strength`

즉:

- `Response = 사건`

### Evidence

- 지금 이 사건이 왜 의미가 있는가
- 예: `support_hold`, `trend_support_hold`, `micro_bull_reject`, `structure support_hold_confirm`

즉:

- `Evidence = 순간 근거`

### Belief

- 그 순간 근거가 한 봉 반짝인가
- 2~3봉 유지되는가
- 같은 방향 근거가 재확인되는가
- 기존 thesis가 유지되는가, 아니면 깨지는가

즉:

- `Belief = 시간 누적 확신`

### State

- 지금 장이 이 확신을 믿어도 되는 환경인가
- 예: `RANGE_SWING`, `SESSION_EDGE_ROTATION`, `BREAKOUT_EXPANSION`, `HIGH_EVENT_RISK`

즉:

- `State = 시장 성격 / 신뢰도 / 인내심`

---

## 3. 왜 Belief가 꼭 필요하나

`Evidence`만 있으면 한 봉짜리 강한 wick, 장악형, micro reclaim 같은 신호는 잘 잡힌다.

하지만 그것만으로는 다음 문제가 생긴다.

- 한 봉 반짝 반응에 너무 빨리 들어감
- 좋은 반등인데도 아직 누적 확신이 없어서 기다릴지 들어갈지 흔들림
- 좋은 진입 후 중간 흔들림에 너무 빨리 청산함
- 반대 thesis 전환이 정말 시작된 건지, 그냥 잡음인지 구분이 어려움

즉 `Belief`가 없으면 시스템은 다음 둘 중 하나로 치우친다.

- 너무 빠르게 반응하는 시스템
- 너무 오래 기다리는 시스템

Belief는 그 중간을 잡아준다.

---

## 4. 현재 Belief 구현 상태

현재 구현 파일:

- [belief_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py)
- [models.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)

현재 `BeliefState` 1급 출력 필드:

- `buy_belief`
  - 현재 `BUY thesis` 누적 확신
- `sell_belief`
  - 현재 `SELL thesis` 누적 확신
- `buy_persistence`
  - `BUY thesis` 연속 유지 정도
- `sell_persistence`
  - `SELL thesis` 연속 유지 정도
- `belief_spread`
  - `buy_belief - sell_belief`
  - 양수면 buy 쪽 우세, 음수면 sell 쪽 우세
- `transition_age`
  - 현재 dominant thesis가 몇 봉째 유지 중인가

현재 metadata에만 있는 내부 값:

- `buy_reversal_belief`
  - `buy reversal evidence` 누적값
- `sell_reversal_belief`
  - `sell reversal evidence` 누적값
- `buy_continuation_belief`
  - `buy continuation evidence` 누적값
- `sell_continuation_belief`
  - `sell continuation evidence` 누적값
- `buy_streak`
  - buy 우세가 몇 봉 연속 유지됐는가
- `sell_streak`
  - sell 우세가 몇 봉 연속 유지됐는가
- `global_dominant_side`
  - `BUY`, `SELL`, `BALANCED`
- `global_dominant_mode`
  - `reversal`, `continuation`, `balanced`

현재 업데이트 규칙:

- `belief_update_mode = ema_rise_decay`
  - 상승 시 빠르게 반영, 하강 시 완만하게 감쇠
- `persistence_mode = activation_streak_window`
  - activation threshold를 넘는 방향이 연속되면 persistence 증가
- `side_dominance_mode = belief_spread_deadband`
  - buy/sell belief 차이가 deadband 안이면 balanced
- `merge_mode = capped_dominant_merge`
  - reversal/continuation belief를 dominant + support 방식으로 합침

즉:

- 현재 Belief의 뼈대는 이미 존재한다
- 완전히 빈 상태는 아니다

---

## 5. 현재 Belief가 실제로 연결된 곳

### 5-1. ContextClassifier -> Belief 생성

파일:

- [context_classifier.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)

현재:

- `build_belief_state(...)` 호출
- `belief_state_v1`가 runtime metadata에 기록됨

### 5-2. ObserveConfirm

파일:

- [observe_confirm_router.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)

현재 실제 사용:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`

현재 역할:

- execution readiness 보정
- confirm / wait 쪽에 약한 가산

평가:

- 연결은 되어 있음
- 하지만 아직 Belief가 핵심 owner는 아님

### 5-3. Barrier

파일:

- [barrier_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/barrier_engine.py)

현재 실제 사용:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`

현재 역할:

- chop/conflict 상황에서 barrier 조절

평가:

- 잘 연결되어 있음
- Belief의 현재 가장 자연스러운 소비자 중 하나

### 5-4. Forecast

파일:

- [forecast_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

현재 실제 사용:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

현재 역할:

- confirm 성공 확률
- reversal 성공 확률
- continuation 성공 확률
- management 기대치

평가:

- 잘 연결되어 있음

---

## 6. 현재 Belief가 약하거나 빠진 연결

### 6-1. WaitEngine

파일:

- [wait_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

현재 문제:

- `State`는 wait bias를 강하게 조정하지만
- `Belief`는 good wait / bad wait 판단에 직접 거의 안 먹는다

그래서 생기는 문제:

- thesis가 이미 2~3봉 유지됐는데도 계속 `WAIT`
- 반대로 한 봉짜리 반짝인데 너무 일찍 들어감

### 6-2. Exit / Hold

파일:

- [exit_profile_router.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/exit_profile_router.py)
- [wait_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

현재 문제:

- `hold_patience`는 많이 `State` 중심
- `Belief`의 누적 확신이 보유 지속에 직접 강하게 반영되지 않음

그래서 생기는 문제:

- 좋은 하단 진입 후 중간 흔들림에서 조기청산
- `SL 두고 방관`해야 할 자리를 중간 판단으로 흔듦

### 6-3. Thesis Flip / Opposite Entry

현재 문제:

- 기존 방향 belief가 깨지고
- 반대 방향 belief가 쌓이는지
- 그걸 독립적으로 해석하는 구조가 약함

그래서 생기는 문제:

- 상단/하단 edge에서 반대 thesis 전환 감지가 불안정
- 반대 move 진입이 `Response`만으로 과민하거나 둔감함

### 6-4. 1급 출력 부족

현재 문제:

- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`
가 metadata 안에만 있음

그래서 생기는 문제:

- 다른 레이어가 Belief를 읽을 때 구조적으로 쓰기 불편함
- runtime/log에서 빠르게 해석하기 어려움

---

## 7. Belief가 꼭 가져야 하는 필드

### A. 반드시 유지해야 하는 1급 필드

- `buy_belief`
  - buy thesis 누적 확신
- `sell_belief`
  - sell thesis 누적 확신
- `buy_persistence`
  - buy thesis 유지 정도
- `sell_persistence`
  - sell thesis 유지 정도
- `belief_spread`
  - buy vs sell 우세 차이
- `transition_age`
  - 현재 dominant thesis 지속 나이

이 6개는 core다.

### B. 1급 필드로 승격을 추천하는 값

현재 metadata에는 있지만 1급 필드로 승격하면 좋은 값:

- `dominant_side`
  - 현재 global dominant side
  - 예: `BUY`, `SELL`, `BALANCED`
- `dominant_mode`
  - dominant side가 reversal인지 continuation인지
- `buy_streak`
  - buy activation 연속 카운트
- `sell_streak`
  - sell activation 연속 카운트

승격 이유:

- Wait/Exit/Flip이 직접 쓰기 쉬워짐
- runtime 디버깅이 쉬워짐

### C. 신규로 고려할 값

- `flip_readiness`
  - 반대 thesis 전환 준비도
- `belief_instability`
  - buy/sell 우세가 너무 자주 뒤집히는지
- `belief_decay_rate`
  - 기존 thesis가 얼마나 빨리 약해지는지
- `last_reinforced_side`
  - 최근 강화된 방향
- `last_reinforced_age`
  - 최근 강화 이후 몇 봉 지났는지

주의:

- 신규 필드는 많이 늘리지 않는다
- `1급 필드`는 핵심만
- 나머지는 metadata 후보로 둔다

---

## 8. Belief가 꼭 연결돼야 하는 소비 레이어

### A. ObserveConfirm

역할:

- 한 봉 반짝이면 `WAIT`
- persistence가 쌓이면 `CONFIRM` 가산
- `belief_spread`가 좁으면 observe 유지

필수 연결값:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`
- 추천 추가: `dominant_side`, `dominant_mode`

### B. WaitEngine

역할:

- 기다림이 좋은 기다림인지 나쁜 기다림인지 판단

필수 연결값:

- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`
- 추천 추가: `flip_readiness`

예:

- persistence가 아직 낮으면 wait 유지 가능
- persistence가 충분히 높은데 계속 wait면 wait 완화

### C. ExitProfileRouter / hold policy

역할:

- 좋은 진입 후 belief가 유지되면 더 오래 보유
- belief가 꺾이면 조기 정리 허용

필수 연결값:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

예:

- `BUY` 포지션인데 `buy_belief`와 `buy_persistence`가 유지되면 hold patience 증가
- 반대로 `sell_belief`가 상승하고 `belief_spread`가 음수로 넘어가면 exit 압력 증가

### D. Thesis Flip / opposite entry

역할:

- 기존 thesis가 끝나고 반대 thesis가 새로 시작됐는지 확인

필수 연결값:

- `belief_spread`
- `transition_age`
- `dominant_side`
- `dominant_mode`
- 추천 추가: `flip_readiness`

예:

- 기존 `BUY` belief가 약해지고
- `SELL` belief가 강해지고
- `transition_age`가 반대편에서 2~3봉 유지되면
- 그때 반대 진입 thesis 성립

---

## 9. Belief가 하면 안 되는 것

Belief는 강해져야 하지만, 다음 역할을 가져가면 안 된다.

- Position 재정의
  - 위치 판단은 Position owner
- Response 재정의
  - 사건 판단은 Response owner
- State 재정의
  - 장 성격 판단은 State owner
- 단독 side 결정
  - Belief 혼자 `BUY/SELL`를 결정하면 안 됨

즉:

- `Belief는 확신 누적기`
- `Belief는 의미 생성기 아님`

---

## 10. Belief vNext 로드맵

### Phase B0. Freeze

목표:

- Belief의 역할을 고정

고정 문장:

`Belief는 thesis의 지속성과 재확인을 나타내는 누적 확신 레이어다.`

완료 기준:

- Position / Response / State와 owner 충돌 없음

### Phase B1. Output promotion

목표:

- metadata 안에만 있는 중요한 값을 1급 출력으로 끌어올림

대상:

- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`

완료 기준:

- `BeliefState` 1급 출력으로 직접 접근 가능
- runtime에서 빠르게 해석 가능

### Phase B2. Wait integration

목표:

- good wait / bad wait에 Belief를 직접 반영

연결 대상:

- [wait_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

주요 규칙:

- persistence 낮음 -> wait 유지 가능
- persistence 높음 + belief spread 확실 -> wait 완화
- spread deadband 안 -> wait 유지

완료 기준:

- `한 봉 반짝` WAIT는 유지
- `2~3봉 누적 confirm`은 덜 놓침

### Phase B3. Hold / Exit integration

목표:

- 좋은 진입 후 belief 유지 시 hold patience 증가

연결 대상:

- [exit_profile_router.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/exit_profile_router.py)
- [wait_engine.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

주요 규칙:

- position side belief 유지 -> hold patience 증가
- opposite belief 상승 -> fast exit risk 상승

완료 기준:

- 좋은 하단/상단 진입 후 중간 흔들림에 덜 털림

### Phase B4. Flip readiness

목표:

- 반대 thesis 전환 준비도를 Belief가 말하게 함

후보 필드:

- `flip_readiness`
- `belief_instability`

주요 규칙:

- old side belief decay
- opposite side belief rise
- transition_age >= 2~3

완료 기준:

- edge turn / thesis flip 해석이 더 안정적

### Phase B5. Runtime acceptance

목표:

- 실제 차트 사례에서 Belief 해석이 자연스러운지 확인

확인할 것:

- 하단 반등 초입에서 persistence가 어떻게 쌓이는가
- 상단 거절 초입에서 sell belief가 어떻게 올라오는가
- 한 봉 반짝인데 confirm으로 튀는가
- 좋은 진입 후 hold 구간에서 belief가 유지되는가

완료 기준:

- 스크린샷 기준 체감과 belief 출력이 맞아들어감

### Phase B6. Pre-ML readiness

목표:

- 나중에 ML calibration이 붙을 때 Belief를 feature로 안전하게 쓸 수 있게 함

필수 출력:

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`
- `dominant_side`
- `dominant_mode`

추천 출력:

- `flip_readiness`
- `belief_instability`

완료 기준:

- ML 없이도 의미적으로 충분히 설명 가능
- ML이 붙어도 owner 충돌 없음

---

## 11. 우선순위

지금 바로 중요한 순서:

1. `B1 Output promotion`
2. `B2 Wait integration`
3. `B3 Hold / Exit integration`
4. `B4 Flip readiness`

이유:

- 지금 가장 체감되는 문제는 `진입을 너무 기다림`과 `좋은 진입 후 너무 흔들림`
- 따라서 wait와 hold에 Belief가 먼저 먹어야 함

---

## 12. 한 줄 결론

현재 `Belief`는 완전히 비어 있지 않고, 이미 `ObserveConfirm`, `Barrier`, `Forecast`에는 연결되어 있다.

하지만 앞으로 시스템이 진짜 좋아지려면:

- `Belief = 근거의 지속성`
으로 역할을 고정하고
- `Wait`
- `Hold / Exit`
- `Thesis Flip`

이 세 방향으로 더 강하게 연결해야 한다.

즉 Belief vNext의 핵심은:

`순간 근거를 확신으로 바꾸고, 그 확신이 언제 유지되고 언제 무너지는지를 시스템이 시간축으로 읽게 만드는 것`
