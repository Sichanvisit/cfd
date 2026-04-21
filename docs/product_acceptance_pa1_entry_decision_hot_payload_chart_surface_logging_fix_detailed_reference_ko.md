# Product Acceptance PA1 Entry-Decision Hot Payload Chart Surface Logging Fix Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 공통 축

이번 축은 특정 symbol family 하나를 더 누르는 작업이 아니라,
`entry_decisions.csv` hot payload가 `consumer_check_state_v1`의 chart surface를
flat column으로 제대로 남기지 못하던 공통 logging gap을 닫는 작업이다.

문제가 드러난 대표 축은 아래였다.

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone`
- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe`

두 축 모두 current-build replay에서는 `WAIT + wait_check_repeat`가 맞게 나오는데,
live fresh CSV row에서는 `chart_event_kind_hint / chart_display_mode / chart_display_reason`가
비어 있어서 PA0 actual evidence가 막히고 있었다.

## 2. 실제 문제

핵심 문제는 modifier logic이 아니라 hot payload flattening이었다.

- `consumer_check_state_v1` nested JSON은 row 안에 들어가고 있었다.
- 하지만 `entry_decisions.csv` hot column set에는 아래 surface가 없었다.
  - `consumer_check_display_score`
  - `consumer_check_display_repeat_count`
  - `chart_event_kind_hint`
  - `chart_display_mode`
  - `chart_display_reason`
- 그래서 replay로는 맞아도, live CSV 증빙은 blank로 남았다.

즉 이 단계에서 막힌 것은 `state-aware display modifier`의 판단이 아니라
`entry decision logging surface`였다.

## 3. 수정 계약

이번 fix의 공통 계약은 단순하다.

- `entry_decisions.csv` header에 chart surface flat columns를 추가한다.
- hot payload build 단계에서 nested `consumer_check_state_v1`를 보고
  flat field가 비어 있으면 자동으로 채운다.
- 이후 PA0는 live CSV의 flat chart surface를 바로 사용해
  fresh runtime evidence를 읽을 수 있어야 한다.

대상 flat field:

- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

## 4. owner

- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- [test_storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_storage_compaction.py)
- [test_entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_engines.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- active `entry_decisions.csv` header에 새 flat column이 실제로 존재할 것
- fresh runtime row에서 `WAIT / wait_check_repeat / chart_display_reason`가 flat surface에 기록될 것
- PA0 refreeze가 replay-only가 아니라 live CSV evidence를 근거로 casebook을 읽을 수 있을 것
- 이후 남는 blank row는 logging omission이 아니라 실제 contract 미적용 residue로 해석할 수 있을 것

## 6. 연결 문서

- [product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_checklist_ko.md)
- [product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md)
