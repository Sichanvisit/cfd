# Current C3 Checkpoint Improvement Orchestrator Loop Detailed Plan

## 목적

`C3 OrchestratorLoop`는 새 판단 엔진이 아니라, 이미 만든 아래 부품들을 한 tick으로 묶는 얇은 지휘자다.

- `light_cycle`
- `governance_cycle`
- `heavy_cycle`
- `Master Board`
- `reconcile placeholder`
- `Telegram approval bridge`

즉 `C3`의 목표는 `무한 루프를 크게 만드는 것`이 아니라, 테스트 가능한 `single tick orchestration`을 먼저 닫는 것이다.

## 이번 단계에서 하는 것

- `checkpoint_improvement_orchestrator.py` 추가
- `run_checkpoint_improvement_orchestrator_tick(...)`
- `CheckpointImprovementOrchestratorLoop.run_tick(...)`
- orchestrator report JSON/MD 출력

## 이번 단계에서 하지 않는 것

- `manage_cfd` 직접 연결
- 별도 worker restart supervisor
- thread/process health daemon
- 자동 recovery policy 확장

## tick 순서

한 tick의 canonical 순서는 아래로 고정한다.

1. `light_cycle`
2. event drain
3. backlog 재계산
4. `governance_cycle`
5. event drain
6. backlog 재계산
7. `heavy_cycle`
8. event drain
9. `master_board` 생성
10. `reconcile_cycle`
11. event drain
12. `master_board` 재생성

즉 board는 reconcile 전/후를 둘 다 본다.

## 왜 이런 순서인가

- `light_cycle`은 가장 빠른 최신화
- `governance_cycle`은 approval/apply backlog에 민감
- `heavy_cycle`은 가장 무겁지만 state는 계속 남긴다
- `reconcile_cycle`은 board를 읽고 움직여야 한다
- 최종 board는 reconcile 이후 상태를 반영해야 한다

## 출력 계약

### summary

- `contract_version`
- `generated_at`
- `trigger_state`
- `recommended_next_action`
- `phase_before`
- `phase_after`
- `total_drained_event_count`

### tick

- `light_trigger_state`
- `governance_trigger_state`
- `heavy_trigger_state`
- `reconcile_trigger_state`
- `approval_backlog_count`
- `apply_backlog_count`

### 세부 섹션

- `light_cycle`
- `governance_cycle`
- `heavy_cycle`
- `reconcile_cycle`
- `master_board_before_reconcile`
- `master_board_after_reconcile`
- `orchestrator_contract`

## orchestrator가 하지 말아야 하는 것

- Telegram API 직접 호출
- approval state 직접 수정
- apply 직접 집행
- 개별 cycle 내부 로직 중복 구현

즉 orchestrator는 `호출 순서와 event drain`만 책임진다.

## 오류 처리

개별 cycle은 자기 오류를 내부에서 처리하지만, orchestrator 레벨에서도 예상 밖 예외를 잡아야 한다.

예상 밖 예외가 나면:

- `SystemStateManager -> DEGRADED`
- `WatchError(cycle_name=orchestrator)` 발행
- 필요하면 `SystemPhaseChanged` 발행
- orchestrator report는 `WATCH_ERROR`로 종료

## 테스트 기준

### 1. 순서 검증

- light -> governance -> heavy -> board -> reconcile -> board 순서 보장

### 2. governance event 연결

- governance에서 `GovernanceActionNeeded`가 나오면
- bridge가 pending group으로 연결
- final board/orchestrator tick에 backlog가 반영

### 3. 예외 처리

- 예기치 않은 예외 시 orchestrator가 `DEGRADED`로 떨어짐

### 4. instance 사용성

- class instance 기반 `run_tick()`도 함수 wrapper와 동일하게 동작

## 완료 기준

`C3` 완료는 아래를 의미한다.

- 단일 tick 기준으로 cycle orchestration이 실제 코드로 존재한다
- event drain과 board/reconcile 갱신이 하나의 흐름으로 묶인다
- 이후 `manage_cfd` 연결 전에도 테스트로 오케스트레이션 순서를 검증할 수 있다

한 줄로 정리하면,

`C3 OrchestratorLoop`는 반장 전체를 완성하는 단계가 아니라, 이미 만든 부품들을 한 번의 운영 tick으로 질서 있게 엮는 첫 지휘자 단계다.
