# D3 continuation stage 분해 상세 계획

## 1. 목적

D3의 목적은 continuation 내부를 하나의 두꺼운 상태로 두지 않고,
`INITIATION / ACCEPTANCE / EXTENSION`으로 분리하는 공용 계약을 먼저 고정하는 것이다.

이번 단계는 아직 기존 dominance 계산이나 execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 continuation stage 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

현재까지의 구조에서는 continuation이 대체로
`CONTINUATION` 또는 `CONTINUATION_WITH_FRICTION` 정도로만 surface된다.

하지만 실제 continuation은 적어도 세 구간으로 나뉜다.

- `INITIATION`
  - breakout 또는 reclaim 직후
  - 가장 이른 continuation 후보 구간
- `ACCEPTANCE`
  - hold가 유지되고 higher low가 쌓이는 정착 구간
  - continuation이 구조적으로 안정화된 상태
- `EXTENSION`
  - continuation은 여전히 맞을 수 있지만 이미 많이 진행된 구간
  - late chase와 extension pressure가 커지는 상태

즉 D3는 continuation이 맞다는 말만 남기지 않고,
**지금 continuation이 어느 시간 위치(stage)에 있는지**를 공용 계약으로 고정하는 단계다.

---

## 3. D3에서 고정할 핵심 규칙

### 3-1. continuation stage

- `NONE`
- `INITIATION`
- `ACCEPTANCE`
- `EXTENSION`

### 3-2. stage 판단 재료

- breakout 또는 reclaim 직후 여부
- `breakout_hold_bars_v1`
- higher low persistence
- late extension pressure

### 3-3. 해석 규칙

- `INITIATION`은 구조가 막 시작됐고 hold가 아직 얕은 continuation 구간이다
- `ACCEPTANCE`는 hold가 안정되고 higher low 지속성이 확인되는 continuation 구간이다
- `EXTENSION`은 continuation이 여전히 유효할 수 있지만 추격 품질이 악화된 구간이다

### 3-4. 금지 규칙

- stage는 구조적 시간 위치이며 texture와 같은 차원으로 다루지 않는다
- `EXTENSION`만으로 reversal을 선언하지 않는다
- continuation stage는 `dominant_side`를 바꾸지 못한다
- continuation stage는 execution/state25를 직접 바꾸지 않는다

즉 D3는 continuation을 더 잘게 설명하지만,
기존 dominance ownership과 execution separation은 계속 유지해야 한다.

---

## 4. D3에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `continuation_stage_contract_v1`
- `continuation_stage_summary_v1`
- `continuation_stage_artifact_paths`

contract 필드 카탈로그:

- `continuation_stage_v1`
- `continuation_stage_confidence_v1`
- `continuation_stage_reason_summary_v1`
- `breakout_post_bars_v1`
- `breakout_hold_bars_v1`
- `higher_low_persistence_v1`
- `extension_pressure_state_v1`

이번 버전은 row-level stage 계산을 실제로 붙이기보다,
먼저 공용 계약과 control rule을 고정하는 데 집중한다.

---

## 5. 산출물

shadow artifact:

- `continuation_stage_latest.json`
- `continuation_stage_latest.md`

runtime detail:

- `continuation_stage_contract_v1`
- `continuation_stage_summary_v1`
- `continuation_stage_artifact_paths`

---

## 6. 완료 기준

- continuation이 `INITIATION`, `ACCEPTANCE`, `EXTENSION`으로 분리된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- stage와 texture가 다른 역할이라는 control rule이 명시된다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 7. 상태 기준

- `READY`: continuation stage 계약, summary, artifact가 정상 surface됨
- `HOLD`: 계약은 있으나 stage 재료 정의나 control rule 설명이 흔들림
- `BLOCKED`: continuation stage가 dominance ownership을 침범하거나 runtime export가 누락됨
