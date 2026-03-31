# Profitability / Operations P2 Expectancy / Attribution Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P2 expectancy / attribution observability`를 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P2-A. closed trade scope and bucket split
-> P2-B. expectancy summary shape
-> P2-C. first canonical expectancy / attribution report script
-> P2-D. grouping expansion
-> P2-E. negative expectancy / drag cluster summary
-> P2-F. operator memo / handoff
```

## 3. 현재 가장 자연스러운 시작점

지금은 `P2-A ~ P2-C`를 먼저 여는 것이 가장 자연스럽다.

이유:

- P1 operator handoff가 이미 나와 있다
- closed trade source의 attribution 필드 분포를 확인했다
- explicit setup과 legacy bucket을 나눠 읽어야 한다는 전제가 선명하다

## 4. P2-A. Closed Trade Scope and Bucket Split

### 목표

- P2에서 어떤 closed trade를 어떤 bucket으로 읽을지 먼저 고정한다.

### 해야 할 일

- `explicit_setup`
- `legacy_without_setup`
- `snapshot_restored_auto`
- `unknown_regime`

같은 해석 bucket을 먼저 정의한다.

### 완료 기준

- P2 report가 explicit setup과 legacy bucket을 섞지 않는다.

## 5. P2-B. Expectancy Summary Shape

### 목표

- canonical report의 구조를 먼저 고정한다.

### 필수 section

- overall expectancy summary
- attribution readiness summary
- symbol expectancy summary
- setup expectancy summary
- regime expectancy summary
- symbol-setup expectancy summary
- decision_winner attribution summary
- decision_reason attribution summary
- exit_wait_state attribution summary
- stage attribution summary
- negative expectancy clusters

### 완료 기준

- json/csv/md 세 output shape가 안정적으로 정해진다.

## 6. P2-C. First Canonical Expectancy / Attribution Report Script

### 목표

- 첫 latest report script를 만든다.

### 구현 방향

- closed trade 중심
- `net_pnl_after_cost` 우선, 없으면 `profit` fallback
- avg pnl, avg win/loss, win rate, profit factor 계산
- attribution은 `decision_winner / decision_reason / exit_wait_state / exit_policy_stage / exit_policy_profile` 기준으로 집계

### 완료 기준

- latest `json/csv/md`가 생성된다.

## 7. P2-D. Grouping Expansion

### 목표

- symbol/setup/regime를 넘어서 실전 grouping을 넓힌다.

### 확장 후보

- symbol+setup
- setup+regime
- direction
- explicit vs legacy bucket

## 8. P2-E. Negative Expectancy / Drag Cluster Summary

### 목표

- operator가 먼저 봐야 할 drag cluster를 뽑는다.

### 예시

- `negative_expectancy_cluster`
- `forced_exit_drag_cluster`
- `reverse_drag_cluster`
- `legacy_bucket_blind_cluster`

## 9. P2-F. Operator Memo / Handoff

### 목표

- latest report를 operator quick memo로 압축한다.

### 포함되어야 할 것

- top 3 negative expectancy concern
- top 3 positive expectancy strength
- setup caution queue
- attribution review queue

## 10. 우선순위 제안

현재 가장 좋은 순서는 아래다.

1. `P2-A bucket split`
2. `P2-B summary shape`
3. `P2-C first canonical script`
4. `P2-D grouping expansion`
5. `P2-E drag clusters`
6. `P2-F operator memo`

즉 지금 당장은 `P2-A ~ P2-C`를 구현하고 산출물을 먼저 여는 것이 맞다.
