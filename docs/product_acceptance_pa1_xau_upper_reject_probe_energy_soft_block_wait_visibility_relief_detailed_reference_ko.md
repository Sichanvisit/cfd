# Product Acceptance PA1 XAU Upper Reject Probe Energy Soft Block Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 chart acceptance 안에서
`XAUUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
family를 별도 하위축으로 고정하는 상세 reference다.

이번 하위축의 질문은 아래 하나다.

```text
XAU upper reject probe가 이미 잡혔는데
energy soft block 때문에 실행만 막힌 상태를
차트에서 숨길 것인가,
아니면 아직 들어가지는 않지만 계속 봐야 하는 wait 상태로 보여줄 것인가?
```

이번 reference에서는 이 family를
`hidden blocked scene`이 아니라
`WAIT + repeated checks`로 읽는다.

## 왜 이 하위축이 필요했는가

직전 PA0 baseline에서 must-show queue 상단은 거의 전부 아래 family였다.

- `symbol = XAUUSD`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_upper_sell_probe`
- `check_stage = BLOCKED`
- `display_ready = False`

즉 의미는 있었다.

- probe scene은 살아 있다
- upper reject development도 살아 있다
- 다만 energy soft block 때문에 실행만 막혀 있다
- 그런데 chart에는 아예 안 보인다

PA1 chart acceptance 관점에서는
이걸 완전 숨김으로 두는 쪽보다
`기다리는 SELL-side probe scene`
으로 보이게 하는 쪽이 더 자연스럽다.

## 이번 하위축의 의미 해석

### 1. semantic 해석

이 family는 아래처럼 읽는다.

- 구조는 이미 probe scene으로 식별됨
- probe ready 상태일 수도 있음
- 다만 energy soft block 때문에 entry는 열리지 않음
- 그렇다고 차트에서 사라질 이유는 아님

한 줄로 줄이면:

```text
실행만 soft-blocked 되었을 뿐, 구조적으로는 계속 추적해야 하는 XAU upper reject probe wait
```

### 2. chart surface 해석

차트에는 아래처럼 번역한다.

- directional `SELL_READY`로 밀지 않음
- neutral `WAIT`
- `wait_check_repeat`
- 반복 체크 중이라는 뜻만 남김

즉 사용자는
`지금 바로 매도`
가 아니라
`매도 probe는 살아 있지만 energy soft block 안에서 기다리는 중`
으로 보게 된다.

## owner boundary

### scene owner

scene owner는 기존 baseline 의미를 그대로 책임진다.

- probe scene
- side
- observe reason
- blocked_by
- stage
- importance/source

### modifier owner

modifier owner는 chart surface만 바꾼다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_energy_soft_block_as_wait_checks`

즉 `구조 의미`를 바꾸는 것이 아니라
`표시 계약`을 바꾼다.

### PA0 owner

PA0는 이 family를 accepted wait relief로 본다.

즉 fresh row가 새 contract를 기록하면
문제 queue에서 빼야 한다.

## contract boundary

이번 relief는 아래 경계에서만 허용한다.

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_upper_sell_probe`
- `probe_ready_for_entry = True`
- `energy_relief_allowed = True`

이번 하위축에 포함하지 않는 family:

- `upper_reject_mixed_confirm`
- `upper_reject_confirm`
- `probe_promotion_gate`
- `order_send_failed`
- `BTC lower_rebound_probe_observe + energy_soft_block`

## 구현 방향

### 1. chart wait relief policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_upper_reject_probe_energy_soft_block_as_wait_checks`
policy axis를 추가한다.

### 2. probe-ready-but-blocked 숨김 예외

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
이 family만큼은 `probe_ready_but_blocked -> hidden`
으로 보내지 않고
probe surface를 유지한다.

### 3. blocked reason 유지

보이기만 하고 이유가 사라지지 않게
`blocked_display_reason = energy_soft_block`
debug surface를 남긴다.

### 4. PA0 accepted wait relief 정렬

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
새 `chart_display_reason`을 accepted wait relief set으로 추가한다.

## 이번 하위축에서 하지 않는 것

- BTC mirror family 처리
- NAS leakage 처리
- entry acceptance 수정
- order_send_failed family 수정

## Done Definition

1. fresh XAU energy-soft-block row가 `WAIT + wait_check_repeat`를 가진다
2. PA0가 그 fresh row를 problem queue에서 제외한다
3. 관련 테스트가 통과한다
4. refreeze delta와 다음 reopen point가 남는다

## 한 줄 요약

```text
이번 PA1 하위축은 XAU upper reject probe의 energy soft block 숨김을
wait-style visibility relief로 바꾸는 작업이다.
```
