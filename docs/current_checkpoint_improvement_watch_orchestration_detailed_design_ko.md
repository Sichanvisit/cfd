# Current Checkpoint Improvement Watch Orchestration Detailed Design

## 목적

이 문서는 `checkpoint_improvement_watch`를 단순한 주기 실행 스크립트가 아니라,
`PA / SA / Telegram control plane`을 조율하는 오케스트레이션 계층으로 설계하기 위한 상세 기준서다.

핵심 질문은 아래 5개다.

1. 누가 언제 무엇을 호출하는가
2. 전체 시스템 상태는 어디서 관리하는가
3. approval과 apply는 어떻게 분리하는가
4. 루프 간 충돌과 중간 장애는 어떻게 복구하는가
5. 오케스트레이션에 들어가기 전에 무엇을 먼저 구축해야 하는가

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_b2_approval_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b2_approval_loop_detailed_plan_ko.md)
- [current_b3_apply_executor_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b3_apply_executor_detailed_plan_ko.md)
- [current_b4_telegram_approval_bridge_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b4_telegram_approval_bridge_detailed_plan_ko.md)
- [current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md)
- [current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md)
- [current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md)
- [current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md)
- [current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md)
- [current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md)
- [current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md)
- [current_pa789_roadmap_realignment_v1_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pa789_roadmap_realignment_v1_ko.md)

권장 읽기 흐름은 아래와 같다.

1. 전체 구조와 현재 blocker는 [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)에서 먼저 본다.
2. `PA8 / PA9 / SA` 잔여 작업은 [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)에서 확인한다.
3. 그 다음 이 문서에서 orchestration 원칙을 읽고, 실제 구현은 `A1 ~ C5` 개별 상세 문서로 내려간다.

---

## 한 줄 결론

`checkpoint_improvement_watch`는 실행자보다 `조율자`에 가까워야 한다.

즉 아래 원칙을 고정한다.

1. watch는 직접 live rule을 넓게 바꾸지 않는다
2. watch는 `candidate / review / approval-needed`를 만든다
3. 상태 전이는 `SystemStateManager`가 맡는다
4. 실제 bounded apply는 `ApplyExecutor`가 맡는다
5. Telegram은 메신저가 아니라 승인 콘솔이다
6. watch의 첫 `light_cycle` tick은 가능한 한 빨리 돌린다
7. approval/apply 기반은 watch와 병렬로 붙인다
8. `Master Board`와 `Reconcile Rules`는 운영 데이터가 나온 뒤 안정화한다

---

## 최종 구조

권장 구조는 아래와 같다.

```text
manage_cfd
  -> main.py (hot path)
  -> state25_candidate_watch
  -> manual_truth_calibration_watch
  -> OrchestratorLoop
     -> EventBus
     -> SystemStateManager
     -> checkpoint_improvement_watch
        -> light_cycle
        -> heavy_cycle
        -> governance_cycle
        -> reconcile_cycle
     -> TelegramNotificationHub
     -> TelegramUpdatePoller
     -> ApprovalLoop
     -> ApplyExecutor
     -> PnlDigestLoop
```

핵심은 아래다.

- `main.py`는 수집과 기본 실행만 담당
- `checkpoint_improvement_watch`는 후보 생성과 주기 조율 담당
- `ApprovalLoop`는 승인 상태 전이 담당
- `ApplyExecutor`는 실제 반영 담당
- `SystemStateManager`는 전체 상태의 단일 진실 소스 담당

즉 watch가 직접 모든 것을 실행하는 구조로 키우지 않는다.

---

## 역할 분해

## 1. OrchestratorLoop

역할:

- 각 worker의 생명주기 관리
- 각 cycle 호출 시점 결정
- event bus drain
- 장애 시 degrade 판단

하지 말아야 할 것:

- Telegram 카드 내용 직접 생성
- DB 상태 직접 수정
- live apply 직접 수행

쉽게 말하면:

`누가 지금 일해야 하는지 정하는 반장`

---

## 2. SystemStateManager

역할:

- 전체 시스템 상태 로드/저장
- 모든 상태 전이 검증
- master board snapshot의 원천 상태 보유

원칙:

- 상태 변경은 이 manager를 통해서만 일어난다
- 각 서비스가 자기 마음대로 state file이나 DB 상태를 직접 바꾸지 않는다
- `SystemStateManager`는 상위 운영 상태의 진실 소스다
- `TelegramStateStore`는 approval/message/offset의 하위 저장소다
- Telegram 하위 저장 정보가 곧 시스템 전체 상태를 대체하면 안 된다

쉽게 말하면:

`교실 출석부와 상태판을 들고 있는 담임`

---

## 3. EventBus

역할:

- worker 간 직접 결합을 줄이는 중계층
- event publish / subscribe / drain

현재 권장 구현:

- 단일 프로세스 인메모리 event bus

v0에서 먼저 잠글 이벤트:

- `LightRefreshCompleted`
- `GovernanceActionNeeded`
- `ApprovalReceived`
- `SystemPhaseChanged`
- `WatchError`

지금 단계에서 굳이 하지 않는 것:

- Redis
- RabbitMQ
- 멀티프로세스 외부 큐

중요:

- bus에는 가능하면 `event`만 태운다
- 실제 apply를 강제하는 command는 숨기지 않는다
- 예를 들어 rollback apply는 executor 호출이어야 하고, 단순 event로 흐려지면 안 된다

쉽게 말하면:

`누가 무슨 일을 알렸는지 전달하는 방송실`

---

## 4. checkpoint_improvement_watch

역할:

- row 증가 감지
- light / heavy / governance / reconcile cycle 호출
- review candidate 생성
- approval-needed event 생성

하지 말아야 할 것:

- Telegram 직접 전송
- 상태 전이 직접 저장
- bounded apply 직접 수행

즉 watch는 `candidate generator + scheduler`다.

---

## 5. ApprovalLoop

역할:

- Telegram callback 수신 결과를 승인 상태 전이로 변환
- `approved / held / rejected / expired / applied` 관리

핵심:

- 버튼 클릭은 함수 호출이 아니라 상태 전이
- 클릭 이력과 승인자를 반드시 남긴다

---

## 6. ApplyExecutor

역할:

- 이미 승인된 bounded action-only change를 실제로 반영
- rollback apply
- closeout apply
- scope registry 갱신

원칙:

- executor는 approval 없는 apply를 하지 않는다
- executor는 오직 bounded scope만 반영한다

쉽게 말하면:

`결정된 일만 실제로 집행하는 집행반`

---

## 전체 상태 모델

권장 상위 상태는 아래 5개다.

- `STARTING`
- `RUNNING`
- `DEGRADED`
- `EMERGENCY`
- `SHUTDOWN`

### 상태 의미

`STARTING`

- 초기화 중
- row source, DB, Telegram, state load 확인 중

`RUNNING`

- 정상 운영
- hot path, watch, approval loop 모두 동작

`DEGRADED`

- 일부 부품만 죽음
- 예: Telegram 끊김, heavy review 실패
- 하지만 hot path는 계속 돌아감

`EMERGENCY`

- MT5, row source, DB 등 핵심이 깨짐
- 신규 진입 차단 등 보수적 운영 필요

`SHUTDOWN`

- 정상 종료 또는 재시작 준비

### 중요한 원칙

Telegram이 죽어도 `RUNNING -> DEGRADED`로만 가야 한다.

즉:

- Telegram은 중요하지만
- hot path를 멈춰야 할 정도의 최종 의존성은 아니다

---

## SystemStateManager 상세 구조

권장 구조:

```text
SystemState
  -> hot_path_state
  -> improvement_state
  -> pa8_state
  -> sa_state
  -> telegram_state
  -> system_health
```

### hot_path_state

- `is_healthy`
- `last_row_ts`
- `row_delta_since_last_tick`
- `active_positions`

### improvement_state

- `light_refresh_last_run`
- `heavy_review_last_run`
- `governance_last_run`
- `reconcile_last_run`
- `pending_review_events`

### pa8_state

- symbol별 `canary_active`
- symbol별 `live_window_ready`
- symbol별 `closeout_state`
- symbol별 `rollback_pending`

### sa_state

- `scene_mode`
  - `preview_only`
  - `log_only`
- `disagreement_count`
- `preview_changed`
- `preview_improved`
- `preview_worsened`

### telegram_state

- `pending_checks`
- `pending_approvals`
- `last_poll_ts`
- `last_send_ts`
- `bot_healthy`

### system_health

- `overall_status`
- `last_error`
- `restart_count`
- `uptime_seconds`

---

## 이벤트 버스 권장 이벤트

초기엔 아래 이벤트만 있으면 충분하다.

### hot path -> 외부

- `NewCheckpointRow`
- `PositionOpened`
- `PositionClosed`
- `PositionPartiallyClosed`

### watch -> 외부

- `LightRefreshCompleted`
- `HeavyReviewCompleted`
- `CanaryActivationReviewNeeded`
- `CanaryRollbackReviewNeeded`
- `CanaryCloseoutReviewNeeded`

### approval -> 외부

- `ApprovalGranted`
- `ApprovalHeld`
- `ApprovalRejected`
- `ApprovalExpired`

### state -> 외부

- `SystemStateChanged`
- `PA8PhaseChanged`
- `EmergencyDetected`

### pnl -> 외부

- `PnlWindowUpdated`
- `PnlWindowClosed`

---

## cycle 분해

`checkpoint_improvement_watch` 내부는 꼭 아래 4 cycle로 분리한다.

## 1. light_cycle

역할:

- row delta 확인
- fast refresh 실행
- management/action/canary board 갱신

권장 주기:

- `3~5분`
- 또는 `25~50 row`

### 2. heavy_cycle

역할:

- PA7 processor refresh
- PA78 governance packet refresh
- scene disagreement audit refresh
- trend_exhaustion preview refresh

권장 주기:

- `15~30분`
- 또는 `100~300 row`

### 3. governance_cycle

역할:

- PA8 first-window ready 여부 확인
- rollback candidate 생성
- closeout candidate 생성
- approval-needed event 발행

권장 주기:

- `1~3분`

### 4. reconcile_cycle

역할:

- pending인데 만료된 approval 정리
- approved인데 applied 안 된 job 정리
- 메시지 edit 실패 후 stale mapping 정리
- poller offset과 state store 불일치 정리
- seed-only rollback false positive 정리

이 cycle은 꼭 별도 책임으로 둔다.

---

## 동시성 제어 규칙

위험한 지점은 아래 3개다.

### 1. row 기록 중 동시 읽기

대응:

- hot path는 row write 완료 후에만 event publish
- watch는 published event 이후 recent row를 읽는다

### 2. callback 연타

대응:

- poller는 callback을 순차 drain
- 동일 approval id는 멱등 무시

### 3. watch와 approval loop의 상태 충돌

대응:

- 상태 변경은 항상 `SystemStateManager.transition()`을 통해서만
- state manager 내부 lock 사용

---

## 장애 복구 원칙

### HotPath 죽음

- 가장 심각
- 즉시 재시작 시도
- 필요시 `EMERGENCY`

### ImprovementWatch 죽음

- `DEGRADED`
- hot path는 계속 유지
- 자동 재시작 시도

### TelegramHub / Poller 죽음

- `DEGRADED`
- 알림/승인만 지연
- hot path는 유지

### PnL loop 죽음

- 가장 낮은 우선순위
- 다음 주기에 복구 가능

### DB 접근 실패

- 매우 심각
- `EMERGENCY`

---

## 오케스트레이션 전에 먼저 구축할 것

이 부분이 중요하다.

v2 기준에선 이 구간을 `A/B/C` 세 층으로 다시 읽는 것이 맞다.

### Track A. watch 최소 기동

- `SystemStateManager v0`
- `EventBus v0`
- `cycle definition`
- `checkpoint_improvement_watch light_cycle first tick`

### Track B. 승인/적용 기반 병렬 구축

- `TelegramStateStore contract`
- `ApprovalLoop`
- `ApplyExecutor`
- `Telegram approval bridge`

### Track C. 합류 후 안정화

- `Master Board`
- `Reconcile placeholder + 운영 중 rule 추가`
- `OrchestratorLoop`
- `Recovery / Health`

핵심은 오케스트레이터를 먼저 만들지 않는 것, 그리고 `watch first tick`을 늦추지 않는 것이다.

## `P0. Event Contract Freeze`

v2에서는 contract freeze를 `soft / hard` 2단계로 나눈다.

### soft contract

지금 먼저 잠글 것:

- phase enum
- approval status enum
- review type enum
- closeout result enum
- v0 event type enum

### hard contract

watch first tick과 approval/apply 흐름을 한 번 돌려본 뒤 잠글 것:

- `approval_id`
- `scope_key`
- `apply_job_key`
- `trace_id`
- `scope_note`
- `decision_deadline_ts`
- `supersedes_approval_id`

왜 이렇게 나누는가:

- enum은 초기에 흔들리면 전체 설계가 흔들린다
- 세부 필드 shape는 실제 운영 로그를 보고 고정하는 편이 안전하다

### `P1. TelegramStateStore`

먼저 있어야 할 것:

- `check_groups`
- `check_events`
- `check_actions`
- `telegram_messages`
- `poller_offsets`

### `P2. ApprovalLoop`

먼저 있어야 할 것:

- pending -> approved/held/rejected/expired
- allowed user 검증
- callback idempotency

### `P3. ApplyExecutor`

먼저 있어야 할 것:

- bounded activation apply
- rollback apply
- closeout apply
- apply job registry

### `P4. Master Board Contract`

먼저 있어야 할 것:

- JSON/MD 출력 shape
- fast / pa / sa / telegram / health section schema

### `P5. Reconcile Rules`

먼저 있어야 할 것:

- `reconcile_cycle` 자리
- rule 추가 포인트
- reconcile 로그 기준

운영 중 실제로 추가될 가능성이 높은 것:

- stale pending timeout
- approved-but-not-applied
- message mapping repair
- late callback invalidation
- same-scope duplicate merge/cancel
- superseded approval 무효화
- seed-only rollback suppression

즉 오케스트레이션 전에

`상태기계 / 적용기 / 최소 cycle`

을 먼저 만들어야 하고, `상태판 / 복구규칙 완성형`은 뒤에서 다듬는 것이 맞다.

---

## 권장 구현 순서

이 문서 기준 구현 순서는 아래처럼 재정렬하는 것이 좋다.

### `O0. 문서 고정`

- 이 문서
- remaining roadmap
- control plane 문서

### `A1. SystemStateManager v0`

- 최소 phase
- 최소 pa8 symbol state
- `last_row_ts / light_last_run / heavy_last_run / governance_last_run`
- lock

### `A2. EventBus v0`

- in-memory bus
- publish / subscribe / drain

### `A3. cycle definition`

- light / heavy / governance / reconcile
- skip / throttle / cooldown 기준

### `A4. checkpoint_improvement_watch first tick`

- row observer
- fast refresh 호출
- `LightRefreshCompleted` 발행

### `B1. TelegramStateStore + ApprovalLoop`

- approval lifecycle
- callback idempotency

### `B2. ApplyExecutor`

- activation / rollback / closeout bounded apply

### `A5. governance_cycle`

- PA8 candidate 생성
- approval-needed event 생성

### `B3. Telegram approval bridge`

- review card 발송
- callback -> approval -> apply 연결

### `C1. Master Board`

- state snapshot -> latest json/md

### `C2. heavy_cycle`

- PA7 / SA review 주기 실행

### `C3. reconcile placeholder`

- 운영 중 발견 rule 추가

### `C4. OrchestratorLoop`

- 각 cycle 호출
- event drain
- degraded/emergency 판단

### `C5. Recovery / Health`

- restart recovery
- health summary

---

## 지금 시점의 추천

지금은 `OrchestratorLoop`부터 바로 코딩하기보다 아래 순서가 맞다.

1. `TelegramStateStore`
2. `ApprovalLoop`
3. `ApplyExecutor`
4. `Master Board Contract`
5. `Reconcile Rules`
6. 그 다음 `checkpoint_improvement_watch`
7. 마지막에 `OrchestratorLoop`

즉 오케스트레이션은 가장 먼저 만들 대상이 아니라,
앞단 뼈대를 다 갖춘 뒤 마지막에 얹는 지붕에 가깝다.

---

## 최종 권장안

지금 외부 조언을 반영한 최종 해석은 아래다.

1. `checkpoint_improvement_watch`는 조율자이지 실행자가 아니다.
2. approval과 apply는 분리한다.
3. `SystemStateManager`를 단일 진실 소스로 둔다.
4. `reconcile_cycle`을 별도 책임으로 둔다.
5. `PA8`은 live closeout 전까지 bounded canary active 상태를 유지한다.
6. `PA9`는 PA8 closeout 이후 시작한다.
7. `SA8`은 여전히 preview-only다.

이렇게 가면 오케스트레이터가 괴물이 되지 않고, 나중에 텔레그램 control plane과도 자연스럽게 연결되는 운영형 구조를 만들 수 있다.
