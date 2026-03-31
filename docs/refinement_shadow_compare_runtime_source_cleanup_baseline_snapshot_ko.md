# Runtime Source Cleanup Baseline Snapshot

## 목적

runtime provenance cleanup 착수 시점의 baseline을 고정한다.

## baseline 진단

- latest live `entry_decisions.csv` rows는 `semantic_shadow_trace_quality = fallback_heavy`로 쏠려 있었다.
- same window에서 `data_completeness_ratio = 1.0`, `missing_feature_count = 0`가 많았기 때문에, 문제는 데이터 부족보다 provenance/fallback 해석 쪽에 있었다.
- detail sample에서는 final row에 `observe_confirm_v2` payload가 보이는데도 `consumer_migration_guard_v1`는 `resolved_field_name = observe_confirm_v1`, `used_compatibility_fallback_v1 = true`로 남는 케이스가 관측됐다.

## 직접 owner 후보

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)

## baseline 가설

1. `consumer_contract` resolution order 자체는 v2-first다.
2. 그런데 runtime row write path가 `prs_canonical_observe_confirm_field = observe_confirm_v1`와 `observe_confirm_v1`만 먼저 싣고 있었다.
3. 그래서 `_append_entry_decision_log()`가 `DecisionResult`를 만들 때, final row의 canonical source가 아니라 pre-normalized row source를 먼저 읽고 있었다.
4. 그 결과 trace quality가 실제 semantic 품질보다 보수적으로 `fallback_heavy`로 남았을 가능성이 컸다.

## baseline 결론

이번 cleanup의 첫 수정 대상은 compare policy가 아니라 runtime write path다.
