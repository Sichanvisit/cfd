# Product Acceptance PA1 BTC Outer-Band Probe Guard Wait Repeat Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
family가 repeated runtime row에서도
`WAIT + wait_check_repeat + probe_guard_wait_as_wait_checks`
contract를 유지하도록 맞춘다.

관련 상세 문서:

- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. baseline freeze

- [x] latest PA0에서 target family가 `must_show / must_block` residue인지 확인
- [x] representative row가 build에서는 visible인데 resolve에서는 `btc_lower_structural_cadence_suppressed`로 꺼지는지 확인

### Step 1. resolve cadence relief

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `btc_outer_band_probe_guard_wait_repeat_relief` 추가
- [x] target family가 `btc_lower_structural_cadence_suppressed`에서 제외되도록 조정
- [x] 기존 `probe_guard_wait_as_wait_checks` contract는 그대로 유지

### Step 2. 회귀 테스트

- [x] build test에서 BTC structural rebound가 `probe_guard_wait_as_wait_checks`를 유지하는지 고정
- [x] resolve test에서 repeated BTC structural wait가 더 이상 cadence suppression으로 숨지 않는지 고정
- [x] painter BTC outer-band wait rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live/runtime 확인

- [x] `main.py` 재시작
- [x] representative current-build replay 확인
- [x] post-restart recent watch에서 exact recurrence 유무 기록

### Step 4. PA0 refreeze delta

- [x] snapshot 보존
- [x] latest baseline refreeze
- [x] target family `must_show / must_block` delta 기록
- [x] total count replacement family 기록

## 3. 확인 사인

- build와 resolve의 역할 차이가 분리돼 보이는가
- repeated BTC outer-band wait가 chart wait contract를 유지하는가
- target family가 PA0 queue에서 실제로 빠지거나 줄었는가
- total count가 유지되면 replacement family가 무엇인지 설명 가능한가

## 4. 다음 단계

이번 축 이후 자연스러운 다음 후보는 아래 둘이다.

- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
- `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
