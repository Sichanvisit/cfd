# PA7 Round-9 Singleton Resolution And Flat WAIT Boundary Patch

## 목적

`PA7 review queue` 상단에 남아 있던 두 종류의 잔여 그룹을 줄인다.

- 현재 policy replay가 이미 hindsight와 맞는 singleton group
- `active_flat_profit` late row인데 아직 `HOLD/FULL_EXIT`로 남는 `WAIT` 경계

## 패치 1: singleton resolved-by-current-policy

기존 processor는 `policy_replay_match_rate >= 0.85`여도 `row_count >= 2`일 때만
`resolved_by_current_policy`로 분류했다.

이 때문에 아래 같은 케이스가 계속 top review에 남았다.

- baseline: `PARTIAL_THEN_HOLD`
- current policy replay: `PARTIAL_EXIT`
- hindsight: `PARTIAL_EXIT`
- row_count = 1

이번 round에서는 `row_count == 1`이어도 `policy_replay_match_rate == 1.0`이면
`resolved_by_current_policy`로 내린다.

## 패치 2: flat late WAIT boundary

현재 `active_flat_profit` 내에서는 아래 두 케이스가 남아 있었다.

1. late flat active-position/wait-bias row인데 사실상 `WAIT`가 더 맞는 경우
2. flat runner-check row인데 `FULL_EXIT`가 과하게 남는 경우

이번 round에서는 아래처럼 아주 좁은 `WAIT` retest를 추가한다.

### 2-1. flat_late_wait_bias_wait_retest

- `source in {open_trade_backfill, exit_manage_hold}`
- `surface_name = continuation_hold_surface`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `row_family in {active_position, wait_bias}`
- `current_profit ~= 0`
- `giveback_ratio <= 0.05`
- `0.39 <= hold_score <= 0.50`
- `partial_score <= 0.36`
- `full_exit_score <= 0.24`

### 2-2. flat_backfill_wait_bias_wait_retest

- `source in {open_trade_backfill, exit_manage_hold}`
- `surface_name = continuation_hold_surface`
- `checkpoint_type = RUNNER_CHECK`
- `row_family in {active_position, wait_bias}`
- `current_profit ~= 0`
- `giveback_ratio <= 0.05`
- `hold_score <= 0.22`
- `partial_score <= 0.40`
- `0.40 <= full_exit_score <= 0.60`
- `reversal >= continuation + 0.30`
- `gap <= 0.20`

## 기대 효과

- current policy가 이미 맞춘 singleton group을 top review에서 제거
- `flat late WAIT` 케이스를 `PA7` queue 상단에서 줄임
- 다음 round를 `profit_hold_bias / runner_secured_continuation trim boundary` 쪽으로 더 선명하게 이동
