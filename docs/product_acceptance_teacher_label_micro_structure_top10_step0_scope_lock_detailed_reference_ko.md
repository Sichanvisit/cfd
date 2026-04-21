# Teacher-Label Micro-Structure Top10 Step 0 범위 고정 상세 기준서

## 목적

이 문서는 `Teacher-Label Micro-Structure Top10`의 `Step 0. 계산 범위 고정`을 위한 상세 기준서다.

핵심 목적은 구현 전에 아래를 확정하는 것이다.

1. Top10 항목의 `1차 정의`
2. 각 항목의 `주 재료`
3. 각 항목의 `구현 방식`
4. 이번 1차에서 `하지 않을 것`

이 문서는 이후 실제 구현에서 “이 값을 정확히 뭘로 볼 것인가”가 흔들리지 않도록 하는 scope-lock 문서다.

## Step 0에서 확정할 원칙

### 1. Top10은 모두 같은 방식으로 만들지 않는다

- `그대로 사용 + 점진 보강`
- `보강 후 승격`
- `anchor 추가 후 재구축`

중 하나로 분류한다.

### 2. 1차 구현은 teacher-state 친화적 compact field가 목적이다

즉 지금 단계는 차트 전체를 완벽히 복제하는 것이 아니라,

- 사람이 차트에서 읽는 핵심 모양
- 이를 기존 state와 자연스럽게 연결하는 compact 숫자

를 만드는 것이 목적이다.

### 3. 1차는 기존 재료를 최대한 재사용한다

- response 재료는 버리지 않는다
- state 재료도 버리지 않는다
- 이미 있는 해석과 충돌하지 않게 canonical field를 덧붙인다

## Top10 1차 정의 고정

| 항목 | 1차 정의 | 구현 방식 | 주 재료 | 1차 산출물 |
|---|---|---|---|---|
| `body_size_pct_20` | 최근 20봉의 평균 몸통 크기 비율 | `보강 후 승격` | OHLC, `recent_body_mean`, candle body 해석 | `s_body_size_pct_20` |
| `upper_wick_ratio_20` | 최근 20봉의 평균 윗꼬리 / 전체 range 비율 | `보강 후 승격` | OHLC, `upper_wick_energy` | `s_upper_wick_ratio_20` |
| `lower_wick_ratio_20` | 최근 20봉의 평균 아랫꼬리 / 전체 range 비율 | `보강 후 승격` | OHLC, `lower_wick_energy` | `s_lower_wick_ratio_20` |
| `doji_ratio_20` | 최근 20봉 중 도지/indecision 캔들 비율 | `보강 후 승격` | candle pattern, motif, `micro_indecision` | `s_doji_ratio_20` |
| `direction_run_stats` | 현재 run 길이, 최근 20봉 최대 run, bull/bear 편중 | `그대로 사용 + 점진 보강` | `buy_streak`, `sell_streak`, persistence, OHLC | `s_same_color_run_current`, `s_same_color_run_max_20` |
| `range_compression_ratio_20` | 최근 20봉 range 압축 정도 | `그대로 사용 + 점진 보강` | `s_compression`, `session_expansion_progress`, OHLC | `s_range_compression_ratio_20` |
| `volume_burst_decay_20` | 거래량 burst 강도와 burst 이후 decay 정도 | `보강 후 승격` | tick/real volume ratio, `s_tick_flow_burst` | `s_volume_burst_ratio_20`, `s_volume_burst_decay_20` |
| `swing_high_retest_count_20` | 최근 20봉에서 동일 고점 재시험 횟수 | `보강 후 승격` | pattern/reject/resistance 재료 | `s_swing_high_retest_count_20` |
| `swing_low_retest_count_20` | 최근 20봉에서 동일 저점 재시험 횟수 | `보강 후 승격` | pattern/hold/support 재료 | `s_swing_low_retest_count_20` |
| `gap_fill_progress` | 세션 gap을 현재가가 얼마나 메웠는지 | `anchor 추가 후 재구축` | session 위치 재료, response, session open, previous close | `s_gap_fill_progress` |

## 항목별 1차 정의

### 1. `body_size_pct_20`

- 목표:
  - “최근 20봉이 얼마나 실체가 큰가”를 직접 수치화
- 1차 정의:
  - 각 봉에서 `abs(close - open)`을 계산
  - 이를 price-scale 또는 recent baseline 기준으로 정규화한 뒤
  - 최근 20봉 평균으로 둔다
- 재료:
  - 현재/이전 OHLC
  - `recent_body_mean`
  - `candle_descriptor_v1.body_size_energy`
- 이번 단계에서 안 하는 것:
  - 종목별 완전 다른 정규화 체계 도입

### 2. `upper_wick_ratio_20`

- 목표:
  - 상단 거절, 페이크아웃, 더블탑류를 더 직접 수치화
- 1차 정의:
  - 각 봉에서 `upper_wick / total_range`
  - 최근 20봉 평균
- 재료:
  - OHLC
  - `upper_wick_energy`
- 이번 단계에서 안 하는 것:
  - wick 모양을 여러 클래스로 다시 분류

### 3. `lower_wick_ratio_20`

- 목표:
  - 하단 지지 반응, 눌림 반등, 바닥 반전을 더 직접 수치화
- 1차 정의:
  - 각 봉에서 `lower_wick / total_range`
  - 최근 20봉 평균
- 재료:
  - OHLC
  - `lower_wick_energy`

### 4. `doji_ratio_20`

- 목표:
  - 횡보, 압축, 엔진 꺼짐, indecision 상태를 직접 수치화
- 1차 정의:
  - 도지 또는 indecision으로 판단된 봉 수 / 최근 20봉
- 재료:
  - `candle_pattern_v1`
  - `candle_motif_v1`
  - `micro_indecision`
- 이번 단계에서 안 하는 것:
  - 도지의 세부 유형을 다시 taxonomy로 쪼개기

### 5. `direction_run_stats`

- 목표:
  - 같은 방향 캔들 연속성을 teacher-state 친화적으로 보존
- 1차 정의:
  - 현재 연속 run 길이
  - 최근 20봉 최대 연속 run 길이
  - 최근 20봉 bull/bear 비율
- 재료:
  - 1차는 `buy_streak`, `sell_streak`, persistence 계열 우선 재사용
  - 이후 direct candle color stat 보강 가능
- 이번 단계에서 안 하는 것:
  - 모든 run 유형을 별도 상태로 분해

### 6. `range_compression_ratio_20`

- 목표:
  - 브레이크 직전, 수렴 압축, 모닝 컨솔리데이션 구간을 수치화
- 1차 정의:
  - 기존 compression score와 최근 range 축소 정도를 함께 반영한 compact ratio
- 재료:
  - `s_compression`
  - `session_expansion_progress`
  - `recent_range_mean`
  - 필요시 최근 20봉 high-low span
- 이번 단계에서 안 하는 것:
  - 삼각수렴 기하학적 모델링

### 7. `volume_burst_decay_20`

- 목표:
  - 거래량이 터졌는지, 터진 뒤 식는지를 분리해서 기록
- 1차 정의:
  - `burst_ratio`: 현재 또는 최근 burst 강도
  - `decay_ratio`: burst 이후 volume 감소 정도
- 재료:
  - `current_tick_volume_ratio`
  - `current_real_volume_ratio`
  - `s_tick_flow_burst`
- 이번 단계에서 안 하는 것:
  - 이벤트성 체결 패턴을 별도 이벤트 엔진으로 분리

### 8. `swing_high_retest_count_20`

- 목표:
  - 더블탑, 페이크아웃 상단 재시험, 저항 재테스트를 count로 보존
- 1차 정의:
  - 최근 20봉에서 허용 오차 내 유사 고점 재시험 횟수
- 재료:
  - `pattern_double_top`
  - `pattern_head_shoulders`
  - resistance touch/reject 재료
- 이번 단계에서 안 하는 것:
  - 완전한 파동 구조 분석 엔진 도입

### 9. `swing_low_retest_count_20`

- 목표:
  - 더블바텀, 눌림목 지지, 데드캣 저점 재시험을 count로 보존
- 1차 정의:
  - 최근 20봉에서 허용 오차 내 유사 저점 재시험 횟수
- 재료:
  - `pattern_double_bottom`
  - `pattern_inverse_head_shoulders`
  - support touch/hold 재료

### 10. `gap_fill_progress`

- 목표:
  - 갭을 메우는 진행 상황을 숫자로 고정
- 1차 정의:
  - `gap anchor`를 기준으로 현재 가격이 갭을 몇 % 메웠는지 계산
  - 값은 보통 `0~1` 또는 방향 포함 signed ratio로 둔다
- 재료:
  - `session_box_height_ratio`
  - `session_expansion_progress`
  - `position_in_session_box`
  - response 캔들 반응
  - `session_open`
  - 필요시 `previous_close`
- 이번 단계에서 안 하는 것:
  - 갭의 원인을 별도 이벤트 타입으로 분리

## 이번 단계에서 제외하는 것

아래는 1차 scope에 넣지 않는다.

- 호가창 기반 미세 체결 패턴
- tick-by-tick orderflow 전체 저장
- 삼각수렴/플래그를 별도 전용 패턴 엔진으로 완전 분리
- 종목마다 다른 정규화 체계를 대대적으로 도입

## 완료 기준

Step 0이 끝났다고 보려면 아래가 고정되어야 한다.

1. Top10 항목과 이름이 확정된다
2. 각 항목의 구현 방식이 확정된다
3. 각 항목의 주 재료가 확정된다
4. 1차에서 하지 않을 것도 확정된다

## 결론

Step 0의 목적은 계산을 시작하는 게 아니라,

- 무엇을 만들지
- 무엇을 재사용할지
- 무엇을 anchor 보강으로 처리할지

를 문서로 고정해 이후 구현이 흔들리지 않게 만드는 것이다.
