# D8. XAU should-have-done / dominance 검증 강화 실행 로드맵

## 목표

XAU decomposition surface를 should-have-done / canonical / dominance accuracy와 다시 묶어
XAU 전용 검증 summary를 만든다.

## 작업 순서

### 1. validation contract 추가

- `xau_decomposition_validation_contract_v1`
- XAU alignment state enum 고정
- read-only / dominance 보호 규칙 명시

### 2. upstream join helper 추가

- `xau_readonly_surface`
- `dominance_validation`
- `dominance_accuracy_shadow`

가 없으면 내부에서 보강 attach

### 3. row-level validation builder 추가

- XAU row에서
  - slot alignment
  - should-have-done candidate
  - over/under veto
  - error type
  를 surface
- 비-XAU row는 `NOT_APPLICABLE`

### 4. summary / artifact 추가

- `xau_decomposition_validation_summary_v1`
- `xau_decomposition_validation_latest.json`
- `xau_decomposition_validation_latest.md`

### 5. runtime detail export 연결

- contract / summary / artifact path를 detail payload에 추가

### 6. 검증

- 단위 테스트
- runtime export 테스트
- 현재 workspace `latest_signal_by_symbol` 기준 스모크

## 완료 후 기대 상태

- XAU decomposition이 실제로 어떤 dominance 문제를 줄이는 쪽인지 수치로 읽을 수 있다.
- D9 공용화 전에 XAU pilot 품질을 teacher/validation 관점에서 판단할 수 있다.
