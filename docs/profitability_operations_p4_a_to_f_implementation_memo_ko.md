# Profitability / Operations P4 A-F Implementation Memo

작성일: 2026-03-30 (KST)

## 이번 구현에서 한 일

- P4 상세 기준 문서 작성
  - [profitability_operations_p4_time_series_comparison_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_detailed_reference_ko.md)
- P4 실행 로드맵 문서 작성
  - [profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md)
- 첫 canonical compare script 구현
  - [profitability_operations_p4_time_series_comparison_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p4_time_series_comparison_report.py)
- 테스트 추가
  - [test_profitability_operations_p4_time_series_comparison_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p4_time_series_comparison_report.py)

## 구현 범위

이번 첫 버전에서 실제로 열린 범위는 아래와 같다.

- `P4-A`: compare scope / window contract freeze
- `P4-B`: current vs previous rebuild harness
- `P4-C`: first compare report
- `P4-D`: worsening / improving signal summary
- `P4-E`: symbol / alert delta aggregation
- `P4-F`: operator handoff surface 생성

즉 이번에는 P4를 문서만 연 것이 아니라,
`최근 창 vs 직전 창`을 실제 latest json/csv/md로 읽을 수 있게 만들었다.

## 첫 canonical output

- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)
- [profitability_operations_p4_compare_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.csv)
- [profitability_operations_p4_compare_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.md)

## 설계 포인트

1. P4는 raw source를 직접 새로 집계하지 않고, 두 창에 대해 P1/P2/P2-support/P3 canonical build를 다시 수행한 뒤 delta를 계산한다.
2. 첫 버전은 `row-window compare`다.
3. deploy before/after compare는 이후 확장으로 남긴다.
4. worsening / improving을 symbol delta와 alert-type delta 양쪽에서 같이 읽게 했다.

## 다음 단계

P4 다음 가장 자연스러운 이어짐은 아래 둘 중 하나다.

1. P4 compare 결과를 기준으로 P5 casebook review queue를 여는 것
2. compare window 정의를 배포 기준 compare까지 확장하는 것
