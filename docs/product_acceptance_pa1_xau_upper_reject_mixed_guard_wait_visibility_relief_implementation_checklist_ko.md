# Product Acceptance PA1 XAU Upper Reject Mixed Guard Wait Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 하위축
`xau_upper_reject_mixed_guard_wait_visibility_relief`
를 실제 구현 순서로 고정하는 체크리스트다.

선행 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md)

## 이번 단계 목표

```text
XAU mixed confirm + barrier_guard + observe_state_wait family를
directional sell leakage로 남기지 않고
WAIT + repeated checks chart contract로 올린다.
```

## 작업 순서

### Step 0. target family freeze

목표:

- 이번 relief가 적용될 XAU family와
- 여전히 숨겨야 하는 인접 family를 분리한다

고정 target:

- `XAUUSD`
- `upper_reject_mixed_confirm`
- `barrier_guard`
- `observe_state_wait`
- `probe_scene_id absent`

keep hidden:

- `upper_reject_confirm`
- `upper_reject_probe_observe`
- `forecast_guard`
- `energy_soft_block`

완료 조건:

- 이번 relief가 어디까지인지 문서로 고정된다

### Step 1. chart wait relief policy 추가

목표:

- consumer와 painter가 함께 읽을 공통 policy axis를 만든다

작업:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
  `display_modifier.chart_wait_reliefs.xau_upper_reject_mixed_guard_wait_as_wait_checks`
  를 추가한다
- symbol / side / observe_reason / blocked_by / action_none_reason / stage / hint payload를 묶는다

완료 조건:

- 이번 relief가 policy contract로 고정된다

### Step 2. consumer modifier generalization

목표:

- 기존 BTC wait relief와 이번 XAU relief를 같은 루프로 적용한다

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
  `chart_wait_reliefs`를 일반 루프로 읽게 바꾼다
- symbol / side / probe-scene present/absent 조건을 policy 기반으로 처리한다

완료 조건:

- XAU relief도 live consumer state에 hint를 남긴다

### Step 3. build-time hide exemption

목표:

- XAU mixed confirm guard wait family가 build 시점에 바로 숨겨지지 않게 한다

작업:

- `xau_upper_reject_guard_wait_hidden` 조건에서 이번 family만 예외 처리한다

완료 조건:

- build 결과가 `display_ready=True` wait relief로 남는다

### Step 4. late hidden / cadence suppression exemption

목표:

- resolve 단계에서 다시 숨겨지는 회귀를 막는다

작업:

- late hidden과 cadence suppression 중
  `upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
  family를 예외 처리한다

완료 조건:

- resolved state도 `WAIT + repeated checks`를 유지한다

### Step 5. PA0 baseline skip alignment

목표:

- accepted wait-check relief가 더 이상 casebook 문제 큐를 채우지 않게 한다

작업:

- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
  새 `chart_display_reason`을 skip allow set으로 추가한다

완료 조건:

- fresh row가 찍히면 PA0 must-show / must-hide / must-block에서 빠질 준비가 된다

### Step 6. tests

목표:

- contract를 테스트로 고정한다

작업:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

완료 조건:

- consumer / painter / PA0 contract가 테스트로 잠긴다

### Step 7. live restart and runtime verification

목표:

- `main.py` 재시작 후 fresh row가 새 contract를 실제로 찍는지 본다

작업:

- `cfd main.py` 재시작
- recent runtime row에서
  `xau_upper_reject_mixed_guard_wait_as_wait_checks`
  확인

완료 조건:

- live row가 새 hint를 기록하거나,
  아직 target family가 recent window에 없다는 사실이 확인된다

### Step 8. PA0 refreeze delta

목표:

- 현재 queue가 실제로 어떻게 바뀌었는지 고정한다

작업:

- baseline snapshot 보존
- PA0 refreeze
- delta 문서 작성

완료 조건:

- 구현 성공 여부와
- 다음 PA1 reopen point가 문서로 남는다

## 금지 사항

- XAU mixed confirm relief를 근거 없이 `SELL leakage`로 되돌리기
- `upper_reject_probe_observe`와 `mixed_confirm`을 한 단계에서 섞어 처리하기
- PA0 queue 총량만 보고 구현 성공/실패를 단정하기
- live target row가 없는데 queue 감소를 억지로 해석하기

## Done Definition

1. policy, consumer, PA0 script가 새 relief contract를 이해한다
2. tests가 통과한다
3. runtime restart 결과가 기록된다
4. refreeze delta와 다음 reopen point가 문서로 남는다
