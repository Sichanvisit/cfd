# D11-2. State Slot Position Lifecycle Policy 실행 로드맵

## 목적

- decomposition slot과 bridge bias를 실제 포지션 운영 posture로 번역하는 read-only lifecycle policy 층을 추가한다.

## 구현 범위

1. XAU는 기존 D11-1 bridge bias를 lifecycle policy로 변환
2. NAS/BTC는 D10 common slot surface에서 동일한 lifecycle posture를 파생
3. runtime detail + summary artifact 생성
4. execution/state25 직접 연결은 금지

## 핵심 작업

- `state_slot_position_lifecycle_policy_contract_v1` 추가
- lifecycle row builder 추가
- `runtime_status.detail.json` export 추가
- artifact 생성
- unit test 추가

## 예상 summary

- `state_slot_position_lifecycle_policy_summary_v1`

핵심 필드:
- `symbol_count`
- `surface_ready_count`
- `lifecycle_policy_state_count_summary`
- `policy_source_count_summary`
- `entry_policy_count_summary`
- `hold_policy_count_summary`
- `reduce_policy_count_summary`

## 통제 규칙

- lifecycle policy는 declarative read-only다
- lifecycle policy는 dominant_side를 바꾸지 않는다
- decomposition / bridge / lifecycle은 모두 execution과 분리한다
- lifecycle policy는 이후 bounded canary 이전의 마지막 설명층이다

## 완료 기준

- 세 심볼 모두 lifecycle policy를 공통 언어로 읽을 수 있다
- bias보다 더 실제적인 `entry / hold / add / reduce / exit` posture가 surface된다
- execution/state25는 여전히 불변이다

## 다음 단계와의 연결

- D11-2가 끝나면:
  - `state_slot -> execution_policy` read-only 변환이 완성된다
- 그다음에야:
  - bounded canary
  - 실제 lifecycle 연결
  을 검토할 수 있다

## 한 문장 결론

이 단계의 본질은 해석 슬롯을 곧바로 매매로 연결하는 것이 아니라, slot과 bias를 사람이 검토 가능한 position lifecycle posture로 번역해 마지막 read-only 행동층을 완성하는 것이다.
