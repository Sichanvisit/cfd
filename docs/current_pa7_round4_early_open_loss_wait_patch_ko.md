# PA7 Round-4 Early Open-Loss WAIT Patch

## 목적

PA7 review queue에서 새 top actionable group으로 올라온
`BTCUSD / follow_through_surface / INITIAL_PUSH / active_open_loss / PARTIAL_EXIT -> hindsight WAIT`
불일치를 현재 policy 기준으로 줄인다.

핵심 문제는 초기 follow-through 구간의 손실 row 중 일부가
`PARTIAL_EXIT`로 너무 빨리 내려가고 있다는 점이다.
이 그룹은 실제 통계상:

- continuation이 reversal보다 의미 있게 높고
- hold quality가 partial exit EV보다 높거나 비슷하며
- full-exit risk는 아직 임계 상단이 아니고
- hindsight는 `WAIT`

인 경우가 많았다.

## 이번 패치

`path_checkpoint_action_resolver.py`의
`full_exit_gate_not_met_trim_fallback` 앞에
아래 조건의 좁은 WAIT retest fallback을 추가한다.

- `surface_name == "follow_through_surface"`
- `management_row_family == "active_open_loss"`
- `checkpoint_type == "INITIAL_PUSH"`
- `current_profit < 0`
- `continuation >= reversal + 0.10`
- `hold_score >= max(partial_score + 0.03, 0.34)`
- `full_exit_score <= 0.52`

위 조건을 만족하면:

- `management_action_label = WAIT`
- `management_action_reason = early_open_loss_wait_retest`

## 의도

이 규칙은 모든 open-loss row를 WAIT로 넓히는 것이 아니다.
오직:

- 초기 push 이후
- 구조가 아직 continuation 쪽으로 살아 있고
- trim보다 retest/wait가 더 합리적인 좁은 케이스

만 다시 WAIT로 돌린다.

## 기대 효과

- BTC 초기 active_open_loss mismatch top group 축소
- PA7 processor 기준 top actionable group 재정렬
- early open-loss row에서 불필요한 trim fallback 감소

## 검증

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_exit_service.py`

## 다음 확인 포인트

이 패치 후 processor 상위 그룹이 바뀌면,
다음 타깃은 `XAUUSD / continuation_hold_surface / RUNNER_CHECK / active_position / HOLD -> WAIT`
backfill family를 분리해 보는 것이다.
