# Phase 1~3 PRS Mapping

`15공식.md`의 조건을 `Position / Response / State` 스키마로 분해한 기준표다.

원칙:

1. 새 조건은 반드시 `Position`, `Response`, `State` 중 하나로만 정의한다.
2. 새 조건을 넣을 때 별도 예외 분기, soft-pass, 하드 가드를 늘리지 않는다.
3. `Position`은 연속 좌표, `Response`는 이벤트, `State`는 감쇠/증폭 환경으로만 해석한다.

## 분해표

| 항목 | Position | Response | State | 구현 메모 |
|---|---|---|---|---|
| 1. 3단 세션 박스권 | `x_box_session` | `r_box_lower_bounce`, `r_box_upper_reject`, `r_box_break` | `s_session_name` | 현재 OHLC/H1 데이터로 계산 가능 |
| 2. 박스 복사 Expansion | `x_box_expansion` | `r_box_break_confirm` | `s_expansion_active` | 세션 박스 계산 후 파생 |
| 3. 당일 시가(Open) 돌파 | `x_daily_open` | `r_open_reclaim`, `r_open_break` | `s_open_bias` | D1/M1 데이터로 계산 가능 |
| 4. 다중 지지/저항 | `x_sr_h1`, `x_sr_h4`, `x_sr_d1`, `x_sr_w1` | `r_sr_hold`, `r_sr_break` | `s_sr_cluster_strength` | H4/W1은 집계 또는 별도 프레임 필요 |
| 5. 4번의 법칙 | - | `r_rule_of_4_break_bias` | `s_rule_of_4_pressure` | pivot 반복터치 수를 상태/반응으로 사용 |
| 6. Double BB | `x_bb20`, `x_bb44` | `r_bb_lower_hold`, `r_bb_upper_reject`, `r_bb_break` | `s_bb_expansion` | 현재 지표 이미 존재 |
| 7. 이격도 | `x_disparity` | `r_disparity_reversal` | `s_disparity_regime` | 현재 disparity 존재 |
| 8. 다중 이평선 배열/수렴 | `x_ma20`, `x_ma60`, `x_ma120`, `x_ma240`, `x_ma480` | `r_ma_reclaim`, `r_ma_break` | `s_alignment`, `s_ma_compression` | 배열은 있음, 수렴은 추가 계산 필요 |
| 9. 추세선 | `x_trendline` | `r_trendline_reclaim`, `r_trendline_break` | `s_trendline_bias` | 자동 재구성 우선, 수동 MT5 오브젝트는 별도 |
| 10. RSI/이격도 다이버전스 | - | `r_divergence_bull`, `r_divergence_bear` | `s_divergence_strength` | 현재 RSI 다이버전스 일부 있음 |
| 11. 캔들 꼬리 | - | `r_candle_lower_reject`, `r_candle_upper_reject` | `s_candle_quality` | OHLC로 계산 가능 |
| 12. 캔들 패턴 | - | `r_pattern_hammer`, `r_pattern_engulfing`, `r_pattern_momentum` | `s_pattern_strength` | OHLC로 계산 가능 |
| 13. 차트 형태 | `x_pattern_neckline` | `r_pattern_confirm_break` | `s_pattern_bias` | pivot 시퀀스 기반 재구성 필요 |
| 14. RSI / DI 극단값 | `x_rsi`, `x_di_gap` | `r_rsi_exit_extreme`, `r_di_cross` | `s_extreme_regime` | 현재 RSI/DI 이미 존재 |
| 15. 1분봉 매물대 필터 | `x_vp_node_1m` | `r_vp_hold`, `r_vp_break` | `s_vp_density` | 현재 raw collector만으로는 부족, 추가 재구성 필요 |

## 현재 collector 기준 분류

### 이미 있음

- `x_bb20`, `x_bb44`
- `x_disparity`
- `x_ma20`, `x_ma60`, `x_ma120`, `x_ma240`, `x_ma480`
- `x_rsi`, `x_di_gap`
- `s_alignment`

### 현재 데이터로 계산 가능

- 세션 박스, 박스 확장, 당일 시가
- H1/H4/D1/W1 S/R
- 추세선 자동 재구성
- 캔들 반응/패턴
- 다이버전스

### 추가 수집 또는 재구성 필요

- 수동 MT5 오브젝트 기반 추세선/박스
- 1분봉 매물대/VP 노드

## Phase 1~3 우선 적용 범위

1. `Position`
   - `x_box`
   - `x_bb20`
   - `x_bb44`
   - `x_ma20`, `x_ma60`, `x_ma120`, `x_ma240`, `x_ma480`
   - `x_sr`
   - `x_trendline`

2. `Response`
   - 다음 Phase에서 추가

3. `State`
   - 현재 `market_mode`, `noise`, `conflict`, `alignment`는 유지
   - 다음 Phase에서 엔진화
