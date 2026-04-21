# Teacher-Label State25 Compact Schema 실행 로드맵

## 목표

`teacher_pattern_*` 필드를 compact dataset에 안정적으로 올리고, 이후 `state25 라벨러`와 `labeling QA`가 바로 이어질 수 있게 만든다.

## 단계별 실행

### Step S1. schema field 확정

필수 canonical 필드:

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

### Step S2. schema owner 편입

owner:

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)

할 일:

- `TRADE_COLUMNS` 추가
- text/numeric normalize 규칙 추가
- nullable 처리 규칙 확정

### Step S3. open snapshot carry 준비

owner:

- [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)
- [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)

할 일:

- teacher-pattern 필드가 들어오면 open row에 보존
- close row에 동일 필드 carry

주의:

- 아직 라벨러가 없더라도 schema는 먼저 실어둔다
- 값이 없는 row는 빈 값으로 허용한다

### Step S4. compact row visibility 확인

목표:

- `trade_closed_history.csv` 한 줄에 teacher-pattern 컬럼이 보이는지 확인

검증:

- schema normalization
- open -> close carry
- 빈 값 안전 처리

### Step S5. 다음 단계 연결

schema가 닫히면 다음으로 바로 이어지는 것은:

1. `state25 라벨러 초안`
2. `labeling QA`
3. `experiment tuning`

즉 schema는 Step 8 QA의 선행 토대다.

## 구현 원칙

1. compact canonical home은 `closed-history`다.
2. `primary + secondary` 구조를 그대로 유지한다.
3. provenance 필드는 필수로 둔다.
4. 실행 편의보다 라벨 품질 추적 가능성을 우선한다.

## 결론

지금 순서는:

1. schema를 먼저 닫는다
2. 그 다음 라벨러를 붙인다
3. 그 다음 QA와 실험으로 간다

즉 이 문서는 state25 본 구현으로 넘어가기 직전의 실무 토대다.
