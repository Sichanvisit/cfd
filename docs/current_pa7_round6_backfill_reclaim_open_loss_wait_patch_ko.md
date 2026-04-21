# PA7 Round-6 Backfill Reclaim Open-Loss WAIT Patch

## 목적

PA7 review processor의 새 top group인
`BTCUSD / continuation_hold_surface / RECLAIM_CHECK / active_open_loss / HOLD -> hindsight WAIT`
불일치를 줄인다.

이번 그룹은:

- `source = open_trade_backfill`
- `surface_name = continuation_hold_surface`
- `checkpoint_type = RECLAIM_CHECK`
- `management_row_family = active_open_loss`
- `continuation`이 매우 강하고
- `hold_quality`가 높고
- `partial_exit/full_exit`는 강하지 않은데
- hindsight는 `WAIT`

인 좁은 reclaim retest 케이스였다.

## 이번 패치

`path_checkpoint_action_resolver.py`에
아래 조건의 backfill reclaim open-loss WAIT retest 예외를 추가한다.

- `source == "open_trade_backfill"`
- `surface_name == "continuation_hold_surface"`
- `checkpoint_type == "RECLAIM_CHECK"`
- `management_row_family == "active_open_loss"`
- `current_profit < 0`
- `continuation >= reversal + 0.20`
- `hold_score >= 0.52`
- `partial_score <= 0.36`
- `full_exit_score <= 0.40`

결과:

- `management_action_label = WAIT`
- `management_action_reason = backfill_reclaim_open_loss_wait_retest`

## 의도

이 규칙은 일반 open-loss row를 WAIT로 넓히는 것이 아니다.
오직:

- backfill
- reclaim
- continuation이 매우 강한 open-loss

만 trim/HOLD 대신 WAIT로 다시 두는 좁은 예외다.

## 기대 효과

- BTC backfill reclaim active_open_loss mismatch 축소
- PA7 queue가 synthetic/backfill mismatch를 더 걷어낸 뒤
  실제 live policy 경계 쪽으로 더 빨리 이동

## 검증

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_exit_service.py`
