# Teacher-Label Micro-Structure Top10 Step 4 메모

## 구현 메모

- Step 4는 새 micro 계산 단계가 아니다.
- 이미 `state_vector_v2.metadata`에 올라간 micro semantic/source를 `entry_decisions.csv` hot row에서
  바로 보이게 평평하게 노출하는 단계다.
- 이 단계가 닫히면 이후 teacher-state casebook / daily compact train set에서
  `entry_decisions.csv`만 읽어도 micro context를 함께 볼 수 있다.

## 구현 원칙

- full payload를 더 무겁게 만들지 않는다.
- `storage_compaction.build_entry_decision_hot_payload`에서 추출/표면화한다.
- compact JSON은 유지하고, hot row에는 바로 필터 가능한 column만 추가한다.

## 이번 Step 4 반영 범위

- semantic state:
  - `micro_breakout_readiness_state`
  - `micro_reversal_risk_state`
  - `micro_participation_state`
  - `micro_gap_context_state`
- source stat:
  - `micro_body_size_pct_20`
  - `micro_doji_ratio_20`
  - `micro_same_color_run_current`
  - `micro_same_color_run_max_20`
  - `micro_range_compression_ratio_20`
  - `micro_volume_burst_ratio_20`
  - `micro_volume_burst_decay_20`
  - `micro_gap_fill_progress`

## 검증 결과

- `pytest -q tests/unit/test_entry_engines.py` -> `15 passed`
- `pytest -q tests/unit/test_forecast_contract.py` -> `44 passed`

## 후속 단계 연결

- Step 5 `closed-history compact 학습 연결`
- teacher-state 25와 micro structure의 행동 bias 검증
