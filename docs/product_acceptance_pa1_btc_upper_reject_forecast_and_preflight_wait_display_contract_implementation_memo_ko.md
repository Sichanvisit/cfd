# Product Acceptance PA1 BTC Upper-Reject Forecast And Preflight Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 턴에서는 BTC 상단 sell residue 두 개를 같이 정리했다.

- `upper_reject_confirm + forecast_guard + observe_state_wait`
- `upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`

핵심 변경:

- confirm forecast family를 `btc_upper_reject_confirm_forecast_wait_as_wait_checks`로 올림
- probe preflight family를 `btc_upper_reject_probe_preflight_wait_as_wait_checks`로 올림
- preflight family는 stage `BLOCKED`를 유지한 채 chart visibility만 복구

반영 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

- `pytest -q tests/unit/test_consumer_check_state.py` -> `92 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `91 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `34 passed`

## 3. Representative Replay

### 3-1. Confirm forecast row

representative row `2026-04-01T01:41:06` current build replay:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_reject_confirm_forecast_wait_as_wait_checks`

build/resolve 둘 다 같은 contract를 유지한다.

### 3-2. Probe preflight row

representative row `2026-04-01T01:49:24` current build replay:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = preflight_action_blocked`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_reject_probe_preflight_wait_as_wait_checks`

build/resolve 둘 다 같은 contract를 유지한다.

## 4. Live / Refreeze

snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_125657.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_125657.json)

latest:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

재시작 로그:

- [cfd_main_restart_20260401_132056.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_132056.out.log)
- [cfd_main_restart_20260401_132056.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_132056.err.log)

이번에도 live fresh row는 기대하기 어려웠다.

- err log 기준 `MT5 connection unavailable`
- 재시작 뒤 current runtime는 새 코드로 올라갔지만, fresh queue turnover를 만들 새 row는 없었다.

## 5. PA0 Delta

delta 문서:

- [product_acceptance_pa0_refreeze_after_btc_upper_reject_forecast_and_preflight_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_upper_reject_forecast_and_preflight_wait_display_contract_delta_ko.md)

결과:

- `BTC confirm forecast must_hide 9 -> 9`
- `BTC probe preflight must_block 10 -> 10`

이번 delta가 안 줄어든 이유는 구현 실패가 아니라, PA0가 아직 old persisted row의 embedded contract를 보고 있고, 이번 턴에는 fresh runtime row가 없었기 때문이다.

즉 현재 상태는 `코드/테스트/replay 완료 + live recurrence pending`이다.
