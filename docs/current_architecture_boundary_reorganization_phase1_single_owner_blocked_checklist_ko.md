# CFD 현재 아키텍처 정리 Phase 1 체크리스트

부제: Consumer Check Single Owner + BLOCKED Visual Continuity

작성일: 2026-03-27 (KST)

## 1. Phase 목표

Phase 1의 목표는 두 가지다.

- `guard -> stage -> display -> effective state` owner를 하나로 모은다
- `BLOCKED`를 chart/runtime에서 `OBSERVE`와 구분되게 보존한다

이 단계는 가장 우선순위가 높다.

이유:

- 최근 wrong READY 류 문제와 직접 연결되어 있다
- 이후 단계의 observability/logging이 믿을 만하려면 먼저 truth owner가 안정화되어야 한다


## 2. 현재 문제 요약

현재 owner는 아래처럼 나뉘어 있다.

- `backend/services/entry_service.py:1838-1916`
- `backend/services/entry_try_open_entry.py:618-645`

그리고 chart는 아래에서 `BLOCKED`를 `WAIT`로 합친다.

- `backend/trading/chart_painter.py:805-817`

즉 현재는 내부 truth와 마지막 표면이 완전히 일치하지 않을 수 있는 구조다.


## 3. 대상 파일

- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`
- `backend/trading/chart_painter.py`
- 필요 시 `backend/services/` 하위의 새 helper 파일
- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_chart_painter.py`
- 필요 시 `tests/unit/test_trading_application_runtime_status.py`


## 4. 권장 구현 방향

### 4-1. 공용 resolver 도입

권장 함수 예시:

- `resolve_consumer_check_effective_state(...)`
- 또는 `build_effective_consumer_check_state_v1(...)`

이 resolver는 아래 값을 한 번에 계산해야 한다.

- `check_stage`
- `check_display_ready`
- `entry_ready`
- `blocked_display_reason`
- `display_level`
- `display_strength`
- `effective_reason`

### 4-2. late suppress guard 흡수

현재 `entry_try_open_entry.py`의 `late_display_suppress_guards`는 phase 1에서 공용 resolver 정책표 안으로 흡수하는 것이 좋다.

즉 `entry_try_open_entry`는 정책 owner가 아니라 finalization caller가 되어야 한다.

### 4-3. chart는 번역만 하게 만들기

`chart_painter.py`는 가능하면 아래 원칙을 따라야 한다.

- truth를 재계산하지 않는다
- upstream effective state를 번역만 한다
- `BLOCKED`와 `OBSERVE`를 별도 visual semantic으로 다룬다


## 5. 체크리스트

### 5-1. 사전 정리

- 현재 `entry_service.py`의 stage/display 계산 구간을 inventory화한다
- 현재 `entry_try_open_entry.py`의 late rewrite 구간을 inventory화한다
- 현재 chart의 `OBSERVE/BLOCKED -> WAIT` 규칙을 명시적으로 기록한다

### 5-2. 계약 정의

- `consumer_check_state_v1`의 effective contract를 문장으로 먼저 고정한다
- `READY / PROBE / OBSERVE / BLOCKED`의 의미를 다시 적는다
- `display_ready`와 `entry_ready`의 의미 차이를 문서화한다
- late block이 들어왔을 때 어떤 stage로 떨어져야 하는지 표로 정리한다

### 5-3. 코드 구조 정리

- 공용 resolver를 새 helper 또는 적절한 owner 위치에 만든다
- `entry_service.py`가 이 resolver를 사용하도록 바꾼다
- `entry_try_open_entry.py`도 같은 resolver를 사용하게 만든다
- 중복 policy set을 제거한다

### 5-4. BLOCKED 표면화

- chart에서 `BLOCKED`를 `WAIT`와 구분하는 표현 규칙을 결정한다
- 가능하면 `BUY_BLOCKED` / `SELL_BLOCKED` 같은 별도 event family를 검토한다
- 별도 event family가 부담이면 최소한 `blocked_reason_class`를 보존한다

### 5-5. 저장/전파 정리

- row에 쓰는 값과 latest signal에 쓰는 값이 공용 resolver 결과를 그대로 사용하게 한다
- runtime/latest/chart 경로가 서로 다른 rule table을 갖지 않게 한다

### 5-6. 테스트 보강

- initial READY 후 late block
- hard block
- soft block
- probe blocked
- observe candidate
- symbol-specific blocked relief
- chart에서 `BLOCKED`가 `OBSERVE`와 구분되는지


## 6. 완료 기준

- `entry_service`와 `entry_try_open_entry`가 stage/display 정책을 따로 갖지 않는다
- 같은 입력에서 row/runtime/chart가 같은 truth를 본다
- `BLOCKED`와 `OBSERVE`를 운영 표면에서 구분할 수 있다
- recent wrong READY 회귀 케이스가 unit test로 고정된다


## 7. 건드리면 안 되는 것

- ObserveConfirm identity owner 자체를 다시 열지 말 것
- chart에서만 임시 보정하는 식으로 문제를 덮지 말 것
- symbol tuning을 더 늘려서 임시 해결하려 하지 말 것


## 8. 권장 테스트 명령

- `pytest tests/unit/test_entry_service_guards.py -k "energy_soft_block or layer_mode_policy_hard_block or probe_not_promoted" -q`
- `pytest tests/unit/test_chart_painter.py -k "prefers_consumer_check_ready_state or downgrades_soft_blocked_sell_ready_into_sell_wait" -q`
- 필요 시 `pytest tests/unit/test_trading_application_runtime_status.py -q`


## 9. Phase 종료 후 확인 포인트

- 최근 `entry_decisions.csv` 200~300행에서 wrong READY가 여전히 0건인지
- `runtime_status.json`의 latest signal이 chart 의미와 어긋나지 않는지
- chart overlay에서 `BLOCKED`와 `OBSERVE`를 분리 인지할 수 있는지
