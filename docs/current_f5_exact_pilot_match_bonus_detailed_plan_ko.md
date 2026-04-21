# F5. Exact Pilot Match Bonus 상세 계획

## 1. 목적

F5의 목적은 `exact pilot match`를 더 이상 hard gate로 쓰지 않고,

- `F1 flow_structure_gate_v1`
- `F2 aggregate_conviction_v1 / flow_persistence_v1`
- `F3 retained calibration`
- `F4 provisional band`

를 통과하거나 설명 가능한 상태 위에서만 작동하는 **bonus layer**로 재배치하는 것이다.

즉 F5는 "pilot과 똑같지 않으면 탈락"을 만드는 단계가 아니라,
"이미 구조와 flow 후보 자격을 받은 장면에 검증된 pilot 유사성을 보너스로 더하는 단계"다.

---

## 2. 왜 F5가 필요한가

F4까지 오면 우리는 이미 다음을 읽을 수 있다.

- 구조가 directional flow 후보인지
- conviction/persistence가 어느 band에 있는지
- symbol-specific retained threshold profile이 무엇인지

하지만 아직 비어 있는 질문이 하나 있다.

`exact pilot match`를 이제 어디까지 허용할 것인가?

이걸 정리하지 않으면 두 가지로 무너진다.

1. 다시 exact match가 hard gate처럼 커진다.
2. 반대로 pilot evidence를 너무 약하게 봐서 검증된 anchor를 버리게 된다.

F5는 이 둘 사이에서 exact match를 **보너스이되 상한이 있는 층**으로 고정한다.

---

## 3. 권한 구조

F5의 권한은 항상 아래 순서를 따른다.

1. `F1 flow_structure_gate_v1`
2. `F4 provisional_flow_band_state_v1`
3. `F5 exact pilot match bonus`

중요한 원칙:

- structure gate를 통과하지 못한 row는 bonus를 받지 못한다.
- `STRUCTURE_BLOCKED`는 exact match가 있어도 뒤집지 못한다.
- exact match는 structure를 대체하지 못한다.
- exact match는 threshold band를 무시한 승격기가 아니다.

---

## 4. F5에서 답하는 질문

F5는 아래 질문을 읽는다.

1. 이 row는 active pilot window와 `MATCHED_ACTIVE_PROFILE`인가?
2. 아니면 `PARTIAL_ACTIVE_PROFILE`인가?
3. symbol별 calibration state가 `PROVISIONAL_BAND_READY`인가?
4. 현재 provisional band state는 `CONFIRMED / BUILDING / UNCONFIRMED` 중 어디인가?
5. stage가 `EXTENSION`이라서 bonus 상한을 막아야 하는가?

즉 F5는 "pilot match가 있다/없다"만 보지 않고,

- match quality
- calibration readiness
- current band state
- extension cap

를 같이 본다.

---

## 5. row-level surface

F5는 아래 필드를 row에 남긴다.

- `exact_pilot_match_bonus_profile_v1`
- `exact_pilot_match_bonus_source_v1`
- `exact_pilot_match_bonus_strength_v1`
- `exact_pilot_match_bonus_effect_v1`
- `pilot_match_bonus_applied_v1`
- `pilot_match_bonus_delta_levels_v1`
- `boosted_provisional_flow_band_state_v1`
- `exact_pilot_match_bonus_reason_summary_v1`

### 5-1. `exact_pilot_match_bonus_source_v1`

- `MATCHED_ACTIVE_PROFILE`
- `PARTIAL_ACTIVE_PROFILE`
- `REVIEW_PENDING`
- `OUT_OF_PROFILE`
- `NOT_APPLICABLE`
- `FALLBACK_MATCH`
- `FALLBACK_PARTIAL`

### 5-2. `exact_pilot_match_bonus_effect_v1`

- `NOT_APPLICABLE`
- `BONUS_BLOCKED`
- `NO_ACTIVE_MATCH`
- `VALIDATION_ONLY`
- `PRIORITY_BOOST`
- `UNCONFIRMED_TO_BUILDING`
- `BUILDING_TO_CONFIRMED`
- `WITHHELD_BY_EXTENSION`
- `WITHHELD_BY_CALIBRATION`
- `WITHHELD_BY_BONUS_CEILING`

### 5-3. `boosted_provisional_flow_band_state_v1`

- `STRUCTURE_BLOCKED`
- `CONFIRMED_CANDIDATE`
- `BUILDING_CANDIDATE`
- `UNCONFIRMED_CANDIDATE`
- `NOT_APPLICABLE`

---

## 6. 핵심 운영 규칙

### 6-1. structure-first

아래 중 하나면 bonus는 차단된다.

- `flow_structure_gate_v1` not in `ELIGIBLE / WEAK`
- `provisional_flow_band_state_v1 == STRUCTURE_BLOCKED`

즉 exact match가 있어도 `BONUS_BLOCKED`다.

### 6-2. exact match는 bonus만 준다

exact match는 아래 역할만 한다.

- `CONFIRMED_CANDIDATE`를 validated 상태로 설명
- `BUILDING_CANDIDATE`에 priority boost 부여
- 제한적으로 `UNCONFIRMED_CANDIDATE -> BUILDING_CANDIDATE`
- 제한적으로 `BUILDING_CANDIDATE -> CONFIRMED_CANDIDATE`

하지만 다음은 금지한다.

- `UNCONFIRMED_CANDIDATE -> CONFIRMED_CANDIDATE` 직행
- `STRUCTURE_BLOCKED -> BUILDING/CONFIRMED` 승격
- structure fail override

### 6-3. calibration readiness가 먼저다

`retained_window_calibration_state_v1 != PROVISIONAL_BAND_READY`면
bonus는 설명/priority 용도로만 쓰고, 상태 승격은 제한한다.

즉 calibration이 partial이면

- `VALIDATION_ONLY`
- `PRIORITY_BOOST`

는 가능하지만, 확정적인 state upgrade는 보수적으로 다룬다.

### 6-4. extension cap 유지

`stage == EXTENSION`이면 bonus는 confirmed 승격을 만들 수 없다.

즉 extension은

- validated
- priority boost

까지만 가능하고,
`BUILDING_TO_CONFIRMED`는 금지한다.

---

## 7. bonus 강도 해석

F5는 F3의 `exact_match_bonus_strength_v1`를 읽는다.

- `LOW`
- `LOW_MEDIUM`
- `MEDIUM`
- `HIGH`

초기 운영 원칙:

- `MATCHED_ACTIVE_PROFILE`는 가장 강한 bonus source
- `PARTIAL_ACTIVE_PROFILE`는 약한 bonus source
- `REVIEW_PENDING`는 bonus source가 아니라 관찰용
- `OUT_OF_PROFILE`는 bonus 없음

그리고 strength가 높아도

- structure block
- extension cap
- calibration not ready

를 넘지 못한다.

---

## 8. 요약 artifact

F5 summary는 최소 아래를 남긴다.

- `exact_pilot_match_bonus_source_count_summary`
- `exact_pilot_match_bonus_effect_count_summary`
- `boosted_provisional_flow_band_state_count_summary`
- `exact_pilot_match_bonus_strength_count_summary`

이렇게 해야

- bonus가 실제로 얼마나 적용됐는지
- validation만 하고 있는지
- state 승격까지 일어났는지
- 어느 심볼에서 보수적으로 막히는지

를 한 번에 볼 수 있다.

---

## 9. 완료 기준

- F5 contract/summary/artifact가 runtime detail에 export된다
- 각 symbol row에서 exact pilot match가
  - blocked인지
  - validation only인지
  - priority boost인지
  - 실제 band 승격인지
  읽을 수 있다
- `UNCONFIRMED -> CONFIRMED` 직행 금지가 코드와 surface에 명시된다
- extension과 structure block이 bonus보다 우선 적용된다

상태 기준:

- `READY`
  - contract/summary/row surface 모두 정상
- `HOLD`
  - 일부 symbol에서 upstream readonly pilot match field가 비어 있음
- `BLOCKED`
  - exact bonus가 structure 권한을 침범하거나 상한 규칙이 깨짐
