# Product Acceptance PA1 XAU Middle-Anchor Guard Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
family를
`WAIT + wait_check_repeat + xau_middle_anchor_guard_wait_as_wait_checks`
contract로 올리고,
repeated row에서도 계속 visible wait로 유지한다.

관련 상세 문서:

- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. baseline freeze

- [x] latest PA0에서 target family가 `must_show` main residue인지 확인
- [x] representative replay에서 build는 visible인데 chart wait contract가 비어 있는지 확인
- [x] repeated resolve에서 `xau_middle_anchor_cadence_suppressed`로 다시 꺼지는지 확인

### Step 1. wait contract 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `xau_middle_anchor_guard_wait_as_wait_checks` 추가
- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 guard wait carry 추가
- [x] repeated cadence suppression 예외 추가

### Step 2. 회귀 테스트

- [x] build test 추가
- [x] resolve repeated wait test 추가
- [x] painter wait rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live/runtime 확인

- [x] `main.py` 재시작
- [x] representative current-build replay 확인
- [x] post-restart recent watch에서 exact recurrence 유무 기록

### Step 4. PA0 refreeze delta

- [x] snapshot 보존
- [x] latest baseline refreeze
- [x] target family delta 기록
- [x] replacement family 기록

## 3. 확인 사인

- XAU no-probe middle-anchor row가 hidden이 아니라 WAIT contract로 보이는가
- repeated row에서도 cadence suppression으로 다시 죽지 않는가
- PA0 residue가 다른 family로 이동하면 그 이동 경로를 설명할 수 있는가

## 4. 다음 단계

이번 축 이후 자연스러운 다음 후보는 아래다.

- `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
