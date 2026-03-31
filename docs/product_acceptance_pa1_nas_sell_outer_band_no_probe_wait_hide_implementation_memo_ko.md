# Product Acceptance PA1 NAS Sell Outer-Band No-Probe Wait Hide Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`
family를 visible observe leakage에서
accepted hidden suppression으로 정리했다.

관련 기준 문서:

- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 일부러 건드리지 않은 범위:

- probe scene이 있는 NAS relief family
- XAU energy-soft-block backlog
- BTC new must-hide replacement family
- entry / wait / hold / exit acceptance

## 3. 구현 내용

### 3-1. SELL outer-band no-probe hide policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`sell_outer_band_wait_hide_without_probe`
policy를 추가했다.

고정 조건:

- `side_allow = SELL`
- `observe_reason_allow = outer_band_reversal_support_required_observe`
- `blocked_by_allow = outer_band_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = true`
- `require_importance_source_absent = true`

즉 probe scene도 없고 importance source도 없는 SELL outer-band wait row만 suppress한다.

### 3-2. common modifier suppression 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) modifier path에
새 soft-cap을 연결했다.

이 family가 걸리면:

- `check_stage = OBSERVE`는 유지
- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = sell_outer_band_wait_hide_without_probe`

로 surface가 바뀐다.

### 3-3. painter top-level fallback 차단

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에서
hidden consumer suppression row는
top-level observe fallback을 다시 그리지 않도록 early return을 추가했다.

즉 nested consumer state가 숨김이라고 확정한 row는
chart에 directional SELL line이 다시 살아나지 않는다.

### 3-4. PA0 accepted hidden suppression 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`sell_outer_band_wait_hide_without_probe`
를 accepted hidden suppression reason으로 추가했다.

그래서 must-show / must-hide / must-block builder가
이 reason이 붙은 hidden row를 queue에서 다시 문제로 세지 않는다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
51 passed
64 passed
7 passed
```

고정한 확인 포인트:

- NAS sell outer-band no-probe row가 build 단계에서 바로 숨는지
- painter가 nested hidden row를 top-level fallback으로 다시 그리지 않는지
- PA0 script가 accepted hidden suppression reason을 문제 queue에서 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 시작했다.

- restart log: [cfd_main_restart_20260331_182712.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_182712.out.log)
- restart err log: [cfd_main_restart_20260331_182712.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_182712.err.log)
- live process: `PID 22332`
- start time: `2026-03-31T18:27:14`

fresh hidden target rows:

- `2026-03-31T18:29:46`
- `2026-03-31T18:29:56`

대표 row에서 nested `consumer_check_state_v1` 계약은 실제로 아래처럼 찍혔다.

- `check_stage = OBSERVE`
- `check_display_ready = False`
- `check_side = SELL`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `blocked_display_reason = outer_band_guard`
- `modifier_primary_reason = sell_outer_band_wait_hide_without_probe`

즉 fresh NAS leakage row는 live에서도 이미 visible observe가 아니라 hidden suppression으로 바뀌었다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_182700.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_182700.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest baseline generated_at:

- `2026-03-31T18:30:11`

핵심 해석:

- fresh NAS hidden rows는 queue overlap이 `0`이었다
- 이전 must-hide main family였던
  `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`
  는 queue에서 `15 -> 0`으로 빠졌다
- total `must_hide = 15`가 그대로인 이유는 새 replacement family가 들어왔기 때문이다

current queue composition:

- `must_show 14/15 = XAU outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_show 1/15 = NAS outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
- `must_hide 15/15 = BTC lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
- `must_block 11/12 = XAU outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_block 1/12 = NAS outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

즉 이번 NAS 하위축은 target family 기준으로는 명확하게 닫혔고,
must-hide main axis는 이제 BTC forecast-wait no-probe family로 이동했다.

## 7. current reopen point

이번 하위축이 반영된 뒤 다음 PA1 reopen point는 아래다.

1. `BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
2. `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
3. `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

즉 must-hide 메인 문제는 BTC no-probe family이고,
must-show / must-block 쪽은 XAU energy-soft-block backlog와 NAS probe-scene family가 남아 있다.

## 8. 한 줄 요약

```text
이번 PA1 하위축으로 NAS sell outer-band no-probe wait family는 fresh row 기준으로 실제 hidden suppression으로 닫혔고,
PA0 queue overlap도 0으로 확인됐다. must-hide total이 그대로인 건 실패가 아니라 다음 BTC forecast-wait no-probe family가 새 main axis로 올라왔기 때문이다.
```
