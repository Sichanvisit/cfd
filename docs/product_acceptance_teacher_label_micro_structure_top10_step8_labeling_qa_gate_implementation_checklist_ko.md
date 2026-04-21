# Teacher-Label Micro-Structure Top10 Step 8 체크리스트
- [x] Step 8 범위를 `teacher_pattern labeling QA gate`로 고정
- [x] `teacher_pattern_labeling_qa.py` 서비스 추가
- [x] hard fail 규칙 고정
- [x] warning 규칙 고정
- [x] watchlist pair (`12-23`, `5-10`, `2-16`) 집계 추가
- [x] rare watch pattern (`3`, `17`, `19`) 경고 추가
- [x] provenance (`source/version/lookback`) 검증 추가
- [x] entry / wait / exit bias 분포 요약 추가
- [x] lowest-confidence 5% review target 추출 추가
- [x] `tests/unit/test_teacher_pattern_labeling_qa.py` 추가
- [x] Step 8 회귀 통과

## 테스트 묶음

- `tests/unit/test_teacher_pattern_labeling_qa.py`
- `tests/unit/test_teacher_pattern_labeler.py`
- `tests/unit/test_trade_logger_open_snapshots.py`

## 테스트 결과

- `pytest -q tests/unit/test_teacher_pattern_labeling_qa.py` -> `3 passed`
- `pytest -q tests/unit/test_teacher_pattern_labeler.py` -> `3 passed`
- `pytest -q tests/unit/test_trade_logger_open_snapshots.py` -> `5 passed`

## 현재 데이터셋 점검 메모

- 현재 [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv) full backlog에 QA report를 돌리면 `labeled_rows = 0`으로 나온다.
- 이는 Step 8 gate 실패가 아니라 `state25 라벨러 도입 이전 closed-history backlog`가 아직 teacher-pattern으로 backfill되지 않았기 때문이다.
- 즉 Step 8 구현은 완료, 현재 runtime row 축적과 이후 backfill/experiment 단계는 별도 후속이다.
