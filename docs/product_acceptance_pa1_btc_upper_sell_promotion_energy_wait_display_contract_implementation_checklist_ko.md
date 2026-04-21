# Product Acceptance PA1 BTC Upper-Sell Promotion Energy Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. 대표 row 재선정

- [x] `probe promotion` representative row 확보
- [x] `confirm energy` representative row 확보
- [x] `probe energy` representative row 확보

## Step 1. policy contract 추가

- [x] `btc_upper_reject_probe_promotion_wait_as_wait_checks`
- [x] `btc_upper_reject_confirm_energy_soft_block_as_wait_checks`
- [x] `btc_upper_reject_probe_energy_soft_block_as_wait_checks`

## Step 2. build / resolve relief 연결

- [x] promotion family를 build/resolve에서 wait-check surface로 유지
- [x] confirm energy family를 `BLOCKED + WAIT`로 유지
- [x] probe energy family를 `PROBE + WAIT`로 유지

## Step 3. blocked_display_reason carry 정리

- [x] `probe_promotion_gate`
- [x] `energy_soft_block`
- [x] duplicate carry block 정리

## Step 4. PA0 accepted reason 반영

- [x] 3개 reason을 accepted wait-check display reason 목록에 추가

## Step 5. 회귀 잠금

- [x] consumer build test
- [x] consumer resolve test
- [x] chart painter neutral wait-check test
- [x] PA0 skip test

## Step 6. live 재시작 / fresh row 확인

- [x] `main.py` 최신 코드로 재시작
- [x] row 유입 재개 확인
- [ ] exact target family가 fresh row에 새 reason으로 기록되는지 확인

## Step 7. PA0 refreeze

- [x] refreeze 실행
- [x] queue composition 재점검
- [ ] target family가 actual queue에서 `0`으로 빠지는지 확정
