# Product Acceptance PA1 XAU Outer-Band Probe Entry-Gate Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. residue / row shape 확인

- [x] PA0 latest에서 target family가 `must_show 14`, `must_enter 10+` main residue인지 확인
- [x] live CSV representative row가 `display_ready=False + BLOCKED + chart reason blank` 상태인지 확인
- [x] current-build replay로 target family가 probe-present entry-gate wait contract 대상인지 분리

## Step 1. chart wait policy 추가

- [x] `xau_outer_band_probe_entry_gate_wait_as_wait_checks` policy 추가
- [x] `probe_scene_allow = xau_upper_sell_probe` 지정
- [x] `blocked_by_allow = clustered_entry_price_zone / pyramid_not_progressed / pyramid_not_in_drawdown` 지정
- [x] `restore_hidden_display = true`, `restore_stage = OBSERVE` 지정

## Step 2. build / resolve carry 보정

- [x] build path에 `xau_outer_band_probe_entry_gate_wait_relief` boolean 추가
- [x] blocked entry-gate reason이 `blocked_display_reason`으로 carry되게 보정
- [x] resolve path에 repeat relief 추가
- [x] late display suppress guard가 이 family를 다시 숨기지 않게 예외 추가

## Step 3. PA0 accepted reason 반영

- [x] `xau_outer_band_probe_entry_gate_wait_as_wait_checks`를 accepted wait-check 목록에 추가
- [x] must-enter builder도 accepted wait-check rows를 skip하도록 보정

## Step 4. 테스트

- [x] display modifier hidden restore test 추가
- [x] build wait-display test 추가
- [x] resolve wait-display test 추가
- [x] chart painter neutral wait-check test 추가
- [x] PA0 skip test 추가
- [x] targeted suites 회귀 통과

## Step 5. live / refreeze

- [x] `main.py` 재기동
- [x] restart 이후 short watch 수행
- [ ] exact fresh row에 새 wait reason이 flat payload로 기록되는지 직접 확인
- [x] representative replay에서 새 wait reason 확인
- [x] PA0 refreeze 수행
- [ ] target family `must_show / must_enter` actual cleanup 확인

## Step 6. 로그 문서화

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] delta 작성
- [x] fresh runtime follow-up 작성
