# Product Acceptance PA1 BTC Upper-Break-Fail Entry-Gate / Energy Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue 확인

- [x] PA0 latest에서 `BTC upper_break_fail_confirm` must-show / must-block family를 다시 확인
- [x] representative row를 current build에 replay해서 current behavior와 stored CSV blank state를 분리

## Step 1. policy contract 추가

- [x] `btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks` 추가
- [x] `btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks` 추가

## Step 2. build path 연결

- [x] entry gate family가 build 단계에서 `WAIT + wait_check_repeat`를 내리게 연결
- [x] energy family가 build 단계에서 `WAIT + wait_check_repeat`를 내리게 연결
- [x] `blocked_display_reason` carry를 유지

## Step 3. resolve path 예외 처리

- [x] late display suppress guard가 entry gate family를 다시 숨기지 않게 exemption 추가
- [x] energy family가 resolve 이후에도 `WAIT` 계약을 유지하는지 확인

## Step 4. PA0 accepted reason 반영

- [x] PA0 accepted wait-check reason 목록에 reason 2개 추가

## Step 5. 회귀 테스트

- [x] consumer build test 추가
- [x] consumer resolve test 추가
- [x] chart painter neutral wait-check test 추가
- [x] PA0 skip test 추가

## Step 6. representative replay

- [x] `clustered_entry_price_zone` row replay 확인
- [x] `pyramid_not_progressed` row replay 확인
- [x] `energy_soft_block + execution_soft_blocked` row replay 확인

## Step 7. live / refreeze

- [x] `main.py` 재기동
- [x] fresh row 유입 확인
- [x] PA0 refreeze 실행
- [ ] exact fresh runtime row에 새 `chart_display_reason`가 실제 기록되는지 확인
- [ ] target family가 PA0 queue에서 `0`까지 빠지는지 최종 확인

## Step 8. 로그 문서화

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
