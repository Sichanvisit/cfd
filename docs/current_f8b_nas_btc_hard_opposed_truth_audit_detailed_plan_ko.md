# F8b. NAS/BTC hard opposed truth audit

## 1. 목적

이 단계의 목적은 NAS/BTC에서 `FLOW_OPPOSED`가 나왔을 때,

- 이 opposed가 정말 고정되어야 하는 opposed인지
- 아니면 should-have-done truth를 너무 빨리 눌러버린 opposed인지
- 그리고 그 opposed를 만든 요인이 고정 규칙인지, 학습 가능한 제어 점수인지

를 분리해서 보는 것이다.

즉 핵심은 아래 두 층을 분리하는 데 있다.

- **고정해야 하는 hard blocker**
- **학습으로 조정 가능한 control score**

---

## 2. 왜 필요한가

F8 결과에서 현재 live snapshot은 아래를 보여줬다.

- `NAS100 = WIDEN_EXPECTED + NEW_FLOW_OPPOSED + OVER_TIGHTENED`
- `BTCUSD = WIDEN_EXPECTED + NEW_FLOW_OPPOSED + OVER_TIGHTENED`

이건 단순히 “새 체인이 엄격하다”에서 끝나면 안 된다.

이제는 한 단계 더 들어가서 아래를 분리해야 한다.

1. polarity mismatch / reversal rejection / reversal override 같은 **절대 규칙** 때문에 막힌 것인가
2. ambiguity threshold / structure soft score / conviction band / persistence band 같은 **학습 가능한 점수 제어부** 때문에 막힌 것인가

이걸 분리해야:

- 절대 건드리면 안 되는 구조는 보호하고
- 조정 가능한 threshold/penalty/recency weight만 학습 대상으로 남길 수 있다

---

## 3. 상위 원칙

### 3-1. 고정 규칙과 학습 규칙을 섞지 않는다

아래는 고정 hard blocker로 유지한다.

- `POLARITY_MISMATCH`
- `REVERSAL_REJECTION`
- `REVERSAL_OVERRIDE`

이건 symbol별 예외나 학습으로 완화하지 않는다.

### 3-2. control score는 학습 가능하게 남긴다

아래는 tuneable control driver로 본다.

- ambiguity threshold
- structure soft score floor
- conviction building floor
- persistence building floor
- ambiguity penalty scale
- veto penalty scale
- persistence recency weight

### 3-3. 이번 단계는 audit이지 apply가 아니다

지금은 학습 가능한 점수들을 **노출하고 분류하는 단계**다.

실제 값 적용은 이후 calibration/apply 단계로 넘긴다.

---

## 4. 입력 층

F8b는 아래 upstream을 사용한다.

- `F1 flow_structure_gate_v1`
- `F2 aggregate_directional_flow_metrics_v1`
- `F6 flow_support_state_v1`
- `F8 flow_candidate_improvement_review_v1`

핵심 입력 필드:

- `flow_structure_gate_hard_disqualifiers_v1`
- `flow_structure_gate_soft_score_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`
- `aggregate_ambiguity_penalty_v1`
- `aggregate_veto_penalty_v1`
- `flow_persistence_recency_weight_v1`
- `flow_candidate_improvement_verdict_v1`
- `new_flow_enabled_state_v1`

---

## 5. audit state 정의

F8b는 아래 state를 사용한다.

- `NOT_APPLICABLE`
- `NON_OPPOSED`
- `FIXED_HARD_OPPOSED`
- `TUNABLE_OVER_TIGHTEN_RISK`
- `MIXED_REVIEW`
- `REVIEW_PENDING`

의미:

- `FIXED_HARD_OPPOSED`
  - opposed의 주된 원인이 immutable hard blocker
- `TUNABLE_OVER_TIGHTEN_RISK`
  - opposed가 truth 기준 over-tightened이고, 원인이 주로 tuneable control
- `MIXED_REVIEW`
  - fixed blocker와 tuneable driver가 같이 섞여 있음

---

## 6. learning state 정의

학습 가능성은 별도 state로 둔다.

- `NOT_APPLICABLE`
- `FIXED_BLOCKED`
- `LEARNING_CANDIDATE`
- `MIXED_REVIEW`
- `REVIEW_PENDING`

이 구분이 필요한 이유는,
모든 over-tightened row를 곧바로 threshold 조정 대상으로 보내면 구조가 무너질 수 있기 때문이다.

---

## 7. control score snapshot

F8b는 tuning 가능한 입력들을 row에 snapshot으로 남긴다.

- `flow_structure_gate_soft_score_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`
- `aggregate_ambiguity_penalty_v1`
- `aggregate_veto_penalty_v1`
- `flow_persistence_recency_weight_v1`
- `aggregate_conviction_building_floor_v1`
- `flow_persistence_building_floor_v1`

이렇게 해야 나중에 “왜 이 row가 learning candidate였는가”를 다시 계산 없이 재검토할 수 있다.

---

## 8. learning key surface

F8b는 tuneable driver를 사람 말이 아니라 tuning key로도 surface한다.

예:

- `flow.ambiguity_threshold`
- `flow.structure_soft_score_floor`
- `flow.conviction_building_floor`
- `flow.persistence_building_floor`
- `flow.ambiguity_penalty_scale`
- `flow.veto_penalty_scale`
- `flow.persistence_recency_weight_scale`

이 key들은 이후 bounded calibration / learning patch에서 연결 지점이 된다.

---

## 9. row-level surface

아래 flat field를 row에 올린다.

- `nas_btc_hard_opposed_truth_audit_profile_v1`
- `nas_btc_hard_opposed_truth_audit_state_v1`
- `nas_btc_hard_opposed_truth_alignment_v1`
- `nas_btc_hard_opposed_fixed_blockers_v1`
- `nas_btc_hard_opposed_tunable_drivers_v1`
- `nas_btc_hard_opposed_control_score_snapshot_v1`
- `nas_btc_hard_opposed_learning_state_v1`
- `nas_btc_hard_opposed_learning_keys_v1`
- `nas_btc_hard_opposed_reason_summary_v1`

---

## 10. 요약 지표

summary에서는 최소 아래를 본다.

- `nas_btc_hard_opposed_truth_audit_state_count_summary`
- `nas_btc_hard_opposed_truth_alignment_count_summary`
- `nas_btc_hard_opposed_learning_state_count_summary`
- `nas_btc_hard_opposed_fixed_blocker_count_summary`
- `nas_btc_hard_opposed_tunable_driver_count_summary`
- `learning_candidate_count`
- `mixed_review_count`

---

## 11. 완료 기준

- NAS/BTC가 `FLOW_OPPOSED`일 때,
  - 고정 blocker 때문인지
  - 학습 가능한 점수 제어부 때문인지
  - 둘이 섞였는지
  row와 summary에서 분리된다.
- execution/state25는 바뀌지 않는다.
- 이후 calibration 단계에서 바로 쓸 수 있는 tuning key가 남는다.
