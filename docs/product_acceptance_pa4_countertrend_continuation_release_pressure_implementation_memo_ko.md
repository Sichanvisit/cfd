# Product Acceptance PA4 Countertrend Continuation Release Pressure Implementation Memo

## implementation

- owner:
  - [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
  - [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- new flag:
  - `countertrend_continuation_exit_pressure`
- trigger:
  - `countertrend_with_entry=True`
  - `topdown_state_label in {BULL_CONFLUENCE, BEAR_CONFLUENCE}`
  - `peak_profit >= 0.80`
  - `giveback >= 0.50`

## verification

- [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py)
  - `7 passed`
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)
  - `46 passed`

## runtime

- `cfd main.py` restarted
- latest runtime log:
  - [cfd_main_restart_20260402_134437.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260402_134437.out.log)
  - [cfd_main_restart_20260402_134437.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260402_134437.err.log)

## result

- immediate baseline count is not expected to drop yet
- this patch is for next fresh closed trades
- current PA4 main remains `must_release 8`

## next

- wait for fresh closed trades
- refreeze and verify whether `structure_exit_context` family starts shrinking
