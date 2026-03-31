# ML Data Storage and Field Roadmap

## 1. 이 문서의 역할

이 문서는 아래 두 가지를 합친 실행 문서다.

- 파일 용량 and 보존 로드맵
- 변수 and 필드 승격 전략

즉 이 문서는 더 이상 "방향 설명 문서"가 아니라,
`1번부터 순서대로 실행할 수 있는 적용 로드맵`이다.

핵심 목표는 아래 4가지다.

1. hot 파일 누수를 먼저 막는다
2. 버리기 아까운 데이터는 warm tier로 살린다
3. 현재 운영 ML과 미래 semantic ML에 쓸 필드를 분리 and 승격한다
4. 나중에 source provenance와 replay 품질이 꼬이지 않게 manifest and key를 붙인다

---

## 2. 현재 상태 한 줄 요약

현재 상태를 한 줄로 요약하면 이렇다.

```text
좋은 데이터는 이미 많다
문제는 부족함이 아니라 hot에 너무 몰려 있고 ML 승격이 덜 되어 있다는 점이다
```

조금 더 구체적으로는 아래와 같다.

- `trade_history.csv`, `trade_closed_history.csv`, `trades.db` 경로는 비교적 건강하다
- 현재 운영 ML은 여기서 만든 작은 dataset만 쓰고 있다
- `entry_decisions.csv`는 191개 컬럼의 giant raw source가 되어 버렸다
- `tail_*`, `legacy_*`, `runtime_status.json`, `events.jsonl`, `bot.log`도 정책이 약하다
- `entry_decisions` 안의 semantic and forecast 자산은 매우 좋은데 아직 compact scalar pack으로 충분히 승격되지 않았다

즉 지금 필요한 것은:

```text
삭제보다 분리
```

그리고:

```text
새 필드 발명보다 기존 고가치 필드 승격이 먼저다
```

---

## 3. 이 로드맵의 공통 원칙

### 3.1 hot은 작게

live append, latest status, 운영 로그는 작고 단순해야 한다.

### 3.2 warm은 풍부하게

replay, 포렌식, shadow compare, validation에 필요한 값은 archive로 남긴다.

### 3.3 ML은 compact만

모델 학습은 raw giant CSV가 아니라 compact dataset만 읽는다.

### 3.4 low-read는 삭제하지 않는다

contract, migration, fallback, debug trace는 곧장 삭제하지 않고 warm or cold metadata로 옮긴다.

### 3.5 구현 순서는 반드시 아래다

```text
누수 차단
-> hot/detail 분리
-> 현재 ML 승격
-> semantic compact export 승격
-> 품질 and trace 변수 추가
-> replay/label and archive discipline 완성
```

---

## 4. 필드 계층을 먼저 고정한다

이 로드맵에서 사용하는 필드 계층은 아래 5가지다.

### 4.1 Hot Keep Pack

hot raw나 latest view에 남겨야 하는 값들이다.

예시:

- time, symbol, action
- core score and threshold
- compact setup and wait
- compact preflight
- compact consumer result
- compact transition and management gap

### 4.2 Warm Metadata Pack

학습 feature보다는 재현성과 검증을 위한 값들이다.

예시:

- `prs_contract_version`
- `prs_canonical_*_field`
- `*_contract_v1`
- `*_scope_contract_v1`
- `*_migration_*`
- `layer_mode_*`
- `shadow_*`
- `last_order_comment`

### 4.3 Current ML Promotion Pack

이미 trade history에 기록되지만 현재 운영 ML에서 거의 안 쓰는 값들이다.

핵심 후보:

- `entry_setup_id`
- `management_profile_id`
- `invalidation_id`
- `entry_wait_state`
- `entry_quality`
- `entry_model_confidence`
- `entry_h1_context_score`
- `entry_m1_trigger_score`
- `entry_h1_gate_pass`
- `entry_topdown_gate_pass`
- `entry_topdown_align_count`
- `entry_topdown_conflict_count`
- `entry_session_name`
- `entry_atr_ratio`
- `entry_slippage_points`
- `net_pnl_after_cost`
- `exit_policy_stage`
- `exit_profile`
- `exit_confidence`
- `giveback_usd`
- `post_exit_mae`
- `post_exit_mfe`
- `shock_score`
- `shock_hold_delta_30`
- `wait_quality_label`
- `loss_quality_label`

### 4.4 Semantic Compact Promotion Pack

이미 `entry_decisions` raw JSON 안에 있지만 아직 compact scalar로 충분히 뽑히지 않은 값들이다.

핵심 후보:

- position pack
  - `position.vector.x_box`
  - `position.vector.x_bb20`
  - `position.vector.x_bb44`
  - `position.vector.x_ma20`
  - `position.vector.x_ma60`
  - `position.interpretation.pos_composite`
  - `position.interpretation.alignment_label`
  - `position.interpretation.conflict_kind`
  - `position.energy.lower_position_force`
  - `position.energy.upper_position_force`
  - `position.energy.position_conflict_score`
- response pack
  - `lower_break_down`
  - `lower_hold_up`
  - `mid_lose_down`
  - `mid_reclaim_up`
  - `upper_break_up`
  - `upper_reject_down`
- state pack
  - `alignment_gain`
  - `breakout_continuation_gain`
  - `trend_pullback_gain`
  - `range_reversal_gain`
  - `conflict_damp`
  - `noise_damp`
  - `liquidity_penalty`
  - `volatility_penalty`
  - `countertrend_penalty`
- evidence pack
  - `buy_total_evidence`
  - `buy_continuation_evidence`
  - `buy_reversal_evidence`
  - `sell_total_evidence`
  - `sell_continuation_evidence`
  - `sell_reversal_evidence`
- forecast summary pack
  - `position_primary_label`
  - `position_secondary_context_label`
  - `position_conflict_score`
  - `middle_neutrality`

### 4.5 New Quality and Trace Pack

지금 거의 없거나 summary가 약한 값들이다.

핵심 후보:

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`
- `signal_age_sec`
- `bar_age_sec`
- `decision_latency_ms`
- `order_submit_latency_ms`
- `missing_feature_count`
- `data_completeness_ratio`
- `used_fallback_count`
- `transition_label_status`
- `management_label_status`
- `label_unknown_count`
- `label_positive_count`
- `label_negative_count`
- `label_is_ambiguous`
- `detail_blob_bytes`
- `snapshot_payload_bytes`

---

## 5. 1번부터 실행하는 적용 순서

## Step 1. 기준선 and manifest부터 만든다

### 목적

이후 모든 정리 and 승격 작업을 추적 가능하게 만든다.

### 대상 파일

- `data/manifests/`
- `docs/ml_data_storage_management_plan_ko.md`
- 필요하면 size audit script 추가

### 작업

1. active 관리 대상 파일 목록을 고정한다
2. `rollover`, `archive`, `export`, `retention` manifest 디렉터리를 만든다
3. 현재 baseline size를 기록한다
4. hot file warning 기준을 정한다

### 같이 고정할 필드 결정

- `Hot Keep Pack`
- `Warm Metadata Pack`
- `Current ML Promotion Pack`
- `Semantic Compact Promotion Pack`

이 4가지를 문서 기준선으로 못 박는다.

### 산출물

- manifest 디렉터리 골격
- baseline report
- field pack 분류표

### 완료 기준

- 이후 발생하는 정리 and export 작업이 전부 기록될 수 있다

---

## Step 2. hot 파일 누수를 먼저 막는다

### 목적

더 이상 giant hot file이 계속 커지지 않게 막는다.

### 대상 파일

- `scripts/rollover_entry_decisions.py`
- `scripts/rollover_trade_history.py`
- `backend/app/trading_application_runner.py`
- `adapters/file_observability_adapter.py`
- 필요하면 `scripts/cleanup_*` 계열 신규 추가

### 작업

1. `entry_decisions.csv`를 size or day 기준으로 rollover한다
2. rollover 직후 `parquet + zstd` archive를 만든다
3. `entry_decisions.tail_*` retention을 7일 or 최근 N개로 제한한다
4. `entry_decisions.legacy_*` retention을 7일 or 최근 N개로 제한한다
5. `events.jsonl`에 rollover and retention을 붙인다
6. `bot.log`를 `RotatingFileHandler`로 바꾼다

### 여기서 중요한 필드 원칙

- 지금 단계에서는 필드를 삭제하지 않는다
- 단지 giant raw가 계속 쌓이는 구조를 멈춘다

### 산출물

- active `entry_decisions.csv` 상한
- archive parquet 첫 경로
- cleanup 규칙
- rotate되는 `bot.log`
- rotate되는 `events.jsonl`

### 완료 기준

- active `entry_decisions.csv`가 1GB 안팎 이하로 유지될 수 있다
- debug and observability 로그가 무제한 누적되지 않는다

---

## Step 3. hot and detail을 분리한다

### 목적

latest view와 replay/detail payload를 분리한다.

### 대상 파일

- `backend/app/trading_application.py`
- `backend/services/entry_engines.py`
- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`

### 작업

1. `runtime_status.json`을 slim 중심 구조로 재편한다
2. 필요하면 `runtime_status.detail.json` or 별도 snapshot 경로를 둔다
3. `entry_decisions`를 hot columns와 detail payload로 나눈다
4. detail payload는 warm archive or sidecar로 보내는 설계를 고정한다

### hot에 남길 것

- core score and threshold
- setup and wait summary
- preflight summary
- consumer summary
- compact forecast gap
- compact observe/energy/belief/barrier summary

### detail로 내릴 것

- raw `position_snapshot_v2`
- raw `response_vector_v2`
- raw `state_vector_v2`
- raw `evidence_vector_v1`
- raw `forecast_features_v1`
- raw `observe_confirm_v2`
- contract and migration fields
- shadow and comment fields

### 산출물

- runtime slim/detail schema
- entry_decisions hot/detail inventory
- backward compatibility 정리표

### 완료 기준

- latest status가 detail payload 때문에 무거워지지 않는다
- hot append는 routing and quick read에 필요한 값만 남는다

---

## Step 4. 현재 운영 ML을 먼저 강하게 만든다

### 목적

지금 이미 돌아가는 entry and exit ML이 놓치고 있는 고가치 trade field를 승격한다.

### 대상 파일

- `ml/dataset_builder.py`
- `ml/train.py`
- `backend/services/trade_csv_schema.py`
- 필요하면 `ml/runtime.py`

### 4-A. entry structure pack 승격

추가 후보:

- `entry_stage`
- `entry_setup_id`
- `management_profile_id`
- `invalidation_id`
- `entry_wait_state`
- `entry_quality`
- `entry_model_confidence`

### 4-B. context quality pack 승격

추가 후보:

- `regime_at_entry`
- `entry_h1_context_score`
- `entry_m1_trigger_score`
- `entry_h1_gate_pass`
- `entry_h1_gate_reason`
- `entry_topdown_gate_pass`
- `entry_topdown_gate_reason`
- `entry_topdown_align_count`
- `entry_topdown_conflict_count`
- `entry_topdown_seen_count`
- `entry_session_name`
- `entry_weekday`
- `entry_session_threshold_mult`
- `entry_atr_ratio`
- `entry_atr_threshold_mult`

### 4-C. execution quality pack 승격

추가 후보:

- `entry_request_price`
- `entry_fill_price`
- `entry_slippage_points`
- `exit_request_price`
- `exit_fill_price`
- `exit_slippage_points`
- `cost_total`
- `net_pnl_after_cost`

### 4-D. exit policy and post-exit pack 승격

추가 후보:

- `signed_exit_score`
- `decision_winner`
- `utility_exit_now`
- `utility_hold`
- `utility_reverse`
- `utility_wait_exit`
- `u_cut_now`
- `u_wait_be`
- `u_wait_tp1`
- `u_reverse`
- `exit_policy_stage`
- `exit_policy_profile`
- `exit_profile`
- `exit_wait_state`
- `exit_wait_selected`
- `exit_wait_decision`
- `p_recover_be`
- `p_recover_tp1`
- `p_deeper_loss`
- `p_reverse_valid`
- `exit_policy_regime`
- `exit_threshold_triplet`
- `exit_route_ev`
- `exit_confidence`
- `exit_delay_ticks`
- `peak_profit_at_exit`
- `giveback_usd`
- `post_exit_mae`
- `post_exit_mfe`
- `shock_score`
- `shock_hold_delta_30`
- `wait_quality_label`
- `wait_quality_score`
- `loss_quality_label`
- `loss_quality_score`

### 작업 순서

1. `dataset_builder.py`에서 low-risk 필드부터 추가한다
2. `train.py` feature list를 넓힌다
3. 기존 모델 대비 metrics 비교를 남긴다
4. 성능 and 안정성이 확인되면 운영 모델 재학습 경로에 반영한다

### 산출물

- `entry_dataset.csv` v2
- `exit_dataset.csv` v2
- 새 feature 포함 모델 metrics

### 완료 기준

- 운영 ML이 `entry_reason + regime + indicator` 수준을 넘어선다
- raw giant CSV를 안 읽고도 품질 개선이 시작된다

---

## Step 5. entry_decisions semantic compact export를 확장한다

### 목적

semantic and forecast 자산을 giant JSON이 아닌 compact scalar pack으로 승격한다.

### 대상 파일

- `scripts/export_entry_decisions_ml.py`

### 추가할 field pack

#### position pack

- `vector.x_box`
- `vector.x_bb20`
- `vector.x_bb44`
- `vector.x_ma20`
- `vector.x_ma60`
- `vector.x_sr`
- `vector.x_trendline`
- `interpretation.pos_composite`
- `interpretation.alignment_label`
- `interpretation.bias_label`
- `interpretation.conflict_kind`
- `energy.lower_position_force`
- `energy.upper_position_force`
- `energy.middle_neutrality`
- `energy.position_conflict_score`

#### response pack

- `lower_break_down`
- `lower_hold_up`
- `mid_lose_down`
- `mid_reclaim_up`
- `upper_break_up`
- `upper_reject_down`

#### state pack

- `alignment_gain`
- `breakout_continuation_gain`
- `trend_pullback_gain`
- `range_reversal_gain`
- `conflict_damp`
- `noise_damp`
- `liquidity_penalty`
- `volatility_penalty`
- `countertrend_penalty`

#### evidence pack

- `buy_total_evidence`
- `buy_continuation_evidence`
- `buy_reversal_evidence`
- `sell_total_evidence`
- `sell_continuation_evidence`
- `sell_reversal_evidence`

#### forecast summary pack

- `position_primary_label`
- `position_secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `management_horizon_bars`
- `signal_timeframe`

### 작업 순서

1. nested JSON에서 scalar만 추출한다
2. raw nested payload 전체는 compact export에 넣지 않는다
3. selected columns and row count manifest를 기록한다
4. symbol별 and setup별 결측률을 함께 기록한다

### 산출물

- `ml_exports/forecast/*.parquet`
- `ml_exports/replay/*.parquet`
- semantic compact schema

### 완료 기준

- semantic and forecast 데이터를 giant JSON 없이 ML-friendly하게 쓸 수 있다

---

## Step 6. 새 quality and trace 변수를 추가한다

### 목적

지금 부족한 freshness, latency, join, quality summary를 추가한다.

### 대상 파일

- `backend/app/trading_application_runner.py`
- `backend/app/trading_application.py`
- `backend/services/entry_engines.py`
- `backend/trading/trade_logger.py`
- 필요하면 `trade_csv_schema.py`, `export_entry_decisions_ml.py`

### 추가할 변수

#### join and provenance

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`
- `replay_row_key`

#### freshness and latency

- `signal_age_sec`
- `bar_age_sec`
- `decision_latency_ms`
- `order_submit_latency_ms`

#### data quality

- `missing_feature_count`
- `data_completeness_ratio`
- `used_fallback_count`
- `compatibility_mode`

#### storage health

- `detail_blob_bytes`
- `snapshot_payload_bytes`
- `row_payload_bytes`

### 이유

- "조금 더 빨리 샀어야 했다"를 보려면 latency and freshness가 필요하다
- fallback이 많은 row와 정상 row를 학습에서 구분하려면 quality summary가 필요하다
- 저장 구조가 다시 무거워지는 지점을 보려면 payload bytes가 필요하다

### 산출물

- quality and trace 변수 초안
- compact export 포함 여부 결정표

### 완료 기준

- delay, fallback, payload size를 정량적으로 볼 수 있다

### 적용 결과

2026-03-18 기준으로 Step 6의 1차 구현은 완료했다.

- `entry_decisions.csv` hot row에 `decision_row_key`, `runtime_snapshot_key`, `trade_link_key`, `replay_row_key`를 기록한다.
- `entry_decisions.csv` hot row와 detail sidecar에서 `signal_age_sec`, `bar_age_sec`, `decision_latency_ms`, `order_submit_latency_ms`를 함께 남긴다.
- `entry_decisions.csv` hot row와 trade history 계열에서 `missing_feature_count`, `data_completeness_ratio`, `used_fallback_count`, `compatibility_mode`를 함께 남긴다.
- `entry_decisions.csv`, `runtime_status.json`, `trade_history.csv` 계열에 `detail_blob_bytes`, `snapshot_payload_bytes`, `row_payload_bytes`를 남겨 payload 비대화를 추적할 수 있게 했다.
- `runtime_status.json` slim view와 `runtime_status.detail.json` detail view가 같은 trace/quality 요약을 보도록 맞췄다.
- `scripts/export_entry_decisions_ml.py` compact export도 위 trace/quality 필드를 함께 싣도록 맞췄다.

### 이번 Step 6에서 고정된 해석 원칙

- `decision_row_key`: entry decision row의 stable join key
- `runtime_snapshot_key`: latest signal row와 runtime status를 잇는 stable key
- `trade_link_key`: trade history row와 entry decision row를 잇는 key
- `replay_row_key`: replay/export/validation이 공유하는 row join key
- `compatibility_mode`: `native_v2`, `hybrid`, `observe_confirm_v1_fallback` 중 하나로 해석한다.

### Step 6 이후 바로 보는 지표

- 평균 `signal_age_sec`
- 평균 `decision_latency_ms`
- 평균 `order_submit_latency_ms`
- symbol별 `used_fallback_count`
- symbol별 `data_completeness_ratio`
- 최근 hot row의 `snapshot_payload_bytes`와 `row_payload_bytes`

### Step 6 다음 후속 작업

- Step 7 label compact summary와 `replay_row_key`를 실제 replay export manifest에 더 강하게 연결한다.
- Step 4 preview 모델 재학습 시 `signal_age_sec`, `decision_latency_ms`, `data_completeness_ratio`, `used_fallback_count`를 후보 feature로 비교한다.
- 운영 대시보드나 size audit report에서 payload bytes 상위 row를 바로 볼 수 있게 만든다.

---

## Step 7. replay and label 품질까지 compact하게 묶는다

### 목적

차세대 semantic or forecast ML에 필요한 label quality와 replay provenance를 compact하게 만든다.

### 대상 파일

- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- `scripts/build_replay_dataset.py`
- 필요하면 validation report script

### 추가할 compact summary

- `transition_label_status`
- `management_label_status`
- `label_unknown_count`
- `label_positive_count`
- `label_negative_count`
- `label_is_ambiguous`
- `label_source_descriptor`
- `is_censored`
- `row_key`

### 작업 순서

1. nested outcome metadata에서 quality summary를 compact scalar로 꺼낸다
2. replay row에 stable key를 붙인다
3. validation report와 training export가 같은 summary를 보게 맞춘다

### 산출물

- replay compact label pack
- label quality manifest

### 완료 기준

- replay and label 데이터가 nested blob이 아니라 training and validation friendly한 구조가 된다

---

## Step 8. warm archive and 운영 가시화를 마무리한다

### 목적

버리기 아까운 데이터를 질서 있게 남기고,
다시 파일이 커질 때 늦게 알지 않게 만든다.

### 대상 파일

- archive and cleanup scripts
- analysis/report scripts
- 필요하면 size audit report script

### 작업

1. `replay_intermediate/*.jsonl` retention 규칙을 붙인다
2. `analysis/*`, `reports/*` 보존 기간을 나눈다
3. monthly checkpoint를 만든다
4. largest files top N report를 만든다
5. last rollover, cleanup 결과, export 실패를 요약한다

### 산출물

- warm archive discipline
- size audit report
- retention report

### 완료 기준

- hot, warm, ML, cold 계층이 실제로 분리돼 돌아간다
- 수동 탐색 없이도 파일 건강 상태를 확인할 수 있다

### 적용 결과

2026-03-18 기준으로 Step 8의 1차 운영 도구는 [`run_ml_storage_maintenance.py`](C:/Users/bhs33/Desktop/project/cfd/scripts/run_ml_storage_maintenance.py)로 구현했다.

- `replay_intermediate/*.jsonl` retention
  - 기본값: `30일` 또는 `최근 20개`
- `analysis/*` retention
  - 기본값: `30일` 또는 `최근 40개`
- `reports/*` retention
  - 기본값: `90일` 또는 `최근 60개`
- 현재 실행 결과는 [`ml_storage_retention_20260318_190548.json`](C:/Users/bhs33/Desktop/project/cfd/data/manifests/retention/ml_storage_retention_20260318_190548.json)에 남긴다.
- health report latest는 [`ml_storage_health_latest.json`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/ml_storage_health_latest.json), [`ml_storage_health_latest.md`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/ml_storage_health_latest.md)에 남긴다.
- monthly checkpoint는 [`ml_storage_checkpoint_2026_03.json`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/checkpoints/ml_storage_checkpoint_2026_03.json), [`ml_storage_checkpoint_2026_03.md`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/checkpoints/ml_storage_checkpoint_2026_03.md)에 남긴다.

### 현재 dry-run에서 바로 보인 핵심 상태

- hot 최대 리스크는 여전히 [`entry_decisions.csv`](C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv) 하나다.
- warm tier의 주 용량은 `entry_decisions.tail_*`, `entry_decisions.legacy_*`, `replay_intermediate/*.jsonl`가 차지한다.
- dry-run 기준으로는 retention 삭제 대상이 아직 없었고, 현재 파일들은 기본 보존 규칙 안에 있다.
- latest manifest 기준으로 export는 성공 기록이 있고 rollover/archive는 아직 최근 manifest가 없다.

### Step 8 실적용 전 원칙

- 먼저 `--dry-run`으로 보고서를 갱신한다.
- 실제 삭제 적용은 retention 결과를 한 번 보고 나서 진행한다.
- hot 문제는 Step 8 alone으로 해결되지 않고, Step 2 rollover 실적용과 같이 봐야 한다.

---

## 6. 바로 시작할 첫 스프린트

첫 스프린트는 아래 5개를 한 묶음으로 가는 것이 맞다.

1. Step 1의 manifest and baseline
2. Step 2의 `entry_decisions` rollover and archive
3. Step 2의 `legacy_*`, `tail_*` cleanup
4. Step 2의 `bot.log` rotation
5. Step 2의 `events.jsonl` rollover

이 스프린트가 끝나면 구조적 누수를 먼저 막을 수 있다.

그 다음 스프린트는 Step 4와 Step 5를 병렬이 아니라 순차로 간다.

1. `trade_history` 기반 운영 ML 승격
2. `entry_decisions` semantic compact export 승격

이 순서가 좋은 이유는:

- `trade_history`는 이미 평평한 표라 구현이 쉽고 효과가 빠르다
- `entry_decisions`는 nested JSON compact화가 필요하므로 그 다음이 맞다

---

## 7. 이번 로드맵에서 가장 중요한 우선 필드 10개

현재 운영 ML 고도화 기준 우선 10개는 아래와 같다.

1. `entry_setup_id`
2. `entry_quality`
3. `entry_model_confidence`
4. `entry_h1_context_score`
5. `entry_topdown_align_count`
6. `entry_atr_ratio`
7. `exit_confidence`
8. `giveback_usd`
9. `wait_quality_label`
10. `loss_quality_label`

semantic compact 승격 기준 우선 6개는 아래와 같다.

1. `position.vector.x_box`
2. `response.mid_reclaim_up`
3. `response.upper_reject_down`
4. `state.noise_damp`
5. `evidence.buy_total_evidence`
6. `forecast_features.position_conflict_score`

새로 추가할 quality and trace 기준 우선 6개는 아래와 같다.

1. `decision_row_key`
2. `signal_age_sec`
3. `decision_latency_ms`
4. `missing_feature_count`
5. `used_fallback_count`
6. `label_unknown_count`

---

## 8. 하지 말아야 할 순서

- giant raw CSV를 계속 학습 입력으로 직접 쓰기
- hot 정리 전에 ML export만 계속 늘리기
- contract and migration 필드를 가치 없다고 보고 삭제하기
- replay intermediate를 크기만 보고 폐기하기
- 최신 상태 파일에 detail payload를 계속 밀어넣기

---

## 9. 결론

이 로드맵의 핵심은 간단하다.

```text
먼저 누수를 막고
그 다음 hot과 detail을 나누고
그 다음 기존 고가치 필드를 현재 ML에 승격하고
마지막으로 semantic and replay 품질을 compact pack으로 만든다
```

즉 이 프로젝트는 새 데이터를 마구 더 쌓는 단계가 아니라,
이미 있는 좋은 데이터를 `어디에 둘지`, `어떻게 요약할지`, `어떤 순서로 ML에 올릴지`를 정리하는 단계다.
