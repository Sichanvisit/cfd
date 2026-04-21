# ST1 HTF Cache / HTF State v1 상세 계획

## 목표

`1H / 4H / 1D`와 `15M` 추세 문맥을 detector hot path 밖에서 안정적으로 계산하고,
그 결과를 downstream이 그대로 읽을 수 있는 `HTF state v1` 계약으로 고정한다.

이번 단계의 핵심은 세 가지다.

- `htf_trend_cache.py`로 MT5/broker fetch + cache 분리
- EMA/ATR 기반 `direction / strength / strength_score` 계산
- `htf_alignment_state / htf_alignment_detail / htf_against_severity`까지 포함한 `HTF state v1` 출력


## 왜 ST1이 먼저인가

`ST0 current state audit` 결과상 context target 46개 중

- `already_computed_but_not_promoted`: 42개
- `not_computed_yet`: 4개

로, 병목은 "없어서 못 읽는 것"보다 "계산 재료가 있는데 latest state contract로 안 올라온 것"에 더 가깝다.

그중에서도 HTF는:

- 사용자 체감 문제가 가장 큼
- 기존 코드에 MT5 timeframe fetch 경로가 이미 있음
- detector/notifier/propose가 공통으로 읽을 가치가 높음

그래서 state-first 실행 순서상 `HTF cache / HTF state v1`를 가장 먼저 구현한다.


## 현재 상태

이미 확인된 기반:

- `TradingApplication.TIMEFRAMES`
  - `15M`, `1H`, `4H`, `1D` 이미 선언됨
- `copy_rates_from_pos(...)`
  - broker/MT5 fetch 경로 이미 존재
- `Mt5SnapshotService`
  - 내부 short TTL cache 패턴이 이미 존재

현재 부족한 것:

- HTF 전용 fetch/cache 서비스 분리 없음
- runtime latest state contract에 HTF raw/interpreted 값 없음
- detector/notifier가 공통으로 읽을 HTF state 계약 없음


## 이번 단계 범위

이번 `ST1`에서 구현할 것:

- `backend/services/htf_trend_cache.py`
- `15M / 1H / 4H / 1D` generic trend fetch + cache
- EMA20 / EMA50 기반 direction 계산
- ATR14 정규화 `strength_score`
- `STRONG / MODERATE / WEAK / FLAT` strength enum
- `HTF state v1` builder

이번 단계에서 하지 않을 것:

- runtime latest payload 합류
- detector/notifier/propose 직접 연결
- HTF quality 본계산
- decision core scoring 반영

즉 이번 단계는 "계산기와 계약을 만든다"까지이고,
"어디에 태워서 운영에 보이게 한다"는 `ST3~ST5` 이후 단계다.


## 구현 원칙

### 1. HTF는 hot path에서 직접 매 tick 계산하지 않는다

권장 구조:

- broker fetch
- symbol/timeframe cache
- timeframe별 TTL

기본 TTL:

- `15M`: 60초
- `1H`: 300초
- `4H`: 900초
- `1D`: 3600초

이유:

- HTF는 초 단위로 급변하지 않는다
- MT5 호출을 매 tick 반복하면 runtime이 흔들린다
- detector가 HTF를 직접 계산하면 state-first 원칙이 깨진다

### 2. raw score는 저장하고 enum은 surface한다

이번 단계에서 같이 저장하는 값:

- `trend_*_strength_score`

surface/해석용 값:

- `trend_*_strength`

이 구조를 쓰면:

- hindsight 비교
- threshold 재튜닝
- 자산별 민감도 점검

이 훨씬 쉬워진다.

### 3. quality는 필드 자리만 열고 계산은 미룬다

이번 `v1`에서는:

- `trend_*_quality = None`

만 싣고,
실제 `CLEAN / OVEREXTENDED / RANGY / REVERSAL_RISK` 계산은 후반 `v2`에서 다룬다.


## HTF trend 계산 규칙

### 입력

- `open`
- `high`
- `low`
- `close`
- `time`

### direction

- `price > EMA20 > EMA50` -> `UPTREND`
- `price < EMA20 < EMA50` -> `DOWNTREND`
- 그 외 -> `MIXED`

### strength_score

- `(EMA20 - EMA50) / ATR14`
- signed raw score로 저장

### strength enum

- `abs(score) > 2.0` -> `STRONG`
- `abs(score) > 1.0` -> `MODERATE`
- `abs(score) > 0.3` -> `WEAK`
- 그 외 -> `FLAT`

### data_state

- `READY`
- `MISSING_RATES`
- `INSUFFICIENT_BARS`
- `ATR_UNAVAILABLE`


## HTF state v1 출력 계약

### raw

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
- `trend_15m_quality`
- `trend_1h_quality`
- `trend_4h_quality`
- `trend_1d_quality`
- `trend_15m_updated_at`
- `trend_1h_updated_at`
- `trend_4h_updated_at`
- `trend_1d_updated_at`
- `trend_15m_age_seconds`
- `trend_1h_age_seconds`
- `trend_4h_age_seconds`
- `trend_1d_age_seconds`

### interpreted

- `htf_alignment_state`
  - `WITH_HTF`
  - `AGAINST_HTF`
  - `MIXED_HTF`
- `htf_alignment_detail`
  - `ALL_ALIGNED_UP`
  - `MOSTLY_ALIGNED_UP`
  - `AGAINST_HTF_UP`
  - `ALL_ALIGNED_DOWN`
  - `MOSTLY_ALIGNED_DOWN`
  - `AGAINST_HTF_DOWN`
  - `MIXED`
- `htf_against_severity`
  - `LOW`
  - `MEDIUM`
  - `HIGH`
  - `None`

### meta

- `htf_context_version`
- `htf_state_version`
- `htf_state_built_at`
- `htf_alignment_updated_at`
- `htf_alignment_age_seconds`


## alignment 규칙

기준:

- `15M`를 현재 기준축으로 본다
- `1H / 4H / 1D`를 상위 문맥으로 본다

예:

- `15M↑ + 1H↑ + 4H↑ + 1D↑` -> `WITH_HTF / ALL_ALIGNED_UP`
- `15M↓ + 1H↑ + 4H↑ + 1D↑` -> `AGAINST_HTF / AGAINST_HTF_UP`
- `15M↑ + 1H↓ + 4H↓ + 1D↓` -> `AGAINST_HTF / AGAINST_HTF_DOWN`
- 그 외 혼조 -> `MIXED_HTF / MIXED`

severity:

- 반대편 HTF 3개 + 평균 강도 높음 -> `HIGH`
- 반대편 HTF 2개 + 평균 강도 중간 이상 -> `MEDIUM`
- 그 외 반대편 HTF 존재 -> `LOW`


## 파일 구성

- `backend/services/htf_trend_cache.py`
  - fetch
  - cache
  - trend snapshot
  - HTF state v1 builder

이번 단계에서는 별도 builder 파일을 만들지 않고,
`htf_trend_cache.py` 안에 HTF 전용 계산과 state 조립을 같이 둔다.
`ST3`에서 `context_state_builder.py`가 들어오면 이 결과를 읽어서 합치는 구조로 간다.


## 테스트 원칙

단위 테스트는 fake broker 기반으로 고정한다.

검증할 것:

- cache hit / ttl expire
- uptrend / downtrend direction
- `strength_score`와 enum 계산
- `AGAINST_HTF_UP` alignment
- `MIXED_HTF` fallback
- insufficient bars fallback


## 완료 기준

- `htf_trend_cache.py`가 존재
- `15M / 1H / 4H / 1D`에 대해 fetch + cache 동작
- `direction / strength / strength_score / freshness`가 계산됨
- `build_htf_state_v1(symbol)`이 interpreted HTF state를 반환
- unit test 통과
- `py_compile` 통과
