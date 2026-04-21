# F8. should-have-done alignment / candidate improvement review

## 1. 목적

F8의 목적은 `F7 old exact-match-only vs new flow-enabled chain shadow comparison` 결과가 실제 should-have-done 후보 truth를 더 잘 살렸는지, 아니면 과하게 tighten했는지를 분리해서 읽는 것이다.

즉 F8은 단순히

- old state
- new state
- delta

를 나열하는 층이 아니라,

`이 delta가 후보 truth 기준으로 좋은 widening인가 / 놓친 widening인가 / 과한 tightening인가`

를 review verdict로 고정하는 층이다.

---

## 2. 왜 필요한가

F7까지만 있으면 아래 정보는 볼 수 있다.

- old exact-only는 어떻게 읽었는가
- new flow-enabled chain은 어떻게 읽었는가
- 둘의 차이는 widening인가 tightening인가

하지만 아직 아래 질문에는 답이 약하다.

- widening이 실제로 좋은 widening인가
- tightening이 실제로 필요한 tightening인가
- should-have-done candidate를 새 체인이 더 잘 살렸는가
- 아니면 후보를 오히려 더 눌렀는가

F8은 이 간극을 메운다.

---

## 3. 상위 원칙

### 3-1. F8은 새 판단기를 만드는 층이 아니다

F8은 execution을 바꾸지 않는다.
F8은 `F7 delta`와 `dominance validation truth`를 review verdict로 번역하는 층이다.

### 3-2. candidate truth는 기존 should-have-done 축을 재사용한다

truth는 새로 발명하지 않는다.
아래 필드를 우선 truth anchor로 사용한다.

- `dominance_should_have_done_candidate_v1`
- `dominance_error_type_v1`

### 3-3. widening과 tightening은 truth 없이 좋다/나쁘다를 말하지 않는다

`FLOW_WIDENS_ACCEPTANCE`가 무조건 좋은 것도 아니고,
`NEW_FLOW_OPPOSED`가 무조건 나쁜 것도 아니다.

반드시 candidate truth와 같이 본다.

---

## 4. 입력 층

F8은 아래 두 층을 upstream으로 둔다.

- `F7 flow_chain_shadow_comparison`
- `dominance_validation_profile`

핵심 입력 필드:

- `old_exact_match_only_flow_state_v1`
- `new_flow_enabled_state_v1`
- `flow_chain_shadow_delta_v1`
- `dominance_should_have_done_candidate_v1`
- `dominance_error_type_v1`

---

## 5. truth 상태 정의

F8은 candidate truth를 아래 4개로 정리한다.

- `NO_CANDIDATE`
- `WIDEN_EXPECTED`
- `TIGHTEN_EXPECTED`
- `REVIEW_PENDING`

### 5-1. WIDEN_EXPECTED

아래류는 새 체인이 acceptance를 더 넓혀야 하는 후보로 본다.

- `CONTINUATION_UNDERPROMOTED`
- `BOUNDARY_STAYED_TOO_LONG`
- `FRICTION_MISREAD_AS_REVERSAL`
- `REVERSAL_OVERCALLED`

### 5-2. TIGHTEN_EXPECTED

아래류는 새 체인이 더 tighten하거나 opposed까지 갈 수 있어야 하는 후보로 본다.

- `TRUE_REVERSAL_MISSED`

### 5-3. NO_CANDIDATE

- `dominance_should_have_done_candidate_v1 == false`

### 5-4. REVIEW_PENDING

candidate는 true지만 error type이 widening/tightening 한쪽으로 아직 깨끗하게 안 묶이는 경우

---

## 6. review verdict 정의

F8 최종 review verdict는 아래 enum으로 고정한다.

- `ALIGNED_IMPROVEMENT`
- `MISSED_IMPROVEMENT`
- `OVER_TIGHTENED`
- `ALIGNED_TIGHTENING`
- `MISSED_TIGHTENING`
- `OVER_WIDENED`
- `UNVERIFIED_WIDENING`
- `SAFE_TIGHTENING`
- `NEUTRAL_NO_CANDIDATE`
- `REVIEW_PENDING`

---

## 7. 판정 규칙

### 7-1. widen expected

- `FLOW_WIDENS_ACCEPTANCE` -> `ALIGNED_IMPROVEMENT`
- `UNCHANGED` + 여전히 low acceptance -> `MISSED_IMPROVEMENT`
- `FLOW_TIGHTENS_ACCEPTANCE` or `NEW_FLOW_OPPOSED` -> `OVER_TIGHTENED`

### 7-2. tighten expected

- `FLOW_TIGHTENS_ACCEPTANCE` or `NEW_FLOW_OPPOSED` -> `ALIGNED_TIGHTENING`
- `UNCHANGED` -> `MISSED_TIGHTENING`
- `FLOW_WIDENS_ACCEPTANCE` -> `OVER_WIDENED`

### 7-3. no candidate

- `FLOW_WIDENS_ACCEPTANCE` -> `UNVERIFIED_WIDENING`
- `FLOW_TIGHTENS_ACCEPTANCE` or `NEW_FLOW_OPPOSED` -> `SAFE_TIGHTENING`
- `UNCHANGED` -> `NEUTRAL_NO_CANDIDATE`

---

## 8. row-level surface

F8은 아래 flat field를 row에 올린다.

- `flow_candidate_improvement_review_profile_v1`
- `flow_candidate_truth_state_v1`
- `flow_candidate_shadow_delta_v1`
- `flow_candidate_review_alignment_v1`
- `flow_candidate_improvement_verdict_v1`
- `flow_candidate_review_priority_v1`
- `flow_candidate_improved_v1`
- `flow_candidate_review_reason_summary_v1`

---

## 9. summary 지표

요약에서는 최소 아래를 본다.

- `flow_candidate_truth_state_count_summary`
- `flow_candidate_improvement_verdict_count_summary`
- `flow_candidate_review_alignment_count_summary`
- `candidate_count`
- `candidate_improved_count`
- `candidate_missed_count`
- `candidate_regression_count`
- `unverified_widening_count`

---

## 10. 완료 기준

- 같은 row에서
  - old exact-only
  - new flow-enabled
  - should-have-done truth
  - 최종 review verdict
  가 한 번에 읽힌다.
- `좋은 widening / 과한 tightening / 놓친 tightening / no-candidate widening`
  이 요약 count로 분리된다.
- execution/state25는 바뀌지 않는다.
