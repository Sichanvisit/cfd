# Profitability / Operations P5 A-F Implementation Memo

작성일: 2026-03-30 (KST)

## 이번 구현에서 한 일

- P5 상세 기준 문서 작성
  - [profitability_operations_p5_optimization_casebook_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_detailed_reference_ko.md)
- P5 실행 로드맵 문서 작성
  - [profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md)
- 첫 canonical casebook / optimization script 구현
  - [profitability_operations_p5_optimization_casebook_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p5_optimization_casebook_report.py)
- 테스트 추가
  - [test_profitability_operations_p5_optimization_casebook_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p5_optimization_casebook_report.py)

## 구현 범위

이번 첫 버전에서 실제로 열린 범위는 아래와 같다.

- `P5-A`: scene key / input contract freeze
- `P5-B`: expectancy + alert + delta join
- `P5-C`: first casebook / tuning report
- `P5-D`: worst / strength scene separation
- `P5-E`: tuning candidate queue refinement
- `P5-F`: operator handoff surface 생성

## 첫 canonical output

- [profitability_operations_p5_casebook_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.json)
- [profitability_operations_p5_casebook_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.csv)
- [profitability_operations_p5_casebook_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.md)

## 이번 버전의 핵심 설계

1. scene key는 `symbol / setup_key / regime_key`로 고정했다.
2. P2 expectancy, P3 active alert, P4 symbol/alert delta를 scene row로 합쳤다.
3. 그 위에서 `worst scene`, `strength scene`, `tuning candidate`를 분리했다.
4. tuning candidate는 첫 버전부터 명시적 candidate type으로 분류했다.

## 첫 결과 해석

현재 latest 기준으로 top candidate type은 아래 두 개가 우세하다.

- `legacy_bucket_identity_restore`
- `entry_exit_timing_review`

즉 지금 개선 본선은
`legacy bucket 식별 복원`과 `XAU 계열 entry/exit timing review`로 읽는 것이 맞다.
