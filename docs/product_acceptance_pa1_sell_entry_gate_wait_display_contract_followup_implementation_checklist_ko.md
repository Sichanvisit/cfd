# Product Acceptance PA1 Sell Entry-Gate Wait Display Contract Follow-Up Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue / live blank 확인

- [x] current CSV에서 `NAS upper_break_fail entry-gate` blank row 확인
- [x] current CSV에서 `XAU upper_reject_mixed entry-gate` blank row 확인
- [x] representative row를 current build에 replay해서 policy-only 상태와 live blank state를 분리

## Step 1. chart wait policy mirror 추가

- [x] `nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks` 추가
- [x] `xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks` 추가
- [x] 기존 `btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`에도 hidden restore 속성 추가

## Step 2. build / resolve carry 보정

- [x] build path에서 NAS/XAU entry-gate family `blocked_display_reason` carry 추가
- [x] resolve path에서 NAS/XAU repeat relief가 late suppress guard에 다시 죽지 않게 연결

## Step 3. hidden baseline restore 보강

- [x] chart wait relief가 hidden baseline에서도 적용되도록 `restore_hidden_display` 경로 추가
- [x] restore 시 `BLOCKED -> OBSERVE` stage 보정 연결

## Step 4. PA0 accepted reason 반영

- [x] NAS/XAU entry-gate reason 2개를 accepted wait-check 목록에 추가

## Step 5. 테스트

- [x] consumer modifier hidden-restore test 추가
- [x] consumer build test 추가
- [x] consumer resolve test 추가
- [x] chart painter neutral wait-check test 추가
- [x] PA0 skip test 추가

## Step 6. live / refreeze

- [x] `main.py` single-run 재기동
- [x] 첫 fresh exact row 확인
- [x] first blank fresh row 확인 후 hidden-restore follow-up 반영
- [x] second restart 후 short watch 수행
- [x] PA0 refreeze 수행
- [ ] second restart 이후 exact fresh row에 새 reason 실제 기록 확인

## Step 7. 로그 문서화

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
