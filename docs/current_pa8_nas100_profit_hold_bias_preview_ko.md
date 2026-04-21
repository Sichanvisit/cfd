# PA8 NAS100 Profit Hold Bias Preview

## Goal

NAS100 action-only review에서 확인된 `continuation_hold_surface + RUNNER_CHECK + profit_hold_bias`
`HOLD -> PARTIAL_THEN_HOLD` blocker를 실제 rule patch 전에 preview로 검증한다.

이번 단계는 resolver를 직접 바꾸지 않고, runtime proxy label 위에 preview action을 덧씌워
hold precision이 실제로 얼마나 개선되는지 본다.

## Scope

- symbol: `NAS100`
- family: `profit_hold_bias`
- surface: `continuation_hold_surface`
- checkpoint_type: `RUNNER_CHECK`
- baseline action: `HOLD`
- preview action: `PARTIAL_THEN_HOLD`

## Preview intent

다음 조건을 만족하는 아주 좁은 row만 preview 대상에 올린다.

- `unrealized_pnl_state = OPEN_PROFIT`
- `giveback_ratio <= 0.05`
- `0.47 <= runtime_hold_quality_score <= 0.54`
- `runtime_partial_exit_ev >= runtime_hold_quality_score + 0.03`
- `runtime_partial_exit_ev <= 0.60`
- `runtime_full_exit_risk <= 0.30`
- `runtime_continuation_odds >= runtime_reversal_odds + 0.20`

## Output

- `checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json`
- `checkpoint_pa8_nas100_profit_hold_bias_preview_latest.md`

## Success criteria

- preview changed rows가 실제 하나의 narrow family로 모인다
- `worsened_row_count = 0`
- `preview_hold_precision >= 0.80`
- `preview_runtime_proxy_match_rate > baseline_runtime_proxy_match_rate`

## Non-goals

- resolver live patch
- scene bias 반영
- BTC/XAU 동시 확장
