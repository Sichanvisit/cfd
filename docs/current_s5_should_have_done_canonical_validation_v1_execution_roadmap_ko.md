# S5. Should-Have-Done / Canonical Surface 결합 검증 실행 로드맵

## 1. 목표

S5는 S4 dominance shadow를
should-have-done review 축과 canonical runtime/execution 축에 연결해
실제 검증 가능한 dominance validation surface를 만드는 단계다.

## 2. 구현 순서

### S5-1. contract/service 추가

- `dominance_validation_contract_v1`
- row builder:
  - `build_dominance_validation_row_v1(...)`
- attach helper:
  - `attach_dominance_validation_fields_v1(...)`
- summary writer

### S5-2. expected dominance 계산

- canonical direction -> expected side
- canonical phase + consumer veto tier -> expected mode
- expected caution level 계산

### S5-3. error type / evidence 매핑

- `dominance_error_type_v1`
- `overweighted_caution_fields_v1`
- `undervalued_continuation_evidence_v1`
- `dominance_should_have_done_candidate_v1`

### S5-4. trading_application 연결

순서:

1. S4 dominance shadow-only
2. S5 dominance validation

detail payload export:

- `dominance_validation_contract_v1`
- `dominance_validation_summary_v1`
- `dominance_validation_artifact_paths`

### S5-5. 테스트 고정

최소 테스트:

- continuation expected but boundary actual -> `CONTINUATION_UNDERPROMOTED`
- friction continuation expected but reversal actual -> `FRICTION_MISREAD_AS_REVERSAL`
- reversal expected but continuation actual -> `TRUE_REVERSAL_MISSED`
- runtime status export smoke
- artifact write smoke

## 3. 완료 기준

- 세 심볼 모두 dominance validation contract로 읽힘
- should-have-done/canonical divergence가 error type으로 보임
- summary artifact가 정상 생성됨

## 4. 상태 기준

- `READY`
  - row/detail/artifact 정상
- `HOLD`
  - 일부 row만 validation surface
- `BLOCKED`
  - S4/canonical field 부족
  - runtime payload 충돌
