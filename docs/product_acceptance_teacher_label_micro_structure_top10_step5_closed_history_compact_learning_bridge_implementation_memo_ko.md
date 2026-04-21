# Teacher-Label Micro-Structure Top10 Step 5 메모

## 구현 메모

- Step 5의 closed-history 학습 연결 단계는 `close 시 다시 계산`이 아니라 `open row가 이미 갖고 있던 compact micro snapshot을 그대로 closed row로 넘기는 것`이다.
- 이 구조가 맞아야 이후 하루치 compact dataset을 만들 때 raw 차트 없이도 `entry / forecast / wait / exit / result + micro shape snapshot`을 같이 읽을 수 있다.
- 이번 구현에서 micro compact field는 [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py), [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py), [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)를 따라 open -> closed로 연결했다.
- close path는 [trade_logger_close_ops.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_close_ops.py)의 row copy를 그대로 쓰고, 별도 재계산은 하지 않는다.
- 추가로 `blank refresh`가 numeric micro 값을 `0`으로 덮는 버그를 잡아, Step 5는 semantic 뿐 아니라 numeric micro compact 값도 refresh/update/close 전 구간에서 유지된다.

## 원칙

- 기존 흐름은 유지한다.
- `learning_*`는 기존대로 보조 해석용으로만 쓰고, micro compact field를 메인 raw/derived-by-system 보강으로 본다.
- open snapshot update 경로와 close copy 경로가 동일 field를 공유하게 둔다.

## 후속 단계 연결

- Step 6 검증 리그레션 묶음
- teacher-state 25 casebook과 closed-history outcome 연결

## 회귀 결과

- `test_trade_logger_open_snapshots.py` -> `4 passed`
- `test_trade_logger_close_ops_micro_structure.py` -> `1 passed`
- `test_trade_logger_lifecycle.py` -> `3 passed`
- `test_loss_quality_wait_behavior.py` -> `5 passed`
