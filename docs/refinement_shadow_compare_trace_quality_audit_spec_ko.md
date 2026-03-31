# Shadow Compare Trace Quality Audit Spec

## 1. 목적

이 문서는 shadow compare 품질개선 트랙의 `S2 trace quality audit` 범위를 고정한다.

현재 상태에서는 source freshness와 replay join mismatch는 해소되었지만, 최신 shadow compare report가 여전히 전부 `fallback_heavy`로 집계된다.

기준 산출물:

- [semantic_shadow_compare_report_20260326_190949.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_190949.json)
- [semantic_preview_audit_20260326_191035.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_191035.json)
- [shadow_compare_production_source_manifest_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\shadow_compare_production_source_manifest_latest.json)

## 2. 현재 증상

latest live 기준에서:

- `matched_replay_rows = 24732`
- `missing_replay_join_rows = 0`
- `scorable_shadow_rows = 22582`
- `trace_quality_counts = {"fallback_heavy": 24732}`

즉 replay freshness와 label coverage는 충분히 확보됐지만, trace quality는 전부 fallback-heavy로 남아 있다.

추가 live row audit 기준:

- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) 전체 `semantic_shadow_trace_quality = fallback_heavy`
- 전체 `compatibility_mode = observe_confirm_v1_fallback`
- 전체 `semantic_shadow_available = 1`
- 전체 `semantic_shadow_should_enter = 1`
- `data_completeness_ratio`는 대부분 `1.0`
- `missing_feature_count`는 대부분 `0`
- `used_fallback_count`는 대부분 `2`

따라서 현재 문제는 "데이터가 비어서 fallback-heavy"가 아니라 "compatibility fallback 경로로 꽉 채워진 row가 live source로 기록된다" 쪽에 가깝다.

## 3. 이번 단계의 질문

이번 audit은 아래 질문에 답해야 한다.

1. `semantic_shadow_trace_quality`는 어디서 결정되는가?
2. `fallback_heavy`는 compare layer의 집계 결과인가, runtime row source 자체의 결과인가?
3. `observe_confirm_v1_fallback`은 어떤 조건에서 생성되는가?
4. `used_fallback_count = 2`는 어떤 fallback source 두 개를 의미하는가?
5. 이 상태가 임시 호환 경로의 정상 동작인지, 아직 정리되지 않은 technical debt인지 구분 가능한가?

## 4. owner 범위

직접 owner:

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

참고 owner:

- [export_entry_decisions_ml.py](c:\Users\bhs33\Desktop\project\cfd\scripts\export_entry_decisions_ml.py)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)

## 5. audit 축

### 5-1. source contract audit

다음을 확인한다.

- `consumer_input_observe_confirm_field`
- `consumer_used_compatibility_fallback_v1`
- `energy_migration_guard_v1.used_compatibility_bridge`
- `energy_migration_guard_v1.compatibility_bridge_rebuild_active`

이 값이 `used_fallback_count`와 `compatibility_mode`에 어떻게 접히는지 본다.

### 5-2. runtime trace audit

다음을 확인한다.

- `semantic_shadow_trace_quality`
- `semantic_shadow_reason`
- `data_completeness_ratio`
- `missing_feature_count`
- `used_fallback_count`
- `compatibility_mode`

즉 "quality degradation"와 "compatibility fallback"를 구분해서 본다.

### 5-3. compare reporting audit

다음을 확인한다.

- `shadow_compare.py`는 trace quality를 재판정하지 않고 source scalar를 그대로 읽는지
- `trace_quality_counts`가 source 문제를 충실히 surface 하는지

## 6. 이번 단계에서 하지 않을 것

- timing / entry_quality / exit_management target 재정의
- split health 재조정
- compare threshold 자체 변경
- bounded live rollout 조정

이번 단계는 trace quality source contract를 설명 가능하게 만드는 데에만 집중한다.

## 7. 완료 기준

아래를 만족하면 `S2 trace quality audit`는 닫는다.

- `fallback_heavy only`의 직접 원인을 row/source contract 기준으로 설명할 수 있다.
- `used_fallback_count`를 구성하는 fallback source가 문서로 분리돼 있다.
- `compatibility_mode = observe_confirm_v1_fallback`이 어떤 경로에서 발생하는지 코드와 문서로 함께 설명 가능하다.
- 다음 단계가 `S3 compare policy refinement`인지, 아니면 먼저 runtime source 정리인지 문서만 보고 판단 가능하다.

## 8. 다음 액션

이 spec 기준 다음 액션은 아래 순서다.

1. trace quality baseline snapshot memo 작성
2. source contract casebook 작성
3. 필요 시 runtime trace summary surface 보강
4. compare policy refinement으로 넘어갈지 결정
