# F11. candidate evaluation / rollback dashboard 실행 로드맵

## 1. 목적

F10 bounded apply 결과를 candidate 단위로 집계해,

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

중 하나로 candidate lifecycle을 판정하는 것이 F11의 목적이다.

---

## 2. 구현 순서

### S1. upstream apply session 정합

아래 upstream이 row에 없으면 attach helper로 다시 붙인다.

- `bounded_candidate_shadow_apply`
- F10 apply session catalog / row-level diff

완료 기준:

- 단독 실행으로도 before / after 비교 입력을 읽을 수 있음

### S2. before / after metric 집계

candidate 단위로 아래를 집계한다.

- `over_veto_rate_before / after`
- `under_veto_rate_before / after`
- `unverified_widening_before / after`
- `cross_symbol_drift_before / after`
- `same_symbol_cross_window_stability`
- `sample_coverage`

완료 기준:

- candidate별 운영 지표가 비교 가능한 형태로 정리됨

### S3. derived delta 계산

아래 delta를 만든다.

- `over_veto_delta_pct`
- `under_veto_delta_pct`
- `unverified_widening_delta_pct`
- `cross_symbol_drift_delta_pct`

완료 기준:

- "좋아졌다 / 나빠졌다"를 숫자로 판단 가능

### S4. outcome rule 적용

아래 outcome rule을 적용한다.

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

핵심 기준:

- over-veto 감소 여부
- under-veto 악화 여부
- harmful widening 존재 여부
- drift 허용 범위 내 여부
- sample/window 충분성

완료 기준:

- 각 candidate가 운영 상태 중 하나로 판정됨

### S5. summary dashboard 생성

summary:

- `active_apply_session_count`
- `candidate_outcome_count_summary`
- `promote_count`
- `keep_observing_count`
- `expire_count`
- `rollback_count`
- `symbol_apply_count_summary`
- `learning_key_apply_count_summary`
- `cross_symbol_warning_count`

완료 기준:

- 운영자가 전체 candidate 운영 상태를 한눈에 볼 수 있음

### S6. detailed candidate dashboard 생성

candidate별 상세 항목:

- candidate id
- apply session id
- apply scope
- affected rows
- before / after metrics
- delta metrics
- outcome
- rollback trigger hit 여부
- next review due time

완료 기준:

- 각 candidate의 운명을 세부적으로 설명 가능

### S7. runtime_status.detail.json export

detail payload에 아래를 올린다.

- `candidate_evaluation_dashboard_contract_v1`
- `candidate_evaluation_dashboard_summary_v1`
- `candidate_evaluation_dashboard_artifact_paths`

완료 기준:

- runtime detail에서 F11 계약/요약/artifact path를 바로 읽을 수 있음

### S8. 검증

단위 테스트 최소 항목:

- over-veto 감소 + harmful widening 없음 -> `PROMOTE`
- 개선은 있으나 sample 부족 -> `KEEP_OBSERVING`
- 유의미한 변화 없음 -> `EXPIRE_WITHOUT_PROMOTION`
- under-veto 증가 또는 drift 증가 -> `ROLLBACK`
- summary / artifact write
- runtime export

완료 기준:

- 테스트 통과
- `py_compile ok`

---

## 3. 상태 기준

- `READY`
  - candidate outcome이 일관되게 surface됨
- `HOLD`
  - sample/window 부족으로 `KEEP_OBSERVING` 비중이 높음
- `BLOCKED`
  - before / after 집계가 불안정하거나
  - outcome rule이 충돌함

---

## 4. 다음 단계 연결

F11이 끝나면 이후는 운영 단계다.

- `PROMOTE`된 candidate만 calibration patch 승격 후보
- `KEEP_OBSERVING`은 shadow 유지
- `EXPIRE_WITHOUT_PROMOTION`은 조용히 종료
- `ROLLBACK`은 즉시 격리 및 이력 보존

즉 F11은

**candidate를 실험 객체에서 운영 결론으로 바꾸는 최종 evaluation / governance 층**

이다.
