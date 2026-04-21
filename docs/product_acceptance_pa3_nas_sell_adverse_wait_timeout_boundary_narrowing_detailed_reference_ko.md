# Product Acceptance PA3 NAS Sell Adverse-Wait Timeout Boundary Narrowing Detailed Reference

## 목적

이 문서는 PA3 첫 구현축인
`NAS100 SELL + hard_guard=adverse + adverse_wait=timeout + bad_wait`
family에 대해, 왜 `adverse_wait` 경계를 먼저 좁히는지 고정하기 위한 상세 기준 문서다.

## 현재 문제

latest baseline의 `must_hold 2`는 모두 아래 shape다.

- `symbol = NAS100`
- `direction = SELL`
- `exit_policy_profile = conservative`
- `wait_quality_label = bad_wait`
- `exit_reason` 안에 `hard_guard=adverse | adverse_wait=timeout(...)`

대표 ticket:

- `91758855`
- `91765176`

공통점:

- opposite 근거가 이미 붙어 있다
- `peak_profit_at_exit`는 작거나 거의 없다
- 그런데도 `adverse_wait=timeout(...)`으로 꽤 오래 기다렸다

즉 문제는 “recovery를 조금 본 것”이 아니라,
`의미 있는 green room이 없는 adverse trade를 tf_confirm 하에서도 너무 오래 들고 간 경계`에 가깝다.

## 조정 원칙

첫 조정은 크게 두 가지를 유지한다.

1. `recovery wait` 자체를 없애지 않는다
2. 대신 `tf_confirm + weak peak`일 때만 max wait를 더 짧게 캡한다

즉,

- 반대쪽 확인이 이미 있고
- 기존 trade가 유의미한 이익 구간도 못 만들었으면
- `better exit를 기다리는 시간`을 더 짧게 보자는 뜻이다

## first patch 방향

- base `ADVERSE_WAIT_MAX_SECONDS`는 그대로 둔다
- `tf_confirm=True`면 상한을 먼저 더 짧게 캡한다
- 그중에서도 `peak_profit <= weak_peak_usd`면 더 짧은 cap을 적용한다

이렇게 하면:

- `meaningful peak`가 있었던 trade는 recovery wait를 유지하고
- `weak peak timeout` family만 먼저 줄일 수 있다

## Step 3 design note

이번 턴에서 `warmup / recovery_need / timeout` 경계를 다시 분해해보면 결론은 아래다.

### warmup

- 현재 대표 bad-wait는 `174s`, `349s` timeout이다
- 즉 `warmup(10s)`가 길어서 생긴 문제는 아니다
- first patch에서 warmup을 줄이는 것은 우선순위가 아니다

### recovery_need

- current closed-trade artifact에는 `adverse_wait=recovery(...)` 사례가 보이지 않는다
- 따라서 지금 문제는 recovery 기준이 과도해서 못 빠져나온다기보다,
  recovery가 전혀 만들어지지 않은 상태로 timeout 상한까지 가는 쪽에 가깝다

### timeout

- 실제 조정 포인트는 여기다
- `tf_confirm=True`인 adverse trade는 원래 더 빨리 접는 쪽이 맞고
- 그중 `peak_profit`도 약했던 trade는 `better exit`를 기다릴 근거가 더 약하다

즉 이번 first patch는 `timeout max cap`을 먼저 자르는 방향으로 고정한다.

## rewrite layer와의 분리

[exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_rewrite_policy.py)
에는 아래 rewrite가 있다.

- `green_close_hold_bias`
- `belief_hold_bias`
- `symbol_edge_hold_bias`
- `state_fast_exit_cut`
- `belief_fast_exit_cut`

하지만 이번 family는 그 이전에
[exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
의 `adverse_wait_state` 경계에서 사실상 승부가 난다.

그래서 이번 축은 rewrite layer를 넓게 손보지 않고,
`adverse timeout boundary`만 먼저 좁히는 것이 맞다.

## closed-trade label mismatch 메모

[trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py) 기준으로
`wait_quality_label`은 아래처럼 계산된다.

- `adverse_wait=recovery(...)` -> `good_wait` 또는 `unnecessary_wait`
- `adverse_wait=timeout(...)` -> `bad_wait`
- 그 외는 대부분 `no_wait`

반면 runtime wait surface는
[wait_engine.py](/C:/Users\bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
에서 `exit_wait_state_policy_v1 -> exit_wait_state_rewrite_v1 -> exit_wait_state_surface_v1`로 더 풍부하게 생성된다.

즉 지금 current artifact에 `good_wait / unnecessary_wait`가 0건인 것은,
runtime hold-state가 비어서라기보다 closed-trade label surface가 더 보수적으로 압축되어 있기 때문으로 본다.

## owner

- primary:
  - [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
  - [backend/core/config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- regression:
  - [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py)
  - [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)
  - [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py)
