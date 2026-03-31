# Consumer-Coupled Check / Entry Alignment Spec

## 1. 목적

체크 표기와 실제 진입을 서로 다른 의미 체계로 분리하지 않고, 같은 semantic/consumer chain 위에서 단계만 다르게 보이게 만든다.

목표는 아래 두 가지를 동시에 만족하는 것이다.

- 차트 체크가 `왜 지금 이 방향을 보고 있는지`를 실제 진입과 같은 이유로 설명해야 한다
- ML이 이후 threshold를 미세조정하더라도 체크와 진입이 함께 움직여야 한다

즉 이번 설계는 `체크를 painter 쪽에서 따로 똑똑하게 만드는 것`이 아니라, `Consumer가 만든 실행 의도를 chart와 entry가 같이 공유`하는 구조다.

현재 baseline snapshot:

- [consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md)

## 2. 수정된 전제

이전의 `check-first display gate` 초안은 방향 자체는 맞지만, painter 쪽 display owner가 너무 강해질 위험이 있었다.

사용자 의도는 더 정확히 이쪽이다.

- `Position -> Response Raw -> Response -> State -> Evidence -> Belief -> Barrier -> Forecast -> Observe/Confirm/Action -> Consumer`
- 이 전체 단계들을 거쳐 형성된 최종 실행 의도가
  - 차트에서는 체크로 먼저 보이고
  - entry에서는 더 높은 문턱을 통과할 때 진입으로 이어져야 한다

따라서 새로운 원칙은:

- `체크 = Consumer pre-entry state`
- `진입 = 같은 Consumer chain의 higher gate pass`

이다.

## 3. 현재 체인과 owner

### 3.1 Semantic identity / readiness chain

이 체인은 현재 문서 기준으로 이미 고정돼 있다.

- `Position`
- `Response Raw`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`
- `Forecast`
- `Observe/Confirm/Action`
- `Consumer`

관련 기준:

- [chart_flow_buy_wait_sell_guide_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\chart_flow_buy_wait_sell_guide_ko.md)

핵심 원칙:

- 방향 정체성은 상류 semantic chain이 만든다
- `Consumer`는 실행 가능성과 block 이유를 붙인다
- chart는 이 체인을 다시 그림으로 번역해야지, 별도 의미를 만들면 안 된다

### 3.2 현재 코드 owner

- semantic routing:
  - `backend/trading/engine/core/observe_confirm_router.py`
- execution / consumer:
  - `backend/services/entry_service.py`
  - `backend/services/entry_try_open_entry.py`
- consumer contract:
  - `backend/services/consumer_contract.py`
- chart translation:
  - `backend/trading/chart_painter.py`
- ML assist / rollout gate:
  - `ml/semantic_v1/promotion_guard.py`

## 4. 핵심 설계 원칙

### 4.1 체크는 Consumer 밖에서 새로 만들지 않는다

체크 표기를 좋게 만들고 싶어도, 의미 owner를 painter로 옮기면 안 된다.

허용:

- Consumer가 만든 pre-entry 상태를 chart가 먼저 보여주는 것

비허용:

- painter가 router/consumer와 별개로 BUY/SELL side를 새로 정하는 것
- chart에만 존재하는 display-only 의미를 만드는 것

### 4.2 display floor와 entry floor는 분리하되 같은 owner가 계산한다

`display floor` 자체는 여전히 필요하다. 하지만 계산 위치가 중요하다.

잘못된 방식:

- painter가 따로 display floor를 계산

맞는 방식:

- Consumer가
  - `check_display_ready`
  - `entry_ready`
  를 같은 payload에서 함께 계산

즉 floor는 2개지만 owner는 1개다.

### 4.3 ML은 같은 Consumer floor를 보정한다

ML이 나중에 adaptive tuning을 하더라도, 아래를 직접 바꾸면 안 된다.

- side identity
- setup identity
- archetype identity

ML이 보정할 수 있는 것은:

- `display threshold delta`
- `entry threshold delta`
- `strength boost`
- `wait bias / hold bias`

즉 ML은 same-chain modifier여야 한다.

## 5. 목표 구조

### 5.1 새 canonical payload

entry_service가 기존 `entry_decision_result_v1`와 별도로, 혹은 그 안에 embedded 형태로 아래 payload를 만든다.

- `consumer_check_state_v1.contract_version`
- `consumer_check_state_v1.check_candidate`
- `consumer_check_state_v1.check_display_ready`
- `consumer_check_state_v1.entry_ready`
- `consumer_check_state_v1.check_side`
- `consumer_check_state_v1.check_stage`
  - `OBSERVE`
  - `PROBE`
  - `READY`
  - `BLOCKED`
- `consumer_check_state_v1.check_reason`
- `consumer_check_state_v1.entry_block_reason`
- `consumer_check_state_v1.semantic_origin_reason`
- `consumer_check_state_v1.consumer_guard_result`
- `consumer_check_state_v1.consumer_block_kind`
- `consumer_check_state_v1.consumer_block_source_layer`
- `consumer_check_state_v1.ml_threshold_assist_applied`
- `consumer_check_state_v1.display_strength_level`

핵심은:

- chart와 entry가 같은 payload를 본다
- chart는 `check_display_ready`
- entry는 `entry_ready`

를 각각 사용한다.

### 5.2 check stage 해석

권장 해석:

- `OBSERVE`
  - 방향성은 있지만 아직 probe candidate까지는 약함
- `PROBE`
  - scene/probe candidate는 있음, 아직 entry 미달
- `READY`
  - entry 직전
- `BLOCKED`
  - 방향은 살아 있지만 현재 실행 block이 걸려 있음

이 stage는 나중에 painter event로 번역된다.

## 6. chart와 entry 연결 방식

### 6.1 chart owner

`chart_painter.py`는 앞으로 아래를 우선 사용한다.

- `consumer_check_state_v1.check_side`
- `consumer_check_state_v1.check_stage`
- `consumer_check_state_v1.check_display_ready`
- `consumer_check_state_v1.display_strength_level`

변환 규칙 예시:

- `PROBE + BUY + display_ready`
  - `BUY_PROBE`
- `OBSERVE + BUY + display_ready`
  - `BUY_WAIT`
- `READY + SELL + display_ready`
  - `SELL_READY`
- `BLOCKED + BUY + display_ready=false`
  - `WAIT`

즉 chart는 더 이상 raw scattered reason을 직접 많이 해석하지 않고, canonical consumer check payload를 우선 읽는다.

### 6.2 entry owner

entry는 기존처럼 `entry_ready=true`일 때만 실제 action으로 간다.

즉:

- `check_display_ready=true`
- `entry_ready=false`

는 아주 자연스러운 상태가 된다.

이 경우 차트 체크는 의미가 있고, entry는 아직 안 간다.

## 7. ML 연결 방식

### 7.1 현재 바른 연결점

ML은 `Observe/Confirm/Action`을 새로 만들지 않는다.

대신 Consumer 단계에서 아래를 보정한다.

- timing probability
- entry_quality probability
- threshold-only assist
- future partial-live assist

### 7.2 원하는 자동 미세조정과의 연결

사용자가 원하는 `시간대/상황대에 맞는 느낌으로 체크와 진입이 같이 조정`되려면:

- ML이 painter를 직접 건드리면 안 된다
- ML이 Consumer floor를 보정해야 한다

즉 구조는 아래와 같아야 한다.

1. semantic chain이 side/scene/meaning 생성
2. Consumer가 `check_display_ready`와 `entry_ready`를 같이 계산
3. ML은 그 floor를 같은 방향으로 보정
4. chart와 entry는 같은 결과를 서로 다른 stage로 소비

이렇게 해야 학습 결과가 누적될수록

- 체크가 뜨는 자리
- READY로 올라가는 자리
- 실제 진입 자리

가 같은 체계 안에서 같이 이동한다.

## 8. 1차 적용 범위

### 8.1 NAS100 우선

현재 NAS에서 드러난 문제:

- scene은 `nas_clean_confirm_probe`
- observe reason은 이미 directional
- 하지만 `probe_pair_gap_not_ready` 때문에 entry가 막히면서 차트도 약하게 밀림

이건 가장 좋은 1차 적용 대상이다.

1차 목표:

- NAS scene에서 `check_display_ready=true`, `entry_ready=false` 상태를 제대로 surface
- chart에서 directional check가 먼저 보이게 함
- 실제 entry 기준은 유지

### 8.2 XAU/BTC는 2차

- XAU는 current side consistency가 아직 흔들림
- BTC는 duplicate / hold / exit follow-up과 섞일 수 있음

따라서 1차는 NAS 한정이 맞다.

## 9. 구현 단계

### Step A. Consumer payload baseline snapshot

실제 row에서 아래를 함께 고정한다.

- `observe_reason`
- `probe_scene_id`
- `core_reason`
- `consumer_guard_result`
- `blocked_by`
- `action_none_reason`
- 현재 chart event

### Step B. `consumer_check_state_v1` contract 추가

대상:

- `backend/services/entry_service.py`

### Step C. Consumer-side floor 계산

동일 owner에서 둘 다 계산한다.

- `check_display_ready`
- `entry_ready`

### Step D. chart translation 연결

대상:

- `backend/trading/chart_painter.py`

chart는 새 payload를 우선 읽고, 없으면 기존 fallback을 쓴다.

### Step E. NAS scene rollout

- `nas_clean_confirm_probe`
- `probe_pair_gap_not_ready`
- `probe_forecast_not_ready`

케이스부터 적용

### Step F. 회귀와 재관측

- runtime reason
- chart event
- distribution / rollout
- semantic runtime reason

모순 여부 확인

## 10. 테스트 포인트

### 10.1 entry_service

- same row에서 `check_display_ready=true`, `entry_ready=false`가 가능해야 함
- `probe_against_default_side`는 둘 다 false
- `execution_soft_blocked`는 display 가능, entry 불가
- `policy_hard_blocked`는 둘 다 false

### 10.2 chart_painter

- `consumer_check_state_v1` 기반으로 directional check가 그려짐
- 기존 entered precursor와 충돌하지 않음
- fallback 없는 경우에도 기존 해석이 깨지지 않음

### 10.3 NAS focused regression

- `nas_clean_confirm_probe + probe_pair_gap_not_ready`
  - chart: directional check visible
  - entry: still blocked

## 11. 완료 기준

- 체크와 entry가 같은 Consumer 체인에서 설명된다
- `왜 체크가 떴는지`와 `왜 아직 진입은 아닌지`가 같은 row에서 동시에 읽힌다
- ML threshold assist가 들어와도 chart/event 의미가 따로 놀지 않는다
- NAS 1차 rollout에서 check timing이 개선되지만 false-ready는 늘지 않는다
