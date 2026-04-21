# Current A1 SystemStateManager v0 Detailed Plan

## 목적

이 문서는 `A1. SystemStateManager v0`를 실제 구현 가능한 수준으로 좁혀서,
무엇을 지금 넣고 무엇을 아직 미루는지 명확하게 적어둔 상세 계획이다.

이번 단계의 목표는 거대한 상태 플랫폼을 만드는 것이 아니다.

`checkpoint_improvement_watch`가 첫 `light_cycle` tick을 돌기 위해 필요한
최소 상태 저장/전이 계층을 먼저 만드는 것이 목표다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)

---

## 이번 단계의 한 줄 목표

`phase / row timestamp / cycle run timestamp / PA8 symbol state / telegram health`를
한 파일에 읽고 쓰고 전이 검증할 수 있는 `SystemStateManager v0`를 만든다.

---

## 지금 넣는 것

### 최소 상태 필드

- `contract_version`
- `created_at`
- `updated_at`
- `phase`
- `last_transition_reason`
- `last_row_ts`
- `row_count_since_boot`
- `light_last_run`
- `heavy_last_run`
- `governance_last_run`
- `pa8_symbols`
  - symbol별
    - `canary_active`
    - `live_window_ready`
- `telegram_healthy`
- `last_error`

### 최소 phase

- `STARTING`
- `RUNNING`
- `DEGRADED`
- `EMERGENCY`
- `SHUTDOWN`

### 최소 책임

- default state bootstrap
- JSON snapshot load/save
- phase transition validation
- row observation update
- cycle run mark
- PA8 symbol state update
- telegram health update
- thread lock 기반 동시 접근 방어

---

## 이번 단계에서 아직 안 넣는 것

- 세부 `sa_state`
- 세부 `improvement_state`
- 복잡한 optimistic locking
- multi-process synchronization
- approval backlog 상세 상태
- reconcile backlog 상세 상태
- master board 집계

즉 A1은 `상위 상태의 최소 골격`만 만든다.

---

## SystemStateManager와 TelegramStateStore 관계

이번 단계에서 이 경계를 꼭 고정한다.

- `SystemStateManager`
  - 상위 운영 상태의 진실 소스
- `TelegramStateStore`
  - approval/message/offset 하위 저장소

텔레그램 하위 저장소의 내용은 나중에 `ApprovalLoop`와 `ApplyExecutor`가 읽고 쓰게 되지만,
시스템 전체 `phase`나 상위 상태 요약은 `SystemStateManager`를 통해 올라와야 한다.

즉 둘은 같은 수준의 state store가 아니다.

---

## 권장 파일

- 구현:
  - `backend/services/system_state_manager.py`
- 테스트:
  - `tests/unit/test_system_state_manager.py`

---

## 권장 public API

이번 단계 public API는 아래 정도면 충분하다.

- `default_checkpoint_improvement_system_state_path()`
- `build_default_system_state()`
- `SystemStateManager.get_state()`
- `SystemStateManager.transition()`
- `SystemStateManager.record_row_observation()`
- `SystemStateManager.mark_cycle_run()`
- `SystemStateManager.set_pa8_symbol_state()`
- `SystemStateManager.set_telegram_health()`

필요하면 이후 `A2/A4`에서 더 늘린다.

---

## 최소 전이 규칙

v0에서는 너무 복잡하게 만들지 않는다.

- `STARTING -> RUNNING | DEGRADED | EMERGENCY | SHUTDOWN`
- `RUNNING -> RUNNING | DEGRADED | EMERGENCY | SHUTDOWN`
- `DEGRADED -> DEGRADED | RUNNING | EMERGENCY | SHUTDOWN`
- `EMERGENCY -> EMERGENCY | DEGRADED | SHUTDOWN`
- `SHUTDOWN -> SHUTDOWN`

즉 운영상 말이 되는 최소 전이만 허용한다.

---

## 테스트 범위

이번 단계 테스트는 아래만 닫으면 충분하다.

1. 파일이 없을 때 default state bootstrap
2. phase transition과 persistence
3. invalid transition reject
4. row observation update
5. cycle run mark
6. PA8 symbol / telegram health update

---

## 완료 조건

- `SystemStateManager v0` 구현이 있다
- 최소 상태 필드가 안정적으로 저장된다
- phase 전이가 검증된다
- 이후 `A4 watch light_cycle first tick`이 이 manager를 바로 사용할 수 있다
- unit test가 통과한다

---

## 다음 단계 연결

A1이 닫히면 바로 다음은 아래 순서가 맞다.

1. `A2. EventBus v0`
2. `A3. cycle definition`
3. `A4. checkpoint_improvement_watch light_cycle first tick`

즉 A1은 독립 완성품이라기보다,
watch가 실제로 첫 tick을 돌기 위한 출석부를 먼저 만드는 단계다.
