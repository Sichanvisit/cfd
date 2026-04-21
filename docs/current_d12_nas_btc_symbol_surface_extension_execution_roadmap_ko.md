# D12. NAS/BTC Symbol-Specific Pilot Surface Extension Execution Roadmap

## 목표

- XAU와 같은 3층 구조를 NAS/BTC에도 올린다.

## 실행 순서

### 1. NAS/BTC pilot mapping 추가

- static retained window catalog를 contract로 올린다.
- `ACTIVE_PILOT / REVIEW_PENDING`를 같이 surface한다.

### 2. NAS/BTC readonly surface 추가

- D10 common slot row를 upstream으로 사용한다.
- symbol-specific prefix로 readonly fields를 올린다.
- `pilot_window_match_v1`를 함께 surface한다.

### 3. NAS/BTC decomposition validation 추가

- dominance validation / dominance accuracy shadow를 join한다.
- `slot_alignment_state`
- `should_have_done_candidate`
- `over_veto / under_veto`
- `decomposition_error_type`
  를 심볼별로 읽게 한다.

### 4. runtime export 연결

- contract
- summary
- artifact paths
  를 detail payload에 추가한다.

### 5. 테스트

- pilot mapping contract/summary
- readonly surface row attach
- decomposition validation row attach
- runtime export presence
  를 잠근다.

## 검증 기준

- XAU 관련 기존 테스트를 깨지 않음
- NAS/BTC 신규 테스트 통과
- detail payload에 NAS/BTC contract + summary + artifact paths가 모두 보임
