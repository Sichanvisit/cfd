# Runtime Source Cleanup Reconfirm Memo

## 이번 라운드 결론

runtime source cleanup은 `compare policy`보다 `runtime provenance alignment`가 먼저라는 가설이 맞았다.

실제 수정 파일:

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)

추가 테스트:

- [test_entry_try_open_entry_probe.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_try_open_entry_probe.py)
- [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)

추가 회귀 확인:

- [test_entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_engines.py)
- [test_consumer_scope_contract.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_scope_contract.py)

## 검증 결과

- targeted regression: `4 passed`
- owner regression: `49 passed`
- combined regression: `121 passed`

## 현재 판단

이번 단계로 최소한 아래는 닫혔다.

- runtime row producer가 v1 canonical처럼 기록하던 직접 원인
- `_append_entry_decision_log()`가 pre-normalized row를 먼저 읽으며 provenance를 fallback처럼 굳히던 문제

## 다음 자연스러운 단계

이제는 `runtime provenance fix`를 한 번 반영한 뒤 실제 live rows를 다시 관측하고,

- `semantic_shadow_trace_quality`
- `compatibility_mode`
- `used_fallback_count`
- `consumer_input_observe_confirm_field`

가 어떻게 바뀌는지 본 다음,
정말 남는 문제가 있으면 그때 `S3 compare policy refinement`로 가는 게 맞다.
