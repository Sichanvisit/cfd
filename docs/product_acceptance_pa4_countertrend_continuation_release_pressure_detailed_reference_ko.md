# Product Acceptance PA4 Countertrend Continuation Release Pressure Detailed Reference

## target

- `must_release 8`의 핵심 family
  - `structure_exit_context 6`
  - `xau_topdown_only_exit_context 1`
  - `generic_exit_context 1`

## representative tickets

- `99774778` `NAS100` `SELL`
- `98726456` `NAS100` `BUY`
- `96732774` `NAS100` `SELL`
- `99802294` `XAUUSD` `SELL`

## interpretation

- 공통 특징
  - `wait_quality_label=no_wait`
  - `decision_reason=exit_now_best`
  - `giveback_usd > 0.5`
  - `peak_profit_at_exit`는 의미 있게 있었음
- 즉 label 과대추정보다
  - 반대 continuation / opposite structure 완성 시점에서
  - runtime이 `release`를 더 빨리 밀어야 하는 family로 해석

## owner

- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

## intended effect

- `countertrend_with_entry + topdown continuation + meaningful giveback`
- 이 조합에 대해 `exit_now` utility를 추가로 올림
- future close에서 `must_release`가 줄어들도록 유도
