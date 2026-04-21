# Current PA6 Rule Refinement Detailed Plan

## 목적

이 문서는 `PA6 rule refinement`에서
실제로 어떤 순서로 코드를 바꾸었고,
무슨 효과가 있었는지 정리한 기록이다.

이번 턴의 초점은 아래 3개였다.

1. `action precedence` 명시
2. `active flat-profit row` 별도 family 분리
3. 대표 row 3개를 `golden test`로 고정

---

## 변경 순서

### 1. resolver precedence 명시

대상:

- `backend/services/path_checkpoint_action_resolver.py`

변경:

- `PATH_CHECKPOINT_ACTION_PRECEDENCE` 추가
- tie-break와 fallback이 알파벳 순서가 아니라
  `FULL_EXIT -> PARTIAL_THEN_HOLD -> PARTIAL_EXIT -> HOLD -> REBUY -> WAIT`
  순서를 따르도록 정리

의도:

- `WAIT`가 단순 기본값이 아니라
  최하단 fallback으로 해석되게 하기 위함

---

### 2. rule feature helper 추가

대상:

- `backend/services/path_checkpoint_action_resolver.py`

변경:

- `build_management_action_rule_features(...)` 추가

핵심 파생치:

- `row_family`
- `active_flat_profit`
- `open_profit`
- `open_loss`
- `giveback_from_peak`
- `giveback_ratio`
- `protective_source`
- `runner_source`

의도:

- score만 보지 않고
  family와 path/position 문맥을 같이 보게 하기 위함

---

### 3. resolver에 active flat-profit 전용 분기 추가

대상:

- `backend/services/path_checkpoint_action_resolver.py`

변경:

- `position_side != FLAT` 이면서 `unrealized_pnl_state = FLAT`인 row를
  별도 family로 처리

핵심 분기:

- 강한 reversal dominance + weak hold면 `PARTIAL_EXIT`
- 명확한 protective break면 `FULL_EXIT`
- continuation 우세면 `HOLD`
- 그 외는 `WAIT`

의도:

- 지금까지 `WAIT`로 너무 많이 남던 family를
  더 직접적으로 다루기 위함

---

### 4. open-profit continuation 분기 보강

대상:

- `backend/services/path_checkpoint_action_resolver.py`

변경:

- `PARTIAL_THEN_HOLD` threshold를
  open-profit continuation row에서 더 자연스럽게 타도록 보정
- `giveback_ratio`를 보고
  `PARTIAL_EXIT` 쪽으로 가는 경우도 분기

의도:

- `HOLD / PARTIAL_THEN_HOLD / PARTIAL_EXIT`의 경계를
  좀 더 실전적으로 나누기 위함

---

### 5. hindsight bootstrap을 같은 family 기준으로 정렬

대상:

- `backend/services/path_checkpoint_dataset.py`

변경:

- resolver와 동일한 `rule feature`를 사용
- `active_flat_profit` 전용 hindsight branch 추가
- `PARTIAL_THEN_HOLD`, `PARTIAL_EXIT`, `FULL_EXIT` confidence 계산 보강
- clear family는 `manual_exception_required`를 덜 타게 완화

의도:

- runtime resolver와 hindsight bootstrap이
  서로 다른 세계를 보지 않게 하기 위함

---

### 6. resolved dataset에 family / giveback 파생치 추가

대상:

- `backend/services/path_checkpoint_dataset.py`

추가 컬럼:

- `management_row_family`
- `giveback_from_peak`
- `giveback_ratio`

의도:

- 나중에 eval / debug / rule tuning에서
  어떤 family가 문제인지 바로 추적하기 위함

---

### 7. representative golden row test 추가

대상:

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`

고정한 대표 row:

1. `BTCUSD active flat-profit row`
   - 기대: `PARTIAL_EXIT`

2. `NAS100 active flat-profit row`
   - 기대: `WAIT`

3. `NAS100 active open-profit continuation row`
   - 기대: `PARTIAL_THEN_HOLD`

의도:

- 다음 rule tuning 때 핵심 사례 분류가 흔들리지 않게 하기 위함

---

## 검증

실행한 테스트:

- `python -m pytest tests/unit/test_path_checkpoint_action_resolver.py tests/unit/test_path_checkpoint_dataset.py`
- `python -m pytest tests/unit/test_path_checkpoint_context.py tests/unit/test_exit_manage_checkpoint_runtime.py tests/unit/test_path_checkpoint_open_trade_backfill.py tests/unit/test_entry_try_open_entry_policy.py tests/unit/test_exit_service.py`

결과:

- `15 passed`
- `26 passed`

즉 핵심 규칙 변경과 영향권 회귀 모두 통과했다.

---

## artifact 재생성 결과

실행:

- `python scripts/build_checkpoint_dataset.py`
- `python scripts/build_checkpoint_eval.py`
- `python scripts/build_checkpoint_management_action_snapshot.py`
- `python scripts/build_checkpoint_position_side_observation.py`

### 최신 dataset 결과

- `resolved_row_count = 6`
- `position_side_row_count = 3`
- `manual_exception_count = 3`
- `non_wait_hindsight_row_count = 2`
- `hindsight_label_counts = WAIT 4 / PARTIAL_EXIT 1 / PARTIAL_THEN_HOLD 1`

### 최신 eval 결과

- `runtime_proxy_match_rate = 1.0`
- `manual_exception_count = 3`
- `runner_capture_rate = 1.0`
- `partial_then_hold_quality = 1.0`
- `recommended_next_action = collect_more_live_position_side_checkpoint_rows_before_pa6`

### observation 결과

- `position_side_row_count = 3`
- `open_profit_row_count = 1`
- `open_loss_row_count = 0`
- `runner_secured_row_count = 0`

---

## 이번 턴에서 실제로 좋아진 점

이전 대비 핵심 변화는 아래다.

- hindsight 분포가 `WAIT 5 / PARTIAL_THEN_HOLD 1`에서
  `WAIT 4 / PARTIAL_EXIT 1 / PARTIAL_THEN_HOLD 1`로 확장
- `manual_exception_count`가 `5`에서 `3`으로 감소
- `runtime_proxy_match_rate`가 `0.833333`에서 `1.0`으로 상승

즉 `WAIT 과다`와 `manual-exception 과다`를
조금이지만 실제로 줄이기 시작한 상태다.

---

## 아직 남은 핵심

이번 refinement로 구조는 좋아졌지만,
아직 아래는 부족하다.

1. `open_loss row`가 거의 없다
2. `runner_secured row`가 아직 없다
3. `HOLD`와 `FULL_EXIT` 사례는 여전히 live dataset이 얇다

즉 다음 우선순위는 여전히 아래다.

1. 더 많은 `exit_manage` position-side row 수집
2. `open_loss` / `runner_secured` family 확보
3. 그 다음 `HOLD` / `FULL_EXIT` precision refinement

---

## 최종 한 줄 결론

이번 PA6 refinement의 본질은
새 label을 늘린 것이 아니라,
**`WAIT`로 뭉개지던 active flat-profit family를 분리하고,
action precedence를 고정해서 runtime/hindsight rule을 같은 방향으로 정렬한 것**이다.
