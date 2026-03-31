# Profitability / Operations P6 A-F Implementation Memo

작성일: 2026-03-30 (KST)

## 이번 구현에서 한 일

- P6 상세 기준 문서 작성
  - [profitability_operations_p6_metacognition_health_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_detailed_reference_ko.md)
- P6 실행 로드맵 문서 작성
  - [profitability_operations_p6_metacognition_health_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_execution_roadmap_ko.md)
- 첫 canonical meta-cognition / health / sizing script 구현
  - [profitability_operations_p6_metacognition_health_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p6_metacognition_health_report.py)
- 테스트 추가
  - [test_profitability_operations_p6_metacognition_health_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p6_metacognition_health_report.py)

## 구현 범위

이번 첫 버전에서 실제로 열린 범위는 아래와 같다.

- `P6-A`: health input contract freeze
- `P6-B`: symbol health / sizing build
- `P6-C`: archetype health summary
- `P6-D`: drift signal summary
- `P6-E`: first meta-cognition report
- `P6-F`: operator handoff surface 생성

## 첫 canonical output

- [profitability_operations_p6_health_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.json)
- [profitability_operations_p6_health_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.csv)
- [profitability_operations_p6_health_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.md)

## 이번 버전의 핵심 해석

현재 latest 기준으로 아래처럼 읽힌다.

- `XAUUSD`: stressed / hard_reduce
- `NAS100`: stressed / hard_reduce
- `BTCUSD`: watch / reduce

즉 첫 advisory layer는 `모든 symbol이 동일하게 위험`하다고 말하지 않고,
XAU/NAS를 더 강하게 줄이고 BTC는 보수적 reduce로 보는 차이를 만들었다.

## 현재 top candidate type

현재 overall top candidate type은 `legacy_bucket_identity_restore`다.

즉 P6 시점에서도 가장 큰 구조적 병목은
`legacy identity / attribution 복원` 쪽이 계속 남아 있다는 뜻이다.
