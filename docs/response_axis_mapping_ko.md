# Response 6축 매핑 정리

## 목적

이 문서는 현재 CFD 엔진의 `Response` 레이어가 어떤 raw 반응들을 수집하고,  
그 raw들이 어떻게 아래 6개의 canonical axis로 압축되는지를 정리한 문서다.

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

핵심 목적은 다음 3가지다.

1. `Response`가 현재 무엇을 보고 있는지 명확히 이해한다.
2. 어떤 raw가 어느 축으로 들어가는지 한눈에 본다.
3. 아직 비어 있는 축, 특히 `S/R 반응`, `추세선 반응`이 어디에 추가돼야 하는지 판단 기준을 만든다.

---

## 큰 구조

현재 `Response`는 아래 순서로 구성된다.

1. `raw detector`들이 반응을 수집한다.
2. raw 반응들이 `ResponseRawSnapshot`에 담긴다.
3. `transition_vector.py`에서 6개의 canonical axis로 압축된다.
4. 이 6개 축이 `Evidence`에서 `Position`, `State`와 결합된다.

즉 구조는 다음과 같다.

```text
Band / Box / Candle / Pattern raw
-> ResponseRawSnapshot
-> ResponseVectorV2 (6 axes)
-> Evidence
```

현재 코드 기준 관련 파일은 아래와 같다.

- raw 조립: `backend/trading/engine/response/builder.py`
- raw 스키마: `backend/trading/engine/core/models.py`
- 밴드 반응: `backend/trading/engine/response/band_response.py`
- 박스 반응: `backend/trading/engine/response/structure_response.py`
- 캔들 반응: `backend/trading/engine/response/candle_response.py`
- 패턴 반응: `backend/trading/engine/response/pattern_response.py`
- 6축 압축: `backend/trading/engine/response/transition_vector.py`
- Evidence 연결: `backend/trading/engine/core/evidence_engine.py`

---

## Response의 역할

현재 설계상 `Response`는 다음 역할만 해야 한다.

- 지금 위치에서 무슨 반응이 나왔는지 표현
- 반응의 방향과 강도를 표현
- 그 반응을 소수의 의미 축으로 압축

`Response`가 하면 안 되는 일은 아래와 같다.

- 최종 side를 단독으로 확정
- Position처럼 “지금 어디에 있는가”를 정의
- State처럼 “지금 장이 어떤 성격인가”를 판단
- Barrier처럼 “실행 금지”를 직접 결정

즉 `Response`는 다음 질문에만 답해야 한다.

- 하단에서 받쳤는가?
- 하단이 깨졌는가?
- 중앙을 되찾았는가?
- 중앙을 잃었는가?
- 상단에서 거절당했는가?
- 상단을 돌파했는가?

---

## 빠른 보기

### Band raw

#### `bb20_lower_hold`
- BB20 하단에서 다시 안쪽으로 들어오며 버팀
- 주로 `lower_hold_up`

#### `bb20_lower_break`
- BB20 하단 아래로 종가 붕괴
- 주로 `lower_break_down`

#### `bb20_mid_hold`
- BB20 중심선을 지지로 삼음
- 주로 `mid_reclaim_up`

#### `bb20_mid_reclaim`
- 중심선을 다시 회복
- 주로 `mid_reclaim_up`

#### `bb20_mid_reject`
- 중심선에서 밀림
- 주로 `mid_lose_down`

#### `bb20_mid_lose`
- 중심선을 잃음
- 주로 `mid_lose_down`

#### `bb20_upper_reject`
- BB20 상단에서 거절당함
- 주로 `upper_reject_down`

#### `bb20_upper_break`
- BB20 상단 위로 종가 돌파
- 주로 `upper_break_up`

#### `bb44_lower_hold`
- BB44 하단에서 한 번 더 받침
- `lower_hold_up` 보조 확인

#### `bb44_upper_reject`
- BB44 상단에서 한 번 더 거절
- `upper_reject_down` 보조 확인

### Structure(Box) raw

#### `box_lower_bounce`
- 박스 하단에서 반등
- 주로 `lower_hold_up`

#### `box_lower_break`
- 박스 하단 아래 종가 붕괴
- 주로 `lower_break_down`

#### `box_mid_hold`
- 박스 중앙선 위 유지
- 주로 `mid_reclaim_up`

#### `box_mid_reject`
- 박스 중앙선에서 밀림
- 주로 `mid_lose_down`

#### `box_upper_reject`
- 박스 상단에서 거절당함
- 주로 `upper_reject_down`

#### `box_upper_break`
- 박스 상단 위 종가 돌파
- 주로 `upper_break_up`

### Candle raw

#### `candle_lower_reject`
- 긴 아래꼬리 + 양봉
- `lower_hold_up` 보조 확인

#### `candle_upper_reject`
- 긴 윗꼬리 + 음봉
- `upper_reject_down` 보조 확인

### Pattern raw

#### `pattern_double_bottom`
- 더블바텀 성격
- `lower_hold_up` 증폭

#### `pattern_inverse_head_shoulders`
- 역헤드앤숄더 성격
- `lower_hold_up`, `mid_reclaim_up` 증폭

#### `pattern_double_top`
- 더블탑 성격
- `upper_reject_down` 증폭

#### `pattern_head_shoulders`
- 헤드앤숄더 성격
- `upper_reject_down`, `mid_lose_down` 증폭

### 점수 형태

#### 이벤트형
- 발생하면 거의 바로 `1.0`
- 예: `break`, `reclaim`, `lose`

#### 근접도 기반 연속형
- 선에 얼마나 가까운지
- 다시 안쪽으로 들어왔는지
- 양봉/음봉인지

#### wick/body 기반 연속형
- 꼬리 길이와 몸통 비율
- 캔들 rejection 성격

#### 구조 강도형
- 대칭성
- 깊이/높이
- neckline 회복/상실

### 현재 빈칸

#### `S/R 직접 반응 raw`
- 아직 없음

#### `추세선 직접 반응 raw`
- 아직 없음

---

## 현재 raw 스키마

현재 `ResponseRawSnapshot`에는 아래 raw들이 들어간다.

### Band 계열 raw

- `bb20_lower_hold`
- `bb20_lower_break`
- `bb20_mid_hold`
- `bb20_mid_reclaim`
- `bb20_mid_reject`
- `bb20_mid_lose`
- `bb20_upper_reject`
- `bb20_upper_break`
- `bb44_lower_hold`
- `bb44_upper_reject`

### Structure(Box) 계열 raw

- `box_lower_bounce`
- `box_lower_break`
- `box_mid_hold`
- `box_mid_reject`
- `box_upper_reject`
- `box_upper_break`

### Candle 계열 raw

- `candle_lower_reject`
- `candle_upper_reject`

### Pattern 계열 raw

- `pattern_double_bottom`
- `pattern_inverse_head_shoulders`
- `pattern_double_top`
- `pattern_head_shoulders`

주의할 점:

- 현재 raw에는 `S/R 직접 반응 raw`가 없다.
- 현재 raw에는 `추세선 직접 반응 raw`가 없다.
- 즉 현재 Response는 `BB + Box + Candle + Pattern` 중심이다.

### raw 스키마 주석 버전

아래 표는 같은 raw 목록에 짧은 주석을 붙인 버전이다.

중요한 해석 규칙:

- `hold / bounce / reject`는 보통 “버티고 반응함” 쪽이다.
- `break / lose`는 보통 “깨지고 밀림” 쪽이다.
- `reclaim`은 “한 번 잃었다가 다시 되찾음” 쪽이다.
- `upper / lower / mid`는 반응이 발생한 위치를 뜻한다.
- `0~1 점수`는 확률이 아니라 `반응 강도`다.

#### Band raw 주석표

| raw | 쉬운 뜻 | 주로 연결되는 축 | 점수 형태 |
|---|---|---|---|
| `bb20_lower_hold` | BB20 하단에서 다시 안쪽으로 들어오며 버팀 | `lower_hold_up` | 근접도 + 되돌림 + 봉 성질 기반 연속형 |
| `bb20_lower_break` | BB20 하단 아래로 종가 붕괴 | `lower_break_down` | 붕괴 이벤트형, 강하면 1.0 |
| `bb20_mid_hold` | BB20 중심선을 지지로 삼음 | `mid_reclaim_up` | 근접도 + 유지형 연속형 |
| `bb20_mid_reclaim` | 중심선을 다시 회복 | `mid_reclaim_up` | 전봉/현봉 교차 이벤트형 |
| `bb20_mid_reject` | 중심선에서 밀림 | `mid_lose_down` | 근접도 + 거절형 연속형 |
| `bb20_mid_lose` | 중심선을 잃음 | `mid_lose_down` | 전봉/현봉 교차 이벤트형 |
| `bb20_upper_reject` | BB20 상단에서 거절당함 | `upper_reject_down` | 근접도 + 윗꼬리/음봉 성질 기반 |
| `bb20_upper_break` | BB20 상단 위로 종가 돌파 | `upper_break_up` | 돌파 이벤트형, 강하면 1.0 |
| `bb44_lower_hold` | BB44 하단에서 한 번 더 받침 | `lower_hold_up` | 보조 확인용 연속형 |
| `bb44_upper_reject` | BB44 상단에서 한 번 더 거절 | `upper_reject_down` | 보조 확인용 연속형 |

#### Structure(Box) raw 주석표

| raw | 쉬운 뜻 | 주로 연결되는 축 | 점수 형태 |
|---|---|---|---|
| `box_lower_bounce` | 박스 하단에서 반등 | `lower_hold_up` | 근접도 + 되돌림 + 꼬리/봉 성질 |
| `box_lower_break` | 박스 하단 아래 종가 붕괴 | `lower_break_down` | 붕괴 이벤트형 |
| `box_mid_hold` | 박스 중앙선 위 유지 | `mid_reclaim_up` | 근접도 + 유지형 |
| `box_mid_reject` | 박스 중앙선에서 밀림 | `mid_lose_down` | 근접도 + 거절형 |
| `box_upper_reject` | 박스 상단에서 거절당함 | `upper_reject_down` | 상단 접촉 + 윗꼬리/음봉 성질 |
| `box_upper_break` | 박스 상단 위 종가 돌파 | `upper_break_up` | 돌파 이벤트형 |

#### Candle raw 주석표

| raw | 쉬운 뜻 | 주로 연결되는 축 | 점수 형태 |
|---|---|---|---|
| `candle_lower_reject` | 긴 아래꼬리 + 양봉 | `lower_hold_up` | 꼬리 비율 기반 연속형 |
| `candle_upper_reject` | 긴 윗꼬리 + 음봉 | `upper_reject_down` | 꼬리 비율 기반 연속형 |

#### Pattern raw 주석표

| raw | 쉬운 뜻 | 주로 연결되는 축 | 점수 형태 |
|---|---|---|---|
| `pattern_double_bottom` | 더블바텀 성격 | `lower_hold_up` | 구조 강도형 연속형 |
| `pattern_inverse_head_shoulders` | 역헤드앤숄더 성격 | `lower_hold_up`, `mid_reclaim_up` | 구조 강도형 연속형 |
| `pattern_double_top` | 더블탑 성격 | `upper_reject_down` | 구조 강도형 연속형 |
| `pattern_head_shoulders` | 헤드앤숄더 성격 | `upper_reject_down`, `mid_lose_down` | 구조 강도형 연속형 |

### 점수는 어떤 형태로 만들어지나

현재 raw 점수는 크게 4가지 형태로 만들어진다.

#### 1. 이벤트형

특정 조건이 만족되면 거의 바로 `1.0`이 되는 형태다.

예:

- `bb20_lower_break`
- `bb20_upper_break`
- `bb20_mid_reclaim`
- `bb20_mid_lose`
- `box_lower_break`
- `box_upper_break`

이런 raw는 의미가 명확하다.

- 선 아래 종가 붕괴
- 선 위 종가 돌파
- 중심선 재탈환
- 중심선 상실

즉 “발생했느냐/안 했느냐”가 중요해서 이벤트형에 가깝다.

#### 2. 근접도 기반 연속형

가격이 특정 선에 얼마나 가까웠는지,
그리고 그 선 근처에서 어떻게 마감했는지로 점수가 생기는 형태다.

예:

- `bb20_lower_hold`
- `bb20_mid_hold`
- `bb20_mid_reject`
- `box_lower_bounce`
- `box_mid_hold`
- `box_mid_reject`

이 계열은 보통 아래 요소가 섞인다.

- 선까지의 거리
- 고가/저가가 닿았는지
- 종가가 다시 안쪽으로 들어왔는지
- 양봉/음봉 성질

즉:

```text
근접도 * 되돌림/유지 조건 * 봉의 방향성
```

형태로 생각하면 된다.

#### 3. wick/body 기반 연속형

캔들 꼬리 길이와 몸통 비율로 반응 강도를 읽는 형태다.

예:

- `candle_lower_reject`
- `candle_upper_reject`

이 계열은 대체로:

```text
꼬리 길이 / 전체 range
```

에 가까운 값이다.

즉:
- 아래꼬리가 길고 양봉이면 하단 reject
- 윗꼬리가 길고 음봉이면 상단 reject

#### 4. 구조 강도형

패턴 계열은 단순 접촉이 아니라 구조 자체의 품질을 본다.

예:

- `pattern_double_bottom`
- `pattern_double_top`
- `pattern_inverse_head_shoulders`
- `pattern_head_shoulders`

이 계열은 보통 아래 요소를 섞는다.

- 좌우 대칭성
- 머리/어깨 깊이 또는 높이
- neckline과의 관계
- 마지막 종가의 회복/상실 정도

즉:

```text
구조 대칭성 + 깊이/높이 + neckline 회복/상실
```

의 합성 점수에 가깝다.

이 값들은 여전히 `0~1`이지만,
확률이 아니라 “패턴이 얼마나 그럴듯한가”에 가깝다.

---

## 현재 6축 정의

현재 `ResponseVectorV2`는 아래 6개 축만 밖으로 내보낸다.

### 1. `lower_hold_up`

뜻:
- 하단에서 지지받고 위로 가려는 반응

쉽게 말하면:
- 하단 bounce
- 하단 support hold
- 하단 reject

### 2. `lower_break_down`

뜻:
- 하단 지지가 깨지고 아래로 밀리는 반응

쉽게 말하면:
- 하단 breakdown
- support fail

### 3. `mid_reclaim_up`

뜻:
- 중앙 기준선을 다시 회복하며 위로 가려는 반응

쉽게 말하면:
- mid reclaim
- 중심 회복

### 4. `mid_lose_down`

뜻:
- 중앙 기준선을 잃고 아래로 밀리는 반응

쉽게 말하면:
- mid lose
- 중심 상실

### 5. `upper_reject_down`

뜻:
- 상단 저항에서 거절당하고 아래로 내려오려는 반응

쉽게 말하면:
- upper reject
- resistance reject

### 6. `upper_break_up`

뜻:
- 상단 저항을 돌파하고 위로 확장하려는 반응

쉽게 말하면:
- upper breakout
- resistance break

---

## 6축 매핑표

아래 표는 현재 코드에서 각 축에 어떤 raw가 들어가는지 정리한 것이다.

| 축 | primary sources | confirmation sources | amplifier sources | 의미 |
|---|---|---|---|---|
| `lower_hold_up` | `bb20_lower_hold`, `box_lower_bounce` | `bb44_lower_hold`, `candle_lower_reject` | `pattern_double_bottom`, `pattern_inverse_head_shoulders` | 하단 지지 반등 |
| `lower_break_down` | `bb20_lower_break`, `box_lower_break` | 없음 | 없음 | 하단 붕괴 |
| `mid_reclaim_up` | `bb20_mid_hold`, `bb20_mid_reclaim`, `box_mid_hold` | 없음 | `pattern_inverse_head_shoulders` | 중심 회복 상승 |
| `mid_lose_down` | `bb20_mid_reject`, `bb20_mid_lose`, `box_mid_reject` | 없음 | `pattern_head_shoulders` | 중심 상실 하락 |
| `upper_reject_down` | `bb20_upper_reject`, `box_upper_reject` | `bb44_upper_reject`, `candle_upper_reject` | `pattern_double_top`, `pattern_head_shoulders` | 상단 저항 거절 |
| `upper_break_up` | `bb20_upper_break`, `box_upper_break` | 없음 | 없음 | 상단 돌파 |

---

## raw별 상세 설명

아래는 현재 raw 하나하나가 어떤 의미를 갖는지 정리한 것이다.

## Band raw 상세

### `bb20_lower_hold`

의미:
- BB20 하단 부근에서 가격이 다시 안쪽으로 들어오며 버텨주는 반응

현재 코드에서 반응을 주는 조건:

- BB20 하단 아래로 강하게 종가 이탈하지 않았을 것
- low가 BB20 하단에 충분히 근접할 것
- 종가가 다시 안쪽에 위치할 것
- 양봉 성격이 있거나, 아래꼬리 reject가 있을 것

결과적으로 이 raw는
- “하단에 닿았다”
가 아니라
- “하단에서 반응한 뒤 안쪽으로 되돌아왔다”
를 의미한다.

이 raw는 `lower_hold_up`의 핵심 primary source다.

---

### `bb20_lower_break`

의미:
- BB20 하단 아래로 종가가 무너진 상태

현재 코드에서 반응을 주는 조건:

- 종가가 BB20 하단 아래로 `band_tol` 이상 이탈

이 raw는 `lower_break_down`의 핵심 primary source다.

즉:
- 단순 하단 접촉이 아니라
- 하단 종가 붕괴를 표현한다.

---

### `bb20_mid_hold`

의미:
- BB20 중앙선을 다시 지지하거나, 중앙선 위에서 유지하는 반응

현재 코드의 의미:

- 중심선 위 종가 유지
- 중심선 부근 접촉 후 양봉 유지
- 중심선이 지지처럼 작용

이 raw는 `mid_reclaim_up`의 primary source다.

---

### `bb20_mid_reclaim`

의미:
- 직전에는 중심선 아래에 있었는데, 이번에는 중심선 위로 올라온 반응

이 raw는 단순히 “중심선 근처”가 아니라
- 중심선을 다시 되찾았는가
를 본다.

이 raw는 `mid_reclaim_up`의 primary source다.

---

### `bb20_mid_reject`

의미:
- 중심선 위로 제대로 못 안착하고 밀리는 반응

현재 코드의 의미:

- 중심선 근처까지 갔다가
- 다시 아래쪽 성격으로 마감

이 raw는 `mid_lose_down`의 primary source다.

---

### `bb20_mid_lose`

의미:
- 직전에는 중심선 위였는데, 이번에 중심선 아래로 내려온 반응

즉:
- 중심선 상실
- mid lose

이 raw는 `mid_lose_down`의 primary source다.

---

### `bb20_upper_reject`

의미:
- BB20 상단에서 저항을 받고 밀린 반응

현재 코드에서 반응을 주는 조건:

- high가 상단에 충분히 닿을 것
- 종가가 다시 안쪽으로 들어올 것
- 음봉 성격 또는 윗꼬리 reject가 있을 것

이 raw는 `upper_reject_down`의 핵심 primary source다.

---

### `bb20_upper_break`

의미:
- BB20 상단을 종가로 돌파한 반응

이 raw는 `upper_break_up`의 핵심 primary source다.

즉:
- 상단 접근이 아니라
- 상단 위 종가 안착에 가깝다.

---

### `bb44_lower_hold`

의미:
- 더 바깥쪽인 BB44 하단에서 받쳐주는 반응

역할:
- `lower_hold_up`의 보조 확인
- BB20 하단 반응이 진짜 외곽 반응인지 추가 확인

이 raw는 confirmation source다.

즉:
- 주인공은 아니고
- “진짜 하단 반응이다”를 받쳐주는 역할이다.

---

### `bb44_upper_reject`

의미:
- 더 바깥쪽인 BB44 상단에서 밀리는 반응

역할:
- `upper_reject_down`의 보조 확인

이 raw도 confirmation source다.

---

## Structure(Box) raw 상세

### `box_lower_bounce`

의미:
- 박스 하단에서 반등해 다시 안쪽으로 들어오는 반응

현재 코드의 의미:

- low가 박스 하단 근처
- 종가가 다시 박스 안쪽
- 양봉 또는 하단 reject 성격

이 raw는 `lower_hold_up`의 핵심 primary source다.

---

### `box_lower_break`

의미:
- 박스 하단 아래로 종가 붕괴

이 raw는 `lower_break_down`의 핵심 primary source다.

즉:
- 박스 하단 touch가 아니라
- 박스 하단 fail이다.

---

### `box_mid_hold`

의미:
- 박스 중앙선을 지지로 삼는 반응

역할:
- `mid_reclaim_up`의 primary source

즉:
- 중심 회복/유지 쪽 의미다.

---

### `box_mid_reject`

의미:
- 박스 중앙선에서 저항받고 밀리는 반응

역할:
- `mid_lose_down`의 primary source

즉:
- 중심선 상실/거절 쪽 의미다.

---

### `box_upper_reject`

의미:
- 박스 상단에서 저항받고 밀리는 반응

역할:
- `upper_reject_down`의 핵심 primary source

즉:
- 상단 rejection 쪽 의미를 준다.

---

### `box_upper_break`

의미:
- 박스 상단 위로 종가 돌파

역할:
- `upper_break_up`의 핵심 primary source

---

## Candle raw 상세

### `candle_lower_reject`

의미:
- 긴 아래꼬리 + 양봉 마감

해석:
- 하단에서 지지 반응이 있었다

역할:
- `lower_hold_up`의 confirmation source

즉:
- 단독으로 방향을 만들기보다
- 하단 hold의 보조 증거 역할이다.

---

### `candle_upper_reject`

의미:
- 긴 윗꼬리 + 음봉 마감

해석:
- 상단에서 저항 반응이 있었다

역할:
- `upper_reject_down`의 confirmation source

---

## Pattern raw 상세

### `pattern_double_bottom`

의미:
- 최근 저점 구조가 double bottom에 가까움

역할:
- `lower_hold_up`의 amplifier

즉:
- 하단 반등 쪽 의미를 강화

---

### `pattern_inverse_head_shoulders`

의미:
- 최근 구조가 역헤드앤숄더에 가까움

역할:
- `lower_hold_up` amplifier
- `mid_reclaim_up` amplifier

즉:
- 하단 반전 / 중심 회복을 증폭

---

### `pattern_double_top`

의미:
- 최근 고점 구조가 double top에 가까움

역할:
- `upper_reject_down` amplifier

---

### `pattern_head_shoulders`

의미:
- 최근 구조가 헤드앤숄더에 가까움

역할:
- `upper_reject_down` amplifier
- `mid_lose_down` amplifier

---

## 현재 압축 방식

현재 `transition_vector.py`는 단순 합산이 아니라 아래 구조를 쓴다.

### 압축 전에 기억할 것

raw는 그대로 다 더하지 않는다.

이유는 간단하다.

- `bb20_lower_hold`
- `box_lower_bounce`
- `bb44_lower_hold`
- `candle_lower_reject`
- `pattern_double_bottom`

이 다 동시에 높다고 해서
그걸 그대로 더하면 같은 뜻을 여러 번 더하는 셈이 된다.

그래서 현재 압축은

```text
dominant primary
+ capped primary support
+ capped confirmation support
+ capped amplifier support
```

형태다.

### 1. dominant primary

축마다 가장 강한 primary source 하나를 먼저 잡는다.

예:

- `lower_hold_up`에서
  - `bb20_lower_hold = 0.82`
  - `box_lower_bounce = 0.64`
  라면
  dominant primary는 `bb20_lower_hold`

### 2. capped primary support

남은 primary source들은
- 전부 그대로 더하지 않고
- 작은 support만 더한다

즉:
- 같은 뜻을 과대 중복 가산하지 않게 하는 장치다.

### 3. capped confirmation support

confirmation source들도
- 보조 가산만 한다
- 축의 주인이 되지 않는다

예:

- `bb44_lower_hold`
- `candle_lower_reject`

이런 것들은 하단 반등의 추가 확인이다.

### 4. amplifier support

pattern 계열은
- 구조적 증폭만 준다
- 기본 반응이 없는데 단독으로 진입을 만들지는 않는다

즉:
- 패턴은 reaction owner가 아니라 amplifier다.

### 형태를 수식처럼 쓰면

현재 축 하나는 대략 아래 개념으로 만들어진다.

```text
axis_score
= dominant_primary
+ min(남은 primary 합 * 0.20, 0.20)
+ min(confirmation 합 * 0.12, 0.12)
+ min(amplifier 합 * 0.10, 0.10)
```

단:

- primary가 하나도 없고 confirmation만 있으면
  confirmation dominant를 `0.82` 스케일로 시작한다.
- 즉 confirmation은 단독 owner가 아니라는 뜻이다.

이게 중요한 이유는:

- primary는 “실제 반응”
- confirmation은 “그 반응을 받쳐주는 보조”
- amplifier는 “구조적 증폭”

으로 역할을 나눠 두기 때문이다.

---

## 현재 구조의 장점

현재 구조의 좋은 점은 아래와 같다.

### 1. raw가 많아도 출력은 6개 축으로 단순화된다

즉:
- 내부는 복잡해도
- 밖에서는 의미만 본다

### 2. 같은 의미를 무한정 더하지 않는다

dominant + capped support 구조 덕분에
- `box lower`
- `bb20 lower`
- `candle lower reject`
- `double bottom`
이 다 떠도
그냥 합산 폭주하지 않는다.

### 3. pattern이 과대 owner가 되지 않는다

패턴은 현재 amplifier라서
- 단독으로 방향을 장악하기 어렵다

이건 현재 단계에선 좋은 설계다.

---

## 현재 구조의 한계

현재 Response 구조가 아직 부족한 지점도 분명하다.

### 1. `S/R 직접 반응 raw`가 없다

현재는 `support/resistance`가 의미상 중요하지만,
raw 차원에서는 아래 같은 필드가 없다.

- `sr_support_hold`
- `sr_support_break`
- `sr_resistance_reject`
- `sr_resistance_break`

즉:
- S/R가 직접 `Response owner`로 들어오지 못한다.

현재는 일부가 박스/볼밴/중심선 의미에 흡수될 뿐이다.

---

### 2. `추세선 직접 반응 raw`가 없다

현재 raw에는 아래 같은 필드가 없다.

- `trendline_support_hold`
- `trendline_support_break`
- `trendline_resistance_reject`
- `trendline_breakout`

즉:
- 추세선은 현재 Position/Context에서는 보이지만
- Response raw owner로는 아직 비어 있다.

---

### 3. 반대축 상쇄가 아직 약하다

현재는 축 내부 dominant/support merge는 있지만,
예를 들어 같은 자리에서 아래 둘이 동시에 높을 수 있다.

- `lower_hold_up`
- `lower_break_down`

이럴 때:
- ambiguity를 적극적으로 깎는 구조
보다는
- 둘이 각각 살아남는 경우가 있다.

이게 이후 ObserveConfirm에서 충돌로 이어질 수 있다.

---

### 4. `middle`과 `edge`의 response 의미 차이가 아직 완전히 분리되진 않았다

현재는 이미 어느 정도 분리돼 있지만,
여전히 middle에서의 reclaim/lose와
edge에서의 hold/break가 실전상 충돌하는 경우가 있다.

즉:
- `Position`이 middle handoff를 하는 구조와
- `Response`가 실제로 middle을 얼마나 보수적으로 처리하는지
가 완전히 일치하진 않는다.

---

## 현재 상태를 한 줄로 요약하면

현재 Response는 이미

- 하단 반등
- 하단 붕괴
- 중심 회복
- 중심 상실
- 상단 거절
- 상단 돌파

라는 6축 구조로 꽤 잘 압축되어 있다.

하지만 아직 raw owner는

- `Box`
- `Bollinger`
- `Candle`
- `Pattern`

중심이고,

당신이 특히 중요하게 보는

- `S/R 반응`
- `추세선 반응`

은 아직 직접 raw 축으로 들어오지 못한 상태다.

즉 지금 단계의 핵심 과제는:

`현재 6축 구조를 버리는 것`이 아니라,
`S/R와 추세선 raw를 이 6축 구조 안에 자연스럽게 추가하고, 반대축 ambiguity를 더 정리하는 것`

이다.

---

## 다음 작업 기준

이 문서 기준으로 다음 단계는 아래 순서가 가장 적절하다.

1. 현재 6축은 유지
2. `S/R raw` 추가
3. `추세선 raw` 추가
4. `lower_hold_up vs lower_break_down`
   `upper_reject_down vs upper_break_up`
   같은 반대축 ambiguity 정리
5. 이후 ObserveConfirm에서 hard override보다 비교형 arbitration 강화

즉 방향은:

`Response를 다시 짜는 것`이 아니라  
`현재 Response 6축을 기반으로 raw owner를 더 정확히 확장하는 것`

이다.
