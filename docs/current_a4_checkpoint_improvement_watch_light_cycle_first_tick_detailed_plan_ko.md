# Current A4 Checkpoint Improvement Watch Light Cycle First Tick Detailed Plan

## 목적

이 문서는 `A4. checkpoint_improvement_watch light_cycle first tick`을
실제 구현 가능한 수준으로 좁혀서 정리한 상세 계획이다.

이번 단계의 핵심은 거대한 watch를 한 번에 완성하는 것이 아니다.

이미 있는 fast refresh 체인을 재사용해서,
`SystemStateManager v0` + `EventBus v0` + `cycle definition v0` 위에서
`light_cycle`이 실제로 첫 tick을 돌게 만드는 것이다.

즉 이 단계는

- row delta를 읽고
- A3 규칙으로 due/skip을 판단하고
- 기존 refresh chain을 호출하고
- 결과를 state/event로 반영하는

아주 얇은 `watch v0`를 만드는 단계다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)
- [current_a2_event_bus_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a2_event_bus_v0_detailed_plan_ko.md)
- [current_a3_cycle_definition_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a3_cycle_definition_v0_detailed_plan_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)

---

## 이번 단계의 목표

`checkpoint_improvement_watch`가 아래 흐름을 실제로 수행하게 만든다.

1. 현재 checkpoint row 수와 마지막 row 시각을 읽는다
2. `SystemStateManager` 기준으로 row delta를 계산한다
3. `evaluate_cycle_decision("light")`로 due/skip을 판단한다
4. due면 기존 `maybe_refresh_checkpoint_analysis_chain()`을 호출한다
5. refresh 성공 시
   - `row_count_since_boot`
   - `last_row_ts`
   - `light_last_run`
   - `phase`
   를 반영한다
6. `LightRefreshCompleted` 이벤트를 발행한다

이렇게 해서 `watch first tick`을 실제로 시작 가능하게 만든다.

---

## 이번 단계에서 새로 만드는 것

### 1. watch v0 service

- `backend/services/checkpoint_improvement_watch.py`

역할:

- row count / latest row ts 관찰
- light cycle due/skip 판단
- refresh chain 호출
- state update
- event publish
- watch layer report artifact 작성

### 2. watch v0 테스트

- `tests/unit/test_checkpoint_improvement_watch.py`

핵심 검증:

- rows missing skip
- first tick refresh success
- cooldown skip
- refresh exception -> degraded

### 3. watch v0 상세 기준 문서

- 이 문서 자체

---

## 이번 단계에서 재사용하는 것

### 기존 fast refresh 체인

- [path_checkpoint_analysis_refresh.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_analysis_refresh.py)

이번 단계에서는 이 체인을 직접 다시 쓰지 않고,
`watch -> refresh chain` 연결만 만든다.

### A1 상태 관리

- [system_state_manager.py](/Users/bhs33/Desktop/project/cfd/backend/services/system_state_manager.py)

이번 단계에서는 full state tree를 쓰지 않는다.
`v0 최소 상태`만 읽고 갱신한다.

### A2 이벤트 버스

- [event_bus.py](/Users/bhs33/Desktop/project/cfd/backend/services/event_bus.py)

이번 단계에서는 아래 이벤트만 사용한다.

- `LightRefreshCompleted`
- `SystemPhaseChanged`
- `WatchError`

### A3 cycle decision

- [checkpoint_improvement_cycle_definition.py](/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_cycle_definition.py)

이번 단계에서는 `light` cycle만 실제로 사용한다.

---

## 권장 public API

이번 단계 public API는 이 정도면 충분하다.

- `default_checkpoint_improvement_watch_report_path()`
- `default_checkpoint_improvement_watch_markdown_path()`
- `run_checkpoint_improvement_watch_light_cycle()`

`run_checkpoint_improvement_watch_light_cycle()`은
다음 의존성을 주입 가능하게 두는 편이 좋다.

- `SystemStateManager`
- `EventBus`
- `refresh_function`

이렇게 해두면 무거운 refresh chain을 직접 돌리지 않고도 unit test를 빠르게 작성할 수 있다.

---

## 최소 동작 규칙

### 1. rows missing

- rows 파일이 없으면 refresh를 시도하지 않는다
- `checkpoint_rows_missing`으로 skip
- state는 바꾸지 않는다
- event도 발행하지 않는다

### 2. light due

- row delta가 있고
- cooldown이 아니면
- light cycle은 due가 될 수 있다

### 3. refresh 성공

refresh summary의 `trigger_state == REFRESHED`일 때만 성공으로 본다.

성공 시:

- `record_row_observation()`
- `mark_cycle_run("light")`
- 필요하면 `STARTING -> RUNNING`
- `LightRefreshCompleted` 발행

### 4. refresh 실패

refresh 함수가 예외를 던지면:

- `DEGRADED`로 전이
- `WatchError` 발행
- 필요하면 `SystemPhaseChanged` 발행

### 5. refresh 미완료

due였지만 refresh summary가 `REFRESHED`가 아니면:

- row processed count는 올리지 않는다
- cycle last run도 찍지 않는다
- `WatchError`만 남긴다

즉 `실제로 refresh가 끝난 경우만` processed state를 전진시킨다.

---

## 왜 row_count_since_boot를 바로 올리지 않나

이 단계에서 `row_count_since_boot`는
단순 관찰 수가 아니라 사실상 `processed row count` 역할을 한다.

그래야 cooldown 때문에 skip된 row가
다음 tick에서 사라지지 않는다.

즉:

- due + refreshed 성공 -> 증가
- skip 또는 refresh 미완료 -> 유지

이 규칙이 맞다.

---

## 권장 산출물

### watch layer report

- `data/analysis/shadow_auto/checkpoint_improvement_watch_latest.json`
- `data/analysis/shadow_auto/checkpoint_improvement_watch_latest.md`

이 report는 refresh chain 자체의 report를 대체하지 않는다.

역할은 다르다.

- refresh report: 무엇을 다시 빌드했는가
- watch report: 왜 이번 tick이 돌았고, state/event는 어떻게 바뀌었는가

---

## 이번 단계에서 아직 하지 않는 것

- governance candidate 생성
- Telegram approval bridge
- heavy cycle 실행
- reconcile cycle 실행
- master board 통합
- orchestrator loop

즉 이번 단계는 `watch 전체`가 아니라 `watch의 light first tick`만 닫는 단계다.

---

## 테스트 범위

이번 단계 테스트는 아래 4개면 충분하다.

1. rows missing -> skip
2. first tick + refresh success -> running + event publish
3. cooldown -> refresh 미호출
4. refresh exception -> degraded + watch error

이 정도면 A4 목표를 검증하기에 충분하다.

---

## 완료 조건

- `checkpoint_improvement_watch.py`가 실제로 존재한다
- `light_cycle` first tick이 코드로 동작한다
- refresh 성공 시 state/event가 반영된다
- refresh 실패 시 degraded/error 흐름이 남는다
- unit test가 통과한다

---

## 다음 단계 연결

A4가 닫히면 다음 순서는 아래가 가장 자연스럽다.

1. `A5. governance_cycle`
2. 병렬로 `B1/B2/B3`
3. 그 다음 `C1. Master Board`

즉 A4는
`watch가 실제 데이터를 한 번 보기 시작하는 첫 단계`
라고 보면 된다.
