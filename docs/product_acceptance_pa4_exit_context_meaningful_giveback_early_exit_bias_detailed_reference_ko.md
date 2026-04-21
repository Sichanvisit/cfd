# Product Acceptance PA4 Exit Context Meaningful Giveback Early Exit Bias Detailed Reference

## target family

이번 축의 main target은 아래 family다.

```text
XAU / NAS
+ wait_quality_label=no_wait
+ exit_policy_stage=mid
+ exit_reason=Exit Context
+ peak_profit_at_exit > 1.0
+ giveback_usd > 0.5
```

대표 ticket:

- `XAUUSD 99802294`
- `NAS100 99774778`
- `NAS100 98726456`

공통 해석은 같다.

- 이미 의미 있는 green room이 있었고
- `bad_loss`도 아니며
- `wait`을 탄 것도 아닌데
- final close가 `Exit Context`로 늦게 정리되면서 giveback이 커졌다

즉 PA4에서 이번 축은 `wait 품질`보다 `profit-path late release` 문제다.

## owner

primary owner:

- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

secondary evidence owner:

- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

## design decision

이번엔 baseline seed를 느슨하게 제외하지 않는다.

대신 profit-path utility에 `meaningful_giveback_exit_pressure`를 추가해서,

- `peak_profit_at_exit`가 충분히 컸고
- `giveback`도 충분히 커졌고
- 현재 trade가 아직 `profit > 0`인 상태라면

`hold / wait_exit`보다 `exit_now`를 더 일찍 고르게 만든다.

## boundary

이번 bias는 아래 family에는 일부러 안 건다.

- `xau_lower_edge_to_edge_hold_bias`
- `btc_lower_hold_bias`
- `btc_lower_mid_noise_hold_bias`

이유:

- 이쪽은 PA4 main issue인 `late release`보다
- 기존 PA3/PA4에서 의도적으로 살린 `hold-through-noise` family이기 때문이다.

## expected effect

fresh closed trade가 다시 쌓이면 아래 변화가 기대된다.

- `Exit Context + meaningful peak + giveback`가 `must_release / bad_exit` queue에서 줄어듦
- 일부는 `Lock Exit` 또는 더 이른 `exit_now_best` 쪽으로 당겨짐
- PA4 queue가 `Exit Context non-loss giveback`와 `adverse bad-loss`로 더 또렷하게 분리됨
