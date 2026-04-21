# R3 Should-Have-Done 상세 계획

## 1. 목적

R3의 목적은 운영자가 보는 차트 장면과 시스템이 실제로 낸 출력 사이의 차이를
`should-have-done` 후보로 축적할 수 있게 만드는 것이다.

지금 단계에서는 실행을 바꾸지 않는다.
오직 아래 질문에 답할 수 있게 만든다.

- 이 장면에서 시스템이 실제로 무엇을 했는가
- 구조상 무엇이 더 맞는 후보였는가
- 그 후보를 어떤 confidence로 남길 것인가

## 2. 왜 지금 R3가 필요한가

R2에서 최소 annotation 언어는 고정됐다.

- `direction_annotation`
- `continuation_annotation`
- `continuation_phase_v1`
- `session_bucket_v1`
- `annotation_confidence_v1`

이제 부족한 것은 이 언어로 실제 정답 후보를 쌓는 축이다.

운영자 스크린샷 메모만으로는 느리고,
자동 hindsight만으로는 오염될 수 있다.

그래서 R3는 `자동 후보 + 운영자 확인`이 가능한 read-only 축을 먼저 만든다.

## 3. R3 v1 범위

### 포함

- should-have-done contract
- 자동 후보 summary
- runtime/detail export
- shadow auto artifact 생성

### 제외

- execution/state25 직접 반영
- manual review workflow 완성
- canonical surface 통합
- phase accuracy 집계

## 4. v1 contract

R3 v1은 아래 필드를 고정한다.

- `expected_direction`
- `expected_continuation`
- `expected_phase_v1`
- `expected_surface`
- `annotation_confidence_v1`
- `candidate_source_v1`
- `operator_note`

## 5. 자동 후보 생성 원칙

### 5-1. surface vs final action mismatch

현재 row에서 overlay 방향이 분명한데 최종 action이 그 방향을 따르지 않으면
`AUTO_SURFACE_EXECUTION_MISMATCH` 후보를 만든다.

예:

- row는 `BUY_WATCH`
- final은 `SELL`

이 경우 expected는 `UP / CONTINUING / CONTINUATION / BUY_WATCH`가 된다.

### 5-2. promotion review candidate

trace에 `promoted_action_side`가 있는데 final이 그 방향으로 가지 않으면
`AUTO_PROMOTION_REVIEW` 후보를 만든다.

예:

- promoted = `BUY`
- final = `SELL`

이 경우 expected는 `UP / CONTINUING / CONTINUATION / BUY_WATCH`가 된다.

## 6. confidence 원칙

- `AUTO_HIGH`
  - overlay score가 높거나
  - promotion 억제 이유가 명확한 경우
- `AUTO_MEDIUM`
  - 방향 후보는 있으나 강도가 중간인 경우
- `AUTO_LOW`
  - 후보는 있으나 score가 약한 경우

수동 annotation은 아직 이 단계에서 직접 생성하지 않지만,
contract는 `operator_note`와 `MANUAL_HIGH`를 수용하게 열어둔다.

## 7. 상태 기준

### READY

- contract가 고정됨
- 자동 후보 summary가 생성됨
- runtime/detail에서 summary와 artifact를 읽을 수 있음

### HOLD

- contract는 있으나 자동 후보가 아직 없음
- 또는 후보 수가 매우 적어 관찰만 가능한 상태

### BLOCKED

- candidate summary 생성이 실패함
- R2 annotation contract와 필드가 어긋남

## 8. 산출물

- `should_have_done_contract_v1`
- `should_have_done_summary_v1`
- `should_have_done_artifact_paths`
- `data/analysis/shadow_auto/should_have_done_candidate_summary_latest.json`
- `data/analysis/shadow_auto/should_have_done_candidate_summary_latest.md`

## 9. R3가 닫혔다는 뜻

R3가 닫혔다는 것은 정답 후보를 완전히 자동 학습에 넣는다는 뜻이 아니다.

정확한 의미는 이렇다.

- 시스템이 스스로 review-worthy 장면을 후보로 남길 수 있다
- 운영자는 그 후보를 보고 수동 정답을 얹을 수 있다
- 이후 R4 canonical surface와 R5 annotation accuracy가 붙을 바닥이 생긴다
