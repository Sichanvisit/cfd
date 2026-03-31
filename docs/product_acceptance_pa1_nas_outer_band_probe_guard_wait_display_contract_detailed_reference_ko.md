# Product Acceptance PA1 NAS Outer-Band Probe Guard Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
family를 왜 `WAIT + wait_check_repeat` 계약으로 봐야 하는지 고정하는 상세 reference다.

관련 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md)

## 2. 문제 family

target family는 아래 조건을 동시에 가진 NAS structural wait row다.

- `symbol = NAS100`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`

latest PA0 baseline에서는 이 family가

- `must_show_missing 15/15`
- `must_block_candidate 12/12`

를 거의 전부 채우고 있었다.

## 3. 왜 must-show/must-block로 남았나

이 family는 단일 성격이 아니었다.

1. 이미 보이는 wait row

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

2. 아직 숨겨지는 row

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `blocked_display_reason = probe_against_default_side`
- chart wait contract 없음

즉 family 전체가 틀린 것이 아니라,
동일한 structural wait family 안에서 일부 row가
`probe_against_default_side` 때문에 `WAIT checks`로 못 올라가고 있었다.

## 4. 목표 contract

이 축의 목표 contract는 아래와 같다.

- `probe_against_default_side`가 있어도
  `outer_band_guard + probe_not_promoted + nas_clean_confirm_probe` structural wait family이면
  `WAIT + wait_check_repeat`로 유지한다
- `blocked_display_reason`는 `outer_band_guard`를 유지한다
- painter는 neutral wait checks로 렌더한다
- PA0 freeze는 `probe_guard_wait_as_wait_checks` row를 problem queue에서 제외한다

## 5. 구현 방향

1. `nas_outer_band_probe_against_default_side_wait_relief` 예외 추가
2. build 단계에서 `probe_against_default_side` 때문에 structural wait가 hidden으로 떨어지지 않도록 완화
3. `blocked_display_reason = outer_band_guard` carry 유지
4. 기존 `probe_guard_wait_as_wait_checks` 계약을 그대로 사용
5. NAS 전용 unit test, runtime restart, PA0 refreeze로 추적

## 6. 이번 축에서 하지 않는 것

- 새 display reason 추가
- must-hide family 추가 수정
- entry / hold / exit acceptance 처리

## 7. 완료 기준

1. current-build에서 target family against-default-side row가 `WAIT + wait_check_repeat`로 보인다
2. painter가 neutral wait checks로 렌더한다
3. fresh exact row가 다시 나오면 PA0 must-show/must-block queue가 줄기 시작한다
