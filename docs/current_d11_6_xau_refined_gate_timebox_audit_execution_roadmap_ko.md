# D11-6. XAU Refined Gate Timebox Audit 실행 로드맵

## 목표

XAU current row가 refined gate를 못 통과하는 이유를 `row-level + artifact`로 즉시 읽게 만든다.

## 단계

### 1. persisted/effective 비교 계약 추가

- persisted gate 필드와 effective recomputation 필드를 동시에 surface한다
- `saved_vs_effective_state`를 별도 축으로 둔다

### 2. effective recomputation 체인 고정

- downstream surface를 strip한 뒤 아래 순서로 다시 붙인다
  - `xau_readonly_surface`
  - `execution bridge`
  - `lifecycle policy`
  - `shadow audit`
  - `bounded canary`

### 3. gate failure stage 판정

- `alignment`
- `pilot match`
- `ambiguity`
- `texture`
- `entry policy`
- `hold policy`
- `residual canary scope`

순서로 1차 driver를 판정한다.

### 4. runtime payload export

- contract
- summary
- artifact path

를 detail payload에 추가한다.

### 5. shadow artifact 생성

- `xau_refined_gate_timebox_audit_latest.json`
- `xau_refined_gate_timebox_audit_latest.md`

### 6. 검증

- 단위 테스트
  - persisted fields missing + effective pilot mismatch
  - artifact write
- runtime export 테스트

## 완료 기준

- XAU current row에 대해
  - persisted vs effective 비교가 보이고
  - failure stage와 primary driver가 보이고
  - artifact로 바로 확인 가능하다

## 기대 결과

현재 XAU row가 refined gate를 못 통과하는 이유를

- `payload stale`
- `pilot match fail`
- `ambiguity`
- `texture drift`
- `entry/hold posture`

중 무엇 때문인지 즉시 구분할 수 있게 된다.
