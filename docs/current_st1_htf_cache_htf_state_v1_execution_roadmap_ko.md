# ST1 HTF Cache / HTF State v1 실행 로드맵

## 목표

`HTF cache + HTF state v1`를 구현해서,
다음 단계의 `context_state_builder`와 `runtime payload 합류`가 바로 읽을 수 있는 기반을 만든다.


## ST1-1. 계약 확정

할 일:

- HTF raw 필드 확정
- interpreted HTF 필드 확정
- freshness/meta 필드 확정
- `quality`는 자리만 열고 계산 보류 원칙 확정

완료 기준:

- 문서상 `HTF state v1` 필드 계약이 고정됨


## ST1-2. htf_trend_cache.py 구현

할 일:

- broker `copy_rates_from_pos(...)` fetch
- timeframe별 TTL cache
- EMA20/EMA50 direction 계산
- ATR14 기반 `strength_score`
- enum `strength`
- `compute_htf_trend_snapshot(...)`
- `get_trend(...)`
- `get_all_trends(...)`
- `build_htf_state_v1(...)`

완료 기준:

- symbol/timeframe 기준 cache hit이 동작
- 15M/1H/4H/1D 추세 snapshot 계산 가능


## ST1-3. alignment / severity 구현

할 일:

- `WITH_HTF / AGAINST_HTF / MIXED_HTF`
- `ALL_ALIGNED_UP / AGAINST_HTF_UP ...`
- `LOW / MEDIUM / HIGH` severity

완료 기준:

- `build_htf_state_v1(symbol)`이 interpreted HTF state까지 반환


## ST1-4. 테스트

할 일:

- fake broker 기반 unit test
- cache TTL 검증
- direction 검증
- `AGAINST_HTF_UP` 검증
- `MIXED_HTF` 검증
- insufficient bars fallback 검증

완료 기준:

- focused pytest 통과
- `py_compile` 통과


## ST1 이후 연결

다음 단계:

1. `ST2 previous_box_calculator.py`
2. `ST3 context_state_builder.py`
3. `ST4 runtime payload 합류`

즉 `ST1`은 standalone 완료가 가능하지만,
실제 runtime latest state에 보이게 하는 건 `ST4`에서 닫는다.


## 현재 상태

- `ST0`: 완료
- `ST1`: 이번 단계에서 구현
- `ST2+`: 대기
