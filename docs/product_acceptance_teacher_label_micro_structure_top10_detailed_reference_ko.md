# Teacher-Label Micro-Structure Top10 상세 기준서

## 목적

`1분봉 25개 teacher-state 최종판`을 실제 학습/판단 체계에 더 잘 연결하기 위해, 현재 시스템에 추가해야 할 `micro-structure` 데이터 10개를 정의한다.

핵심은 `10개를 다 새로 계산하는 것`이 아니라,

- 이미 있는 재료는 최대한 재사용하고
- 부족한 것은 집계형 canonical state로 승격하고
- 기준점이 없는 것은 anchor를 보강해 재구축

하는 것이다.

## 현재 시스템이 이미 잘 받고 있는 층

### 1. 시장 분위기 / regime

- 변동성이 큰지 작은지
- 거래량이 평소보다 큰지 작은지
- 스프레드가 부담인지 아닌지
- 지금이 추세장인지, 박스장인지, 확장장인지

### 2. 구조 위치 / position-response

- 현재 가격이 상단/중앙/하단 중 어디쯤인지
- 상단 돌파인지, 상단 거절인지, 하단 반등인지, 하단 붕괴인지
- 위치 에너지가 충돌하는지, 정렬되는지

### 3. 진입/대기/청산 해석

- 왜 observe인지
- 왜 blocked인지
- 왜 probe인지
- 기다리면 더 좋아질 가능성이 있는지
- 바로 잘라야 하는지
- 지금은 역추세인지, 정렬된 추세인지

### 4. 실제 결과

- 최종 손익
- giveback
- post-exit MFE/MAE
- wait_quality / loss_quality

## 현재 부족한 핵심

부족한 것은 대체로 `차트 모양 자체`를 직접 수치화한 값들이다.

- 몸통이 작은 캔들이 많은지
- 윗꼬리/아랫꼬리 비율이 높은지
- 같은 방향 캔들이 몇 개 연속으로 나왔는지
- 최근 범위가 실제로 얼마나 조여졌는지
- 비슷한 고점/저점을 몇 번 재시험했는지
- 거래량이 터졌다가 식는지
- 시가 갭을 얼마나 메웠는지

## Top10 구현 방식 최종 요약

| 항목 | 구현 분류 | 현재 재료 | 지금 판단 |
|---|---|---|---|
| `body_size_pct_20` | `보강 후 승격` | candle body 해석 + `recent_body_mean` | 새로 처음부터 만들 필요는 없고 집계형 canonical field가 필요 |
| `upper_wick_ratio_20` | `보강 후 승격` | candle descriptor 윗꼬리 에너지 | 최근 20봉 평균 비율로 재정리 필요 |
| `lower_wick_ratio_20` | `보강 후 승격` | candle descriptor 아랫꼬리 에너지 | 최근 20봉 평균 비율로 재정리 필요 |
| `doji_ratio_20` | `보강 후 승격` | candle pattern/motif + indecision | 최근 20봉 compact 비율로 정리 필요 |
| `direction_run_stats` | `그대로 사용 + 점진 보강` | streak/persistence 계열 | 1차는 기존 값 재사용 가능 |
| `range_compression_ratio_20` | `그대로 사용 + 점진 보강` | compression/session expansion 계열 | 1차는 기존 값 재사용 가능 |
| `volume_burst_decay_20` | `보강 후 승격` | volume ratio + tick flow burst | burst/decay 구조만 다시 풀어주면 됨 |
| `swing_high_retest_count_20` | `보강 후 승격` | double top / head&shoulders / reject 재료 | count field로 승격 필요 |
| `swing_low_retest_count_20` | `보강 후 승격` | double bottom / inverse H&S / hold 재료 | count field로 승격 필요 |
| `gap_fill_progress` | `anchor 추가 후 재구축` | session 위치 재료 + response 반응 | gap 기준점만 보강하면 정식 state화 가능 |

## Top10 micro-structure 정의

### 1. `body_size_pct_20`

- 뜻: 최근 20봉 기준 평균 몸통 크기
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `recent_body_mean`
  - `candle_descriptor_v1.body_size_energy`
- 정리 방식:
  - 현재 body 해석을 버리지 않고, 최근 20봉 평균 몸통 비율을 state로 승격

### 2. `upper_wick_ratio_20`

- 뜻: 최근 20봉 기준 평균 윗꼬리 비율
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `candle_descriptor_v1.upper_wick_energy`
  - 상단 reject 계열 response
- 정리 방식:
  - 윗꼬리 평균 비율을 state에 canonical field로 둔다

### 3. `lower_wick_ratio_20`

- 뜻: 최근 20봉 기준 평균 아랫꼬리 비율
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `candle_descriptor_v1.lower_wick_energy`
  - 하단 reject/hold 계열 response
- 정리 방식:
  - 아랫꼬리 평균 비율을 state에 canonical field로 둔다

### 4. `doji_ratio_20`

- 뜻: 최근 20봉 중 도지형 캔들 비율
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `candle_pattern_v1`
  - `candle_motif_v1`
  - `micro_indecision`
- 정리 방식:
  - 최근 20봉 도지/indecision 비율을 compact state로 정리

### 5. `direction_run_stats`

- 뜻:
  - 같은 방향 캔들 연속 개수
  - 최근 20봉 양봉/음봉 비율
- 구현 분류: `그대로 사용 + 점진 보강`
- 현재 재료:
  - `buy_streak`, `sell_streak`
  - `buy_persistence`, `sell_persistence`
- 정리 방식:
  - 1차는 기존 streak를 그대로 활용
  - 이후 필요하면 direct 양봉/음봉 연속 통계를 추가

### 6. `range_compression_ratio_20`

- 뜻: 최근 20봉 범위가 그 이전 기준 대비 얼마나 줄었는지
- 구현 분류: `그대로 사용 + 점진 보강`
- 현재 재료:
  - `s_compression`
  - `session_expansion_progress`
  - `recent_range_mean`
- 정리 방식:
  - 1차는 기존 compression 계열 재사용
  - 이후 direct ratio 필드를 추가해 teacher-state 친화적으로 보강

### 7. `volume_burst_decay_20`

- 뜻:
  - 거래량이 갑자기 터졌는지
  - 터진 뒤 바로 식는지
  - 연속적으로 유지되는지
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `current_tick_volume_ratio`
  - `current_real_volume_ratio`
  - `s_tick_flow_burst`
- 정리 방식:
  - burst와 decay를 나누는 compact state로 승격

### 8. `swing_high_retest_count_20`

- 뜻: 최근 20봉에서 비슷한 고점을 몇 번 다시 테스트했는지
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `pattern_double_top`
  - `pattern_head_shoulders`
  - resistance touch/reject 재료
- 정리 방식:
  - 동일 고점 재시험 횟수를 direct count로 승격

### 9. `swing_low_retest_count_20`

- 뜻: 최근 20봉에서 비슷한 저점을 몇 번 다시 테스트했는지
- 구현 분류: `보강 후 승격`
- 현재 재료:
  - `pattern_double_bottom`
  - `pattern_inverse_head_shoulders`
  - support touch/hold 재료
- 정리 방식:
  - 동일 저점 재시험 횟수를 direct count로 승격

### 10. `gap_fill_progress`

- 뜻: 세션 시작 이후 갭을 얼마나 메웠는지
- 구현 분류: `anchor 추가 후 재구축`
- 현재 재료:
  - `session_box_height_ratio`
  - `session_expansion_progress`
  - `position_in_session_box`
  - response 캔들 반응
- 왜 신규가 아닌가:
  - 이미 session 위치 재료와 캔들 반응은 있다
  - 즉 `메우는 중인지`, `메우다 실패하는지`는 간접적으로는 읽을 수 있다
- 왜 anchor가 필요한가:
  - `현재 가격이 gap을 몇 % 메웠는가`를 일관된 숫자로 만들려면
  - `세션 시가`, 필요시 `전 세션 종가` 같은 기준점이 필요하다
- 정리 방식:
  - 기존 session 재료를 재사용하되 gap anchor를 보강해 canonical progress로 재구축

## 결론

Top10의 대부분은 `새로 처음부터 계산`이 아니라,

- 이미 있는 response/state 재료를 재사용하고
- 필요한 것만 compact 집계형 state로 승격하고
- anchor가 부족한 항목만 기준점을 추가

하는 방식이 맞다.
