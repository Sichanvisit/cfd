# S4. Dominance Resolver Shadow-Only 실행 로드맵

## 1. 목표

S4는 기존 S1/S2/S3를 바탕으로
`state_structure_dominance_profile_v1`를 read-only shadow layer로 추가하는 단계다.

핵심은

- local continuation discount
- would_override_caution
- dominant side/mode/caution summary

를 row/detail/artifact에 기록하는 것이다.

## 2. 구현 순서

### S4-1. contract/service 추가

- `state_structure_dominance_profile_v1` builder
- `state_structure_dominance_contract_v1`
- summary writer

### S4-2. row-level dominance shadow 계산

입력:

- S1 state strength flat fields
- S2 local structure flat fields
- S3 `consumer_veto_tier_v1`
- session bucket은 참고 context만 제공

출력:

- `dominance_shadow_dominant_side_v1`
- `dominance_shadow_dominant_mode_v1`
- `dominance_shadow_caution_level_v1`
- `dominance_shadow_gap_v1`
- `local_continuation_discount_v1`
- `would_override_caution_v1`
- `dominance_reason_summary_v1`

### S4-3. summary artifact 추가

- `state_structure_dominance_summary_v1`
- `state_structure_dominance_artifact_paths`
- shadow artifact:
  - `state_structure_dominance_summary_latest.json`
  - `state_structure_dominance_summary_latest.md`

### S4-4. trading_application 연결

순서:

1. S1 state strength
2. S2 local structure
3. S3 runtime read-only surface
4. S4 dominance shadow-only surface

detail payload export:

- `state_structure_dominance_contract_v1`
- `state_structure_dominance_summary_v1`
- `state_structure_dominance_artifact_paths`

### S4-5. 테스트 고정

최소 테스트:

- friction-only continuation -> `would_override_caution_v1 = true`
- boundary case -> `BOUNDARY`
- reversal override case -> `REVERSAL_RISK`, no discount
- runtime status export smoke
- artifact write smoke

## 3. 완료 기준

- 세 심볼 모두 dominance shadow row가 same contract로 surface
- local continuation discount와 caution override shadow field가 보임
- summary artifact가 정상 생성됨

## 4. 상태 기준

- `READY`
  - row/detail/artifact 모두 정상
- `HOLD`
  - 일부 row나 artifact freshness 흔들림
- `BLOCKED`
  - S1~S3 field 부족
  - dominance report 생성 실패
  - runtime payload 충돌
