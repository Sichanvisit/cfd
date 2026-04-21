# F9. bounded calibration candidate

## 1. 목적

F9의 목적은 이미 구축된

- `flow_candidate_improvement_review`
- `nas_btc_hard_opposed_truth_audit`

가 말해주는 진단 결과를,

**구조를 깨지 않는 아주 좁은 calibration 후보**

로 변환하는 것이다.

즉 F9는 threshold를 바로 바꾸는 층이 아니다.
F9는 아래 질문에 답하는 층이다.

- 무엇을 조정 후보로 올릴 것인가
- 무엇은 절대 조정 대상이 아니어야 하는가
- 어느 정도 폭까지만 제안할 것인가
- 이 후보를 어떤 근거로 shadow / bounded apply에 넘길 것인가

---

## 2. 왜 필요한가

지금까지의 구조는 이미 매우 많은 것을 설명할 수 있다.

- 왜 어떤 row가 `FLOW_OPPOSED`가 되었는가
- 그 opposed가 fixed blocker 때문인가, tunable score 때문인가
- old exact-only보다 new flow-enabled chain이 후보를 더 잘 살렸는가
- 아니면 과하게 tightening했는가

하지만 여기서 멈추면 시스템은

**"잘 설명하지만 실제 개선은 사람이 감으로 하는 시스템"**

으로 남는다.

예를 들어 BTC row가

- `OVER_TIGHTENED`
- `MIXED_REVIEW`
- tunable driver로
  - `flow.ambiguity_threshold`
  - `flow.conviction_building_floor`
  - `flow.persistence_recency_weight_scale`

를 같이 가리킨다고 해도,
그 다음 층이 없으면 결국 사람은

- 무엇을 우선 바꿀지
- 어느 정도만 바꿀지
- 한 번에 몇 개만 시험할지
- 실패하면 어떻게 되돌릴지

를 수동으로 결정하게 된다.

F9는 바로 이 간극,

**"설명 -> 안전한 개선 후보"**

를 메우는 첫 운영 층이다.

---

## 3. 상위 원칙

### 3-1. F9는 구조를 바꾸지 않는다

F9는 해석기의 뼈대를 바꾸지 않는다.
F9가 다루는 것은 이미 고정된 해석 구조 위의
좁은 제어 손잡이뿐이다.

### 3-2. candidate는 `symbol × learning_key`를 기본 단위로 둔다

candidate 기본 id는 아래처럼 둔다.

- `BTCUSD:flow.ambiguity_threshold`
- `NAS100:flow.conviction_building_floor`
- `XAUUSD:flow.persistence_building_floor`

이렇게 해야

- 이력 관리가 가능하고
- symbol별 특성을 유지하면서
- 너무 잘게 쪼개진 candidate 폭발을 막을 수 있다.

### 3-3. `error_type`은 identity가 아니라 evidence다

`OVER_TIGHTENED`, `WIDEN_EXPECTED`, `MIXED_REVIEW` 같은 정보는
candidate id를 구성하지 않는다.

이들은

- 왜 이 candidate가 생성되었는지
- 어떤 truth cluster에서 나왔는지

를 설명하는 evidence cluster로만 둔다.

### 3-4. timebox는 candidate 정체성이 아니라 검증 창이다

candidate가 특정 한 구간에만 맞는 local optimization으로 흐르지 않게 하려면,
timebox는 identity가 아니라 validation window로 써야 한다.

즉 candidate는

- 특정 row 하나에 귀속되지 않고
- 같은 symbol의 여러 retained/live window에서
- 버티는지 확인되어야 한다.

### 3-5. identity는 단순하게 두고 scope를 정교하게 한다

v1에서는 candidate identity를 가능한 한 단순하게 유지하는 편이 안전하다.

- identity는 `symbol × learning_key`
- `truth_error_type`, `state bucket`, `timebox`, `review cluster`는 scope/evidence

즉 `BTCUSD:flow.ambiguity_threshold`는 하나의 candidate로 유지하고,
그 candidate를

- `FLOW_BUILDING`에서만
- 특정 retained/live validation window에서만
- 특정 review cluster를 중심으로

시험하는 식으로 범위를 제한하는 편이 더 낫다.

이 원칙은 candidate 파편화를 막고,
같은 key가 반복적으로 어떻게 작동하는지 추적하기 쉽게 만든다.

### 3-6. immutable과 tunable은 다시 섞이지 않는다

F9는 아래를 calibration 대상에서 명시적으로 제외한다.

- `POLARITY_MISMATCH`
- `REVERSAL_REJECTION`
- `REVERSAL_OVERRIDE`
- `dominance_gap` 계산 구조
- `dominant_side` 변경 권한
- decomposition이 side를 바꾸지 못하는 원칙

즉 F9는

**"무엇을 절대 건드리지 않을지"를 먼저 잠그고 시작하는 층**

이다.

### 3-7. shared/common parameter보다 local parameter를 먼저 다룬다

bounded calibration은 영향 범위가 작은 손잡이부터 다루는 것이 원칙이다.

초기에는 아래를 우선한다.

- symbol-local parameter
- state-local apply scope
- small delta candidate

반대로 shared/common parameter는

- 충분한 shadow 검증
- same-symbol cross-window 확인
- cross-symbol drift 확인

이 누적된 뒤에만 다루는 편이 더 안전하다.

---

## 4. 입력 층

F9는 아래를 upstream으로 둔다.

- `F8 flow_candidate_improvement_review`
- `F8b nas_btc_hard_opposed_truth_audit`

핵심 입력 필드:

- `flow_candidate_truth_state_v1`
- `flow_candidate_improvement_verdict_v1`
- `flow_candidate_review_alignment_v1`
- `nas_btc_hard_opposed_truth_audit_state_v1`
- `nas_btc_hard_opposed_fixed_blockers_v1`
- `nas_btc_hard_opposed_tunable_drivers_v1`
- `nas_btc_hard_opposed_learning_state_v1`
- `nas_btc_hard_opposed_learning_keys_v1`
- `nas_btc_hard_opposed_control_score_snapshot_v1`

보조 입력:

- `flow_support_state_v1`
- `flow_structure_gate_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`
- `flow_threshold_profile_v1`

---

## 5. candidate seed 철학

F9는 바로 candidate를 만들지 않고,
먼저 row-level `seed`를 만든 뒤 그것을 집계한다.

### 5-1. seed가 될 수 있는 row

아래는 seed 후보가 될 수 있다.

- `OVER_TIGHTENED`이며 tunable driver가 존재하는 row
- `MIXED_REVIEW`이지만 tunable driver가 존재하는 row
- `WIDEN_EXPECTED`였으나 new chain이 충분히 못 살린 row

### 5-2. seed가 될 수 없는 row

아래는 seed 후보가 되면 안 된다.

- fixed blocker만 있는 `FIXED_HARD_OPPOSED`
- `dominant_side`를 바꿔야만 해결되는 row
- truth가 `REVIEW_PENDING`만 남고 조정 방향이 아직 불분명한 row

즉 F9는

**"학습할 수 없는 실패"와 "학습해볼 가치가 있는 실패"를 먼저 분리**

해야 한다.

---

## 6. candidate seed 분류

row-level seed 상태는 아래처럼 두는 것이 좋다.

- `NOT_APPLICABLE`
- `FIXED_BLOCKED`
- `TUNABLE_SEED`
- `MIXED_SEED`
- `FILTERED_OUT`
- `REVIEW_PENDING`

### 6-1. `TUNABLE_SEED`

- tunable driver만 있고
- fixed blocker가 없으며
- verdict가 `OVER_TIGHTENED` 또는 명확한 missed improvement

### 6-2. `MIXED_SEED`

- fixed blocker와 tunable driver가 함께 있으나
- tunable 부분만 학습 대상으로 뽑아볼 가치가 있는 경우

이 경우 confidence는 기본적으로 낮춘다.

### 6-3. `FIXED_BLOCKED`

- fixed blocker만 본체인 경우
- 설명용으로만 남기고 candidate 생성은 하지 않는다

---

## 7. learning key importance

한 row에서 tunable key가 여러 개 동시에 걸릴 수 있으므로,
F9는 key importance를 같이 계산해야 한다.

최소 축은 아래를 권장한다.

- `truth_pressure`
  - should-have-done truth가 얼마나 분명한가
- `delta_severity`
  - tightening/widening이 얼마나 강하게 잘못 나왔는가
- `tunable_purity`
  - fixed blocker보다 tunable이 본체인가
- `repetition_support`
  - 같은 symbol / 같은 key가 여러 row에서 반복되는가
- `control_gap`
  - 현재 score와 building/confirmed floor 차이가 얼마나 큰가

이 값은 처음부터 복잡한 모델보다
가중 합이나 rank-style score로 두는 편이 안전하다.

하지만 importance만으로는 운영 우선순위를 정하기에 부족하다.
따라서 candidate score는 최소 아래 세 축으로 따로 surface하는 편이 좋다.

- `relevance`
  - 이 key가 현재 error type과 얼마나 직접적으로 연결되는가
- `safety`
  - immutable rule을 건드리지 않고 bounded apply가 가능한가
- `repeatability`
  - 같은 symbol / 유사 window에서 같은 방향 문제로 반복되는가

즉 candidate score는 단순한 "좋아 보임"이 아니라,

**문제 적합성, 안전성, 반복성**

을 동시에 반영해야 한다.

운영에서는 아래처럼 분리하는 편이 더 안정적이다.

- `candidate_relevance_score_v1`
- `candidate_safety_score_v1`
- `candidate_repeatability_score_v1`
- `candidate_priority_score_v1`

여기서 `priority`와 `confidence`는 같은 값이 아니다.

- `priority`
  - 무엇을 먼저 시험할지
- `confidence`
  - 이 candidate가 정말 조정 가능한 본체를 가리키는지

를 뜻한다.

---

## 8. candidate filtering layer

이 단계가 F9의 핵심이다.
없으면 candidate 폭발이 일어난다.

### 8-1. row-level 제한

- row 하나당 review 대상으로 올리는 key는 최대 2개
- importance 상위 1~2개만 유지
- 서로 반대 방향의 조정을 동시에 제안하지 않는다

### 8-2. candidate-level 제한

- 동시에 `ACTIVE` 또는 `SHADOW`로 올리는 candidate는 매우 작게 유지
- 첫 운영에서는 active candidate 최대 2개
- 가능하면 같은 symbol에 대해서도 한 번에 1 key만 shadow로 올린다

### 8-3. recent rollback 보호

- 최근 `ROLLED_BACK`된 같은 `symbol × learning_key`는 즉시 재제안 금지
- 재등장하더라도 `PROPOSED` 수준에서 추가 검토를 요구

### 8-4. mixed row confidence 하향

- `MIXED_SEED`는 candidate 생성은 가능하지만
- confidence를 `LOW`로 캡
- fixed blocker 때문에 최종 상태가 바뀌지 않을 수 있음을 evidence에 남긴다

즉 filtering layer의 목적은

**"좋아 보이는 조정 아이디어를 줄이는 것"이 아니라, 실제로 시험 가능한 몇 개만 남기는 것"**

이다.

### 8-5. candidate 우선순위 규칙

filtering 이후에도 동시에 시험 가능한 candidate 수는 매우 제한적이므로,
남은 후보 사이의 우선순위 규칙이 필요하다.

권장 우선순위는 아래와 같다.

1. fixed blocker와 직접 충돌하지 않는 key를 우선한다
2. 동일 symbol에서 반복적으로 같은 truth-error-type과 함께 등장한 key를 우선한다
3. expected effect 방향이 일관된 key를 우선한다
4. shared/common parameter보다 symbol-local parameter를 먼저 시험한다
5. penalty scale보다 threshold / floor 계열 key를 먼저 시험한다

즉 candidate 우선순위는 단순히 점수가 큰 것을 먼저 시험하는 것이 아니라,

**반복성, 안전성, 국소성, effect 일관성**

이 높은 후보를 먼저 다루는 방향이어야 한다.

---

## 9. candidate 구조

권장 candidate 구조는 아래와 같다.

```json
{
  "candidate_id": "BTCUSD:flow.ambiguity_threshold",
  "symbol": "BTCUSD",
  "learning_key": "flow.ambiguity_threshold",
  "current_value": 0.40,
  "proposed_value": 0.35,
  "delta": -0.05,
  "max_allowed_delta": 0.10,
  "direction": "RELAX",
  "confidence": "MEDIUM",
  "importance_score": 0.74,
  "evidence": {
    "truth_error_types": ["OVER_TIGHTENED"],
    "affected_row_count": 8,
    "pure_tunable_count": 6,
    "mixed_row_count": 2,
    "fixed_blocker_overlap_count": 2,
    "alignment_rate": 0.75
  },
  "scope": {
    "apply_mode": "shadow_only",
    "apply_symbols": ["BTCUSD"],
    "apply_states": ["FLOW_BUILDING", "FLOW_UNCONFIRMED"],
    "validation_windows": ["recent_live", "retained_symbol_windows"],
    "apply_duration_hours": 48
  },
  "rollback": {
    "rollback_to": 0.40,
    "auto_rollback_if": {
      "under_veto_increase_pct": 10,
      "unverified_widening_increase_pct": 20,
      "cross_symbol_drift_pct": 10
    }
  },
  "status": "PROPOSED"
}
```

핵심 설계 원칙:

- `delta`는 반드시 제한된다
- `direction`는 명시적으로 남긴다
- evidence 없이 제안하지 않는다
- scope는 좁게 시작한다
- rollback 기준이 candidate 안에 같이 들어간다

또한 score 계층은 한 값으로만 접지 말고,
최소 아래처럼 나누는 편이 좋다.

- `candidate_relevance_score_v1`
- `candidate_safety_score_v1`
- `candidate_repeatability_score_v1`
- `candidate_priority_score_v1`

여기서 `candidate_priority_score_v1`는
무엇을 먼저 시험할지 정하는 운영 score이고,
`confidence`는 그 candidate가 얼마나 믿을 만한 조정 본체인지를 뜻하는 별도 축으로 둔다.

---

## 10. confidence 규칙

candidate confidence는 최소 아래처럼 두는 편이 좋다.

- `HIGH`
  - pure tunable row가 충분히 많고
  - 같은 key가 반복되며
  - cross-window에서도 유사 패턴이 확인됨
- `MEDIUM`
  - tunable evidence가 우세하지만 표본이 아직 제한적
- `LOW`
  - `MIXED_REVIEW` 비중이 높거나
  - fixed blocker overlap이 크거나
  - retained/live validation이 약함

즉 confidence는

**"이 candidate를 적용하면 얼마나 좋아질까"**

보다,

**"이 candidate가 정말 조정 가능한 본체를 가리키고 있는가"**

를 말해줘야 한다.

---

## 11. proposed delta 원칙

delta는 작게 시작해야 한다.

예:

- threshold/floor류는 소폭 상하향
- penalty scale은 작은 비율 변화
- recency weight는 급격한 구조 변경 금지

중요 원칙:

- 한 번에 큰 폭으로 조정하지 않는다
- 같은 key를 연속 RELAX하기 전에는 충분한 shadow 관찰 기간을 둔다
- 효과가 좋더라도 GRADUATED 전까지는 default 값을 직접 덮어쓰지 않는다

또한 delta는

- relevance가 높더라도
- safety가 낮으면

자동으로 더 작게 제한되는 편이 안전하다.

---

## 12. cross-window validation

candidate는 특정 row 하나에서 좋아 보이는 것만으로는 부족하다.

따라서 최소 아래 검증이 필요하다.

- 같은 symbol의 다른 retained window에서 부작용이 없는가
- 같은 symbol의 최근 live rows에서도 false widening이 급증하지 않는가
- 공용 파라미터라면 다른 symbol의 분포가 흔들리지 않는가

즉 F9의 candidate는

**"좋아 보이는 key"** 가 아니라,

**"다른 창에서도 버틸 가능성이 있는 key"**

여야 한다.

---

## 13. candidate outcome / graduation

bounded apply 이후 모든 candidate가

- 승격되거나
- rollback되기만 하는 것은 아니다.

운영상은 최소 아래 outcome으로 나누는 편이 자연스럽다.

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

### 13-1. `PROMOTE`

- 최소 shadow 관찰 window 수 충족
- same-symbol cross-window에서 일관된 개선
- `under_veto_rate` 유의미한 악화 없음
- `unverified_widening_rate` 급증 없음
- shared/common parameter라면 cross-symbol drift 허용 범위 내

즉 candidate는 단순히 "좋아 보였다"가 아니라,

**bounded apply -> cross-window validation -> harmful widening 없음 -> 안정적 개선**

을 통과했을 때만 졸업해야 한다.

### 13-2. `KEEP_OBSERVING`

- 개선 신호는 있으나
- 관찰 window 또는 sample 수가 아직 부족한 경우

### 13-3. `EXPIRE_WITHOUT_PROMOTION`

- 유의미한 개선도 악화도 없이
- 중립적으로 종료되는 경우

이 outcome이 있어야 active candidate가 zombie처럼 오래 남지 않는다.

### 13-4. `ROLLBACK`

- under-veto 악화
- unverified widening 급증
- cross-symbol drift 증가
- confirmed accuracy 악화

같은 부작용이 나타나면 즉시 되돌린다.

---

## 14. row-level surface

F9가 실제 구현으로 내려갈 때 row에 남길 핵심 field는 아래를 권장한다.

- `bounded_calibration_candidate_seed_state_v1`
- `bounded_calibration_candidate_seed_keys_v1`
- `bounded_calibration_candidate_seed_importance_v1`
- `bounded_calibration_candidate_seed_confidence_v1`
- `bounded_calibration_candidate_seed_priority_v1`
- `bounded_calibration_candidate_seed_reason_v1`

이 row field는 최종 candidate object의 근거를 설명하는 디버그 층이다.

---

## 15. candidate catalog / summary

F9 summary와 artifact에는 최소 아래가 필요하다.

- `candidate_count`
- `candidate_status_count_summary`
- `candidate_direction_count_summary`
- `candidate_confidence_count_summary`
- `candidate_symbol_count_summary`
- `candidate_learning_key_count_summary`
- `candidate_outcome_count_summary`
- `mixed_seed_count`
- `fixed_blocked_count`

그리고 실제 candidate catalog가 같이 있어야 한다.

즉 summary는 count를 보여주고,
artifact는

- 어떤 candidate가
- 어떤 evidence로
- 어떤 delta를 제안받았는지

를 보여줘야 한다.

---

## 16. 상태 기준

- `READY`
  - seed -> filtering -> candidate catalog가 일관되게 만들어짐
  - fixed/tunable 분리가 유지됨
- `HOLD`
  - candidate는 만들어졌지만 evidence가 약하거나 cross-window 검증이 부족함
- `BLOCKED`
  - immutable 항목을 candidate로 밀어올리거나
  - 같은 row에서 candidate filtering이 일관되지 않음

---

## 17. 완료 기준

- `symbol × learning_key` 단위 candidate가 일관되게 생성된다
- fixed blocker row는 candidate로 승격되지 않는다
- `MIXED_REVIEW`는 tunable 부분만 제한적으로 candidate에 반영된다
- candidate마다
  - delta
  - confidence
  - evidence
  - scope
  - rollback
  가 같이 남는다
- 다음 단계의 bounded apply가 바로 이어질 수 있을 정도로 후보가 좁고 설명 가능하다
- 무엇을 먼저 시험할지 `priority`로 설명 가능하다
- 좋은 후보를 언제 졸업시키고, 효과 없는 후보를 언제 종료할지 outcome 규칙이 있다

---

## 18. 다음 단계 연결

F9가 끝나면 다음은 아래 두 단계다.

1. `F10 bounded candidate shadow apply`
   - candidate를 실제 threshold patch로 적용하지 않고 shadow-only로 먼저 시험

2. `F11 candidate evaluation / rollback dashboard`
   - before/after를 숫자로 보고
   - rollback / graduate 결정을 운영 규칙으로 고정
