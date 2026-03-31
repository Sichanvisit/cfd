# Shadow Compare Trace Quality Audit Implementation Checklist

## 1. 범위

이 체크리스트는 [refinement_shadow_compare_trace_quality_audit_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_audit_spec_ko.md) 구현 순서를 고정한다.

## 2. 구현 순서

### Step 1. Trace Quality Baseline Snapshot 고정

목표:

- latest live 기준 trace quality 분포를 문서로 고정한다.

해야 할 일:

- latest shadow compare report에서 `trace_quality_counts`를 기록한다.
- latest live entry rows에서 `compatibility_mode`, `used_fallback_count`, `data_completeness_ratio`, `missing_feature_count` 분포를 기록한다.
- 심볼별 분포도 같이 남긴다.

완료 기준:

- baseline snapshot memo가 있다.

### Step 2. Source Contract Audit

목표:

- `used_fallback_count`와 `compatibility_mode`가 어떤 source field에서 만들어지는지 고정한다.

해야 할 일:

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py) 에서 runtime shadow feature row 생성 경로를 확인한다.
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py) 의 `summarize_trace_quality()` fold 규칙을 정리한다.
- `consumer_input_observe_confirm_field`, `consumer_used_compatibility_fallback_v1`, `energy_migration_guard_v1.*`가 각각 어떤 fallback source인지 분리한다.

완료 기준:

- source contract casebook이 있다.

### Step 3. Compare Reporting Owner Audit

목표:

- compare layer가 trace quality를 다시 계산하지 않고 source scalar를 집계만 하는지 확인한다.

해야 할 일:

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py) 의 trace quality 집계 경로를 점검한다.
- 필요 시 report summary에 source interpretation용 필드를 추가한다.

완료 기준:

- compare owner 범위가 문서로 분리된다.

### Step 4. 테스트 / 회귀 확인

목표:

- trace quality audit 과정에서 owner 해석이 흔들리지 않게 한다.

해야 할 일:

- 관련 테스트를 보강하거나 재실행한다.
- 필요한 경우 trace quality source fold 테스트를 추가한다.

완료 기준:

- 관련 테스트가 통과한다.

### Step 5. 결과 memo와 다음 active step 고정

목표:

- 이번 단계 결과를 memo로 닫고 다음 active step을 고정한다.

해야 할 일:

- baseline snapshot memo 작성
- source contract casebook 작성
- 필요한 경우 master plan에 현재 상태를 반영

완료 기준:

- 문서만 봐도 다음이 `S3 compare policy refinement`인지, `runtime source cleanup`인지 판단 가능하다.

## 3. Done Definition

아래를 만족하면 `S2`는 닫는다.

- trace quality baseline snapshot memo가 있다.
- source contract casebook이 있다.
- compare reporting owner가 정리돼 있다.
- `fallback_heavy only` 상태의 직접 이유를 문장으로 설명할 수 있다.

현재 상태:

- `Step 1. Trace Quality Baseline Snapshot` 완료
  - [refinement_shadow_compare_trace_quality_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_baseline_snapshot_ko.md)
- `Step 2. Source Contract Audit` 완료
  - [refinement_shadow_compare_trace_quality_source_contract_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_source_contract_casebook_ko.md)
- `Step 3. Compare Reporting Owner Audit` 완료
  - [refinement_shadow_compare_trace_quality_compare_owner_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_compare_owner_audit_ko.md)

현재 active step:

- `Step 5. 결과 memo와 다음 active step 고정` 완료
  - [refinement_shadow_compare_trace_quality_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_trace_quality_reconfirm_memo_ko.md)
