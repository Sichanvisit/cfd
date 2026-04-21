# Current PA3 Checkpoint Context Storage Detailed Plan

## 목적

이 문서는 `PA3. Checkpoint Context Builder / Storage`를 실제 구현 단위로 내려서,
기존 entry/exit/runtime/learning 흐름과 충돌 없이 넣기 위한 상세 계획이다.

이번 단계의 목표는 아래 한 줄이다.

> `leg`와 `checkpoint`를 찾는 데서 멈추지 않고,
> 각 checkpoint를 실제 학습 가능한 row schema로 저장하기

즉 지금은 아직

- management score 계산
- hindsight best action label
- runtime action 변경

을 건드리지 않는다.

대신 아래를 먼저 고정한다.

- checkpoint row schema
- runtime storage 경로
- entry / exit에서 공통으로 row를 쌓는 방식

---

## 이번 단계에서 바꾸는 것

### 1. 신규 서비스

- `backend/services/path_checkpoint_context.py`

역할:

- `build_checkpoint_context(...)`
- `build_flat_position_state()`
- `build_exit_position_state(...)`
- `record_checkpoint_context(...)`
- `build_checkpoint_context_snapshot(...)`

를 제공한다.

### 2. 신규 builder

- `scripts/build_checkpoint_context_snapshot.py`

역할:

- `runtime_status.json`
- `data/runtime/checkpoint_rows.csv`

를 읽어 `checkpoint_context_snapshot_latest.json`을 만든다.

### 3. 신규 runtime storage

- `data/runtime/checkpoint_rows.csv`
- `data/runtime/checkpoint_rows.detail.jsonl`

역할:

- csv는 hot row 저장
- jsonl은 detail payload 저장

### 4. 최소 연동

- `backend/services/entry_try_open_entry.py`
  - FLAT position 기준 checkpoint row 저장
- `backend/services/exit_manage_positions.py`
  - 실제 open position 기준 checkpoint row 저장

---

## 이번 단계에서 바꾸지 않는 것

- entry/exit execution action
- PA4 score
- PA5 hindsight label
- dataset export / preview eval / signoff / activation 기준

즉 이번 단계는 **checkpoint row 저장 계층 추가**이고, **행동 계층 변경이 아니다**.

---

## PA3 최소 row schema

이번 단계에서 저장할 최소 필드는 아래다.

- `generated_at`
- `source`
- `symbol`
- `surface_name`
- `leg_id`
- `leg_direction`
- `checkpoint_id`
- `checkpoint_type`
- `checkpoint_index_in_leg`
- `checkpoint_transition_reason`
- `bars_since_leg_start`
- `bars_since_last_push`
- `bars_since_last_checkpoint`
- `position_side`
- `position_size_fraction`
- `avg_entry_price`
- `realized_pnl_state`
- `unrealized_pnl_state`
- `runner_secured`
- `mfe_since_entry`
- `mae_since_entry`
- `current_profit`

---

## 상세 구현 순서

### PA3-A. Context Contract 고정

핵심 함수:

- `build_checkpoint_context(...)`
- `append_checkpoint_context_row(...)`
- `record_checkpoint_context(...)`
- `build_checkpoint_context_snapshot(...)`

초기 원칙:

- entry row는 `FLAT` position state로 저장
- exit row는 실제 position state로 저장
- entry_decisions.csv를 덮어쓰지 않고, 별도 runtime storage에 저장

### PA3-B. Position State 분리

entry용:

- `build_flat_position_state()`

exit용:

- `build_exit_position_state(...)`

핵심:

- `position_side`
- `position_size_fraction`
- `avg_entry_price`
- `realized_pnl_state`
- `unrealized_pnl_state`
- `runner_secured`
- `mfe_since_entry`
- `mae_since_entry`

를 checkpoint row에 직접 넣는다.

### PA3-C. Entry Runtime Storage

위치:

- `entry_try_open_entry.py`

방법:

- PA2까지 계산된 `leg / checkpoint` 위에
  `FLAT` position state를 얹어 checkpoint row 생성
- row를 `checkpoint_rows.csv`와 `checkpoint_rows.detail.jsonl`에 append
- runtime latest row에는 scalar 요약만 반영

의도:

- entry/follow-through 성격의 checkpoint row를 먼저 축적

### PA3-D. Exit Runtime Storage

위치:

- `exit_manage_positions.py`

방법:

- 현재 포지션의
  `direction / lot / entry_price / profit / peak_profit / partial_done / be_moved`
  기준으로 position state 생성
- checkpoint row 생성 후 같은 storage에 append

의도:

- continuation_hold / protective_exit 성격의 checkpoint row 축적

### PA3-E. Snapshot Builder

위치:

- `scripts/build_checkpoint_context_snapshot.py`

산출물:

- `data/analysis/shadow_auto/checkpoint_context_snapshot_latest.json`

포함 내용:

- symbol별 row 수
- source 분포
- surface 분포
- checkpoint type 분포
- runner secured 수
- open profit / open loss row 수

### PA3-F. 테스트

- `tests/unit/test_path_checkpoint_context.py`
- `tests/unit/test_build_checkpoint_context_snapshot.py`

최소 검증:

- entry row가 `FLAT` 상태로 context row를 만드는가
- exit row가 `OPEN_PROFIT / runner_secured` 같은 position state를 반영하는가
- csv / detail jsonl이 실제로 써지는가
- snapshot artifact가 market-family 기준으로 만들어지는가

---

## 충돌 방지 규칙

### 1. 기존 entry_decisions.csv 스키마를 더 넓히지 않는다

PA3의 full context는 별도 runtime storage로 보낸다.

### 2. runtime latest row에는 scalar만 반영한다

복잡한 nested payload는 `checkpoint_rows.detail.jsonl`로 보내고,
runtime latest row는 스칼라 요약만 유지한다.

### 3. 기존 learning artifact를 덮어쓰지 않는다

- 기존 preview dataset
- 기존 eval/signoff/activation

과 직접 연결하지 않는다.

---

## 이번 단계의 완료 기준

- `checkpoint_rows.csv`가 실제로 생성된다
- `checkpoint_rows.detail.jsonl`가 실제로 생성된다
- entry / exit 양쪽에서 row가 append된다
- `checkpoint_context_snapshot_latest.json`이 생성된다
- 기존 targeted pytest가 깨지지 않는다

---

## 다음 단계로 넘기는 기준

PA3가 닫히면 다음 단계는 `PA4 Passive Score Calculation`이다.

즉 다음엔

- checkpoint를 저장하는 것

에서

- 각 checkpoint마다 continuation / reversal / hold / partial / full / rebuy score를 계산하는 것

으로 넘어간다.
