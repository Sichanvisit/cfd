# CA1 Continuation Accuracy Tracking + Execution Diff Logging Roadmap

## 현재 단계

이번 단계는 큰 설계를 더 확장하는 단계가 아니라,
이미 연결된 continuation / execution / state25 bridge를
`관찰 -> 계측 -> 검증` 가능한 상태로 바꾸는 단계다.

## STAGE A. 구현

완료:

- continuation accuracy tracker 서비스 추가
- runtime row에 `current_close / live_price` 보강
- accuracy summary / artifact export 연결
- execution diff nested + flat fields 추가
- `ai_entry_traces`에 execution diff 기록
- `entry_decision_result_v1.metrics`에 execution diff 기록

핵심 파일:

- [directional_continuation_accuracy_tracker.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\directional_continuation_accuracy_tracker.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

## STAGE B. 관찰

다음부터 실제로 볼 값:

1. continuation accuracy

- `directional_continuation_accuracy_summary_v1.primary_correct_rate`
- symbol/direction별 `correct_rate`
- `false_alarm_rate`

2. execution diff

- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`
- `execution_diff_reason_keys`

## STAGE C. 검증

### wrong-side guard

- 최근 50건 진입 시도 중 guard 발동 건수
- guard 발동 후 hindsight 정합률

### continuation promotion

- 최근 50건 중 promotion 발동 건수
- promotion 승격 후 승률 / false promotion 비율

### continuation accuracy

- primary horizon `20 bars`
- 기준:
  - `> 65%`: 안정적
  - `55~65%`: 계속 관찰
  - `< 55%`: 기준 재검토

## STAGE D. bounded live 전환 준비

전환 판단 전 최소 확인:

1. log-only 샘플 충분
2. continuation accuracy 기준 충족
3. wrong-side guard / promotion execution diff 누적
4. false alarm 과도 증가 없음

즉 다음 핵심은 새 로드맵을 더 그리는 게 아니라,
이 로그가 실제로 쌓이며 어떤 수치를 만드는지 보는 것이다.

## 테스트

추가/확인 테스트:

- [test_directional_continuation_accuracy_tracker.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_directional_continuation_accuracy_tracker.py)
- [test_entry_try_open_entry_probe.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_try_open_entry_probe.py)
- [test_storage_compaction.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_storage_compaction.py)
- [test_trading_application_runtime_status.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_trading_application_runtime_status.py)

이번 단계 기준 검증:

- `py_compile ok`
- `pytest 94 passed`
