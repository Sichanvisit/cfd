# PF5 Runner-Family Hold Refinement Detailed Plan

## 목적

- `runner_secured` family row가 거의 없어서 `HOLD`가 runner 기준으로 잘 열리지 않던 병목을 줄인다.
- `open trade`만 보던 backfill을 넓혀 `closed trade`의 `lock / hold_continue / target` 흔적도 runner-family bootstrap row로 수집한다.
- 이미 runner가 확보된 row는 `PARTIAL_THEN_HOLD`보다 `HOLD`가 먼저 열리도록 resolver와 hindsight bootstrap을 보강한다.

## 이번 단계 구현

### 1. runner-family bootstrap 수집 확장

대상 파일:

- `backend/services/path_checkpoint_open_trade_backfill.py`

핵심 변경:

- `closed_trades` 최근 구간을 읽는 loader 추가
- `exit_reason / exit_policy_stage / exit_wait_decision_family / exit_wait_bridge_status / exit_wait_hold_class`를 합쳐서 `runner / hold` candidate를 판정
- `Lock Exit`, `hold_continue`, `mid/late`, `target` 같은 closed-trade 흔적을 checkpoint row로 backfill
- `source`
  - `closed_trade_runner_backfill`
  - `closed_trade_hold_backfill`
  로 분리
- `runner_secured_row_count_after`를 artifact summary에 추가
- open-trade backfill도 `runtime_row`의 `exit_manage_context_v1 / exit_wait_taxonomy_v1`를 읽어서 runner/hold 문맥을 더 잘 복원

### 2. runner-secured HOLD rule 추가

대상 파일:

- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_dataset.py`

핵심 변경:

- 이미 `runner_secured=true`
- `size_fraction <= 0.68`
- `giveback_ratio <= 0.22`
- `continuation >= reversal - 0.02`
- `hold_score >= 0.46`

조건이면 `PARTIAL_THEN_HOLD`보다 `HOLD`를 우선

새 reason:

- `runner_secured_hold_continue`
- `runner_family_hold_bias`
- `bootstrap_runner_secured_hold_continue`
- `bootstrap_runner_family_hold_continue`

## 테스트

추가/갱신 파일:

- `tests/unit/test_path_checkpoint_open_trade_backfill.py`
- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`

검증 결과:

- checkpoint/refinement/backfill 묶음: `23 passed`
- context/exit/entry 영향권 회귀: `26 passed`

총 `49 passed`

## 최신 artifact 결과

### checkpoint_open_trade_backfill_latest.json

- `open_trade_count = 4`
- `closed_trade_count = 80`
- `closed_candidate_count = 65`
- `appended_count = 69`
- `closed_appended_count = 65`
- `position_side_row_count_after = 80`
- `runner_secured_row_count_after = 47`

### checkpoint_dataset_resolved.csv / checkpoint_action_eval_latest.json

- `resolved_row_count = 83`
- `position_side_row_count = 80`
- `manual_exception_count = 17`
- `runtime_proxy_match_rate = 0.915663`
- `hold_precision = 0.851852`
- `partial_then_hold_quality = 0.95`
- `hindsight_label_counts`
  - `PARTIAL_THEN_HOLD = 39`
  - `HOLD = 23`
  - `WAIT = 12`
  - `PARTIAL_EXIT = 8`
  - `FULL_EXIT = 1`

### checkpoint_position_side_observation_latest.json

- `runner_secured_row_count = 47`
- `hold_candidate_row_count = 73`
- `full_exit_candidate_row_count = 8`
- `family_counts`
  - `runner_secured_continuation = 47`
  - `profit_hold_bias = 21`
  - `active_open_loss = 6`
  - `open_loss_protective = 2`

## 해석

- 이전 병목은 `FULL_EXIT precision`만이 아니라 `runner-family coverage 부족`이었다.
- 이번 단계로 `runner_secured`가 더 이상 0이 아니게 됐고, `HOLD`가 실제 runner-family 기준으로 열리기 시작했다.
- 다만 현재 row의 상당수는 `closed_trade_*_backfill`에서 온 bootstrap row다.
- 즉 구조 검증과 rule shaping에는 매우 유용하지만, 다음 단계에서는 `live exit_manage_runner` source 비중을 늘려서 bootstrap 의존도를 점진적으로 낮추는 게 맞다.

## 다음 순서

1. `exit_manage_runner` live source row를 더 실제로 늘리기
2. `closed_trade_hold_backfill` 비중이 너무 높은 symbol이 있는지 점검
3. `runner_secured_continuation` 내부에서
   - `HOLD`
   - `PARTIAL_THEN_HOLD`
   - `PARTIAL_EXIT`
   경계 margin을 한 번 더 조정
