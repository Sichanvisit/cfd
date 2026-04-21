# F9. bounded calibration candidate 실행 로드맵

## 1. 목적

F8 / F8b가 만들어낸

- candidate truth verdict
- fixed vs tunable 분리
- learning key surface

를 바탕으로,

실제로 시험 가능한 bounded calibration candidate를
`symbol × learning_key` 단위로 materialize하는 것이 목적이다.

이 단계는 threshold를 바로 바꾸는 단계가 아니라,

**"무엇을 왜 얼마나 바꿔볼지"를 운영 가능한 객체로 만드는 단계**

다.

---

## 2. 구현 순서

### S1. upstream 정합

아래 upstream이 row에 없으면 attach helper로 다시 붙인다.

- `flow_candidate_improvement_review`
- `nas_btc_hard_opposed_truth_audit`

완료 기준:

- 단독 row 입력만으로도 candidate seed builder가 self-contained하게 동작

### S2. row-level seed 추출

row를 아래 seed state로 분류한다.

- `NOT_APPLICABLE`
- `FIXED_BLOCKED`
- `TUNABLE_SEED`
- `MIXED_SEED`
- `FILTERED_OUT`
- `REVIEW_PENDING`

완료 기준:

- 모든 row가 "candidate 생성 가능 / 불가 / 보류" 중 하나로 분리됨

### S3. learning key importance 계산

row의 tunable learning key마다 importance를 계산한다.

최소 축:

- `truth_pressure`
- `delta_severity`
- `tunable_purity`
- `repetition_support`
- `control_gap`

완료 기준:

- row 하나에서 여러 key가 있더라도 우선순위를 정할 수 있음

### S4. candidate priority / score 분해

importance와 별도로 아래 score 축을 분리한다.

- `candidate_relevance_score_v1`
- `candidate_safety_score_v1`
- `candidate_repeatability_score_v1`
- `candidate_priority_score_v1`

완료 기준:

- `priority`와 `confidence`가 분리되고,
- 무엇을 먼저 시험할지 설명 가능한 상태가 됨

### S5. candidate filtering layer

필터 규칙:

- row당 review key 최대 2개
- conflicting direction 동시 제안 금지
- fixed-only row는 candidate 생성 금지
- `MIXED_SEED`는 confidence 하향
- 최근 rollback된 same `symbol × learning_key`는 재제안 억제

완료 기준:

- candidate 폭발 없이 시험 가능한 key만 남음

### S6. `symbol × learning_key` 집계

row-level seed를 아래 기본 단위로 집계한다.

- `BTCUSD:flow.ambiguity_threshold`
- `NAS100:flow.conviction_building_floor`

집계 항목:

- affected row count
- pure tunable count
- mixed row count
- fixed blocker overlap count
- truth error type cluster
- alignment rate

완료 기준:

- candidate가 row가 아니라 운영 가능한 단위로 묶임

### S7. candidate object materialization

각 candidate에 아래를 채운다.

- `current_value`
- `proposed_value`
- `delta`
- `max_allowed_delta`
- `direction`
- `confidence`
- `importance_score`
- `evidence`
- `scope`
- `rollback`
- `status`

초기 status:

- `PROPOSED`
- `FILTERED_OUT`
- `REVIEW_ONLY`

완료 기준:

- 사람이 읽고 바로 shadow apply로 넘길 수 있는 candidate object가 생김

### S8. cross-window validation seed

candidate 자체에 아래 validation scope를 같이 박아둔다.

- same-symbol retained windows
- same-symbol recent live windows
- shared parameter일 경우 cross-symbol check

완료 기준:

- candidate가 특정 row 하나에만 맞는 제안인지 아닌지 검증 경로가 명시됨

### S9. candidate outcome / graduation rule

candidate lifecycle outcome을 아래처럼 고정한다.

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

graduation 최소 조건:

- 최소 shadow 관찰 window 수 충족
- same-symbol cross-window에서 일관된 개선
- `under_veto` 악화 없음
- `unverified_widening` 급증 없음
- shared/common parameter면 cross-symbol drift 허용 범위 내

완료 기준:

- rollback만이 아니라 promote / keep observing / expire가 같이 정의됨

### S10. row-level flat surface

row에 아래 필드를 올린다.

- `bounded_calibration_candidate_seed_state_v1`
- `bounded_calibration_candidate_seed_keys_v1`
- `bounded_calibration_candidate_seed_importance_v1`
- `bounded_calibration_candidate_seed_confidence_v1`
- `bounded_calibration_candidate_seed_priority_v1`
- `bounded_calibration_candidate_seed_reason_v1`

완료 기준:

- row를 보면 왜 어떤 candidate가 생겼는지 설명 가능

### S11. summary / artifact

summary:

- `candidate_count`
- `candidate_status_count_summary`
- `candidate_direction_count_summary`
- `candidate_confidence_count_summary`
- `candidate_symbol_count_summary`
- `candidate_learning_key_count_summary`
- `candidate_outcome_count_summary`
- `mixed_seed_count`
- `fixed_blocked_count`

artifact:

- candidate catalog JSON
- candidate review Markdown

완료 기준:

- 운영자가 "지금 어떤 candidate가 떠 있는가"를 한 번에 볼 수 있음

### S12. runtime_status.detail.json export

detail payload에 아래를 올린다.

- `bounded_calibration_candidate_contract_v1`
- `bounded_calibration_candidate_summary_v1`
- `bounded_calibration_candidate_artifact_paths`

완료 기준:

- runtime detail에서 F9 계약/요약/artifact path를 바로 읽을 수 있음

### S13. 검증

단위 테스트 최소 항목:

- fixed-only row는 candidate 생성 금지
- pure tunable row는 `TUNABLE_SEED`
- mixed row는 `MIXED_SEED` + low confidence
- row당 key 2개 제한
- candidate id는 `symbol × learning_key`
- recently rolled-back key는 즉시 재제안 억제
- priority와 confidence가 분리되어 surface됨
- no-change candidate는 `EXPIRE_WITHOUT_PROMOTION`으로 종료 가능
- artifact write / runtime export

완료 기준:

- 테스트 통과
- `py_compile ok`

---

## 3. 상태 기준

- `READY`
  - candidate catalog가 일관되게 surface됨
  - fixed/tunable 분리가 유지됨
- `HOLD`
  - candidate는 생성되었지만 evidence나 validation scope가 약함
- `BLOCKED`
  - immutable 항목이 candidate로 올라오거나
  - candidate filtering이 row마다 뒤집힘

---

## 4. 다음 단계 연결

F9가 끝나면 다음은 두 갈래로 이어진다.

1. `F10 bounded candidate shadow apply`
   - `PROPOSED` candidate를 아주 좁은 scope에서 shadow-only로 시험

2. `F11 candidate evaluation / rollback dashboard`
   - before/after를 비교해서
   - `PROMOTE / KEEP_OBSERVING / EXPIRE_WITHOUT_PROMOTION / ROLLBACK`
   로 운영 결정을 내리는 층

즉 F9는

**설명 가능한 진단 결과를 실제 운영 가능한 calibration 객체로 바꾸는 첫 단계**

이고,
F10/F11은 그 객체를 시험하고 평가하는 단계다.
