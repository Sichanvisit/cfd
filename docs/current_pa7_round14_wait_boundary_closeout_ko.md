# PA7 Round-14 Wait Boundary Closeout

## 목적

PA7 review queue에서 마지막으로 남아 있던 아래 5개 그룹을 한 번에 줄인다.

- `XAUUSD | continuation_hold_surface | RUNNER_CHECK | runner_secured_continuation | ... | WAIT`
  - raw 기준으로는 `mixed_backfill_value_scale_review`
  - normalized preview 기준으로는 `mixed_wait_boundary_review`
- `BTCUSD | follow_through_surface | FIRST_PULLBACK_CHECK | open_loss_protective | ... | WAIT`
- `BTCUSD | protective_exit_surface | LATE_TREND_CHECK | open_loss_protective | ... | WAIT`
- `BTCUSD | continuation_hold_surface | RUNNER_CHECK | active_flat_profit | ... | WAIT`
- `NAS100 | follow_through_surface | FIRST_PULLBACK_CHECK | active_flat_profit | ... | WAIT`

핵심 원칙은 두 가지다.

1. XAU backfill 그룹은 raw `current_profit` scale을 직접 근거로 patch하지 않는다.
2. 남은 BTC/NAS 그룹은 broad rule이 아니라 `micro WAIT boundary`만 아주 좁게 닫는다.

## 처리 전략

### 1. XAU normalized handoff 처리

resolver에서 다음의 매우 좁은 backfill runner WAIT boundary를 추가한다.

- `symbol = XAUUSD`
- `source in {open_trade_backfill, closed_trade_hold_backfill}`
- `surface = continuation_hold_surface`
- `checkpoint = RUNNER_CHECK`
- `row_family = runner_secured_continuation`
- `runner_secured = true`
- `realized_pnl_state = LOCKED`
- `unrealized_pnl_state = OPEN_LOSS`
- `giveback_ratio <= 0.35`
- `continuation >= reversal + 0.02`
- `hold 0.35~0.39`
- `partial 0.39~0.44`
- `full_exit <= 0.57`

이렇게 하면 raw scale을 쓰지 않고도 XAU backfill 그룹이 `WAIT boundary`로 replay될 수 있다.

## 2. BTC protective micro open-loss WAIT boundary

남은 두 BTC 그룹은 공통 shape를 가진다.

- `source = exit_manage_hold`
- `row_family = open_loss_protective`
- `checkpoint in {FIRST_PULLBACK_CHECK, LATE_TREND_CHECK}`
- `abs(current_profit) <= 0.35`
- `giveback_ratio >= 0.98`
- `hold 0.26~0.34`
- `partial 0.31~0.35`
- `full_exit 0.50~0.67`

이 구간은 `PARTIAL_EXIT/FULL_EXIT`보다 `WAIT`가 hindsight에 더 맞는 `tiny protective loss` 경계로 본다.

## 3. BTC/NAS flat-active micro WAIT boundary

남은 flat-active 2개 그룹은 `FLAT + no runner + tiny balance` 성격이다.

- `source = exit_manage_hold`
- `surface in {follow_through_surface, continuation_hold_surface}`
- `checkpoint in {FIRST_PULLBACK_CHECK, RUNNER_CHECK}`
- `row_family = active_flat_profit`
- `abs(current_profit) <= 0.01`
- `giveback_ratio >= 0.98`
- `hold 0.44~0.46`
- `partial 0.44~0.50`
- `full_exit <= 0.30`
- `continuation >= reversal + 0.18`

이 구간은 `HOLD`보다 `WAIT`가 더 맞는 micro boundary로 본다.

## processor 정리

이전에는 `mixed_backfill_value_scale_review`가 `resolved_by_current_policy`보다 먼저 잡혔다.

round-14에서는 아래 원칙으로 바꾼다.

- `policy_replay_match_rate >= 0.85`
- `policy_replay_action_label == hindsight`

이면 backfill mixed group이라도 먼저 `resolved_by_current_policy`로 내린다.

즉 scale audit은 남기되, 현재 policy replay가 이미 hindsight와 맞으면 계속 top blocker로 들고 있지 않는다.

## 기대 결과

- XAU normalized handoff 1개가 `resolved_by_current_policy`로 내려간다.
- BTC protective mixed WAIT boundary 2개가 줄어든다.
- BTC/NAS active_flat mixed WAIT boundary 2개가 줄어든다.
- PA7 processor summary의 `mixed_wait_boundary_review`와 `mixed_backfill_value_scale_review`가 크게 줄거나 사라진다.

## 검증

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_path_checkpoint_dataset.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_exit_service.py`

## 다음 단계

round-14 이후 남는 그룹이 있다면, rule patch를 더 키우기보다

- `resolved_by_current_policy`
- `confidence_only_confirmed`
- `hydration/baseline gap`

중 어디로 내려갈지 먼저 보고, 그 다음 `PA8 packet semantics` 쪽으로 넘어간다.
