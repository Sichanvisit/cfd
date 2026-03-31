# Product Acceptance PA1 XAU Middle-Anchor Guard Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 하위축에서 한 일

이번 PA1 하위축에서는
`XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
family를 `WAIT + repeated checks` contract로 올렸다.

이 family는 no-probe guard-wait row지만,
XAU lower-side structural 확인이라는 성격상
숨기는 것보다 `기다림 + 체크 반복`으로 남기는 쪽이 맞다고 봤다.

관련 문서:

- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. chart wait relief 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_middle_anchor_guard_wait_as_wait_checks`를 추가했다.

조건:

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_absent = True`
- `stage = OBSERVE`

반환:

- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_middle_anchor_guard_wait_as_wait_checks`

### 3-2. blocked reason carry

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
이 family는 `blocked_display_reason = middle_sr_anchor_guard`를 carry하도록 맞췄다.

### 3-3. repeated cadence suppression 예외

기존 repeated resolve는
`xau_middle_anchor_cadence_suppressed`
로 target family를 다시 숨기고 있었다.

이번에는
`chart_display_reason = xau_middle_anchor_guard_wait_as_wait_checks`
인 row는 cadence suppression에서 제외되도록 예외를 넣었다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
69 passed
77 passed
20 passed
```

고정한 테스트:

- [test_build_consumer_check_state_keeps_xau_middle_anchor_guard_wait_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_repeated_xau_middle_anchor_observe_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_xau_middle_anchor_guard_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_xau_middle_anchor_guard_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. current-build replay

representative current-build replay는 아래처럼 맞게 나왔다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `check_side = SELL`
- `blocked_display_reason = middle_sr_anchor_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_middle_anchor_guard_wait_as_wait_checks`
- `display_repeat_count = 1`
- `display_strength_level = 5`
- `display_score = 0.75`

즉 build와 repeated resolve 모두
`XAU middle-anchor guard wait`
를 visible wait contract로 유지한다.

## 6. live/runtime 확인

`main.py`를 재시작했다.

- restart log: [cfd_main_restart_20260331_224305.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_224305.out.log)
- restart err log: [cfd_main_restart_20260331_224305.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_224305.err.log)

post-restart recent watch에서는 exact target family fresh recurrence가 다시 나오지 않았다.

recent window에서 잡힌 exact family 4건은 모두

- `2026-03-31T22:32:37`
- `2026-03-31T22:32:49`
- `2026-03-31T22:33:03`
- `2026-03-31T22:33:17`

으로, restart 이전 old row였고
`chart_event_kind_hint / chart_display_mode / chart_display_reason`는 비어 있었다.

즉 이번 축은
`fresh exact live row 증빙`
은 아직 없고,
current-build replay와 PA0 queue delta로 먼저 확인된 상태다.

## 7. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_224305.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_224305.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T22:47:06`

target family delta:

- `must_show 12 -> 0`
- `must_block 0 -> 0`

즉 target middle-anchor residue는 latest queue에서 사라졌다.

다만 total summary는 그대로가 아니었다.

- `must_show_missing_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`
- `must_hide_leakage_count = 0 -> 4`

즉 이번 refreeze에서 queue의 메인이 아래처럼 이동했다.

- `must_show = 15`
  - `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_block = 12`
  - `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_hide = 4`
  - `BTCUSD + upper_reject_probe_observe +  + probe_not_promoted + btc_upper_sell_probe` = `2`
  - `XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked +` = `2`

## 8. 결론

이번 축의 결론은 아래와 같다.

```text
XAU middle-anchor no-probe guard wait family는
WAIT + repeated checks contract로 올리는 것이 맞았고,
current-build replay와 PA0 delta 기준으로는 target residue가 queue에서 사라진 상태다.
다만 fresh exact live row 증빙은 아직 다시 나오지 않아 추가 확인 대기다.
```

## 9. 다음 reopen point

이제 가장 자연스러운 다음 메인축은 아래다.

1. `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
2. `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
