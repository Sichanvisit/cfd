# Profitability / Operations P1-A~P1-C Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 범위

이번 구현 범위는 아래 세 단계다.

- `P1-A`: input scope and coverage-aware split
- `P1-B`: lifecycle summary shape
- `P1-C`: first canonical lifecycle report script

## 2. 구현 산출물

- canonical script:
  - [profitability_operations_p1_lifecycle_correlation_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p1_lifecycle_correlation_report.py)
- latest outputs:
  - [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)
  - [profitability_operations_p1_lifecycle_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.csv)
  - [profitability_operations_p1_lifecycle_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.md)
- tests:
  - [test_profitability_operations_p1_lifecycle_correlation_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p1_lifecycle_correlation_report.py)

## 3. 이번 구현에서 고정한 것

- decision row는 `p0_decision_trace_v1`가 비어 있어도 P0 helper fallback으로 coverage state와 owner relation을 다시 계산한다.
- lifecycle summary는 `symbol / setup_key / regime_key` 기준 family summary를 canonical flat row로 만든다.
- coverage는 trade row와 decision row를 섞지 않고, decision row 쪽에서만 `in_scope / outside / unknown`으로 분리한다.
- first report는 `overall / coverage / symbol / setup / regime / lifecycle_family / suspicious_clusters / quick_read_summary` shape로 고정한다.

## 4. 현재 읽을 수 있는 것

이제 latest report만 보면 아래 질문에 바로 답할 수 있다.

- 최근 decision flow가 `wait`와 `skip` 중 어디에 더 몰리는가
- 어떤 family가 `outside_coverage`에 많이 남아 있는가
- 어떤 family에서 `fast_adverse_close`가 반복되는가
- 어떤 family가 상대적으로 in-scope coverage 안에서 안정적으로 관측되는가

## 5. 현재 한계

- exact ticket-level lifecycle join을 강제하지는 않는다.
- trade side에서 `entry_setup_id`가 비어 있으면 `legacy_trade_without_setup_id::<direction>::<entry_stage>` family로 묶는다.
- suspicious cluster는 첫 heuristic 버전이라, 이후 `P1-D / P1-E`에서 더 날카롭게 다듬어야 한다.

## 6. 다음 단계

가장 자연스러운 다음 단계는 아래 둘이다.

1. `P1-D`: grouping expansion
2. `P1-E`: suspicious lifecycle cluster refinement

즉 지금은 P1이 설계 단계가 아니라, 첫 운영 관측 surface가 열린 상태다.
