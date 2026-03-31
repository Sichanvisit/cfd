# Profitability / Operations P3 A-F Implementation Memo

작성일: 2026-03-30 (KST)

## 이번 구현에서 한 일

- P3 상세 기준 문서 작성
  - [profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md)
- P3 실행 로드맵 문서 작성
  - [profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md)
- 첫 canonical alert script 구현
  - [profitability_operations_p3_anomaly_alerting_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p3_anomaly_alerting_report.py)
- 테스트 추가
  - [test_profitability_operations_p3_anomaly_alerting_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p3_anomaly_alerting_report.py)

## 구현 범위

이번 첫 버전에서 실제로 열린 범위는 아래와 같다.

- `P3-A`: input scope / source contract freeze
- `P3-B`: canonical alert shape 정의
- `P3-C`: first anomaly / alerting report
- `P3-D`: severity normalization 초안
- `P3-E`: symbol / alert-type aggregation
- `P3-F`: operator handoff surface 생성

즉 이번에는 P3를 문서만 연 것이 아니라,
첫 운영 경보 surface까지 실제 latest json/csv/md로 생성 가능한 상태로 만들었다.

## 입력 source

- [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)
- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)
- [profitability_operations_p2_zero_pnl_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.json)

## 첫 canonical output

- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)
- [profitability_operations_p3_anomaly_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.csv)
- [profitability_operations_p3_anomaly_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.md)

## 이번 버전의 설계 포인트

1. P1/P2 concern을 raw cluster 그대로 다시 보여주지 않고 `active_alerts`라는 공통 row로 승격했다.
2. P2의 `zero_pnl_information_gap_cluster`는 직접 쓰지 않고, 더 정확한 [profitability_operations_p2_zero_pnl_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.json) source를 사용했다.
3. `severity`, `alert_type`, `symbol` 단위 summary를 함께 만들었다.
4. operator queue는 symbol/setup/regime 기준으로 dedupe해서 바로 review 가능한 형태로 만들었다.

## 다음 단계

다음 가장 자연스러운 이어짐은 아래 둘 중 하나다.

1. P3 latest를 기준으로 anomaly threshold를 조금 더 다듬기
2. P4 time-series comparison으로 넘어가기
