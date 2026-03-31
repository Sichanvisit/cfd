# Consumer-Coupled Check/Entry Scene Refinement
## S0. Baseline Snapshot Spec

### 목적

`consumer-coupled check / entry` 체계와 `7-stage display` 체계를 이미 연결한 상태에서,
추가 scene refinement에 들어가기 전에 현재 baseline을 고정한다.

이 단계의 목적은:

- 지금 실제로 무엇이 `display=true`로 보이고 있는지
- 무엇이 `BLOCKED / OBSERVE / PROBE / READY`로 분류되는지
- `BTCUSD / NAS100 / XAUUSD`가 비슷한 장면을 어떻게 다르게 읽고 있는지
- 어디가 `must-show missing`, 어디가 `must-hide leakage`인지

를 코드/데이터 기준으로 설명 가능한 상태로 만드는 것이다.

즉 S0는 “수정” 단계가 아니라,
이후 S1~S5에서 기준이 흔들리지 않도록 현재 상태를 동결하는 단계다.

### 왜 필요한가

현재 남은 문제는 새 체계를 만드는 문제가 아니라,
이미 만든 `consumer_check_state_v1 -> entry_try_open_entry -> chart_painter`
체계 위에서

- 어떤 장면은 체크가 반드시 떠야 하고
- 어떤 장면은 절대 남발하면 안 되며
- 비슷하게 보이는 장면이 왜 서로 다르게 분기되는지

를 정밀하게 조정하는 문제다.

이때 baseline snapshot이 없으면:

- 원래도 이랬는지
- 최근 수정 때문에 바뀐 건지
- 심볼별 문제인지 scene 분류 문제인지

를 구분하기 어렵다.

따라서 S0는 이후 refinement의 공통 출발점을 고정하는 필수 단계다.

### 범위

이번 S0는 아래 범위만 다룬다.

- `BTCUSD`, `NAS100`, `XAUUSD` 최근 row 비교
- `consumer_check_state_v1` 관점의 stage/display 상태 비교
- chart display 관점의 density/imbalance 관찰
- `must-show missing` 후보와 `must-hide leakage` 후보 수집
- visually similar but semantically diverged case seed 수집

이번 단계에서는 아래는 하지 않는다.

- scene rule 자체 수정
- threshold / score / display tier 수정
- symbol override 값 수정
- painter shape/size/offset 수정

즉 현 상태 관찰과 고정만 수행한다.

### 직접 owner

- scene / check state owner
  - `backend/services/consumer_check_state.py`
  - `backend/services/entry_service.py`
  - `backend/services/entry_try_open_entry.py`
- chart display owner
  - `backend/trading/chart_painter.py`
  - `backend/trading/chart_flow_policy.py`
- baseline 관찰 데이터
  - `data/trades/entry_decisions.csv`
  - `data/runtime_status.json`
  - `data/analysis/chart_flow_distribution_latest.json`
  - `data/analysis/chart_flow_rollout_status_latest.json`

### 반드시 고정할 baseline 질문

S0에서는 아래 질문에 답할 수 있어야 한다.

1. 최근 row 기준으로 `BTCUSD / NAS100 / XAUUSD`는 어떤 `observe_reason`에서 많이 머무는가
2. `consumer_check_stage`는 각 심볼에서 어떤 비율로 `BLOCKED / OBSERVE / PROBE / READY`에 분포하는가
3. `consumer_check_display_ready=true`인 row는 주로 어떤 scene/reason에서 발생하는가
4. `display_score`와 `display_repeat_count`는 stage와 실제로 어떻게 매핑되고 있는가
5. 사용자가 “여긴 떠야 했는데 안 떴다”고 느끼는 장면은 실제로 어떤 reason/guard 때문에 숨겨졌는가
6. 사용자가 “여긴 뜨면 안 되는데 떴다”고 느끼는 장면은 실제로 어떤 candidate/late-block 경로로 표시됐는가
7. visually similar scene인데 서로 다른 side/scene/stage로 갈라진 사례가 무엇인가

### 필수 수집 필드

S0 baseline snapshot에서는 아래 필드를 반드시 함께 수집한다.

#### runtime/entry row 관점

- `symbol`
- `decision_time`
- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_scene_id`
- `consumer_check_stage`
- `consumer_check_side`
- `consumer_check_display_ready`
- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `entry_ready`
- `action`
- `box_state`
- `bb_state`
- `default_side`

#### chart/overlay 관점

- symbol별 최근 flow event 분포
- `BUY_WATCH / BUY_WAIT / BUY_PROBE / BUY_READY`
- `SELL_WATCH / SELL_WAIT / SELL_PROBE / SELL_READY`
- neutral `WAIT`
- stage별 density 차이
- 심볼별 directional imbalance

### baseline 산출물

S0 완료 시 아래 산출물이 있어야 한다.

1. `tri-symbol baseline table`
  - `BTCUSD / NAS100 / XAUUSD`의 recent row 비교표
2. `stage density snapshot`
  - 각 심볼의 `BLOCKED / OBSERVE / PROBE / READY` 밀도
3. `display ladder snapshot`
  - `display_score`와 `repeat_count`가 실제 row에서 어떻게 분포하는지
4. `must-show missing candidate list`
  - 사용자가 보기엔 떠야 하는데 숨겨진 대표 장면들
5. `must-hide leakage candidate list`
  - 사용자가 보기엔 뜨면 안 되는데 남아 있는 대표 장면들
6. `visually similar divergence seed list`
  - 비슷한 차트 모양인데 내부 scene/side가 다르게 갈라진 사례 seed

### baseline 분류 원칙

S0에서는 아직 “맞다/틀리다”를 확정하지 않는다.
대신 아래 네 가지 분류로만 수집한다.

#### 1. aligned

- 사용자 체감과 내부 scene/stage/display가 크게 어긋나지 않는 경우

#### 2. must-show missing

- 구조적으로 약한 체크라도 있어야 하는데 `display=false`거나 너무 낮게 눌린 경우

#### 3. must-hide leakage

- 실제론 막히거나 conflict인데 방향 체크가 남아 있는 경우

#### 4. visually similar divergence

- 차트상 유사해 보이는데 내부에선 서로 다른 side/scene/stage로 해석된 경우

### 완료 기준

아래가 만족되면 S0는 완료로 본다.

- `BTCUSD / NAS100 / XAUUSD` 각각에 대해 recent baseline 표를 만들 수 있다
- `consumer_check_stage`, `display_ready`, `display_score`, `repeat_count`의 실제 분포를 설명할 수 있다
- `must-show missing`과 `must-hide leakage` 대표 사례를 최소 각 3건 이상 확보한다
- visually similar divergence 사례를 다음 S3에서 바로 사용할 수 있게 seed 형태로 확보한다
- 이후 S1/S2/S3가 이 baseline을 참조해 출발할 수 있다

### 다음 단계 연결

- S1: must-show scene casebook
- S2: must-hide scene casebook
- S3: visually similar scene alignment audit

즉 S0는 이후 모든 refinement 단계의 기준선 역할을 한다.
