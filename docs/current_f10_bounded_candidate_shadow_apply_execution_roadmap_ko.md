# F10. bounded candidate shadow apply 실행 로드맵

## 1. 목적

F9 candidate를

- 바로 기본값에 반영하지 않고
- 아주 좁은 apply scope에서
- shadow-only로 시험하고
- before / after diff를 일관되게 남기는 것

이 F10의 목적이다.

---

## 2. 구현 순서

### S1. upstream candidate catalog 정합

아래 upstream이 없으면 attach helper로 다시 붙인다.

- `bounded_calibration_candidate`
- F9 candidate catalog / summary

완료 기준:

- 단독 실행으로도 active/proposed candidate를 읽을 수 있음

### S2. apply session object 생성

candidate와 별도로 apply session을 만든다.

핵심 필드:

- `apply_session_id`
- `candidate_id`
- `apply_mode`
- `scope`
- `started_at`
- `scheduled_review_at`
- `status`

완료 기준:

- candidate와 실험 세션이 분리되어 추적 가능

### S3. scope match 판단

각 row가 apply scope에 포함되는지 판정한다.

scope 최소 항목:

- symbol
- learning key
- state bucket
- validation window
- duration

완료 기준:

- scope 밖 row에는 영향이 없고
- scope 안 row만 before/after 계산에 들어감

### S4. bounded patch 적용

candidate patch를 shadow-only로 적용한다.

핵심 규칙:

- `max_allowed_delta` 초과 금지
- safety가 낮으면 delta 추가 축소
- 기본 apply mode는 `SHADOW_ONLY`

완료 기준:

- live result는 유지한 채 shadow 재계산이 가능

### S5. conflict rule 적용

겹치는 scope에서 반대 방향 효과를 가진 candidate를 감지한다.

규칙:

- same symbol
- same state bucket
- same validation window

에서 반대 효과면 conflict

처리:

- higher priority만 유지
- 나머지는 `HOLD`

완료 기준:

- 혼합 실험이 아니라 분리된 candidate 실험이 됨

### S6. drift memory 적용

`symbol × learning_key` 기준 cumulative shift를 추적한다.

추가 규칙:

- shared/common parameter는 global drift도 추적
- drift limit 초과 시 추가 relax/tighten 차단

완료 기준:

- bounded apply가 조용한 장기 drift로 바뀌지 않음

### S7. row-level before / after surface

아래 flat field를 row에 올린다.

- `bounded_apply_session_id_v1`
- `bounded_apply_candidate_id_v1`
- `bounded_apply_mode_v1`
- `bounded_apply_scope_match_v1`
- `flow_support_state_before_v1`
- `flow_support_state_after_v1`
- `aggregate_conviction_before_v1`
- `aggregate_conviction_after_v1`
- `flow_persistence_before_v1`
- `flow_persistence_after_v1`
- `flow_state_change_type_v1`
- `candidate_effect_direction_v1`
- `bounded_apply_conflict_flag_v1`
- `bounded_apply_drift_guard_state_v1`

완료 기준:

- row 하나만 봐도 apply 영향과 차이를 설명 가능

### S8. apply session summary / artifact

summary:

- `active_apply_session_count`
- `apply_mode_count_summary`
- `apply_status_count_summary`
- `apply_symbol_count_summary`
- `apply_learning_key_count_summary`
- `conflict_session_count`
- `drift_guard_block_count`

artifact:

- apply session catalog JSON
- apply session review Markdown

완료 기준:

- 운영자가 현재 어떤 bounded experiment가 떠 있는지 바로 볼 수 있음

### S9. runtime_status.detail.json export

detail payload에 아래를 올린다.

- `bounded_candidate_shadow_apply_contract_v1`
- `bounded_candidate_shadow_apply_summary_v1`
- `bounded_candidate_shadow_apply_artifact_paths`

완료 기준:

- runtime detail에서 F10 계약/요약/artifact path를 바로 읽을 수 있음

### S10. 검증

단위 테스트 최소 항목:

- scope 밖 row는 변화 없음
- delta는 `max_allowed_delta`를 넘지 않음
- conflict candidate는 동시에 `ACTIVE`가 되지 않음
- drift limit 초과 시 `BLOCKED`
- before / after diff surface 정상
- artifact write / runtime export

완료 기준:

- 테스트 통과
- `py_compile ok`

---

## 3. 상태 기준

- `READY`
  - apply session과 row diff가 일관되게 surface됨
- `HOLD`
  - candidate conflict 또는 sample 부족으로 관찰이 더 필요
- `BLOCKED`
  - drift limit, immutable 침범, invalid patch로 apply가 막힘

---

## 4. 다음 단계 연결

F10이 끝나면 다음은 F11이다.

F11은 F10의 before / after 결과를 candidate 단위로 집계해서,

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

을 결정하는 evaluation / governance 층이다.
