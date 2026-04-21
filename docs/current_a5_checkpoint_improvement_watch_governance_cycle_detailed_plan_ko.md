# Current A5 Checkpoint Improvement Watch Governance Cycle Detailed Plan

## 목적

이 문서는 `A5. checkpoint_improvement_watch governance_cycle`을
실제 구현 가능한 수준으로 좁혀서 정리한 상세 계획이다.

이번 단계의 핵심은 승인이나 적용을 직접 하는 것이 아니다.

이미 존재하는 PA8 canary 상태 산출물을 읽어서,
`rollback review`나 `closeout review` 같은
`승인 필요 후보(candidate)`를 감지하고
그 결과를 event와 state에 반영하는 데 있다.

즉 A5는

- governance due/skip 판단
- PA8 canary refresh board 읽기
- symbol live 상태 동기화
- `GovernanceActionNeeded` 이벤트 발행

까지만 담당하고,
실제 승인/적용은 이후 B-track의 `ApprovalLoop / ApplyExecutor`에 넘긴다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)

---

## 이번 단계의 목표

`governance_cycle`이 아래 흐름을 실제로 수행하게 만든다.

1. `A3` 규칙으로 governance due/skip을 판단한다
2. 최신 PA8 canary refresh board를 읽는다
3. board의 symbol 상태를 `SystemStateManager`에 동기화한다
4. rollback/closeout/activation review 후보를 좁게 식별한다
5. `GovernanceActionNeeded` 이벤트를 발행한다
6. `governance_last_run`을 반영한다

이번 단계는 `candidate generator`까지만 닫는다.

---

## 왜 activation보다 rollback/closeout에 먼저 맞추나

현재 구조에서는 PA8 canary가 이미 활성 상태인 심볼이 존재한다.
반면 activation 승인 흐름은 B-track이 아직 없어서
실제 승인 상태기계와 apply executor가 완성되기 전까지는
자동으로 이어붙이면 경계가 흐려질 수 있다.

따라서 A5의 기본 타깃은 아래다.

- `ROLLBACK_REQUIRED` -> `CANARY_ROLLBACK_REVIEW`
- `READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW` -> `CANARY_CLOSEOUT_REVIEW`

`activation_apply_state`가 hold 계열인 경우는
보조적으로 `CANARY_ACTIVATION_REVIEW` 후보를 만들 수 있게 두되,
이후 승인 트랙이 완성되기 전까지는 candidate 수준으로만 다룬다.

---

## 이번 단계에서 새로 만드는 것

### 1. governance cycle service 확장

- [checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_watch.py)

추가 public API:

- `run_checkpoint_improvement_watch_governance_cycle()`

### 2. governance cycle 테스트

- [test_checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/tests/unit/test_checkpoint_improvement_watch.py)

핵심 검증:

- active canary가 없으면 skip
- rollback candidate가 있으면 event 발행
- 후보가 없어도 governance run은 기록
- board loader 오류 시 degraded + watch error

### 3. A5 상세 문서

- 이 문서 자체

---

## 이번 단계에서 재사용하는 것

### PA8 canary refresh board

- [path_checkpoint_pa8_canary_refresh.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_canary_refresh.py)

이 산출물은 이미 symbol별

- `activation_apply_state`
- `first_window_status`
- `closeout_state`
- `live_observation_ready`
- `recommended_next_action`

를 제공한다.

이번 단계에서는 이 board를 governance 입력으로 재사용한다.

### A1 상태 관리자

- [system_state_manager.py](/Users/bhs33/Desktop/project/cfd/backend/services/system_state_manager.py)

여기서는 symbol별

- `canary_active`
- `live_window_ready`

상태를 board 결과로 다시 맞춘다.

### A2 이벤트 버스

- [event_bus.py](/Users/bhs33/Desktop/project/cfd/backend/services/event_bus.py)

이번 단계에서는 아래 이벤트를 사용한다.

- `GovernanceActionNeeded`
- `WatchError`
- `SystemPhaseChanged`

### A3 governance 판단 규약

- [checkpoint_improvement_cycle_definition.py](/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_cycle_definition.py)

이번 단계에서는
`row_delta`, `approval_backlog_count`, `active_pa8_symbol_count`
기준으로 governance due 여부를 계산한다.

---

## 최소 동작 규칙

### 1. due가 아니면 아무 것도 하지 않는다

- `no_active_canary_or_backlog`
- `cooldown_active`
- `waiting_for_row_delta_or_interval`

같은 skip reason이면
candidate 생성도, event 발행도 하지 않는다.

### 2. due면 board를 읽는다

board는 기본적으로 최신
`checkpoint_pa8_canary_refresh_board_latest.json`
을 읽는다.

테스트에서는 payload 주입을 허용해서 무거운 의존성을 피한다.

### 3. board row를 state로 동기화한다

각 row의

- `activation_apply_state == ACTIVE_ACTION_ONLY_CANARY`
- `live_observation_ready`

를 읽어서
`SystemStateManager.pa8_symbols`에 반영한다.

즉 governance는 판단만 하는 것이 아니라
symbol canary 상태를 상위 상태판에 반영하는 역할도 맡는다.

### 4. candidate는 매우 좁게 만든다

현재 v0 후보 생성 규칙은 아래 정도면 충분하다.

- `closeout_state == ROLLBACK_REQUIRED`
  - `CANARY_ROLLBACK_REVIEW`
- `closeout_state == READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW`
  - `CANARY_CLOSEOUT_REVIEW`
- `activation_apply_state in HOLD_CANARY_ACTIVATION_APPLY / HELD_ACTION_ONLY_CANARY`
  - `CANARY_ACTIVATION_REVIEW`

그 외 상태는 그냥 관찰만 하고 candidate를 만들지 않는다.

### 5. apply는 하지 않는다

이번 단계에서 governance는 절대 실제 apply를 하지 않는다.

역할은 여기까지다.

- candidate 감지
- event 발행
- state 동기화
- governance run 기록

---

## 권장 candidate payload

`GovernanceActionNeeded` payload는 최소한 아래 필드를 가지면 충분하다.

- `review_type`
- `governance_action`
- `scope_key`
- `symbol`
- `activation_apply_state`
- `closeout_state`
- `first_window_status`
- `live_observation_ready`
- `observed_window_row_count`
- `active_trigger_count`
- `recommended_next_action`

이 단계에서는 `approval_id`까지 강제하지 않는다.
그건 B-track에서 실제 승인 흐름이 붙을 때 강화하는 편이 맞다.

---

## 실패 처리

### board loader 예외

board loader가 예외를 던지면
이건 governance 입력을 만들 수 없는 상태이므로

- `DEGRADED` 전이
- `WatchError`
- 필요 시 `SystemPhaseChanged`

까지는 남기는 편이 맞다.

### board가 비어 있는 경우

board는 읽혔지만 후보가 없는 경우는 오류가 아니다.

- `GOVERNANCE_NO_ACTION_NEEDED`
- `candidate_count = 0`

로 정상 종료하면 된다.

---

## 완료 조건

- governance due/skip 판단이 동작한다
- PA8 board를 읽어 symbol state를 동기화한다
- rollback/closeout candidate를 event로 발행한다
- `governance_last_run`이 기록된다
- unit test가 통과한다

---

## 다음 단계 연결

A5가 닫히면 다음 순서는 아래가 가장 자연스럽다.

1. 병렬로 `B1/B2/B3`
2. 그 다음 `A6 heavy_cycle`
3. 이후 `C1 Master Board`

즉 A5는
`watch가 canary 상태를 보고 승인 필요 후보를 올리는 첫 단계`
라고 보면 된다.
