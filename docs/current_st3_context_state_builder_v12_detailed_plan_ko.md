# ST3 Context State Builder v1.2 상세 계획

## 목표

`HTF state v1`와 `previous box state v1`를 하나의 공용 context 묶음으로 조립하고,
downstream이 raw를 다시 조합하지 않도록

- `context_conflict_state`
- `context_conflict_flags`
- `context_conflict_intensity`
- `late_chase_risk_state`

까지 upstream에서 먼저 계산한다.


## 왜 ST3가 필요한가

`ST1`과 `ST2`만으로는 아직 detector/notifier가

- HTF 따로 읽고
- previous box 따로 읽고
- 필요하면 다시 조합해서

판단해야 한다.

이러면 다시 서비스마다 해석이 갈라질 수 있다.

그래서 `ST3`에서는 `raw + interpreted context`를 한 번에 조립하는
`context_state_builder.py`를 둔다.


## 이번 단계 범위

이번 `ST3`에서 구현할 것:

- `backend/services/context_state_builder.py`
- HTF state merge
- previous box state merge
- optional share state merge
- `context_conflict_state` primary
- `context_conflict_flags`
- `context_conflict_intensity`
- `context_conflict_score`
- `context_conflict_label_ko`
- `late_chase_risk_state`
- `late_chase_reason`
- `late_chase_confidence`
- `late_chase_trigger_count`

이번 단계에서 하지 않을 것:

- runtime latest payload 합류
- detector/notifier 직접 연결
- decision core scoring 반영
- trend quality 본계산


## 구현 원칙

### 1. primary + flags 같이 둔다

- `context_conflict_state`
  - downstream quick summary용
- `context_conflict_flags`
  - 복합 상태 보존용

즉 요약은 단순하게 유지하되, 정보 손실은 줄인다.

### 2. late chase는 독립 축으로 유지하되 conflict에도 반영한다

`late_chase_risk_state`는 별도 필드로 유지한다.
동시에 late chase가 켜지면 `context_conflict_flags`에도 `LATE_CHASE_RISK`를 넣어,
downstream summary가 쉽게 읽을 수 있게 한다.

### 3. share는 optional merge

`ST6` 이전이므로 share는 필수 계산 대상이 아니다.
다만 입력으로 들어오면:

- `cluster_share_symbol_band`
- `share_context_label_ko`

정도는 바로 보강해준다.


## conflict 계산 규칙

### primary 우선순위

1. `AGAINST_PREV_BOX_AND_HTF`
2. `LATE_CHASE_RISK`
3. `AGAINST_HTF`
4. `AGAINST_PREV_BOX`
5. `CONTEXT_MIXED`
6. `NONE`

### AGAINST_HTF

- `consumer_check_side = BUY`
  - `1H / 4H / 1D` 중 반대 방향이 다수면 against
- `consumer_check_side = SELL`
  - `1H / 4H / 1D` 중 상승이 다수면 against

severity는 HTF strength score 평균으로 낮음/중간/강함을 정한다.

### AGAINST_PREV_BOX

- `SELL`인데
  - `previous_box_break_state = BREAKOUT_HELD`
  - 또는 `previous_box_relation in ABOVE / AT_HIGH`
- `BUY`인데
  - `previous_box_break_state = BREAKDOWN_HELD`
  - 또는 `previous_box_relation in BELOW / AT_LOW`

confidence가 높을수록 intensity를 올린다.

### CONTEXT_MIXED

- side가 없고
- HTF가 혼조거나
- previous box confidence/lifecycle이 약하면

`CONTEXT_MIXED`


## late_chase 초기 규칙

지원 reason:

- `EXTENDED_ABOVE_PREV_BOX`
- `AGAINST_PULLBACK_DEPTH`
- `HTF_ALREADY_EXTENDED`
- `MULTI_BAR_RUN_AFTER_BREAK`

초기 기준:

- `EXTENDED_ABOVE_PREV_BOX`
  - BUY
  - `previous_box_relation = ABOVE`
  - `distance_from_previous_box_high_pct > 1.5`
- `AGAINST_PULLBACK_DEPTH`
  - `pullback_ratio < 0.25`
- `HTF_ALREADY_EXTENDED`
  - BUY
  - `trend_1h_direction = UPTREND`
  - `trend_15m_direction = UPTREND`
  - `trend_1h_strength_score >= 2.0`
  - `previous_box_relation = ABOVE`
- `MULTI_BAR_RUN_AFTER_BREAK`
  - BUY
  - `previous_box_break_state = BREAKOUT_HELD`
  - `same_color_run_current >= 5`

위 기준 충족 개수와 강도를 바탕으로

- `late_chase_risk_state`
  - `NONE`
  - `EARLY_WARNING`
  - `HIGH`

를 만든다.


## meta

이번 builder가 같이 내보내는 meta:

- `context_state_version`
- `htf_context_version`
- `previous_box_context_version`
- `conflict_context_version`
- `share_context_version`
- `context_state_built_at`


## 완료 기준

- `context_state_builder.py` 존재
- HTF/previous box/share merge 가능
- conflict/late chase 계산 가능
- unit test 통과
- `py_compile` 통과
