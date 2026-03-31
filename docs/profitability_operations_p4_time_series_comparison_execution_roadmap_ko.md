# Profitability / Operations P4 Time-Series Comparison Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P4 time-series comparison`을 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p4_time_series_comparison_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P4-A. compare scope / window contract freeze
-> P4-B. current vs previous rebuild harness
-> P4-C. first compare report script
-> P4-D. worsening / improving signal summary
-> P4-E. symbol / alert delta aggregation
-> P4-F. operator handoff memo
```

## 3. P4-A. Compare Scope / Window Contract Freeze

### 목표

- recent row window와 previous row window를 어떻게 자를지 고정한다.

### 첫 버전 원칙

- raw source tail row를 같은 window size로 분할
- current = 최근 window
- previous = 그 직전 window

## 4. P4-B. Current vs Previous Rebuild Harness

### 목표

- 각 window에 대해 P1/P2/P3 canonical report를 다시 만들 수 있게 한다.

### 포함할 것

- raw csv slicing
- temporary window csv/json 생성
- P1/P2/P2-support/P3 build 재사용

## 5. P4-C. First Compare Report Script

### 목표

- 첫 canonical compare report를 만든다.

### 필수 output

- overall delta summary
- p1 cluster delta
- p2 cluster delta
- p3 alert delta
- symbol alert delta

## 6. P4-D. Worsening / Improving Signal Summary

### 목표

- operator가 바로 읽는 worsening / improving queue를 만든다.

### 포함할 것

- top worsening symbols
- top worsening alert types
- top improving alert types

## 7. P4-E. Symbol / Alert Delta Aggregation

### 목표

- 어떤 symbol이 최근 더 위험해졌는지 빨리 보이게 한다.

### 포함할 것

- current vs previous active alert count delta
- current vs previous critical / high delta

## 8. P4-F. Operator Handoff Memo

### 목표

- compare 결과를 운영 해석으로 압축한다.

### 포함할 것

- 최근 악화 top 3
- 최근 완화 top 3
- P5 casebook으로 넘길 review 후보

## 9. 우선순위 제안

지금 가장 자연스러운 순서는 아래다.

1. `P4-A`
2. `P4-B`
3. `P4-C`
4. `P4-D`
5. `P4-E`
6. `P4-F`

즉 첫 구현에서는 `P4-A ~ P4-C`를 열고,
가능하면 `P4-D ~ P4-E`까지 함께 묶는 것이 가장 좋다.
