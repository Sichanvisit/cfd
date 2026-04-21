# Teacher-Label Micro-Structure Top10 Step 5 상세 기준서

## 목표

`Step 5`의 목표는 `trade_closed_history.csv` 한 줄이 close 결과만 남기는 것이 아니라,
entry 시점에 이미 확보했던 micro-structure compact snapshot도 같이 들고 닫히게 만드는 것이다.

이번 단계의 핵심은:

- close 시점에 micro를 새로 다시 계산하지 않고
- open row에 이미 실려 있는 micro compact surface를 closed row로 그대로 보존하고
- 이후 학습/분석은 기존 `position -> forecast -> decision -> wait -> exit -> close result` 흐름 위에서
  micro snapshot을 보조 입력으로 같이 읽게 하는 것이다.

## Step 5 owner

- `backend/services/trade_csv_schema.py`
- `backend/trading/trade_logger.py`
- `backend/trading/trade_logger_open_snapshots.py`

`trade_logger_close_ops.py`는 open row 복사본이 closed row로 내려가는 구조이므로 직접 owner라기보다
보존 경로로 본다.

## closed-history에 남길 micro compact field

### semantic state

- `micro_breakout_readiness_state`
- `micro_reversal_risk_state`
- `micro_participation_state`
- `micro_gap_context_state`

### source stat

- `micro_body_size_pct_20`
- `micro_doji_ratio_20`
- `micro_same_color_run_current`
- `micro_same_color_run_max_20`
- `micro_range_compression_ratio_20`
- `micro_volume_burst_ratio_20`
- `micro_volume_burst_decay_20`
- `micro_gap_fill_progress`

## 설계 원칙

1. close row에서 새 micro 계산을 하지 않는다.
2. entry/open 시점 snapshot이 있으면 그것을 canonical compact state로 취급한다.
3. open row에 없던 값은 빈 값으로 허용한다.
4. `learning_*`는 메인 학습 입력으로 승격하지 않는다.
   이번 Step 5는 기존 흐름 위에 micro compact snapshot을 붙이는 단계다.

## 데이터 흐름

1. entry / open snapshot 시점에 micro field가 OPEN row에 기록됨
2. close 시 open row copy가 `trade_closed_history.csv`로 이동
3. `normalize_trade_df`가 새 column을 안정적으로 정규화
4. 이후 closed-history compact 학습셋 builder는 기존 result field와 함께 micro snapshot을 읽음

## 비목표

- micro teacher-state 25 직접 라벨링
- 새 learning score 추가 발명
- exit 결과 재채점 로직 변경

## 검증 기준

- `TRADE_COLUMNS`에 micro compact field가 보인다.
- open snapshot upsert에서 값이 OPEN row에 들어간다.
- closed row append 후에도 same field가 보존된다.
- `normalize_trade_df`가 빈 값/숫자/문자열을 안전하게 다룬다.
