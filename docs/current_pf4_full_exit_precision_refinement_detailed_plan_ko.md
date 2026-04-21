# Current PF4 Full Exit Precision Refinement Detailed Plan

## 목적

이 문서는 `PF2/PF3 collection + observation` 다음 단계로 진행한
`PF4 FULL_EXIT precision refinement + runner carry-forward groundwork`
작업 기록이다.

이번 단계의 핵심 목적은 아래 2개였다.

1. `FULL_EXIT`가 score leader라는 이유만으로 너무 쉽게 열리지 않게 만들기
2. `runner_secured` family가 나중에 더 잘 이어지도록 backfill carry-forward 기반을 깔아두기

---

## 문제 인식

이전 상태는 아래가 핵심 병목이었다.

- `open_loss_row_count = 2`
- `runner_secured_row_count = 0`
- `premature_full_exit_rate = 1.0`
- `full_exit_precision = 0.0`

즉 `open_loss` family는 실제 row가 생기기 시작했는데,
runtime resolver가 `FULL_EXIT`를 너무 쉽게 고르고 있었고,
hindsight는 그걸 따라가지 못하고 있었다.

한 줄로 말하면:

> `FULL_EXIT`가 “강한 protective open-loss” family에서만 precision 있게 열려야 하는데,
> 실제로는 `score_leader::full_exit` fallback으로 과도하게 열리고 있었다.

---

## 이번에 실제로 바꾼 것

## 1. FULL_EXIT gate를 별도 함수로 분리

대상:

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)

추가:

- `_full_exit_gate_passed(...)`

핵심 rule:

- `open_loss + protective_source + full_exit_score + reversal dominance + giveback_ratio`
  조합일 때만 `FULL_EXIT`
- family hint가 없어도
  `full_exit_score`와 `reversal dominance`가 매우 강하면
  `open_loss_extreme_pressure_exit` 허용
- `active_open_loss`인데 protective gate가 없으면
  `FULL_EXIT` 대신 `PARTIAL_EXIT` 또는 `WAIT` fallback

의도:

- `FULL_EXIT`를 단순 score leader가 아니라
  precision gate를 통과한 family에서만 허용하기 위함

---

## 2. non-protective open-loss row는 PARTIAL_EXIT로 강등

대상:

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)
- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

변경:

- `open_loss`지만 `protective_source`가 아니고
  full exit gate를 통과하지 못하는 row는
  `PARTIAL_EXIT` 또는 `WAIT` fallback으로 강등

의도:

- `FULL_EXIT` precision을 지키면서도
  `open_loss` row를 전부 `WAIT`로 보내지 않기 위함

---

## 3. hindsight bootstrap도 같은 gate를 공유

대상:

- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

변경:

- runtime resolver와 동일하게
  `_full_exit_gate_passed(...)`를 사용
- `open_loss_protective`면 `FULL_EXIT`
- `active_open_loss`면 우선 `PARTIAL_EXIT`

의도:

- runtime / hindsight drift를 줄이기 위함

---

## 4. runner carry-forward 기반 추가

대상:

- [path_checkpoint_open_trade_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_open_trade_backfill.py)

추가:

- `_build_prior_trade_context_map(...)`
- `_resolve_prior_trade_context(...)`

기능:

- 같은 `ticket` 또는 `trade_link_key`에
  이전 checkpoint row가 있으면
  `runner_secured`, `position_size_fraction`, `family_hint`, `exit_stage_family`
  문맥을 이어받음

의도:

- open trade snapshot만으로도
  이전 runner 상태를 일정 부분 이어받게 하기 위함

주의:

- 이번 artifact에선 실제 live runner row가 없어서
  아직 수치상 `runner_secured_row_count = 0`
- 하지만 이후 runner row가 한 번이라도 생기면
  backfill 연속성이 더 좋아진다

---

## 5. resolved dataset 중복 컬럼 정리

대상:

- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

변경:

- `PATH_CHECKPOINT_RESOLVED_COLUMNS`에서
  base dataset 컬럼과 중복되던 `giveback_from_peak`, `giveback_ratio` 중복 정의 제거

의도:

- resolved csv 소비 편의성과 schema 안정성 확보

---

## 테스트

실행:

- `python -m pytest tests/unit/test_path_checkpoint_action_resolver.py tests/unit/test_path_checkpoint_dataset.py tests/unit/test_path_checkpoint_open_trade_backfill.py tests/unit/test_path_checkpoint_context.py tests/unit/test_path_checkpoint_position_side_observation.py tests/unit/test_build_checkpoint_open_trade_backfill.py tests/unit/test_build_checkpoint_position_side_observation.py`
- `python -m pytest tests/unit/test_entry_try_open_entry_policy.py tests/unit/test_exit_manage_checkpoint_runtime.py tests/unit/test_exit_service.py`

결과:

- `30 passed`
- `19 passed`

즉 FULL_EXIT gate, hindsight alignment, runner carry-forward, 기존 영향권까지 모두 통과했다.

---

## artifact 재생성 결과

실행:

- `python scripts/build_checkpoint_open_trade_backfill.py`
- `python scripts/build_checkpoint_dataset.py`
- `python scripts/build_checkpoint_eval.py`
- `python scripts/build_checkpoint_management_action_snapshot.py`
- `python scripts/build_checkpoint_position_side_observation.py`

---

## 최신 backfill 결과

- `open_trade_count = 6`
- `appended_count = 6`
- `position_side_row_count_after = 11`

해석:

- position-side row가 크게 늘었다
- 이제 rule refinement를 실제 row 위에서 더 볼 수 있다

---

## 최신 dataset 결과

- `resolved_row_count = 14`
- `position_side_row_count = 11`
- `manual_exception_count = 9`
- `non_wait_hindsight_row_count = 7`
- `hindsight_label_counts = WAIT 7 / PARTIAL_EXIT 5 / PARTIAL_THEN_HOLD 1 / FULL_EXIT 1`

해석:

- `open_loss` family가 많이 들어오면서 `PARTIAL_EXIT`와 `FULL_EXIT` hindsight가 실제로 생겼다
- 하지만 `manual_exception`은 아직 많다

---

## 최신 eval 결과

- `runtime_proxy_match_rate = 0.714286`
- `premature_full_exit_rate = 0.5`
- `runner_capture_rate = 1.0`
- `partial_then_hold_quality = 1.0`
- `full_exit_precision = 0.5`

가장 중요한 변화:

- `premature_full_exit_rate`
  - 이전: `1.0`
  - 현재: `0.5`

- `full_exit_precision`
  - 이전: `0.0`
  - 현재: `0.5`

즉 `FULL_EXIT precision`은 실제로 개선되기 시작했다.

---

## 최신 management action snapshot 결과

- `WAIT = 4`
- `PARTIAL_EXIT = 4`
- `HOLD = 3`
- `FULL_EXIT = 2`
- `PARTIAL_THEN_HOLD = 1`

해석:

- runtime management 분포에서 `HOLD`가 실제로 등장하기 시작했다
- 즉 이전보다 `WAIT`만 남는 구조는 벗어나고 있다

다만 이 `HOLD`가 정말 좋은 `HOLD`인지,
아직은 runner-secured family가 아니라 open-loss/hold-bias 쪽인지
다음 검토가 필요하다

---

## 최신 observation 결과

- `position_side_row_count = 11`
- `open_profit_row_count = 1`
- `open_loss_row_count = 7`
- `runner_secured_row_count = 0`
- `hold_candidate_row_count = 4`
- `full_exit_candidate_row_count = 7`
- `giveback_heavy_row_count = 7`

`family_counts`

- `active_open_loss = 6`
- `open_loss_protective = 1`
- `active_position = 1`

해석:

- `open_loss` family는 충분히 보이기 시작했다
- `runner_secured`는 여전히 실제 data가 없다
- 따라서 다음 단계는 분명하다

1. `FULL_EXIT`는 이제 더 다듬을 수 있다
2. `HOLD`는 runner family가 없어서 아직 완전하게 닫기 어렵다

---

## 이번 턴에서 얻은 가장 중요한 판단

### 1. FULL_EXIT는 이제 “조정 가능한 precision 문제”로 바뀌었다

이전엔 거의 전부 premature였다.
지금은 `0.5`까지 내려왔다.

즉 다음 refinement는
`open_loss_protective`와 `active_open_loss` 경계만 더 다듬으면
추가 개선 여지가 크다.

### 2. HOLD는 이제 수는 보이지만 family가 아직 약하다

runtime 분포엔 `HOLD = 3`이 나타났다.
하지만 observation 기준 `runner_secured_row_count = 0`이라
우리가 원했던 “runner 유지형 HOLD”는 아직 충분히 확보되지 않았다.

즉 `HOLD` 정교화는
지금 당장 threshold를 더 세게 만지는 것보다
`runner_secured` row를 실제로 더 수집하는 것이 먼저다.

### 3. 다음 병목은 precision보다 family coverage다

지금은 `open_loss`는 너무 많고
`runner_secured`는 하나도 없다.

즉 다음 단계는

- `runner collection 강화`
- `FULL_EXIT protective gate 미세 조정`

이 두 개가 핵심이다.

---

## 다음 구현 순서 추천

1. `exit_manage_runner` live row가 실제 checkpoint row로 더 남도록 보강
2. `runner_secured` family fixture 추가
3. `FULL_EXIT`에서 `open_loss_protective` vs `active_open_loss` margin 추가 조정
4. artifact 재생성 후
   - `premature_full_exit_rate`
   - `full_exit_precision`
   - `runner_secured_row_count`
   - `hold_precision`
   재확인

---

## 최종 한 줄 결론

이번 PF4의 핵심 성과는
`FULL_EXIT`를 score fallback에서 family gate 기반으로 바꾸기 시작해서
실제 precision을 `0.0 -> 0.5` 수준으로 올린 것이다.

반면 `runner_secured`는 아직 실제 row가 없으므로,
다음 단계의 본질은 **`FULL_EXIT`를 조금 더 다듬으면서, 동시에 runner family를 실제로 채우는 것**이다.
