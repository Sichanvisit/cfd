# Current A2 EventBus v0 Detailed Plan

## 목적

이 문서는 `A2. EventBus v0`를 실제 구현 가능한 수준으로 좁혀서,
이번 단계에서 무엇을 넣고 무엇을 아직 미루는지 정리한 상세 계획이다.

이번 단계의 목표는 거대한 메시지 플랫폼을 만드는 것이 아니다.

`checkpoint_improvement_watch`, `ApprovalLoop`, `ApplyExecutor`, `SystemStateManager`가
직접 서로를 세게 참조하지 않도록, 단일 프로세스 안에서 쓰는 가벼운 이벤트 중계층을 먼저 만든다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)

---

## 이번 단계의 한 줄 목표

`publish / subscribe / drain / handler error isolation`이 되는
단일 프로세스용 `EventBus v0`와, 최소 이벤트 5종을 만든다.

---

## 지금 넣는 것

### EventBus 책임

- queue에 event 적재
- event type별 handler 등록
- queue drain
- handler 오류 격리
- dispatch error 기록

### 최소 이벤트 5종

1. `LightRefreshCompleted`
2. `GovernanceActionNeeded`
3. `ApprovalReceived`
4. `SystemPhaseChanged`
5. `WatchError`

### 공통 이벤트 필드

- `trace_id`
- `occurred_at`
- `payload`

즉 이벤트 자체는 작고, 세부 데이터는 `payload`에 넣는 v0 형태로 간다.

---

## 이번 단계에서 아직 안 넣는 것

- Redis / RabbitMQ
- durable event queue
- retry queue
- event persistence
- priority queue
- wildcard subscribe
- command bus

즉 A2는 `방송실`이지 `작업 지시 엔진`이 아니다.

---

## 중요한 원칙

### 1. bus에는 event만 태운다

bus는 가능하면 `발생 사실`만 전달한다.

예:

- `GovernanceActionNeeded`
- `ApprovalReceived`

반대로 아래처럼 실제 적용을 직접 의미하는 command는
bus에 숨기지 않는다.

- `ApplyRollbackNow`
- `RunCloseoutNow`

이런 것은 나중에도 `ApplyExecutor`의 명시적 호출로 남기는 것이 맞다.

### 2. handler 하나가 실패해도 다른 handler는 계속 돌아야 한다

v0에서 가장 중요한 안정성 규칙은 이거다.

한 handler가 죽었다고 queue drain 전체가 멈추면
오히려 bus가 위험한 결합점이 된다.

### 3. 단일 프로세스 in-memory면 충분하다

지금 단계는 `manage_cfd` 아래 단일 프로세스 orchestration을 가정하므로,
in-memory deque 기반이면 충분하다.

---

## 권장 파일

- 구현:
  - `backend/services/event_bus.py`
- 테스트:
  - `tests/unit/test_event_bus.py`

---

## 권장 public API

이번 단계 public API는 아래 정도면 충분하다.

- `EventEnvelope.event_type`
- `EventBus.publish()`
- `EventBus.subscribe()`
- `EventBus.drain()`
- `EventBus.pending_count()`
- `EventBus.get_dispatch_errors()`
- `EventBus.clear_dispatch_errors()`

---

## 권장 이벤트 구조

v0에서는 이벤트마다 복잡한 전용 필드를 많이 만들지 않는다.

예를 들면:

- `LightRefreshCompleted(payload={...})`
- `ApprovalReceived(payload={...})`

같은 식으로 가고,
세부 필드는 이후 `ApprovalLoop`, `governance_cycle`, `ApplyExecutor`가 붙으면서 늘린다.

핵심은 `event type`과 `trace_id`가 살아 있는 것이다.

---

## 테스트 범위

이번 단계 테스트는 아래만 닫으면 충분하다.

1. publish 후 pending count 증가
2. subscribe한 handler가 event를 받는다
3. 여러 handler가 모두 호출된다
4. handler 하나가 실패해도 다른 handler는 계속 호출된다
5. dispatch error가 기록된다
6. queue drain이 FIFO 순서를 유지한다
7. subscriber 없는 event도 안전하게 drain된다

---

## 완료 조건

- `EventBus v0` 구현이 있다
- 최소 이벤트 5종이 정의되어 있다
- handler 오류 격리가 된다
- 이후 `A4 watch light_cycle first tick`이 bus를 바로 사용할 수 있다
- unit test가 통과한다

---

## 다음 단계 연결

A2가 닫히면 바로 다음은 아래 순서가 맞다.

1. `A3. cycle definition`
2. `A4. checkpoint_improvement_watch light_cycle first tick`
3. 병렬로 `B2. ApprovalLoop`

즉 A2는 단독 목표가 아니라,
watch가 event를 발행하고 다음 단계가 그 event를 읽게 만드는 기반 공사다.
