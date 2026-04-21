# Product Acceptance PA1 XAU Middle-Anchor Probe Guard Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue 확인

- [x] latest PA0에서 exact family `must_show 4 / must_block 4` 확인
- [x] representative row와 current-build replay 비교

## Step 1. contract owner 확인

- [x] `probe_guard_wait_as_wait_checks`가 exact family를 이미 소유하는지 확인
- [x] build / resolve에서 stage, side, reason carry 결과 확인

## Step 2. production 변경 필요성 판단

- [x] 새 policy/state 수정이 필요한지 점검
- [x] production 코드 변경 없이 existing generic contract로 충분하다고 판단

## Step 3. regression lock

- [x] consumer build exact family 테스트 추가
- [x] consumer resolve exact family 테스트 추가
- [x] chart painter exact family 테스트 추가
- [x] PA0 skip exact family 테스트 추가

## Step 4. runtime / refreeze

- [x] post-restart fresh recurrence 재확인
- [x] PA0 refreeze 재실행
- [ ] exact fresh row에 `probe_guard_wait_as_wait_checks`가 live CSV에 기록되는지 재확인
- [ ] turnover 이후 `must_show 4 / must_block 4 -> 0` 최종 확인

## Step 5. 문서 로그

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
