# Profitability / Operations P5 Optimization Loop / Casebook Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P5 optimization loop / casebook strengthening`을 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p5_optimization_casebook_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P5-A. scene key / input contract freeze
-> P5-B. expectancy + alert + delta join
-> P5-C. first casebook / tuning report
-> P5-D. worst / strength scene separation
-> P5-E. tuning candidate queue refinement
-> P5-F. operator handoff memo
```

## 3. P5-A. Scene Key / Input Contract Freeze

### 목표

- P5 scene key를 고정한다.

### 첫 버전 key

- `symbol / setup_key / regime_key`

## 4. P5-B. Expectancy + Alert + Delta Join

### 목표

- P2 expectancy, P3 active alert, P4 delta를 하나의 scene row로 합친다.

## 5. P5-C. First Casebook / Tuning Report

### 목표

- 첫 canonical casebook report를 만든다.

### 필수 output

- worst scene candidates
- strength scene candidates
- tuning candidate queue

## 6. P5-D. Worst / Strength Scene Separation

### 목표

- 무엇을 줄일지와 무엇을 보존할지 분리해서 보여준다.

## 7. P5-E. Tuning Candidate Queue Refinement

### 목표

- 다음 review candidate를 명시적 타입으로 분류한다.

### candidate type 예시

- `entry_exit_timing_review`
- `consumer_gate_pressure_review`
- `legacy_bucket_identity_restore`
- `pnl_lineage_attribution_audit`
- `scene_casebook_review`

## 8. P5-F. Operator Handoff Memo

### 목표

- casebook 결과를 다음 review 순서로 압축한다.

### 포함할 것

- caution scene top 3
- strength scene top 3
- tuning queue top 5

## 9. 우선순위 제안

지금 가장 자연스러운 순서는 아래다.

1. `P5-A`
2. `P5-B`
3. `P5-C`
4. `P5-D`
5. `P5-E`
6. `P5-F`

즉 첫 구현에서는 `P5-A ~ P5-C`를 열고,
가능하면 `P5-D ~ P5-E`까지 함께 묶는 것이 가장 좋다.
