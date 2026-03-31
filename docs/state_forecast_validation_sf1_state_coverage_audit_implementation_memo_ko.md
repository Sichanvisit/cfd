# State / Forecast Validation SF1 State Coverage Audit Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 목적

SF1은 `state / forecast` surface가 historical row에서 실제로 얼마나 살아 있는지 확인하는 단계다.

이번 구현의 목적은 아래를 분리하는 것이다.

- `field가 아예 sparse 한가`
- `field는 row에 거의 항상 있지만 default-heavy 인가`
- `field는 present 하고 meaningful 비율도 충분한가`

즉 SF1은 raw 추가 여부를 결정하는 단계가 아니라,
`지금 있는 state / harvest surface가 coverage 관점에서 건강한지`를 먼저 확인하는 단계다.

## 2. 구현 파일

- script:
  - [state_forecast_validation_state_coverage_audit.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_state_coverage_audit.py)
- test:
  - [test_state_forecast_validation_state_coverage_audit.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_state_coverage_audit.py)

## 3. 샘플링 방식

이번 SF1은 아래 방식으로 bounded audit를 수행한다.

- source: `entry_decisions*.detail.jsonl`
- strategy: `detail_jsonl_per_file_head_sample`
- sampled source count: `85`
- sampled rows per file: `40`
- total sampled rows: `3400`

즉 전체 gigantic history를 전부 다 도는 대신,
모든 historical detail source에서 소량씩 고르게 읽어 coverage/default-heavy 여부를 먼저 확인하는 방식이다.

## 4. 생성 산출물

- [state_forecast_validation_sf1_coverage_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf1_coverage_latest.json)
- [state_forecast_validation_sf1_coverage_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf1_coverage_latest.csv)
- [state_forecast_validation_sf1_coverage_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf1_coverage_latest.md)

## 5. 이번 SF1에서 본 핵심 결과

latest 기준:

- `position_snapshot_present_ratio = 0.9944`
- `state_vector_present_ratio = 0.9944`
- `forecast_features_present_ratio = 0.9944`
- `semantic_forecast_inputs_present_ratio = 0.9944`
- `state_harvest_present_ratio = 0.9944`
- `secondary_harvest_present_ratio = 0.9944`
- `sparse_field_count = 0`
- `default_heavy_field_count = 5`
- `light_signal_field_count = 2`

즉 이번 SF1의 1차 결론은 이렇다.

`state / harvest surface는 sparse 해서 비는 문제가 아니라, 대부분 row에 존재한다.`

즉 현재 문제는 `surface missing`보다 `specific field default-heavy / activation weakness` 쪽으로 읽는 게 맞다.

## 6. suspicious field 후보

이번 SF1에서 바로 눈에 띈 후보는 아래다.

### default-heavy

- `secondary_harvest.order_book_state`
- `state_vector_v2.metadata.order_book_state`
- `secondary_harvest.source_sr_touch_count`
- `state_vector_v2.metadata.source_sr_touch_count`
- `state_vector_v2.liquidity_penalty`

### light-signal

- `position_snapshot_v2.energy.middle_neutrality`
- `state_vector_v2.countertrend_penalty`

## 7. 해석

이번 결과를 기준으로 보면:

- `state raw / state vector / harvest`가 아예 row에 안 남는 문제는 아니다
- `advanced input activation` 중 특히 `order_book` 쪽은 present surface 대비 실제 meaningful activation이 매우 약하다
- 일부 state scalar는 row엔 남지만 실제 non-default signal 빈도가 낮다

즉 다음 active question은 자연스럽게 아래로 이어진다.

- order_book / advanced input이 실제로 얼마나 켜지는가
- activation state가 심볼/시간대별로 어떤 분포인가
- default-heavy field가 진짜 useless인지, 특정 slice에서만 살아 있는지

## 8. 검증

실행 결과:

- SF1 전용 테스트: `2 passed`
- 관련 state/forecast 축 테스트: `65 passed`
- 전체 unit: `1166 passed, 127 warnings`

## 9. 다음 단계

SF1 다음 active step은 `SF2 advanced input activation audit`이다.

이번 SF1 기준으로 다음에 먼저 봐야 하는 포인트는:

1. `advanced_input_activation_state` 분포
2. `tick_history / order_book / event_risk` collector별 activation 분포
3. symbol/timeframe/regime별 activation 차이
4. `order_book_state`가 왜 거의 항상 default-heavy 인지

한 줄 요약:

`SF1은 state surface가 historical row에 거의 다 살아 있음을 확인했고, 이제 SF2에서 advanced input activation weakness를 직접 측정할 차례다.`
