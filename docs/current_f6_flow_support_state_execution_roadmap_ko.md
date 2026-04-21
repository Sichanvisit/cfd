# F6. `flow_support_state_v1` 실행 로드맵

## 1. 목적

F6는 F1~F5를 하나의 공용 directional flow state로 정리하는 단계다.

이 단계에서 새 threshold를 만들지 않고,
이미 있는 구조/밴드/보너스 결론을 final read-only state로 고정한다.

---

## 2. 구현 순서

### F6-1. Upstream 정합

아래 upstream을 동일 기준으로 읽는다.

- `flow_structure_gate_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`
- `provisional_flow_band_state_v1`
- `boosted_provisional_flow_band_state_v1`
- `exact_pilot_match_bonus_effect_v1`

### F6-2. Hard opposed vs unconfirmed 분리

gate가 `INELIGIBLE`일 때도 모두 `FLOW_OPPOSED`로 보내지 않는다.

- polarity/reversal hard conflict -> `FLOW_OPPOSED`
- ambiguity/support 부족 -> `FLOW_UNCONFIRMED`

### F6-3. Band 기반 final state 결정

structure가 살아 있는 row는 boosted band state를 기본으로 final state를 정한다.

- confirmed candidate -> confirmed
- building candidate -> building
- unconfirmed candidate -> unconfirmed

### F6-4. Extension cap 재적용

`EXTENSION`이면 confirmed를 building으로 캡한다.

### F6-5. Summary / artifact export

state, authority, threshold profile, gate 분포를 summary에 남긴다.

---

## 3. 구현 산출물

### 문서

- `current_f6_flow_support_state_detailed_plan_ko.md`
- `current_f6_flow_support_state_execution_roadmap_ko.md`

### 코드

- `backend/services/flow_support_state_contract.py`
- `backend/app/trading_application.py`

### 테스트

- `tests/unit/test_flow_support_state_contract.py`
- `tests/unit/test_trading_application_runtime_status.py`

---

## 4. 운영 규칙

### 허용

- `BUILDING -> CONFIRMED` 반영
- `UNCONFIRMED -> BUILDING` 반영
- structure hard opposed / blocked unconfirmed 분리
- extension confirmed cap 유지

### 금지

- structure fail을 confirmed/building으로 뒤집기
- bonus로 `UNCONFIRMED -> CONFIRMED` 직행
- extension을 confirmed로 내리기

---

## 5. 완료 기준

- runtime detail에 F6 contract/summary/artifact가 export된다
- row-level에서 `flow_support_state_v1`와 authority path를 읽을 수 있다
- live snapshot에서 opposed/unconfirmed 분리가 설명 가능하다
- 테스트와 py_compile이 모두 통과한다

상태 기준:

- `READY`
  - F6 surface 정상
- `HOLD`
  - 일부 row가 upstream fallback에 의존
- `BLOCKED`
  - F6가 structure-first 원칙을 깨뜨림
