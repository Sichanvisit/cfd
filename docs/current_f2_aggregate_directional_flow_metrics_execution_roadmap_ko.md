# F2. Aggregate Conviction / Flow Persistence 실행 로드맵

## 1. 목적

F2의 목적은 `flow_structure_gate_v1` 다음 층에서

- `aggregate_conviction_v1`
- `flow_persistence_v1`

를 공용 계약으로 분리 고정하는 것이다.

이 단계는 threshold rollout이 아니라, 이후 `FLOW_CONFIRMED / BUILDING / UNCONFIRMED / OPPOSED` 분류에 필요한 공용 숫자 surface를 안정적으로 만드는 단계다.

---

## 2. 진행 원칙

### 원칙 1. structure-first 유지

F2는 F1 뒤에 붙는다.
숫자는 F1을 대체하지 않는다.

### 원칙 2. conviction / persistence 분리

둘을 너무 일찍 하나의 score로 접지 않는다.

### 원칙 3. conviction 최소 구성축 고정

`aggregate_conviction`는 최소 아래를 포함해야 한다.

- `dominance_support`
- `structure_support`
- `decomposition_alignment`

### 원칙 4. persistence has recency/decay

`flow_persistence`는 최근 N-bar에 더 큰 가중치를 두고, 오래된 persistence는 decay한다.

### 원칙 5. read-only 유지

F2는 execution/state25를 바꾸지 않는다.

---

## 3. 단계별 로드맵

### F2-1. contract 고정

목적:

- F2의 enum, row fields, authority order를 먼저 고정한다.

핵심 작업:

- `aggregate_directional_flow_metrics_contract_v1`
- `aggregate_conviction_bucket_enum_v1`
- `flow_persistence_state_enum_v1`
- row-level field 목록 정의

완료 기준:

- contract가 문서/코드/runtime에서 같은 이름으로 보인다.

### F2-2. dominance_support 계산 고정

목적:

- dominance layer 증거를 conviction component로 번역한다.

핵심 작업:

- `dominance_shadow_gap_v1`
- `dominance_shadow_dominant_side_v1`
- `dominance_shadow_dominant_mode_v1`
- `state_strength_continuation_integrity_v1`
- `state_strength_reversal_evidence_v1`

를 이용해 `aggregate_dominance_support_v1` 계산

완료 기준:

- side mismatch나 reversal pressure가 dominance_support를 명확히 낮춘다.

### F2-3. structure_support 계산 고정

목적:

- local structure와 hold/swing/drive를 conviction component로 번역한다.

핵심 작업:

- `breakout_hold_quality_v1`
- `few_candle_structure_bias_v1`
- relevant swing intact state
- `body_drive_state_v1`

를 이용해 `aggregate_structure_support_v1` 계산

완료 기준:

- strong/stable hold + continuation favor + intact swing이 높은 structure_support를 만든다.

### F2-4. decomposition_alignment 계산 고정

목적:

- slot의 intent/stage/texture/location을 conviction component로 번역한다.

핵심 작업:

- `intent`
- `stage`
- `texture`
- `location`

기반 정렬 점수화

완료 기준:

- `ACCEPTANCE` + `POST_BREAKOUT` + `CLEAN/FRICTION` 조합은 alignment가 높고
- `EXTENSION` + `EXTENDED` 조합은 낮아진다.

### F2-5. ambiguity / veto penalty 고정

목적:

- ambiguity와 caution 성격이 conviction을 어떻게 약화시키는지 수치화한다.

핵심 작업:

- `aggregate_ambiguity_penalty_v1`
- `aggregate_veto_penalty_v1`

산출

완료 기준:

- `HIGH ambiguity`, `BOUNDARY_WARNING`, `REVERSAL_OVERRIDE`가 conviction을 강하게 제한한다.

### F2-6. aggregate_conviction_v1 최종 산출

목적:

- 3개 support와 2개 penalty를 종합한 공용 conviction score를 고정한다.

핵심 작업:

- `aggregate_conviction_v1`
- `aggregate_conviction_bucket_v1`

산출

완료 기준:

- conviction이 high/mid/low bucket으로 일관되게 surface된다.

### F2-7. flow_persistence_v1 + recency weight 산출

목적:

- persistence를 단순 누적이 아닌 recency-weighted persistence로 surface한다.

핵심 작업:

- `tempo`
- `breakout_hold_quality`
- relevant swing persistence
- `body_drive_state`
- `flow_persistence_recency_weight_v1`

를 이용해

- `flow_persistence_v1`
- `flow_persistence_state_v1`

산출

완료 기준:

- `ACCEPTANCE + PERSISTING`은 높은 persistence
- `INITIATION + EARLY`는 building 성격
- `EXTENSION`은 decay 반영으로 fresh persistence가 과대평가되지 않음

### F2-8. runtime export 연결

목적:

- F2 contract/summary/artifact가 runtime detail에 안정적으로 export되게 한다.

핵심 작업:

- `trading_application.py` import
- report init
- attach/generate 순서 추가
- detail payload export 추가

완료 기준:

- runtime detail에
  - `aggregate_directional_flow_metrics_contract_v1`
  - `aggregate_directional_flow_metrics_summary_v1`
  - `aggregate_directional_flow_metrics_artifact_paths`
  가 보인다.

### F2-9. 테스트 고정

목적:

- F2가 숫자만 높다고 구조 권한을 침범하지 않는지 확인한다.

핵심 테스트:

- strong acceptance row -> conviction/persistence 높음
- mixed weak row -> conviction mid or low, persistence fragile/building
- extension row -> persistence는 남아도 fresh conviction/alignment가 제한됨
- artifact write test
- runtime export test

완료 기준:

- 단위 테스트와 runtime export 테스트 통과

---

## 4. 산출물

문서:

- `current_f2_aggregate_directional_flow_metrics_detailed_plan_ko.md`
- `current_f2_aggregate_directional_flow_metrics_execution_roadmap_ko.md`

코드:

- `backend/services/aggregate_directional_flow_metrics_contract.py`

테스트:

- `tests/unit/test_aggregate_directional_flow_metrics_contract.py`
- `tests/unit/test_trading_application_runtime_status.py` export 보강

artifact:

- `data/analysis/shadow_auto/aggregate_directional_flow_metrics_latest.json`
- `data/analysis/shadow_auto/aggregate_directional_flow_metrics_latest.md`

---

## 5. 다음 단계 연결

F2가 끝나면 다음은 자연스럽게 아래 순서로 간다.

1. F3
   retained window 기준 provisional conviction/persistence band calibration

2. F4
   symbol-specific threshold band 조정

3. F5
   exact pilot match를 hard gate에서 bonus로 재배치

즉 F2는 최종 flow acceptance가 아니라,
그 acceptance를 안전하게 할 수 있게 해주는 공용 숫자 설명층이다.
