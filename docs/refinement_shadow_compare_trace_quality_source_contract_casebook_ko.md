# Shadow Compare Trace Quality Source Contract Casebook

## 1. 목적

이 문서는 `S2 trace quality audit`에서 확인한 source contract를 casebook 형태로 고정한다.

기준 파일:

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl)

## 2. trace quality 결정 owner

최종 `semantic_shadow_trace_quality` 해석 owner는 [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)의 `resolve_trace_quality_state()` 이다.

하지만 이 함수는 아래 slim scalar만 읽는다.

- `data_completeness_ratio`
- `missing_feature_count`
- `used_fallback_count`
- `compatibility_mode`

즉 trace quality의 실질 source owner는 이 scalar를 먼저 만드는 [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)의 `summarize_trace_quality()` 쪽이다.

## 3. summarize_trace_quality fold 규칙

[storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py) 기준 fold 규칙은 아래와 같다.

### 3-1. completeness

- `ENTRY_TRACE_REQUIRED_FIELDS` 중 payload present 개수를 센다.
- `missing_feature_count`
- `data_completeness_ratio`

를 만든다.

### 3-2. fallback count

`used_fallback_count`는 아래 source로 구성된다.

1. `consumer_input_observe_confirm_field == "observe_confirm_v1"`
2. `consumer_used_compatibility_fallback_v1 == true`
3. `energy_migration_guard_v1.used_compatibility_bridge == true`
4. `energy_migration_guard_v1.compatibility_bridge_rebuild_active == true`

현재 코드는 3번과 4번을 한 묶음으로 친다.

### 3-3. compatibility_mode

`compatibility_mode`는 아래 우선순위다.

1. `consumer_input_observe_confirm_field == "observe_confirm_v1"` 이면 무조건 `observe_confirm_v1_fallback`
2. 그 외 fallback count가 1개 이상이면 `hybrid`
3. 아니면 `native_v2`

즉 `compatibility_mode = observe_confirm_v1_fallback`은 단순 경고가 아니라, consumer input source 자체가 아직 v1 compatibility payload라는 뜻이다.

## 4. latest slim row에서 보이는 것

latest live [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) 기준으로 직접 확인되는 건 아래까지다.

- `consumer_input_observe_confirm_field = observe_confirm_v1`
- `compatibility_mode = observe_confirm_v1_fallback`
- `used_fallback_count = 2`

하지만 slim row에는 아래 두 값이 남지 않는다.

- `consumer_used_compatibility_fallback_v1`
- `energy_migration_guard_v1`

즉 hot CSV만으로는 `used_fallback_count = 2`의 정확한 구성요소를 완전히 복원할 수 없다.

## 5. latest detail sidecar에서 보이는 것

latest [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl) tail sample 기준으로는 아래가 확인된다.

- `consumer_input_observe_confirm_field = observe_confirm_v1`
- `consumer_used_compatibility_fallback_v1 = True`
- `prs_compatibility_observe_confirm_field = observe_confirm_v1`
- `energy_migration_guard_v1.used_compatibility_bridge = false`
- `energy_migration_guard_v1.compatibility_bridge_rebuild_active = false`

즉 latest sample 기준 `used_fallback_count = 2`는 아래 두 source로 설명된다.

1. consumer input source가 `observe_confirm_v1`
2. consumer compatibility fallback flag가 `true`

현재 latest sample 기준으로는 energy bridge는 active source가 아니다.

## 6. 현재 해석

현재 `fallback_heavy only` 상태는 아래처럼 읽는 것이 가장 맞다.

- feature missing 문제: 아님
- completeness 저하 문제: 아님
- compare 집계 문제: 아님
- consumer observe-confirm source가 아직 `observe_confirm_v1` compatibility branch에 머물러 있는 상태: 맞음

즉 현재 trace quality warning은 data loss warning보다 migration/compatibility path warning에 가깝다.

## 7. 다음 결정 포인트

이 casebook 기준 다음 질문은 아래 둘 중 하나다.

1. 지금 상태가 의도된 conservative runtime source라면
   - compare policy refinement으로 넘어간다.
2. 지금 상태가 정리되지 않은 migration debt라면
   - runtime source cleanup이 compare policy보다 먼저다.

현재 문서 기준으로는 2번 가능성을 먼저 점검하는 게 더 안전하다.
