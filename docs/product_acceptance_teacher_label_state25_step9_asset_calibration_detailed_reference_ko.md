# Teacher-Label State25 Step E1 자산별 캘리브레이션 상세 기준서

## 목적

이 문서는 Step 9 첫 하위축인 `E1 자산별 캘리브레이션`의 실제 구현 기준을 고정한다.

핵심 목적은:

- 현재 확보된 labeled seed를 `BTC / XAU / NAS` 단위로 다시 읽고
- 자산별로 어떤 패턴/미시구조/신뢰도에 치우쳤는지 확인하고
- 이후 `threshold 조정 / 10K QA / baseline` 전에 왜곡을 먼저 잡는 것이다.

즉 이번 단계는 `실행 룰 조정`이 아니라 `실험용 분포 확인` 단계다.

## 왜 seed report 다음에 이 단계가 필요한가

Step 9 seed report로는 아래까지는 확인된다.

- labeled seed가 1K를 넘겼는지
- 전체 패턴 분포가 어떤지
- QA warning이 무엇인지

하지만 그것만으로는 부족하다.

우리는 아직 아래를 모른다.

- BTC, XAU, NAS 중 어떤 자산이 특정 패턴에 과도하게 몰렸는지
- ATR proxy와 변동성 proxy가 자산별로 얼마나 다른지
- `12↔23`, `5↔10`, `16↔2` 같은 watchlist pair가 자산별로 어디에 몰리는지
- 특정 자산이 사실상 한 그룹만 배우고 있는지

그래서 `asset calibration report`가 Step E1 owner가 된다.

## 이번 단계에서 사용할 실제 입력

raw ATRP 시계열 전체를 다시 읽는 단계는 아니다.

이번 E1은 현재 compact dataset에 이미 남아 있는 아래 필드를 기준으로 본다.

- `entry_atr_ratio`
- `regime_volatility_ratio`
- `micro_body_size_pct_20`
- `micro_doji_ratio_20`
- `micro_range_compression_ratio_20`
- `micro_volume_burst_ratio_20`
- `micro_volume_burst_decay_20`
- `teacher_pattern_*`

즉 이 단계는 `현재 compact seed 기준의 실용 캘리브레이션`이다.

## 출력 규격

### 1. 전체 요약

- `labeled_rows`
- `min_rows_per_symbol`
- `symbols_present`
- `missing_symbols`
- `warnings`

### 2. 자산별 보고서

각 심볼에 대해 아래를 만든다.

- `rows`
- `ratio`
- `warnings`
- `primary_patterns`
- `group_distribution`
- `bias_distribution`
- `confidence_summary`
- `entry_atr_ratio_summary`
- `regime_volatility_ratio_summary`
- `micro_body_size_pct_20_summary`
- `micro_doji_ratio_20_summary`
- `micro_range_compression_ratio_20_summary`
- `micro_volume_burst_ratio_20_summary`
- `micro_volume_burst_decay_20_summary`
- `watchlist_pairs`

### 3. watchlist pair

이번 단계에서 직접 추적하는 pair는 아래 3개다.

- `12-23`
- `5-10`
- `2-16`

여기서 pair는 `primary/secondary`가 unordered pair로 한 row 안에 같이 붙은 경우를 센다.

## warning 규칙

### 전체 warning

- `missing_symbol_seed:<symbol>`
  - BTC/XAU/NAS 중 해당 심볼 labeled seed가 0
- `insufficient_symbol_seed:<symbol>`
  - 해당 심볼 labeled row가 최소 기준보다 적음
- `group_skew:<symbol>:<group>`
  - 해당 심볼 labeled row의 80% 이상이 한 그룹에 몰림

### 자산별 warning

- `no_labeled_rows`
- `insufficient_rows`
- `group_skew:<group>`

## 이번 단계의 완료 기준

- asset calibration builder 추가
- CLI report 추가
- 자산별 분포/미시구조/신뢰도 요약 산출 가능
- watchlist pair를 자산별로 읽을 수 있음
- 실제 labeled seed에 한 번 실행해 결과를 기록함

## 다음 단계 연결

이번 E1이 완료되면 다음은:

1. Step E2 `10K full labeling QA`
2. Step E3 `baseline model`

으로 넘긴다.
