# PRS Rebuild Roadmap

## 목적

이 문서는 지금까지 정리한 `Position / Response / State` 기준을 실제 구현 순서로 다시 묶은 실행 로드맵이다.

이번 로드맵의 핵심은 아래 4가지다.

1. `Position`은 위치 지도와 지도 스케일을 담당한다.
2. `Response`는 위치에서 나온 실제 반응을 의미 축으로 압축한다.
3. `State`는 시장 환경과 품질을 보정한다.
4. `Evidence / Belief / Barrier`는 그 뒤에서 신뢰, 기다림, 보유를 조절한다.

---

## 현재 기준 요약

### Position

- `box`, `bb20`, `bb44`는 위치 owner다.
- `Position`은 `어디에 있는가`와 `지금 지도가 얼마나 넓거나 좁은가`를 말한다.
- 최근 반영으로 `position_scale` 메타데이터가 추가되었다.
  - `box_height`
  - `bb20_width`
  - `bb44_width`
  - `box_height_ratio`
  - `bb20_width_ratio`
  - `bb44_width_ratio`
  - `box_size_state`
  - `bb20_width_state`
  - `bb44_width_state`
  - `map_size_state`
  - `compression_score`
  - `expansion_score`

### Response

- `Response`는 raw를 바로 최종 진입 신호로 쓰지 않는다.
- raw를 먼저 `반응 의미`로 압축한 뒤 `Response 6축`으로 보낸다.
- 현재 6축은 아래와 같다.
  - `lower_hold_up`
  - `lower_break_down`
  - `mid_reclaim_up`
  - `mid_lose_down`
  - `upper_reject_down`
  - `upper_break_up`

### State

- `State`는 이 반응을 얼마나 믿어도 되는지 보정한다.
- owner 후보:
  - `RSI`
  - `이격도`
  - `정배열/역배열`
  - `market mode`
  - `liquidity`
  - `noise`
  - `conflict`
  - `volatility`

### Evidence / Belief / Barrier

- `Evidence`: 순간 신뢰도 owner
- `Belief`: 지속 신뢰도 owner
- `Barrier`: 실행 금지/보류 owner

---

## 현재 반영 상태

| 영역 | 현재 상태 | 비고 |
| --- | --- | --- |
| `Position: box/bb 위치` | `완료에 가까움` | 실전 사용 중 |
| `Position: box/bb 크기 스케일` | `이번에 반영` | `position_scale` 메타데이터 추가 |
| `Position: MA/SR 보조축` | `보조 연결` | 메인 owner는 아님 |
| `Position: trendline` | `슬롯만 있음` | 라이브 입력 거의 없음 |
| `Response: BB/Box/Candle/Pattern raw` | `기존 구현 있음` | 현재 6축으로 압축 중 |
| `Response: S/R raw` | `미구현` | 앞으로 추가 예정 |
| `Response: trendline raw` | `미구현` | 앞으로 추가 예정 |
| `Response: candle descriptor/pattern/motif/context gate` | `개념 정리 완료` | 아직 코드 구조화 전 |
| `State: 시장 환경 보정` | `기존 구현 있음` | 규칙형 보강 필요 |
| `Evidence/Belief/Barrier owner 정리` | `문서 기준 확립` | 튜닝은 남음 |

---

## 전체 진행 순서

| 단계 | 이름 | 목표 | 상태 |
| --- | --- | --- | --- |
| `R0` | 계약 고정 | Position/Response/State owner 고정 | `완료` |
| `R1` | Position 지도 고정 | 위치와 크기 스케일 지도 완성 | `진행중` |
| `R2` | Response 재구성 | raw -> descriptor -> pattern/motif -> context gate -> 6축 | `예정` |
| `R3` | State 재배치 | 큰지도와 시장품질 보정 정리 | `예정` |
| `R4` | Evidence 결합 재정렬 | Position/Response/State 결합 방식 안정화 | `예정` |
| `R5` | Belief/Barrier 조율 | 신뢰 지속성과 엔트리 대기 기준 정리 | `예정` |
| `R6` | Exit/Wait 재정렬 | 오래 들고 갈지/언제 기다릴지 정리 | `예정` |

---

## R0. 계약 고정

### 목표

레이어 역할이 섞이지 않게 기준을 고정한다.

### 기준

- `Position`
  - 위치
  - 거리
  - 지도 크기
- `Response`
  - 지지/저항/추세선/캔들/패턴 반응
- `State`
  - 환경
  - 품질
  - 시장 모드
- `Evidence`
  - 순간 근거 합산
- `Belief`
  - 지속성
- `Barrier`
  - 차단

### 완료 기준

- 새 기능을 추가할 때 owner 논쟁이 반복되지 않는다.
- 위치는 `Position`, 사건은 `Response`, 보정은 `State`로 먼저 분류할 수 있다.

---

## R1. Position 지도 고정

### 목표

`Position`이 “지금 어디인가”와 “그 공간이 얼마나 압축/확장됐는가”를 안정적으로 설명하게 만든다.

### 현재 반영된 것

- `x_box`
- `x_bb20`
- `x_bb44`
- `x_ma20`
- `x_ma60`
- `x_sr`
- `x_trendline`

그리고 새로 반영된 스케일 메타데이터:

- `box_height`
- `bb20_width`
- `bb44_width`
- `box_height_ratio`
- `bb20_width_ratio`
- `bb44_width_ratio`
- `box_size_state`
- `bb20_width_state`
- `bb44_width_state`
- `map_size_state`
- `compression_score`
- `expansion_score`

### 지금 할 일

#### R1-1. box/bb 위치 acceptance

- `upper/lower/middle` 해석이 스크린샷 감각과 맞는지 확인
- `bias`, `unresolved`, `conflict` 과민/과소 점검

#### R1-2. box/bb 크기 해석 acceptance

- 좁은 박스/밴드에서 `compression_score`가 높게 찍히는지 확인
- 넓은 박스/밴드에서 `expansion_score`가 높게 찍히는지 확인
- live runtime에 `position_scale`이 정상 기록되는지 확인

#### R1-3. MA 큰지도 연결

상위 MA는 Position/State 쪽으로 연결한다.

- `D1`
- `H4`
- `H1`
- `M30`
- `M15`

추가 목표:

- 각 MA와의 signed distance
- 각 MA proximity
- 상위 MA 정렬 상태의 기초 raw

#### R1-4. trendline 거리 지도

추세선은 먼저 거리/위치부터 Position에 넣는다.

목표 필드:

- `x_tl_m1`
- `x_tl_m15`
- `x_tl_h1`
- `x_tl_h4`
- `tl_proximity_m1`
- `tl_proximity_m15`
- `tl_proximity_h1`
- `tl_proximity_h4`

### 완료 기준

- 박스/볼밴 위치와 크기를 설명하는 메타데이터가 런타임에서 안정적으로 보인다.
- Position만 봐도 “좁은지도인지, 넓은지도인지”를 설명할 수 있다.
- 추세선과 MA는 적어도 거리 owner로서 분리 설계가 끝난다.

---

## R2. Response 재구성

### 목표

복잡한 raw를 바로 6축에 넣지 말고, 중간 semantic 단계를 둬서 축을 안정화한다.

### 목표 구조

```text
OHLC / level / swing
-> descriptor
-> pattern
-> motif
-> context gate
-> Response 6축
```

### 세부 단계

#### R2-1. Candle descriptor

캔들은 먼저 중립 descriptor가 필요하다.

후보:

- `body_signed_energy`
- `body_shape_energy`
- `upper_wick_energy`
- `lower_wick_energy`
- `close_location_energy`
- `wick_balance_energy`
- `range_size_energy`
- `body_size_energy`

#### R2-2. Candle pattern

20개 캔들 패턴을 단일/2봉/3봉 패턴으로 정리한다.

예:

- `Hammer`
- `Shooting Star`
- `Bullish Engulfing`
- `Bearish Engulfing`
- `Morning Star`
- `Evening Star`
- `Three White Soldiers`
- `Three Black Crows`

#### R2-3. Candle motif

패턴 이름을 직접 6축에 넣지 않고 motif로 압축한다.

후보:

- `bull_reject`
- `bear_reject`
- `bull_reversal_2bar`
- `bear_reversal_2bar`
- `bull_reversal_3bar`
- `bear_reversal_3bar`
- `bull_break_body`
- `bear_break_body`
- `indecision`
- `climax`

#### R2-4. Structure motif

구조 패턴은 candle motif와 분리한다.

후보:

- `double_bottom`
- `double_top`
- `inverse_head_shoulders`
- `head_shoulders`

이를 다시 structure motif로 압축한다.

- `reversal_base_up`
- `reversal_top_down`
- `support_hold_confirm`
- `resistance_reject_confirm`

#### R2-5. S/R raw 추가

현재 비어 있는 직접 S/R 반응 raw를 추가한다.

후보:

- `sr_support_hold`
- `sr_support_break`
- `sr_resistance_reject`
- `sr_resistance_break`

#### R2-6. Trendline raw 추가

추세선 반응은 Response owner다.

후보:

- `trend_support_hold_*`
- `trend_support_break_*`
- `trend_resistance_reject_*`
- `trend_resistance_break_*`

#### R2-7. Context gate

같은 패턴도 위치가 다르면 의미가 달라진다.

gate 입력:

- Position zone
- support/resistance proximity
- trendline proximity
- range size / expansion-compression
- recent move quality

#### R2-8. 최종 6축 안정화

최종 목표 축:

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

### 완료 기준

- raw 개수가 늘어나도 6축이 쉽게 포화되지 않는다.
- 같은 의미가 여러 번 중복 합산되지 않는다.
- `S/R`, `trendline`, `candle`, `pattern`이 모두 6축에 자연스럽게 연결된다.

---

## R3. State 재배치

### 목표

큰지도와 시장 품질을 `State`가 일관되게 보정하게 만든다.

### owner 후보

- `RSI`
- `이격도`
- `ma_alignment`
- `market_mode`
- `liquidity`
- `noise`
- `volatility`
- `conflict`

### 큰지도 적용 원칙

- `D1 / H4 / H1` = 큰 방향
- `M30 / M15` = 연결 구간
- `M5 / M1` = 실제 진입 반응

### State가 하는 일

- 상위 방향과 맞는 반응은 gain
- 반대 반응은 damp 또는 penalty
- 압축/확장 상태에 따라 reversal/continuation 성격 보정

### 완료 기준

- 같은 Response라도 trend/range/chop에 따라 의미가 달라진다.
- 큰지도는 직접 진입을 결정하지 않고 신뢰도와 인내심을 조절한다.

---

## R4. Evidence 결합 재정렬

### 목표

`Position + Response + State`가 서로 겹치지 않게 Evidence에서 합쳐지도록 정리한다.

### 원칙

- `Position`은 위치 적합도
- `Response`는 반응 strength
- `State`는 gain/damp

### 결합 방향

- `buy_reversal`
- `sell_reversal`
- `buy_continuation`
- `sell_continuation`

### 주의점

- 같은 의미 중복 가산 금지
- `Position`이 반응까지 대신 말하면 안 됨
- `Response`가 위치까지 대신 말하면 안 됨

### 완료 기준

- Evidence가 각 모드별 근거를 분리해서 설명할 수 있다.
- 특정 raw가 들어와도 Evidence가 쉽게 포화되지 않는다.

---

## R5. Belief / Barrier 조율

### 목표

“좋은 반응이 한 번 나왔다”와 “믿고 기다려도 되는가”를 분리한다.

### Belief가 하는 일

- 근거 지속성 누적
- 한 봉 반짝 신호 억제
- 2~3봉 확인 구조 강화

### Barrier가 하는 일

- middle chop 차단
- conflict 차단
- liquidity 차단
- policy 차단
- 연속 진입 차단

### 완료 기준

- 좋은 반응 하나만으로 과속 진입하지 않는다.
- 의미 없는 잡음엔 wait가 자연스럽게 늘어난다.

---

## R6. Exit / Wait 재정렬

### 목표

엔트리 대기와 보유 지속을 분리해서 튜닝한다.

### 엔트리 기다림 owner

- `ObserveConfirm`
- `Barrier`
- `WaitEngine`

### 보유 지속 owner

- `management_profile`
- `ExitProfileRouter`
- `WaitEngine`
- `ExitManagePositions`

### 적용 방향

- 큰지도와 같은 방향은 더 기다릴 수 있게
- 큰지도와 반대 방향은 더 짧게
- 하단 BUY는 mid 저항 하나에 과하게 털리지 않게
- 상단 SELL은 첫 흔들림에 과하게 청산되지 않게

### 완료 기준

- “조금 먹고 바로 팔아버리는” 현상이 줄어든다.
- “같은 자리에서 연속 손실”이 줄어든다.

---

## 지금부터의 실제 작업 순서

### 1순위

- `R1-2`: Position scale live 확인
- `R1-3`: MTF MA 큰지도 설계
- `R1-4`: MTF trendline 거리 설계

### 2순위

- `R2-1`: candle descriptor
- `R2-2`: candle pattern
- `R2-3`: candle motif
- `R2-4`: structure motif

### 3순위

- `R2-5`: S/R raw
- `R2-6`: trendline raw
- `R2-7`: context gate

### 4순위

- `R3`: State 큰지도 보정
- `R4`: Evidence 결합 재정렬

### 5순위

- `R5`: Belief / Barrier
- `R6`: Exit / Wait

---

## 지금 단계 한 줄 요약

지금은 `Position 지도`를 다시 고정하는 단계이고, 이번에 `위치 스케일`까지 들어왔으니 다음은 `큰지도(MA/Trendline)`를 Position/State에 붙이고, 그 위에 `Response`를 descriptor -> pattern -> motif -> context gate -> 6축 구조로 다시 세우는 단계다.
