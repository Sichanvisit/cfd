# State S0 Freeze

## 목적

이 문서는 `State`의 역할을 더 이상 흔들리지 않게 고정하기 위한 freeze 문서다.

이번 freeze의 목적은 단순하다.

- `State`가 무엇을 owner로 가져가는지 고정한다.
- `State`가 무엇을 owner로 가져가면 안 되는지 고정한다.
- 이후 `State` 개선은 구조 변경이 아니라 입력 확장과 execution 연결 강화 중심으로만 가게 만든다.

---

## 고정 문장

`State는 Position도 아니고 Response도 아니다. State는 시장 성격과 신뢰도, 인내심을 말한다.`

---

## State가 owner로 가져가는 것

### 1. Regime interpretation

State는 지금 장이 어떤 장인지 해석한다.

예:

- `RANGE_SWING`
- `RANGE_COMPRESSION`
- `TREND_PULLBACK`
- `BREAKOUT_EXPANSION`
- `CHOP_NOISE`
- `SHOCK`

### 2. Topdown bias interpretation

State는 큰지도가 어느 쪽으로 더 기울어 있는지 말한다.

예:

- `topdown_bull_bias`
- `topdown_bear_bias`
- `big_map_alignment_gain`
- `topdown_state_label`

### 3. Market quality interpretation

State는 지금 반응을 얼마나 믿을 만한지 말한다.

예:

- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `liquidity_penalty`
- `volatility_penalty`
- `quality_state_label`

### 4. Patience and execution temperament

State는 지금 기다릴지, 확인할지, 오래 들고 갈지에 대한 시장 성격을 말한다.

예:

- `wait_patience_gain`
- `confirm_aggression_gain`
- `hold_patience_gain`
- `fast_exit_risk_penalty`
- `patience_state_label`

---

## State가 owner로 가져가면 안 되는 것

### 1. Position location identity

State는 아래를 직접 owner로 가져가면 안 된다.

- 박스 상단/하단/중앙 그 자체
- 볼린저 상단/하단/중앙 그 자체
- MA/추세선 위아래 위치 그 자체

이건 `Position` owner다.

### 2. Response event identity

State는 아래를 직접 owner로 가져가면 안 된다.

- 지지 받침
- 지지 붕괴
- 저항 거절
- 저항 돌파
- reclaim
- lose

이건 `Response` owner다.

### 3. Direct buy/sell side identity

State는 `BUY` / `SELL` 방향 identity를 직접 만들면 안 된다.

State는 오직

- 더 믿게 하거나
- 덜 믿게 하거나
- 더 기다리게 하거나
- 덜 기다리게 하거나
- 더 오래 들고 가게 하거나
- 빨리 정리하게 하는

보정 레이어여야 한다.

### 4. Trigger event ownership

State는 진입 trigger 자체를 만들면 안 된다.

trigger owner는 항상:

- `Position + Response + ObserveConfirm`

조합 쪽에 남아 있어야 한다.

---

## canonical cluster 고정

State는 당분간 아래 4개 canonical cluster로 고정한다.

1. `regime_state`
2. `topdown_state`
3. `quality_state`
4. `patience_state`

중요한 점:

- 입력 변수는 더 늘어날 수 있다.
- 하지만 최종 State cluster는 먼저 이 4개를 유지한다.
- 즉 `State`를 또 다른 6축처럼 무한 확장하지 않는다.

---

## freeze 이후 허용되는 변화

### 허용

- 입력 변수 추가
- 입력 품질 개선
- label 정교화
- execution layer 연결 강화
- gain / penalty / patience 숫자 보정

### 비허용

- State가 Position처럼 위치 identity를 먹는 변경
- State가 Response처럼 사건 identity를 먹는 변경
- State가 BUY/SELL side를 직접 결정하는 변경
- State cluster를 이유 없이 계속 쪼개는 변경

---

## 코드 계약

State freeze 이후 `state_vector_v2.metadata`에는 아래 계약이 남아 있어야 한다.

- `semantic_owner_contract = state_market_trust_patience_only_v1`
- `state_freeze_phase = S0`
- `canonical_state_clusters_v1`
- `semantic_owner_scope`

의미:

- `State`는 시장 성격/신뢰도/인내심 owner다
- Position/Response identity를 넘보지 않는다
- direct side identity를 만들지 않는다

---

## freeze 이후 다음 우선순위

freeze가 끝나면 바로 다음은 이 순서가 맞다.

1. 이미 있는데 안 쓰는 입력을 State에 먹이기
2. session 기반 state 붙이기
3. topdown spacing / slope 붙이기
4. spread / volume stress 붙이기
5. State를 ObserveConfirm / Wait / Exit에 더 직접 연결하기

즉 freeze는 끝이 아니라,
`State를 흔들지 않는 기준 위에서 입력과 연결성을 강화하기 위한 출발점`
이다.
