# Profitability / Operations P-Track Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P 트랙`을 실제 실행 가능한 순서로 쪼개기 위한 로드맵이다.

R refinement 트랙에서 P profitability/operations 트랙으로 넘어온 전체 전이 맥락은
아래 문서를 함께 기준으로 본다.

- [r_to_p_transition_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\r_to_p_transition_memo_ko.md)

상세 정의는 아래 문서를 기준으로 한다.

- [profitability_operations_p_track_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_detailed_reference_ko.md)

현재 전제는 분명하다.

- `R / S / R0-B / C` 트랙은 현재 scope에서 한 번 닫혔다
- coverage limitation은 explicit 상태로 유지한다
- 다음 본선은 `P 트랙`이다

## 2. 전체 실행 순서

```text
P0. trace / ownership / coverage-aware foundation
-> P1. lifecycle correlation observability
-> P2. expectancy / attribution observability
-> P3. alerting / anomaly detection
-> P4. time-series comparison
-> P5. optimization loop / casebook strengthening
-> P6. meta-cognition / health / drift / sizing
-> P7. controlled counterfactual / selective adaptation
```

## 3. 현재 시작점

현재 가장 자연스러운 시작점은 아래다.

- `즉시 시작`: P0 + P1
- `다음`: P2
- `그 이후`: P3 ~ P5
- `마지막`: P6 ~ P7

## 4. P0. Trace / Ownership / Coverage-Aware Foundation

### 목표

- 운영 해석의 공통 언어를 먼저 고정한다.

### 해야 할 일

- decision trace를 entry / wait / exit / consumer surface에 연결
- legacy scorer ↔ semantic owner relation을 설정/로그로 명시
- `coverage_in_scope / outside_coverage` 상태를 summary와 report에 명시
- 현재 hard-stop guard 결과를 trace surface에 통합

### 대표 owner

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [consumer_contract.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)

### 완료 기준

- “왜 이런 판단이 나왔는가”를 한 줄 trace로 말할 수 있다
- semantic / legacy relation을 로그로 재현할 수 있다
- coverage limitation이 summary에 명시된다

## 5. P1. Lifecycle Correlation Observability

### 목표

- entry / wait / exit를 하나의 거래 생애주기로 읽게 만든다.

### 해야 할 일

- lifecycle correlation summary shape 설계
- symbol / setup / regime 기준 lifecycle table 생성
- blocked_by / wait state / exit family와 결과의 상관 표면 생성
- operator quick-read용 lifecycle markdown 또는 json summary 생성

### 완료 기준

- 최근 손실이 entry / wait / exit 중 어디서 생기는지 빠르게 읽을 수 있다
- setup / regime / symbol 기준 lifecycle 이상 지점을 찾을 수 있다

## 6. P2. Expectancy / Attribution Observability

### 목표

- 무엇이 실제 기대값을 만드는지 수치화한다.

### 해야 할 일

- setup expectancy summary
- regime expectancy summary
- symbol expectancy summary
- stage attribution summary
- recovery / reverse / cut family별 attribution summary

### 완료 기준

- 어떤 setup을 키우고 어떤 setup을 줄일지 숫자로 말할 수 있다
- wait / exit family의 손익 기여를 구분할 수 있다

## 7. P3. Alerting / Anomaly Detection

### 목표

- 운영 이상 징후를 먼저 감지한다.

### 해야 할 일

- anomaly signal 목록 정의
- 임계치 초안 정의
- operator review queue 정의
- summary에 anomaly section 추가

## 8. P4. Time-Series Comparison

### 목표

- recent window / deploy before-after를 비교해 변화 방향을 읽는다.

### 해야 할 일

- recent-vs-previous compare shape 정의
- deploy before/after compare summary
- symbol / setup / regime delta summary
- wait / exit family delta summary

## 9. P5. Optimization Loop / Casebook Strengthening

### 목표

- 운영 결과를 다음 개선 input으로 되돌리는 루프를 만든다.

### 해야 할 일

- best / worst scene casebook
- setup caution / blacklist 문서
- tuning candidate queue

## 10. P6. Meta-Cognition / Health / Drift / Sizing

### 목표

- 시스템이 자기 건강도와 시장 분포 변화를 읽게 만든다.

### 해야 할 일

- archetype health tracker
- recent confidence / health summary
- drift detection
- semantic-aware size overlay

## 11. P7. Controlled Counterfactual / Selective Adaptation

### 목표

- 대안 행동을 비교하고 제한적으로 적응한다.

### 해야 할 일

- entry / exit counterfactual 확장
- safe adaptation proposal
- rollback / cap / min evidence / cooldown guard

## 12. 우선순위 제안

현재 기준 우선순위는 아래가 가장 자연스럽다.

1. `P0 trace / ownership / coverage-aware foundation`
2. `P1 lifecycle correlation observability`
3. `P2 expectancy / attribution observability`
4. `P3 alerting / anomaly detection`
5. `P4 time-series comparison`
6. `P5 optimization loop`
7. `P6 meta-cognition`
8. `P7 selective adaptation`

즉 지금 당장 해야 하는 일은 `P1부터`가 아니라, `작은 P0를 먼저 고정하고 P1을 여는 것`이다.

## 13. 지금 바로 시작할 첫 작업

가장 현실적인 첫 작업 묶음은 아래 셋이다.

1. P0 decision trace / ownership / coverage-aware contract 초안
2. P1 lifecycle correlation summary shape 설계
3. P1 첫 latest report script 구현

## 14. 한 줄 결론

P 트랙은 `구조를 운영 해석과 수익 개선으로 연결하는 본선`이고, 지금 시작점은 `작은 P0 정리와 함께 P1 lifecycle correlation observability를 여는 것`이다.

## 15. P0 Canonical Docs

P0 상세 / 로드맵은 아래를 기준으로 한다.

- [profitability_operations_p0_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_detailed_reference_ko.md)
- [profitability_operations_p0_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_execution_roadmap_ko.md)

## 16. P1 Canonical Docs

P1 상세 / 로드맵은 아래를 기준으로 한다.

- [profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md)
- [profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md)

## 17. P2 Canonical Docs

P2 ?곸꽭 / 濡쒕뱶留듭? ?꾨옒瑜?湲곗??쇰줈 ?쒕떎.

- [profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md)
- [profitability_operations_p2_expectancy_attribution_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_execution_roadmap_ko.md)

## 18. P3 Canonical Docs

P3 anomaly / alerting 기준 문서는 아래 두 문서다.

- [profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md)
- [profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md)

## 19. P4 Canonical Docs

P4 time-series comparison 기준 문서는 아래 두 문서다.

- [profitability_operations_p4_time_series_comparison_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_detailed_reference_ko.md)
- [profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md)

## 20. P5 Canonical Docs

P5 optimization / casebook 기준 문서는 아래 두 문서다.

- [profitability_operations_p5_optimization_casebook_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_detailed_reference_ko.md)
- [profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md)

## 21. P6 Canonical Docs

P6 meta-cognition / health / drift / sizing 기준 문서는 아래 두 문서다.

- [profitability_operations_p6_metacognition_health_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_detailed_reference_ko.md)
- [profitability_operations_p6_metacognition_health_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_execution_roadmap_ko.md)

## 22. P7 Canonical Docs

P7 controlled counterfactual / selective adaptation 기준 문서는 아래 두 문서다.

- [profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md)
- [profitability_operations_p7_counterfactual_selective_adaptation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_execution_roadmap_ko.md)

## 23. Current Close-Out / Next Experiment

현재 P0~P7 종합 close-out과 바로 다음 guarded size overlay 실험 기준 문서는 아래 두 문서다.

- [profitability_operations_p0_to_p7_master_close_out_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_to_p7_master_close_out_ko.md)
- [profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md)
