# PA7 Review Processor: Policy Replay Refinement

## 왜 보강했나

`PA7 review queue`는 historical `management_action_label` 기준으로 manual-exception 그룹을 모은다.

이건 “당시 실제로 어떤 결정이 저장됐는가”를 보는 데는 맞지만, 정책 패치를 몇 번 거친 뒤에는 아래 문제가 생긴다.

- historical label은 여전히 `PARTIAL_EXIT`
- 현재 resolver replay는 이미 `WAIT`
- 그런데 review processor가 historical label만 우선 보면
  같은 그룹이 계속 top mismatch로 남는다

즉 `queue는 움직이지 않는데, 현재 정책은 이미 고쳐진 상황`을 분리해서 봐야 한다.

## 이번 보강

`path_checkpoint_pa7_review_processor.py`

각 manual-exception row에 대해 추가로:

- `policy_replay_action_label`

을 계산한다.

이 값은 historical stored label을 그대로 읽지 않고,
현재 `resolve_management_action()`을 다시 돌린 결과다.

## 새 review disposition

- `policy_mismatch_review`
  - stored baseline도 틀리고 current replay도 아직 안 맞는 그룹
- `baseline_hydration_gap`
  - blank baseline / missing score가 큰 그룹
- `confidence_only_confirmed`
  - stored baseline과 hindsight가 이미 대부분 맞는 그룹
- `resolved_by_current_policy`
  - stored baseline은 틀렸지만 current replay는 이미 hindsight와 맞는 그룹

## 의미

`resolved_by_current_policy`는 “더 이상 resolver patch 1순위가 아닌 그룹”이다.

즉 이 그룹은:

- historical queue에는 남아 있지만
- current policy 기준으로는 이미 고쳐졌고
- 다음으로는 note만 남기고 더 아래 priority로 내려도 된다

## 기대 효과

- PA7 top queue가 현재 patch 효과를 반영해 실제 다음 작업을 보여준다
- 이미 고쳐진 family가 top mismatch로 계속 남는 현상을 줄인다
- 다음 실제 patch 대상이 `current policy` 기준으로 남아 있는 그룹으로 올라온다
