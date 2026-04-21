# Product Acceptance PA1 XAU Upper-Reclaim Wait Hide Without Probe Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue 확인

- [x] PA0 latest에서 `XAU upper_reclaim_strength_confirm + forecast_guard + observe_state_wait`가 `must_hide 5 / must_block 5`를 채우는지 확인
- [x] live CSV representative row가 `display_ready=True + chart reason blank` 상태인지 확인
- [x] current-build replay로 이 family가 hidden suppression target인지 분리

## Step 1. policy mirror 추가

- [x] `xau_upper_reclaim_wait_hide_without_probe` soft-cap policy 추가
- [x] NAS upper reclaim hidden suppression policy와 symbol/side만 다르게 mirror 구성

## Step 2. build suppression 연결

- [x] build modifier path에서 XAU upper reclaim soft-cap applies 조건 추가
- [x] 적용 시 `effective_display_ready = False`로 내리기
- [x] `modifier_primary_reason = xau_upper_reclaim_wait_hide_without_probe` 기록
- [x] `modifier_stage_adjustment = visibility_suppressed` 기록

## Step 3. painter / PA0 skip 반영

- [x] painter hidden suppression reason 목록에 XAU reason 추가
- [x] PA0 accepted hidden suppression reason 목록에 XAU reason 추가

## Step 4. 테스트

- [x] consumer build hidden suppression test 추가
- [x] chart painter hidden skip test 추가
- [x] PA0 skip test 추가
- [x] targeted suites 회귀 통과

## Step 5. live / refreeze

- [x] `main.py` 재기동
- [x] restart 이후 short watch 수행
- [ ] exact fresh row에 새 hidden reason이 flat payload로 기록되는지 직접 확인
- [x] representative replay에서 새 hidden reason 확인
- [x] PA0 refreeze 수행
- [x] turnover 기준 `must_hide 5 -> 0`, `must_block 5 -> 0` 확인

## Step 6. 로그 문서화

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
