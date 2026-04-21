# PA4 Countertrend Topdown Exit Context Fast-Exit Bias Detailed Reference

## 목표

`must_release / bad_exit`에 남아 있는 `TopDown-only Exit Context` family를 다음 fresh close부터 더 빨리 `exit_now`로 밀기 위한 PA4 하위축이다.

대표 residue:

- `XAUUSD 99802294`
- `XAUUSD 99848313`
- `XAUUSD 99848319`
- `NAS100 99774778`
- `NAS100 98726456`

공통 특징:

- `wait_quality_label=no_wait`
- `loss_quality_label=non_loss` 또는 `bad_loss`
- `exit_reason`가 `Exit Context`인데 구조/flow보다 `TopDown 30M/5M/1M` counter signal 비중이 크다
- current queue에서는 오래된 backlog가 아직 최근 120 close window 안에 남아 있다

## owner

primary owner:

- [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py)
- [exit_utility_input_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_input_contract.py)

config owner:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

verification:

- [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py)
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)

## 설계 요지

이번 축은 `exit_reason` 문자열을 직접 파싱하지 않는다.

대신 [exit_utility_input_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_input_contract.py) 가 이미 제공하는:

- `state_execution_bias_v1.countertrend_with_entry`
- `state_execution_bias_v1.prefer_fast_cut`
- `state_execution_bias_v1.topdown_state_label`

를 이용해서 `countertrend topdown exit pressure`를 scene bias에 추가한다.

즉 의미는:

- entry 방향과 상위 topdown이 충돌하고
- utility input 자체가 fast-cut 성향을 가지고 있으며
- opposite-edge completion이나 lower-edge hold bias 같은 기존 예외가 아니면
- `exit_now`를 더 올리고 `hold / wait_exit`를 더 깎는다

## 기대 효과

- future close에서 `TopDown-only Exit Context` family가 더 빨리 정리된다
- old backlog가 recent window에 남아 있어도, 새 close row는 queue 바깥으로 빠질 가능성이 높아진다
- 기존 `meaningful giveback` / `weak peak adverse` 패치와 충돌하지 않고 상보적으로 동작한다
