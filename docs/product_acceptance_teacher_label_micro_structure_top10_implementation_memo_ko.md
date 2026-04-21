# Teacher-Label Micro-Structure Top10 구현 메모

## 현재 판단

현재 시스템은 `시장 분위기`, `방향성`, `구조 위치`, `진입/대기/청산 해석`, `결과`까지는 충분히 좋다.

이번 보강의 본질은 새로운 regime 체계를 다시 만드는 것이 아니라, `캔들 몸통/꼬리/연속성/압축/재시험/갭 메움` 같은 차트 모양 정보를 직접 숫자로 state에 편입하는 데 있다.

## 왜 지금 해야 하나

`1분봉 25개 teacher-state 최종판`을 실제 학습 대상으로 쓰려면, 아래 패턴들은 지금 구조만으로는 간접 해석은 가능하지만 직접성이 부족하다.

- 페이크아웃 반전
- 더블탑/더블바텀
- 삼각수렴 압축
- 플래그 패턴장
- 꼬리물림장
- 갭필링 진행장
- 캔들 연속 패턴

즉 현재 gap은 `해석 로직` 부족이 아니라 `micro-structure 직접 수치화` 부족이다.

## owner 정리

### 1차 owner

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)
  - 1분봉 OHLCV 원천 획득

### 2차 owner

- [builder.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
- [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)
  - raw state 편입

### 3차 owner

- [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
  - 기록/export 연결

## 10개 제작 방식 요약

| 항목 | 제작 방식 | 메모 |
|---|---|---|
| `body_size_pct_20` | `보강 후 승격` | 기존 body 재료를 집계형 state로 올림 |
| `upper_wick_ratio_20` | `보강 후 승격` | 기존 윗꼬리 해석을 평균 비율로 올림 |
| `lower_wick_ratio_20` | `보강 후 승격` | 기존 아랫꼬리 해석을 평균 비율로 올림 |
| `doji_ratio_20` | `보강 후 승격` | indecision/motif를 compact ratio로 올림 |
| `direction_run_stats` | `그대로 사용 + 점진 보강` | 1차는 streak 재사용 |
| `range_compression_ratio_20` | `그대로 사용 + 점진 보강` | 1차는 compression 재사용 |
| `volume_burst_decay_20` | `보강 후 승격` | volume burst를 decay 구조까지 분리 |
| `swing_high_retest_count_20` | `보강 후 승격` | pattern 재료를 count field로 승격 |
| `swing_low_retest_count_20` | `보강 후 승격` | pattern 재료를 count field로 승격 |
| `gap_fill_progress` | `anchor 추가 후 재구축` | session 재료는 있으나 gap 기준점이 필요 |

## 지금 기준 추천

### 바로 추가할 값

- `body_size_pct_20`
- `doji_ratio_20`
- `direction_run_stats`
- `range_compression_ratio_20`
- `volume_burst_decay_20`

이 5개만 먼저 들어가도 25개 teacher-state 중 절반 이상을 더 또렷하게 구분할 수 있다.

### 그 다음 추가할 값

- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`
- `gap_fill_progress`

이 5개는 반전/실패/갭 메움류 패턴 정밀도에 직접적이다.

## MT5 추가 데이터 필요성 판단

지금 기준으로는 대부분 불필요하다.

필수는:

- 기존 1분봉 OHLC
- volume

있으면 좋은 것:

- 세션 시가
- spread
- tick volume / real volume

즉 방향은 `새 원천데이터 확보`보다 `기존 1분봉 정보의 재가공`이 맞다.

다만 `gap_fill_progress`는 예외적으로,

- session box 위치 재료
- position in session box
- response 캔들 해석

만으로 간접 추정은 가능하지만,

`현재 가격이 gap을 몇 % 메웠는가`를 안정적으로 쓰려면 gap anchor가 함께 있어야 한다.

즉 이 항목은 `완전 신규`라기보다 `기존 session 재료 + anchor 보강 후 재구축`으로 보는 게 더 맞다.

## 결론

이번 축은 사실상 `state 개편`의 후속이며, 기존 state를 깨지 않고 teacher-state가 이해할 수 있는 micro-structure 층을 얹는 작업이다.

다음 실제 구현은 `Top10 중 1차 5개`부터 시작하는 것이 가장 안전하고 생산적이다.
