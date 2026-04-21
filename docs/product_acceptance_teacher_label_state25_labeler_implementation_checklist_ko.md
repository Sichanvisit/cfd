# Teacher-Label State25 Labeler Checklist

## Step 1. owner 고정

- [x] rule owner를 [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py) 로 고정
- [x] attach owner를 [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py) 로 고정

## Step 2. first-pass label attach

- [x] 명시 teacher 값이 없을 때만 auto attach
- [x] primary / secondary / bias / confidence 반환
- [x] provenance (`version/source/review_status`) 같이 채우기
- [x] unlabeled fallback 허용

## Step 3. rule draft 범위

- [x] micro semantic state 사용
- [x] micro numeric state 사용
- [x] optional wick / retest / gap richer input 허용
- [x] existing entry context (`setup/session/direction`) 보조 사용
- [x] close result / future info 미사용

## Step 4. regression

- [x] direct labeler unit test
- [x] open snapshot auto attach test
- [x] 기존 compact schema regression 재통과

## Step 5. 다음 단계 연결

- [ ] Step 8 labeling QA에서 confusion / rare pattern 검토
- [ ] Step 9 experiment tuning에서 threshold / pair 조정
- [ ] 필요 시 preview surface 확장 여부 판단
