# F7. Flow Chain Shadow Comparison 실행 로드맵

## 1. 목적

F7은 old exact-match-only verdict와 new flow-enabled verdict를 같은 row에서 비교하는 shadow 단계다.

이 단계는 rollout이 아니라 comparison layer다.

---

## 2. 구현 순서

### F7-1. Upstream 정합

아래 upstream을 읽는다.

- `symbol_state_strength_profile_match_v1`
- `exact_pilot_match_bonus_source_v1`
- `flow_support_state_v1`
- `flow_support_state_authority_v1`
- `dominance_should_have_done_candidate_v1`

### F7-2. Old verdict 재구성

pilot/profile exactness만 이용해 old exact-only verdict를 공용 `FLOW_*` enum으로 매핑한다.

### F7-3. New verdict 결합

F6의 `flow_support_state_v1`를 new verdict로 사용한다.

### F7-4. Delta 계산

old/new를 비교해

- `UNCHANGED`
- `FLOW_WIDENS_ACCEPTANCE`
- `FLOW_TIGHTENS_ACCEPTANCE`
- `NEW_FLOW_OPPOSED`

로 분류한다.

### F7-5. Candidate improvement 계산

should-have-done candidate row에서 new가 old보다 acceptance를 높였는지 계산한다.

### F7-6. Summary / artifact export

old/new/delta/improved 요약을 artifact로 남긴다.

---

## 3. 구현 산출물

### 문서

- `current_f7_flow_chain_shadow_comparison_detailed_plan_ko.md`
- `current_f7_flow_chain_shadow_comparison_execution_roadmap_ko.md`

### 코드

- `backend/services/flow_chain_shadow_comparison_contract.py`
- `backend/app/trading_application.py`

### 테스트

- `tests/unit/test_flow_chain_shadow_comparison_contract.py`
- `tests/unit/test_trading_application_runtime_status.py`

---

## 4. 운영 규칙

### 허용

- old exact-only baseline 재구성
- new flow-enabled state와의 delta 비교
- should-have-done candidate improvement 집계

### 금지

- F7에서 새 structure 판단 생성
- F7에서 new verdict 수정
- F7 결과를 바로 execution/state25에 연결

---

## 5. 완료 기준

- runtime detail에 F7 contract/summary/artifact가 export된다
- row-level old/new/delta를 읽을 수 있다
- live snapshot에서 widened/tightened/opposed 전이가 설명 가능하다
- 테스트와 py_compile이 모두 통과한다

상태 기준:

- `READY`
  - F7 surface 정상
- `HOLD`
  - 일부 row가 exact fallback source에 의존
- `BLOCKED`
  - comparison delta가 upstream state와 모순됨
