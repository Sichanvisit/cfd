# Runtime Source Cleanup Timing / Write-Order Casebook

## 문제였던 순서

정리 전 순서는 사실상 이랬다.

1. [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py) 가 runtime row 초안을 만든다.
2. 그 초안은 `observe_confirm_v1`를 canonical처럼 기록하고 있었다.
3. [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)의 `_append_entry_decision_log()`가 그 row로 먼저 `DecisionResult`를 만든다.
4. 그 과정에서 `consumer_migration_guard_v1`와 consumer provenance가 fallback처럼 계산될 수 있었다.
5. 이후 hot/detail/export 쪽이 그 provenance를 따라간다.

즉 문제는 `guard가 늦게 계산됐다`가 아니라 `guard가 읽는 row source가 이미 v1 canonical로 기울어 있었다`는 점이다.

## 수정 후 순서

1. `try_open_entry`가 처음부터 `observe_confirm_v2` canonical / `observe_confirm_v1` compatibility dual-write row를 만든다.
2. `_append_entry_decision_log()`는 들어온 row를 한 번 더 canonical 기준으로 self-heal한다.
3. 그 다음 `DecisionResult`를 만든다.
4. 그 결과 `consumer_migration_guard_v1`, `consumer_input_observe_confirm_field`, trace quality summary가 final canonical source와 맞춰진다.

## 의미

이번 cleanup은 compare 계산식 수정이 아니라, compare가 읽는 provenance의 write-order를 바로잡은 작업이다.
