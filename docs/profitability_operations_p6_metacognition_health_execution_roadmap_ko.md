# Profitability / Operations P6 Meta-Cognition / Health / Drift / Sizing Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P6 meta-cognition / health / drift / sizing`을 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p6_metacognition_health_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P6-A. health input contract freeze
-> P6-B. symbol health / sizing build
-> P6-C. archetype health summary
-> P6-D. drift signal summary
-> P6-E. first meta-cognition report
-> P6-F. operator handoff memo
```

## 3. P6-A. Health Input Contract Freeze

### 목표

- P3/P4/P5 latest 중 어떤 section을 health source로 쓸지 고정한다.

## 4. P6-B. Symbol Health / Sizing Build

### 목표

- symbol 기준 health score / health state / size multiplier를 만든다.

## 5. P6-C. Archetype Health Summary

### 목표

- setup_key를 archetype proxy로 보고 caution/strength bias를 요약한다.

## 6. P6-D. Drift Signal Summary

### 목표

- recent worsening / improving signal을 drift 관점으로 재정리한다.

## 7. P6-E. First Meta-Cognition Report

### 목표

- 첫 canonical health / drift / sizing report를 만든다.

## 8. P6-F. Operator Handoff Memo

### 목표

- 건강도와 sizing advisory를 운영 메모로 고정한다.

## 9. 우선순위 제안

지금 가장 자연스러운 순서는 아래다.

1. `P6-A`
2. `P6-B`
3. `P6-C`
4. `P6-D`
5. `P6-E`
6. `P6-F`

즉 첫 구현에서는 `P6-A ~ P6-E`를 한 번에 열고,
최종적으로 operator memo까지 연결하는 것이 가장 좋다.
