# Product Acceptance PA1 XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
family를
`WAIT + wait_check_repeat + xau_upper_reject_confirm_energy_soft_block_as_wait_checks`
contract로 올린다.

관련 상세 문서:

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. baseline / replay 확인

- [x] latest PA0에서 target family가 `must_show 12` residue인지 확인
- [x] representative replay에서 build / resolve 모두 hidden blocked 상태인지 확인
- [x] suppression owner가 `xau_upper_sell_repeat_suppressed`인지 확인

### Step 1. wait contract 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 new wait contract 추가
- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 energy wait relief boolean 추가
- [x] `xau_upper_sell_repeat_suppressed` 예외 추가
- [x] blocked reason carry 추가

### Step 2. 테스트 고정

- [x] build test 추가
- [x] resolve replay test 추가
- [x] painter wait rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live/runtime 확인

- [x] current-build replay 확인
- [x] cfd runtime 재시작
- [x] fresh exact row watch 결과 기록

### Step 4. PA0 refreeze delta

- [x] restart 직전 snapshot 보존
- [x] latest baseline refreeze
- [x] target family delta 기록
- [x] replacement queue 기록

## 3. 확인 포인트

- no-probe confirm blocked family가 WAIT contract로 surface되는가
- repeat suppression이 target family를 다시 죽이지 않는가
- fresh exact row가 없을 때 queue가 유지되는 이유를 설명할 수 있는가

## 4. 다음 단계

이 축 다음 자연스러운 후속축은 아래 둘이다.

- `XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
- `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
