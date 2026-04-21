# D2 Rejection 분리 규칙 상세 계획

## 1. 목적

D2의 목적은 rejection을 하나의 거친 경고로 소비하지 않고,
`FRICTION_REJECTION`과 `REVERSAL_REJECTION`으로 분리하는 공용 규칙을 먼저 고정하는 것이다.

이번 단계는 아직 기존 dominance 계산이나 execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 rejection 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

현재까지의 해석 구조에서는 `upper_reject`, `soft_block`, `wait_bias` 같은 rejection 계열 신호가
쉽게 reversal 쪽으로 소비될 위험이 있다.

하지만 실제로 rejection은 두 종류로 나뉜다.

- 구조를 깨는 rejection
  - continuation 실패와 structure break가 함께 확인되는 경우
  - 이는 `REVERSAL_REJECTION`으로 분리되어야 한다
- 구조는 유지되지만 진입 품질만 나빠지는 rejection
  - 이는 `FRICTION_REJECTION`으로 분리되어야 한다

즉 D2는 rejection을 단순한 신호명이 아니라,
**dominance가 어떻게 소비해야 하는지까지 포함한 공용 계약**으로 고정하는 단계다.

---

## 3. D2에서 고정할 핵심 규칙

### 3-1. rejection type

- `NONE`
- `FRICTION_REJECTION`
- `REVERSAL_REJECTION`

### 3-2. consumption role

- `NONE`
- `FRICTION_ONLY`
- `REVERSAL_EVIDENCE`

### 3-3. 해석 규칙

- structure-breaking rejection -> `REVERSAL_REJECTION`
- non-breaking rejection -> `FRICTION_REJECTION`
- `FRICTION_REJECTION`은 mode/caution만 조정하고 side는 바꾸지 못한다
- `REVERSAL_REJECTION`은 reversal evidence를 강화할 수 있지만, side 변경 권한은 여전히 dominance layer만 가진다

### 3-4. 금지 규칙

아래는 단독으로 `REVERSAL_REJECTION`이나 `REVERSAL_OVERRIDE`가 되면 안 된다.

- 단일 `upper_reject`
- 단일 `soft_block`
- 단일 `wait_bias`

즉 rejection 분리 규칙은 “무엇이 reversal 증거이고, 무엇이 friction인지”를 더 선명하게 만들지만,
기존 dominance ownership을 침범하지 않아야 한다.

---

## 4. D2에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `rejection_split_rule_contract_v1`
- `rejection_split_rule_summary_v1`
- `rejection_split_rule_artifact_paths`

contract 필드 카탈로그:

- `rejection_type_v1`
- `rejection_consumption_role_v1`
- `rejection_split_confidence_v1`
- `rejection_structure_break_confirmed_v1`
- `rejection_reversal_evidence_bridge_v1`
- `rejection_friction_bridge_v1`
- `rejection_reason_summary_v1`

이번 버전은 row-level 계산을 실제로 붙이기보다,
먼저 공용 계약과 control rule을 고정하는 데 집중한다.

---

## 5. 산출물

shadow artifact:

- `rejection_split_rule_latest.json`
- `rejection_split_rule_latest.md`

runtime detail:

- `rejection_split_rule_contract_v1`
- `rejection_split_rule_summary_v1`
- `rejection_split_rule_artifact_paths`

---

## 6. 완료 기준

- rejection이 `FRICTION_REJECTION`과 `REVERSAL_REJECTION`으로 분리된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 7. 상태 기준

- `READY`: rejection 분리 계약, summary, artifact가 정상 surface됨
- `HOLD`: 계약은 있으나 field catalog나 control rule 설명이 흔들림
- `BLOCKED`: rejection 분리 규칙이 dominance ownership을 침범하거나 runtime export가 누락됨
