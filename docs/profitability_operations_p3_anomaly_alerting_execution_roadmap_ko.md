# Profitability / Operations P3 Anomaly / Alerting Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P3 anomaly / alerting`을 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P3-A. input scope / source contract freeze
-> P3-B. canonical alert shape 정의
-> P3-C. first anomaly / alerting report script
-> P3-D. severity normalization / review queue refinement
-> P3-E. symbol / alert-type aggregation 강화
-> P3-F. operator handoff memo
```

## 3. P3-A. Input Scope / Source Contract Freeze

### 목표

- P3가 어떤 latest source를 읽는지 고정한다.

### 대상 source

- P1 lifecycle latest
- P2 expectancy latest
- P2 zero-pnl gap audit latest

## 4. P3-B. Canonical Alert Shape

### 목표

- P3 json/csv/md의 공통 shape를 먼저 고정한다.

### 필수 section

- overall alert summary
- source summary
- severity summary
- alert type summary
- symbol alert summary
- active alerts
- operator review queue
- quick read summary

## 5. P3-C. First Report Script

### 목표

- 첫 canonical alert report script를 만든다.

### 구현 방향

- P1 suspicious cluster -> P3 lifecycle alert 승격
- P2 negative expectancy cluster -> P3 expectancy alert 승격
- P2 zero-pnl audit -> P3 information gap alert 승격

## 6. P3-D. Severity Normalization / Review Queue Refinement

### 목표

- source severity를 그대로 노출하지 않고 운영 우선순위로 재정렬한다.

### 포함할 것

- critical / high / medium 정규화
- top alert dedupe
- 정보 공백과 negative expectancy 분리

## 7. P3-E. Symbol / Alert-Type Aggregation

### 목표

- operator가 symbol 기준 집중도와 alert type 집중도를 빨리 읽게 만든다.

### 포함할 것

- symbol alert summary
- alert type summary
- source summary

## 8. P3-F. Operator Handoff Memo

### 목표

- 지금 당장 무엇을 봐야 하는지 operator memo로 고정한다.

### 포함할 것

- top anomaly 3개
- information-gap concern 3개
- immediate review queue
- P4 compare로 넘길 관찰 포인트

## 9. 우선순위 제안

지금 가장 자연스러운 순서는 아래다.

1. `P3-A`
2. `P3-B`
3. `P3-C`
4. `P3-D`
5. `P3-E`
6. `P3-F`

즉 이번 첫 구현에서는 `P3-A ~ P3-C`를 열고,
가능하면 `P3-D ~ P3-E`까지 함께 묶는 것이 가장 효율적이다.
