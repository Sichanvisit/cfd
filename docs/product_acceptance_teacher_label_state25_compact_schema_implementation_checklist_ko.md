# Teacher-Label State25 Compact Schema 체크리스트

## Step 1. 필드 정의 확정

- [ ] `teacher_pattern_id`
- [ ] `teacher_pattern_name`
- [ ] `teacher_pattern_group`
- [ ] `teacher_pattern_secondary_id`
- [ ] `teacher_pattern_secondary_name`
- [ ] `teacher_direction_bias`
- [ ] `teacher_entry_bias`
- [ ] `teacher_wait_bias`
- [ ] `teacher_exit_bias`
- [ ] `teacher_transition_risk`
- [ ] `teacher_label_confidence`
- [ ] `teacher_lookback_bars`
- [ ] `teacher_label_version`
- [ ] `teacher_label_source`
- [ ] `teacher_label_review_status`

## Step 2. schema owner 반영

- [ ] [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)에 컬럼 추가
- [ ] text/numeric normalize 규칙 추가
- [ ] nullable/empty 처리 규칙 고정

## Step 3. carry path 준비

- [ ] [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py) 에 teacher field passthrough 준비
- [ ] [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py) 에 open snapshot carry 준비
- [ ] closed row로 copy 시 필드 손실 없는지 확인

## Step 4. 최소 회귀 준비

- [ ] schema normalize test
- [ ] open snapshot preserve test
- [ ] close row carry test
- [ ] empty/null safety test

## Step 5. 다음 단계 연결

- [ ] schema 완료 후 `state25 라벨러 초안` 문서 시작
- [ ] `labeling QA` 문서가 이 필드를 기준으로 동작하는지 연결
- [ ] `experiment tuning` 문서가 같은 필드명을 보도록 확인
