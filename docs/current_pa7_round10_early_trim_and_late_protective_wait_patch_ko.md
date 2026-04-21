# PA7 Round-10 Early Trim And Late Protective WAIT Patch

## 목적

`PA7 review queue`에 남은 high-priority singleton 3개를 줄인다.

- `NAS FIRST_PULLBACK_CHECK + profit_hold_bias + PARTIAL_THEN_HOLD -> PARTIAL_EXIT`
- `NAS FIRST_PULLBACK_CHECK + runner_secured_continuation + PARTIAL_THEN_HOLD -> PARTIAL_EXIT`
- `XAU protective_exit_surface + LATE_TREND_CHECK + active_open_loss + PARTIAL_EXIT -> WAIT`

## 패치 1: runner_secured_early_trim_bias 완화

기존 early trim bias는 아래 조건이었다.

- `raw_partial_exit_ev >= 0.52`
- `raw_hold_quality <= 0.40`
- `reversal >= continuation + 0.04`
- `partial_then_hold_score <= partial_score + 0.08`

이번 round에서는 마지막 조건만 `+0.10`으로 완화한다.

의도:

- `FIRST_PULLBACK_CHECK`의 early runner trim은 잡고
- 건강한 `PARTIAL_THEN_HOLD`는 그대로 둔다

## 패치 2: profit_hold_micro_trim_bias 추가

아주 작은 이익 상태의 `profit_hold_bias` first pullback에서
`PARTIAL_THEN_HOLD`가 `PARTIAL_EXIT`보다 약간만 높게 계산되는 케이스를 분리한다.

조건:

- `row_family = profit_hold_bias`
- `surface_name = follow_through_surface`
- `checkpoint_type = FIRST_PULLBACK_CHECK`
- `pnl_state = OPEN_PROFIT`
- `current_profit <= 0.05`
- `giveback_ratio <= 0.05`
- `partial_score >= 0.49`
- `hold_score <= 0.42`
- `partial_then_hold_score <= partial_score + 0.03`

행동:

- `PARTIAL_EXIT`
- reason = `profit_hold_micro_trim_bias`

## 패치 3: protective_late_open_loss_wait_retest 추가

late protective loss인데

- full-exit도 강하지 않고
- trim도 확신이 낮고
- reversal/continuation이 비슷하게 맞붙은

애매한 row는 `WAIT`가 더 적절할 수 있다.

조건:

- `surface_name = protective_exit_surface`
- `row_family in {active_open_loss, open_loss_protective}`
- `checkpoint_type = LATE_TREND_CHECK`
- `current_profit < 0`
- `giveback_ratio >= 0.95`
- `abs(continuation - reversal) <= 0.04`
- `hold_score >= 0.30`
- `partial_score >= 0.47`
- `full_exit_score <= 0.50`
- `gap <= 0.02`

행동:

- `WAIT`
- reason = `protective_late_open_loss_wait_retest`

## 기대 효과

- `PA7` top 3 singleton mismatch 축소
- 다음 round를 `mixed_review`와 hydration 잔여 정리 단계로 이동
