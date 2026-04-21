# Teacher-Label State25 Current Handoff

## 목적

이 문서는 다른 스레드나 다른 작업자가 지금 `state25` 프로젝트를 바로 이어받을 수 있도록, 현재까지 끝난 것과 아직 남은 것을 실행 순서 중심으로 정리한 handoff 문서다.

핵심 목표는 아래 3가지다.

1. `1분봉 25개 teacher-state`를 compact dataset row에 실제 라벨로 붙일 수 있게 만들기
2. 그 라벨이 `micro-structure Top10`과 기존 시스템 state/forecast를 같이 쓰도록 연결하기
3. 이후 `labeling QA -> experiment tuning -> execution 반영 판단` 순서로 넘어갈 수 있게 seed를 확보하기

## 가장 중요한 현재 상태 요약

현재 상태를 한 줄로 요약하면 아래와 같다.

- `micro-structure Top10` 파이프라인 구축 완료
- `teacher_pattern_* compact schema` 구축 완료
- `state25 rule-based labeler` 구축 완료
- `Step 8 labeling QA gate` 구축 완료
- `bounded backfill + richer detail micro backfill`까지 적용 완료
- `Step 9-E1~E5` 틀과 리포트 구축 완료
- 현재 `Step 9`는 `labeler retune + tuned relabel + pattern 25 / 11 primary 승격 relabel + E1/E2/E3 재실행`까지 진행된 상태다
- 현재 `E4`의 confusion blocker는 threshold 기준 해소되었고, `E5`는 재확인 게이트로 남아 있다
- `guarded runtime recycle` 기본 구현 완료, 현재는 `log_only` 한 사이클 관찰 구간이다
- `wait quality WQ1~WQ5` 기본 구현 완료, 현재는 pilot baseline auxiliary 연결까지 들어간 상태다
- 현재 남은 메인 이슈는 `payload flatness`나 `group skew`가 아니라 `10K seed 확장`, `watchlist pair 관찰`, `runtime long-run drift 관찰`, `NAS lower_rebound BUY add-on/pyramid live 재확인`이다
- 그 다음 상위 목표는 `state25 자동 개선 / ML 재연동 상위 로드맵` 기준으로 `economic target -> retrain/promotion gate -> execution integration`을 붙이는 것이다
- 지금 남은 메인만 통합해서 보려면 [state25 남은 메인 통합 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_remaining_candidate_quality_apply_bounded_live_roadmap_ko.md)을 같이 보면 된다
- forecast를 state25 / wait / economic 학습 루프와 직접 묶는 다음 축은 [forecast-state25 bridge 상세 설계](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_design_ko.md), [forecast-state25 bridge 구현 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_implementation_roadmap_ko.md) 기준으로 진행한다

## 지금까지 끝난 것

### 1. state25 정의와 threshold 기준 문서화

이미 결정된 것:

- 25개 teacher-state 정의
- 5개 상위 그룹 구조
- 주패턴 + 보조패턴 구조
- entry / wait / exit bias 구조
- threshold v2 보정
- labeling QA 원칙
- experiment tuning 방향

핵심 참고 문서:

- [state25 마스터 플랜](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_master_plan_ko.md)
- [state25 최종 패턴 기준표](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_25_minute_state_mapping_ko.md)
- [threshold calibration 기준](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md)
- [labeling QA 기준](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md)
- [experiment tuning 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md)

### 2. micro-structure Top10 구축 완료

처음에 `state25`를 붙이기 전에 필요한 상위 재료 10개를 정리했고, 그 재료를 실제 시스템 파이프라인에 심었다.

도입 범위:

- `body_size_pct_20`
- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `doji_ratio_20`
- `direction_run_stats`
- `range_compression_ratio_20`
- `volume_burst_decay_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`
- `gap_fill_progress`

핵심 참고 문서:

- [micro-structure Top10 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_detailed_reference_ko.md)
- [micro-structure 실행 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_execution_roadmap_ko.md)
- [state25 micro bridge](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_micro_structure_casebook_bridge_ko.md)

완료된 step:

- [Step 0 scope lock](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step0_scope_lock_detailed_reference_ko.md)
- [Step 1 OHLCV helper](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_detailed_reference_ko.md)
- [Step 2 state_raw_snapshot](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_detailed_reference_ko.md)
- [Step 3 vector / forecast harvest](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_detailed_reference_ko.md)
- [Step 4 entry hot payload](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_detailed_reference_ko.md)
- [Step 5 closed-history compact bridge](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_detailed_reference_ko.md)
- [Step 6 regression bundle](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_detailed_reference_ko.md)
- [Step 7 casebook bridge](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_detailed_reference_ko.md)

### 3. teacher_pattern schema 구축 완료

이 단계에서 `teacher_pattern_*`를 실제 compact dataset에 저장할 그릇을 만들었다.

대표 컬럼:

- `teacher_pattern_id`
- `teacher_pattern_name`
- `teacher_pattern_group`
- `teacher_pattern_secondary_id`
- `teacher_pattern_secondary_name`
- `teacher_direction_bias`
- `teacher_entry_bias`
- `teacher_wait_bias`
- `teacher_exit_bias`
- `teacher_transition_risk`
- `teacher_label_confidence`
- `teacher_lookback_bars`
- `teacher_label_version`
- `teacher_label_source`
- `teacher_label_review_status`

참고 문서:

- [compact schema 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_detailed_reference_ko.md)
- [compact schema 실행 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_execution_roadmap_ko.md)

### 4. state25 라벨러 구축 완료

결정된 기준을 실제 row에 붙이는 첫 룰 기반 초안이 이미 구현되어 있다.

참고 문서:

- [state25 labeler 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeler_detailed_reference_ko.md)
- [state25 labeler 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeler_implementation_checklist_ko.md)
- [state25 labeler 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeler_implementation_memo_ko.md)

### 5. Step 8 labeling QA gate 구축 완료

라벨이 실제로 붙은 뒤, 아래를 체크하는 QA gate가 이미 있다.

- unlabeled row 존재 여부
- rare pattern 경고
- low-confidence review 대상
- provenance(source/version/lookback) 이상 여부
- confusion pair watchlist

참고 문서:

- [Step 8 labeling QA gate 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_detailed_reference_ko.md)
- [Step 8 labeling QA gate 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_checklist_ko.md)
- [Step 8 labeling QA gate 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_memo_ko.md)

### 6. labeled row 확보 단계도 구현 완료

runtime accumulation만 기다리지 않고, bounded backfill로 seed를 더 빨리 확보하는 경로를 만들었다.

참고 문서:

- [labeled row acquisition 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeled_row_acquisition_detailed_reference_ko.md)
- [labeled row acquisition 실행 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeled_row_acquisition_execution_roadmap_ko.md)
- [labeled row acquisition 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeled_row_acquisition_implementation_checklist_ko.md)
- [labeled row acquisition 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeled_row_acquisition_implementation_memo_ko.md)

이 과정에서 추가로 richer backfill도 만들었다.

참고 문서:

- [detail micro backfill 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_detail_micro_backfill_detailed_reference_ko.md)
- [detail micro backfill 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_detail_micro_backfill_implementation_checklist_ko.md)
- [detail micro backfill 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_detail_micro_backfill_implementation_memo_ko.md)

## 현재 데이터 상태

현재 closed-history 기준 핵심 수치는 아래와 같다.

- total closed rows: `8705`
- labeled rows: `2596`
- unlabeled rows: `6109`

symbol별 labeled row:

- `BTCUSD`: `785`
- `XAUUSD`: `1030`
- `NAS100`: `781`

현재 QA 상태:

- Step 8 QA: `PASS_WITH_WARNINGS`
- 현재 경고:
  - `unlabeled_rows_present`
  - `rare_pattern_watch_triggered`
  - `low_confidence_review_required`

현재 Step 9 calibration / experiment 상태:

- `entry_atr_ratio_flat:*` 경고는 해소됨
- `group_skew:*` 경고도 현재는 해소됨
- 현재 관측된 primary pattern은 `1, 5, 9, 11, 12, 14, 21, 25`다
- 현재 pilot baseline supported pattern은 `1, 5, 9, 11, 14, 21, 25`다
- `E4` confusion tuning report 기준 high / medium unresolved confusion은 현재 없다

즉 지금은 `payload가 비어 있는 문제`, `group skew 문제`, `coverage 부족`은 한 차례 해소됐고, `10K seed shortfall`과 `watchlist pair 미관측`이 메인이다.

현재는 `coverage / support 확장`이 메인 단계가 아니라,
`10K labeled seed 누적 + watchlist pair 관찰 + E5 재확인 타이밍 관리`가 메인 단계다.

참고 문서:

- [Step 9 asset calibration 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md)
- [Step 9 asset calibration 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_implementation_checklist_ko.md)
- [Step 9 asset calibration 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_implementation_memo_ko.md)

## 이번에 특별히 해결한 문제

### 1. micro payload zero 문제

이전에는 labeled row가 붙어도 recent close에 `micro_*` 값이 거의 0으로 남아 있어서 Step 9 calibration이 payload flatness 경고를 냈다.

현재는:

- runtime open snapshot 경로에 `micro_*` carry가 연결됨
- detail JSONL 기반 richer backfill이 recent closed row에 `micro_*`를 채움
- 결과적으로 `micro_payload_zero:*` 경고는 Step 9에서 사라짐

### 2. entry_atr_ratio_flat 문제

이전에는 `entry_atr_ratio`가 최근 labeled row 대부분에서 `1.0`으로 고정되어 있었다.

원인:

- 최근 runtime 경로에서 `AtrThresholdPolicy`가 15M 기준이 부족하면 기본값 `1.0`을 반환
- detail payload에도 direct `entry_atr_ratio`가 항상 있지 않음

해결:

- runtime carry 시 direct ATR이 default-like면 `regime_volatility_ratio`를 proxy로 사용
- detail richer backfill에서도 direct ATR이 없고 `1.0`이면 같은 proxy fallback 적용

결과:

- `entry_atr_ratio_flat:BTCUSD`
- `entry_atr_ratio_flat:XAUUSD`
- `entry_atr_ratio_flat:NAS100`

이 세 경고가 모두 Step 9 report에서 사라졌다.

## 지금 코드 기준으로 어디가 핵심인가

핵심 코드 경로는 아래다.

- `micro helper / source`
  - [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)
- `raw snapshot / vector / forecast`
  - [builder.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
  - [coefficients.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/coefficients.py)
  - [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)
- `entry hot payload`
  - [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
  - [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- `compact schema`
  - [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- `state25 labeler`
  - [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py)
- `QA gate`
  - [teacher_pattern_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeling_qa.py)
- `backfill`
  - [teacher_pattern_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_backfill.py)
  - [teacher_pattern_detail_micro_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_detail_micro_backfill.py)
- `seed calibration`
  - [teacher_pattern_asset_calibration.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_asset_calibration.py)

## 아직 남은 것

현재부터는 `구현 기반 구축`보다 `실험/검증/튜닝`이 메인이다.

### 바로 다음 메인 작업

1. `Step 9 experiment tuning` 본격 진행

핵심 문서:

- [Step 9 experiment tuning 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_experiment_tuning_detailed_reference_ko.md)
- [Step 9 experiment tuning 체크리스트](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_experiment_tuning_implementation_checklist_ko.md)
- [Step 9 experiment tuning 메모](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_experiment_tuning_implementation_memo_ko.md)
- [experiment tuning 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md)

Step 9에서 할 일:

- `tuned relabel` 이후 seed / calibration / full QA / baseline / handoff gate를 다시 검증
- `covered_primary_count 8`과 `supported_pattern_count 7` 상태를 유지하면서 labeled row와 live coverage를 계속 누적
- watchlist pair와 rare pattern이 실제로 관측되는지 추적
- `E5` 재확인 트리거가 차면 execution handoff gate를 다시 연다
- `teacher_pattern_step9_watch_report.py`로 `rows_to_target`, `new_watchlist_pairs`, `blocker_codes`를 계속 기록한다

### 현재 남은 실질 이슈

1. `execution handoff gate`
- 현재 `E5`는 아직 `NOT_READY`다
- 직접 blocker는 아래 1개다
- `labeled_rows = 2596 < 10000`

2. `coverage / support 확장`
- 현재 labeled primary는 `1, 5, 9, 11, 12, 14, 21, 25`까지 관측됐다
- pilot baseline이 실제로 지원 가능한 primary는 `1, 5, 9, 11, 14, 21, 25` 일곱 개다
- 즉 현재 `supported pattern`과 `covered primary`는 execution 기준선을 넘겼고, 이제 남은 건 row 수 누적과 watchlist 관찰이다

3. `rare pattern scarcity`
- 3, 17, 19 같은 rare pattern은 여전히 적다
- 이건 false negative 문제라기보다 표본 자체가 적은 쪽일 수 있음

4. `watchlist pair`
- `12-23`, `5-10`, `2-16`은 아직 모두 `0`이다
- 즉 confusion blocker는 해소됐지만, watchlist 관측 자체는 계속 필요하다

5. `entry live watch`
- NAS `lower_rebound BUY` 경로는 최근 완화 이후 `forecast_guard / probe_forecast_not_ready / energy_soft_block`에서 한 단계 올라왔고, 현재 직접 확인이 필요한 마지막 축은 `add-on / pyramid`다
- `shadow_lower_rebound_probe_observe_nas_lower_breakdown_probe` reason variant까지 pyramid 완화가 들어간 상태다
- 다만 최신 live tail은 `market_closed_session`으로 끊겨 있어서, NAS 세션 재개 후 `pyramid_not_in_drawdown` 해소 여부를 다시 확인해야 한다
- 다음 확인 포인트는 `entry_decisions.csv` 최신 NAS row에서 `pyramid_not_in_drawdown`이 사라졌는지, 아니면 새 다음 blocker가 올라오는지다

6. `housekeeping`
- pandas concat warning
- DataFrame fragmentation warning

이건 기능 blocking은 아니지만, Step 9 중간이나 execution handoff 전엔 정리하는 게 좋다.

### 6. `runtime long-run drift` 운영 가설

- 최근 운영 중 “오래 켜둘수록 entry / wait / exit가 루즈해진다”는 체감이 제기됐다
- 현재 구조상 main 중복 문제라기보다, cache / adaptive state / policy runtime의 누적성 문제일 가능성이 더 크다
- 상위 policy refresh(`ENABLE_POLICY_LOOP_REFRESH`)도 현재는 사실상 비활성 운영에 가깝다
- 그래서 별도 독립 축으로 `guarded hourly recycle` 기본 구현을 넣었고, 현재는 `log_only` 한 사이클 관찰로 두고 있다

핵심 운영 노트:

- [runtime recycle operating note](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_runtime_recycle_operating_note_ko.md)
- [state25 자동 개선 / ML 재연동 상위 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_auto_improvement_execution_roadmap_ko.md)
- [state25 남은 메인 통합 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_remaining_candidate_quality_apply_bounded_live_roadmap_ko.md)
- [forecast-state25 bridge 상세 설계](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_design_ko.md)
- [forecast-state25 bridge 구현 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_implementation_roadmap_ko.md)

## 추천 실행 순서

다른 스레드에서 이어받는다면 아래 순서가 가장 자연스럽다.

1. 이 문서 먼저 읽기
2. [state25 마스터 플랜](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_master_plan_ko.md) 읽기
3. [state25 최종 패턴 기준표](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_25_minute_state_mapping_ko.md) 와 [threshold calibration 기준](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md) 읽기
4. [micro-structure 실행 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_execution_roadmap_ko.md) 에서 Step 1~8 완료 상태 확인
5. [Step 9 asset calibration 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md) 확인
6. [Step 9 experiment tuning 상세](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_experiment_tuning_detailed_reference_ko.md) 로 넘어가기
7. 런타임 운영 이슈를 같이 볼 경우 [runtime recycle operating note](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_runtime_recycle_operating_note_ko.md) 확인
8. `state25` 이후 상위 목표와 ML 재연동 구조를 볼 때는 [state25 자동 개선 / ML 재연동 상위 로드맵](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_auto_improvement_execution_roadmap_ko.md) 확인

## 다음 스레드에서 바로 물어볼 만한 질문

다른 스레드가 바로 이어받는다면 보통 아래 질문으로 시작하면 된다.

- 지금 seed `2596` 기준으로 `10K`까지 가는 동안 어떤 live / backfill 누적 전략이 가장 효율적일까?
- watchlist pair `12-23`, `5-10`, `2-16` 중 무엇이 먼저 관측될 가능성이 높을까?
- rare pattern은 룰을 건드려서 늘릴 문제인가, 아니면 표본 축적 문제인가?
- `E5` 재확인은 `+100 fresh closed`, `watchlist pair 관측`, `supported pattern 증가` 중 무엇이 먼저 올까?
- `teacher_pattern_step9_watch_report.py` 기준 다음 `recheck_now`가 언제 켜질까?
- long-run drift 체감이 실제 운영 지표와 맞는가?
- `runtime recycle`의 `log_only` 한 사이클이 기대한 due/blocked 흐름으로 찍히는가?

## 최종 결론

현재 프로젝트는 `state25를 만들 재료를 심는 단계`를 넘어서, 실제 `retune / relabel / baseline 재검증`과 `execution 직전 gate 정리` 단계까지 들어갔다.

지금부터는:

- `state25 label 품질`
- `seed 확장`
- `coverage / support 확장`
- `baseline 재검증`

이 네 가지가 메인이다.

즉 다른 스레드에서 이어받을 때는 `새로운 파이프라인 공사`보다 `Step 9 실험/튜닝`과 `E5 재확인 전제조건 쌓기`에 집중하면 된다.
