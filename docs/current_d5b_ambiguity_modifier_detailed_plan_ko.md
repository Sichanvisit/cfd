# D5b ambiguity modifier 상세 계획

## 1. 목적

D5b의 목적은 애매한 장면을 continuation, friction, reversal 중 하나로 억지 소비하지 않고,
**ambiguity를 공용 modifier로 남기는 계약**을 먼저 고정하는 것이다.

이번 단계는 아직 기존 dominance 계산이나 execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 ambiguity 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

실전 장면 중 가장 많은 상태는
명확한 continuation도 아니고, 명확한 reversal도 아닌 장면이다.

이런 장면을 별도 축 없이 처리하면 아래 둘 중 하나로 과잉 흡수되기 쉽다.

- continuation 또는 friction으로 끌려감
- BOUNDARY로 과잉 소비됨

즉 D5b는 애매한 장면을 단순 noise로 버리지 않고,
**boundary/caution을 조정하는 별도 modifier**로 고정하는 단계다.

---

## 3. D5b에서 고정할 핵심 규칙

### 3-1. ambiguity level

- `LOW`
- `MEDIUM`
- `HIGH`

### 3-2. ambiguity source

- `CONTINUATION_REVERSAL_CONFLICT`
- `BOUNDARY_CONFLICT`
- `STRUCTURE_MIXED`
- `INSUFFICIENT_CONFIRMATION`

### 3-3. 해석 규칙

- `LOW`는 conflict가 약하고 dominant interpretation이 비교적 선명한 상태다
- `MEDIUM`은 경쟁 해석이 함께 살아 있어 caution/boundary 조정이 필요한 상태다
- `HIGH`는 continuation과 reversal을 억지로 확정하면 과잉 분류가 발생하는 상태다

### 3-4. 금지 규칙

- ambiguity는 core slot driver가 아니다
- ambiguity는 `dominant_side`를 바꾸지 못한다
- `HIGH ambiguity`를 friction이나 continuation에 조용히 흡수하지 않는다
- ambiguity는 boundary bias와 caution level을 조정하지만 execution/state25는 직접 바꾸지 않는다

즉 D5b는 unresolved scene을 그대로 남길 수 있게 하는 안전장치이며,
기존 dominance ownership과 execution separation은 계속 유지해야 한다.

---

## 4. D5b에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `ambiguity_modifier_contract_v1`
- `ambiguity_modifier_summary_v1`
- `ambiguity_modifier_artifact_paths`

contract 필드 카탈로그:

- `ambiguity_level_v1`
- `ambiguity_source_v1`
- `ambiguity_confidence_v1`
- `ambiguity_reason_summary_v1`
- `boundary_bias_adjustment_v1`
- `caution_bias_adjustment_v1`

이번 버전은 row-level ambiguity 계산을 실제로 붙이기보다,
먼저 공용 계약과 control rule을 고정하는 데 집중한다.

---

## 5. 산출물

shadow artifact:

- `ambiguity_modifier_latest.json`
- `ambiguity_modifier_latest.md`

runtime detail:

- `ambiguity_modifier_contract_v1`
- `ambiguity_modifier_summary_v1`
- `ambiguity_modifier_artifact_paths`

---

## 6. 완료 기준

- ambiguity modifier가 `LOW / MEDIUM / HIGH`로 분리된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- ambiguity는 boundary/caution 조정용 modifier라는 control rule이 명시된다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 7. 상태 기준

- `READY`: ambiguity modifier 계약, summary, artifact가 정상 surface됨
- `HOLD`: 계약은 있으나 ambiguity source 정의나 control rule 설명이 흔들림
- `BLOCKED`: ambiguity modifier가 dominance ownership을 침범하거나 runtime export가 누락됨
