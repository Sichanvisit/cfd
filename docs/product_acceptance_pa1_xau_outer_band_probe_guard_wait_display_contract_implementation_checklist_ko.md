# Product Acceptance PA1 XAU Outer-Band Probe Guard Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## 목표

`XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
family의 `probe_against_default_side` hidden row를 neutral wait checks로 되돌린다.

관련 상세 문서:

- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)

## 구현 체크리스트

### Step 0. baseline 확인

- [x] latest PA0에서 target family가 `must_show/must_block` residue인지 확인
- [x] representative row replay로 `probe_against_default_side`가 hidden 원인인지 확인

### Step 1. build / resolve relief

- [x] `consumer_check_state.py`에 `xau_outer_band_probe_against_default_side_wait_relief` 추가
- [x] `display_blocked` 예외에 연결
- [x] `blocked_display_reason = outer_band_guard` carry 연결

### Step 2. 테스트

- [x] build test 추가
- [x] resolve test 추가
- [x] painter wait-check rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live / refreeze 확인

- [x] `main.py` restart
- [x] representative replay 확인
- [x] PA0 refreeze 재실행
- [x] exact fresh recurrence 부재를 follow-up으로 기록
