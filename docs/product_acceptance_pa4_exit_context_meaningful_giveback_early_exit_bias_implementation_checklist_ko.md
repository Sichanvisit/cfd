# Product Acceptance PA4 Exit Context Meaningful Giveback Early Exit Bias Implementation Checklist

## scope

- [x] `must_release / bad_exit` representative row 재확인
- [x] owner를 `scene bias + utility decision`으로 고정
- [x] lower-reversal hold family 제외 경계 고정

## implementation

- [x] [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py) 에 meaningful giveback bias config 추가
- [x] [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py) 에 `meaningful_giveback_exit_pressure` flag 및 delta 추가
- [x] [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py) current path에서 새 delta가 실제 winner에 반영되도록 확인

## regression

- [x] [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py) 추가
- [x] [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py) 추가
- [x] `pytest -q tests/unit/test_exit_utility_scene_bias_policy.py`
- [x] `pytest -q tests/unit/test_wait_engine.py`

## verification

- [x] PA0 baseline refreeze
- [x] current queue unchanged 가능성 memo 기록
- [x] next owner를 `fresh closed trade follow-up`으로 고정

## done condition

- 코드상으로는 `Exit Context meaningful giveback` family가 더 이른 `exit_now` 쪽으로 기울어야 한다
- baseline 수치가 즉시 안 줄더라도, 이유가 `fresh close artifact 대기`인지 문서로 남아 있어야 한다
