# Shadow Compare Trace Quality Baseline Snapshot

## 1. 목적

이 문서는 `S2 trace quality audit`의 baseline snapshot을 고정한다.

기준 산출물:

- [semantic_shadow_compare_report_20260326_190949.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_190949.json)
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)

## 2. latest compare 기준

latest compare summary:

- `rows_total = 24732`
- `matched_replay_rows = 24732`
- `missing_replay_join_rows = 0`
- `scorable_shadow_rows = 22582`
- `unscorable_shadow_rows = 2150`
- `trace_quality_counts = {"fallback_heavy": 24732}`

즉 join / source freshness / future-bar coverage는 충분하지만 trace quality는 전부 fallback-heavy다.

## 3. live entry row 기준

latest live [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) audit 결과:

- 전체 `semantic_shadow_trace_quality = fallback_heavy`
- 전체 `compatibility_mode = observe_confirm_v1_fallback`
- 전체 `semantic_shadow_available = 1`
- 전체 `semantic_shadow_should_enter = 1`
- `data_completeness_ratio`
  - min `0.0`
  - p50 `1.0`
  - p90 `1.0`
  - max `1.0`
- `missing_feature_count`
  - p50 `0`
  - p90 `0`
- `used_fallback_count`
  - min `1`
  - p50 `2`
  - p90 `2`
  - max `2`

대표 combo:

- `compatibility_mode = observe_confirm_v1_fallback`
- `used_fallback_count = 2`
- `semantic_shadow_trace_quality = fallback_heavy`

이 combo가 거의 전부를 차지한다.

## 4. 심볼별 요약

### BTCUSD

- 대부분 `observe_confirm_v1_fallback + used_fallback_count=2 + fallback_heavy`

### NAS100

- 대부분 `observe_confirm_v1_fallback + used_fallback_count=2 + fallback_heavy`

### XAUUSD

- 전부 `observe_confirm_v1_fallback + used_fallback_count=2 + fallback_heavy`

즉 현재 현상은 특정 심볼 한쪽 문제가 아니라 live source contract 전체 문제다.

## 5. 1차 해석

현재 상태는 "feature가 비어서 degraded/fallback-heavy"가 아니다.

오히려:

- `data_completeness_ratio`는 높고
- `missing_feature_count`는 낮고
- `compatibility_mode`는 명시적으로 `observe_confirm_v1_fallback`
- `used_fallback_count`는 대부분 `2`

이므로, 최신 shadow input이 compatibility fallback 경로를 기본 source로 사용하고 있다고 해석하는 편이 맞다.

즉 `fallback_heavy only`는 compare 집계 이상이라기보다 runtime source contract의 결과일 가능성이 높다.

## 6. 다음 질문

다음 단계에서 답해야 하는 질문은 아래와 같다.

1. `observe_confirm_v1_fallback`는 정확히 어떤 source owner에서 만들어지는가?
2. `used_fallback_count = 2`의 두 source는 무엇인가?
3. 이 상태가 일시적 migration bridge인지, 아직 정리되지 않은 기본 경로인지?
4. 이 상태에서 compare policy refinement로 바로 가도 되는지, 아니면 source cleanup이 먼저인지?
