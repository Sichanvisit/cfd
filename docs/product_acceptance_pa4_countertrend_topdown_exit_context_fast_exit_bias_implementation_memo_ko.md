# PA4 Countertrend Topdown Exit Context Fast-Exit Bias Implementation Memo

## 구현 요약

이번 축은 `TopDown-only Exit Context` release/bad-exit family를 대상으로 `countertrend topdown exit pressure`를 추가한 패치다.

반영 파일:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py)

확인 회귀:

- `pytest -q tests/unit/test_exit_utility_scene_bias_policy.py` -> `5 passed`
- `pytest -q tests/unit/test_wait_engine.py` -> `46 passed`

runtime:

- [cfd_main_restart_20260401_204238.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_204238.out.log)
- [cfd_main_restart_20260401_204238.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_204238.err.log)

## 구현 포인트

- 문자열 기반 `exit_reason` 파싱은 추가하지 않았다
- utility input의 `state_execution_bias_v1`를 읽어서 `countertrend_with_entry / prefer_fast_cut / topdown_state_label` 기준으로 bias를 건다
- 기존 `meaningful_giveback_exit_pressure`와 별도 flag로 두어 추적 가능하게 했다
- hold-bias가 강한 lower-edge family에는 이 pressure가 겹치지 않도록 예외를 두었다

## 현재 해석

latest baseline 기준:

- `must_hold = 0`
- `must_release = 10`
- `bad_exit = 10`

숫자가 바로 줄지 않은 건 정상이다. 이번 축은 과거 close history를 재채점한 게 아니라 다음 fresh close부터 더 빨리 자르기 위한 bias 패치이기 때문이다.

## 같이 봐야 하는 evidence

이번 refreeze에서 fresh weak-peak adverse row:

- `104265149`
- `104264287`
- `104262775`
- `104263033`

는 queue에 직접 올라오지 않았다. 즉 fresh row 쪽은 이미 일부 정리되고 있고, 현재 `must_release / bad_exit 10`은 stale backlog 비중이 크다.

## follow-up

- [product_acceptance_pa0_refreeze_after_pa4_countertrend_topdown_exit_context_fast_exit_bias_fresh_close_watch_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_countertrend_topdown_exit_context_fast_exit_bias_fresh_close_watch_followup_ko.md)
