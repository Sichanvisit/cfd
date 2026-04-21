# Teacher-Label Micro-Structure Top10 Step 1 OHLCV Helper 상세 기준서

## 목적

이 문서는 `Step 1. 1분봉 집계 helper 추가`의 상세 기준서다.

Step 1의 목적은 `기존 1분봉 OHLCV`와 `기존 session metadata`를 이용해,
이후 state에 편입할 `micro_structure_v1` compact dict를 안정적으로 만드는 것이다.

이번 단계에서 중요한 건:

1. 계산 source를 새로 늘리지 않는다
2. `trading_application.py` 안에서 재사용 가능한 helper를 만든다
3. 1차 5개는 확실하게 계산 가능하게 하고
4. 나머지 5개는 재료/anchor 상태까지 함께 정리한다

## Step 1 owner

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

현재 이 파일은 이미:

- `copy_rates_from_pos`로 recent OHLCV를 가져오고
- downstream metadata를 여러 곳에 흘리는 진입점

역할을 하므로, Step 1 owner로 가장 자연스럽다.

## Step 1 입력

### 필수 입력

- 최근 `1분봉 OHLCV`
- 기본 lookback window
  - 기본 `20`
  - 보조 `50`

### 권장 입력

- 현재 metadata 안의 session 위치 재료
  - `session_box_height_ratio`
  - `session_expansion_progress`
  - `position_in_session_box`

### gap 전용 anchor 후보

- `session_open`
- 필요시 `previous_close`

## Step 1 산출물

Step 1의 직접 산출물은 `micro_structure_v1` dict다.

권장 shape:

```python
{
    "version": "micro_structure_v1",
    "lookback_bars": 20,
    "window_size": 20,
    "data_state": "READY",
    "anchor_state": "READY",
    "body_size_pct_20": ...,
    "upper_wick_ratio_20": ...,
    "lower_wick_ratio_20": ...,
    "doji_ratio_20": ...,
    "same_color_run_current": ...,
    "same_color_run_max_20": ...,
    "bull_ratio_20": ...,
    "bear_ratio_20": ...,
    "range_compression_ratio_20": ...,
    "volume_burst_ratio_20": ...,
    "volume_burst_decay_20": ...,
    "swing_high_retest_count_20": ...,
    "swing_low_retest_count_20": ...,
    "gap_fill_progress": ...,
}
```

## 1차 구현 기준

### 이번 단계에서 반드시 안정화할 5개

- `body_size_pct_20`
- `doji_ratio_20`
- `direction_run_stats`
- `range_compression_ratio_20`
- `volume_burst_decay_20`

이 다섯 개는 Step 1에서 fully usable한 값으로 나와야 한다.

### 이번 단계에서 shape만 고정해도 되는 5개

- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`
- `gap_fill_progress`

이 다섯 개는 Step 1에서 가능하면 계산하되,
최소한 아래는 고정되어야 한다.

- key 이름
- null-safe fallback
- anchor/state 부족 시 표기 규칙

## 항목별 Step 1 계산 원칙

### `body_size_pct_20`

- 최근 20봉 각각의 `abs(close - open)` 계산
- symbol scale에 맞는 baseline으로 정규화
- 최근 20봉 평균으로 산출

### `doji_ratio_20`

- 몸통이 range 대비 매우 작거나
- 기존 indecision 조건에 걸리는 봉을 count
- 최근 20봉 대비 비율로 산출

### `direction_run_stats`

- 현재 연속 양봉/음봉 길이
- 최근 20봉 최대 연속 길이
- 최근 20봉 bull/bear 비율

### `range_compression_ratio_20`

- 최근 20봉 range span을 이전 baseline과 비교
- 기존 `compression` 계열 값이 있으면 helper 안에서 함께 참고

### `volume_burst_decay_20`

- 현재 또는 최근 volume burst 강도
- burst 이후 최근 몇 봉에서 얼마나 식었는지

### `upper_wick_ratio_20`

- 최근 20봉 평균 `upper_wick / total_range`

### `lower_wick_ratio_20`

- 최근 20봉 평균 `lower_wick / total_range`

### `swing_high_retest_count_20`

- 최근 20봉 고점 cluster를 tolerance 기준으로 묶고
- 동일 고점 재시험 횟수 count

### `swing_low_retest_count_20`

- 최근 20봉 저점 cluster를 tolerance 기준으로 묶고
- 동일 저점 재시험 횟수 count

### `gap_fill_progress`

- gap anchor가 있는 경우에만 정식 계산
- anchor가 없으면 `None` 또는 neutral fallback을 반환하되
  `anchor_state`에 이유를 남긴다

## null-safe 규칙

Step 1 helper는 실패해도 downstream을 깨면 안 된다.

원칙:

- bars 부족 시 `data_state="INSUFFICIENT_BARS"`
- gap anchor 부족 시 `anchor_state="MISSING_GAP_ANCHOR"`
- 숫자는 가능한 범위에서 `0.0` 또는 `None` fallback
- 예외를 그대로 밖으로 던지지 않는다

## 이번 단계에서 하지 않을 것

- tick-by-tick 전체 재구성
- 고급 패턴 엔진 재작성
- 종목별 완전 다른 정규화 룰 도입
- teacher-state 최종 분류를 Step 1 helper 안에서 직접 수행

## Step 1 완료 기준

아래를 만족하면 Step 1 완료로 본다.

1. `micro_structure_v1` helper가 추가된다
2. recent OHLCV만으로 재현 가능하다
3. 1차 5개가 안정적으로 계산된다
4. 나머지 5개도 key와 fallback 규칙이 고정된다
5. helper 실패가 runtime 전체를 깨지 않는다

## 결론

Step 1은 `state 편입` 전 단계다.

여기서 해야 할 일은:

- 1분봉 recent window
- 기존 session metadata
- 최소 anchor

를 이용해 `micro_structure_v1`를 만드는 것이다.
