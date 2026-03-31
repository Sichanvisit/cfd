# Shadow Compare Runtime Source Cleanup Spec

## 1. 목적

이 문서는 shadow compare 품질개선 트랙에서 `runtime source cleanup / compatibility contract audit` 범위를 고정한다.

현재 상태에서는:

- replay source freshness는 해결됐다.
- replay join alignment는 해결됐다.
- scoreable transition coverage도 확보됐다.
- 그런데 latest live rows는 여전히 `compatibility_mode = observe_confirm_v1_fallback`로 기록되고 있다.

즉 compare policy를 더 만지기 전에, runtime source provenance가 실제 current contract를 반영하는지 먼저 점검할 필요가 있다.

기준 문서:

- [refinement_shadow_compare_trace_quality_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_reconfirm_memo_ko.md)
- [refinement_shadow_compare_runtime_source_cleanup_candidate_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_runtime_source_cleanup_candidate_memo_ko.md)

## 2. 현재 의심 지점

latest detail sample 기준으로:

- final payload에는 `observe_confirm_v2`가 존재한다.
- 동시에 `consumer_migration_guard_v1`는
  - `canonical_payload_present = false`
  - `resolved_field_name = observe_confirm_v1`
  - `used_compatibility_fallback_v1 = true`

로 남아 있다.

즉 최종 row에 남는 payload와 guard가 계산한 source가 서로 다를 수 있다.

## 3. 이번 단계의 핵심 질문

1. consumer resolution은 실제로 어느 시점의 `observe_confirm_v2`를 보고 있는가?
2. final payload의 `observe_confirm_v2`는 canonical input인가, later-stage mirrored payload인가?
3. `consumer_migration_guard_v1`는 final row provenance를 정확히 반영하는가?
4. 현재 `observe_confirm_v1_fallback`은 의도된 conservative runtime contract인가, 아니면 정리되지 않은 migration debt인가?

## 4. 직접 owner

- [consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)
- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

보조 owner:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl)

## 5. audit 축

### 5-1. consumer resolution audit

다음을 확인한다.

- `resolve_consumer_observe_confirm_resolution()`
- `build_consumer_migration_guard_metadata()`
- `observe_confirm_v2 / observe_confirm_v1` local source
- canonical candidate resolution order

### 5-2. timing / write-order audit

다음을 확인한다.

- guard metadata가 계산되는 시점
- final payload가 직렬화되는 시점
- `observe_confirm_v2`가 나중에 채워지는지 여부

### 5-3. provenance surface audit

다음을 확인한다.

- slim row
- detail sidecar
- replay intermediate

중 어디까지 source provenance를 유지하는지

## 6. 이번 단계에서 하지 않을 것

- timing / entry_quality / exit_management target 재정의
- compare threshold 변경
- promotion gate 변경
- bounded live rollout 변경

이번 단계는 source provenance를 설명 가능하게 만드는 데에만 집중한다.

## 7. 완료 기준

아래를 만족하면 `runtime source cleanup` 단계는 닫는다.

- `observe_confirm_v1_fallback`의 실제 owner와 발생 시점이 설명 가능하다.
- final payload와 migration guard가 왜 어긋나는지, 혹은 실제로 안 어긋나는지 문서로 설명 가능하다.
- 다음 액션이
  - `source provenance fix`
  - 또는 `S3 compare policy refinement`
  중 어느 쪽인지 문서만 보고 판단 가능하다.

## 8. 다음 액션

이 spec 기준 다음 액션은 아래 순서다.

1. runtime source baseline snapshot
2. consumer resolution casebook
3. timing / write-order casebook
4. provenance surface memo
5. next-step decision memo
