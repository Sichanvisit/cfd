# F8b. NAS/BTC hard opposed truth audit 실행 로드맵

## 1. 목적

NAS/BTC에서 `FLOW_OPPOSED`가 뜬 row를 한 번 더 파서,

- immutable hard blocker
- learnable control score

를 분리하고, learning-ready tuning key까지 surface한다.

---

## 2. 구현 순서

### S1. upstream 정합

아래 upstream이 없으면 attach helper로 다시 붙인다.

- `flow_candidate_improvement_review`
- `flow_chain_shadow_comparison`
- `dominance_validation_profile`

완료 기준:

- 단독 row 입력만으로도 audit row builder가 동작

### S2. fixed blocker / tunable driver 분리

고정 blocker:

- `POLARITY_MISMATCH`
- `REVERSAL_REJECTION`
- `REVERSAL_OVERRIDE`

tuneable driver:

- `AMBIGUITY_THRESHOLD`
- `STRUCTURE_SOFT_SCORE_FLOOR`
- `CONVICTION_BUILDING_FLOOR`
- `PERSISTENCE_BUILDING_FLOOR`
- `AMBIGUITY_PENALTY_SCALE`
- `VETO_PENALTY_SCALE`
- `RECENCY_WEIGHT_SCALE`

완료 기준:

- row 하나에서 fixed와 tunable이 따로 나온다

### S3. audit state / learning state 판정

audit state:

- `FIXED_HARD_OPPOSED`
- `TUNABLE_OVER_TIGHTEN_RISK`
- `MIXED_REVIEW`

learning state:

- `FIXED_BLOCKED`
- `LEARNING_CANDIDATE`
- `MIXED_REVIEW`

완료 기준:

- over-tightened row가 calibration 대상인지 아닌지 분리됨

### S4. control snapshot / tuning key surface

아래 score snapshot을 row에 남긴다.

- structure soft score
- conviction
- persistence
- ambiguity penalty
- veto penalty
- recency weight
- current floors

그리고 tuning key도 남긴다.

완료 기준:

- 이후 learning/apply 단계에서 재사용할 수 있는 key와 score가 같이 남음

### S5. summary / artifact

summary에서는 아래를 본다.

- fixed blocker count
- tunable driver count
- learning candidate count
- mixed review count

완료 기준:

- live snapshot에서 NAS/BTC hard opposed 성격이 한눈에 읽힘

### S6. runtime_status.detail.json export

detail payload에 아래를 올린다.

- `nas_btc_hard_opposed_truth_audit_contract_v1`
- `nas_btc_hard_opposed_truth_audit_summary_v1`
- `nas_btc_hard_opposed_truth_audit_artifact_paths`

### S7. 검증

단위 테스트:

- fixed blocker only -> fixed blocked
- tunable over-tightened -> learning candidate
- fixed+tunable -> mixed review
- non-opposed row -> non-opposed
- artifact / runtime export

완료 기준:

- 테스트 통과
- `py_compile ok`

---

## 3. 상태 기준

- `READY`: fixed vs tunable vs mixed가 일관되게 분리됨
- `HOLD`: 일부 row가 `REVIEW_PENDING`으로 남아 추가 truth 정제가 필요
- `BLOCKED`: 같은 row에서 upstream attach/recompute 결과가 audit state를 뒤집음

---

## 4. 다음 단계 연결

F8b가 끝나면 다음은 두 방향이다.

1. `learning candidate`로 잡힌 tuneable control만 bounded calibration 대상으로 묶기
2. `fixed hard blocked`는 구조 보호 영역으로 고정하고 learning 대상에서 제외하기
