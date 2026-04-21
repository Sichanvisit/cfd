# Product Acceptance PA2 Teacher Label Exploration Entry Layer Implementation Memo

## 상태

이번 문서는 `teacher-label exploration entry layer` 1차 구현 memo다.

핵심은:

- 메인 entry policy는 그대로 두고
- 놓친 teacher-label entry family만 soft-guard bypass로 좁게 열고
- reduced size와 explicit logging을 붙였다는 점이다

## 반영 파일

- [backend/core/config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [backend/services/entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [tests/unit/test_entry_service_guards.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_service_guards.py)

## 구현 요약

- 새 config:
  - `ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED`
  - allowlist / score ratio / threshold gap / size multiplier 계열
- 새 helper:
  - `teacher_label_exploration_entry_v1`
- 우회 지점:
  - `probe_promotion_guard_v1`
  - `consumer_open_guard_v1`
- 로깅:
  - `teacher_label_exploration_active`
  - `teacher_label_exploration_family`
  - `teacher_label_exploration_reason`
  - `teacher_label_exploration_size_multiplier`

## 검증

- `pytest -q tests/unit/test_entry_service_guards.py` -> `78 passed`
- `pytest -q tests/unit/test_entry_try_open_entry_probe.py` -> `18 passed`

## 현재 판단

이번 1차는 broad exploration이 아니라
`teacher-label family on-demand exploration`
으로 시작하는 것이 맞다.

다음은 runtime 실제 row에서 exploration tag가 찍히는지 보고,
그 다음에 2차 family를 넓힐지 결정하면 된다.
