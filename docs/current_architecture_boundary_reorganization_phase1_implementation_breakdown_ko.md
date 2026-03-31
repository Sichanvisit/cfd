# CFD 현재 아키텍처 정리 Phase 1 구현 분해 문서

부제: Consumer Check Single Owner + BLOCKED Visual Continuity 실제 구현용 가이드

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 Phase 1을 실제 코드 수정 단위로 쪼개기 위한 구현 가이드다.

같이 보면 좋은 문서:

- [current_architecture_boundary_reorganization_phase1_single_owner_blocked_checklist_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_phase1_single_owner_blocked_checklist_ko.md)
- [current_architecture_boundary_reorganization_detail_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_detail_ko.md)

이 문서의 목표는 아래다.

- 어떤 함수부터 손대야 하는지 정한다
- 공용 resolver를 어떤 형태로 뽑을지 정한다
- chart 쪽 영향 범위를 미리 정리한다
- 테스트를 어떤 이름/순서로 추가할지 정한다


## 2. 현재 코드상 핵심 진입점

Phase 1에서 실제로 중요한 함수는 세 개다.

### 2-1. base consumer check 생성

- `backend/services/entry_service.py:1762`
- 함수명: `_build_consumer_check_state(payload: dict) -> dict`

현재 성격:

- `_core_action_decision(...)` 내부 nested helper
- candidate/stage/display/blocked reason/strength를 한 번에 계산

문제:

- nested helper라 재사용/테스트/공용화가 어렵다
- 여기서 계산한 값이 이후 late rewrite로 다시 바뀐다

### 2-2. late effective consumer check 재계산

- `backend/services/entry_try_open_entry.py:590`
- 함수명: `_resolve_effective_consumer_check_state(...)`

현재 성격:

- late block, action_none, order-side fallback을 반영해 effective state를 다시 만든다

문제:

- `entry_service.py`와 별도 policy owner를 가진다
- `late_display_suppress_guards`가 별도 set으로 존재한다

### 2-3. chart event translation

- `backend/trading/chart_painter.py:796`
- 함수명: `_resolve_consumer_check_event_kind(cls, row: dict) -> tuple[str, str, str] | None`

현재 성격:

- `consumer_check_state_v1`를 chart event kind로 바꾼다

문제:

- `BLOCKED`와 `OBSERVE`를 둘 다 `*_WAIT`로 합친다
- `check_display_ready = false`면 아예 시각 surface에서 사라진다


## 3. Phase 1의 목표 상태

Phase 1이 끝났을 때 원하는 상태는 아래다.

### 3-1. consumer check truth owner

아래 값의 최종 owner가 한 군데여야 한다.

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `check_reason`
- `entry_block_reason`
- `blocked_display_reason`
- `display_strength_level`

### 3-2. base와 effective의 역할 구분

권장 구분:

- `base state`
  - semantic/consumer 관점의 1차 surface
- `effective state`
  - late execution block까지 반영한 최종 surface

중요:

- 둘을 나누는 것은 괜찮다
- 하지만 둘의 policy table owner는 하나여야 한다

### 3-3. chart의 역할

chart는 truth owner가 아니어야 한다.

chart는 아래만 해야 한다.

- effective state 읽기
- event family로 번역
- 색상/두께/위치 표현


## 4. 권장 파일 구조

Phase 1에서는 아래처럼 공용 모듈을 하나 도입하는 방향을 권장한다.

### 4-1. 후보 파일

- `backend/services/consumer_check_state.py`

권장 이유:

- `entry_service.py` 밖으로 nested helper를 빼기 좋다
- `entry_try_open_entry.py`도 같은 모듈을 재사용하기 쉽다
- Phase 1 범위가 명확하다

### 4-2. 권장 public 함수 후보

후보 1:

- `build_base_consumer_check_state_v1(...) -> dict`

후보 2:

- `resolve_effective_consumer_check_state_v1(...) -> dict`

후보 3:

- `coerce_consumer_check_state_v1(...) -> dict`

후보 4:

- `consumer_check_blocked_visual_allowed(...) -> bool`

주의:

- chart 전용 event kind 번역 함수까지 service 모듈로 빼는 것은 권장하지 않는다
- chart는 chart_painter 안에 두되, upstream state를 더 정직하게 읽게 만드는 편이 좋다


## 5. 실제 구현 순서 권장안

### Step 1. nested helper를 독립 가능한 순수 함수로 바꾸기

시작 지점:

- `backend/services/entry_service.py:1762`

해야 할 일:

- 현재 `_build_consumer_check_state(payload)`가 암묵적으로 캡처하는 외부 변수 목록을 정리한다
- `symbol`, `shadow_reason`, `shadow_side`, `box_state`, `bb_state`, `probe_plan_v1`, `default_side_gate_v1` 등 dependency를 명시 인자로 바꾼다
- side-effect 없이 dict만 반환하는 순수 함수 형태로 정리한다

핵심 이유:

- nested helper 상태로는 `entry_try_open_entry`와 공용화가 불편하다
- 먼저 pure function으로 만들면 이후 외부 모듈 이동이 쉬워진다

산출물:

- `build_base_consumer_check_state_v1(...)`

### Step 2. 새 공용 모듈로 이동하기

대상:

- `backend/services/consumer_check_state.py`

해야 할 일:

- Step 1에서 정리한 pure function을 새 모듈로 옮긴다
- contract version 관련 기본값을 이 모듈에서 처리한다
- `entry_service.py`는 이 함수를 import해서 사용하게 바꾼다

완료 판단:

- `entry_service.py` 안에 nested `_build_consumer_check_state`가 더 이상 없어야 한다

### Step 3. effective resolver를 같은 모듈로 흡수하기

시작 지점:

- `backend/services/entry_try_open_entry.py:590`

해야 할 일:

- 현재 `_resolve_effective_consumer_check_state(...)`의 policy를 새 모듈의 `resolve_effective_consumer_check_state_v1(...)`로 이동한다
- `late_display_suppress_guards`를 공용 정책표 안으로 흡수한다
- `entry_try_open_entry.py`는 resolver caller만 남긴다

중요:

- 이 단계가 Phase 1의 핵심이다
- `entry_service`와 `entry_try_open_entry`의 stage/display owner를 실제로 하나로 만드는 순간이다

산출물:

- `resolve_effective_consumer_check_state_v1(...)`

### Step 4. row/runtime payload가 공용 resolver 결과만 쓰게 정리하기

관련 구간:

- `backend/services/entry_service.py:2206-2215`
- `backend/services/entry_try_open_entry.py:712-718`
- `backend/services/entry_try_open_entry.py:1195-1201`
- `backend/services/entry_try_open_entry.py:1257-1263`

해야 할 일:

- base state는 base state대로
- effective state는 effective state대로
- 어떤 경로가 최종 row/runtime/chart truth source인지 명확히 고정한다

권장:

- row/latest signal/chart가 참조하는 최종 truth는 effective state 하나로 맞춘다

### Step 5. chart에서 `BLOCKED`를 별도 event family로 승격하기

시작 지점:

- `backend/trading/chart_painter.py:796-818`

권장 방향:

- `BUY_BLOCKED`
- `SELL_BLOCKED`

새 event family를 추가하는 방향을 우선 추천한다.

이유:

- 운영자가 `WAIT`와 `BLOCKED`를 즉시 구분할 수 있다
- `level`, `color`, `line_width` 차등 적용이 쉬워진다

fallback 방향:

- 신규 event family가 부담이면 `BUY_WAIT`/`SELL_WAIT`를 유지하되 blocked metadata를 필수 표면값으로 두는 차선책도 가능하다

하지만 Phase 1에서는 명시적 blocked event가 더 정직하다.

### Step 6. chart_painter의 event-kind 참조 구간을 함께 정리하기

`_resolve_consumer_check_event_kind` 하나만 바꾸면 끝나지 않는다.

같이 확인해야 할 대표 구간:

- `backend/trading/chart_painter.py:69`
- `backend/trading/chart_painter.py:257-262`
- `backend/trading/chart_painter.py:608-615`
- `backend/trading/chart_painter.py:718-734`
- `backend/trading/chart_painter.py:1362-1368`
- `backend/trading/chart_painter.py:1504`
- `backend/trading/chart_painter.py:1539`
- `backend/trading/chart_painter.py:1650-1653`
- `backend/trading/chart_painter.py:1866-1886`

왜 같이 봐야 하나:

- color map
- event grouping
- side inference
- line width
- ready/wait normalization
- record/render branch

가 여러 군데 흩어져 있기 때문이다

즉 `BUY_BLOCKED`/`SELL_BLOCKED`를 넣으면 이 집합 membership도 함께 업데이트해야 한다.

### Step 7. 테스트를 base/effective/visual 3층으로 나누어 추가하기

권장 구조:

- service-layer pure function tests
- effective resolver tests
- chart translation tests

이렇게 나누면 이후 회귀가 생겨도 어느 층에서 깨졌는지 바로 알 수 있다.


## 6. 구체적인 함수 후보 시그니처

아래는 구현을 시작할 때 참고할 만한 후보 시그니처다.

```python
def build_base_consumer_check_state_v1(
    *,
    payload: Mapping[str, Any],
    symbol: str,
    shadow_reason: str,
    shadow_side: str,
    box_state: str,
    bb_state: str,
    probe_plan_default: Mapping[str, Any] | None = None,
    default_side_gate_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ...
```

```python
def resolve_effective_consumer_check_state_v1(
    *,
    state: Mapping[str, Any] | None,
    blocked_by_value: str = "",
    action_none_reason_value: str = "",
    action_value: str = "",
    observe_reason_value: str = "",
    late_display_suppress_guards: Collection[str] | None = None,
) -> dict[str, Any]:
    ...
```

```python
def resolve_consumer_check_stage_level_v1(
    *,
    candidate: bool,
    entry_ready: bool,
    display_ready: bool,
    blocked: bool,
    probe_ready: bool,
    weak_observe: bool,
    structural_observe: bool,
    candidate_support: float,
    pair_gap: float,
) -> tuple[str, int]:
    ...
```

주의:

- 위 시그니처는 권장안이다
- 그대로 복붙용이라기보다 실제 리팩터링 방향을 잡기 위한 기준이다


## 7. 세부 작업 단위

### 7-1. Task A1: dependency inventory 작성

목표:

- `_build_consumer_check_state`가 외부에서 암묵 캡처하는 값 목록을 확정한다

출력:

- 함수 인자 표
- payload key dependency 표

### 7-2. Task A2: base resolver pure extraction

목표:

- nested helper를 모듈 함수로 외부화한다

출력:

- `consumer_check_state.py`
- `build_base_consumer_check_state_v1`

### 7-3. Task A3: effective resolver unification

목표:

- late rewrite 로직을 공용 모듈 함수로 이동한다

출력:

- `resolve_effective_consumer_check_state_v1`

### 7-4. Task A4: caller replacement

목표:

- `entry_service.py`
- `entry_try_open_entry.py`

가 공용 함수를 호출하게 바꾼다

### 7-5. Task B1: blocked event family 결정

목표:

- `BUY_BLOCKED` / `SELL_BLOCKED` 채택 여부를 확정한다

권장:

- 채택

### 7-6. Task B2: painter event-kind propagation

목표:

- chart_painter의 color/group/render membership에 blocked event를 반영한다

### 7-7. Task B3: visual regression tests

목표:

- blocked/observe/probe/ready 시각 의미가 고정되도록 테스트를 추가한다


## 8. 테스트 추가 권장안

### 8-1. 새 pure resolver 테스트 후보

권장 파일:

- `tests/unit/test_consumer_check_state.py`

권장 테스트명 예시:

- `test_build_base_consumer_check_state_marks_probe_not_promoted_as_probe`
- `test_build_base_consumer_check_state_marks_energy_soft_block_as_blocked`
- `test_build_base_consumer_check_state_suppresses_balanced_conflict_display`
- `test_resolve_effective_consumer_check_state_drops_display_for_late_suppress_guard`
- `test_resolve_effective_consumer_check_state_downgrades_ready_to_observe_on_late_action_none`

### 8-2. 기존 entry_service 테스트 보강 후보

관련 파일:

- `tests/unit/test_entry_service_guards.py`

권장 추가 포인트:

- 공용 resolver 사용 이후에도 기존 symbol-specific 예외가 유지되는지
- `blocked_display_reason`가 유지되는지
- `consumer_check_state_v1` contract version/fields가 유지되는지

### 8-3. chart 테스트 보강 후보

관련 파일:

- `tests/unit/test_chart_painter.py`

권장 테스트명 예시:

- `test_add_decision_flow_overlay_prefers_consumer_check_blocked_state`
- `test_resolve_consumer_check_event_kind_returns_buy_blocked_for_blocked_stage`
- `test_blocked_event_uses_distinct_visual_family_from_wait`
- `test_blocked_event_preserves_block_reason_for_history_reload`


## 9. 권장 PR 분할

Phase 1을 한 PR에 다 넣기보다 아래처럼 나누는 편이 좋다.

### PR 1

- `consumer_check_state.py` 추가
- base resolver extraction
- entry_service caller 교체
- pure function tests 추가

### PR 2

- effective resolver unification
- entry_try_open_entry caller 교체
- late suppress guard 공용화
- entry_service/runtime 관련 회귀 테스트 추가

### PR 3

- chart blocked event family 도입
- color/group/render propagation
- chart tests 추가

이 분할의 장점:

- 어디서 회귀가 생기는지 추적이 쉽다
- chart 변경과 service 변경을 분리해 이해할 수 있다


## 10. 구현 중 피해야 할 선택

### 10-1. `entry_try_open_entry`에만 임시 보정 더하기

이건 Phase 1 목표와 정반대다.

이유:

- truth owner를 더 늘린다
- 다음 bug를 더 찾기 어렵게 만든다

### 10-2. chart에서만 blocked를 세게 보이게 하고 upstream은 그대로 두기

이것도 피해야 한다.

이유:

- 시각 증상은 줄어들 수 있어도 truth owner는 그대로 분산된다

### 10-3. Phase 1에서 symbol-specific tuning까지 같이 손대기

이건 Phase 4 영역이다.

Phase 1은 owner 통합과 visual continuity까지만 집중하는 편이 안전하다.


## 11. 가장 먼저 시작할 실제 순서

실제 구현을 시작한다면 아래 순서를 추천한다.

1. `entry_service.py:1762`의 nested `_build_consumer_check_state`를 pure function으로 정리한다
2. 새 `consumer_check_state.py` 모듈을 만든다
3. `entry_try_open_entry.py:590`의 effective resolver를 새 모듈로 옮긴다
4. `entry_service.py`와 `entry_try_open_entry.py`가 같은 모듈을 쓰게 만든다
5. `chart_painter.py:796`에서 `BUY_BLOCKED` / `SELL_BLOCKED` 번역을 도입한다
6. chart_painter의 event-kind set membership 전부 업데이트한다
7. pure resolver / entry_service / chart 테스트를 차례로 붙인다


## 12. 종료 기준

Phase 1 구현이 끝났다고 볼 수 있는 기준은 아래다.

- stage/display policy owner가 사실상 한 곳이다
- late block 회귀가 공용 resolver 테스트로 잡힌다
- chart에서 `WAIT`와 `BLOCKED`가 분리된다
- row/runtime/chart가 같은 consumer check truth를 읽는다
- 기존 targeted tests와 신규 resolver tests가 모두 통과한다
