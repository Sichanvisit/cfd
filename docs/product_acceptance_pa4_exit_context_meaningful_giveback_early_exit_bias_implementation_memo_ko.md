# Product Acceptance PA4 Exit Context Meaningful Giveback Early Exit Bias Implementation Memo

## what changed

이번 PA4-2에서는 `Exit Context + meaningful peak + giveback` family를 future close 기준으로 더 빨리 정리하도록 bias를 넣었다.

수정 파일:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py)
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)

새 flag:

- `meaningful_giveback_exit_pressure`

핵심 동작:

- `profit > 0`
- `peak_profit_at_exit >= 1.0`
- `giveback`가 절대값/비율 경계를 넘음
- `state in {ACTIVE, GREEN_CLOSE, NONE}`

이면 `utility_exit_now`를 올리고 `utility_hold / utility_wait_exit`를 내린다.

## regression

검증 결과:

- `pytest -q tests/unit/test_exit_utility_scene_bias_policy.py` -> `4 passed`
- `pytest -q tests/unit/test_wait_engine.py` -> `46 passed`

## refreeze

기준:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

현재 refreeze는 즉시 숫자를 줄이진 않았다.

- `must_release = 10`
- `bad_exit = 10`

이건 구현 실패라기보다, closed history는 이미 확정된 과거 artifact라서 새 bias가 fresh close에 반영되어야 변화가 보이는 구조다.

## interpretation

이번 패치로 PA4 queue는 더 깔끔하게 두 층으로 나뉜다.

1. `Exit Context + meaningful peak + giveback`
2. `Protect Exit / Adverse Stop + hard_guard=adverse + bad_loss`

즉 다음 실전 확인 포인트는 fresh close row가 추가된 뒤,

- `XAUUSD 99802294`
- `NAS100 99774778`
- `NAS100 98726456`

같은 family가 더 이상 top release/bad-exit seed로 남는지 보는 것이다.
