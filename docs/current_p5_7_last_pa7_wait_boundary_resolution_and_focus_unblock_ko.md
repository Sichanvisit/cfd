# P5-7 마지막 PA7 WAIT 경계 정리 및 Focus Unblock

## 목적

남아 있던 마지막 `PA7 narrow review` 1건을 broad patch 없이 초협소 규칙으로 정리하고,
`first symbol closeout/handoff` 관찰축의 실제 blocker를 `PA7 backlog`에서 `PA8 live window pending`으로 되돌린다.

## 배경

직전 상태는 아래와 같았다.

- `pa7_narrow_review_status = REVIEW_NEEDED`
- `pa7_narrow_review_group_count = 1`
- primary group
  - `BTCUSD | follow_through_surface | INITIAL_PUSH | active_open_loss | active_open_loss | WAIT`
- `first_symbol_closeout_handoff_status = WATCHLIST`
- 상단 board blocker가 여전히 `pa7_review_backlog`

문제는 raw `pa78 unresolved count`가 아니라,
`INITIAL_PUSH / active_open_loss / HOLD vs WAIT` 경계가 마지막으로 남아 있었다는 점이었다.

## 관찰 결과

실제 dataset row를 다시 확인하면 이 cluster는 아래 성격을 가졌다.

- `source = exit_manage_hold`
- `surface_name = follow_through_surface`
- `checkpoint_type = INITIAL_PUSH`
- `row_family = active_open_loss`
- `giveback_ratio ~= 0.99`
- `current_profit < 0`
- `continuation >> reversal`
- 하지만 `hold_score`는 `0.45`대에 머물고
- `partial/full_exit`도 강하지 않아
- runtime은 `HOLD`로 남지만 hindsight는 `WAIT`로 수렴하던 micro boundary였다.

즉 이건 방향 반전 문제가 아니라,
`INITIAL_PUSH`의 초반 active open loss에서 `HOLD`가 과민하게 남는 매우 좁은 WAIT 경계였다.

## 적용 원칙

이번 정리는 아래 원칙으로 제한했다.

- broad rule 금지
- symbol-wide patch 금지
- `INITIAL_PUSH + follow_through_surface + active_open_loss`에만 한정
- `giveback 0.98+`, `hold 0.44~0.47`, `partial <= 0.34`, `full_exit <= 0.42`, `gap <= 0.12`
  수준의 micro boundary에만 적용
- effect는 `HOLD -> WAIT` 한 칸 완화만 허용

## 구현

### 1. Resolver micro rule 추가

파일:

- `backend/services/path_checkpoint_action_resolver.py`

새 reason:

- `initial_push_active_open_loss_wait_boundary_retest`

조건:

- `source == exit_manage_hold`
- `surface_name == follow_through_surface`
- `checkpoint_type == INITIAL_PUSH`
- `row_family == active_open_loss`
- `current_profit < 0`
- `giveback_ratio >= 0.98`
- `continuation >= reversal + 0.30`
- `0.44 <= hold_score <= 0.47`
- `partial_score <= 0.34`
- `full_exit_score <= 0.42`
- `gap <= 0.12`

결과:

- `management_action_label = WAIT`

### 2. PA7 processor end-to-end 검증 추가

파일:

- `tests/unit/test_path_checkpoint_pa7_review_processor.py`

검증 내용:

- 위 micro boundary에 해당하는 `HOLD -> WAIT` 혼합 cluster 6건을 주면
- policy replay가 전부 `WAIT`로 재수렴하고
- group disposition이 `resolved_by_current_policy`로 바뀌는지 확인

### 3. Master board blocker 우선순위 보정

파일:

- `backend/services/checkpoint_improvement_master_board.py`

보정 내용:

- 이제 상단 `blocking_reason`은 raw `pa78 unresolved count`보다
  `pa7_narrow_review_status / pa7_narrow_review_group_count`를 더 신뢰한다
- 그래서 narrow lane이 `CLEAR`면
  blocker는 더 이상 `pa7_review_backlog`가 아니라
  실제 blocker인 `pa8_live_window_pending`으로 넘어간다

## 검증 결과

테스트:

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_checkpoint_improvement_master_board_p5.py`

결과:

- `54 passed`

실 artifact 기준 결과:

- `checkpoint_pa7_review_processor_latest.json`
  - `review_disposition_counts.resolved_by_current_policy = 12`
  - `mixed_wait_boundary_review = 0`
- `checkpoint_improvement_pa7_narrow_review_latest.json`
  - `status = CLEAR`
  - `group_count = 0`
- `checkpoint_improvement_master_board_latest.json`
  - `blocking_reason = pa8_live_window_pending`
  - `pa7_narrow_review_status = CLEAR`
  - `pa7_narrow_review_group_count = 0`
- `checkpoint_improvement_first_symbol_focus_latest.json`
  - `symbol = BTCUSD`
  - `status = WATCHLIST`
  - `blocking_reason = pa8_live_window_pending`

## 해석

이제 `P5` 승격축에서 PA7의 마지막 좁은 경계는 정리됐다.

현재 남은 실제 blocker는 이것뿐이다.

- `BTCUSD` first symbol closeout focus는 여전히 `WATCHLIST`
- 이유는 `live window row 부족`
- 즉 `WATCHLIST -> CONCENTRATED` 전이는
  이제 `PA7 backlog`가 아니라
  실제 live evidence가 쌓이느냐로만 결정된다

## 다음 단계

이후 흐름은 아래로 고정한다.

1. `BTCUSD WATCHLIST` 유지 관찰
2. `observed_window_row_count` 증가 확인
3. `WATCHLIST -> CONCENTRATED -> READY_FOR_CLOSEOUT_REVIEW` 전이 감시
4. 전이 발생 시 `check/report` surface
5. 그 뒤 `PA8 closeout -> PA9 handoff`
