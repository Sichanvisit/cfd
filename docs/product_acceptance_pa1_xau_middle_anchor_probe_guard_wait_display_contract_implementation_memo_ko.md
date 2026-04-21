# Product Acceptance PA1 XAU Middle-Anchor Probe Guard Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 턴에서 한 일

`XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe` 축을 다시 열어봤고, 결론은 `새 production 코드 변경 없이 existing generic contract로 이미 커버된다`는 것이었다.

관련 문서:

- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

## 2. 변경 owner

이번 턴의 실질 코드 변경은 회귀 테스트 추가다.

- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

production owner는 조사만 했다.

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)

## 3. current-build replay

대표 row: `2026-04-01T14:59:07`

stored CSV:

- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

current build:

- `check_candidate = True`
- `check_display_ready = True`
- `check_side = BUY`
- `check_stage = OBSERVE`
- `display_importance_source_reason = xau_second_support_reclaim`
- `display_importance_tier = medium`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

resolve:

- `blocked_display_reason = middle_sr_anchor_guard`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

즉 이 family는 이미 generic `probe_guard_wait_as_wait_checks`로 정상 소유되고 있다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
114 passed
102 passed
45 passed
```

## 5. live / refreeze 메모

- restart log: [cfd_main_restart_20260401_151920.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.out.log)
- err log: [cfd_main_restart_20260401_151920.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.err.log)

fresh row는 계속 들어왔다.

- `entry_decisions.csv` latest row time: `2026-04-01T15:32:54`

하지만 post-restart watch 구간에서는 exact family fresh recurrence가 다시 나오지 않았다. 그래서 live CSV `chart_display_reason` blank backlog가 최근 window에 그대로 남아 있다.

## 6. 해석

이 축은 `구현할 것`이 아니라 `이미 구현된 generic contract를 exact family 기준으로 다시 확인하고 잠그는 것`이었다.

현재 상태는 다음으로 정리한다.

`production 변경 불필요 + replay 확인 완료 + regression lock 완료 + actual cleanup은 exact fresh recurrence pending`
