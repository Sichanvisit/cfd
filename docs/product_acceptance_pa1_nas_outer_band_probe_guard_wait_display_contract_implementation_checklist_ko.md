# Product Acceptance PA1 NAS Outer-Band Probe Guard Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
family 안에서 `probe_against_default_side` 때문에 hidden으로 떨어지는 row를
`WAIT + wait_check_repeat` contract로 유지한다.

관련 상세 문서:

- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 freeze

- [x] latest PA0에서 target family가 must-show/must-block main axis인지 확인
- [x] visible row와 hidden row의 차이가 `probe_against_default_side`임을 확인

### Step 1. build relief 추가

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `nas_outer_band_probe_against_default_side_wait_relief` 추가
- [x] `display_blocked` 예외에 relief를 연결
- [x] `blocked_display_reason = outer_band_guard` carry 유지

### Step 2. 회귀 테스트

- [x] build test 추가
- [x] resolve effective test 추가
- [x] painter NAS wait rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live/runtime 확인

- [x] `main.py` restart
- [x] patch 이전 fresh row에서 visible/hidden split 원인 확인
- [x] patch 이후 current-build contract 확인
- [x] post-restart recent 120-row에 exact recurrence가 아직 없음을 기록

### Step 4. PA0 refreeze delta

- [x] snapshot 보존
- [x] latest baseline refreeze
- [x] must-show/must-block가 아직 old backlog 중심인지 기록

## 3. 확인 포인트

- structural wait family가 against-default-side에서도 neutral wait checks로 유지되는가
- hidden must-show queue와 current-build contract를 분리해서 해석했는가
- 이 축 다음 main backlog가 무엇인지 선명해졌는가

## 4. 다음 단계

이 축 다음 reopen point는
fresh exact row가 다시 쌓인 뒤 PA0 refreeze를 한 번 더 보는 것이다.
