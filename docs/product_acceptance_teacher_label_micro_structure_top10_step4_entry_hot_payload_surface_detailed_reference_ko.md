# Teacher-Label Micro-Structure Top10 Step 4 상세 기준서

## 목표

`Step 4`의 목표는 Step 3에서 `state_vector_v2.metadata`와 `forecast_features_v1` 쪽으로 수확한
micro-structure semantic/source를 `entry_decisions.csv` hot row에서 바로 읽을 수 있는 flat surface로
올리는 것이다.

이 단계의 핵심은 새 판단 로직을 만드는 것이 아니라:

- 이미 계산된 micro 값을 다시 계산하지 않고
- hot payload에서 바로 집계/필터링 가능한 최소 flat key만 노출하고
- verbose 구조는 기존 JSON payload에 그대로 남겨두는 것이다.

## Step 4 owner

- `backend/services/entry_engines.py`
- `backend/services/storage_compaction.py`

`context_classifier.py`는 Step 3에서 이미 micro semantic/source를 `state_vector_v2.metadata`로 수확했으므로,
이번 Step 4에서는 직접 owner가 아니라 upstream provider로 본다.

## hot payload에 올릴 최소 surface

### semantic state

- `micro_breakout_readiness_state`
- `micro_reversal_risk_state`
- `micro_participation_state`
- `micro_gap_context_state`

### compact source stat

- `micro_body_size_pct_20`
- `micro_doji_ratio_20`
- `micro_same_color_run_current`
- `micro_same_color_run_max_20`
- `micro_range_compression_ratio_20`
- `micro_volume_burst_ratio_20`
- `micro_volume_burst_decay_20`
- `micro_gap_fill_progress`

## source 규칙

우선순위는 아래로 고정한다.

1. `state_vector_v2.metadata`
2. `forecast_features_v1.secondary_harvest`
3. 빈 값 유지

이번 단계에서는 Step 3 semantic/source가 정상적으로 `state_vector_v2.metadata`에 있기 때문에
실제 구현은 1번 경로만으로 충분해야 한다.

## compact 원칙

- hot row에는 숫자/짧은 상태 문자열만 올린다.
- 구조형 설명은 `state_vector_v2`, `forecast_features_v1` compact JSON에 남긴다.
- `gap_fill_progress`는 anchor가 없으면 `None` 허용
- semantic state가 비어 있으면 빈 문자열 허용

## 비목표

- teacher-state 25개 직접 라벨링
- 새로운 micro 계산 추가
- forecast 재튜닝
- entry gate 변경

## 검증 기준

- `ENTRY_DECISION_LOG_COLUMNS`에 새 flat column이 보인다.
- recorder 경로에서 row 하나를 쓰면 CSV hot row에 값이 실제로 기록된다.
- 기존 compact JSON surface(`state_vector_v2`, `forecast_features_v1`)는 깨지지 않는다.
