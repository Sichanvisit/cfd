# State-First Context Contract Gap 상세 계획

## 1. 왜 detector보다 state가 먼저인가

현재 사용자가 체감하는 문제는 detector가 완전히 틀렸다는 것보다,
detector가 먹는 최신 state payload가 너무 얇아서 사람과 같은 좌표계로 보지 못한다는 점에 가깝다.

예를 들어 지금 NAS100 최신 runtime row에는 대체로 다음 정도만 보인다.

- `consumer_check_side`
- `consumer_check_reason`
- `box_state`
- `signal_timeframe`
- 일부 force / forecast 요약

하지만 사용자는 실제 차트를 볼 때 다음 정보를 같이 본다.

- 직전 박스 상단/하단과 현재가 관계
- 직전 박스 돌파 유지인지 실패인지
- 1H / 4H / 1D 상위 추세 방향
- 현재 15M 판단이 상위 추세와 정합인지 역행인지
- 이 장면이 심볼 내부에서 얼마나 반복되는지

즉 지금 문제의 본질은:

- detector 로직 부족도 있지만
- 그보다 먼저
- **state contract에 올라오는 정보가 부족하다**

따라서 다음 단계는 detector를 더 복잡하게 만드는 것이 아니라,
사람이 보는 큰 그림을 **runtime latest state contract**로 먼저 끌어올리는 것이다.


## 2. 현재 이미 있는 것

코드를 보면 필요한 재료가 완전히 없는 것은 아니다.

### 2-1. Higher timeframe fetch 인프라

관련 파일:

- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [mt5_snapshot_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\mt5_snapshot_service.py)
- [trade_constants.py](C:\Users\bhs33\Desktop\project\cfd\backend\core\trade_constants.py)

이미 존재하는 단서:

- `TIMEFRAME_H1`
- `TIMEFRAME_H4`
- `TIMEFRAME_D1`
- `copy_rates_from_pos(...)`

즉 1H / 4H / 1D 데이터를 아예 못 가져오는 구조는 아니다.

### 2-2. Box / session / swing 단서

관련 파일:

- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

이미 존재하는 단서:

- `box_low`
- `box_high`
- `session_position`
- `session_expansion_progress`
- `swing_high_retest_count_20`
- `swing_low_retest_count_20`

즉 직전 박스/돌파 유지 관련 정보의 재료도 어느 정도는 있다.

### 2-3. 현재 detector가 이미 쓰는 일부 구조 증거

관련 파일:

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

이미 사용 중:

- `box_relative_position`
- `box_zone`
- `upper_wick_ratio`
- `lower_wick_ratio`
- `recent_3bar_direction`

즉 detector는 아예 빈 상태가 아니라,
**현재 state contract에 올라온 좁은 증거만 읽고 있는 상태**다.


## 3. 지금 부족한 것

현재 최신 runtime row에 직접 없거나 충분히 노출되지 않는 핵심은 아래 3축이다.

### 3-1. HTF Trend Context

부족한 필드 예:

- `trend_1h_direction`
- `trend_4h_direction`
- `trend_1d_direction`
- `htf_alignment_state`
- `htf_alignment_detail`
- `trend_1h_strength`
- `trend_4h_strength`
- `trend_1d_strength`

지금은 `forecast`가 일부 higher-level bias를 간접 반영하지만,
사람이 이해할 수 있는 직접 필드로는 없다.

### 3-2. Previous Box Context

부족한 필드 예:

- `previous_box_high`
- `previous_box_low`
- `previous_box_mid`
- `previous_box_relation`
- `previous_box_break_state`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`

현재는 `box_state` 정도만 있어
“이미 이전 박스 상단 위 체류 중” 같은 핵심 맥락을 직접 말하기 어렵다.

### 3-3. Share Context

부족한 필드 예:

- `cluster_share_global`
- `cluster_share_symbol`
- `time_box_share_15m`
- `time_box_share_1h`
- `time_box_share_session`

현재 일부 semantic cluster에는 `cluster_share`, `cluster_symbol_share`가 있지만
runtime latest state contract나 detector evidence의 공통 state로는 올라와 있지 않다.


## 4. 왜 state contract가 먼저여야 하는가

### detector만 먼저 손대면 생기는 문제

- detector가 자체 fallback/proxy를 계속 늘리게 된다
- detector마다 서로 다른 방식으로 HTF / 박스 / share를 흉내 내게 된다
- 나중에 같은 개념이 여러 이름으로 퍼진다
- notifier/propose/hindsight와 의미 정합성이 깨진다

### state contract부터 올리면 좋은 점

- detector / notifier / propose가 같은 필드를 본다
- 나중에 direct binding도 더 쉬워진다
- 오판의 원인이 detector인지 state 부족인지 구분 가능하다
- 사람이 보는 큰 그림이 runtime 최신 snapshot에 남는다

즉 지금의 정답은:

- detector를 더 똑똑하게 만들기 전에
- detector가 볼 **state를 먼저 풍부하게 만드는 것**


## 5. state-first 구축 원칙

### 원칙 1. 계산과 surface를 분리한다

- upstream state layer
  - 계산
  - raw field 생성
- downstream detector/notifier
  - 해석
  - 경고 문장 구성

즉 detector에서 HTF를 계산하지 않고,
state가 HTF를 계산해서 detector는 읽기만 하게 해야 한다.

### 원칙 2. HTF는 경고이지 방향 강제가 아니다

- `AGAINST_HTF`를 자동 SELL 차단/BUY 차단에 쓰지 않는다
- 지금 단계에선 경고와 hindsight evidence로만 쓴다

### 원칙 3. previous box는 v1에서 단순화한다

- 첫 버전은 완전한 consolidation detector가 아니라
- `shifted range + swing retest` 기반 hybrid로 시작한다

### 원칙 4. share는 마지막에 확신도 보강으로 쓴다

- share는 explanation boost 용도
- 핵심 방향 설명은 HTF와 previous box가 먼저 담당

### 원칙 5. raw context와 interpreted context를 분리한다

- raw context
  - 가능한 한 중립적인 계산 결과
  - 예: `trend_1h_direction`, `trend_1h_strength`, `previous_box_high`
- interpreted context
  - 사람이 바로 읽을 수 있는 해석 상태
  - 예: `htf_alignment_state`, `previous_box_break_state`, `context_conflict_state`

이 분리를 두는 이유는:

- detector / notifier / propose가 같은 해석 상태를 공통으로 읽게 하기 위해서
- raw 값이 왜 그런 해석으로 이어졌는지 나중에 되짚을 수 있게 하기 위해서
- downstream 레이어가 다시 제각각 해석문을 만들지 않게 하기 위해서

### 원칙 6. freshness 메타를 함께 싣는다

- HTF는 느리게 바뀌지만 stale할 수 있다
- previous box도 봉이 바뀌면 즉시 갱신될 수 있다

따라서 context state에는 값만이 아니라 다음도 같이 있어야 한다.

- `updated_at`
- `age_seconds`
- `context_state_version`
- `htf_context_version`
- `previous_box_context_version`
- `conflict_context_version`

### 원칙 7. context는 경고/evidence이지 방향 강제가 아니다

- `AGAINST_HTF`라고 해서 즉시 BUY/SELL을 막지 않는다
- `late_chase_risk_state`가 높다고 해서 바로 진입 차단으로 쓰지 않는다
- 지금 단계의 목적은 먼저 사람이 보는 좌표계를 runtime state에 올리고, detector / notifier / hindsight가 이를 읽게 만드는 것이다


## 6. state contract v1.2 설계

### 6-0. state 계산 구조

추천 파일 구조:

- `backend/services/htf_trend_cache.py`
  - HTF 데이터 fetch + cache
- `backend/services/previous_box_calculator.py`
  - previous box 계산
- `backend/services/context_state_builder.py`
  - HTF / previous box / share를 하나의 context state로 조립

이 구조의 목적은 detector가 직접 HTF나 previous box를 계산하지 않게 하는 것이다.

### 6-0-1. HTF 계산 위치

HTF는 hot path에서 매 tick마다 직접 계산하지 않는다.

권장 방식:

- MT5 snapshot 수집 흐름에 얹어서 fetch
- symbol / timeframe별 cache 적용
- cache freshness 예:
  - `1H`: 5분
  - `4H`: 15분
  - `1D`: 1시간

이유:

- 1H / 4H / 1D는 초 단위로 급격히 바뀌지 않는다
- hot path에 직접 MT5 재호출을 반복하면 실행 지연과 불안정성이 커진다
- detector / notifier가 state를 읽기만 하게 하려면 upstream에서 안정적으로 캐싱된 context를 공급하는 편이 낫다

### 6-1. HTF Context v1

raw 필드:

- `trend_15m_direction`
- `trend_1h_direction`
- `trend_4h_direction`
- `trend_1d_direction`
- `trend_15m_strength`
- `trend_1h_strength`
- `trend_4h_strength`
- `trend_1d_strength`
- `trend_15m_strength_score`
- `trend_1h_strength_score`
- `trend_4h_strength_score`
- `trend_1d_strength_score`
- `trend_15m_updated_at`
- `trend_1h_updated_at`
- `trend_4h_updated_at`
- `trend_1d_updated_at`
- `trend_15m_age_seconds`
- `trend_1h_age_seconds`
- `trend_4h_age_seconds`
- `trend_1d_age_seconds`

interpreted 필드:

- `htf_alignment_state`
  - `WITH_HTF`
  - `AGAINST_HTF`
  - `MIXED_HTF`
- `htf_alignment_detail`
  - `ALL_ALIGNED_UP`
  - `MOSTLY_ALIGNED_UP`
  - `AGAINST_HTF_UP`
  - `ALL_ALIGNED_DOWN`
  - `MIXED`
- `htf_against_severity`
  - `LOW`
  - `MEDIUM`
  - `HIGH`
- `trend_1h_quality`
- `trend_4h_quality`
- `trend_1d_quality`

v1 계산 원칙:

- EMA 기반
- `price > EMA20 > EMA50`면 상승
- `price < EMA20 < EMA50`면 하락
- 나머지는 혼조
- strength는 `EMA20-EMA50` spread를 ATR로 정규화해 `STRONG / MODERATE / WEAK / FLAT` 정도만 먼저 둔다
- quality / exhaustion은 v2로 미룬다

이유:

- 첫 버전은 계산이 단순해야 한다
- detector보다 먼저 state를 올리는 목적에 맞다
- 그러나 direction만으로는 너무 거칠기 때문에 최소한의 strength는 같은 state contract에 열어두는 편이 downstream 품질에 유리하다

`trend_*_quality` 원칙:

- v1.2에서는 필드 자리만 먼저 확보한다
- 실제 quality 계산은 direction / strength / freshness가 안정된 뒤 v2에서 본격 적용한다
- 즉 `quality`는 schema 선반영, 계산은 후반 도입 원칙으로 둔다
- 반면 `trend_*_strength_score`는 raw tuning과 hindsight 비교에 바로 유용하므로 v1.2에서 같이 저장하는 편이 좋다

### 6-2. Previous Box Context v1

raw 필드:

- `previous_box_high`
- `previous_box_low`
- `previous_box_mid`
- `previous_box_updated_at`
- `previous_box_age_seconds`
- `previous_box_mode`
  - `MECHANICAL`
  - `STRUCTURAL`
- `previous_box_confidence`
  - `LOW`
  - `MEDIUM`
  - `HIGH`
- `previous_box_lifecycle`
  - `FORMING`
  - `CONFIRMED`
  - `BROKEN`
  - `RETESTED`
  - `INVALIDATED`
- `previous_box_is_consolidation`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`

interpreted 필드:

- `previous_box_relation`
- `previous_box_break_state`

v1 계산 원칙:

- current box: 최근 N봉
- previous box: 그 이전 N봉
- swing_high/low retest count를 같이 참고
- 첫 버전은 `shifted range + swing hybrid`
- 다만 이전 구간이 실제 박스였는지 여부를 `previous_box_is_consolidation`으로 같이 싣고, 이 값이 약하면 detector가 evidence 강도를 낮게 읽게 한다
- `previous_box_lifecycle`는 box 정의가 충분히 안정되기 전까지 schema 자리만 먼저 두고, 실제 lifecycle 계산은 v1.2 후반 또는 v2에서 도입한다

`previous_box_lifecycle` 최소 규칙 예:

- `CONFIRMED`
  - `previous_box_is_consolidation = true`
  - `previous_box_confidence >= MEDIUM`
- `BROKEN`
  - `previous_box_break_state`가 `BREAKOUT_HELD` 또는 `BREAKOUT_FAILED`
- `RETESTED`
  - break 이후 현재가가 다시 박스 경계 근처로 접근
- `INVALIDATED`
  - `previous_box_confidence = LOW`
  - `previous_box_is_consolidation = false`

break state 예:

- `BREAKOUT_HELD`
- `BREAKOUT_FAILED`
- `RECLAIMED`
- `INSIDE`

### 6-3. Share Context v1

raw 필드:

- `cluster_share_global`
- `cluster_share_symbol`

interpreted 필드:

- `share_context_label_ko`
- `cluster_share_symbol_band`
  - `RARE`
  - `OCCASIONAL`
  - `COMMON`
  - `DOMINANT`

v1 원칙:

- 이미 semantic cluster에서 계산되는 share를 재사용
- 별도 복잡한 time-box share는 나중 단계로 미룸
- share는 방향 authority가 아니라 confidence booster로만 사용
- `cluster_share_symbol_band`는 notifier / detector summary에서 반복성을 짧게 설명하기 위한 interpreted 보조 필드다

### 6-4. Context Conflict / Late Chase State v1

interpreted 필드:

- `context_conflict_state`
  - `NONE`
  - `AGAINST_PREV_BOX`
  - `AGAINST_HTF`
  - `AGAINST_PREV_BOX_AND_HTF`
  - `LATE_CHASE_RISK`
  - `CONTEXT_MIXED`
- `context_conflict_intensity`
  - `LOW`
  - `MEDIUM`
  - `HIGH`
- `context_conflict_flags`
- `context_conflict_score`
- `context_conflict_label_ko`
- `late_chase_risk_state`
  - `NONE`
  - `EARLY_WARNING`
  - `HIGH`
- `late_chase_reason`
  - `EXTENDED_ABOVE_PREV_BOX`
  - `AGAINST_PULLBACK_DEPTH`
  - `HTF_ALREADY_EXTENDED`
  - `MULTI_BAR_RUN_AFTER_BREAK`
- `late_chase_confidence`
- `late_chase_trigger_count`

이 필드들은 detector가 raw HTF / previous box를 다시 조합해 충돌을 계산하게 하지 않고,
upstream state 차원에서 먼저 요약된 충돌 상태를 제공하기 위한 것이다.

### 6-4-1. context_conflict_state 우선순위 규칙

v1.2에서는 `context_conflict_state`를 단일 primary 값으로 유지한다.

우선순위:

1. `AGAINST_PREV_BOX_AND_HTF`
2. `LATE_CHASE_RISK`
3. `AGAINST_HTF`
4. `AGAINST_PREV_BOX`
5. `CONTEXT_MIXED`
6. `NONE`

운영 원칙:

- 여러 conflict가 동시에 참이어도 가장 높은 우선순위 하나만 `context_conflict_state`에 넣는다
- 복합 해석은 `context_conflict_label_ko`, `context_conflict_flags`, 또는 downstream evidence bundle에서 보강한다
- 복합 상태 배열은 v2에서 검토한다

### 6-4-2. context_conflict_intensity 원칙

`context_conflict_intensity`는 conflict 종류와 별개로, 그 충돌이 얼마나 강한지 표현하는 축이다.

예:

- `AGAINST_HTF`이지만 `htf_against_severity = LOW`면 intensity `LOW`
- `AGAINST_HTF`이고 `htf_against_severity = HIGH`면 intensity `HIGH`
- `AGAINST_PREV_BOX`인데 `previous_box_confidence = LOW`면 intensity `LOW`
- `LATE_CHASE_RISK`가 높고 다봉 연장이 크면 intensity `HIGH`

즉 downstream은 conflict 종류와 강도를 함께 읽되, 계산은 upstream state에서 끝내는 구조를 유지한다

### 6-4-3. late_chase_risk 판정 기준

초기 판정 기준 예:

- `EXTENDED_ABOVE_PREV_BOX`
  - 현재가가 `previous_box_high` 위
  - `distance_from_previous_box_high_pct > 1.5%`
- `AGAINST_PULLBACK_DEPTH`
  - 최근 pullback 깊이가 최근 impulse 대비 너무 얕음
  - 초기 기준: `pullback_ratio < 0.25`
- `HTF_ALREADY_EXTENDED`
  - HTF strength가 `STRONG`
  - 현재가가 `1H EMA20` 대비 `2 x ATR` 이상 확장
- `MULTI_BAR_RUN_AFTER_BREAK`
  - `previous_box_break_state = BREAKOUT_HELD`
  - 돌파 후 동일 방향 봉이 5개 이상 이어짐

이 기준은 운영 중 조정 가능한 초기값이며, 중요한 것은 "경고 기준이 있다"는 점이다

보조 메타:

- `late_chase_confidence`
  - 기준 충족 강도를 0~1로 정규화한 값
- `late_chase_trigger_count`
  - 동시에 충족된 late chase reason 수


## 7. downstream 연결 방식

### detector

대상 파일:

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

역할:

- state field와 interpreted context를 읽어서
  - `상위 추세 역행`
  - `직전 박스 상단 위 유지`
  - `상승 지속 누락 가능성`
  - `늦은 추격 숏 경계`
  같은 문장으로 바꾼다

권장 방식:

- detector는 계산기보다 evidence bundle reader에 가깝게 유지
- 예:
  - `htf_alignment_state`
  - `previous_box_break_state`
  - `context_conflict_state`
  - `context_conflict_flags`
  - `late_chase_risk_state`
  - `share_context_label_ko`
  를 한 묶음으로 읽고 짧은 summary를 만든다

### notifier

대상 파일:

- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

역할:

- DM을 길게 만들지 말고
- mismatch가 강할 때만 1줄 추가

예시 템플릿:

- `맥락: <HTF> | <직전박스> | <추격위험>`

예:

- `맥락: 1H/4H/1D 상승 정렬 | 직전 박스 상단 위 유지 | 늦은 역행 SELL 경계`
- `맥락: HTF 혼조 | 직전 박스 내부 복귀 | 추격 위험 낮음`

### propose / hindsight

대상 파일:

- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)

역할:

- 새 state-derived evidence를 review 후보까지 연결
- hindsight에서는 `direction wrong`만이 아니라
  - `timing_mismatch`
  - `context_conflict persisted`
  - `late_chase_risk ignored`
  같은 형태로도 분류 근거를 보강


## 8. 기대 효과

이 state-first 공사가 들어가면, 지금 사용자가 느끼는 문제:

- “계속 올라갈 것 같은데 왜 시스템은 그걸 전달 못 하지?”
- “늦은 추격인 걸 왜 더 잘 못 말하지?”
- “표식이 차트 체감보다 약하다”

를 detector만 수정하는 것보다 더 근본적으로 줄일 수 있다.

즉 이 단계는 기능 추가보다,
**시스템이 사람과 같은 큰 그림을 보게 만드는 state 확장 공사**다.


## 9. v1.2에서 의도적으로 하지 않는 것

- HTF만으로 side를 뒤집는 것
- HTF / previous box / share를 곧바로 decision core score에 합산하는 것
- time-box share 세분화
- session별 previous box 분기
- symbol별 박스 정의를 모두 다르게 가져가는 것
- notifier에 context line을 항상 노출하는 것

즉 v1.2의 목표는 어디까지나:

- 사람 좌표계를 state contract에 먼저 올리고
- detector / notifier / propose가 공통으로 읽게 만드는 것

이지, decision core를 바로 재작성하는 것이 아니다.
