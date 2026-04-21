# Teacher-State 25 ↔ Micro-Structure Top10 Casebook Bridge

## 목적

이 문서는 `1분봉 25개 teacher-state`를 현재 시스템의 `micro-structure Top10`과 연결하는 실사용 기준서다.

원칙은 간단하다.

- 각 pattern마다 `핵심 micro field 2~4개`
- 필요할 때만 `기존 state/forecast field`
- 마지막에 `행동 바이어스`

## A. 조용한 장

### 1. 쉬운 루즈장
- 핵심 micro:
  - `body_size_pct_20`
  - `doji_ratio_20`
  - `direction_run_stats`
- 같이 볼 기존 field:
  - `regime_volatility_ratio`
  - `micro_participation_state`
- 행동 바이어스:
  - `wait`
- 해석:
  - 몸통이 작고 도지가 많고 연속 방향성이 약하면 루즈장 가능성이 높다.

### 10. 공허한 횡보장
- 핵심 micro:
  - `doji_ratio_20`
  - `range_compression_ratio_20`
  - `direction_run_stats`
- 같이 볼 기존 field:
  - `middle_chop_barrier`
  - `position_conflict_score`
- 행동 바이어스:
  - `wait`
- 해석:
  - 좁은 범위 안에서 도지와 혼전이 반복되면 추세형보다 공허한 횡보장에 가깝다.

### 14. 모닝 컨솔리데이션
- 핵심 micro:
  - `range_compression_ratio_20`
  - `doji_ratio_20`
  - `volume_burst_decay_20`
- 같이 볼 기존 field:
  - `entry_session_name`
  - `session_expansion_progress`
- 행동 바이어스:
  - `short_wait`
- 해석:
  - 장 시작 직후 압축이 유지되고 거래량 burst가 아직 본격 지속으로 이어지지 않으면 아침 컨솔리데이션으로 본다.

### 13. 변동성 컨트랙션
- 핵심 micro:
  - `range_compression_ratio_20`
  - `body_size_pct_20`
  - `volume_burst_decay_20`
- 같이 볼 기존 field:
  - `s_compression`
  - `micro_breakout_readiness_state`
- 행동 바이어스:
  - `wait`
- 해석:
  - 범위와 몸통이 줄고 burst 이후 식는 흐름이면 컨트랙션으로 읽는다.

### 23. 삼각수렴 압축
- 핵심 micro:
  - `range_compression_ratio_20`
  - `swing_high_retest_count_20`
  - `swing_low_retest_count_20`
- 같이 볼 기존 field:
  - `position_in_session_box`
  - `box_state`
- 행동 바이어스:
  - `short_wait`
- 해석:
  - 범위가 줄면서 위아래를 반복 테스트하면 삼각수렴형 압축으로 본다.

## B. 추세장

### 4. 추세 지속장
- 핵심 micro:
  - `direction_run_stats`
  - `body_size_pct_20`
  - `volume_burst_decay_20`
- 같이 볼 기존 field:
  - `buy_persistence / sell_persistence`
  - `p_continuation_success`
- 행동 바이어스:
  - `entry`
- 해석:
  - 방향 연속성이 강하고 몸통이 유지되며 volume이 급격히 죽지 않으면 추세 지속장이다.

### 6. 점진적 추세장
- 핵심 micro:
  - `direction_run_stats`
  - `body_size_pct_20`
  - `range_compression_ratio_20`
- 같이 볼 기존 field:
  - `trend_pullback_gain`
  - `hold_patience_gain`
- 행동 바이어스:
  - `entry`
- 해석:
  - 연속 방향성은 있으나 몸통이 과격하지 않고 눌림이 정돈되어 있으면 점진적 추세장에 가깝다.

### 15. 캔들 연속 패턴
- 핵심 micro:
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `buy_streak / sell_streak`
  - `confirm_aggression_gain`
- 행동 바이어스:
  - `entry`
- 해석:
  - 같은 방향 봉 연속성이 직접 핵심이다.

### 19. 속도감 추세장
- 핵심 micro:
  - `body_size_pct_20`
  - `direction_run_stats`
  - `volume_burst_decay_20`
- 같이 볼 기존 field:
  - `regime_volatility_ratio`
  - `micro_participation_state`
- 행동 바이어스:
  - `breakout_entry`
- 해석:
  - 큰 몸통, 높은 속도, 강한 참여가 동시에 붙을 때 속도감 추세장으로 읽는다.

### 24. 플래그 패턴장
- 핵심 micro:
  - `range_compression_ratio_20`
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `trend_pullback_gain`
  - `breakout_continuation_gain`
- 행동 바이어스:
  - `confirm_entry`
- 해석:
  - 강한 방향 이동 후 좁아진 조정 박스가 이어지면 플래그 재개 후보로 본다.

## C. 발산장

### 12. 브레이크아웃 직전
- 핵심 micro:
  - `range_compression_ratio_20`
  - `volume_burst_decay_20`
  - `direction_run_stats`
- 같이 볼 기존 field:
  - `micro_breakout_readiness_state`
  - `breakout_continuation_gain`
- 행동 바이어스:
  - `breakout_wait_then_entry`
- 해석:
  - 압축이 쌓이고 volume 준비가 보이면 브레이크아웃 직전으로 본다.

### 7. 변동성 확대장
- 핵심 micro:
  - `body_size_pct_20`
  - `volume_burst_decay_20`
  - `range_compression_ratio_20`
- 같이 볼 기존 field:
  - `regime_volatility_ratio`
  - `micro_participation_state`
- 행동 바이어스:
  - `conditional`
- 해석:
  - 몸통이 커지고 참여가 살아나지만 아직 방향 확정 전이면 변동성 확대장이다.

### 17. 거래량 폭발장
- 핵심 micro:
  - `volume_burst_decay_20`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `current_tick_volume_ratio`
  - `tick_flow_burst`
- 행동 바이어스:
  - `conditional_breakout`
- 해석:
  - 거래량 burst가 구조적으로 핵심이고, 몸통이 뒤따르면 진짜 발산 가능성이 높다.

### 3. 갑자기 발작장
- 핵심 micro:
  - `body_size_pct_20`
  - `volume_burst_decay_20`
  - `direction_run_stats`
- 같이 볼 기존 field:
  - `shock_score`
  - `fast_exit_risk_penalty`
- 행동 바이어스:
  - `fast_decision`
- 해석:
  - 갑작스런 큰 몸통과 거래량 burst가 짧게 폭발하면 발작장으로 본다.

## D. 반전·되돌림장

### 5. Range 반전장
- 핵심 micro:
  - `swing_high_retest_count_20`
  - `swing_low_retest_count_20`
  - `doji_ratio_20`
- 같이 볼 기존 field:
  - `range_reversal_gain`
  - `middle_chop_barrier`
- 행동 바이어스:
  - `fade_entry`
- 해석:
  - 상하단 재시험과 도지 혼전이 많으면 range 반전장 가능성이 높다.

### 11. 눌림목 반등장
- 핵심 micro:
  - `lower_wick_ratio_20`
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `trend_pullback_gain`
  - `lower_hold_up`
- 행동 바이어스:
  - `confirm_entry`
- 해석:
  - 눌림 뒤 하단 wick 지지와 방향 재개가 보이면 눌림목 반등장에 가깝다.

### 16. 페이크아웃 반전
- 핵심 micro:
  - `upper_wick_ratio_20`
  - `lower_wick_ratio_20`
  - `swing_high_retest_count_20`
- 같이 볼 기존 field:
  - `p_false_break`
  - `micro_reversal_risk_state`
- 행동 바이어스:
  - `fast_cut_or_fade`
- 해석:
  - 긴 wick과 반복 테스트 후 되밀림이 핵심이라 reversal risk가 높게 읽혀야 한다.

### 22. 더블탑/바텀
- 핵심 micro:
  - `swing_high_retest_count_20`
  - `swing_low_retest_count_20`
  - `doji_ratio_20`
- 같이 볼 기존 field:
  - `pattern_double_top / bottom`
  - `range_reversal_gain`
- 행동 바이어스:
  - `confirm_reversal`
- 해석:
  - 동일 고점/저점 재시험 횟수가 핵심이다.

### 25. 데드캣 바운스
- 핵심 micro:
  - `upper_wick_ratio_20`
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `countertrend_with_entry`
  - `prefer_fast_cut`
- 행동 바이어스:
  - `fast_cut`
- 해석:
  - 약한 반등 뒤 다시 눌리는 구조라 upper wick과 countertrend fast-cut 성격이 강하다.

### 21. 갭필링 진행장
- 핵심 micro:
  - `gap_fill_progress`
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `position_in_session_box`
  - `session_expansion_progress`
- 행동 바이어스:
  - `confirm_or_range_take`
- 해석:
  - gap 메움 진행률이 직접 핵심이다.

## E. 전환·위험장

### 2. 변동성 큰 장
- 핵심 micro:
  - `body_size_pct_20`
  - `upper_wick_ratio_20`
  - `lower_wick_ratio_20`
- 같이 볼 기존 field:
  - `regime_volatility_ratio`
  - `execution_friction_state`
- 행동 바이어스:
  - `conditional_or_fast_cut`
- 해석:
  - 큰 몸통과 긴 wick이 같이 나오면 거친 위험장 성격이 강하다.

### 8. 죽음의 가위장
- 핵심 micro:
  - `direction_run_stats`
  - `body_size_pct_20`
- 같이 볼 기존 field:
  - `topdown_bear_bias`
  - `sell_persistence`
- 행동 바이어스:
  - `sell_confirm`
- 해석:
  - 하락 쪽 연속성과 추세 전환 편향을 같이 봐야 한다.

### 9. 황금십자 직전
- 핵심 micro:
  - `direction_run_stats`
  - `body_size_pct_20`
  - `range_compression_ratio_20`
- 같이 볼 기존 field:
  - `topdown_bull_bias`
  - `buy_persistence`
- 행동 바이어스:
  - `early_buy_confirm`
- 해석:
  - 상승 전환 초입은 몸통 확대보단 연속성과 정렬 회복이 더 중요하다.

### 18. 꼬리물림장
- 핵심 micro:
  - `upper_wick_ratio_20`
  - `lower_wick_ratio_20`
  - `doji_ratio_20`
- 같이 볼 기존 field:
  - `position_conflict_score`
  - `micro_reversal_risk_state`
- 행동 바이어스:
  - `avoid_or_fast_cut`
- 해석:
  - 양쪽 wick과 indecision이 많은 충돌형 장세다.

### 20. 엔진 꺼짐장
- 핵심 micro:
  - `body_size_pct_20`
  - `doji_ratio_20`
  - `volume_burst_decay_20`
- 같이 볼 기존 field:
  - `hold_patience_gain`
  - `fast_exit_risk_penalty`
- 행동 바이어스:
  - `scale_out_or_exit`
- 해석:
  - 몸통이 줄고 도지가 늘고 burst가 꺼지면 엔진 꺼짐장으로 읽는다.

## 행동축 요약

### 진입 우선
- `4`, `6`, `11`, `12`, `15`, `19`, `24`

### 기다림 우선
- `1`, `10`, `13`, `14`, `23`

### 청산/컷 우선
- `16`, `20`, `25`

### 조건부
- `2`, `3`, `5`, `7`, `8`, `9`, `17`, `18`, `21`, `22`

## 결론

Step 7 bridge의 의미는 `teacher-state 25`를 실제 시스템 feature 위에 올려놓는 것이다.

즉 이제부터는

- 사람이 “이건 12번 브레이크아웃 직전”이라고 붙였을 때
- 시스템은 `range_compression_ratio_20 + volume_burst_decay_20 + direction_run_stats + breakout_readiness_state`
를 같이 보게 되고
- 그 패턴이 진입/기다림/청산 중 어디로 연결되는지도 같은 문맥에서 읽게 된다.
