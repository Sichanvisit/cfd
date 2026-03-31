# Shadow Compare Runtime Source Cleanup Implementation Checklist

## 1. 범위

이 체크리스트는 [refinement_shadow_compare_runtime_source_cleanup_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_runtime_source_cleanup_spec_ko.md) 구현 순서를 고정한다.

## 2. 구현 순서

### Step 1. Runtime Source Baseline Snapshot 고정

목표:

- latest detail sample 기준 source provenance baseline을 문서로 고정한다.

해야 할 일:

- latest detail row에서 `observe_confirm_v2`, `observe_confirm_v1`, `consumer_migration_guard_v1`를 같이 기록한다.
- latest slim row에서 `compatibility_mode`, `used_fallback_count`, `consumer_input_observe_confirm_field`를 같이 기록한다.

완료 기준:

- baseline snapshot memo가 있다.

### Step 2. Consumer Resolution Casebook

목표:

- canonical/compatibility resolution order와 실제 resolved field를 설명 가능하게 만든다.

해야 할 일:

- [consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py) 의 resolution order를 정리한다.
- `canonical_payload_present`, `compatibility_payload_present`, `used_fallback_v1`, `resolved_field_name` 해석표를 만든다.

완료 기준:

- consumer resolution casebook이 있다.

### Step 3. Timing / Write-Order Audit

목표:

- guard 계산 시점과 final payload write 시점이 같은 source를 보는지 확인한다.

해야 할 일:

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py) logging path를 점검한다.
- local `observe_confirm_v2`가 언제 비고 언제 채워지는지 좁힌다.
- 필요하면 sample row와 코드 흐름을 연결한 memo를 만든다.

완료 기준:

- timing / write-order casebook이 있다.

### Step 4. Provenance Surface Audit

목표:

- provenance가 slim row, detail sidecar, replay intermediate 어디까지 보존되는지 정리한다.

해야 할 일:

- slim row에 남는 provenance 필드와 빠지는 필드를 정리한다.
- detail sidecar에서만 복원 가능한 source를 분리한다.
- compare/debug에 필요한 provenance minimum set를 적는다.

완료 기준:

- provenance surface memo가 있다.

### Step 5. 결과 memo와 다음 active step 고정

목표:

- source provenance fix가 먼저인지, compare policy refinement가 먼저인지 결정한다.

해야 할 일:

- reconfirm memo를 작성한다.
- 다음 active step을 고정한다.

완료 기준:

- 문서만 봐도 다음이 `runtime provenance fix`인지 `S3 compare policy refinement`인지 판단 가능하다.

## 3. Done Definition

아래를 만족하면 이 단계는 닫는다.

- runtime source baseline snapshot memo가 있다.
- consumer resolution casebook이 있다.
- timing / write-order casebook이 있다.
- provenance surface memo가 있다.
- 다음 active step decision memo가 있다.

현재 active step:

- `Step 1. Runtime Source Baseline Snapshot`
