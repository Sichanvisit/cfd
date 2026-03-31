# Downstream Semantic Inventory

## 1. 목적

이 문서는 이미 손본 상류 semantic layer:

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

위에 올라가는 하류 소비층을 다시 점검해서,

1. 이미 잘 쓰는 것
2. 이미 있는데 잘 못 쓰고 놀고 있는 것
3. 있으면 더 좋은 것

을 단계별로 나누어 정리한 문서다.

핵심 질문은 하나다.

`좋은 semantic을 이미 만들었는데, 아래 레이어들이 그 의미를 실제로 제대로 소비하고 있느냐`


## 2. 전체 구조

현재 점검 대상 downstream은 다음 구간이다.

```text
Market Data
-> Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier

-> Forecast Features
-> Transition Forecast / Trade Management Forecast
-> Observe / Confirm / Action
-> Consumer

Policy / Utility Overlay
raw semantic outputs
-> Layer Mode
-> effective semantic outputs
-> Energy Helper
-> consumer hint usage

Offline path
semantic + forecast snapshots
-> OutcomeLabeler
-> validation / replay / dataset / calibration
```


## 3. 큰 결론

현재 상태를 가장 짧게 말하면 이렇다.

- 상류 semantic layer는 예전보다 훨씬 좋아졌다.
- downstream은 `완전히 비어 있지 않다`.
- 하지만 `계약은 잘 되어 있는데 실제 소비는 약한 구간`이 꽤 있다.

특히 이 구분이 중요하다.

- `잘 쓰는 층`
  - `ForecastFeatures`
  - `ForecastEngine`의 core forecast
  - `WaitEngine`
  - `Consumer contract`
  - `replay_dataset_builder`
- `계약은 있는데 bridge 성격이 강한 층`
  - `Layer Mode`
  - `forecast_effective_policy_v1`
  - `consumer policy overlay`
- `이미 있는데 충분히 못 쓰는 층`
  - `ObserveConfirm`의 v2-native usage
  - `Energy helper`의 rich semantic usage
  - `OutcomeLabeler`의 semantic-aware diagnostics


## 4. 단계별 분류

---

## 4-1. Forecast Features

대상 파일:

- `backend/trading/engine/core/forecast_features.py`

### 이미 잘 쓰는 것

- `ForecastFeaturesV1`가 semantic bundle 역할을 잘 한다.
- 아래 6개를 canonical하게 묶는다.
  - `position_snapshot_v2`
  - `response_vector_v2`
  - `state_vector_v2`
  - `evidence_vector_v1`
  - `belief_state_v1`
  - `barrier_state_v1`
- raw detector score를 직접 읽지 않고 semantic bundle만 넘기는 방향은 좋다.

### 있는데 놀고 있는 것

- `ForecastFeatures` 자체는 bundle 역할은 좋은데, bundle 내부에서 더 압축된 scene feature나 normalized compact feature는 없다.
- 즉 `semantic object 묶음`까진 있는데, `forecast 친화적 compact feature slice`는 약하다.

### 있으면 더 좋은 것

- 추후 추가 후보:
  - `state_scene_signature_v1`
  - `response_scene_signature_v1`
  - `belief_barrier_summary_v1`
- 의미:
  - Forecast 모델/규칙이 object 내부를 너무 많이 직접 파지 않게 도와주는 compact layer


---

## 4-2. Transition Forecast / Trade Management Forecast

대상 파일:

- `backend/trading/engine/core/forecast_engine.py`

### 이미 잘 쓰는 것

- `Position` core label을 잘 씀
  - `position_primary_label`
  - `position_bias_label`
  - `position_secondary_context_label`
  - `position_conflict_score`
- `Response 6축`을 직접 쓴다
  - `lower_hold_up`
  - `lower_break_down`
  - `mid_reclaim_up`
  - `mid_lose_down`
  - `upper_reject_down`
  - `upper_break_up`
- `Belief` core를 잘 쓴다
  - `buy_belief`
  - `sell_belief`
  - `buy_persistence`
  - `sell_persistence`
  - `belief_spread`
  - `transition_age`
- `Barrier` core도 쓴다
  - `buy_barrier`
  - `sell_barrier`
  - `middle_chop_barrier`
  - `conflict_barrier`

### 있는데 놀고 있는 것

- 새 `State v2` 라벨 대부분을 직접 거의 안 쓴다.
  - `session_regime_state`
  - `session_expansion_state`
  - `session_exhaustion_state`
  - `topdown_spacing_state`
  - `topdown_slope_state`
  - `topdown_confluence_state`
  - `spread_stress_state`
  - `volume_participation_state`
  - `execution_friction_state`
  - `event_risk_state`
- 새 `Belief` 확장 출력도 거의 안 쓴다.
  - `dominant_side`
  - `dominant_mode`
  - `buy_streak`
  - `sell_streak`
  - `flip_readiness`
  - `belief_instability`
- 새 `Barrier` score도 거의 안 쓴다.
  - `edge_turn_relief_score`
  - `breakout_fade_barrier_score`
  - `execution_friction_barrier_score`
  - `event_risk_barrier_score`

### 있으면 더 좋은 것

- `State scene-aware modulation`
  - edge turn, breakout continuation, middle chop을 forecast가 더 직접 반영
- `Belief flip-aware forecast`
  - `flip_readiness`, `belief_instability`를 reversal/false-break 확률 보정에 사용
- `Barrier scene-aware forecast`
  - barrier 상세 score를 confirm/fake gap 쪽에 직접 반영


---

## 4-3. Observe / Confirm / Action

대상 파일:

- `backend/trading/engine/core/observe_confirm_router.py`
- `backend/services/entry_service.py`
- `backend/services/entry_engines.py`

### 이미 잘 쓰는 것

- `StateVectorV2` direct input 경로는 정리됐다.
- `ObserveConfirm`은 이제 `State v2` 실행 성향을 직접 읽는다.
  - `confirm_aggression_gain`
  - `wait_patience_gain`
  - `hold_patience_gain`
  - `fast_exit_risk_penalty`
  - `topdown_state_label`
  - `quality_state_label`
  - `patience_state_label`
  - `execution_friction_state`
  - `session_exhaustion_state`
  - `event_risk_state`
- `EntryService`는 consumer side에서
  - `observe_confirm_v2`
  - `layer_mode_policy_v1`
  - `energy_helper_v2`
  를 handoff surface로 잘 받는다.

### 있는데 놀고 있는 것

- `ObserveConfirm` 내부 판단은 아직 legacy response raw 사용 비중이 높다.
  - `response.r_bb20_*`
  - `response.r_box_*`
  - `response.r_candle_*`
- 즉 `response_vector_v2`가 upstream에서 좋아졌는데,
  `ObserveConfirm`은 완전한 v2-native router는 아니다.
- `Belief`의 새 출력도 ObserveConfirm에서 약하게만 쓰인다.
  - `flip_readiness`
  - `belief_instability`
  - `dominant_mode`
  - `buy_streak / sell_streak`
- `Barrier`의 scene-aware 상세 score도 ObserveConfirm 직접 소비는 약하다.

### 있으면 더 좋은 것

- `ObserveConfirm v2-native routing`
  - legacy raw보다 `response_vector_v2`를 primary owner로 더 강하게 올리기
- `Belief-guided confirm release`
  - `flip_readiness`, `buy_streak`, `sell_streak`, `dominant_mode` 활용
- `Barrier scene-aware suppression`
  - `edge_turn_relief_score`
  - `breakout_fade_barrier_score`
  - `event_risk_barrier_score`
  를 confirm/observe split에 직접 사용


---

## 4-4. Consumer

대상 파일:

- `backend/services/consumer_contract.py`
- `backend/services/entry_service.py`
- `backend/services/setup_detector.py`
- `backend/services/exit_service.py`

### 이미 잘 쓰는 것

- Consumer contract는 꽤 잘 잡혀 있다.
- 중요한 원칙이 명확하다.
  - consumer는 raw semantic vector를 직접 재해석하면 안 된다
  - canonical identity owner는 `observe_confirm_v2`
  - policy overlay는 `layer_mode_policy_v1`
  - utility helper는 `energy_helper_v2`
- 이 구조 자체는 매우 좋다.

### 있는데 놀고 있는 것

- consumer는 많은 semantic payload를 row에 싣고 다니지만,
  실제 live gating에서 직접 소비하는 건 제한적이다.
- 이는 계약상 의도된 부분도 있다.
  - raw semantic direct read 금지
- 다만 결과적으로
  - `forecast_effective_policy_v1`
  - `belief/barrier effective payload`
  - `layer_mode_policy_v1`
  가 `실제 행동 보정`보다 `audit/log 중심`에 가깝다.

### 있으면 더 좋은 것

- consumer는 raw semantic owner를 가져가면 안 되므로,
  추가는 항상 `handoff 강화` 방향이어야 한다.
- 추천:
  - `observe_confirm_v2` 개선
  - `layer_mode_policy_v1`의 runtime delta 실제화
  - `energy_helper_v2` hint 정교화
- 즉 consumer 자체를 semantic 판단기로 키우는 건 비추천이다.


---

## 4-5. Policy / Utility Overlay

대상 파일:

- `backend/services/policy_service.py`
- `backend/services/utility_router.py`

### 이미 잘 쓰는 것

- `utility_router.py`는 entry/wait/exit/hold/reverse 계산용 기본 함수가 있다.
- `policy_service.py`는 adaptive threshold / risk tuning 기반이 있다.

### 있는데 놀고 있는 것

- 현재 `policy_service.py`는 closed trade 기반 threshold 조정 중심이다.
- 새 semantic rich layer를 직접 calibration feature로 쓰는 구조는 약하다.
- `utility_router.py`는 generic math helper일 뿐, semantic-rich input을 묶는 정책층은 아니다.

### 있으면 더 좋은 것

- `semantic-aware policy calibration`
  - `Belief`, `Barrier`, `Forecast gap`, `State friction` 요약을 정책 보정에 사용
- `utility composition bundle`
  - 단순 함수 모음이 아니라 실제 runtime에서 explainable utility를 남기는 계층
- `wait vs enter`, `hold vs cut`, `reverse vs hold`에 대해
  semantic summary를 직접 feature로 묶는 얇은 adapter


---

## 4-6. raw semantic outputs -> Layer Mode -> effective semantic outputs

대상 파일:

- `backend/services/layer_mode_contract.py`
- `backend/services/context_classifier.py`

### 이미 잘 쓰는 것

- contract, inventory, dual-write 구조는 매우 잘 되어 있다.
- raw/effective dual-write가 있다.
  - `position_snapshot_effective_v1`
  - `response_vector_effective_v1`
  - `state_vector_effective_v1`
  - `evidence_vector_effective_v1`
  - `belief_state_effective_v1`
  - `barrier_state_effective_v1`
  - `forecast_effective_policy_v1`
- consumer handoff surface도 명시적이다.

### 있는데 놀고 있는 것

- 현재 `build_layer_mode_effective_metadata()`는 사실상 `raw-equivalent bridge`다.
- 특히 `forecast_effective_policy_v1`는 raw forecast들을 그냥 policy bundle처럼 복사해 둔 상태다.
- `layer_mode_policy_v1`도 현재 기본적으로:
  - `overlay_execution_state = bridge_ready_no_runtime_delta`
  - `suppressed_reasons = []`
  - `confidence_adjustments = []`
  - `hard_blocks = []`
  인 bridge 성격이 강하다.
- 즉 contract는 훌륭한데 실제 runtime delta는 약하다.

### 있으면 더 좋은 것

- `Belief assist rollout`
- `Barrier assist/enforce rollout`
- `Forecast assist rollout`
- 다만 이건 semantic owner를 바꾸는 게 아니라,
  effective output과 policy overlay를 진짜 runtime delta로 키우는 작업이어야 한다.


---

## 4-7. Energy Helper

대상 파일:

- `backend/services/energy_contract.py`

### 이미 잘 쓰는 것

- `energy_helper_v2`는 현재 downstream에서 가장 실용적으로 쓰는 helper 중 하나다.
- 입력은 명확하다.
  - `evidence_vector_effective_v1`
  - `belief_state_effective_v1`
  - `barrier_state_effective_v1`
  - `forecast_effective_policy_v1`
  - `observe_confirm_v2.action/side`
- 출력도 실용적이다.
  - `action_readiness`
  - `continuation_support`
  - `reversal_support`
  - `suppression_pressure`
  - `forecast_support`
  - `net_utility`
  - `confidence_adjustment_hint`
  - `soft_block_hint`

### 있는데 놀고 있는 것

- `energy_helper_v2`는 raw semantic을 직접 읽지 않는다는 점은 좋지만,
  반대로 rich semantic scene을 충분히 못 먹는다.
- 직접 안 먹는 대표값:
  - `response_vector_v2`
  - rich `state_vector_v2` 라벨들
  - `flip_readiness`
  - `belief_instability`
  - `edge_turn_relief_score`
  - `breakout_fade_barrier_score`
  - `execution_friction_barrier_score`
  - `event_risk_barrier_score`
- 즉 helper는 이미 useful하지만,
  현재는 `effective belief/barrier/forecast 요약`까지만 쓰는 수준이다.

### 있으면 더 좋은 것

- `energy_helper_v3` 후보:
  - richer scene-aware barrier contribution
  - belief flip-aware contribution
  - state friction/event/session contribution
- 단, 여전히 helper여야 하고 semantic owner를 가져가면 안 된다.


---

## 4-8. consumer hint usage

대상 파일:

- `backend/services/entry_service.py`
- `backend/services/wait_engine.py`
- `backend/services/exit_service.py`

### 이미 잘 쓰는 것

- `EntryService`
  - `energy_helper_v2.action_readiness`
  - `confidence_adjustment_hint`
  - `soft_block_hint`
  를 실제로 live gating에 쓴다.
- `WaitEngine`
  - `energy_helper_v2.metadata.utility_hints.wait_vs_enter_hint`
  를 잘 쓴다.
- `layer_mode_policy_v1`도 hard block / suppression / priority boost를 읽는 경로는 있다.

### 있는데 놀고 있는 것

- `layer_mode_policy_v1` 자체는 현재 bridge-only output이 많아서,
  읽는 경로는 있지만 실제로 active delta가 자주 생기진 않는다.
- `energy_helper_v2`도 consumer usage trace는 좋지만,
  그 hint의 semantic richness는 아직 제한적이다.

### 있으면 더 좋은 것

- `Belief/Barrier/Forecast` assist rollout 이후
  consumer hint usage가 실제로 더 풍부해질 수 있다.
- 즉 지금은 consumer 쪽보다 upstream effective overlay를 먼저 키우는 게 맞다.


---

## 4-9. Offline path

대상 파일:

- `backend/trading/engine/offline/replay_dataset_builder.py`
- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/trading/engine/offline/outcome_label_validation_report.py`

### 이미 잘 쓰는 것

- `replay_dataset_builder.py`는 semantic snapshot을 꽤 잘 보존한다.
- 저장되는 semantic snapshot:
  - `position_snapshot_v2`
  - `response_raw_snapshot_v1`
  - `response_vector_v2`
  - `state_raw_snapshot_v1`
  - `state_vector_v2`
  - `evidence_vector_v1`
  - `belief_state_v1`
  - `barrier_state_v1`
  - `observe_confirm_v1`
  - `layer_mode_policy_v1`
  - `layer_mode_logging_replay_v1`
- 저장되는 forecast snapshot:
  - `forecast_features_v1`
  - `transition_forecast_v1`
  - `trade_management_forecast_v1`
  - `forecast_gap_metrics_v1`

즉 `오프라인 경로에 semantic이 없다`가 아니라,
`replay dataset builder 단계에는 꽤 잘 있다`가 맞다.

### 있는데 놀고 있는 것

- `OutcomeLabeler` 본체는 주로 미래 경로와 close context로 결과를 라벨링한다.
- 즉 semantic snapshot을 `label 생성기`가 직접 의미적으로 많이 쓰진 않는다.
- 결과적으로:
  - semantic snapshot은 저장됨
  - 하지만 semantic-aware diagnostics는 약함

### 있으면 더 좋은 것

- `semantic-aware outcome diagnostics`
  - 예: `lower_hold_up 높았는데 false break`
  - 예: `barrier 높았는데 실제론 진입이 맞았음`
  - 예: `belief persistence 낮았는데 continuation 성공`
- `calibration-ready derived rows`
  - semantic snapshot + outcome label + realized path summary
- `validation report`가 semantic family별 failure cluster를 뽑아주면 매우 좋다.


## 5. 핵심 분류표

### 이미 잘 쓰는 것

- `ForecastFeatures` semantic bundle
- `ForecastEngine`의 core Position/Response/Belief/Barrier usage
- `WaitEngine`의 Belief/State/Energy usage
- `Consumer contract`와 handoff discipline
- `replay_dataset_builder`의 semantic/forecast snapshot preservation

### 있는데 놀고 있는 것

- `ForecastEngine` 안의 rich `State v2` scene labels
- `ObserveConfirm` 안의 v2-native response ownership
- `Belief`의 `flip_readiness`, `belief_instability`, `dominant_mode`, `streak` downstream usage
- `Barrier`의 scene-aware detailed score downstream usage
- `Layer Mode`의 runtime delta
- `forecast_effective_policy_v1`의 실질 overlay 성격
- `Energy helper`의 rich scene awareness
- `OutcomeLabeler`의 semantic-aware diagnostics

### 있으면 더 좋은 것

- scene-aware forecast modulation
- v2-native ObserveConfirm
- semantic-aware policy calibration
- richer energy helper
- offline semantic diagnostics and calibration rows


## 6. 지금 기준 실제 우선순위

### 1순위

- `ObserveConfirm`을 더 v2-native하게 만들기
- 이유:
  - 차트 체감과 실행의 어긋남이 여기가 제일 큼

### 2순위

- `ForecastEngine`에 rich `State v2` + `Belief/Barrier` 확장 score 반영
- 이유:
  - 이미 좋은 semantic이 있는데 예측층은 아직 core만 많이 씀

### 3순위

- `Layer Mode / effective overlay`를 bridge-only에서 assist-ready로 키우기
- 이유:
  - 계약은 훌륭하지만 실제 행동 변화가 아직 약함

### 4순위

- `Energy helper`를 richer scene-aware helper로 키우기
- 이유:
  - consumer는 raw semantic을 직접 읽지 못하므로 helper 품질이 중요함

### 5순위

- `Offline diagnostics` 강화
- 이유:
  - 나중 ML/calibration에 가장 큰 도움을 줌


## 7. 마지막 한 줄 결론

현재 downstream은 `아무것도 없는 상태`가 아니라,

`core 뼈대와 계약은 꽤 잘 갖춰져 있지만, rich semantic을 실제 행동 변화와 calibration-ready 진단으로 끝까지 소비하는 힘은 아직 부족한 상태`

라고 보는 게 가장 정확하다.

즉 다음 작업의 핵심은:

- 새 semantic layer를 더 만드는 것보다
- 이미 만든 `Position / Response / State / Evidence / Belief / Barrier`를
- `Forecast / ObserveConfirm / LayerMode / Energy / Offline path`
에서 더 깊고 일관되게 소비하게 만드는 것이다.
