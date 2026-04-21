# Teacher-Label Micro-Structure Top10 구현 로드맵

## 목표

`micro-structure Top10`을 현재 state 체계에 무리 없이 얹고, `entry / wait / exit / close result`까지 이어지게 만든다.

## 구현 원칙

1. 새 원천데이터 수집보다 기존 1분봉 OHLCV 가공을 우선한다.
2. 1차 owner는 `state_raw_snapshot`이다.
3. `entry_decisions`에는 compact surface를 올리고, verbose raw는 metadata 쪽에 유지한다.
4. 학습 입력은 기존 시스템이 만들던 값이 중심이고, micro-structure는 그 흐름을 보강하는 canonical state로 둔다.

## 구현 분기 원칙

| 분기 | 의미 | 대상 |
|---|---|---|
| `그대로 사용 + 점진 보강` | 이미 있는 값을 1차로 쓰고 direct stat을 나중에 보강 | `direction_run_stats`, `range_compression_ratio_20` |
| `보강 후 승격` | response/state 재료를 20봉 집계형 canonical state로 승격 | `body`, `upper/lower wick`, `doji`, `volume burst/decay`, `swing high/low retest` |
| `anchor 추가 후 재구축` | 기존 재료는 있으나 기준점이 부족해서 anchor를 붙여 정식 state로 만듦 | `gap_fill_progress` |

## 단계별 실행

### Step 0. 계산 범위 고정

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

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step0_scope_lock_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step0_scope_lock_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step0_scope_lock_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step0_scope_lock_implementation_checklist_ko.md)

### Step 1. 1분봉 집계 helper 추가

owner:

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

상태:

- 구현 완료
- `micro_structure_v1` helper와 fallback 규칙 추가
- `test_trading_application_micro_structure.py` 회귀 통과

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step1_ohlcv_helper_implementation_memo_ko.md)

### Step 2. state raw snapshot 편입

owner:

- [builder.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
- [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)

상태:

- 구현 완료
- `StateRawSnapshot` canonical field와 metadata surface 연결 완료
- `test_state_contract.py` 회귀 통과

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step2_state_raw_snapshot_implementation_memo_ko.md)

### Step 3. state_vector / forecast harvest 연결

owner:

- [coefficients.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/coefficients.py)
- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

상태:

- 구현 완료
- micro semantic state harvest와 vector bias 보정 완료
- `test_state_contract.py`, `test_forecast_contract.py` 회귀 통과

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step3_vector_forecast_harvest_implementation_memo_ko.md)

### Step 4. entry hot payload surface 추가

owner:

- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)

상태:

- 구현 완료
- `entry_decisions.csv` hot payload flat micro surface 연결 완료
- `test_entry_engines.py` 회귀 통과

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step4_entry_hot_payload_surface_implementation_memo_ko.md)

### Step 5. closed-history compact 학습 연결

owner:

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)
- [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)

상태:

- 구현 완료
- schema / normalize / open snapshot / close carry 연결 완료
- `blank refresh -> numeric zero overwrite` 보정 완료
- 회귀 통과 완료

원칙:

- `learning_*` 같은 신규 합성 점수는 메인 입력으로 두지 않음
- 기존 시스템 값 + micro-structure raw/derived만 보강

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step5_closed_history_compact_learning_bridge_implementation_memo_ko.md)

### Step 6. 테스트 / 검증 묶음

owner:

- state builder 회귀
- forecast feature harvest 회귀
- entry hot payload column 회귀
- closed-history schema / carry 회귀

검증 축:

- 계산값이 최근 20봉 기준으로 일관적인지
- NaN / 빈 윈도우에서도 안전한지
- 25개 teacher-state 중 대표 패턴 케이스에서 값이 직관적으로 맞는지

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step6_regression_bundle_implementation_memo_ko.md)

상태:

- 구현 완료
- cross-stage regression bundle 추가 완료
- Step 1~5 핵심 회귀 재실행 통과 완료

### Step 7. teacher-state casebook 연결

owner:

- [product_acceptance_teacher_label_25_minute_state_mapping_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_25_minute_state_mapping_ko.md)

기준 문서:

- [product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step7_teacher_state_casebook_bridge_implementation_memo_ko.md)
- [product_acceptance_teacher_label_state25_micro_structure_casebook_bridge_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_micro_structure_casebook_bridge_ko.md)

상태:

- 초기 bridge 작성 완료
- 25개 pattern 전체에 대해 Top10 핵심 2~4개와 보조 state 연결 완료

### Step 7A. teacher-pattern compact schema

owner:

- [product_acceptance_teacher_label_state25_compact_schema_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_detailed_reference_ko.md)

기준 문서:

- [product_acceptance_teacher_label_state25_compact_schema_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_compact_schema_execution_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_execution_roadmap_ko.md)
- [product_acceptance_teacher_label_state25_compact_schema_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_state25_compact_schema_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_compact_schema_implementation_memo_ko.md)

상태:

- 기준 문서 작성 완료
- 다음 구현 선행 토대로 고정 완료

### Step 8. teacher-pattern labeling QA gate

owner:

- [product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md)

기준 문서:

- [product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_labeling_qa_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_state25_labeling_qa_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_implementation_memo_ko.md)

상태:

- 기준 문서 작성 완료
- look-ahead bias 금지 / confusion pair / 희소 패턴 감시 / post-label checklist 고정 완료

#### Step 8 implementation follow-up

- [product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_detailed_reference_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_micro_structure_top10_step8_labeling_qa_gate_implementation_memo_ko.md)
- QA gate report builder implemented
- regression tests passed
- full backlog remains unlabeled until runtime accumulation or backfill

### Step 9. teacher-pattern experiment tuning

owner:

- [product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md)

기준 문서:

- [product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md)

상태:

- 실험 분기 문서 작성 완료
- 1K ATR 캘리브레이션 / 10K QA / baseline / top confusion tuning / execution handoff 순서 고정 완료

## 추천 구현 순서

### 1차 최소 배치

- `body_size_pct_20`
- `doji_ratio_20`
- `direction_run_stats`
- `range_compression_ratio_20`
- `volume_burst_decay_20`

### 2차 반전 보강

- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`

### 3차 세션 / 갭 보강

- `gap_fill_progress`

## 결론

이 작업은 아예 별도 체계를 새로 만드는 것이 아니라, 기존 state 체계 위에 `차트 모양 자체`를 직접 수치화한 layer를 얹는 작업이다. 현재는 Step 1~7 구현/기준 정리가 닫혔고, 다음 자연스러운 단계는 Step 7A compact schema, Step 8 labeling QA gate, Step 9 experiment tuning이다.
