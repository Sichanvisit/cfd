# Product Acceptance PA1 XAU Upper Reject Mixed Guard Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`XAUUSD upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
family를 숨김 축으로 두지 않고
`WAIT + repeated checks` chart contract로 연결했다.

관련 기준 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 6. Forecast Guard Extension

이후 같은 contract를 `forecast_guard`까지 확장한 follow-up은 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 하지 않은 범위:

- `upper_reject_probe_observe` family 조정
- `probe_promotion_gate` leakage 조정
- entry / wait / hold / exit acceptance 조정

## 3. 구현 내용

### 3-1. policy axis 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`display_modifier.chart_wait_reliefs.xau_upper_reject_mixed_guard_wait_as_wait_checks`
를 추가했다.

이 policy는 아래 조건을 묶는다.

- `symbol_allow = XAUUSD`
- `side_allow = SELL`
- `observe_reason_allow = upper_reject_mixed_confirm`
- `blocked_by_allow = barrier_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = True`
- `stage_allow = PROBE, OBSERVE`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`

### 3-2. consumer modifier 일반화

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서는
기존 단일 BTC wait relief 처리 대신
`chart_wait_reliefs` 전체를 순회하는 일반 루프로 바꿨다.

그래서 이번 XAU relief도 같은 공통 modifier contract로 적용된다.

### 3-3. XAU guard-wait hide exemption

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
아래 build / resolve 경계를 예외 처리했다.

- `xau_upper_reject_guard_wait_hidden`
- XAU upper reject late hidden
- XAU upper reject cadence suppression

단, 예외는
`upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
family에만 제한된다.

### 3-4. PA0 skip alignment

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`xau_upper_reject_mixed_guard_wait_as_wait_checks`
를 accepted wait-check relief set에 추가했다.

이제 fresh row가 이 contract를 기록하면
PA0 problem seed queue에서 skip된다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
46 passed
61 passed
4 passed
```

고정된 핵심 확인점:

- XAU mixed confirm barrier wait가 `WAIT + wait_check_repeat`로 남는지
- resolved state에서도 다시 숨겨지지 않는지
- painter가 neutral repeated wait surface로 그리는지
- PA0 script가 accepted wait-check relief를 seed queue에서 제외하는지

## 5. live runtime 확인

`cfd main.py`는 새 코드로 재시작했다.

- running process: `2026-03-31 17:09:49`
- recent check 시점 PID: `25228`

재시작 이후 recent row를 확인한 결과:

- total rows since restart: `69`
- per symbol: `BTCUSD 23 / NAS100 23 / XAUUSD 23`

다만 이 recent window에는
이번 target family 자체가 아직 나타나지 않았다.

- `XAUUSD + upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
- since restart count: `0`
- `chart_display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`
- since restart count: `0`

즉 구현은 live 코드에 올라갔지만
이 family가 recent window에 다시 등장해 PA0 artifact에 반영되는 장면은 아직 안 찍혔다.

## 6. PA0 refreeze delta 해석

refreeze 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_171330.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_171330.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

새 baseline generated_at:

- `2026-03-31T17:14:42`

요약:

- `must_show_missing_count = 15`
- `must_hide_leakage_count = 15`
- `must_block_candidate_count = 12`
- `divergence_seed_count = 1`

현재 queue composition:

- must-show `14/15`:
  `XAUUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe + hidden`
- must-hide `15/15`:
  `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe + visible`

즉 이번 XAU mixed confirm relief는 코드/테스트 기준으로는 완료됐지만,
지금 recent queue를 실제로 채우는 주범은 이미 다음 family로 이동했다.

## 7. 현재 reopen point

다음 PA1 follow-up은 아래 둘 중 하나로 좁혀진다.

1. `XAU upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
   이 family를 숨김이 아니라 wait-style visibility로 올릴지 검토
2. `NAS upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
   directional leakage를 더 눌러야 하는지 검토

현재 recent baseline 기준으로는 1번이 must-show 쪽에서 더 크다.

## 8. 한 줄 요약

```text
XAU mixed confirm guard-wait relief는 구현과 테스트까지 완료됐고 live 코드에도 올라갔다.
다만 recent runtime에는 아직 target family가 다시 나오지 않아 queue 감소로 바로 드러나진 않았고,
현재 PA1 다음 메인 표적은 XAU energy-soft-block hidden family와 NAS probe leakage family다.
```

## 9. linked energy-soft-block follow-up

바로 다음 PA1 하위축인
`XAU upper reject probe + energy_soft_block`
wait visibility relief는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
