# Profitability / Operations P1 Lifecycle Correlation Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P1 lifecycle correlation observability`를 실제 실행 가능한 순서로 쪼개기 위한 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P1-A. input scope and coverage-aware split
-> P1-B. lifecycle summary shape
-> P1-C. first canonical lifecycle report script
-> P1-D. symbol/setup/regime grouping expansion
-> P1-E. suspicious lifecycle cluster summary
-> P1-F. quick-read memo / operator handoff
```

## 3. 현재 시작점

현재는 바로 `P1-A ~ P1-C`로 들어가는 것이 가장 자연스럽다.

그 이유는:

- P0 trace surface가 이미 들어갔고
- lifecycle_watch_report seed도 이미 있으며
- coverage limitation도 C6에서 explicit 상태로 정리됐기 때문이다

## 4. P1-A. Input Scope and Coverage-Aware Split

### 목표

- P1이 어떤 데이터를 읽고, 어떤 표본을 in-scope / out-of-scope로 나눌지 먼저 고정한다.

### 해야 할 일

- entry decision source 선택
- open / closed trade source 선택
- join 기준 선택
- `p0_coverage_state` 기준 분리 규칙 반영

### 대표 입력

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [trade_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_history.csv)
- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv)

### 완료 기준

- P1 report가 `coverage_in_scope`와 `outside_coverage`를 섞지 않는다

## 5. P1-B. Lifecycle Summary Shape

### 목표

- canonical report의 구조를 먼저 고정한다.

### 꼭 들어가야 할 section

- overall summary
- symbol summary
- setup summary
- regime summary
- lifecycle family summary
- coverage summary
- suspicious clusters

### 핵심 컬럼 예시

- `symbol`
- `setup_id`
- `market_mode`
- `entered_count`
- `wait_count`
- `skipped_count`
- `decision_winner_top`
- `decision_reason_top`
- `exit_wait_state_top`
- `p0_decision_owner_relation_top`
- `coverage_state`

### 완료 기준

- 운영자가 json/csv/md 세 가지 출력 형태를 예측할 수 있다

## 6. P1-C. First Canonical Lifecycle Report Script

### 목표

- 첫 latest report script를 만든다.

### 구현 방향

- 기존 [lifecycle_watch_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\lifecycle_watch_report.py) 를 seed로 참고
- 하지만 canonical 출력은 별도 script로 만드는 것이 더 안전하다
- P0 trace surface와 coverage-aware split을 입력으로 추가

### 권장 산출물

- `json`
- `csv`
- `md`

### 완료 기준

- 최근 window 기준으로 lifecycle latest report를 재생성할 수 있다

## 7. P1-D. Symbol / Setup / Regime Grouping Expansion

### 목표

- lifecycle 문제를 group 기준으로 읽게 만든다.

### 해야 할 일

- symbol group
- setup group
- regime group
- side group

### 완료 기준

- “어디에서 lifecycle이 꼬이는가”를 group 기준으로 말할 수 있다

## 8. P1-E. Suspicious Lifecycle Cluster Summary

### 목표

- 운영자가 먼저 봐야 하는 군집을 추린다.

### 예시 cluster

- 특정 setup에서 `wait_selected -> exit_now`가 몰리는 경우
- 특정 symbol에서 `blocked -> immediate adverse close`가 몰리는 경우
- 특정 regime에서 `reverse_now`가 급증하는 경우

### 완료 기준

- lifecycle report가 단순 통계표를 넘어서 review queue 역할을 한다

## 9. P1-F. Quick-Read Memo / Operator Handoff

### 목표

- 운영자가 report를 빠르게 읽고 방향을 잡을 수 있게 만든다.

### 형태

- 최신 markdown memo
- top 3 lifecycle concern
- top 3 lifecycle strength
- next review queue

### 완료 기준

- quick memo만 읽어도 “지금 어디가 문제인지” 방향을 말할 수 있다

## 10. 대표 owner

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [wait_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\wait_engine.py)
- [exit_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_service.py)
- [lifecycle_watch_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\lifecycle_watch_report.py)
- 새 canonical lifecycle summary script

## 11. 우선순위 제안

현재 기준 가장 좋은 순서는 아래다.

1. `P1-A input scope / coverage-aware split`
2. `P1-B lifecycle summary shape`
3. `P1-C first canonical report script`
4. `P1-D grouping expansion`
5. `P1-E suspicious clusters`
6. `P1-F quick memo`

즉 지금 당장 가장 좋은 시작은 `새 report script를 바로 짜는 것`보다, 먼저 `coverage-aware summary shape`를 고정하는 것이다.

## 12. 한 줄 결론

P1 로드맵의 핵심은 `기존 lifecycle_watch_report seed를 운영 canonical surface로 승격시키는 것`이다. 첫 실제 시작점은 `coverage-aware split + lifecycle summary shape 고정`이다.
