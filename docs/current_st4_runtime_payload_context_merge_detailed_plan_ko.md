# ST4 Runtime Payload Context Merge 상세 계획

## 목표

`ST1 HTF state v1`, `ST2 previous box state v1`, `ST3 context_state_builder v1.2` 결과를
실제 `latest_signal_by_symbol` runtime row에 합류시켜,

- detail payload
- slim payload
- detector/notifier/propose downstream

가 같은 context contract를 읽게 만든다.


## 왜 ST4가 필요한가

지금까지는

- 계산기와 계약은 생겼지만
- 실제 runtime row에는 아직 안 실린 상태

였다.

즉 `ST1~ST3`만 끝나면 "좋은 계산기"는 생기지만,
운영 체감은 아직 거의 없다.

`ST4`는 그 계산 결과를 실제 runtime payload export 선에 태워,
이후 detector/notifier가 바로 읽을 수 있게 만드는 단계다.


## 구현 원칙

### 1. export 직전에 한 번만 enrich한다

merge 위치:

- `TradingApplication._write_runtime_status(...)`

이유:

- `latest_signal_by_symbol` export 직전이 가장 공용 지점이다
- detail/slim payload가 같은 enriched row를 같이 쓸 수 있다
- detector를 다시 계산기로 만들지 않는다

### 2. row 자체는 flat simple field 유지

이번 단계에서는 context를 nested object로 새로 묶지 않고,
기존 runtime row와 같은 flat simple field로 싣는다.

이유:

- `compact_runtime_signal_row(...)`가 simple scalar/list를 그대로 보존한다
- 현재 downstream이 flat row를 읽는 관성이 강하다
- v1에서는 운영 반영을 우선한다

### 3. broker 미지원/데이터 부족이어도 export는 깨지지 않는다

원칙:

- HTF/previous box 계산 실패 -> row 유지
- broker에 `copy_rates_from_pos`가 없으면 context enrich skip
- export 전체는 계속 진행

즉 ST4는 payload 강화이지, runtime export 실패를 만드는 단계가 아니어야 한다.


## 구현 항목

### TradingApplication 내부

- `_resolve_runtime_context_current_price(...)`
- `_extract_runtime_share_state(...)`
- `_enrich_runtime_signal_row_with_state_context(...)`
- `_enrich_runtime_signal_rows_with_state_context(...)`

### merge 지점

`_write_runtime_status(...)` 안에서:

1. `normalized_signal_rows`
2. `context_enriched_signal_rows`
3. `self.latest_signal_by_symbol = context_enriched_signal_rows`
4. detail/slim payload 모두 enriched rows 사용


## 이번 단계에서 runtime row에 추가되는 대표 필드

### HTF

- `trend_15m_direction`
- `trend_1h_direction`
- `trend_4h_direction`
- `trend_1d_direction`
- `trend_*_strength`
- `trend_*_strength_score`
- `htf_alignment_state`
- `htf_alignment_detail`
- `htf_against_severity`

### previous box

- `previous_box_high`
- `previous_box_low`
- `previous_box_mode`
- `previous_box_confidence`
- `previous_box_lifecycle`
- `previous_box_is_consolidation`
- `previous_box_relation`
- `previous_box_break_state`

### context / late chase

- `context_conflict_state`
- `context_conflict_flags`
- `context_conflict_intensity`
- `context_conflict_score`
- `context_conflict_label_ko`
- `late_chase_risk_state`
- `late_chase_reason`
- `late_chase_confidence`
- `late_chase_trigger_count`

### meta

- `context_state_version`
- `htf_context_version`
- `previous_box_context_version`
- `conflict_context_version`
- `share_context_version`
- `context_state_built_at`


## 테스트 기준

실제 `_write_runtime_status(...)` 경로를 타는 단위 테스트에서 확인:

- slim payload에 HTF field 존재
- slim payload에 previous box field 존재
- slim payload에 conflict/late chase field 존재
- detail payload에 `context_state_version`, `previous_box_context_version` 존재


## 완료 기준

- runtime status export가 state-first context를 합류한 채 기록됨
- slim/detail payload 둘 다 새 필드 보존
- 기존 runtime status 테스트 회귀 통과
- focused pytest 통과
- `py_compile` 통과
