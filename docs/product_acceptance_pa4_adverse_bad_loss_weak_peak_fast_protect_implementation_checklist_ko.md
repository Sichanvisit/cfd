# Product Acceptance PA4 Adverse Bad Loss Weak Peak Fast Protect Implementation Checklist

## confirm

- [x] fresh closed trade source 재확인
- [x] top `bad_loss adverse` representative row 재수집
- [x] weak-peak family로 target 고정

## implementation

- [x] [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py) 에 weak-peak adverse hold config 추가
- [x] [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py) 에 weak-peak min-hold 적용
- [x] [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py) 에 `adverse_weak_peak_protect` 추가
- [x] [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py) 호출부에 `peak_profit` 전달
- [x] [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 경유 시그니처 맞춤

## regression

- [x] [test_exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_hard_guard_action_policy.py)
- [x] [test_exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_engines.py)
- [x] [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py)
- [x] [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py)

## runtime

- [x] `cfd main.py` 재기동
- [x] restart log 기록

## verification

- [x] PA0 refreeze
- [x] immediate queue unchanged 가능성 기록
- [x] next follow-up을 fresh closed trade wait로 고정
