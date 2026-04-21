# F7. Old Exact-Match-Only vs New Flow-Enabled Chain Shadow Comparison 상세 계획

## 1. 목적

F7의 목적은 예전 `exact-match-only` 해석과 현재 `flow-enabled` 해석을 같은 row 위에서 나란히 비교하는 것이다.

즉 F7은 새 체인을 바로 실행으로 올리는 단계가 아니라,

- old exact-only verdict
- new flow-enabled verdict
- 둘 사이의 delta

를 shadow로 surface해서,
"새 체인이 실제로 어디서 더 잘 넓혀주고, 어디서 더 보수적으로 막는가"를 보게 만드는 단계다.

---

## 2. 왜 F7이 필요한가

F6까지 오면 우리는 이미 `flow_support_state_v1`를 읽을 수 있다.

하지만 아직 중요한 질문이 남아 있다.

1. 예전 exact-only 방식이라면 이 row를 뭐라고 불렀을까?
2. 새 flow-enabled 방식은 그 결론을 어떻게 바꿨는가?
3. 그 변화가 should-have-done candidate 관점에서 개선인가, 과잉 확장인가?

F7은 바로 이 질문을 다룬다.

---

## 3. 비교 대상

### 3-1. Old exact-match-only verdict

F7에서 old verdict는 새 구조를 무시하고, pilot/profile exactness만 보던 방식으로 재구성한다.

기본 해석:

- `MATCHED_ACTIVE_PROFILE` -> `FLOW_CONFIRMED`
- `PARTIAL_ACTIVE_PROFILE` -> `FLOW_BUILDING`
- `REVIEW_PENDING / OUT_OF_PROFILE / NOT_APPLICABLE` -> `FLOW_UNCONFIRMED`

즉 old 체인은 구조보다 exactness를 우선하던 read-only verdict로 본다.

### 3-2. New flow-enabled verdict

F6의 최종 상태를 그대로 사용한다.

- `flow_support_state_v1`
- `flow_support_state_authority_v1`

---

## 4. F7에서 답하는 질문

F7은 아래 질문을 row별로 답한다.

1. old exact-only verdict는 무엇이었는가?
2. new flow-enabled verdict는 무엇인가?
3. new가 old보다 acceptance를 넓혔는가?
4. new가 old보다 더 보수적으로 tightened 했는가?
5. new가 hard opposed로 재분류했는가?
6. should-have-done candidate 관점에서 개선이 있었는가?

---

## 5. row-level surface

F7은 아래 필드를 row에 남긴다.

- `flow_chain_shadow_comparison_profile_v1`
- `old_exact_match_only_flow_state_v1`
- `old_exact_match_only_source_v1`
- `new_flow_enabled_state_v1`
- `new_flow_enabled_authority_v1`
- `flow_chain_shadow_delta_v1`
- `flow_chain_shadow_should_have_done_candidate_v1`
- `flow_chain_shadow_candidate_improved_v1`
- `flow_chain_shadow_reason_summary_v1`

### 5-1. `flow_chain_shadow_delta_v1`

- `UNCHANGED`
- `FLOW_WIDENS_ACCEPTANCE`
- `FLOW_TIGHTENS_ACCEPTANCE`
- `NEW_FLOW_OPPOSED`

의미:

- `FLOW_WIDENS_ACCEPTANCE`
  - old보다 new가 더 높은 acceptance를 준 상태
- `FLOW_TIGHTENS_ACCEPTANCE`
  - old보다 new가 더 보수적으로 내린 상태
- `NEW_FLOW_OPPOSED`
  - old는 미정/약한 acceptance였지만 new는 반대 구조로 읽은 상태

### 5-2. `flow_chain_shadow_candidate_improved_v1`

`dominance_should_have_done_candidate_v1 == true`인 row에서,
new가 old보다 더 높은 acceptance를 주면 `true`다.

즉 "old exact-only에서는 놓쳤지만, new flow chain은 더 잘 인정했다"는 뜻이다.

---

## 6. 운영 규칙

### 6-1. old verdict는 재구성값이다

F7의 old verdict는 historical replay가 아니라,
현재 row surface 위에서 "exact-only였다면"을 다시 읽는 shadow 값이다.

즉 execution truth가 아니라 comparison baseline이다.

### 6-2. new verdict는 F6를 그대로 사용한다

F7은 F6를 다시 계산하지 않는다.
F6의 final state를 그대로 읽고 비교만 한다.

### 6-3. delta는 ordinal 비교이되 opposed는 별도 취급

old/new 둘 다 같은 `FLOW_*` enum을 사용하지만,
`FLOW_OPPOSED`는 단순 낮은 점수가 아니라 별도 재분류로 다룬다.

즉

- old `UNCONFIRMED`
- new `OPPOSED`

는 그냥 tightened가 아니라 `NEW_FLOW_OPPOSED`다.

---

## 7. summary artifact

F7 summary는 최소 아래를 포함한다.

- `old_exact_match_only_flow_state_count_summary`
- `new_flow_enabled_state_count_summary`
- `flow_chain_shadow_delta_count_summary`
- `flow_chain_shadow_candidate_improved_count`

이렇게 해야

- 새 체인이 old exact-only보다 실제로 acceptance를 넓히는지
- 아니면 대부분 더 보수적으로 가는지
- should-have-done candidate 구간에서 개선이 있는지

를 한 번에 볼 수 있다.

---

## 8. 완료 기준

- F7 contract/summary/artifact가 runtime detail에 export된다
- old/new verdict와 delta를 각 row에서 읽을 수 있다
- `FLOW_WIDENS_ACCEPTANCE / FLOW_TIGHTENS_ACCEPTANCE / NEW_FLOW_OPPOSED`가 일관되게 surface된다
- should-have-done candidate 개선 여부를 summary에서 읽을 수 있다

상태 기준:

- `READY`
  - contract/summary/row surface 모두 정상
- `HOLD`
  - 일부 row가 old baseline fallback에 의존
- `BLOCKED`
  - old/new 비교가 upstream state와 모순되거나 delta 분류가 뒤집힘
