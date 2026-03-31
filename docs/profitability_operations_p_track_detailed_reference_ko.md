# Profitability / Operations P-Track Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 프로젝트의 `P 트랙`이 무엇인지, 왜 필요한지, 각 단계가 무엇을 의미하는지, 그리고 지금 어디서부터 시작해야 하는지를 고정하기 위한 상세 기준 문서다.

핵심 질문은 이것이다.

`이미 구축한 semantic trading framework를 실제 수익 해석, 운영 판단, 이상 감지, 장기 개선 루프로 어떻게 연결할 것인가?`

## 2. P 트랙이 필요한 이유

지금까지 프로젝트는 크게 세 축을 지나왔다.

- `R 트랙`: reason / key / storage / semantic refinement / acceptance 기반 공사
- `S 트랙`: chart-check-entry를 consumer chain에 맞추는 scene refinement
- `C 트랙`: decision log coverage / retention / archive / backfill 운영 공백 정리

이 단계들로 우리는 다음을 얻었다.

- entry / wait / exit / observe_confirm / consumer chain의 구조적 경계
- replay / dataset / shadow / promotion을 위한 기반
- forensic과 coverage limitation을 분리해서 읽는 기준

하지만 아직 이것만으로는 부족하다.

지금 구조는 시장과 실행을 해석할 수는 있어도,

- 어떤 setup이 실제로 기대값을 만드는지
- 어떤 regime에서 손익이 무너지는지
- entry 문제가 wait 문제인지 exit 문제인지
- 최근 운영 변화가 개선인지 악화인지
- 지금 시스템 상태를 얼마나 믿어야 하는지

를 체계적으로 읽고 다시 개선 input으로 연결하는 계층은 아직 부족하다.

P 트랙은 바로 이 빈칸을 메우는 상위 운영 / 수익 해석 트랙이다.

## 3. P 트랙이 아닌 것

P 트랙은 아래 작업과 다르다.

- 새 매매 전략을 하나 더 발명하는 일
- 지표를 더 섞어서 진입 조건을 복잡하게 만드는 일
- scene display를 더 화려하게 만드는 일
- 기존 semantic layer를 더 세분화하는 일

즉 P 트랙의 초점은 `새 신호 추가`가 아니라 `현재 구조를 더 잘 읽고, 검증하고, 운영하고, 개선하는 것`이다.

## 4. 현재 위치

현재 위치는 이렇게 보는 것이 가장 정확하다.

- `R0 ~ R4`: 완료
- `S0 ~ S6`: 구현 완료, final verdict는 hold and observe one more window
- `R0-B`: actual entry forensic 수행 및 주요 family 정리 완료
- `C0 ~ C6`: internal coverage / retention / archive 트랙 close-out 완료

즉 지금은 “기반 공사”와 “현재 known forensic 공백 정리”를 끝내고, 다시 본선으로 올라갈 수 있는 시점이다.

이 시점의 공식 해석은 아래와 같다.

- internal coverage / archive / reader hardening은 현재 scope에서 닫혔다
- 남은 coverage gap은 external historical source availability 문제로 본다
- 따라서 다음 상위 본선은 `P 트랙`이다

## 5. P 트랙 전체 구조

P 트랙은 `P0 ~ P7`로 이해하는 것이 가장 자연스럽다.

### P0. Trace / Ownership / Coverage-Aware Foundation

이 단계는 P1~P7을 위한 바닥 정리 단계다.

핵심 목적:

- decision trace를 운영 surface와 연결
- legacy scorer ↔ semantic ownership을 명시
- coverage-in-scope / outside-coverage를 명시적 상태로 유지

대표 산출물:

- decision trace contract
- ownership / decision owner enum 정리
- coverage-aware row labeling 규칙

### P1. Lifecycle Correlation Observability

이 단계는 entry / wait / exit를 하나의 거래 생애주기로 읽는 계층이다.

핵심 질문:

- 최근 손실은 entry timing 문제인가
- wait가 너무 길어서 기회를 놓치는가
- exit pressure가 너무 빨라서 수익을 깎는가
- 어떤 blocked reason이 실제 hold / exit 결과와 연결되는가

대표 산출물:

- lifecycle correlation summary
- symbol / setup / regime 기준 correlation view
- entry-wait-exit quick read surface

### P2. Expectancy / Attribution Observability

이 단계는 `무엇이 실제로 기대값을 만드는가`를 숫자로 읽는 계층이다.

핵심 질문:

- 어떤 setup이 돈을 버는가
- 어떤 regime에서 expectancy가 무너지는가
- wait가 expectancy를 살리는가, 죽이는가
- early exit / reverse now / cut now가 실제로 어떤 손익을 만드는가

대표 산출물:

- setup expectancy summary
- regime expectancy summary
- symbol expectancy summary
- stage attribution summary

### P3. Alerting / Anomaly Detection

이 단계는 운영 이상 신호를 자동으로 감지하는 계층이다.

대표 산출물:

- anomaly summary
- alert thresholds
- operator review queue

### P4. Time-Series Comparison

이 단계는 “좋아졌는지 나빠졌는지”를 recent window끼리 비교하는 계층이다.

대표 산출물:

- recent-vs-previous compare
- deploy before/after compare
- symbol / setup / regime delta summary

### P5. Optimization Loop / Casebook Strengthening

이 단계는 운영 데이터와 해석 결과를 다음 개선 입력으로 되돌리는 계층이다.

대표 산출물:

- best / worst scene casebook
- setup blacklist / caution list
- tuning candidate queue

### P6. Meta-Cognition / Health / Drift / Sizing

이 단계부터는 시스템이 자기 상태를 읽기 시작한다.

대표 산출물:

- archetype health tracker
- drift detector
- semantic-aware size overlay
- confidence penalty layer

### P7. Controlled Counterfactual / Selective Adaptation

이 단계는 가장 상위 자동화 단계다.

대표 산출물:

- counterfactual reports
- safe adaptation proposals
- rollback / cap / cooldown guards

## 6. P 트랙에서 반드시 지킬 불변조건

1. consumer contract를 깨지 않는다.
2. semantic vector를 downstream에서 다시 해석하지 않는다.
3. outside-coverage를 unknown으로 뭉개지 않는다.
4. coverage-in-scope 표본과 coverage-out-of-scope 표본을 섞지 않는다.
5. P1~P5는 운영 가시화와 개선 입력이 중심이고, P6~P7은 더 늦게 간다.

## 7. 현재 시점의 가장 현실적인 시작점

현재 시점에서는 P 전체를 한 번에 열기보다 아래 순서가 가장 좋다.

1. `P0`
   decision trace / ownership / coverage-aware labeling 고정
2. `P1`
   lifecycle correlation observability
3. `P2`
   expectancy / attribution observability

즉 지금 당장의 우선순위는 `P1`이지만, 실제로는 `작은 P0 정리`와 함께 묶어서 시작하는 게 가장 안전하다.

## 8. 한 줄 결론

P 트랙은 `지금까지 만든 구조를 실제 수익 해석, 운영 판단, 이상 감지, 장기 개선 루프로 연결하는 상위 운영 계층`이다. 지금 시점의 가장 현실적인 다음 시작점은 `작은 P0 정리와 함께 P1 lifecycle correlation observability`를 여는 것이다.

## 9. P0 Canonical Docs

현재 P0 기준 문서는 아래 두 문서다.

- [profitability_operations_p0_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_detailed_reference_ko.md)
- [profitability_operations_p0_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_execution_roadmap_ko.md)

## 10. P1 Canonical Docs

현재 P1 기준 문서는 아래 두 문서다.

- [profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md)
- [profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md)

## 11. P2 Canonical Docs

?꾩옱 P2 湲곗? 臾몄꽌???꾨옒 ??臾몄꽌??

- [profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md)
- [profitability_operations_p2_expectancy_attribution_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_execution_roadmap_ko.md)

## 12. P3 Canonical Docs

P3 anomaly / alerting 기준 문서는 아래 두 문서다.

- [profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md)
- [profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_execution_roadmap_ko.md)

## 13. P4 Canonical Docs

P4 time-series comparison 기준 문서는 아래 두 문서다.

- [profitability_operations_p4_time_series_comparison_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_detailed_reference_ko.md)
- [profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_execution_roadmap_ko.md)

## 14. P5 Canonical Docs

P5 optimization / casebook 기준 문서는 아래 두 문서다.

- [profitability_operations_p5_optimization_casebook_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_detailed_reference_ko.md)
- [profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_execution_roadmap_ko.md)

## 15. P6 Canonical Docs

P6 meta-cognition / health / drift / sizing 기준 문서는 아래 두 문서다.

- [profitability_operations_p6_metacognition_health_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_detailed_reference_ko.md)
- [profitability_operations_p6_metacognition_health_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_execution_roadmap_ko.md)

## 16. P7 Canonical Docs

P7 controlled counterfactual / selective adaptation 기준 문서는 아래 두 문서다.

- [profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md)
- [profitability_operations_p7_counterfactual_selective_adaptation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_execution_roadmap_ko.md)

## 17. Current Close-Out / Next Experiment

현재 P0~P7 종합 close-out과 바로 다음 guarded size overlay 실험 기준 문서는 아래 두 문서다.

- [profitability_operations_p0_to_p7_master_close_out_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_to_p7_master_close_out_ko.md)
- [profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md)
