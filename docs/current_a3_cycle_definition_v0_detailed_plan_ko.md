# Current A3 Cycle Definition v0 Detailed Plan

## 목적

이 문서는 `A3. cycle definition`을 실제 구현 가능한 수준으로 좁혀서,
이번 단계에서 무엇을 넣고 무엇을 아직 미루는지 정리한 상세 계획이다.

이번 단계의 목표는 똑똑한 스케줄러를 완성하는 것이 아니다.

`checkpoint_improvement_watch`가 `light / heavy / governance / reconcile`을
어떤 규칙으로 돌리고 건너뛰는지에 대한 `v0 계약 + 판단 헬퍼`를 먼저 만든다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)
- [current_a2_event_bus_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a2_event_bus_v0_detailed_plan_ko.md)

---

## 이번 단계의 한 줄 목표

`light / heavy / governance / reconcile` 4개 cycle의 기본 주기와
`due / skip / cooldown` 판정을 코드 상수와 함수로 고정한다.

---

## 지금 넣는 것

### 1. cycle contract

아래 4개 cycle에 대한 기본 contract를 둔다.

- `light`
- `heavy`
- `governance`
- `reconcile`

각 contract엔 최소한 아래가 들어간다.

- `cycle_name`
- `min_interval_seconds`
- `preferred_interval_seconds`
- `row_delta_floor`
- `sample_floor`

### 2. decision evaluator

각 cycle에 대해 아래를 판단하는 헬퍼를 둔다.

- 지금 due인가
- 아니면 skip/cooldown인가
- 어떤 이유로 due 또는 skip이 났는가
- 기준 elapsed / row delta / sample 수는 얼마인가

### 3. v0 기준값

v0는 아래 정도면 충분하다.

- `light`
  - min interval: `180s`
  - preferred interval: `300s`
  - row delta floor: `25`
- `governance`
  - min interval: `60s`
  - preferred interval: `180s`
  - row delta floor: `1`
- `heavy`
  - min interval: `900s`
  - preferred interval: `1800s`
  - row delta floor: `100`
  - sample floor: `100`
- `reconcile`
  - min interval: `300s`
  - preferred interval: `600s`
  - row delta floor: `0`

이 수치는 운영 중 바뀔 수 있지만,
`A4 watch first tick`이 기대할 초깃값으로 먼저 고정한다.

---

## 이번 단계에서 아직 안 넣는 것

- 동적 주기 조정
- 부하 기반 adaptive scheduling
- priority scheduler
- external cron integration
- multi-worker coordination
- reconcile rule 본체

즉 A3는 `스케줄러 엔진`이 아니라 `사이클 규약과 판단 함수`다.

---

## 중요한 원칙

### 1. light는 first tick을 늦추지 않는다

`light_cycle`은 row가 조금이라도 들어오면,
첫 실행은 빠르게 탈 수 있어야 한다.

즉 `row_delta > 0`인 첫 실행은 바로 due가 될 수 있어야 한다.

### 2. governance는 Telegram에 종속되지 않는다

`governance_cycle`은 approval candidate를 만드는 쪽이지,
Telegram이 살아 있을 때만 돌면 안 된다.

즉 Telegram이 죽어도 governance는 candidate를 만들고
필요하면 log-only로 남길 수 있어야 한다.

### 3. heavy는 보수적으로

`heavy_cycle`은 hot path healthy + sample floor 만족일 때만
주기적으로 돈다고 보는 게 맞다.

### 4. reconcile은 placeholder로 시작

reconcile은 지금 단계에서 자리만 만들고,
`신호가 있을 때 due` 판단만 넣는다.

---

## 권장 파일

- 구현:
  - `backend/services/checkpoint_improvement_cycle_definition.py`
- 테스트:
  - `tests/unit/test_checkpoint_improvement_cycle_definition.py`

---

## 권장 public API

이번 단계 public API는 아래 정도면 충분하다.

- `build_default_cycle_definitions()`
- `get_cycle_definition()`
- `evaluate_cycle_decision()`
- `active_pa8_symbol_count()`

필요하면 이후 `A4`에서 헬퍼를 더 늘린다.

---

## 최소 판단 규칙

### light

- `row_delta == 0`이면 skip
- 첫 실행이고 row가 있으면 due
- min interval 안이면 cooldown
- row floor를 넘기거나 preferred interval이 지나면 due

### governance

- active canary도 backlog도 없으면 skip
- 첫 실행이면 due
- min interval 안이면 cooldown
- backlog가 있거나 row가 있거나 preferred interval이 지나면 due

### heavy

- hot path unhealthy면 skip
- sample floor 미달이면 skip
- 첫 실행 + sample floor 충족이면 due
- min interval 안이면 cooldown
- row floor + sample floor를 만족하거나 preferred interval이 지나면 due

### reconcile

- 신호가 없으면 기본적으로 skip
- 신호가 있으면 due 후보
- min interval 안이면 cooldown
- preferred interval이 지나면 periodic scan으로 due 가능

---

## 테스트 범위

이번 단계 테스트는 아래만 닫으면 충분하다.

1. 4개 cycle contract 생성
2. light first run due
3. light cooldown skip
4. governance no active/no backlog skip
5. governance active canary due
6. heavy hot path unhealthy skip
7. heavy sample floor + row floor 충족 시 due
8. reconcile signal 없으면 skip
9. reconcile signal 있으면 due

---

## 완료 조건

- cycle contract가 코드 상수로 존재한다
- due/skip 판단 헬퍼가 있다
- `A4 checkpoint_improvement_watch first tick`이 바로 읽어 쓸 수 있다
- unit test가 통과한다

---

## 다음 단계 연결

A3가 닫히면 바로 다음은 아래 순서가 맞다.

1. `A4. checkpoint_improvement_watch light_cycle first tick`
2. `A5. governance_cycle`

즉 A3는 watch를 실제로 움직이기 전,
“어떤 타이밍에 움직일지”를 먼저 잠그는 단계다.
