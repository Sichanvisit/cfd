# Current C4 Checkpoint Improvement Recovery Health Detailed Plan

## 목적

`C4 recovery / health`는 오케스트레이터를 더 크게 만드는 단계가 아니라,
이미 생성된 `system state / orchestrator tick / master board`를 읽어서
지금 상태가

- 정상 계속 운전인지
- 다음 tick 재시도가 맞는지
- 사람 개입이 필요한지

를 canonical하게 판정하는 얇은 상태 요약층이다.

## 입력

- `checkpoint_improvement_system_state_latest.json`
- `checkpoint_improvement_orchestrator_latest.json`
- `checkpoint_improvement_master_board_latest.json`

## 출력

- `checkpoint_improvement_recovery_health_latest.json`
- `checkpoint_improvement_recovery_health_latest.md`

## 핵심 판단 축

- `overall_status`
  - `GREEN`
  - `YELLOW`
  - `RED`
- `recovery_state`
  - `HEALTHY_CONTINUE`
  - `WAIT_FOR_PA7_REVIEW_BACKLOG`
  - `WAIT_FOR_PA8_LIVE_WINDOW`
  - `WAIT_FOR_APPROVAL_DECISIONS`
  - `WAIT_FOR_APPLY_BACKLOG_DRAIN`
  - `RETRY_ORCHESTRATOR_NEXT_TICK`
  - `REFRESH_STALE_ARTIFACTS`
  - `ESCALATE_OPERATOR_ACTION`
  - `SHUTDOWN_PENDING`

## v0 원칙

- backlog는 곧바로 장애로 보지 않는다
- `DEGRADED / WATCH_ERROR / stale artifact`는 재시도 권고로 본다
- `EMERGENCY`만 즉시 operator escalation로 본다
- 이 레이어는 apply를 수행하지 않는다
- 이 레이어는 restart를 직접 수행하지 않는다

## 다음 연결점

- orchestrator watch runner가 매 cycle 뒤에 health snapshot을 함께 생성한다
- `manage_cfd`는 이 runner를 별도 watch 프로세스로 유지한다
