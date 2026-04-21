# D4 location_context_v1 상세 계획

## 1. 목적

D4의 목적은 같은 rejection, continuation, friction이라도
**어디서 발생했는지**를 공용 modifier로 고정하는 것이다.

이번 단계는 아직 기존 dominance 계산이나 execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 location context 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

같은 `upper_reject`라도 위치에 따라 의미가 달라진다.

- 박스 안쪽의 reject
- 엣지에서의 reject
- breakout 직후의 reject
- 이미 많이 연장된 구간의 reject

같은 continuation도 위치에 따라 해석이 달라진다.

- 박스 안 continuation
- edge continuation
- breakout 직후 continuation
- extended continuation

즉 D4는 signal 이름만 보지 않고,
**그 signal이 어디에서 발생했는지**를 공용 계약으로 고정하는 단계다.

---

## 3. D4에서 고정할 핵심 규칙

### 3-1. location context

- `NONE`
- `IN_BOX`
- `AT_EDGE`
- `POST_BREAKOUT`
- `EXTENDED`

### 3-2. location 판단 재료

- box interior 여부
- edge proximity 여부
- breakout/reclaim 직후 zone 여부
- extension/late chase zone 여부

### 3-3. 해석 규칙

- `IN_BOX`는 interior drift/structure 설명이 edge 설명보다 앞서는 위치다
- `AT_EDGE`는 rejection/friction 해석이 중요해지는 위치다
- `POST_BREAKOUT`은 fresh breakout/reclaim 해석이 중요한 위치다
- `EXTENDED`는 late chase/extension 압력이 커지는 위치다

### 3-4. 금지 규칙

- location context는 core slot driver가 아니라 modifier다
- `AT_EDGE`만으로 reversal을 선언하지 않는다
- `EXTENDED`만으로 reversal을 선언하지 않는다
- location context는 `dominant_side`를 바꾸지 못한다
- location context는 execution/state25를 직접 바꾸지 않는다

즉 D4는 state를 더 잘게 설명하지만,
기존 dominance ownership과 execution separation은 계속 유지해야 한다.

---

## 4. D4에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `location_context_contract_v1`
- `location_context_summary_v1`
- `location_context_artifact_paths`

contract 필드 카탈로그:

- `location_context_v1`
- `location_context_confidence_v1`
- `location_context_reason_summary_v1`
- `box_position_state_v1`
- `edge_proximity_state_v1`
- `post_breakout_zone_v1`
- `extension_zone_state_v1`

이번 버전은 row-level location 계산을 실제로 붙이기보다,
먼저 공용 계약과 control rule을 고정하는 데 집중한다.

---

## 5. 산출물

shadow artifact:

- `location_context_latest.json`
- `location_context_latest.md`

runtime detail:

- `location_context_contract_v1`
- `location_context_summary_v1`
- `location_context_artifact_paths`

---

## 6. 완료 기준

- location context가 `IN_BOX`, `AT_EDGE`, `POST_BREAKOUT`, `EXTENDED`로 분리된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- location은 modifier이며 dominant side를 바꾸지 못한다는 control rule이 명시된다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 7. 상태 기준

- `READY`: location context 계약, summary, artifact가 정상 surface됨
- `HOLD`: 계약은 있으나 location 재료 정의나 control rule 설명이 흔들림
- `BLOCKED`: location context가 dominance ownership을 침범하거나 runtime export가 누락됨
