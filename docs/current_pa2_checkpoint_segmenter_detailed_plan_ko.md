# Current PA2 Checkpoint Segmenter Detailed Plan

## 목적

이 문서는 `PA2. Checkpoint Segmenter Instrumentation`을 실제 구현 단위로 내려서,
기존 entry/exit/runtime/learning 흐름과 충돌 없이 넣기 위한 상세 계획이다.

이번 단계의 목표는 아래 한 줄이다.

> 같은 `leg` 안에서 모든 row를 새 checkpoint로 자르지 않고,
> `지금 다시 판단해야 할 순간`만 `checkpoint_type`으로 안정적으로 표기하기

즉 지금은 아직

- score 계산
- best action 선택
- hold / partial / full / rebuy 실행

을 바꾸지 않는다.

`checkpoint_id`, `checkpoint_type`, `checkpoint_index_in_leg`, `checkpoint_transition_reason`
만 먼저 심어서, 다음 단계인 `checkpoint context / storage / scoring`이 올라갈 바닥을 만든다.

---

## 이번 단계에서 바꾸는 것

### 1. 신규 서비스

- `backend/services/path_checkpoint_segmenter.py`

역할:

- `classify_checkpoint_type(leg_ctx, runtime_row)` 제공
- `assign_checkpoint_context(symbol, runtime_row, symbol_state)` 제공
- 같은 phase면 같은 `checkpoint_id` 유지
- phase가 바뀌면 새 `checkpoint_id`를 열기
- checkpoint distribution artifact 빌드 로직 제공

### 2. 신규 builder

- `scripts/build_checkpoint_distribution.py`

역할:

- `runtime_status.json`
- `entry_decisions.csv`

를 읽어 `checkpoint_distribution_latest.json`을 만든다.

### 3. 최소 연동

- `backend/services/entry_try_open_entry.py`
  - decision payload 생성 직전에 checkpoint assignment 수행
- `backend/services/entry_service.py`
  - runtime latest row sync 대상에 checkpoint 필드 추가
- `backend/services/entry_engines.py`
  - `entry_decisions.csv` 컬럼에 checkpoint 필드 추가
- `backend/services/exit_manage_positions.py`
  - exit manage loop에서도 active checkpoint를 읽을 수 있게 read-side 보강

---

## 이번 단계에서 바꾸지 않는 것

- `initial_entry_surface` taxonomy
- actual entry / exit execution
- checkpoint context full row storage
- hindsight labeling
- management score
- best action resolver
- dataset export / preview eval / signoff / activation 기준

즉 이번 단계는 **checkpoint 분류 계층 추가**이고, **행동 계층 변경이 아니다**.

---

## v1 checkpoint taxonomy

이번 단계는 아래 5개만 쓴다.

- `INITIAL_PUSH`
- `FIRST_PULLBACK_CHECK`
- `RECLAIM_CHECK`
- `LATE_TREND_CHECK`
- `RUNNER_CHECK`

이 다섯 개를 먼저 안정적으로 찍는 것이 목표다.

---

## 상세 구현 순서

### PA2-A. Checkpoint Contract 고정

핵심 함수:

- `classify_checkpoint_type(leg_ctx, runtime_row)`
- `assign_checkpoint_context(symbol, runtime_row, symbol_state)`
- `build_checkpoint_distribution(runtime_status, entry_decisions, recent_limit)`

초기 규칙:

- `leg_id`가 바뀌면 checkpoint도 새로 연다
- `leg_row_count <= 2`면 `INITIAL_PUSH`
- 초기 구간에서 반대 압력이 보이면 `FIRST_PULLBACK_CHECK`
- bridge / reclaim signal이 보이면 `RECLAIM_CHECK`
- leg가 충분히 오래 지속되면 `LATE_TREND_CHECK`
- 너무 빨리 열리지 않게 guard를 둔 뒤 `RUNNER_CHECK`

### PA2-B. 과분할 방지 규칙

checkpoint는 row마다 새로 만들지 않는다.

핵심 원칙:

- 같은 phase면 같은 `checkpoint_id` 유지
- phase progression이 명확할 때만 새 checkpoint 생성
- `FIRST_PULLBACK_CHECK -> RECLAIM_CHECK -> LATE_TREND_CHECK -> RUNNER_CHECK`
  처럼 단조 progression을 기본으로 한다
- shallow rebuild는 기존 checkpoint 유지 쪽으로 본다

즉 PA2의 본질은

`분류`

만큼이나

`과분할 방지`

이다.

### PA2-C. Entry Payload Instrumentation

위치:

- `entry_try_open_entry.py`

방법:

- PA1에서 붙인 leg fields 직후 checkpoint assignment 수행
- 생성된 checkpoint 필드를 payload에 직접 삽입
- runtime 내부에 `path_checkpoint_state_by_symbol`을 유지

의도:

- 모든 entry decision row가 csv에 내려가기 전에 checkpoint identity를 함께 갖게 함

### PA2-D. Runtime Latest Row Sync

위치:

- `entry_service.py`
- `entry_engines.py`

방법:

- `ENTRY_DECISION_FULL_COLUMNS`에 checkpoint 필드 추가
- `_append_entry_decision_log`의 scalar sync 목록에 checkpoint 필드 추가

의도:

- `latest_signal_by_symbol`에도 checkpoint identity가 남게 함
- 다음 row segmentation이 이전 checkpoint context를 이어받을 수 있게 함

### PA2-E. Exit Read-Side Continuity

위치:

- `exit_manage_positions.py`

방법:

- exit manage loop가 읽는 `latest_signal_row`에도 checkpoint 필드가 비어 있지 않게 보강
- 아직 exit action은 바꾸지 않고, current active checkpoint를 읽을 수 있게만 유지

의도:

- 이후 `continuation_hold / protective_exit` 단계에서 같은 checkpoint 기준으로 score를 붙일 수 있게 준비

### PA2-F. Distribution Builder

위치:

- `scripts/build_checkpoint_distribution.py`

산출물:

- `data/analysis/shadow_auto/checkpoint_distribution_latest.json`

포함 내용:

- symbol별 checkpoint type 분포
- active checkpoint id / type / index
- checkpoint_count
- new_checkpoint_share

### PA2-G. 테스트

- `tests/unit/test_path_checkpoint_segmenter.py`
- `tests/unit/test_build_checkpoint_distribution.py`

최소 검증:

- 같은 phase의 연속 row가 같은 `checkpoint_id`를 공유하는가
- `INITIAL_PUSH -> FIRST_PULLBACK_CHECK -> RECLAIM_CHECK` progression이 나오는가
- `RUNNER_CHECK`가 너무 이르게 열리지 않는가
- `BTC / NAS / XAU` distribution artifact가 만들어지는가

---

## 충돌 방지 규칙

### 1. 기존 학습 파이프라인을 덮어쓰지 않는다

- 기존 dataset 컬럼은 유지
- checkpoint 필드는 이번 단계에서 `entry_decisions.csv`와 `latest_signal_by_symbol`에만 추가
- checkpoint full row storage는 PA3로 미룬다

### 2. 기존 P0 / bridge / breakout 로직과 경쟁하지 않는다

- checkpoint 분류는 기존 action을 바꾸지 않는다
- bridge / breakout / observe 신호는 segmentation evidence로만 사용한다

### 3. exit execution은 아직 건드리지 않는다

- exit manage는 checkpoint를 읽기만 하고, 실제 매매 실행 경로는 그대로 둔다

---

## 이번 단계의 완료 기준

- `entry_decisions.csv`에 checkpoint 필드가 기록된다
- `latest_signal_by_symbol`에 checkpoint 필드가 유지된다
- `checkpoint_distribution_latest.json`이 생성된다
- checkpoint가 row마다 과도하게 새로 열리지 않는다
- 기존 targeted pytest가 깨지지 않는다

---

## 다음 단계로 넘기는 기준

PA2가 닫히면 다음 단계는 `PA3 Checkpoint Context Builder / Storage`다.

즉 다음엔

- 같은 leg 안의 어떤 순간이 checkpoint인지 자르는 것

에서

- 그 checkpoint를 학습 가능한 row schema로 저장하는 것

으로 넘어간다.
