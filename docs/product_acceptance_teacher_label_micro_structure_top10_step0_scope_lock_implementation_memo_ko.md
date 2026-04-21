# Teacher-Label Micro-Structure Top10 Step 0 범위 고정 메모

## 현재 결론

`Step 0`에서 가장 중요한 판단은 아래다.

1. Top10을 전부 새로 만들지 않는다
2. 이미 있는 response/state 재료를 최대한 재사용한다
3. 다만 최종 학습/판단용 공용 필드는 state canonical field로 정리한다
4. `gap_fill_progress`는 완전 신규가 아니라 `anchor 추가 후 재구축`으로 본다

## 왜 이 판단이 맞는가

현재 시스템은 이미:

- 시장 분위기
- 구조 위치
- 진입/대기/청산 해석
- close 결과

를 강하게 가지고 있다.

그래서 지금 필요한 것은 완전히 새로운 분석 엔진이 아니라,
차트 모양을 더 직접 표현하는 compact micro-structure field다.

## Step 0에서 고정된 것

### 그대로 사용 + 점진 보강

- `direction_run_stats`
- `range_compression_ratio_20`

### 보강 후 승격

- `body_size_pct_20`
- `upper_wick_ratio_20`
- `lower_wick_ratio_20`
- `doji_ratio_20`
- `volume_burst_decay_20`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`

### anchor 추가 후 재구축

- `gap_fill_progress`

## 구현상 의미

이 결론 덕분에 다음 단계는 더 간단해진다.

- Step 1에서는 모든 걸 새 수식으로 처음부터 만들 필요가 없다
- 기존 builder/response/state 재료를 helper 형태로 엮으면 된다
- 1차 구현 5개는 위험이 낮고 효과가 크다

## 다음

Step 0이 끝났으니 다음은 자연스럽게 `Step 1. 1분봉 집계 helper 추가`로 내려가면 된다.
