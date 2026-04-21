# Current Pre-Orchestration Foundation Execution Roadmap

## 목적

이 문서는 `checkpoint_improvement_watch`와 `OrchestratorLoop`를 얹기 전에,
무엇을 어떤 순서로 먼저 깔아야 하는지를 `실전 착수 기준`으로 다시 정리한
v2 실행 로드맵이다.

핵심 메시지는 하나다.

`기반 공사를 완벽하게 다 끝낸 뒤 watch를 만드는 것`이 아니라,
`watch가 가능한 한 빨리 첫 tick을 돌 수 있게 최소 기반을 먼저 깔고,
승인/적용 기반은 병렬로 붙인 뒤, 운영 중에 보드와 reconcile을 안정화한다`

를 목표로 한다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)
- [current_a2_event_bus_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a2_event_bus_v0_detailed_plan_ko.md)
- [current_a3_cycle_definition_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a3_cycle_definition_v0_detailed_plan_ko.md)
- [current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md)
- [current_a5_checkpoint_improvement_watch_governance_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a5_checkpoint_improvement_watch_governance_cycle_detailed_plan_ko.md)
- [current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md)
- [current_b1_telegram_state_store_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b1_telegram_state_store_detailed_plan_ko.md)
- [current_b2_approval_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b2_approval_loop_detailed_plan_ko.md)
- [current_b3_apply_executor_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b3_apply_executor_detailed_plan_ko.md)
- [current_b4_telegram_approval_bridge_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b4_telegram_approval_bridge_detailed_plan_ko.md)
- [current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md)
- [current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md)
- [current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md)
- [current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md)
- [current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md)
- [current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)

권장 읽기 흐름은 아래와 같다.

1. 전체 시스템의 현재 위치와 blocker는 [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)에서 먼저 본다.
2. 그 다음 이 문서에서 `Track A / B / C` 기반 공사 순서를 확인한다.
3. 실제 구현은 `A1 ~ C5` 개별 상세 문서로 내려간다.

---

## 한 줄 요약

v2 기준의 시작 순서는 아래처럼 읽는 게 가장 맞다.

```text
Track A. watch 최소 기동
  A1. SystemStateManager v0
  A2. EventBus v0
  A3. cycle definition
  A4. checkpoint_improvement_watch light_cycle first tick
  A5. governance_cycle
  A6. heavy_cycle

Track B. 승인/적용 기반 병렬 구축
  B1. TelegramStateStore contract 정렬
  B2. ApprovalLoop
  B3. ApplyExecutor
  B4. Telegram approval bridge

Track C. 합류 후 안정화
  C1. Master Board
  C2. reconcile placeholder + 운영 중 rule 추가
  C3. OrchestratorLoop
  C4. recovery / health
  C5. hard contract freeze
```

즉 `PF0 -> PF8 직렬 완료 후 watch`가 아니라,
`A/B 병렬 -> C 합류` 구조로 읽어야 한다.

---

## 왜 v2로 재정렬하는가

기존 PF형 순서는 설계상 깔끔했지만,
실전에서는 아래 위험이 있었다.

- 기반 공사를 너무 오래 하다가 `checkpoint_improvement_watch` 첫 tick이 늦어진다
- `PA8` live first-window가 계속 seed/reference 단계에 머문다
- `Master Board`와 `Reconcile`을 실제 데이터 없이 먼저 만들게 된다
- `PA8 Governance Contract`를 별도 단계로 두면서, 이미 있는 activation/closeout 판단 로직과 승인/적용 축이 분리되어 읽힌다

v2는 이 문제를 피하기 위해,
`없으면 watch가 시작 불가한 것`과 `있으면 승인/적용이 붙는 것`,
`운영하면서 다듬으면 되는 것`을 다시 나눴다.

---

## Track A. watch 최소 기동

이 트랙은 `watch가 첫 tick을 돌기 위해 반드시 필요한 최소 기반`이다.

### A1. SystemStateManager v0

#### 목적

`checkpoint_improvement_watch`가 참조하고 갱신할 상위 상태 진실 소스를 만든다.

#### v0에서 꼭 있어야 하는 것

- `phase`
  - `STARTING / RUNNING / DEGRADED / EMERGENCY / SHUTDOWN`
- `last_row_ts`
- `row_count_since_boot`
- `light_last_run`
- `heavy_last_run`
- `governance_last_run`
- `pa8_symbols`
  - `canary_active`
  - `live_window_ready`
- `telegram_healthy`
- `last_error`
- `threading.Lock`
- JSON snapshot load/save

#### v0에서 아직 미루는 것

- 세부 `sa_state`
- 세부 `improvement_state`
- 복잡한 optimistic locking
- 고급 transition validator

#### 중요한 경계

- `SystemStateManager`는 상위 운영 상태의 진실 소스다
- `TelegramStateStore`는 하위 승인/메시지/offset 저장소다
- Telegram 관련 영속 정보는 하위 저장소에 남기되,
  상위 phase 변화나 요약 상태 반영은 항상 `SystemStateManager.transition()`을 거쳐 올린다

#### 완료 조건

- 최소 phase 전이가 작동한다
- `pa8_symbols` 상태를 읽고 쓸 수 있다
- `last_row_ts`가 갱신된다
- state snapshot을 파일 기준으로 dump/load할 수 있다

세부 기준은 [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)를 따른다.

---

### A2. EventBus v0

#### 목적

worker 간 직접 import와 강한 결합을 피하기 위한 최소 이벤트 중계층을 둔다.

#### v0에서 꼭 있어야 하는 것

- `publish`
- `subscribe`
- `drain`
- handler 오류 격리

#### v0에서 먼저 잠글 이벤트

1. `LightRefreshCompleted`
2. `GovernanceActionNeeded`
3. `ApprovalReceived`
4. `SystemPhaseChanged`
5. `WatchError`

#### 중요한 원칙

- bus에는 `발생 사실(event)`만 태운다
- 상태를 바꾸는 직접 명령(command)은 숨기지 않는다
- 예를 들어 `CanaryActivationReviewNeeded`는 event가 될 수 있지만,
  실제 activation apply는 `ApplyExecutor` 명시 호출이어야 한다

#### 완료 조건

- publish/subscribe/drain이 동작한다
- handler 하나 실패해도 다른 handler는 계속 돌 수 있다
- v0 이벤트 5개 타입이 상수로 정리된다

세부 기준은 [current_a2_event_bus_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a2_event_bus_v0_detailed_plan_ko.md)를 따른다.

---

### A3. cycle definition

#### 목적

watch가 어떤 cycle을 언제 돌리고 언제 건너뛰는지,
실행 규칙을 먼저 잠근다.

#### 정의할 cycle

- `light_cycle`
- `heavy_cycle`
- `governance_cycle`
- `reconcile_cycle`

#### v0에서 꼭 적어야 하는 것

- 주기 기준
- row delta 기준
- lock/throttle 기준
- skip 조건
- 각 cycle의 책임 산출물

#### 권장 v0 해석

- `light_cycle`
  - 최근 row 변화 감지
  - fast refresh 호출
  - state update
- `governance_cycle`
  - PA8 canary 상태 확인
  - approval-needed candidate 생성
- `heavy_cycle`
  - PA7/SA heavy review
  - 초기엔 늦게 붙여도 된다
- `reconcile_cycle`
  - 초기엔 자리만 두고 비워둘 수 있다

#### 완료 조건

- 네 cycle의 역할과 주기, skip 조건이 문서 기준으로 고정된다

세부 기준은 [current_a3_cycle_definition_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a3_cycle_definition_v0_detailed_plan_ko.md)를 따른다.

---

### A4. checkpoint_improvement_watch light_cycle first tick

#### 목적

기반 공사가 완벽하지 않아도, watch가 실제 데이터를 보며 첫 tick을 돌게 한다.

#### 해야 하는 일

- row delta 감지
- fast refresh 호출
- `SystemStateManager` 갱신
- `LightRefreshCompleted` 발행

#### 이 단계에서 아직 안 해도 되는 것

- Telegram 승인 처리
- heavy review
- closeout apply
- reconcile rule 완성

#### 완료 조건

- 첫 tick이 돌고 artifact가 갱신된다
- state에 `light_last_run`과 `last_row_ts`가 반영된다

---

### A5. governance_cycle

#### 목적

watch가 PA8 bounded canary를 관찰하고
`승인 필요 / 계속 관찰 / 아직 조건 미달`을 구분하게 만든다.

#### 해야 하는 일

- PA8 canary refresh board 확인
- activation/rollback/closeout 필요 상황 감지
- candidate를 event로 발행
- 아직 승인 기반이 없으면 log-only로 남길 수 있게 함

#### 완료 조건

- watch가 `approval-needed candidate generator`로 동작한다
- apply를 직접 하지 않는다

---

### A6. heavy_cycle

#### 목적

watch가 무거운 PA7/SA review도 주기적으로 조율하게 만든다.

#### 해야 하는 일

- PA7 processor 호출
- PA78 review packet 호출
- scene disagreement / preview 호출

#### skip 조건 예시

- hot path degraded
- 이전 heavy run 아직 진행 중
- recent sample floor 미달

#### 완료 조건

- heavy review가 hot path와 분리되어 주기적으로 실행된다

---

## Track B. 승인/적용 기반 병렬 구축

이 트랙은 `watch가 이미 돌고 있는 동안` 병렬로 붙일 수 있는 승인/적용 인프라다.

### B1. TelegramStateStore contract 정렬

#### 목적

다른 스레드에서 Telegram 구현을 맡더라도,
우리 쪽에서 읽고 의존할 저장 계약을 먼저 맞춘다.

#### 최소 계약

- `check_groups`
- `check_events`
- `check_actions`
- `telegram_messages`
- `poller_offsets`

#### 중요한 관계

- TelegramStateStore는 approval/offset/message의 하위 저장소다
- 상위 운영 상태 반영은 `SystemStateManager`가 맡는다

#### 완료 조건

- `ApprovalLoop`와 `ApplyExecutor`가 의존할 저장 shape가 고정된다

---

### B2. ApprovalLoop

#### 목적

pending approval을 승인 상태기계로 바꾼다.

#### v0 지원 상태

- `pending`
- `approved`
- `held`
- `rejected`
- `expired`
- `applied`

#### v0 지원 review type

- `CANARY_ACTIVATION_REVIEW`
- `CANARY_ROLLBACK_REVIEW`
- `CANARY_CLOSEOUT_REVIEW`

#### 최소 요구사항

- allowed user 검증
- callback idempotency
- deadline 만료
- 전이 이력 기록

#### 완료 조건

- pending에서 approved/held/rejected/expired로 전이된다
- 동일 callback 중복 적용이 막힌다

---

### B3. ApplyExecutor

#### 목적

승인된 bounded action-only 변경을 실제 apply하는 집행기를 둔다.

#### v0 범위

- activation apply
- rollback apply
- closeout apply
- 동일 job 중복 apply 차단

#### 완료 조건

- approval 없는 apply를 거부한다
- activation/rollback/closeout apply 결과를 기록한다

---

### B4. Telegram approval bridge

#### 목적

governance candidate와 approval loop를 실제 승인 흐름으로 이어준다.

#### 해야 하는 일

- approval-needed event -> Telegram review card
- Telegram callback -> ApprovalLoop
- approval 결과 -> ApplyExecutor

#### 여기서 흡수되는 것

기존 문서에서 별도 단계처럼 보였던 `PA8 Governance Contract`는
실전 구현에선 `ApprovalLoop + ApplyExecutor`에 흡수하는 게 맞다.

즉 별도 대단한 새 판단 로직이 필요한 게 아니라,
이미 있는 activation/rollback/closeout 판단을
승인/적용 lifecycle에 묶는 것이 핵심이다.

#### 완료 조건

- approval card가 생성되고 승인 결과가 apply까지 이어진다

---

## Track C. 합류 후 안정화

이 트랙은 watch와 approval/apply가 둘 다 실제로 돌기 시작한 뒤에 붙인다.

### C1. Master Board

#### 목적

실제 운영 상태를 한눈에 보는 canonical board를 만든다.

#### 왜 뒤로 미루는가

- watch 첫 tick 전에는 데이터가 비어 있다
- approval/apply가 붙기 전에는 pending/apply backlog를 제대로 볼 수 없다

#### 최소 필드

- `blocking_reason`
- `next_required_action`
- `oldest_pending_approval_age_sec`
- `last_successful_apply_ts`
- `degraded_components`
- `reconcile_backlog_count`

#### 완료 조건

- board를 보는 순간 `왜 막혔는지 / 다음에 뭘 해야 하는지`가 보인다

---

### C2. reconcile placeholder + 운영 중 rule 추가

#### 목적

reconcile을 사전 완성형 규칙집이 아니라,
운영 중 발견한 불일치를 정리하는 자리로 둔다.

#### v0에서 먼저 하는 것

- `reconcile_cycle` 빈 자리 확보
- rule 추가 포인트 확보
- reconcile 로그 남길 위치 확보

#### 운영 중 실제로 추가할 규칙 예시

- stale pending timeout
- approved-but-not-applied cleanup
- late callback invalidation
- same-scope duplicate merge/cancel
- superseded approval 무효화
- message mapping repair

#### 완료 조건

- reconcile 자리는 존재하고,
  규칙은 실제 문제가 발견될 때 추가할 수 있는 구조가 마련된다

---

### C3. OrchestratorLoop

#### 목적

각 cycle과 worker의 생명주기를 최종적으로 조율한다.

#### 왜 마지막에 얹는가

- 개별 부품이 먼저 실제로 동작해야 지휘자 역할이 분명해진다
- 그렇지 않으면 orchestrator가 오히려 과하게 비대해진다

#### 완료 조건

- light/heavy/governance/reconcile
- approval/apply
- event drain
- degraded/emergency 판단

을 orchestrator가 최종 호출한다

---

### C4. recovery / health

#### 목적

장애 전파와 재시작 복구를 운영형으로 다듬는다.

#### 완료 조건

- HotPath / watch / Telegram / DB 장애별 degraded 또는 emergency 반응이 정리된다

---

### C5. hard contract freeze

#### 목적

실제 watch 첫 tick과 approval/apply가 돈 뒤에,
세부 필드 계약을 늦게 잠근다.

#### soft contract에서 먼저 잠글 것

- phase enum
- approval status enum
- review type enum
- closeout result enum
- v0 event type enum

#### hard contract에서 나중에 잠글 것

- `approval_id`
- `scope_key`
- `apply_job_key`
- `trace_id`
- `scope_note`
- `decision_deadline_ts`
- `supersedes_approval_id`

#### 완료 조건

- 실제 운영 로그를 보고 나서 세부 shape가 고정된다

---

## 최소 착수 순서

다음 스레드에서 정말 바로 구현에 들어간다면,
이 순서를 권장한다.

1. `A1. SystemStateManager v0`
2. `A2. EventBus v0`
3. `A3. cycle definition`
4. `A4. watch light_cycle first tick`
5. 병렬로 `B1. TelegramStateStore contract 정렬`
6. `B2. ApprovalLoop`
7. `B3. ApplyExecutor`
8. `A5. governance_cycle`
9. `B4. Telegram approval bridge`
10. `C1. Master Board`
11. `A6. heavy_cycle`
12. `C2. reconcile placeholder`
13. `C3. OrchestratorLoop`

---

## 지금 시점의 추천

지금 단계에서 제일 중요한 건 아래 세 가지다.

1. `watch first tick`을 최대한 빨리 돌린다
2. approval/apply 기반은 병렬로 만든다
3. Master Board와 Reconcile은 실제 운영 데이터가 나온 뒤 붙인다

즉 기반 공사를 하더라도,
`실제 데이터가 흐르기 시작하는 시점`을 최대한 늦추지 않는 것이 핵심이다.

---

## 최종 권장안

이 문서의 v2 해석을 한 줄로 요약하면 아래다.

`A/B 병렬로 watch를 먼저 기동하고, approval/apply를 뒤따라 붙인 다음, 실제 운영 데이터가 나온 뒤 Master Board와 Reconcile을 안정화한다`
