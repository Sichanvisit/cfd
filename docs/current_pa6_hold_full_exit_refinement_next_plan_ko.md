# Current PA6 Hold / Full Exit Refinement Next Plan

## 목적

이 문서는 `PA6 rule refinement` 다음 단계로,
왜 지금 `open_loss`와 `runner_secured` position-side row를 더 모아야 하는지,
그리고 그 데이터를 바탕으로 `HOLD / FULL_EXIT` 규칙을 어떤 순서로 다듬는 것이 맞는지
실행 가능한 형태로 정리한 문서다.

이번 문서의 초점은 단순히
`데이터를 더 모으자`
가 아니다.

핵심은 아래 두 가지를 동시에 닫는 것이다.

1. `open_loss family`와 `runner_secured family`를 의도적으로 더 수집
2. 그 위에서 `HOLD / FULL_EXIT` rule을 precedence와 evidence 기준으로 더 정교화

---

## 현재 상태 진단

기준 artifact:

- [checkpoint_action_eval_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_action_eval_latest.json)
- [checkpoint_position_side_observation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_position_side_observation_latest.json)

현재 요약:

- `resolved_row_count = 6`
- `position_side_row_count = 3`
- `manual_exception_count = 3`
- `runtime_proxy_match_rate = 1.0`
- `WAIT 4 / PARTIAL_EXIT 1 / PARTIAL_THEN_HOLD 1`
- `open_profit_row_count = 1`
- `open_loss_row_count = 0`
- `runner_secured_row_count = 0`

즉 지금은 다음까진 왔다.

- `WAIT 과다` 일부 완화
- `active flat-profit family` 분리
- `PARTIAL_EXIT / PARTIAL_THEN_HOLD`는 첫 사례 확보

하지만 아직 아래는 사실상 비어 있다.

- `HOLD` 사례
- `FULL_EXIT` live position-side 사례
- `runner_secured` 사례
- `open_loss` 사례

따라서 다음 refinement의 핵심은
새 threshold를 더 억지로 넣는 것보다 먼저
**지금 비어 있는 family를 채우는 방향으로 수집 경로를 설계하는 것**이다.

---

## 외부 조언에서 실제로 채택할 부분

외부 조언 중 이번 단계에 실제로 채택할 가치는 아래가 크다.

### 1. `WAIT`는 마지막 fallback으로 다뤄야 한다

이건 이미 1차 반영이 들어갔다.
다음 단계에서는 `HOLD / FULL_EXIT` family를 더 선명하게 만들수록
`WAIT`가 자연스럽게 더 줄어들게 된다.

### 2. family를 먼저 분리하고 rule을 얹어야 한다

현재는 `active_flat_profit`까지 분리했다.
다음은 아래 2개를 더 명시적으로 볼 필요가 있다.

- `active_open_loss`
- `active_runner_secured`

### 3. evidence는 등급을 나눠야 한다

이번 단계에서는 다음처럼 보는 것이 맞다.

#### 1급 evidence

- `checkpoint_type`
- `source`
- `runner_secured`
- `position_size_fraction`
- `giveback_from_peak`

#### 2급 evidence

- `mfe_since_entry`
- `mae_since_entry`
- `shock_at_profit`

#### 3급 evidence

- runner 전용 세부 label 분화를 위한 추가 파생치

### 4. 대표 family를 먼저 판정하고 일반 rule로 확장해야 한다

즉 이번 단계는 전체 일반화보다
아래 family를 먼저 닫는 것이 맞다.

- `open_loss -> FULL_EXIT`
- `runner_secured + continuation -> HOLD / PARTIAL_THEN_HOLD`
- `open_profit but no runner -> HOLD vs PARTIAL_THEN_HOLD`

---

## 다음 refinement의 큰 방향

한 줄로 요약하면 이렇다.

> 다음 단계는 `WAIT를 더 줄이자`가 아니라,
> **`open_loss`와 `runner_secured` family를 먼저 채우고,
> 그 위에서 `HOLD / FULL_EXIT` 규칙을 여는 단계**다.

즉 순서는 아래가 맞다.

1. family 수집 경로 강화
2. family 관측 artifact 강화
3. family별 rule gate 추가
4. golden row / regression 검증
5. eval 기준선 재확인

---

## 세부 로드맵

## PF1. Collection Target Lock

### 목적

다음 refinement에서 의도적으로 늘릴 row family를 고정한다.

### 이번에 목표로 삼을 family

1. `active_open_loss`
2. `active_runner_secured`
3. `active_open_profit_hold_bias`

### 정의

#### `active_open_loss`

- `position_side != FLAT`
- `unrealized_pnl_state = OPEN_LOSS`

#### `active_runner_secured`

- `position_side != FLAT`
- `runner_secured = true`

#### `active_open_profit_hold_bias`

- `position_side != FLAT`
- `unrealized_pnl_state = OPEN_PROFIT`
- `runner_secured = false`
- `continuation`이 `reversal`보다 우세
- `partial_exit_ev`가 아주 강하지 않음

### 완료 기준

- 위 3개 family가 문서와 테스트에서 공통 기준으로 고정된다

---

## PF2. Exit-Manage Collection Enrichment

### 목적

`exit_manage` 경로에서
`open_loss`와 `runner_secured` row가 더 자주 checkpoint row로 남게 한다.

### 핵심 아이디어

지금 부족한 것은 score가 아니라 row 밀도다.
따라서 `exit_manage_positions.py`에서
이미 존재하는 final-stage 분기를 더 세밀하게 source/family로 남기게 해야 한다.

### 수집 우선 source

#### `FULL_EXIT` 후보 수집용

- `exit_manage_protective`
- `exit_manage_recovery`
- `exit_manage_managed_exit`

#### `HOLD / PARTIAL_THEN_HOLD` 후보 수집용

- `exit_manage_runner`
- `exit_manage_hold`

### 추가로 남기면 좋은 필드

- `checkpoint_rule_family_hint`
  - `open_loss_protective`
  - `runner_secured_continuation`
  - `profit_hold_bias`
- `giveback_from_peak`
- `giveback_ratio`
- `exit_stage_family`
  - `protective`
  - `runner`
  - `hold`
  - `managed_exit`

### 구현 대상

- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)
- [path_checkpoint_open_trade_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_open_trade_backfill.py)

### 완료 기준

- 새로 쌓이는 row에서 `open_loss_row_count > 0`
- `runner_secured_row_count > 0`

---

## PF3. Observation Upgrade

### 목적

부족한 family가 실제로 늘고 있는지
artifact만 봐도 바로 알 수 있게 한다.

### 추가로 보고 싶은 observation 항목

- `active_open_loss_row_count`
- `active_runner_secured_row_count`
- `hold_candidate_row_count`
- `full_exit_candidate_row_count`
- `giveback_heavy_row_count`
- symbol별 `family_counts`

### 구현 대상

- [path_checkpoint_position_side_observation.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_position_side_observation.py)
- [build_checkpoint_position_side_observation.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_checkpoint_position_side_observation.py)

### 완료 기준

- observation artifact만 봐도
  어떤 family가 부족한지 즉시 드러난다

---

## PF4. HOLD Rule Refinement

### 목적

`open-profit continuation`과 `runner-secured continuation`에서
`HOLD`를 더 선명하게 분리한다.

### 어떤 장면을 `HOLD` 후보로 볼 것인가

#### hold family A

- `runner_secured = true`
- `continuation >= reversal`
- `full_exit_risk 낮음`
- `giveback_ratio 낮음`

이 경우는 `PARTIAL_THEN_HOLD` 이후의 유지 상태이므로
`HOLD` 쪽이 더 자연스럽다.

#### hold family B

- `OPEN_PROFIT`
- `continuation` 우세
- `partial_exit_ev`가 hold보다 뚜렷하게 높지 않음
- `checkpoint_type in {RECLAIM_CHECK, LATE_TREND_CHECK, RUNNER_CHECK}`

이 경우도 `WAIT`보다는 `HOLD`가 더 자연스럽다.

### 초안 rule 방향

```python
if runner_secured and continuation >= reversal and full_exit_risk < 0.32 and giveback_ratio < 0.22:
    HOLD

elif open_profit and continuation >= reversal + 0.05 and hold_quality >= 0.50 and partial_exit_ev < hold_quality + 0.03:
    HOLD
```

### 주의점

- 초반엔 `HOLD` auto-apply를 너무 넓히지 않는다
- `runner_secured`가 붙은 row부터 먼저 여는 편이 안전하다

### 구현 대상

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)
- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

### 완료 기준

- hindsight / runtime 양쪽에서 `HOLD` 사례가 최소 1개 이상 생긴다
- `manual_exception`이 과도하게 늘지 않는다

---

## PF5. FULL_EXIT Rule Refinement

### 목적

`active_open_loss` family에서
`FULL_EXIT`를 더 분명하게 auto-apply 가능한 family로 만들기 시작한다.

### 어떤 장면을 `FULL_EXIT` 후보로 볼 것인가

#### full-exit family A

- `OPEN_LOSS`
- `reversal`이 `continuation`보다 강하게 우세
- `full_exit_risk` 높음
- `source`가 protective/recovery/managed_exit 계열

#### full-exit family B

- `active_flat_profit` 또는 `OPEN_LOSS`
- `giveback_ratio`가 매우 큼
- `checkpoint_type = LATE_TREND_CHECK`
- hold / partial 근거가 약함

### 초안 rule 방향

```python
if open_loss and full_exit_risk >= 0.68 and reversal >= continuation + 0.08 and protective_source:
    FULL_EXIT

elif open_loss and full_exit_risk >= 0.74 and reversal >= continuation + 0.12:
    FULL_EXIT

elif active_flat_profit and giveback_ratio >= 0.55 and reversal >= continuation + 0.15 and hold_quality < 0.30:
    FULL_EXIT
```

### 주의점

- `FULL_EXIT`는 precision 우선
- 첫 단계에서는 protective source에 강하게 묶는 편이 맞다

### 구현 대상

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)
- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

### 완료 기준

- `open_loss` row가 생겼을 때 `FULL_EXIT`가 실제로 잡힌다
- `premature_full_exit_rate`가 악화되지 않는다

---

## PF6. Manual-Exception Adoption Order

### 목적

어떤 family부터 auto-apply를 넓힐지 순서를 정한다.

### 추천 순서

1. `open_loss + protective_source + high_full_exit_risk`
   - 가장 먼저 auto-apply 넓혀도 되는 family

2. `runner_secured + continuation strong + low giveback`
   - `HOLD` 또는 `PARTIAL_THEN_HOLD`

3. `open_profit hold-bias`
   - 아직은 일부 manual 유지

4. `flat-profit ambiguous`
   - 계속 가장 보수적으로 유지

### 이유

- 외부 조언대로 precision 우선 family부터 auto-apply를 넓히는 편이 안전하다
- `HOLD`와 `PARTIAL_EXIT`는 여전히 가장 애매하므로 늦게 넓히는 편이 맞다

---

## PF7. Golden Test Expansion

### 목적

새 family가 열릴 때마다 rule drift를 막는다.

### 다음에 추가할 golden row

1. `open_loss protective row -> FULL_EXIT`
2. `runner_secured continuation row -> HOLD`
3. `open_profit hold-bias row -> HOLD`
4. `open_profit trim-bias row -> PARTIAL_THEN_HOLD or PARTIAL_EXIT`

### 구현 대상

- [test_path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_action_resolver.py)
- [test_path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_dataset.py)
- [test_exit_manage_checkpoint_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_manage_checkpoint_runtime.py)

### 완료 기준

- 대표 family가 fixture로 고정된다
- rule 변경 시 결과가 즉시 드러난다

---

## 실제 코드 변경 순서 추천

다음 턴에서 코드를 건드릴 때는 이 순서가 가장 안전하다.

1. `path_checkpoint_context.py`
   - family hint / giveback field 정리

2. `exit_manage_positions.py`
   - source / family hint / final-stage collection 강화

3. `path_checkpoint_open_trade_backfill.py`
   - live row를 더 잘 따라가도록 backfill 보강

4. `path_checkpoint_position_side_observation.py`
   - 부족 family 관측 항목 확장

5. `path_checkpoint_action_resolver.py`
   - HOLD / FULL_EXIT rule 추가 refinement

6. `path_checkpoint_dataset.py`
   - hindsight bootstrap과 manual-exception 기준 동기화

7. 테스트
   - golden rows
   - exit manage runtime
   - dataset/eval 회귀

8. artifact 재생성
   - dataset
   - eval
   - management action snapshot
   - position-side observation

---

## 이번 단계의 성공 기준

다음 refinement가 성공했다고 보려면 최소 아래가 필요하다.

### 데이터 기준

- `open_loss_row_count >= 1`
- `runner_secured_row_count >= 1`

### 라벨 기준

- `HOLD` hindsight 또는 runtime 사례 최소 1개
- `FULL_EXIT` hindsight 또는 runtime 사례 최소 1개

### 품질 기준

- `manual_exception_count` 유지 또는 감소
- `premature_full_exit_rate` 악화 없음
- `runtime_proxy_match_rate` 유지

---

## 최종 한 줄 결론

다음 단계의 본질은
규칙을 더 똑똑하게 “추측”하는 것이 아니라,
**지금 비어 있는 `open_loss`와 `runner_secured` family를 먼저 채우고,
그 위에서 `HOLD / FULL_EXIT` 규칙을 precision 우선으로 여는 것**이다.
