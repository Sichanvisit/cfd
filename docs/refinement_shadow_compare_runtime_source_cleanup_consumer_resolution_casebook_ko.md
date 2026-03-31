# Runtime Source Cleanup Consumer Resolution Casebook

## 핵심 확인

`consumer_contract`의 공식 규칙은 이미 `observe_confirm_v2 -> observe_confirm_v1` 순서다.

직접 확인한 파일:

- [consumer_contract.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_contract.py)
- [test_consumer_scope_contract.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_scope_contract.py)

## runtime mismatch 케이스

문제는 resolution helper가 아니라 runtime row producer였다.

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py) 는 cleanup 전까지 `prs_canonical_observe_confirm_field = observe_confirm_v1`를 기록했다.
- same path에서 `observe_confirm_v2` dual-write도 보장되지 않았다.
- 그래서 [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py) 의 `_append_entry_decision_log()`가 `DecisionResult`를 만들 때 fallback처럼 해석될 수 있었다.

## 적용한 정리

### 1. runtime dual-write helper 추가

[entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)에 `_build_runtime_observe_confirm_dual_write()`를 추가했다.

이 helper는 아래를 동시에 고정한다.

- `prs_canonical_observe_confirm_field = observe_confirm_v2`
- `prs_compatibility_observe_confirm_field = observe_confirm_v1`
- `observe_confirm_v2`
- `observe_confirm_v1`
- `observe_confirm_input_contract_v2`
- `observe_confirm_migration_dual_write_v1`
- `observe_confirm_output_contract_v2`
- `observe_confirm_scope_contract_v1`
- `consumer_input_contract_v1`

### 2. try_open_entry write path에 helper 적용

same file의 runtime row payload와 `setup_context.metadata`에 dual-write helper를 그대로 연결했다.

즉 이제 live row와 setup detector context는 둘 다 v2 canonical 기준으로 같은 source를 본다.

### 3. append 단계 self-heal 추가

[entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)의 `_append_entry_decision_log()` 앞단에 아래 보호막을 넣었다.

- canonical field가 비어 있거나 `observe_confirm_v1`면 `observe_confirm_v2`로 교정
- v2가 비어 있고 v1이 있으면 v2를 mirror
- v1이 비어 있고 v2가 있으면 compatibility bridge도 mirror

이 self-heal은 live write-path의 provenance를 `DecisionResult` 생성 전에 정렬하기 위한 목적이다.

## 기대 효과

- `consumer_migration_guard_v1`가 final row와 같은 canonical source를 보게 된다.
- `consumer_input_observe_confirm_field`가 v2 canonical과 일치한다.
- trace quality 계산에서 불필요한 `observe_confirm_v1_fallback` 과대 표기가 줄어든다.
