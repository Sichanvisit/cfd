# F6. `flow_support_state_v1` 상세 계획

## 1. 목적

F6의 목적은 F1~F5에서 이미 만들어진 해석을 하나의 공용 상태로 묶는 것이다.

즉 F6는 새 threshold를 만들거나 structure 권한을 바꾸는 단계가 아니라,

- `F1 flow_structure_gate_v1`
- `F2 aggregate_conviction_v1`
- `F2 flow_persistence_v1`
- `F4 provisional_flow_band_state_v1`
- `F5 exact pilot match bonus`

를 종합해 최종 read-only state를 아래 중 하나로 표면화한다.

- `FLOW_CONFIRMED`
- `FLOW_BUILDING`
- `FLOW_UNCONFIRMED`
- `FLOW_OPPOSED`

---

## 2. 왜 F6가 필요한가

F5까지 오면 우리는 이미 아래를 다 읽을 수 있다.

- 구조 자격이 있는가
- conviction/persistence가 어느 정도인가
- provisional band상 confirmed/building 후보인가
- exact pilot match bonus가 적용되었는가

하지만 아직 runtime row에서는 이걸 한 줄의 공용 해석으로 바로 읽기 어렵다.

F6는 바로 이 문제를 해결한다.

즉 F6는

"이 row는 지금 방향 흐름이 확정인가 / 형성 중인가 / 아직 약한가 / 반대인가"

를 공용 state로 정리하는 **final read-only flow acceptance layer**다.

---

## 3. 권한 구조

F6는 절대로 아래 순서를 뒤집지 않는다.

1. `flow_structure_gate_v1`
2. `aggregate_conviction_v1 / flow_persistence_v1`
3. `provisional_flow_band_state_v1`
4. `exact pilot match bonus`
5. `flow_support_state_v1`

즉 F6는 upstream 결론을 번역하는 층이지,

- structure를 무시하는 층이 아니고
- threshold를 새로 hard gate로 만드는 층이 아니고
- exact bonus를 hard gate로 복귀시키는 층이 아니다

---

## 4. 상태 의미

### 4-1. `FLOW_CONFIRMED`

의미:

- structure gate를 통과했고
- conviction/persistence가 confirmed band 기준을 만족하며
- final band state가 confirmed 후보로 읽히는 상태

주의:

- `EXTENSION`은 기본적으로 여기로 올리지 않는다
- exact bonus가 있어도 `UNCONFIRMED -> CONFIRMED` 직행은 금지다

### 4-2. `FLOW_BUILDING`

의미:

- structure는 directional flow 후보로 인정되며
- conviction과 persistence 중 하나가 앞서고 다른 하나가 따라오거나
- confirmed 직전 단계이거나
- extension cap 때문에 confirmed가 building으로 제한된 상태

즉 "방향은 살아 있으나 아직 확정이라 부르기엔 이르거나, 이미 늦은 자리"다.

### 4-3. `FLOW_UNCONFIRMED`

의미:

- structure가 약하거나 borderline이거나
- conviction/persistence가 아직 building floor 아래거나
- ambiguity/soft-support 부족 때문에 flow acceptance를 보류해야 하는 상태

중요:

- `FLOW_UNCONFIRMED`는 항상 반대를 뜻하지 않는다
- 그냥 "아직 directional flow로 인정하기 이르다"는 뜻이다

### 4-4. `FLOW_OPPOSED`

의미:

- polarity mismatch
- reversal rejection
- reversal override

처럼 방향 자체가 반대로 읽히는 hard reason이 있는 상태

즉 단순 약세가 아니라 **현재 directional flow hypothesis와 반대**다.

---

## 5. 운영 규칙

### 5-1. structure-first 유지

`flow_structure_gate_v1`가 `INELIGIBLE`일 때도 무조건 `FLOW_OPPOSED`로 보내지 않는다.

분리 규칙:

- `POLARITY_MISMATCH`
- `REVERSAL_REJECTION`
- `REVERSAL_OVERRIDE`

면 `FLOW_OPPOSED`

그 외

- `AMBIGUITY_HIGH`
- `UNMAPPED_SLOT`
- `SOFT_SUPPORT_MISSING`

류는 `FLOW_UNCONFIRMED`

즉 F6는 "hard fail = 모두 반대"로 단순화하지 않는다.

### 5-2. provisional band가 기본 뼈대

structure를 통과한 row에 대해서는 F6가 아래를 그대로 따른다.

- `CONFIRMED_CANDIDATE` -> `FLOW_CONFIRMED`
- `BUILDING_CANDIDATE` -> `FLOW_BUILDING`
- `UNCONFIRMED_CANDIDATE` -> `FLOW_UNCONFIRMED`

단, 아래 예외가 있다.

### 5-3. extension cap 유지

`stage == EXTENSION`이면

- base/boosted band가 confirmed여도
- final state는 `FLOW_BUILDING`까지만 허용한다

즉 extension은 late continuation 관리 대상으로 본다.

### 5-4. exact bonus 상한 유지

F6는 F5의 상한 규칙을 그대로 존중한다.

- `STRUCTURE_BLOCKED` override 금지
- `UNCONFIRMED -> CONFIRMED` 직행 금지
- calibration not ready면 승격 제한

즉 F6는 bonus 결과를 그대로 읽되, bonus 권한을 새로 키우지 않는다.

---

## 6. row-level surface

F6는 아래 필드를 row에 남긴다.

- `flow_support_state_profile_v1`
- `flow_support_state_v1`
- `flow_support_state_authority_v1`
- `flow_support_structure_gate_v1`
- `flow_support_base_band_state_v1`
- `flow_support_boosted_band_state_v1`
- `flow_support_bonus_effect_v1`
- `flow_support_threshold_profile_v1`
- `flow_support_reason_summary_v1`

### 6-1. `flow_support_state_authority_v1`

예시:

- `STRUCTURE_HARD_OPPOSED`
- `STRUCTURE_BLOCKED_UNCONFIRMED`
- `PROVISIONAL_CONFIRMED`
- `PROVISIONAL_BUILDING`
- `PROVISIONAL_UNCONFIRMED`
- `EXTENSION_CAPPED_BUILDING`

이 필드는 "왜 최종 state가 이렇게 되었는가"를 가장 짧게 설명한다.

---

## 7. summary artifact

F6 summary는 최소 아래를 포함한다.

- `flow_support_state_count_summary`
- `flow_support_state_authority_count_summary`
- `flow_support_threshold_profile_count_summary`
- `flow_support_structure_gate_count_summary`

이렇게 해야

- 지금 live rows가 confirmed/building/unconfirmed/opposed 어디에 몰려 있는지
- structure block이 많은지
- symbol별 threshold profile이 어떤 분포인지

를 한 번에 볼 수 있다.

---

## 8. 완료 기준

- F6 contract/summary/artifact가 runtime detail에 export된다
- 각 symbol row에서 final `flow_support_state_v1`를 읽을 수 있다
- `FLOW_OPPOSED`와 `FLOW_UNCONFIRMED`가 hard reason 기준으로 분리된다
- extension confirmed cap이 final state에도 유지된다
- exact bonus가 final state에서 hard gate처럼 재등장하지 않는다

상태 기준:

- `READY`
  - contract/summary/row surface 모두 정상
- `HOLD`
  - 일부 row가 upstream field 누락으로 authority path를 충분히 설명하지 못함
- `BLOCKED`
  - F6가 structure 권한을 침범하거나 bonus 상한을 깨뜨림
