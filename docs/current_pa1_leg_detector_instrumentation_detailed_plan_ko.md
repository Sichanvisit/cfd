# Current PA1 Leg Detector Instrumentation Detailed Plan

## 목적

이 문서는 `PA1. Leg Detector Instrumentation`을 실제 구현 단위로 더 잘게 쪼개서,
기존 entry/exit/runtime/learning 흐름과 부딪히지 않게 어떻게 넣을지 고정하기 위한 상세 계획이다.

이번 단계의 목표는 오직 하나다.

> `action`을 바꾸지 않고, runtime row가 가능한 한 안정적으로 같은 `leg_id`를 공유하게 만드는 것

즉 지금은 매매 판단을 고치지 않는다.
`leg_id`, `leg_direction`, `leg_state`, `leg_transition_reason`를 먼저 심고,
그 다음 단계인 `checkpoint segmentation`과 `checkpoint context`가 올라갈 바닥을 만든다.

---

## 이번 단계에서 바꾸는 것

### 1. 신규 서비스

- `backend/services/path_leg_runtime.py`

역할:

- row 기준 방향 힌트 해석
- `assign_leg_id(symbol, runtime_row, symbol_state)` 제공
- active leg 유지 / 새 leg 오픈 / shallow rebuild 유지 규칙 제공
- path leg snapshot 빌드 로직 제공

### 2. 신규 builder

- `scripts/build_path_leg_snapshot.py`

역할:

- `runtime_status.json`
- `entry_decisions.csv`

를 읽어 `path_leg_snapshot_latest.json`을 만든다.

### 3. 최소 연동

- `backend/services/entry_try_open_entry.py`
  - decision payload 생성 직전에 leg assignment 수행
- `backend/services/entry_service.py`
  - runtime latest row sync 대상에 leg 필드 추가
- `backend/services/entry_engines.py`
  - `entry_decisions.csv` 컬럼에 leg 필드 추가
- `backend/services/exit_manage_positions.py`
  - exit manage 루프에서도 현재 latest signal row에 leg 필드가 유지되도록 read-side 보강

---

## 이번 단계에서 바꾸지 않는 것

- `initial_entry_surface` taxonomy
- 실제 entry/exit action resolver
- follow-through / hold / exit score
- checkpoint type 분류
- hindsight label
- dataset export / preview eval / signoff / activation 기준

즉 이번 단계는 **관측 계층 추가**이고, **행동 계층 변경이 아니다**.

---

## 상세 구현 순서

### PA1-A. Leg Assignment Contract 고정

핵심 함수:

- `assign_leg_id(symbol, runtime_row, symbol_state)`
- `close_active_leg(symbol, symbol_state, reason, event_time)`
- `build_path_leg_snapshot(runtime_status, entry_decisions, recent_limit)`

초기 규칙:

- bridge action이 있으면 그것을 최우선 방향 힌트로 사용
- 그 다음은 `breakout_candidate_direction`
- 그 다음은 `action / observe_side / intended_direction`
- active leg가 이미 있고 새 row가 같은 방향이면 같은 `leg_id` 유지
- active leg가 있고 row가 반대 방향이어도, 강한 새 impulse가 아니면 shallow rebuild로 보고 leg를 끊지 않음
- 새 `entered` impulse가 잡히면 새 `leg_id`를 열 수 있음

### PA1-B. Entry Payload Instrumentation

위치:

- `entry_try_open_entry.py`

방법:

- `_decision_payload(...)` 마지막 단계에서 leg assignment 수행
- 생성된 4개 필드를 payload에 직접 삽입
- runtime 내부에 `path_leg_state_by_symbol`을 들고 가되,
  기존 action 결정에는 영향 주지 않음

의도:

- 모든 entry decision row가 csv에 내려가기 전에 leg identity를 함께 갖게 함

### PA1-C. Runtime Latest Row Sync

위치:

- `entry_service.py`
- `entry_engines.py`

방법:

- `ENTRY_DECISION_FULL_COLUMNS`에 leg 필드 추가
- `_append_entry_decision_log`의 scalar sync 목록에 leg 필드 추가

의도:

- `latest_signal_by_symbol`에도 같은 leg identity가 남게 함
- 다음 row assignment가 이전 row의 leg context를 이어받을 수 있게 함

### PA1-D. Exit Read-Side Continuity

위치:

- `exit_manage_positions.py`

방법:

- exit manage loop가 읽는 `latest_signal_row`에도 leg 필드가 비어 있지 않게 보강
- 아직 exit action을 바꾸지 않고, 단지 current active leg를 읽을 수 있게만 유지

의도:

- 이후 `continuation_hold / protective_exit` 단계에서 같은 leg 기준으로 판단할 수 있게 준비

### PA1-E. Snapshot Builder

위치:

- `scripts/build_path_leg_snapshot.py`

산출물:

- `data/analysis/shadow_auto/path_leg_snapshot_latest.json`

포함 내용:

- symbol별 recent row 수
- leg assignment 성공 수
- missing leg row 수 / 비율
- active leg id / direction / state / transition reason

### PA1-F. 테스트

- `tests/unit/test_path_leg_runtime.py`
- `tests/unit/test_build_path_leg_snapshot.py`

최소 검증:

- 같은 leg 안의 연속 row가 같은 `leg_id`를 공유하는가
- full exit 이후 새 impulse가 새 `leg_id`를 여는가
- shallow rebuild가 과도하게 새 leg로 끊기지 않는가
- `BTC / NAS / XAU` snapshot artifact가 모두 만들어지는가

---

## 충돌 방지 규칙

### 1. 기존 학습 파이프라인을 덮어쓰지 않는다

- 기존 dataset 컬럼은 유지
- 기존 eval/signoff/activation 조건은 그대로 둔다
- leg 필드는 이번 단계에서 `entry_decisions.csv`와 `latest_signal_by_symbol`에만 추가

### 2. 기존 wrong-side correction과 경쟁하지 않는다

- leg direction 힌트는 `bridge action`과 `breakout direction`을 우선 사용한다
- 그래서 `wrong-side SELL`이 남아 있어도 leg context는 더 큰 path 방향을 따라갈 수 있다

### 3. exit execution은 아직 건드리지 않는다

- exit manage는 leg를 읽기만 하고, 매매 실행 경로는 그대로 둔다
- 실제 `full exit -> leg close` 자동화는 다음 단계나 bounded adoption 전에 다룬다

---

## 이번 단계의 완료 기준

- `entry_decisions.csv`에 4개 leg 필드가 실제로 기록된다
- `latest_signal_by_symbol`에 4개 leg 필드가 유지된다
- `path_leg_snapshot_latest.json`이 생성된다
- 최근 `BTC / NAS / XAU` row에서 `leg_id` 없는 주요 row 비율이 낮아진다
- 기존 targeted pytest가 깨지지 않는다

---

## 다음 단계로 넘기는 기준

PA1이 닫히면 다음 단계는 `PA2 Checkpoint Segmenter Instrumentation`이다.

즉 다음엔

- 같은 leg를 찾는 것

에서

- 그 leg 안의 어느 지점이 `checkpoint`인지 자르는 것

으로 넘어간다.
