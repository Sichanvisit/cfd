# Current Exit Manage Position-Side Checkpoint Enrichment Detailed Plan

## 목적

이 문서는 PA5/PA6 다음 단계에서 왜 `exit_manage` checkpoint 기록 시점을 바꾸는지 고정하기 위한 상세 메모다.

핵심 목적은 아래 한 줄이다.

> `exit_manage`가 실제 포지션 운영이 끝난 뒤의 상태를 checkpoint row로 남기게 해서,
> `open_profit / open_loss / runner_secured` row가 학습 경로에 더 잘 쌓이게 만든다.

---

## 기존 문제

기존 구현은 `manage_positions(...)` 루프 안에서

- leg assignment
- checkpoint assignment
- checkpoint context 기록

을 비교적 이른 시점에 수행했다.

즉 아직 아래가 반영되기 전이었다.

- `partial_done`
- `be_moved`
- `runner_preservation`
- final managed-exit selection
- final hold/wait/protective branch

그래서 실제로는 runner가 보존되었어도,
checkpoint row에는 그 흔적이 약하게 남거나 아예 빠지는 경우가 있었다.

---

## 이번 보강의 원리

### 1. early snapshot보다 final-stage snapshot을 우선한다

이번 변경에서는 loop 중간의 조기 기록보다,
최종 branch 직전의 checkpoint 기록을 더 중요하게 본다.

즉 다음과 같이 바뀐다.

- 기존: “판단 도중 상태”
- 변경 후: “이번 loop에서 최종적으로 어떤 운영 판단에 도달했는지”

### 2. 같은 checkpoint id 위에 richer position state를 남긴다

이 변경은 checkpoint segmentation 자체를 바꾸는 작업이 아니다.

- leg id
- checkpoint id
- checkpoint type

은 그대로 유지하고,
같은 checkpoint 위에 더 풍부한 `position_state`를 남긴다.

### 3. runner / hold / protective / managed-exit를 source로 분리한다

새 row source 예:

- `exit_manage_hold`
- `exit_manage_runner`
- `exit_manage_recovery`
- `exit_manage_protective`
- `exit_manage_managed_exit`

이렇게 source를 나누면 later harvest/eval에서
어떤 운영 단계의 row인지 다시 읽기 쉬워진다.

---

## 구현 포인트

### 신규 helper

`backend/services/exit_manage_positions.py`

- `_ensure_exit_checkpoint_assignment(...)`
- `_build_exit_checkpoint_runtime_row(...)`
- `_record_exit_manage_checkpoint(...)`

### 변경 방향

- path leg / checkpoint assignment는 한 번만 안정적으로 만든다
- checkpoint row append는 최종 branch 직전에 수행한다
- `record_checkpoint_context(...)`가 runtime prefixed fields를 쓴 뒤,
  다시 raw latest row로 덮어쓰지 않게 한다

---

## 기대 효과

이번 보강 이후에는 future live rows에서 아래가 더 잘 쌓인다.

- 실제 `OPEN_PROFIT` hold row
- 실제 `OPEN_LOSS` protective row
- `runner_secured = true` row
- managed exit 직전 full-exit candidate row

즉 PA5 hindsight가 `WAIT` 밖으로 퍼질 수 있는 재료가 더 잘 들어오기 시작한다.

---

## backfill 보조 보강

실 live row가 충분히 쌓이기 전까지는,
`open_trades` backfill도 약간 더 똑똑하게 읽는다.

현재 보조 규칙:

- `profit == 0`이어도 `shock_at_profit`이 있으면 fallback profit으로 사용
- `exit_wait_decision_family / exit_wait_bridge_status`가 runner 성격이면
  runner flags를 보수적으로 추론

이건 live row를 대체하는 게 아니라,
transition 기간의 sparse-data 완화용이다.

---

## 완료 기준

- `exit_manage` 최종 branch에서 checkpoint row가 기록된다
- `runner_preserved` 상황이 `runner_secured` row로 남는다
- `open_profit / open_loss`가 checkpoint dataset에 더 잘 반영된다
- PA5 dataset/eval 재실행 시 `position_side_row_count`가 유지되거나 증가한다
- 회귀 테스트가 통과한다
