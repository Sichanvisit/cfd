# Teacher-Label Micro-Structure Top10 Step 1 OHLCV Helper 메모

## 현재 판단

Step 1에서 중요한 건 `다 계산하는 것`보다 `안정적인 helper 경계`를 먼저 만드는 것이다.

즉:

- recent M1 bars를 받아
- micro_structure_v1 dict로 묶고
- null-safe하게 반환하는 틀

을 먼저 세우는 게 핵심이다.

## 왜 Step 1 문서가 필요한가

이 단계는 구현이 단순 계산처럼 보이지만 실제로는 아래가 쉽게 흔들린다.

- window 길이
- baseline 정규화
- doji 정의
- burst/decay 정의
- gap anchor 처리

그래서 구현 전에 `helper 경계`를 문서로 고정하는 게 필요하다.

## Step 1 핵심 판단

### 1차 fully usable

- `body_size_pct_20`
- `doji_ratio_20`
- `direction_run_stats`
- `range_compression_ratio_20`
- `volume_burst_decay_20`

### shape/fallback 우선

- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`
- `gap_fill_progress`

## gap 항목 메모

`gap_fill_progress`는 이 단계에서 완벽 계산보다

- anchor가 있으면 계산
- 없으면 이유를 상태값으로 남김

이 더 중요하다.

즉 Step 1에서는 `계산 가능성 + 안전한 fallback`이 핵심이다.

## 다음

이 문서 기준으로 다음부터는 Step 1 구현과 테스트에 들어가면 된다.
