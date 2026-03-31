# Semantic ML v1 승격 기준표

## 1. 목적

이 문서는 semantic ML v1이 "좋아 보인다" 수준이 아니라,
"나빠진 모델은 절대 live에 못 올라오게 막는" 승격 기준표다.

핵심 원칙은 아래 4가지다.

1. 의미 결정은 계속 규칙 엔진이 owner로 가진다.
2. 새 ML은 `timing`, `entry quality`, `exit management` 보정만 맡는다.
3. 승격은 `offline -> shadow -> bounded live -> expansion` 순서로만 간다.
4. 숫자 기준을 못 넘기면 아무리 직관적으로 좋아 보여도 승격하지 않는다.

---

## 2. 이 문서가 막고 싶은 실패

- 몇 번의 예쁜 사례만 보고 live에 올리는 것
- 전체 평균은 좋아졌는데 `XAUUSD`, `BTCUSD`, `NAS100` 중 하나가 크게 망가지는 것
- 더 빨리 들어가긴 했지만 가짜 반등 추격이 늘어나는 것
- label 품질이 낮은 row까지 먹여서 "늦어도 괜찮다"를 배우는 것
- fallback and compatibility row가 많아졌는데도 모델을 계속 믿는 것

---

## 3. 승격 철학

이 프로젝트에서 "자동으로 좋아진다"에 가장 가까운 방법은
"좋은 모델만 올리는 것"이 아니라 "나쁜 모델은 절대 못 올라오게 막는 것"이다.

따라서 아래 4단계를 반드시 통과해야 한다.

1. `Gate A`: 데이터 and 라벨 품질 통과
2. `Gate B`: offline 평가 통과
3. `Gate C`: shadow compare 통과
4. `Gate D`: bounded live rollout 통과

어느 Gate에서든 실패하면 즉시 이전 단계로 되돌린다.

---

## 4. 공통 전제 조건

### rule-owner로 남기는 것

- `side`
- `entry_setup_id`
- `management_profile_id`
- `invalidation_id`
- hard guard
- kill-switch

### model-owner로 허용하는 것

- `timing_now_vs_wait`
- `entry_quality`
- `exit_management`
- `meta calibration`
- bounded threshold adjustment
- bounded wait adjustment
- bounded penalty adjustment

### 반드시 같은 key를 공유할 것

- `decision_row_key (진입 판단 row 고유키)`
- `runtime_snapshot_key (실시간 상태 스냅샷 고유키)`
- `trade_link_key (거래 연결 고유키)`
- `replay_row_key (리플레이 row 고유키)`

---

## 5. Gate A. 데이터 and 라벨 품질 통과선

### 목적

모델이 잘못 배우지 않게 학습 row의 최소 건강 상태를 강제한다.

### 필수 조건

1. `label_is_ambiguous = true` row는 기본 학습셋에서 제외한다.
2. `is_censored = true` row는 학습 기본셋에서 제외하거나 별도 실험셋으로 분리한다.
3. `data_completeness_ratio < 0.85` row는 기본 학습셋에서 제외한다.
4. `missing_feature_count` 상위 10% row는 기본 학습셋에서 제외하거나 가중치를 낮춘다.
5. `compatibility_mode = true` row 비중이 5%를 넘으면 승격 평가를 보류한다.
6. 심볼별 최소 학습 row 수를 충족해야 한다.

### 권장 최소 row 수

- 전체 학습 row: `10,000+`
- 심볼별 row: `1,500+`
- 주요 setup별 row: `500+`
- 주요 regime별 row: `500+`

### 보류 조건

- `label_unknown_count > 0` 비중이 20% 초과
- `used_fallback_count > 0` 비중이 15% 초과
- `decision_row_key`와 `trade_link_key` join 성공률이 95% 미만
- 시간순 split 이후 검증 구간 row 수가 너무 적음

### Gate A 산출물

- `data quality report`
- `label quality report`
- `dataset inclusion/exclusion summary`

---

## 6. Gate B. offline 평가 통과선

### 목적

baseline보다 좋아졌다는 말을 숫자로 증명한다.

### 공통 평가 축

- overall AUC or PR-AUC
- calibration error
- symbol별 성능
- regime별 성능
- setup별 성능
- clean row vs fallback-heavy row 비교
- 비용 반영 후 성과

### 공통 합격 원칙

1. 전체 지표가 baseline보다 좋아야 한다.
2. `XAUUSD`, `BTCUSD`, `NAS100` 중 어느 하나도 큰 역행이 있으면 불합격이다.
3. symbol, regime, setup slice 중 2개 이상에서 뚜렷한 붕괴가 있으면 불합격이다.
4. calibration이 baseline보다 나빠지면 불합격이다.

### Timing Model 합격선

- `early entry gain`이 baseline 대비 `+5%` 이상
- `false early entry rate` 증가는 `+2%p` 이내
- `timing_now_vs_wait` calibration error는 baseline 이하
- `signal_age_sec` 상위 지연 구간에서도 붕괴가 없어야 함

### Entry Quality Model 합격선

- entry quality 관련 핵심 분류 지표가 baseline 대비 `+3%` 이상 개선
- top decile candidate precision이 baseline보다 높아야 함
- `entry_setup_id` 주요 상위 5개 setup 중 4개 이상에서 성능 유지 또는 개선
- 비용 반영 후 `net_pnl_after_cost` proxy가 baseline보다 나빠지면 불합격

### Exit Management Model 합격선

- `giveback_usd` 평균이 baseline 대비 감소
- `peak_profit_at_exit` 대비 giveback 비율이 개선
- `exit_confidence` calibration이 baseline보다 좋아야 함
- `shock_score` 상위 구간에서 무리한 hold 증가가 없어야 함

### 권장 보수적 기준

- 전체 핵심 지표 개선폭이 작더라도,
  심볼별 안정성과 calibration이 더 좋으면 통과 후보로 본다.
- 한두 개 지표만 크게 좋아지고 나머지가 불안정하면 불합격으로 본다.

---

## 7. Gate C. shadow compare 통과선

### 목적

offline에서 좋아 보이는 모델이 실제 runtime row에서도 같은 성향을 내는지 확인한다.

### 최소 shadow 기간

- 기간: `2주+`
- 또는 의사결정 row: `2,000+`
- 또는 심볼별 `300+`

위 셋 중 적어도 두 조건을 만족하는 것을 권장한다.

### shadow에서 꼭 볼 항목

- `더 일찍 진입했는가`
- `가짜 반등 추격이 늘지 않았는가`
- `wait가 줄었는데 품질이 유지되는가`
- `compatibility_mode`, `used_fallback_count`가 높은 row에서 이상 행동이 없는가
- `decision_latency_ms`, `signal_age_sec` 구간별로 성향이 일관적인가

### shadow 합격선

1. baseline 대비 `조기 진입 개선`이 확인될 것
2. 비용 반영 후 손익 proxy가 baseline보다 나쁘지 않을 것
3. 심볼별로 심각한 붕괴가 없을 것
4. 특정 session or regime에서만 좋아지고 나머지가 무너지지 않을 것
5. `missing_feature_count` 상위 row에서 과잉 자신감이 늘지 않을 것

### shadow 즉시 불합격 조건

- 주요 심볼 중 하나에서 손실 proxy가 크게 악화
- false positive 급증
- calibration 붕괴
- fallback row에서 비정상적으로 높은 score 출력

---

## 8. Gate D. bounded live rollout 통과선

### 목적

새 semantic ML을 한 번에 갈아끼우지 않고, 보정 폭이 제한된 상태로 천천히 올린다.

### 단계

#### Stage 0. log only

- runtime에 예측만 기록
- 규칙 엔진과 기존 live ML에는 영향 없음

#### Stage 1. alert only

- 예측 차이가 클 때만 알림
- 실제 threshold and wait는 바꾸지 않음

#### Stage 2. bounded adjustment

- `threshold`, `wait`, `penalty`만 소폭 조정
- 조정 폭 상한을 둔다

#### Stage 3. partial live influence

- 일부 심볼, 일부 setup, 일부 시간대에서만 제한 적용

### bounded adjustment 상한 예시

- threshold 조정: 절대값 기준 `10%` 이내
- wait 조정: `1~2 bar` 이내
- penalty 조정: baseline의 `15%` 이내

### Stage 2 or 3 통과선

1. baseline 대비 비용 반영 성과가 유지 또는 개선
2. false positive 증가가 제한 범위 이내
3. 심볼별 붕괴 없음
4. fallback-heavy row에서 과잉 진입 없음
5. 수동 복기 기준으로도 "너무 공격적"이라는 패턴이 반복되지 않음

---

## 9. 즉시 롤백 기준

아래 중 하나라도 만족하면 즉시 이전 baseline으로 복귀한다.

- 하루 단위 손실 proxy가 baseline 대비 급격히 악화
- 3일 rolling 기준 false positive가 급증
- `XAUUSD`, `BTCUSD`, `NAS100` 중 하나에서 연속 붕괴
- `compatibility_mode = true` 비중 급증
- `missing_feature_count` 급증
- `decision_latency_ms` 급증으로 timing 품질 붕괴
- `used_fallback_count` 급증
- join 실패율 증가
- 운영자가 수동 복기에서 명확한 이상 패턴을 확인

### 롤백 구현 원칙

1. `kill-switch` 한 번으로 baseline 복귀 가능해야 한다.
2. 새 semantic ML 비활성화가 config flag 하나로 가능해야 한다.
3. rollback 후 비교 리포트를 자동 저장해야 한다.

---

## 10. 심볼별 최소 통과 원칙

### 목적

전체 평균이 아니라 네가 실제 중요하게 보는 심볼에서 무너지지 않게 한다.

### 최소 원칙

- `XAUUSD`: false breakout 추격 증가 금지
- `BTCUSD`: lower rebound 과잉매수 증가 금지
- `NAS100`: 늦은 추격 진입 감소 여부를 따로 본다

### 합격 해석 원칙

- 전체가 좋아도 위 3개 중 하나가 심하게 나빠지면 승격 금지
- 전체 개선폭이 작아도 위 3개가 안정적이면 통과 후보

---

## 11. 운영 체크리스트

### 승격 전 체크

- Gate A 통과
- Gate B 통과
- Gate C 통과
- rollout 범위와 상한 확정
- rollback flag 확인

### 승격 중 체크

- 일별 비교 리포트
- 심볼별 비교 리포트
- fallback and compatibility 비율
- payload and latency 건강 상태

### 승격 후 체크

- 1일
- 3일
- 1주

위 3개 시점에서 반드시 baseline 비교를 다시 수행한다.

---

## 12. 관련 파일

- `docs/semantic_ml_v1_execution_plan_ko.md`
- `docs/ml_application_and_csv_map_ko.md`
- `scripts/export_entry_decisions_ml.py`
- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- 추후 신규 `ml/semantic_v1/promotion_guard.py`

---

## 13. 한 줄 결론

이 프로젝트에서 "자동으로 좋아진다"에 가장 가까운 방법은
좋아질 거라고 믿는 것이 아니라,
"좋아졌음을 숫자로 증명하기 전에는 절대 live에 못 올라오게 하는 것"이다.
