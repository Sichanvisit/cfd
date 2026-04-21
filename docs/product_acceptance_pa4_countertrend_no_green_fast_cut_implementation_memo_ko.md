# PA4 Countertrend No-Green Fast-Cut Implementation Memo

## 구현 요약

이번 축은 `TopDown-only Exit Context` 잔여 4건 중 실제로 runtime에서 다시 만들 가능성이 큰 `no-green countertrend loss` family를 대상으로 recovery wait을 끄는 패치다.

반영 파일:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_utility_bundle.py)
- [test_exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_recovery_utility_bundle.py)

회귀:

- `pytest -q tests/unit/test_exit_recovery_utility_bundle.py` -> `3 passed`
- `pytest -q tests/unit/test_wait_engine.py` -> `46 passed`

runtime:

- [cfd_main_restart_20260401_211653.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_211653.out.log)
- [cfd_main_restart_20260401_211653.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_211653.err.log)

## 핵심 포인트

- `countertrend_with_entry + no_green_peak`이면 `wait_be / wait_tp1`를 disable
- disable reason은 `countertrend_no_green_fast_cut`
- lower-edge hold bias에는 적용하지 않음

## 최신 상태

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T21:17:22`

exit summary:

- `must_hold = 0`
- `must_release = 10`
- `bad_exit = 10`

가 그대로다.

즉 이번 축은 `구현 완료 + runtime 반영 완료 + future close 대기` 상태다.

## 남은 family 구성

- `exit_context_topdown_only = 4`
- `protect_exit_adverse = 2`
- `adverse_stop_adverse = 1`
- `exit_context_bullish_flow = 1`
- `exit_context_bearish_flow = 1`
- `exit_context_other = 1`
