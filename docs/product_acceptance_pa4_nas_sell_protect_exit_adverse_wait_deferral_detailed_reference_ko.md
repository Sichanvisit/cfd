# Product Acceptance PA4 NAS Sell Protect Exit Adverse-Wait Deferral Detailed Reference

## 목적

이 문서는 PA4 첫 구현축인
`NAS100 SELL + Protect Exit + hard_guard=adverse + no_wait`
family에 대해, 왜 `Protect Exit`보다 `adverse_wait defer`를 먼저 보게 바꾸는지 고정하기 위한 상세 기준 문서다.

## 현재 문제

현재 `must_release / bad_exit` 대표 family는 아래 shape다.

- `symbol = NAS100`
- `direction = SELL`
- `exit_policy_profile = conservative`
- `wait_quality_label = no_wait`
- `exit_reason = Protect Exit ... hard_guard=adverse`
- `Flow: BB 20/2 mid 돌파지지 (+80점)`
- `TopDown 1M: bullish (+20점)` 또는 `H1 Context: RSI oversold (+40점)`

대표 ticket:

- `91754280`
- `91754399`
- `91756959`
- `91770037`

공통점:

- adverse context는 이미 감지됐고
- opposite 확인도 붙어 있는데
- `Protect Exit`가 먼저 확정되면서 `no_wait`로 닫힌다

즉 문제는 `adverse_wait`가 틀린 것이 아니라,
`adverse_wait defer`보다 `adverse Protect Exit`가 먼저 short-circuit 되는 순서에 가깝다.

## first patch 방향

이번 축의 첫 patch는 새 threshold를 추가하는 게 아니라,
`hard_guard action candidate`의 우선순위를 조정하는 것이다.

원칙:

1. `wait_adverse=True`면 먼저 defer를 태운다
2. 그 다음에만 `adverse Protect Exit`를 허용한다
3. `plus_to_minus`나 `profit_giveback` hard guard 우선순위는 건드리지 않는다

즉 아래 한 줄이 핵심이다.

```text
adverse Protect Exit가 맞더라도, adverse-wait contract가 이미 wait를 요청하면 먼저 defer를 태운다.
```

## owner

- primary:
  - [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py)
- connected runtime owner:
  - [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
- regression:
  - [test_exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_hard_guard_action_policy.py)
  - [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py)

## 기대 효과

- `NAS SELL adverse Protect Exit no_wait` family 일부가 바로 닫히지 않고 wait/defer path로 넘어간다
- 즉 PA4에서는 final close action의 조급함을 줄이고,
  PA3 경계와도 더 자연스럽게 이어지게 만든다
