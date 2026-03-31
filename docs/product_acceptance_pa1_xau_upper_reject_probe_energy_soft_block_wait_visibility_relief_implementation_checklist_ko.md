# Product Acceptance PA1 XAU Upper Reject Probe Energy Soft Block Wait Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 하위축
`xau_upper_reject_probe_energy_soft_block_wait_visibility_relief`
를 실제 구현 순서로 고정하는 체크리스트다.

선행 문서:

- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md)

## 이번 단계 목표

```text
XAU upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe family를
차트에서 숨기지 않고
WAIT + repeated checks contract로 올린다.
```

## 작업 순서

### Step 0. target family freeze

고정 target:

- `XAUUSD`
- `upper_reject_probe_observe`
- `energy_soft_block`
- `execution_soft_blocked`
- `xau_upper_sell_probe`

제외 대상:

- `probe_promotion_gate`
- `order_send_failed`
- `upper_reject_mixed_confirm`
- BTC mirror family

### Step 1. policy axis 추가

작업:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
  새 `chart_wait_reliefs` rule 추가
- symbol / side / observe_reason / blocked_by / action_none_reason / probe_scene / stage를 묶음

완료 조건:

- XAU energy-soft-block wait relief가 policy로 고정된다

### Step 2. consumer probe-ready blocked 예외 추가

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
  `probe_ready_but_blocked` 숨김 경계에서
  이번 family만 예외 처리

완료 조건:

- probe scene은 유지되고 display는 살아 있다

### Step 3. blocked reason carry

작업:

- visible 상태여도 `blocked_display_reason`가 비지 않게
  `energy_soft_block` reason을 남긴다

완료 조건:

- chart/debug surface에서 왜 기다리는지 읽을 수 있다

### Step 4. PA0 accepted wait relief alignment

작업:

- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
  새 `chart_display_reason` 추가

완료 조건:

- fresh row가 PA0 must-show / must-hide / must-block에서 빠질 준비가 된다

### Step 5. tests

작업:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

완료 조건:

- contract가 테스트로 잠긴다

### Step 6. live restart and fresh row verify

작업:

- `main.py` 재시작
- fresh XAU row에서 nested `consumer_check_state_v1` 기준
  `WAIT + wait_check_repeat + xau_upper_reject_probe_energy_soft_block_as_wait_checks`
  확인

완료 조건:

- live row가 새 contract를 실제로 찍는다

### Step 7. PA0 refreeze delta

작업:

- snapshot 보존
- PA0 refreeze
- fresh relief row가 queue에 없는지 확인
- 남은 queue 주력을 다음 reopen point로 기록

완료 조건:

- `상세 -> 체크리스트 -> 구현 memo -> refreeze delta` 체인이 닫힌다

## 금지 사항

- energy soft block family를 즉시 entry-like SELL surface로 올리기
- BTC mirror family와 한 단계에서 섞어 처리하기
- top-level CSV chart columns만 보고 구현 실패로 단정하기

## Done Definition

1. live nested row가 새 WAIT relief를 가진다
2. fresh relief row가 PA0 queue에서 제외된다
3. 테스트와 delta 문서가 남는다
