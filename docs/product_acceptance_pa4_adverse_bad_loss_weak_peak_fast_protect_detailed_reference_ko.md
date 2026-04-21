# Product Acceptance PA4 Adverse Bad Loss Weak Peak Fast Protect Detailed Reference

## target family

이번 PA4 main axis는 아래 family다.

```text
Protect Exit / Adverse Stop
+ hard_guard=adverse
+ loss_quality_label=bad_loss
+ wait_quality_label=no_wait 또는 bad_wait
+ peak_profit_at_exit <= 0.25 근방
```

대표 row:

- `BTCUSD 96740516`
- `BTCUSD 96743677`
- `NAS100 98754873`
- `XAUUSD 104200362`

공통 의미:

- 의미 있는 green room을 거의 만들지 못했고
- adverse family인데
- close가 늦어지면서 `bad_loss`가 커졌다

## owner

primary owner:

- [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
- [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py)
- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [exit_service.py](/C:/Users\bhs33/Desktop/project/cfd/backend/services/exit_service.py)

config owner:

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

## design

이번 축은 `wait 품질`을 더 늘리는 쪽이 아니라
`약한 peak` 케이스의 adverse min-hold 경계를 줄이는 쪽이다.

즉:

- peak가 거의 없었고
- 이미 adverse risk로 기운 상태라면
- 기존 `ADVERSE_MIN_HOLD_SECONDS`를 그대로 다 채우지 말고
- 더 빠른 protect 쪽으로 당긴다

## implementation intent

새 경계:

- `ADVERSE_WEAK_PEAK_USD`
- `ADVERSE_WEAK_PEAK_MIN_HOLD_SECONDS`

그리고 hard-guard candidate에 `adverse_weak_peak_protect`를 추가해,
약한 peak adverse family가 더 이르게 `Protect Exit`로 정리되게 만든다.

## expected effect

fresh closed trade가 더 쌓이면 아래 family가 먼저 줄어들어야 한다.

- `Protect Exit ... hard_guard=adverse` bad-loss rows
- `Adverse Stop ... adverse_wait=timeout(...)` weak-peak rows

즉 PA4 queue에서 `bad_loss adverse family`가 먼저 눌리고,
남는 queue가 `Exit Context + meaningful giveback`와 더 분리되어 보여야 한다.
