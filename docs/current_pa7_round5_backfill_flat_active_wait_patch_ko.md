# PA7 Round-5 Backfill Flat-Active WAIT Patch

## 목적

PA7 review processor의 새 top group으로 올라온
`XAUUSD / continuation_hold_surface / RUNNER_CHECK / active_position / HOLD -> hindsight WAIT`
불일치를 현재 policy 기준으로 줄인다.

이번 그룹은 live runner 관리 mismatch라기보다,
`open_trade_backfill`이 같은 XAU checkpoint를 반복 기록한 flat-active row가
`flat_active_hold_retest`로 HOLD에 남아 있는 케이스였다.

## 관찰

실제 group은:

- `source = open_trade_backfill`
- `checkpoint_type = RUNNER_CHECK`
- `management_row_family = active_position`
- `runner_secured = False`
- `unrealized_pnl_state = FLAT`
- `current_profit = 0`
- `continuation`은 우세하지만
- `hold_quality`는 강한 HOLD까지는 아니고
- `partial_exit`와 `full_exit`도 강하지 않음
- hindsight는 `WAIT`

또한 review queue 기준 row `6`건이지만,
실제 unique checkpoint는 `1`건이었다.

## 이번 패치

`path_checkpoint_action_resolver.py`의 active flat-profit 분기에서
아래 조건이면 `HOLD` 대신 `WAIT`로 둔다.

- `source == "open_trade_backfill"`
- `checkpoint_type == "RUNNER_CHECK"`
- `management_row_family == "active_position"`
- `runner_secured == False`
- `abs(current_profit) <= 0.01`
- `continuation >= reversal + 0.12`
- `hold_score in [0.40, 0.46]`
- `partial_score <= 0.35`
- `full_exit_score <= 0.24`

결과:

- `management_action_label = WAIT`
- `management_action_reason = backfill_flat_active_wait_retest`

## 의도

이 규칙은 일반 live `active_flat_profit` HOLD를 넓게 줄이는 패치가 아니다.
오직:

- backfill synthetic row
- flat active
- non-runner
- ambiguous HOLD

만 `WAIT`로 눌러서 review queue의 synthetic mismatch를 줄인다.

## 기대 효과

- XAU backfill HOLD->WAIT top mismatch 완화
- PA7 queue가 실제 live policy mismatch 쪽으로 더 빨리 이동

## 검증

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_exit_service.py`
