# XAU BTC Execution Tuning Short Roadmap

## 1. 목적

지금 필요한 것은 구조를 다시 만드는 것이 아니라,

- `XAU`는 상단 `SELL`을 더 빨리 잡고
- `BTC`는 하단 `BUY`를 덜 자주, 더 오래 들고 가고
- 공통적으로는 `probe -> confirm -> hold -> opposite edge exit`

가 더 자연스럽게 이어지게 하는 것이다.

즉 이번 로드맵은 `Position / Response / State`를 다시 설계하는 문서가 아니라,
이미 만든 semantic outputs를 실제 execution temperament에 더 잘 연결하는 짧은 작업 순서다.

---

## 2. 현재 진단

### 2-1. XAU

- 하단 `BUY` 쪽은 상대적으로 잘 보는데
- 상단 `SELL`은 늦거나 아예 안 나오는 장면이 있다
- 특히 `upper-edge reject`를
  - `probe`로 먼저 던지고
  - `confirm`에서 더 강하게 이어가는 구조가 약하다

### 2-2. BTC

- 하단 `BUY` 자체는 자주 읽는다
- 하지만
  - 같은 하단에서 반복 재진입하고
  - middle 흔들림에서 너무 빨리 정리하고
  - 결국 실제 계좌 기준으로는 수수료형 매매가 되기 쉽다

### 2-3. 공통

- `probe`는 semantic 상으로는 들어왔지만
- 실제 lot 분리와 `confirm add`는 아직 없다
- `Belief`, `Barrier`, `Forecast` 안에 좋은 값이 이미 많은데
- 실행층에서 아직 약하게만 쓰는 친구들이 남아 있다

---

## 3. 조정 방향

### 3-1. XAU

핵심 방향:

- `upper-edge probe SELL` 강화
- 상단 거절 persistence를 더 빨리 누적
- 좋은 상단 자리의 `SELL` 후보를 energy/soft block이 너무 쉽게 막지 않게

한 줄 요약:

`XAU는 lower buy bias를 줄이고 upper sell timing을 앞당긴다.`

### 3-2. BTC

핵심 방향:

- 같은 하단 반복 `BUY` 억제
- 하단 `BUY` 후 hold patience 강화
- `BB20 mid` 흔들림만으로 바로 exit하지 않게

한 줄 요약:

`BTC는 lower buy 빈도를 줄이고, 잡았으면 더 오래 들고 간다.`

### 3-3. 공통

핵심 방향:

- `probe`와 `confirm`를 실제 주문 구조로 분리
- `opposite edge`까지 가져가는 hold/exit 연결 강화
- runtime trace를 더 잘 남겨서 왜 안 샀는지, 왜 빨리 팔았는지 즉시 볼 수 있게

---

## 4. 짧은 실행 로드맵

## Phase SX1. XAU upper sell probe

### 목표

상단 `SELL`을 confirm-only에서 `probe + confirm` 구조로 앞당긴다.

### 손볼 곳

- [observe_confirm_router.py](/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)
- [entry_service.py](/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [belief_engine.py](/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/belief_engine.py)

### 할 일

- `UPPER_EDGE + upper_reject_down + nearby resistance/trendline`일 때
  - `upper_reject_probe_observe`가 더 빨리 뜨게
- `sell_belief`, `sell_streak`가 상단 거절 구간에서 더 빨리 쌓이게
- 상단 `SELL_ONLY` 장면에서 `energy_soft_block` 과막힘 여부 재점검

### 기대 효과

- 꼭대기 부근 `SELL`을 지금보다 1~2박자 빨리 잡음

### 리스크

- continuation 장면에서 너무 빠른 역추세 `SELL`이 늘 수 있음

---

## Phase SX2. BTC lower hold + duplicate-edge suppression

### 목표

하단 `BUY`를 덜 자주 하고, 잡았으면 더 오래 들고 간다.

### 손볼 곳

- [entry_engines.py](/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [wait_engine.py](/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [exit_profile_router.py](/Users/bhs33/Desktop/project/cfd/backend/services/exit_profile_router.py)

### 할 일

- `duplicate-edge` 재진입 억제 강화
- `btc_lower_hold_bias`를 더 실제적으로 활용
- `BB20 mid` 흔들림만으로 `exit_now`가 쉽게 이기지 않게
- `thesis break`와 `middle noise`를 더 분리

### 기대 효과

- 반복 진입/청산 감소
- fee donation 형태 감소

### 리스크

- 진짜 breakdown에서 손실이 더 깊어질 수 있음

---

## Phase SX3. Probe size / confirm add

### 목표

지금 있는 `probe`를 semantic-only가 아니라 실제 주문 구조로 만든다.

### 손볼 곳

- [entry_try_open_entry.py](/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_service.py](/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)

### 할 일

- `probe`는 작은 lot
- `confirm`은 add 또는 normal size
- `probe fail`은 빠르게 컷
- `confirm success`는 hold로 연결

### 기대 효과

- 좋은 꼭대기/바닥 가격을 더 잘 잡음
- 동시에 완전한 도박 선진입은 아님

### 리스크

- same thesis 누적 주문 관리가 복잡해짐

---

## Phase SX4. Edge-to-edge hold / exit

### 목표

좋은 진입이면 반대 edge까지 가져가는 구조를 강화한다.

### 손볼 곳

- [wait_engine.py](/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [exit_profile_router.py](/Users/bhs33/Desktop/project/cfd/backend/services/exit_profile_router.py)
- [exit_recovery_predictor.py](/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_predictor.py)

### 할 일

- `hold through noise`
- `premature exit risk`
- `edge_to_edge_completion`

를 symbol-aware하게 더 반영

### 기대 효과

- `XAU`: 하단 `BUY` 후 상단 정리
- `BTC`: 하단 `BUY` 후 중간 흔들림에 덜 털림

### 리스크

- opposite edge 인식이 약하면 늦은 청산 가능

---

## Phase SX5. Runtime acceptance

### 목표

차트 체감과 runtime 이유가 실제로 맞는지 본다.

### 체크포인트

#### XAU

- 상단에서 `upper_reject_probe_observe`가 실제로 뜨는가
- `SELL` 후보를 `energy_soft_block`이 너무 쉽게 죽이지 않는가

#### BTC

- `btc_lower_hold_bias = true`가 실제로 찍히는가
- `duplicate-edge` 재진입이 줄었는가
- `winner != exit_now`가 더 자주 나오는가

#### 공통

- `probe`가 실제 lot 구조로 작동하는가
- `confirm add`가 너무 공격적이지 않은가

---

## 5. 조정하면서 생길 수 있는 문제

### XAU 쪽

- 상단 `SELL`을 앞당기면
  - continuation 장면에서 premature short가 늘 수 있다

### BTC 쪽

- hold를 늘리면
  - fee churn은 줄어도
  - 진짜 붕괴 때 손실이 더 커질 수 있다

### 공통

- symbol-aware 분기가 늘수록
  - 유지보수 난도
  - 튜닝 난도
가 같이 올라간다

즉 방향은 맞지만,
`더 빨리 진입`과 `더 오래 보유`는 항상
`가짜 신호 증가`와 `손실 깊이 증가`
리스크를 같이 가진다.

---

## 6. 지금 놀고 있거나 덜 쓰는 친구

### 6-1. 이미 있는데 덜 쓰는 값

- `probe_candidate_v1`
- `entry_probe_plan_v1`
- `flip_readiness`
- `belief_instability`
- `duplicate_edge_barrier_v1`
- `forecast_effective_policy_v1`

### 6-2. 수집은 되지만 live 영향이 약한 값

- `advanced_input_activation_state`
- `tick_flow_state`
- `order_book_state`

이 값들은 harvest와 trace는 되지만,
실전 execution에서 체감 영향은 아직 약하다.

### 6-3. 추가되면 좋은 것

- 실제 `probe lot`과 `confirm add` 분리
- symbol-aware invalidation depth
- same-thesis reentry cooldown
- runtime trace top-level promotion

---

## 7. 이번 짧은 로드맵의 우선순위

1. `SX1 XAU upper sell probe`
2. `SX2 BTC lower hold + duplicate-edge suppression`
3. `SX3 probe size / confirm add`
4. `SX4 edge-to-edge hold / exit`
5. `SX5 runtime acceptance`

---

## 8. 한 줄 결론

지금 필요한 건 새 이론이 아니라,

`XAU는 upper sell을 더 빨리, BTC는 lower buy를 덜 자주 더 오래, 공통적으로는 probe/confirm/hold/edge-exit를 실제 execution 구조로 완성하는 것`

이다.
