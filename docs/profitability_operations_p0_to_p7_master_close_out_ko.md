# Profitability / Operations P0~P7 Master Close-Out

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P0 ~ P7` profitability / operations 본선이 어디까지 구현되었는지, 각 단계가 실제로 무엇을 남겼는지, 현재 공식 해석이 무엇인지, 그리고 지금 당장 무엇을 다음 액션으로 잡는 것이 맞는지 한 번에 고정하기 위한 close-out 문서다.

핵심 질문은 아래다.

`P0부터 P7까지 올라온 지금, 우리는 무엇을 이미 볼 수 있게 되었고, 무엇만 실제 적용 후보로 좁혀졌는가?`

## 2. 현재 위치 한 줄 요약

현재 상태는 아래처럼 요약하는 것이 가장 정확하다.

- `P0 ~ P7 canonical surface`는 모두 구현되었다.
- `운영 관측 -> 수익 해석 -> 이상 감지 -> 비교 -> casebook -> health -> guarded proposal`까지 연결되었다.
- 지금 당장 `guarded apply` 가능한 것은 `size_overlay_guarded_apply`뿐이다.
- XAU timing 계열은 `review_only`다.
- legacy balanced family 계열은 대부분 `identity_first_gate`로 `no_go`다.

즉 현재 단계는 `자동 최적화 직전`이 아니라, `무엇을 당장 적용하고 무엇은 아직 건드리면 안 되는지 구분할 수 있게 된 상태`다.

## 3. 단계별 close-out

### P0. Trace / Ownership / Coverage-Aware Foundation

핵심 결과:

- decision trace surface 고정
- semantic / legacy relation 명시
- coverage-aware labeling 고정

대표 기준:

- [profitability_operations_p0_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_detailed_reference_ko.md)
- [profitability_operations_p0_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_execution_roadmap_ko.md)
- [p0_decision_trace.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p0_decision_trace.py)

의미:

- 이후 모든 보고서는 `누가 판단했고`, `왜 막혔고`, `coverage 안/밖인지`를 같이 말할 수 있게 되었다.

### P1. Lifecycle Correlation Observability

핵심 결과:

- entry / wait / exit를 lifecycle 단위로 관측하는 surface 확보
- suspicious cluster와 quick-read 확보

대표 기준:

- [profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md)
- [profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md)
- [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)

의미:

- `entry timing 문제인가`, `wait pressure인가`, `exit family 문제인가`를 scene / symbol / setup 단위로 읽을 수 있게 되었다.

### P2. Expectancy / Attribution Observability

핵심 결과:

- expectancy / attribution surface 확보
- zero-pnl information gap을 별도 보조 audit로 분리

대표 기준:

- [profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p2_expectancy_attribution_detailed_reference_ko.md)
- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)
- [profitability_operations_p2_zero_pnl_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.json)

의미:

- 이제 `무엇이 실제로 돈을 까먹는지`와 `무엇이 정보 공백인지`를 분리해 읽을 수 있다.

### P3. Alerting / Anomaly Detection

핵심 결과:

- anomaly signal을 alert queue로 변환
- severity / symbol / alert type summary 확보

대표 기준:

- [profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p3_anomaly_alerting_detailed_reference_ko.md)
- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)

의미:

- `지금 운영상 무엇이 이상한가`를 상단 queue로 읽을 수 있게 되었다.

### P4. Time-Series Comparison

핵심 결과:

- recent window vs previous window 비교 surface 확보
- worsening / improving signal summary 확보

대표 기준:

- [profitability_operations_p4_time_series_comparison_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p4_time_series_comparison_detailed_reference_ko.md)
- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)

의미:

- `지금 더 나빠지고 있는가`, `완화되고 있는가`를 창 비교로 읽을 수 있게 되었다.

### P5. Optimization Loop / Casebook Strengthening

핵심 결과:

- worst / strength scene casebook 확보
- tuning candidate queue 확보

대표 기준:

- [profitability_operations_p5_optimization_casebook_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p5_optimization_casebook_detailed_reference_ko.md)
- [profitability_operations_p5_casebook_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.json)

의미:

- 무엇을 next tuning input으로 봐야 하는지 scene 단위로 정리되었다.

### P6. Meta-Cognition / Health / Drift / Sizing

핵심 결과:

- symbol health / archetype proxy health / drift / sizing advisory 확보

대표 기준:

- [profitability_operations_p6_metacognition_health_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_metacognition_health_detailed_reference_ko.md)
- [profitability_operations_p6_health_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.json)
- [profitability_operations_p6_f_operator_handoff_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p6_f_operator_handoff_memo_ko.md)

현재 공식 해석:

- `XAUUSD`: stressed / hard_reduce / 0.25
- `NAS100`: stressed / hard_reduce / 0.43
- `BTCUSD`: watch / reduce / 0.57

의미:

- 이제 단순 anomaly가 아니라 `운영상 어느 심볼을 얼마나 보수적으로 봐야 하는지`까지 advisory로 읽을 수 있다.

### P7. Controlled Counterfactual / Selective Adaptation

핵심 결과:

- counterfactual review queue
- selective adaptation proposal queue
- safety gate summary
- guarded application queue

대표 기준:

- [profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md)
- [profitability_operations_p7_counterfactual_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.json)
- [profitability_operations_p7_f_operator_handoff_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_f_operator_handoff_memo_ko.md)

현재 공식 해석:

- `guarded_apply_count = 3`
- `review_only_count = 3`
- `no_go_count = 12`
- top proposal type = `legacy_identity_restore_first`

의미:

- 지금 단계에서 `무엇을 실제로 만져볼 수 있는지`와 `무엇은 아직 만지면 안 되는지`를 처음으로 분리했다.

## 4. 현재 공식 운영 해석

지금까지의 P0~P7 결과를 한 줄로 묶으면 아래다.

1. `size_overlay_guarded_apply`만 실제 적용 후보다.
2. XAU timing 계열은 `review_only`다.
3. legacy balanced family는 `identity_first_gate`로 `no_go`다.

즉 다음 액션은 `무언가를 많이 바꾸는 것`이 아니라, `guarded apply 가능한 좁은 범위만 실험하는 것`이 맞다.

## 5. 지금 당장 하지 말아야 하는 것

아래는 아직 이르다.

- entry timing proposal을 live에 바로 적용
- exit profile swap을 즉시 적용
- identity gap이 큰 legacy scene에 counterfactual 적용
- P7을 auto-adaptation처럼 읽기

즉 P7은 `적용 허가 엔진`이 아니라 `적용 후보를 보수적으로 거르는 엔진`으로 해석해야 한다.

## 6. 지금 당장 해도 되는 것

현재 시점에서 가장 자연스러운 다음 액션은 `size overlay guarded apply 실험`이다.

실험 후보:

- `XAUUSD -> hard_reduce -> 0.25`
- `NAS100 -> hard_reduce -> 0.43`
- `BTCUSD -> reduce -> 0.57`

이건 scene-level rule change가 아니라 `보수적 size overlay`이므로, 현재 P7 결과와 가장 일관된 다음 단계다.

## 7. 기준선과 검증 상태

현재 latest 기준선은 아래다.

- P7 전용 테스트 통과
- 전체 unit `1136 passed, 127 warnings`

즉 P0~P7 close-out은 현재 기준으로 green baseline 위에 놓여 있다.

## 8. 다음 문서

지금 close-out 이후 바로 이어지는 실무 문서는 아래다.

- [profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md)

## 9. 결론

P0~P7까지 오면서 우리는 `관측`, `수익 해석`, `이상 감지`, `비교`, `casebook`, `health`, `guarded proposal`까지 모두 연결했다.

이제 남은 건 새 시스템을 또 만드는 것이 아니라, 이미 분리된 결과를 기준으로 `좁고 보수적인 실험`을 하나씩 검증해 나가는 것이다.
