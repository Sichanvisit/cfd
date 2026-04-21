# Product Acceptance PA4 Countertrend No-Green Exit Pressure Detailed Reference

## 목적

`XAU topdown-only Exit Context`처럼

- countertrend entry였고
- green room이 거의 없었고
- 결국 손실로 닫힌

family를 더 빨리 `release/cut` 쪽으로 밀어준다.

## anchor family

- `XAUUSD SELL + Exit Context + TopDown bullish`
- `peak_profit_at_exit ~= 0`
- `wait_quality_label=no_wait`
- `loss_quality_label=bad_loss`

이 family는 `wait이 길었다`기보다 `no-green 상태에서 cut이 충분히 빠르지 않았다`에 가깝다.

## owner

- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)

## 설계

기존 `countertrend_topdown_exit_pressure`는

- adverse
- prefer_fast_cut
- meaningful peak
- meaningful giveback

중 하나가 있어야 켜졌다.

이번 하위축은 그 전 단계, 즉 `no-green countertrend`도 별도 pressure로 잡는다.

조건:

- `countertrend_with_entry=True`
- `topdown_state_label in {BULL_CONFLUENCE, BEAR_CONFLUENCE, TOPDOWN_CONFLICT}`
- `profit < 0`
- `peak_profit <= no_green_max_peak`
- opposite-edge completion / lower-reversal hold bias 아님

효과:

- `utility_exit_now_delta` 증가
- `utility_hold_delta` 감소
- `utility_wait_exit_delta` 감소
