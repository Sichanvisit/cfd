# State / Forecast Validation SF3 Forecast Harvest Usage Audit Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 목적

SF3는 `state / belief / barrier / secondary harvest가 실제로 row에 존재하는가`가 아니라,
`forecast branch math가 그 harvest를 실제로 직접 사용하는가`를 확인하는 단계다.

이번 단계의 핵심 질문은 아래였다.

- `transition_forecast_v1`, `trade_management_forecast_v1`에 usage trace가 실제로 저장되는가
- branch별로 어떤 harvest section이 직접 수학에 올라가는가
- `secondary_harvest`는 실제 direct-use까지 올라오는가, 아니면 harvest-only 상태인가
- SF4에서 value/slice audit로 넘어가도 되는가

## 2. 구현 파일

- script:
  - [state_forecast_validation_forecast_harvest_usage_audit.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_forecast_harvest_usage_audit.py)
- test:
  - [test_state_forecast_validation_forecast_harvest_usage_audit.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_forecast_harvest_usage_audit.py)

## 3. 샘플링 방식

이번 SF3도 SF1/SF2와 같은 bounded head-sample 전략을 유지했다.

- source: `entry_decisions*.detail.jsonl`
- strategy: `detail_jsonl_per_file_head_sample`
- sampled source count: `87`
- sampled rows per file: `40`
- total sampled rows: `3480`

즉 giant history 전체를 풀스캔하기보다, active / legacy / rotated detail source 전반에서 usage trace persistence와 branch별 harvest usage 차이를 먼저 측정했다.

## 4. 생성 산출물

- [state_forecast_validation_sf3_usage_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf3_usage_latest.json)
- [state_forecast_validation_sf3_usage_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf3_usage_latest.csv)
- [state_forecast_validation_sf3_usage_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf3_usage_latest.md)

## 5. 핵심 결과

latest 기준:

- `transition_forecast_present_ratio = 0.9945`
- `trade_management_forecast_present_ratio = 0.9945`
- `transition_usage_trace_present_ratio = 0.9945`
- `trade_management_usage_trace_present_ratio = 0.9945`
- `gap_metrics_present_ratio = 1.0`
- `gap_metrics_usage_trace_present_ratio = 0.0`
- `transition_direct_math_field_unique_count = 12`
- `trade_management_direct_math_field_unique_count = 10`
- `secondary_harvest_direct_use_field_count = 0`

즉 이번 SF3의 1차 결론은 아래 한 줄로 요약된다.

`transition / trade_management branch usage trace는 historical row에 거의 항상 남지만, secondary_harvest는 실제 branch math direct-use까지는 전혀 올라가지 않는다.`

## 6. branch trace persistence

현재 sampled history에서 usage trace persistence는 충분히 높다.

- `transition_branch_trace_working = true`
- `trade_management_branch_trace_working = true`
- `usage_state = usage_trace_present`

즉 SF4 이후 value audit을 진행해도 `usage trace가 안 남아서 무엇을 쓰는지 모르겠다`는 문제는 크지 않다.

다만 `forecast_gap_metrics_v1`는 payload는 row에 존재하지만, persisted usage trace는 이번 샘플에서 관측되지 않았다.
즉 gap metrics는 현재 historical row에서 `direct harvest usage audit`의 주체라기보다 `branch output derived layer`로 보는 해석이 맞다.

## 7. branch별 직접 사용 범위

### transition branch

- `state_harvest`: `6 / 10` fields direct-use
- `belief_harvest`: `2 / 6` fields direct-use
- `barrier_harvest`: `4 / 7` fields direct-use
- `secondary_harvest`: `0 / 11` fields direct-use

transition은 상대적으로 넓은 state/barrier harvest를 직접 사용하는 구조다.
즉 현재 의미는 `시장 구조/장벽/방향성 상태`를 활용해서 transition score를 세분화하고 있다는 쪽에 가깝다.

### trade_management branch

- `state_harvest`: `1 / 10` fields direct-use
- `belief_harvest`: `6 / 6` fields direct-use
- `barrier_harvest`: `3 / 7` fields direct-use
- `secondary_harvest`: `0 / 11` fields direct-use

management는 state_harvest를 넓게 쓰지 않고, belief harvest를 중심으로 direct math를 구성하고 있다.
즉 현재 구조는 `관리/홀드/재진입 판단`에서 state보다는 belief persistence/flip/readiness에 더 무게를 두는 쪽으로 읽을 수 있다.

## 8. 가장 중요한 gap

이번 SF3에서 가장 중요한 gap은 아래 두 가지였다.

### 8-1. secondary harvest direct-use gap

- `secondary_harvest_direct_use_field_count = 0`

즉 현재 아래 항목들은 forecast feature bundle에 실리고는 있지만,
transition / management branch 수학에는 직접 올라가지 않는다.

- `advanced_input_activation_state`
- `tick_flow_state`
- `order_book_state`
- `source_current_rsi`
- `source_current_adx`
- `source_current_plus_di`
- `source_current_minus_di`
- `source_recent_range_mean`
- `source_recent_body_mean`
- `source_sr_level_rank`
- `source_sr_touch_count`

이건 바로 “쓸모가 없다”는 뜻은 아니다.
다만 현재 단계에서 정확한 해석은 아래다.

`secondary_harvest는 coverage와 activation은 어느 정도 살아 있어도, forecast branch direct math에는 아직 연결되지 않는다.`

### 8-2. management state_harvest narrow usage

- `trade_management_branch state_harvest direct-use = 1 / 10`

즉 management branch는 execution friction 쪽만 state direct-use로 읽고,
session / expansion / topdown / event risk 같은 state는 현재 direct-use 범위에 거의 없다.

이건 나중에 SF4/SF5에서 value audit 결과를 보고,
management 쪽에 더 많은 state bridge를 넣을지 검토할 근거가 된다.

## 9. SF2와 연결해서 읽으면

SF2에서는 아래가 확인됐다.

- `tick_history` active-like ratio는 높다
- `event_risk` active-like ratio도 높다
- `order_book`만 availability gap이 매우 크다

SF3까지 합치면 해석은 더 명확해진다.

1. `tick_history`, `event_risk`는 collector activation 차원에서는 살아 있다
2. 하지만 그 정보가 `secondary_harvest`로만 남고 direct branch math에는 아직 안 올라간다
3. 따라서 다음 질문은 `raw/collector를 더 넣을까`가 아니라 `이 active secondary signal들이 실제 예측 가치가 있나`가 된다

즉 SF4는 자연스럽게 `active하지만 direct-use는 안 되는 input이 정말 가치가 있는지`를 보는 단계가 된다.

## 10. 이번 SF3의 결론

이번 SF3의 핵심 결론은 아래와 같다.

1. usage trace persistence는 충분히 높다
2. transition은 state/barrier를 넓게 쓰고, management는 belief 중심으로 더 좁게 쓴다
3. `secondary_harvest`는 현재 branch direct math에 전혀 연결되지 않는다
4. 따라서 다음 단계는 `무엇이 실제로 예측 가치가 있는지`를 보는 `SF4 forecast feature value / slice audit`이 맞다

## 11. 검증

실행 결과:

- SF3 전용 테스트: `2 passed`
- SF0~SF3 + state/forecast validation 및 contract 묶음: `60 passed`
- 전체 unit: `1168 passed, 127 warnings`

## 12. 다음 단계

SF3 이후 active step은 `SF4 forecast feature value / slice audit`이다.

SF4에서 먼저 확인해야 할 질문은 아래다.

1. transition이 넓게 쓰는 `state/barrier harvest`가 실제 metric에 기여하는가
2. management에서 belief 중심 direct-use가 실제로 유의미한가
3. `secondary_harvest`를 direct-use로 올릴 가치가 있는가, 아니면 bridge 요약 후보로만 남겨야 하는가
4. `tick_history`, `event_risk`처럼 activation은 살아 있는 input이 value audit에서도 살아남는가

최종 요약:

`SF3는 usage trace가 historical row에 충분히 남는다는 점과, 현재 forecast branch가 secondary_harvest를 직접 쓰지 않는다는 점을 숫자로 고정한 단계다.`
