# Share / Previous Box / HTF Trend Context 상세 계획

## 1. 왜 이 축이 필요한가

지금 사용자가 체감하는 핵심 문제는 이렇다.

- 차트에서는 `계속 올라갈 가능성`, `늦은 추격`, `상위 추세 역행 숏/매수`가 분명히 보이는데
- 현재 시스템 surface는 주로
  - 현재 force
  - 현재 box state
  - 최근 3봉 흐름
  - semantic observe/blocked 군집
  정도까지만 본다.

즉 시스템이 완전히 못 보는 것은 아니지만,
사람이 실제로 보는 좌표계 3개가 빠져 있다.

1. 전체 share / 시간대 box 점유 맥락
2. 직전 box 라인과 현재 위치 관계
3. 1H / 4H / 1D 상위 추세 정합성

이 3축이 빠지면 다음 같은 장면에서 설명이 약해진다.

- 늦게 따라붙었는데 이미 상위 추세가 계속 밀고 있는 장면
- 직전 box 상단을 회복한 뒤 재상승 중인 장면
- 현재 15M 해석은 SELL인데 1H / 4H / 1D는 계속 상승 구조인 장면


## 2. 현재 어디까지 되어 있는가

### 2-1. 이미 있는 것

- `cluster_share`, `cluster_symbol_share`
  - semantic baseline no-action cluster 후보에서 부분적으로 사용 중
- `box_state`
  - `LOWER / MIDDLE / UPPER / ABOVE` 정도의 현재 박스 위치는 있음
- `box_relative_position`
  - detector evidence로는 proxy/direct 혼합 방식으로 있음
- `position_dominance`, `wick/body`, `recent_3bar_direction`
  - P4-6에서 이미 구축됨
- `forecast_runtime_summary_v1`
  - continuation / false_break / fail_now / decision_hint는 있음

### 2-2. 아직 부족한 것

- `직전 box high / low / mid / break / reclaim 상태`
  - 현재 latest runtime row에는 직접 없음
- `1H / 4H / 1D trend direction / slope / alignment`
  - 현재 latest runtime row에는 직접 없음
- `time-box share`
  - 현재 share는 cluster 기준으로만 있고, 시간대 박스 점유 맥락은 없음

### 2-3. 현재 최신 NAS100 관찰 상태

현재 latest runtime 기준으로 NAS100은 대략 이렇게 읽힌다.

- `consumer_check_side = SELL`
- `consumer_check_reason = upper_break_fail_confirm`
- `box_state = ABOVE`
- `forecast decision_hint = WAIT_BIASED`

그리고 semantic sample audit 쪽에는 다음 군집이 있다.

- `NAS100 | upper_break_fail_confirm | energy_soft_block | execution_soft_blocked`

이건 이미 `상승 지속 누락 가능성 관찰`로 자동 candidate화할 수 있게 보강했지만,
여전히 다음 질문에는 직접 답하지 못한다.

- 지금이 직전 box 상단 위인지 아래인지
- 직전 box를 재돌파한 상태인지
- 1H / 4H / 1D가 계속 상승인지 아닌지


## 3. 왜 지금 표식이 충분히 안 좋아졌는가

지금 표식이 안 좋아지는 이유는 “학습을 하나도 안 한다”가 아니라,
학습에 들어가는 좌표계가 사람 좌표계보다 좁기 때문이다.

현재 시스템은 대체로 이런 식으로 본다.

- 현재 force가 어느 쪽 우세인가
- 현재 box가 upper/lower 어디인가
- 최근 3봉은 오르나 내리나
- semantic이 observe/blocked로 반복되는가

하지만 사용자는 이런 식으로 본다.

- 지금은 이전 박스 상단을 이미 회복했다
- 이건 15M만 보면 애매해도 1H/4H/1D는 계속 상승 추세다
- 지금 반대로 따라가면 늦은 추격 숏/매수가 된다

즉 지금 필요한 건 “새 예측 엔진”보다,
사람이 실제로 차트를 보는 기준을 detector/propose/notifier가 같이 보게 만드는 것이다.


## 4. 앞으로 추가해야 할 evidence 계약

### 4-1. Share Context

목적:
- 현재 장면이 전체 로그에서 얼마나 큰지뿐 아니라
- 심볼 내부, 시간대 내부에서 얼마나 반복되는지 본다.

추가 후보 필드:

- `cluster_share_global`
- `cluster_share_symbol`
- `time_box_share_15m`
- `time_box_share_1h`
- `time_box_share_session`
- `share_context_label_ko`

해석 예:

- `global 18.3% / symbol 93.8%`
  - 전체로는 작아 보여도 NAS100 안에서는 거의 지배적인 장면


### 4-2. Previous Box Context

목적:
- “현재 box 위치”만이 아니라
- “직전 box 경계와의 관계”를 본다.

추가 후보 필드:

- `previous_box_high`
- `previous_box_low`
- `previous_box_mid`
- `previous_box_relation`
  - `ABOVE_PREV_HIGH`
  - `INSIDE_PREV_BOX`
  - `BELOW_PREV_LOW`
- `previous_box_break_state`
  - `BREAKOUT_HELD`
  - `BREAKOUT_FAILED`
  - `RECLAIMED`
  - `REJECTED`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`

해석 예:

- `직전 박스 상단 회복 후 유지`
- `직전 박스 상단 위 체류 중`
- `직전 박스 상단 재돌파 실패`


### 4-3. HTF Trend Context

목적:
- 현재 15M 판단이 상위 추세와 정합인지 본다.

추가 후보 필드:

- `trend_15m_direction`
- `trend_1h_direction`
- `trend_4h_direction`
- `trend_1d_direction`
- `trend_1h_slope`
- `trend_4h_slope`
- `trend_1d_slope`
- `htf_alignment_state`
  - `WITH_HTF`
  - `AGAINST_HTF`
  - `MIXED_HTF`
- `htf_trend_label_ko`

해석 예:

- `15M SELL이지만 1H/4H/1D는 상승 정렬`
- `상위 추세와 같은 방향`
- `상위 추세 혼조`


## 5. 어디에 붙여야 하는가

### 업스트림 runtime payload

현재 직접 필드가 없기 때문에, 먼저 runtime 최신 row에 이 축을 올려야 한다.

후보 파일:

- [trading_application_runner.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application_runner.py)
- latest runtime snapshot을 구성하는 upstream bridge/service

### detector

후보 파일:

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

해야 할 일:

- 기존 `force / box / wick / recent_3bar` evidence에
  - share context
  - previous box context
  - HTF trend context
  를 추가
- NAS100 continuation-gap 장면에서는
  - `계속 올라갈 가능성`
  - `직전 box 상단 위 유지`
  - `상위 추세 역행 SELL 경계`
  같은 문장을 만들 수 있게 함

### notifier / DM

후보 파일:

- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

해야 할 일:

- 평소 DM은 짧게 유지
- 단, mismatch가 강할 때만
  - `직전 박스`
  - `상위 추세`
  - `share`
  를 한 줄로 보여줌

예:

- `직전 박스: 상단 위 유지 | 상위 추세: 1H/4H 상승 정렬 | share: NAS100 내부 93.8%`

### proposal / hindsight

후보 파일:

- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)

해야 할 일:

- 새 evidence key를 registry에 등록
- proposal에서 어떤 장면이 반복되는지
  - `상승 지속 누락`
  - `직전 box 돌파 유지`
  - `상위 추세 역행 진입`
  로 요약 가능하게 함


## 6. 구축 원칙

### 해야 하는 것

- 먼저 evidence를 올린다
- 사람 언어로 surface한다
- detector/propose에서 자동으로 누적되게 한다
- feedback이 들어오면 그때 review 우선순위를 높인다

### 아직 하면 안 되는 것

- 이 3축만 보고 자동 진입/청산을 바꾸기
- HTF만으로 side를 뒤집기
- previous box만으로 바로 apply

지금 단계는 어디까지나
`좌표계 맞추기 -> surface 강화 -> 누적 학습`
이다.


## 7. 기대 효과

이 축이 들어오면 사용자가 느끼는 가장 큰 불만,

- “이건 계속 올라갈 것 같았는데 왜 전달을 못했지?”
- “늦은 추격인데 왜 그걸 못 잡았지?”
- “표식이 차트 체감보다 너무 약하다”

를 직접 겨냥할 수 있다.

즉 이건 단순 feature 추가가 아니라,
시스템이 사람과 같은 차트 좌표계로 보기 시작하게 만드는 공사다.
