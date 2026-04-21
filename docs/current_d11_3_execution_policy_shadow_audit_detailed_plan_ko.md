# D11-3. Execution Policy Shadow Audit 상세 계획

## 목적

- D11-2 lifecycle policy가 실제로 slot/stage/texture/ambiguity와 일관되게 번역됐는지 shadow-only로 검증한다.

## 핵심 질문

- `EXTENSION`인데 entry가 너무 공격적으로 번역되진 않았는가?
- `INITIATION`인데 reduce가 너무 강하게 번역되진 않았는가?
- `ACCEPTANCE + CLEAN`인데 hold가 과하게 약하게 번역되진 않았는가?

## 예상 row-level field

- `execution_policy_shadow_audit_profile_v1`
- `lifecycle_policy_alignment_state_v1`
- `entry_delay_conflict_flag_v1`
- `hold_support_alignment_v1`
- `reduce_exit_pressure_alignment_v1`
- `execution_policy_shadow_error_type_v1`
- `execution_policy_shadow_reason_summary_v1`

## 핵심 원칙

- shadow audit은 진단층이다
- execution/state25를 바꾸지 않는다
- `REVIEW_PENDING`은 실패가 아니라 보류로 분리한다

## 완료 기준

- 세 심볼 모두 lifecycle policy shadow audit row가 surface된다
- alignment/error typing이 summary로 집계된다
