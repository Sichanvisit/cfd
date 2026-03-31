# Product Acceptance PA0 Baseline Freeze and Target Capture Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 단계에서는 PA0를 문서 기준으로만 두지 않고,
실제 latest baseline artifact를 남기는 구현까지 진행했다.

추가한 핵심 항목:

- [product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md)
- [product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 2. canonical input source

이번 PA0 baseline capture는 아래 입력을 canonical source로 사용한다.

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [runtime_status.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [chart_flow_distribution_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\trade_closed_history.csv)

entry row에서는 `consumer_check_state_v1` nested contract를 우선 읽고,
closed trade row에서는 `net_pnl_after_cost / giveback_usd / post_exit_mfe / wait_quality_label / loss_quality_label`
를 기준으로 hold/exit seed를 만든다.

## 3. 구현된 산출물

script가 아래 latest artifact를 생성한다.

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
- [product_acceptance_pa0_baseline_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.csv)
- [product_acceptance_pa0_baseline_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.md)

이 report는 아래를 포함한다.

- tri-symbol baseline summary
- stage density snapshot
- display ladder snapshot
- chart / entry seed queue
- hold / exit seed queue
- visually similar divergence seed

## 4. 이번 런의 quick read

현재 데이터 기준 latest summary는 아래다.

- recent entry row count: `360`
- recent closed trade count: `79`
- must-show missing count: `15`
- must-hide leakage count: `15`
- must-enter candidate count: `12`
- must-block candidate count: `12`
- divergence seed count: `1`
- must-hold candidate count: `2`
- must-release candidate count: `10`
- good-exit candidate count: `0`
- bad-exit candidate count: `10`

tri-symbol chart baseline quick read:

- `BTCUSD`: recent row `120`, display_ready_ratio `0.833333`, entry_ready_count `0`
- `NAS100`: recent row `120`, display_ready_ratio `0.775`, entry_ready_count `0`
- `XAUUSD`: recent row `120`, display_ready_ratio `0.283333`, entry_ready_count `3`

현재 markdown quick read에서 먼저 보이는 포인트:

- must-show missing 상위 후보는 `XAUUSD`, `NAS100` 쪽 hidden candidate가 많다
- must-hide leakage 상위 후보는 `BTCUSD` wait visibility 쪽이 많이 잡힌다
- divergence seed는 `MIDDLE|MID|middle|observe_state_wait|no_probe`에서 `BTCUSD / XAUUSD`가 갈린다

## 5. 이번 단계에서 의도적으로 하지 않은 것

아래는 이번 단계에서 일부러 하지 않았다.

- acceptance rule 수정
- common state-aware modifier 구현
- symbol override 재조정
- painter translation 수정
- PA1 / PA2 / PA3 / PA4 세부 튜닝 시작

즉 이번 단계는 baseline freeze와 casebook seed capture까지만 수행했다.

## 6. 테스트

실행한 테스트:

```text
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
2 passed
```

## 7. 해석 메모

이번 PA0 report는 최종 판정표가 아니라
다음 단계에서 바로 리뷰할 seed queue를 만드는 성격이다.

특히 현재 `good-exit candidate count = 0`은
“좋은 청산이 전혀 없다”는 확정 결론이라기보다,
현재 recent closed trade window와 단순 heuristic 기준으로는
좋은 exit seed가 자동 추출되지 않았다는 뜻으로 해석하는 게 안전하다.

즉 PA4 전에 필요하면
good-exit seed heuristic은 한 번 더 좁게 reopen할 수 있다.

## 8. 다음 reopen point

다음 순서는 아래가 맞다.

1. PA0 latest artifact를 기준으로 must-show / must-hide / divergence seed를 먼저 훑는다
2. 그 다음 [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md) 기준으로 PA1 chart acceptance modifier 구현에 들어간다
3. PA1 구현 중 Step 0에서는 반드시 이번 PA0 latest artifact를 baseline으로 참조한다

## 9. 한 줄 요약

```text
PA0는 문서만 만든 상태가 아니라,
tri-symbol chart / entry / exit baseline과 casebook seed queue를
latest json/csv/md artifact로 실제 고정한 상태다.
```
