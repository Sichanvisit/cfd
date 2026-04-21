# Current PA4 Passive Score Calculation Detailed Plan

## 목적

이 문서는 `PA4. Passive Score Calculation`을 실제 구현 단위로 내린 상세 계획이다.

이번 단계의 목표는 하나다.

> checkpoint를 실제 행동으로 바꾸기 전에,
> 각 checkpoint row마다 management score를 log-only로 계산하고 저장하기

즉 이번 단계에서는 아직

- actual entry action 변경
- actual exit action 변경
- hindsight best label 적용
- resolver 기반 runtime adoption

으로 들어가지 않는다.

먼저 `runtime_continuation_odds / runtime_reversal_odds / runtime_hold_quality_score / runtime_partial_exit_ev / runtime_full_exit_risk / runtime_rebuy_readiness`를
안전하게 찍고, 다음 `PA5 / PA6`이 올라갈 수 있는 score contract를 고정하는 단계다.

---

## 이번 단계에서 바꾸는 것

### 1. 신규 서비스

- `backend/services/path_checkpoint_scoring.py`

역할:

- passive score 계산
- score reason 생성
- runtime latest row 반영용 prefixed field 생성
- checkpoint score snapshot 요약 생성

### 2. 신규 builder

- `scripts/build_checkpoint_score_snapshot.py`

역할:

- `checkpoint_rows.csv`를 읽는다
- score 분포를 symbol 기준으로 요약한다
- `checkpoint_score_snapshot_latest.json`을 만든다

### 3. storage 확장

기존 `checkpoint_rows.csv`에 아래 score column을 추가한다.

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`
- `runtime_score_reason`

### 4. 기존 entry/exit 흐름에는 log-only로만 연결

- `entry_try_open_entry.py`
- `exit_manage_positions.py`

이 두 경로는 이미 `record_checkpoint_context(...)`를 통해 checkpoint row를 저장한다.
이번 단계에서는 그 저장 함수 내부에서 score를 같이 계산하고 붙인다.

즉 entry/exit 코드는 더 흔들지 않고,
checkpoint storage 계층에서 score를 흘린다.

---

## 이번 단계에서 바꾸지 않는 것

- `initial_entry_surface` taxonomy
- 기존 broker execution finality
- actual `HOLD / PARTIAL / FULL_EXIT / REBUY` runtime 선택
- hindsight best action label
- dataset export / preview eval / signoff / activation

즉 이번 단계는 **판단 변경이 아니라 score 기록 단계**다.

---

## score contract

이번 단계에서 고정할 최소 runtime score는 아래 6개다.

- `runtime_continuation_odds`
  지금 leg가 같은 방향으로 더 이어질 가능성
- `runtime_reversal_odds`
  지금 leg가 꺾이거나 thesis가 깨질 가능성
- `runtime_hold_quality_score`
  현재 size를 유지할 품질
- `runtime_partial_exit_ev`
  일부 줄이고 runner를 남기는 편이 유리한지
- `runtime_full_exit_risk`
  지금 안 나가면 손상될 위험이 큰지
- `runtime_rebuy_readiness`
  pullback/reclaim 이후 다시 늘리거나 재진입할 준비도가 충분한지

추가로:

- `runtime_score_reason`
  이번 score 묶음에서 가장 강한 방향을 짧게 설명하는 reason string

---

## score evidence

PA4는 아래 4층 evidence만 사용한다.

### 1. structure / path hint

- `checkpoint_type`
- `surface_name`
- `leg_direction`
- `bars_since_last_checkpoint`

### 2. runtime directional hint

- `observe_action`
- `observe_side`
- `entry_candidate_bridge_action`
- `breakout_candidate_action`
- `blocked_by`

### 3. position state

- `position_side`
- `position_size_fraction`
- `unrealized_pnl_state`
- `runner_secured`
- `mfe_since_entry`
- `mae_since_entry`

### 4. pressure tokens

- wrong-side guard 성격 토큰
- protective/adverse 토큰
- continuation/reclaim 성격 토큰

이번 단계에서는 미래 정보가 들어가는 `hindsight_*` 필드는 절대 사용하지 않는다.

---

## 상세 구현 순서

### PA4-A. score service 추가

`path_checkpoint_scoring.py`에서 아래를 제공한다.

- `build_passive_checkpoint_scores(...)`
- `apply_checkpoint_scores_to_runtime_row(...)`
- `score_checkpoint_frame(...)`
- `build_checkpoint_score_snapshot(...)`

핵심 규칙:

- 모든 score는 `0.01 ~ 0.99`로 clamp한다
- 0/1 hard label처럼 굳지 않게 한다
- checkpoint / position / pressure가 동시에 반영되게 한다

### PA4-B. checkpoint storage 확장

`path_checkpoint_context.py`에서

- checkpoint csv column에 score 필드를 추가하고
- `record_checkpoint_context(...)` 내부에서 score를 계산해
  row / detail / runtime latest row에 같이 반영한다

### PA4-C. schema migration 방어

이미 `PA3`에서 생성된 `checkpoint_rows.csv`가 있으므로,
그 파일에 새 score column이 바로 append되면 header mismatch가 날 수 있다.

그래서 append 전에:

- 기존 csv header를 검사하고
- 새 schema와 다르면
- 기존 row를 읽어 새 column을 빈 값으로 채운 뒤
- 최신 column 순서로 다시 저장한다

이 규칙이 있어야 기존 구축물과 부딪히지 않는다.

### PA4-D. score snapshot builder

`build_checkpoint_score_snapshot.py`는

- score column이 이미 있는 row는 그대로 읽고
- score column이 비어 있는 구 row는 builder에서 fallback 계산해
- score snapshot artifact를 만든다

즉 live 누적이 아직 적어도 artifact는 바로 만들 수 있게 한다.

### PA4-E. tests

최소 아래를 검증한다.

- continuation 쪽 checkpoint는 `continuation > reversal`로 기울 수 있는가
- protective exit 쪽 loss checkpoint는 `full_exit_risk`가 높아지는가
- runtime latest row에 prefixed score가 반영되는가
- 기존 schema csv가 score column 확장으로 깨지지 않는가
- score snapshot artifact가 실제로 생성되는가

---

## 완료 기준

- `backend/services/path_checkpoint_scoring.py`가 생성된다
- `checkpoint_rows.csv`가 score column 확장을 안전하게 처리한다
- entry / exit에서 새 action 변경 없이 score가 checkpoint row에 붙는다
- `checkpoint_score_snapshot_latest.json`이 생성된다
- 기존 targeted pytest가 깨지지 않는다

---

## 다음 단계로 넘어가는 기준

PA4가 닫히면 다음은 `PA5 Hindsight Label / Dataset / Eval`이다.

즉 그 다음부터는

- score를 찍는 것

에서

- hindsight best management action을 붙이고
- checkpoint dataset / eval / KPI를 만드는 것

으로 넘어간다.
