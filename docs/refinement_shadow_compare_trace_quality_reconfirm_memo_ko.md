# Shadow Compare Trace Quality Reconfirm Memo

## 1. 이번 단계에서 확인된 것

`S2 trace quality audit` 결과, 현재 `fallback_heavy only`의 직접 원인은 compare layer가 아니라 runtime source contract 쪽으로 좁혀졌다.

핵심 근거:

- [semantic_shadow_compare_report_20260326_190949.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_190949.json)
  - `trace_quality_counts = {"fallback_heavy": 24732}`
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
  - `compatibility_mode = observe_confirm_v1_fallback`
  - `used_fallback_count` 대부분 `2`
  - `data_completeness_ratio` 대부분 `1.0`
  - `missing_feature_count` 대부분 `0`
- [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl) latest sample
  - `consumer_input_observe_confirm_field = observe_confirm_v1`
  - `consumer_used_compatibility_fallback_v1 = True`
  - `energy_migration_guard_v1.used_compatibility_bridge = false`

즉 latest sample 기준 `used_fallback_count = 2`는:

1. `observe_confirm_v1` consumer input
2. `consumer compatibility fallback flag`

로 설명된다.

## 2. 이번 단계에서 해결된 것

- replay source freshness: 해결
- replay join alignment: 해결
- scoreable transition coverage: 해결
- trace quality owner separation: 설명 가능

## 3. 아직 남은 것

남은 핵심 질문은 이것이다.

- 지금 `observe_confirm_v1_fallback`이 의도된 임시 conservative runtime contract인가?
- 아니면 compare policy보다 먼저 정리해야 하는 migration debt인가?

## 4. 다음 active step

현재 기준 다음 active step은 두 갈래 중 하나다.

1. `runtime source cleanup / compatibility contract audit`
2. `S3 compare policy refinement`

이번 S2 결과만 놓고 보면 1번을 먼저 한 번 더 보는 편이 더 안전하다.
