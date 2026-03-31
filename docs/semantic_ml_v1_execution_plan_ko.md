# Semantic ML v1 실행 분해안

## 1. 목적

이 문서는 현재 운영 중인 tabular ML을 바로 뜯어고치는 대신,
semantic 기반 차세대 ML을 안전하게 붙이기 위한 실행 분해안이다.

핵심 원칙은 아래 3가지다.

1. 의미 결정은 규칙 엔진이 계속 owner로 가진다.
2. ML은 `timing`, `entry quality`, `exit management`, `meta calibration`만 맡는다.
3. 기존 live ML은 바로 폐기하지 않고 baseline으로 유지한 채 shadow compare를 거친다.

---

## 2. 최종 목표 그림

```text
Semantic Engine
-> Compact Feature Layer
-> Semantic ML v1
-> Shadow Compare
-> Bounded Live Rollout
-> Old Live ML Retirement
```

---

## 3. 추천 폴더 구조

새 세대는 기존 `ml/`을 건드리되, 처음부터 분리된 폴더로 시작하는 게 좋다.

```text
ml/
  semantic_v1/
    contracts.py
    feature_packs.py
    dataset_builder.py
    dataset_splits.py
    train_timing.py
    train_entry_quality.py
    train_exit_management.py
    evaluate.py
    shadow_compare.py
    runtime_adapter.py
    promotion_guard.py
```

기존 live baseline은 그대로 유지한다.

- `ml/dataset_builder.py`
- `ml/train.py`
- `ml/runtime.py`
- `models/ai_models.joblib`

---

## 4. 실행 단계

이 문서의 Phase 4, Phase 5에 해당하는 승격 and 롤백 기준은
별도 문서 `docs/semantic_ml_v1_promotion_gates_ko.md`를 기준으로 본다.

## Phase 1. Semantic 계약을 먼저 고정한다

### 목적

새 ML이 무엇을 먹고 무엇을 절대 안 먹는지 먼저 고정한다.

### 대상 파일

- `docs/ml_application_and_csv_map_ko.md`
- `scripts/export_entry_decisions_ml.py`
- 신규 `ml/semantic_v1/contracts.py`
- 신규 `ml/semantic_v1/feature_packs.py`

### 작업

1. semantic input pack을 4묶음으로 고정한다.
2. trace and quality pack을 별도 묶음으로 고정한다.
3. target label family를 3개로 고정한다.
4. rule-owner field와 model-owner field를 문서상으로 분리한다.

### semantic input pack

- `position pack`
- `response pack`
- `state pack`
- `evidence pack`
- `forecast summary pack`
- `trace and quality pack`

### model target family

- `timing_now_vs_wait`
- `entry_quality`
- `exit_management`

### rule-owner로 남길 것

- `side`
- `entry_setup_id`
- `management_profile_id`
- `invalidation_id`
- hard guard and kill-switch

### 산출물

- `semantic_feature_contract_v1`
- `semantic_target_contract_v1`
- `rule_owner_vs_model_owner_table`

### 완료 기준

- 이후 dataset builder와 runtime adapter가 같은 계약을 공유한다.

---

## Phase 2. 학습용 compact dataset을 3개로 나눈다

### 목적

raw giant log가 아니라 semantic compact dataset만 보고 학습하게 만든다.

### 대상 파일

- `scripts/export_entry_decisions_ml.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- `backend/trading/engine/offline/outcome_labeler.py`
- 신규 `ml/semantic_v1/dataset_builder.py`
- 신규 `ml/semantic_v1/dataset_splits.py`

### 작업

1. compact export에서 semantic scalar만 사용한다.
2. replay and label summary를 join해서 학습 row를 만든다.
3. dataset을 아래 3개로 분리한다.
4. split은 시간 기준으로 한다.
5. symbol and regime holdout을 같이 본다.

### 새 dataset

- `timing_dataset.parquet`
- `entry_quality_dataset.parquet`
- `exit_management_dataset.parquet`

### row key 원칙

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`
- `replay_row_key`

위 4개는 dataset에도 그대로 남긴다.

### 제외할 누설 필드

- post-exit only field
- label direct text
- future knowledge field
- 운영 후행 품질 필드 중 target을 설명해버리는 값

### 산출물

- `data/datasets/semantic_v1/timing_dataset.parquet`
- `data/datasets/semantic_v1/entry_quality_dataset.parquet`
- `data/datasets/semantic_v1/exit_management_dataset.parquet`
- dataset manifest and missingness report

### 완료 기준

- `entry_decisions.csv`를 직접 읽지 않아도 semantic 학습셋이 생성된다.

---

## Phase 3. semantic tabular model v1을 학습한다

### 목적

현재 live ML을 대체할 후보 모델을 offline에서 만든다.

### 대상 파일

- 신규 `ml/semantic_v1/train_timing.py`
- 신규 `ml/semantic_v1/train_entry_quality.py`
- 신규 `ml/semantic_v1/train_exit_management.py`
- 신규 `ml/semantic_v1/evaluate.py`
- 신규 `models/semantic_v1/`

### 작업

1. 첫 버전은 sequence model이 아니라 tabular model로 간다.
2. tree-based model 또는 안정적인 tabular model을 쓴다.
3. probability calibration을 분리한다.
4. metric은 accuracy보다 calibration과 business slice를 우선 본다.

### 필수 평가 축

- overall auc
- calibration error
- symbol별 auc
- regime별 auc
- setup별 auc
- top-k precision
- expected value proxy
- fallback-heavy row vs clean row 비교

### 산출물

- `models/semantic_v1/timing_model.*`
- `models/semantic_v1/entry_quality_model.*`
- `models/semantic_v1/exit_management_model.*`
- `models/semantic_v1/metrics.json`

### 완료 기준

- semantic model이 baseline과 비교 가능한 형태로 고정된다.

---

## Phase 4. shadow compare를 구축한다

### 목적

기존 live ML과 새 semantic ML을 같은 row에서 비교한다.

### 대상 파일

- 신규 `ml/semantic_v1/shadow_compare.py`
- 신규 `ml/semantic_v1/runtime_adapter.py`
- `backend/app/trading_application.py`
- `backend/services/entry_try_open_entry.py`
- 필요하면 `data/analysis/*`

### 작업

1. 현재 live ML 결과와 semantic ML 결과를 동시에 기록한다.
2. 동일 row에서 아래 비교치를 남긴다.
3. live 판단은 아직 baseline이 owner로 유지한다.

### 비교 포인트

- semantic이 더 일찍 들어가려 했는가
- semantic이 더 늦게 막았는가
- false positive가 늘었는가
- symbol마다 개선이 같은가
- regime마다 개선이 같은가
- setup마다 개선이 같은가
- trace quality가 낮을 때 모델이 무너지는가

### 산출물

- `semantic_shadow_compare_report_*.json`
- `semantic_shadow_compare_report_*.md`
- rollout candidate threshold table

### 완료 기준

- "어디서 좋아지고 어디서 망가지는지"를 row 수준으로 말할 수 있다.

---

## Phase 5. bounded live rollout을 시작한다

### 목적

새 semantic ML을 한 번에 의사결정 owner로 두지 않고 제한적으로 반영한다.

### 대상 파일

- 신규 `ml/semantic_v1/promotion_guard.py`
- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_service.py`
- `backend/app/trading_application.py`
- `backend/core/config.py`

### 작업

1. 첫 반영은 `log only`로 시작한다.
2. 다음은 `alert only`로 간다.
3. 그다음 `threshold adjustment only`를 연다.
4. 마지막에야 `partial live weight`를 준다.

### bounded rule

- model은 `side`를 직접 정하지 않는다.
- model은 `setup_id`를 직접 정하지 않는다.
- model은 `management_profile_id`를 직접 정하지 않는다.
- model은 threshold, wait, size, exit urgency만 제한적으로 보정한다.
- `missing_feature_count`가 높거나 `compatibility_mode`가 나쁘면 자동 fallback 한다.

### 산출물

- semantic live gate config
- rollout 단계별 manifest
- fallback rules and kill switch

### 완료 기준

- 새 semantic ML이 live에 붙어도 rule baseline으로 즉시 복귀 가능하다.

---

## Phase 6. 기존 live ML을 legacy baseline으로 내린다

### 목적

semantic ML이 안정화된 뒤 현재 tabular ML의 역할을 줄인다.

### 대상 파일

- `ml/runtime.py`
- `ml/retrain_and_deploy.py`
- `models/ai_models.joblib`
- 필요하면 신규 `models/legacy_live_ml/`

### 작업

1. 현재 live ML을 제거하지 말고 legacy baseline으로 보존한다.
2. 비교 실험이나 emergency fallback 경로로 남긴다.
3. 운영 기본값만 semantic ML 쪽으로 넘긴다.

### 산출물

- legacy baseline archive
- semantic ML default runtime
- rollback instructions

### 완료 기준

- 현재 live ML은 더 이상 주력은 아니지만 언제든 rollback 가능한 baseline으로 남아 있다.

---

## 5. 지금 바로 착수 순서

가장 현실적인 첫 구현 순서는 아래 5개다.

1. `ml/semantic_v1/contracts.py`
2. `ml/semantic_v1/feature_packs.py`
3. `ml/semantic_v1/dataset_builder.py`
4. `ml/semantic_v1/train_timing.py`
5. `ml/semantic_v1/evaluate.py`

즉 첫 스타트는 `timing model`부터다.

이유는 아래와 같다.

- 네가 가장 자주 느끼는 불만이 "조금만 더 일찍 샀어야 했다"라서 timing이 제일 체감도가 높다.
- timing은 `position/response/state/evidence/forecast + trace/quality`와 연결이 잘 된다.
- entry direction 자체를 새로 맞히는 것보다 위험이 낮다.

---

## 6. 하지 말아야 할 시작점

- 현재 live ML을 바로 삭제하기
- giant JSON 그대로 학습하기
- semantic engine이 정하던 `side/setup/invalidation`을 모델에게 넘기기
- sequence model부터 시작하기
- shadow compare 없이 live 투입하기

---

## 7. 한 줄 결론

지금 필요한 건 "운영 ML 재학습"이 아니라
`semantic compact dataset -> timing model -> shadow compare -> bounded rollout`
순서로 가는 세대교체 설계다.
