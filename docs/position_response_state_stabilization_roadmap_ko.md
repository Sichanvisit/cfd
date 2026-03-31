# Position / Response / State 안정화 및 연결성 강화 로드맵

## 목적

이 문서는 현재까지 재구성한 `Position`, `Response`, `State`가
큰 그림에서 서로 잘 어우러지는지 확인하고,
무엇을 어떤 순서로 테스트하고 보정해야 하는지를 고정하는 실행 로드맵이다.

이번 로드맵의 초점은 아래 4가지다.

1. `Position`이 지도 역할을 안정적으로 하는지 확인한다.
2. `Response`가 사건 역할을 안정적으로 하는지 확인한다.
3. `State`가 신뢰도/인내심/큰지도 해석 owner로 제대로 올라왔는지 확인한다.
4. 이 3개가 `Evidence -> ObserveConfirm -> Wait/Exit`로 자연스럽게 이어지는지 점검한다.

---

## 핵심 원칙

### Position

- 무엇을 말하나:
  - 현재 위치
  - 현재 거리
  - 현재 지도 크기
- 대표 필드:
  - `x_box`
    - 박스 기준 위치 에너지
  - `x_bb20`
    - BB20 기준 위치 에너지
  - `x_bb44`
    - BB44 기준 위치 에너지
  - `position_scale`
    - 지도 크기 관련 메타데이터 묶음
  - `mtf_ma_big_map_v1`
    - 상위 이평 지도
  - `mtf_trendline_map_v1`
    - 상위 추세선 지도

### Response

- 무엇을 말하나:
  - 그 위치에서 실제로 어떤 사건이 일어났는가
- 현재 구조:
  - `descriptor -> pattern -> motif -> subsystem -> context gate -> Response 6축`
- 최종 6축:
  - `lower_hold_up`
    - 하단 지지 반등 힘
  - `lower_break_down`
    - 하단 지지 붕괴 힘
  - `mid_reclaim_up`
    - 중심 회복 상승 힘
  - `mid_lose_down`
    - 중심 상실 하락 힘
  - `upper_reject_down`
    - 상단 저항 거절 힘
  - `upper_break_up`
    - 상단 저항 돌파 힘

### State

- 무엇을 말하나:
  - 지금 이 반응을 얼마나 믿을 만한가
  - 지금 얼마나 기다려야 하는가
  - 지금 얼마나 오래 들고 갈 가치가 있는가
- 현재 방향:
  - 단순 quality 보조기에서
  - `큰지도 + 신뢰도 + 인내심` 레이어로 승격 중

---

## 현재 구현 상태 요약

### 1. Position

현재 Position은 아래가 이미 구현돼 있다.

- 박스 / 볼린저 위치
  - `x_box`
  - `x_bb20`
  - `x_bb44`
- 지도 크기
  - `box_height`
  - `bb20_width`
  - `bb44_width`
  - `box_height_ratio`
  - `bb20_width_ratio`
  - `bb44_width_ratio`
  - `compression_score`
    - 지도가 얼마나 압축되어 있는지
  - `expansion_score`
    - 지도가 얼마나 확장되어 있는지
- MTF MA 지도
  - `mtf_ma_big_map_v1`
- MTF trendline 지도
  - `x_tl_m1`
  - `x_tl_m15`
  - `x_tl_h1`
  - `x_tl_h4`
  - `tl_proximity_m1`
  - `tl_proximity_m15`
  - `tl_proximity_h1`
  - `tl_proximity_h4`

판단:

- Position은 현재 `지도 owner`로는 꽤 안정적이다.
- 당분간 구조를 크게 흔들기보다 acceptance와 튜닝 중심으로 가는 게 맞다.

### 2. Response

현재 Response는 아래 구조가 이미 구현돼 있다.

- candle descriptor
  - `body_signed_energy`
    - 양봉/음봉 방향 강도
  - `body_shape_energy`
    - 봉 내부에서 몸통 비중
  - `upper_wick_energy`
    - 위꼬리 비중
  - `lower_wick_energy`
    - 아래꼬리 비중
  - `close_location_energy`
    - 종가가 고가 쪽인지 저가 쪽인지
  - `wick_balance_energy`
    - 아래꼬리 우세 vs 위꼬리 우세
  - `range_size_energy`
    - 봉 전체 길이의 최근 평균 대비 크기
  - `body_size_energy`
    - 몸통 길이의 최근 평균 대비 크기
- candle pattern
  - `hammer_like`
  - `shooting_star_like`
  - `bullish_engulfing_like`
  - `bearish_engulfing_like`
  - `morning_star_like`
  - `evening_star_like`
  - `three_white_soldiers_like`
  - `three_black_crows_like`
- candle motif
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
- structure motif
  - `reversal_base_up`
  - `reversal_top_down`
  - `support_hold_confirm`
  - `resistance_reject_confirm`
- S/R subsystem
  - `support_hold_strength`
  - `support_break_strength`
  - `resistance_reject_strength`
  - `resistance_break_strength`
- trendline subsystem
  - `trend_support_hold_strength`
  - `trend_support_break_strength`
  - `trend_resistance_reject_strength`
  - `trend_resistance_break_strength`
- micro-TF subsystem
  - `micro_bull_reject_strength`
  - `micro_bear_reject_strength`
  - `micro_bull_break_strength`
  - `micro_bear_break_strength`
  - `micro_indecision_strength`
- context gate
  - `response_context_gate_v1`
  - `pre_axis_candidates`
- Response 6축
  - 현재 `context_gated_candidate_primary_only`
  - legacy는 gate 자체가 없을 때만 기술 fallback

판단:

- Response는 현재 구조적으로는 가장 많이 정리된 상태다.
- 지금부터는 `재설계`보다 `관찰 + acceptance + 숫자 보정`이 우선이다.

### 3. State

최근 State는 아래 방향으로 끌어올린 상태다.

- raw
  - `s_topdown_bias`
    - 큰지도 signed bias
  - `s_topdown_agreement`
    - 큰지도 정합도
  - `s_compression`
    - 압축도
  - `s_expansion`
    - 확장도
  - `s_middle_neutrality`
    - 가운데 애매함
- state outputs
  - `topdown_bull_bias`
    - 상방 큰지도 편향
  - `topdown_bear_bias`
    - 하방 큰지도 편향
  - `big_map_alignment_gain`
    - 큰지도가 현재 반응과 맞을 때 주는 gain
  - `wait_patience_gain`
    - 기다릴 가치 보정
  - `confirm_aggression_gain`
    - confirm 쪽 공격성 보정
  - `hold_patience_gain`
    - 보유 인내심 보정
  - `fast_exit_risk_penalty`
    - 빠른 청산을 유도할 리스크 패널티
- labels
  - `regime_state_label`
  - `quality_state_label`
  - `topdown_state_label`
  - `patience_state_label`

판단:

- `Evidence`에는 이미 새 State가 일부 연결되어 있다.
- 하지만 `ObserveConfirm`, `WaitEngine`, `ExitProfileRouter`, `ExitManagePositions`에는 아직 직접 연결이 약하다.
- 즉 현재 가장 중요한 연결성 숙제는 `State -> execution layer` 쪽이다.

---

## 현재 가장 중요한 연결성 진단

### 이미 잘 연결된 부분

1. `Position -> Response context gate`
   - Position 요약이 Response gate 입력으로 들어간다.
2. `Position -> State raw`
   - `position_scale`, `mtf_context_weight_profile_v1`, `middle_neutrality`가 State raw로 들어간다.
3. `State -> Evidence`
   - `big_map_alignment_gain`
   - `topdown_bull_bias`
   - `topdown_bear_bias`
   가 Evidence multiplier로 반영된다.
4. `Response -> ObserveConfirm`
   - Response 6축과 archetype 기반 흐름은 이미 작동 중이다.

### 아직 약한 부분

1. `State -> ObserveConfirm`
   - 새 `wait_patience_gain`
   - `confirm_aggression_gain`
   - `patience_state_label`
   가 ObserveConfirm 의사결정에 직접 반영되는 정도가 아직 약하다.
2. `State -> WaitEngine`
   - `wait_patience_gain`이 실제 wait 성격을 직접 바꾸는 연결이 아직 약하다.
3. `State -> ExitProfileRouter`
   - `hold_patience_gain`
   - `fast_exit_risk_penalty`
   가 실제 hold/exit policy를 직접 바꾸는 연결이 아직 약하다.
4. `State -> ExitManagePositions`
   - 청산 집행 레벨에서 새 State 값이 체감적으로 반영되려면 후속 연결이 더 필요하다.

---

## 안정화의 큰 우선순위

현재는 아래 순서가 가장 안전하다.

1. `R2-9 freeze 유지`
2. `Position / Response / State acceptance`
3. `State -> ObserveConfirm` 연결 강화
4. `State -> Wait/Exit` 연결 강화
5. `보정`
6. `기본 승률/체감 검증`
7. `그 다음 ML shadow`

핵심 문장:

`ML 전에 기본 semantic 구조와 execution 연결이 이미 자연스럽고 높은 승률을 보여야 한다.`

---

## acceptance 시나리오

아래 시나리오를 기준으로 Position / Response / State가 함께 맞아야 한다.

### A. 하단 반등 케이스

기대:

- Position:
  - `lower edge` 또는 `lower context`
- Response:
  - `lower_hold_up` 우세
  - `lower_break_down`은 낮아야 함
- State:
  - `RANGE_SWING` 또는 `TREND_PULLBACK`에서 bullish reversal을 믿을 만하면 support
- ObserveConfirm:
  - 과도한 WAIT 없이 BUY candidate를 살려야 함

### B. 하단 붕괴 케이스

기대:

- Position:
  - 하단이더라도 붕괴 가능 자리
- Response:
  - `lower_break_down` 우세
- State:
  - `TREND` 또는 quality 저하 구간이면 break를 더 믿게 보정
- ObserveConfirm:
  - buy-type 관성으로 끌리지 않아야 함

### C. 상단 거절 케이스

기대:

- Position:
  - `upper edge` 또는 `upper context`
- Response:
  - `upper_reject_down` 우세
- State:
  - `RANGE_SWING` 또는 `topping/reject`를 믿을 만한 상태면 sell bias 강화
- ObserveConfirm:
  - upper reject를 WAIT로 너무 오래 죽이지 않아야 함

### D. 상단 돌파 케이스

기대:

- Position:
  - 상단 접근 또는 상단 돌파 지점
- Response:
  - `upper_break_up` 우세
- State:
  - `BREAKOUT_EXPANSION`류면 continuation 쪽 강화
- ObserveConfirm:
  - 상단이라고 무조건 SELL로 눌러버리지 않아야 함

### E. 중앙 reclaim 케이스

기대:

- Position:
  - middle 또는 lower->middle 회복 구간
- Response:
  - `mid_reclaim_up` 우세
- State:
  - chop/noise면 약화
  - healthy reclaim이면 강화

### F. 중앙 lose 케이스

기대:

- Position:
  - middle 근처
- Response:
  - `mid_lose_down` 우세
- State:
  - 추세 전환 초기인지 단순 노이즈인지 구분해 보정

### G. range swing alternation 케이스

기대:

- Position:
  - 상하단 왕복이 명확
- Response:
  - `lower_hold_up <-> upper_reject_down`가 번갈아 살아야 함
- State:
  - `RANGE_SWING`
  - `WAIT`보다 edge turn 실행을 약간 더 허용
- Exit:
  - 첫 흔들림에 자르지 말고 반대 edge까지 보유 가능

### H. trend continuation 케이스

기대:

- Position:
  - 큰지도 정렬
- Response:
  - pullback/reclaim 후 continuation 축이 살아야 함
- State:
  - `TREND_PULLBACK` 또는 `BREAKOUT_EXPANSION`
  - reversal보다 continuation 쪽 gain
- Exit:
  - 조기청산 줄이기

---

## 테스트 계층

### 1. 계약 테스트

목적:

- 필드가 살아 있는지
- contract가 안 깨졌는지

확인 대상:

- Position contract
- Response contract
- State contract
- Evidence contract
- ObserveConfirm contract

### 2. 결합 테스트

목적:

- `Position -> Response -> State -> Evidence -> ObserveConfirm` 흐름이 끊기지 않는지 확인

핵심 포인트:

- Position이 gate 입력으로 제대로 들어가는지
- State raw가 Position 메타를 받아오는지
- Evidence가 State gain/topdown을 받는지
- ObserveConfirm이 canonical fields를 읽는지

### 3. runtime acceptance

목적:

- live runtime에서 실제 필드가 보이는지 확인

필수 확인 항목:

- `position_snapshot_v2`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `observe_confirm_v2`
- `response_context_gate_v1`

### 4. 차트 케이스 테스트

목적:

- 스크린샷 체감과 엔진 해석이 맞는지 검증

필수 비교:

- 실제 진입 시점
- 들어갔어야 할 시점
- 실제 청산 시점
- 청산했어야 할 시점
- 그때의 Position / Response / State / ObserveConfirm 값

---

## 영어 변수 주석집

### Position 쪽

- `x_box`
  - 박스 안에서 현재가 위치
- `x_bb20`
  - BB20 기준 현재가 위치
- `x_bb44`
  - BB44 기준 현재가 위치
- `compression_score`
  - 지도 압축 강도
- `expansion_score`
  - 지도 확장 강도
- `position_conflict_score`
  - Position 내부 충돌 강도
- `middle_neutrality`
  - 가운데 애매함 강도

### Response 쪽

- `lower_hold_up`
  - 하단 지지 반등 축
- `lower_break_down`
  - 하단 지지 붕괴 축
- `mid_reclaim_up`
  - 중심 회복 상승 축
- `mid_lose_down`
  - 중심 상실 하락 축
- `upper_reject_down`
  - 상단 저항 거절 축
- `upper_break_up`
  - 상단 돌파 상승 축
- `support_hold_strength`
  - 수평 지지선 hold 강도
- `support_break_strength`
  - 수평 지지선 break 강도
- `resistance_reject_strength`
  - 수평 저항선 reject 강도
- `resistance_break_strength`
  - 수평 저항선 break 강도
- `trend_support_hold_strength`
  - 추세선 지지 hold 강도
- `trend_support_break_strength`
  - 추세선 지지 break 강도
- `trend_resistance_reject_strength`
  - 추세선 저항 reject 강도
- `trend_resistance_break_strength`
  - 추세선 저항 break 강도
- `micro_bull_reject_strength`
  - 1M/5M bullish reject 강도
- `micro_bear_reject_strength`
  - 1M/5M bearish reject 강도
- `micro_bull_break_strength`
  - 1M/5M bullish break 강도
- `micro_bear_break_strength`
  - 1M/5M bearish break 강도
- `micro_indecision_strength`
  - 1M/5M 애매함 강도
- `ambiguity_penalty`
  - gate가 애매하다고 판단해 축을 눌러버리는 패널티

### State 쪽

- `topdown_bull_bias`
  - 큰지도가 상방을 얼마나 밀어주는지
- `topdown_bear_bias`
  - 큰지도가 하방을 얼마나 밀어주는지
- `big_map_alignment_gain`
  - 큰지도와 현재 해석이 맞을 때 주는 gain
- `wait_patience_gain`
  - WAIT을 더 허용하는 인내심 gain
- `confirm_aggression_gain`
  - confirm 쪽으로 기울게 하는 gain
- `hold_patience_gain`
  - 보유를 더 유지하게 하는 gain
- `fast_exit_risk_penalty`
  - 빠른 청산을 유도하는 리스크 패널티
- `regime_state_label`
  - 장 모드 라벨
- `quality_state_label`
  - 시장 품질 라벨
- `topdown_state_label`
  - 큰지도 정렬 라벨
- `patience_state_label`
  - WAIT/CONFIRM/HOLD 성격 라벨

---

## 보정 우선순위

현재 기준으로는 아래 순서가 좋다.

1. `State -> ObserveConfirm` 연결
   - 이유:
     - 지금 가장 큰 체감 병목은 `Response는 읽었는데 WAIT가 너무 많다`
     - 새 `wait_patience_gain`, `confirm_aggression_gain`가 ObserveConfirm에 더 직접적으로 반영돼야 한다.
2. `State -> Wait/Exit` 연결
   - 이유:
     - `hold_patience_gain`
     - `fast_exit_risk_penalty`
     가 실제 보유/청산에서 살아야 한다.
3. `ambiguity_penalty`
   - 이유:
     - gate 과보수 문제를 먼저 줄여야 한다.
4. `micro 반응 비중`
   - 이유:
     - 타이밍 문제를 조절하는 핵심이다.
5. `S/R vs trendline 비중`
   - 이유:
     - 어떤 선이 실질 owner가 되는지 체감에 큰 영향을 준다.
6. `mid reclaim / mid lose 민감도`
   - 이유:
     - 중앙 구간 체감 오판 방지용

---

## 실행 로드맵

### Phase 0. Freeze 유지

목표:

- Position/Response/State owner 계약을 더 이상 흔들지 않는다.

완료 기준:

- 큰 구조 수정 없이 acceptance와 보정만 진행

### Phase 1. Position / Response / State acceptance

목표:

- 각각이 자기 역할을 제대로 하는지 확인

해야 할 것:

- Position edge/middle acceptance
- Response 6축 acceptance
- State label/gain acceptance

완료 기준:

- 대표 시나리오에서 각 레이어 역할이 설명 가능

### Phase 2. 연결성 acceptance

목표:

- 세 레이어가 실제로 이어지는지 확인

해야 할 것:

- `Position -> Response gate`
- `Position -> State raw`
- `State -> Evidence`
- `State -> ObserveConfirm`
- `State -> Wait/Exit`
를 따로 점검

완료 기준:

- 어디까지 연결됐고 어디가 아직 비어 있는지 명확해짐

### Phase 3. execution 연결 보강

목표:

- 새 State가 실제 행동을 바꾸게 한다.

우선 작업:

1. ObserveConfirm이
   - `wait_patience_gain`
   - `confirm_aggression_gain`
   - `patience_state_label`
   를 읽게 한다.
2. Wait/Exit가
   - `hold_patience_gain`
   - `fast_exit_risk_penalty`
   를 읽게 한다.

완료 기준:

- `WAIT 과보수`
- `조기청산`
증상이 줄어든다.

### Phase 4. 숫자 보정

목표:

- 구조를 안 바꾸고 민감도만 맞춘다.

보정 순서:

1. `ambiguity_penalty`
2. `micro reaction weight`
3. `S/R vs trendline weight`
4. `mid reclaim / lose sensitivity`

완료 기준:

- 스크린샷 체감과 엔진 해석의 차이가 줄어든다.

### Phase 5. 기본형 검증

목표:

- ML 없이도 기본형이 괜찮은지 확인

봐야 할 것:

- 좋은 진입
- 좋은 기다림
- 좋은 보유
- 조기청산 감소
- 불필요한 churn 감소

완료 기준:

- "이 기본형이면 돌릴 만하다"는 수준 확보

### Phase 6. ML shadow

목표:

- 의미 구조를 유지한 채 숫자 보정만 shadow로 검증

주의:

- 이 단계 전에는 ML로 구조를 보정하려고 하지 않는다.

---

## 지금 바로 시작할 순서

현 시점에서 제일 현실적인 다음 순서는 이거다.

1. `State -> ObserveConfirm` 연결 acceptance를 먼저 본다.
2. `State -> Wait/Exit` 연결 acceptance를 본다.
3. `ambiguity_penalty`가 과보수인지 확인한다.
4. 차트 케이스 3~5개로 edge-turn / reclaim / lose를 비교한다.
5. 그 다음에야 숫자 보정에 들어간다.

즉 다음 핵심 질문은 이것이다.

`새 State가 지금 실제로 WAIT / CONFIRM / HOLD를 얼마나 바꾸고 있는가?`

이 질문에 답할 수 있어야, 다음 보정과 나중 ML도 자연스럽게 이어진다.
