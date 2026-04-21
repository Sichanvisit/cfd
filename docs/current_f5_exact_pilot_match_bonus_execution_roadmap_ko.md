# F5. Exact Pilot Match Bonus 실행 로드맵

## 1. 목적

F5는 `exact pilot match`를 hard gate에서 bonus layer로 내리되,

- structure-first
- threshold-as-confidence
- extension cap
- symbol-specific calibration readiness

를 그대로 유지하는 실행 단계를 정리한다.

---

## 2. 구현 순서

### F5-1. Upstream 정합

아래 upstream을 동일 기준으로 읽는다.

- `flow_structure_gate_v1`
- `provisional_flow_band_state_v1`
- `retained_window_calibration_state_v1`
- symbol별 readonly `*_pilot_window_match_v1`

### F5-2. Bonus source 통일

symbol별 pilot match를 공용 source enum으로 정규화한다.

- `MATCHED_ACTIVE_PROFILE`
- `PARTIAL_ACTIVE_PROFILE`
- `REVIEW_PENDING`
- `OUT_OF_PROFILE`

필드가 비면 fallback으로 `symbol_state_strength_profile_match_v1`를 사용한다.

### F5-3. Bonus 상한 규칙 적용

아래 상한을 먼저 적용한다.

- structure blocked면 bonus 차단
- calibration not ready면 state 승격 제한
- extension이면 confirmed 승격 금지
- `UNCONFIRMED -> CONFIRMED` 직행 금지

### F5-4. Bonus effect 계산

각 row를 아래 중 하나로 분류한다.

- `VALIDATION_ONLY`
- `PRIORITY_BOOST`
- `UNCONFIRMED_TO_BUILDING`
- `BUILDING_TO_CONFIRMED`
- `WITHHELD_*`

### F5-5. Summary / artifact export

source/effect/boosted-state 요약을 artifact로 남긴다.

---

## 3. 구현 산출물

### 문서

- `current_f5_exact_pilot_match_bonus_detailed_plan_ko.md`
- `current_f5_exact_pilot_match_bonus_execution_roadmap_ko.md`

### 코드

- `backend/services/exact_pilot_match_bonus_contract.py`
- `backend/app/trading_application.py`

### 테스트

- `tests/unit/test_exact_pilot_match_bonus_contract.py`
- `tests/unit/test_trading_application_runtime_status.py`

---

## 4. 운영 규칙

### 허용

- `CONFIRMED_CANDIDATE + exact match` validated surface
- `BUILDING_CANDIDATE + exact match` priority boost
- 제한적 `UNCONFIRMED -> BUILDING`
- 제한적 `BUILDING -> CONFIRMED`

### 금지

- `STRUCTURE_BLOCKED` override
- `UNCONFIRMED -> CONFIRMED` 직행
- `EXTENSION -> CONFIRMED` 승격
- hard disqualifier 무시

---

## 5. 완료 기준

- runtime detail에 F5 contract/summary/artifact가 export된다
- row-level에서 bonus source/effect/boosted state를 읽을 수 있다
- live snapshot에서 exact match bonus가 structure 권한을 넘지 못함이 확인된다
- 테스트와 py_compile이 모두 통과한다

상태 기준:

- `READY`
  - F5 surface 정상, 상한 규칙 정상
- `HOLD`
  - 일부 symbol bonus source가 fallback에 의존
- `BLOCKED`
  - bonus가 structure 권한을 침범하거나 금지 승격이 발생
