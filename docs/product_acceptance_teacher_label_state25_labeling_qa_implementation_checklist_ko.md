# Teacher-Label State25 Labeling QA 체크리스트

## Step 1. 지금 고정할 운영 규칙 반영

- [ ] look-ahead bias 금지 규칙을 문서에 명시한다.
- [ ] 라벨러/리뷰어/관리자 3역할 검수 흐름을 문서화한다.
- [ ] `20% 재라벨링`, `하위 confidence 5% 최종 검수`를 고정한다.

## Step 2. confusion watchlist 반영

- [ ] `12 ↔ 23`
- [ ] `5 ↔ 10`
- [ ] `16 ↔ 2`

위 3쌍을 사전 혼동 패턴으로 문서에 고정한다.

## Step 3. 희소 패턴 감시 규칙 반영

- [ ] `3`, `17`, `19`를 희소 패턴 감시 대상으로 문서화한다.
- [ ] 첫 10K 후 `1% 미만` 발생률 경고 규칙을 적는다.
- [ ] 희소하더라도 즉시 삭제/병합하지 않는다는 원칙을 적는다.

## Step 4. 라벨링 후 검증 체크 반영

- [ ] 패턴 25개별 발생률
- [ ] primary/secondary 조합 빈도
- [ ] 행동 bias 분포
- [ ] 자산별 패턴 분포
- [ ] confusion pair 요약

위 항목을 post-label QA checklist로 고정한다.

## Step 5. 실험 항목 분리

- [ ] 자산별 ATR 캘리브레이션은 실험 항목으로 분리한다.
- [ ] train/val/test split은 실험 항목으로 분리한다.
- [ ] XGBoost baseline 목표치는 참고값으로만 둔다.
- [ ] execution 반영 조건은 실험 후 결정으로 둔다.
