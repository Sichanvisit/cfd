# Product Acceptance PA1 XAU Outer-Band Probe Energy Soft-Block Wait Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
family를
`WAIT + wait_check_repeat + xau_outer_band_probe_energy_soft_block_as_wait_checks`
contract로 올리고, PA0 queue에서 accepted wait surface로 분리한다.

관련 상세 문서:

- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. baseline 확인

- [x] latest PA0에서 target family가 `must_show 15 / must_block 12` main residue인지 확인
- [x] representative replay에서 build 단계부터 hidden blocked scene인지 확인
- [x] fresh exact row 재발 여부와 상관없이 current-build replay를 근거로 먼저 구현 가능한지 확인

### Step 1. wait contract 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `xau_outer_band_probe_energy_soft_block_as_wait_checks` 추가
- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 build-stage relief boolean 추가
- [x] `probe_ready_but_blocked` blanket hide 예외 추가
- [x] resolve blocked reason carry 추가

### Step 2. 테스트 고정

- [x] build test 추가
- [x] resolve replay test 추가
- [x] painter wait rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live/runtime 확인

- [x] cfd `main.py`만 안전하게 재시작
- [x] representative current-build replay 확인
- [x] post-restart fresh exact row watch 결과 기록

### Step 4. PA0 refreeze delta

- [x] restart 직전 snapshot 보존
- [x] latest baseline refreeze
- [x] target family delta 기록
- [x] replacement family 기록

## 3. 확인 포인트

- target family가 hidden blocked가 아니라 WAIT contract로 surface되는가
- fresh exact row가 없더라도 queue turnover만으로 target residue가 빠졌는가
- replacement queue가 다음 PA1 main axis를 설명 가능한가

## 4. 다음 단계

이 축 다음 자연스러운 후속축은 아래 둘 중 하나다.

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
- `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
