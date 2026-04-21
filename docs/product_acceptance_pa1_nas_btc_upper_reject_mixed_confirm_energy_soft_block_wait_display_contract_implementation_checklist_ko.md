# Product Acceptance PA1 NAS/BTC Upper-Reject Mixed-Confirm Energy-Soft-Block Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue 재확인

- [x] active runtime에서 `SELL + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked` blank family 확인
- [x] NAS/BTC 둘 다 같은 패턴인지 확인

## Step 1. policy 추가

- [x] NAS mixed-confirm energy wait reason 추가
- [x] BTC mixed-confirm energy wait reason 추가

## Step 2. build surface 보강

- [x] build 단계에서 `blocked_display_reason = energy_soft_block` 유지
- [x] chart wait reason이 flat/nested state에 같이 남도록 확인

## Step 3. 회귀 고정

- [x] consumer_check_state build test 추가
- [x] chart_painter wait overlay test 추가
- [x] PA0 accepted wait skip test 추가

## Step 4. live / PA0 확인

- [x] 런타임 재기동
- [x] PA0 refreeze 재실행
- [x] latest queue composition 확인
- [ ] fresh exact NAS/BTC mixed energy row에서 새 reason 직접 확인

## Step 5. 문서 연결

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
- [x] 상위 memo / roadmap / handoff 연결
