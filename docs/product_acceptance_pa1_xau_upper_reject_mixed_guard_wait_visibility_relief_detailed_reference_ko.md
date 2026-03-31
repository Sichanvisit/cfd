# Product Acceptance PA1 XAU Upper Reject Mixed Guard Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 chart acceptance 안에서
`XAUUSD upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
family를 별도 하위축으로 고정하는 상세 reference다.

이번 하위축의 질문은 단순하다.

```text
XAU upper reject mixed confirm이 barrier guard에 막혀 있을 때
차트에서 완전히 숨길 것인가,
아니면 아직 진입은 아니지만 계속 봐야 하는 wait 상태로 보여줄 것인가?
```

이번 reference에서는 이 family를 `directional sell leakage`가 아니라
`WAIT + repeated checks`로 해석한다.

## 왜 이 하위축이 필요했는가

이전 PA0 baseline과 casebook review에서
아래 family가 반복적으로 `must-show missing`으로 잡혔다.

- `symbol = XAUUSD`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = barrier_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`
- `display_ready = False`

해석은 명확했다.

- 아직 `SELL`로 밀어붙일 단계는 아니다
- 하지만 upper reject 구조가 아예 무의미한 것도 아니다
- barrier guard가 있으니 방향 강조 대신 wait surface가 더 맞다

즉 이 family는
`숨길 것`보다 `wait로 남길 것`에 가깝다.

## 이번 하위축의 의미 해석

### 1. semantic 해석

이 family는 다음 뜻으로 읽는다.

- 구조는 보이지만 아직 강한 승격은 안 됨
- barrier guard가 있어서 entry-ready가 아님
- 그래도 완전 무시할 장면은 아님
- chart에는 `기다림`으로 남겨야 함

한 줄로 줄이면 이렇다.

```text
아직 들어가면 안 되지만, 구조적으로는 계속 체크해야 하는 XAU upper reject wait 상태
```

### 2. chart surface 해석

차트에는 아래 방식으로 연결한다.

- directional `SELL` 강조로 밀지 않음
- neutral event kind `WAIT`
- `wait_check_repeat` display mode
- check count를 통해 반복 관찰 중이라는 뜻만 보여줌

즉 사용자에게는
`지금 매도하라`가 아니라
`매도 구조는 생기고 있지만 아직 guard 안에서 기다리는 중`으로 보이게 한다.

## owner boundary

### scene owner

scene owner는 baseline meaning을 계속 책임진다.

- candidate 여부
- side
- observe reason
- blocked_by
- baseline stage / score / repeat count

### modifier owner

modifier owner는 chart display contract만 책임진다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`

즉 의미를 다시 만들지 않고
표현 계약만 바꾼다.

### painter owner

painter는 modifier가 준 hint를 wait surface로 번역한다.

- WAIT neutral event
- explicit repeat count
- neutral repeated marker

## contract boundary

이번 relief는 아래 경계에서만 허용한다.

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = barrier_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id absent`
- `stage in {PROBE, OBSERVE}`

아래 family는 이번 하위축에 포함하지 않는다.

- `upper_reject_confirm`
- `forecast_guard` family
- `probe_promotion_gate` family
- `energy_soft_block` family
- `upper_reject_probe_observe` family

## 구현 방향

### 1. policy axis 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`display_modifier.chart_wait_reliefs.xau_upper_reject_mixed_guard_wait_as_wait_checks`
contract를 추가한다.

### 2. consumer hide boundary 완화

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
build-time `xau_upper_reject_guard_wait_hidden`과
late hidden / cadence suppression 경계 중
이번 family에 해당하는 경우만 wait relief 예외로 뺀다.

### 3. PA0 skip alignment

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에서
새 `chart_display_reason`을 accepted wait-check relief에 포함시킨다.

### 4. painter verification

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에서
WAIT repeated checks surface가 XAU family에도 같은 contract로 보이는지 확인한다.

## 이번 하위축에서 하지 않는 것

- `upper_reject_probe_observe` family 조정
- `probe_promotion_gate` leakage 조정
- `energy_soft_block` must-show 조정
- entry / hold / exit acceptance 조정

## Done Definition

1. XAU mixed confirm guard wait family가 `WAIT + repeated checks` chart hint를 가진다
2. build-time / late hidden이 이 family를 다시 숨기지 않는다
3. PA0 script가 이 family를 accepted wait-check relief로 skip한다
4. consumer / painter / PA0 tests가 통과한다
5. implementation memo와 refreeze delta가 이어진다

## 한 줄 요약

```text
이번 PA1 하위축은 XAU mixed upper reject guard-wait를
숨겨야 할 leakage가 아니라 wait-style visibility relief로 올리는 작업이다.
```
