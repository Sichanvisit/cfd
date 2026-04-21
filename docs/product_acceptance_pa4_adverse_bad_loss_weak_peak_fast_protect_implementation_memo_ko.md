# Product Acceptance PA4 Adverse Bad Loss Weak Peak Fast Protect Implementation Memo

## what changed

이번 PA4 main axis에서는 `weak peak adverse bad_loss` family를 더 빨리 정리하도록 경계를 줄였다.

수정 파일:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
- [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py)
- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)

핵심 변화:

- `peak_profit <= ADVERSE_WEAK_PEAK_USD`면 adverse min-hold를 더 짧게 잡는다
- 그 상태에서 `protect_now`가 성립하면 `adverse_weak_peak_protect`로 더 빨리 `Protect Exit`를 낸다

## why

대표 row를 보면 아래 공통점이 있었다.

- `loss_quality_label = bad_loss`
- `exit_reason = Protect Exit / Adverse Stop`
- `peak_profit_at_exit`가 매우 작다
- 그런데 `giveback_usd`와 final loss는 크다

즉 이 family는 `더 기다릴 가치가 있는 hold`가 아니라
`너무 늦게 잘린 adverse loss`에 가깝다.

## regression

검증:

- `pytest -q tests/unit/test_exit_hard_guard_action_policy.py` -> `6 passed`
- `pytest -q tests/unit/test_exit_engines.py` -> `6 passed`
- `pytest -q tests/unit/test_exit_service.py` -> `2 passed`
- `pytest -q tests/unit/test_loss_quality_wait_behavior.py` -> `3 passed`

## runtime

live restart:

- [cfd_main_restart_20260401_202950.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_202950.out.log)
- [cfd_main_restart_20260401_202950.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_202950.err.log)

현재 `main.py`는 새 코드로 다시 올라간 상태다.

## current interpretation

이 패치는 과거 closed history를 즉시 줄이는 종류가 아니라
다음 fresh close에서 `bad_loss adverse`를 더 일찍 정리하게 만드는 종류다.

즉 immediate PA0 queue가 그대로여도 구현 실패로 보지 않는다.
