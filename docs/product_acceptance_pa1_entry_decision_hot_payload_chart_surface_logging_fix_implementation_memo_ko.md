# Product Acceptance PA1 Entry-Decision Hot Payload Chart Surface Logging Fix Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 수정은 `consumer_check_state_v1` nested state를
`entry_decisions.csv` flat chart surface로 다시 올리는 작업이다.

반영 파일:

- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- [test_storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_storage_compaction.py)

추가 / 보강된 flat surface:

- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_storage_compaction.py` -> `17 passed`
- `pytest -q tests/unit/test_rollover_entry_decisions_script.py` -> `1 passed`
- `pytest -q tests/unit/test_entry_engines.py` -> `15 passed`

## 3. Live Runtime 확인

active CSV 확인 결과:

- total rows: `22`
- last row time: `2026-04-01T15:55:50`
- recent non-empty `chart_display_reason` rows: `6`

fresh row example:

- `2026-04-01T15:54:06` `XAUUSD`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = xau_upper_reject_confirm_energy_soft_block_as_wait_checks`
- `2026-04-01T15:55:44` `XAUUSD`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = xau_upper_reject_confirm_forecast_wait_as_wait_checks`

즉 hot payload chart surface logging 누락은 실제 fresh row에서 닫혔다.

## 4. 해석

이번 fix의 핵심 효과는 두 가지다.

- 이제 PA0 actual evidence가 live CSV flat surface를 바로 읽을 수 있다.
- 이후 fresh row가 blank이면 우선 `logging omission`이 아니라
  `current build가 해당 family에 wait/display reason을 아직 안 올린 상태`로 해석할 수 있다.

실제로 XAU wait-contract row는 flat surface까지 잘 올라왔고,
반면 일부 BTC / NAS blocked row는 nested state 자체가 blank라서
다음 residue는 logic 축으로 다시 좁혀볼 수 있게 됐다.

## 5. PA0 재실행

delta 문서:

- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md)

fresh runtime follow-up:

- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md)

## 6. 현재 의미

이번 건은 특정 residue를 바로 `0`으로 만든 축이 아니라,
앞으로의 PA1 actual cleanup 확인을 가능하게 만든 공통 관측면 보강이다.

특히 아래 축들의 fresh-runtime 확인 막힘을 푼 상태로 본다.

- `BTC upper_break_fail clustered entry`
- `XAU middle_anchor probe guard`
- 그 외 `WAIT + wait_check_repeat` 계열 전반
