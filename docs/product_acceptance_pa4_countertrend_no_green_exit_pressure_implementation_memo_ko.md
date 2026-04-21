# Product Acceptance PA4 Countertrend No-Green Exit Pressure Implementation Memo

## 구현

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
  - `EXIT_COUNTERTREND_NO_GREEN_PRESSURE_ENABLED`
  - `EXIT_COUNTERTREND_NO_GREEN_EXIT_BONUS`
  - `EXIT_COUNTERTREND_NO_GREEN_HOLD_PENALTY`
  - `EXIT_COUNTERTREND_NO_GREEN_WAIT_PENALTY`
- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
  - `countertrend_no_green_exit_pressure` 추가

## 테스트

- [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py) -> `6 passed`
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py) -> `46 passed`

## 결과 해석

이번 패치는 future close를 더 빨리 `exit_now`로 밀어주는 runtime bias다.

그래서 현재 closed-history 기준 refreeze 숫자는 바로 줄지 않아도 정상이다.

- latest baseline:
  - `must_release=8`
  - `bad_exit=10`

즉 이번 하위축은 `숫자 즉시 감소`보다 `다음 fresh close family 개선`을 노린 패치다.
