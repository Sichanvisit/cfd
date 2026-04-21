# PA4 Countertrend No-Green Fast-Cut Detailed Reference

## 목표

`TopDown-only Exit Context` 잔여 family 중, `peak_profit_at_exit ~= 0` 상태에서 `countertrend topdown`만으로 늦게 잘린 large-loss close를 다음 fresh close부터 더 빨리 `cut_now`로 보내기 위한 PA4 하위축이다.

대표 residue:

- `XAUUSD 99848313`
- `XAUUSD 99848319`
- `XAUUSD 99848330`

공통 특징:

- `exit_reason = Exit Context, TopDown 30M/5M/1M bullish ...`
- `direction = SELL`
- `profit < 0`
- `peak_profit_at_exit = 0`
- `giveback_usd = 0`
- `wait_quality_label = no_wait`
- `loss_quality_label = bad_loss`

즉 의미 있는 green peak 없이 countertrend topdown만 보고 뒤늦게 잘린 family다.

## owner

primary owner:

- [exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_utility_bundle.py)
- [exit_wait_state_input_contract.py](/C:/Users\bhs33/Desktop/project/cfd/backend/services/exit_wait_state_input_contract.py)

config owner:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

verification:

- [test_exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_recovery_utility_bundle.py)
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)

## 설계 요지

이번 축은 `scene bias`보다 한 단계 아래인 `recovery utility gating`을 건드린다.

조건:

- `countertrend_with_entry = true`
- `topdown_state_label in {BULL_CONFLUENCE, BEAR_CONFLUENCE, TOPDOWN_CONFLICT}`
- `profit < 0`
- `peak_profit <= small threshold`
- lower-edge hold bias 예외는 아님

이 조합이면 `wait_be / wait_tp1`를 비활성화하고 `cut_now`를 우선하게 만든다.

## 기대 효과

- no-green 상태의 countertrend close가 더 빨리 방어적 exit로 정리된다
- `TopDown-only Exit Context + bad_loss` family의 future recurrence를 줄인다
- 기존 `weak_peak adverse protect`와 보완적으로 작동한다
