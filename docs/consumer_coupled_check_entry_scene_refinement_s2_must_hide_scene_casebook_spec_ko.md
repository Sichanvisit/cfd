# Consumer-Coupled Check/Entry Scene Refinement
## S2. Must-Hide Scene Casebook Spec

### 목적

S2의 목적은
`사용자가 보기에 체크가 남으면 안 되는 장면`
을 문서와 사례 기준으로 고정하는 것이다.

현재 S0/S1 기준으로 가장 명확한 문제는:

- `BTCUSD`와 `NAS100`의 하단 반등 family가
  진입은 막히는데도 너무 강하게 반복 표시되는 것

이다.

즉 S2는 must-show를 여는 단계가 아니라,
`leakage를 줄이고 must-hide 장면을 잠그는 단계`
다.

---

### 왜 필요한가

현재 사용자가 강하게 느끼는 문제 중 하나는 아래다.

- “계속 내려가는데 buy 가능성 표기가 너무 많다”
- “진입은 안 되는데 차트가 너무 낙관적으로 보인다”
- “blocked인데도 계속 strong probe처럼 남는다”

이 문제는 painter 문제가 아니라,
scene가 `display-worthy`로 너무 넓게 남는 contract 문제다.

따라서 S2는
`어떤 장면은 hidden 또는 더 약한 단계로 내려가야 한다`
를 casebook으로 먼저 고정하는 단계다.

---

### 범위

이번 S2는 아래만 다룬다.

- `must-hide leakage` 정의
- recent runtime row 기반 leakage case 수집
- family별 leakage 패턴 정리
- `hidden`, `OBSERVE downgrade`, `repeat count reduction` 후보 분리
- 향후 S4 contract refinement에 넣을 suppression 후보 정리

이번 단계에서 하지 않는 것:

- must-show scene 확장
- visually similar scene alignment 자체 판단
- threshold / display ladder 숫자 변경
- painter shape/size 변경

즉 “숨겨야 하는 장면 정의와 사례 고정”까지만 한다.

---

### 직접 owner

- scene / check owner
  - `backend/services/entry_service.py`
  - `backend/services/consumer_check_state.py`
  - `backend/services/entry_try_open_entry.py`
- chart translation owner
  - `backend/trading/chart_painter.py`
- 관찰 입력
  - `data/trades/entry_decisions.csv`
  - `data/runtime_status.json`
  - `data/analysis/chart_flow_distribution_latest.json`

---

### must-hide scene의 정의

S2에서 말하는 `must-hide scene`은 아래 조건을 만족하는 장면이다.

1. 실제 진입은 명확히 막혀 있다
2. 사용자가 차트상으로 보기에도 계속 같은 방향을 강조하면 오해를 만든다
3. 현재 표기가 구조적 관찰보다는 leakage에 가깝다
4. hidden 또는 더 약한 단계로 내려가는 것이 더 자연스럽다

즉 must-hide는
`display-worthy가 아니다`
또는
`현재 단계보다 낮춰야 한다`
를 뜻한다.

---

### must-hide가 기대하는 처리 방식

S2에서는 must-hide case를 아래 셋 중 하나로 처리 후보를 잡는다.

#### 1. full hide

- `display=false`
- 체크를 남기지 않는다

#### 2. stage downgrade

- `PROBE -> OBSERVE`
- `READY -> PROBE`
- 강한 단계만 낮춘다

#### 3. repeat reduction

- stage는 유지하되
- 반복 개수(`2개`, `3개`)를 줄인다

즉 S2는 무조건 숨기기만 하는 게 아니라,
`완전 hide / 약화 / 반복 축소`
를 구분한다.

---

### S2에서 우선 수집할 leakage family

#### 1. lower rebound probe leakage

대표 reason:

- `lower_rebound_probe_observe`
- `probe_not_promoted`
- `barrier_guard`
- `probe_promotion_gate`

대표 심볼:

- `BTCUSD`
- `NAS100`

#### 2. structural observe over-display

대표 reason:

- `outer_band_reversal_support_required_observe`
- `probe_not_promoted`
- `outer_band_guard`

이 family는 must-show와 must-hide 경계가 애매할 수 있으므로
repeat reduction 또는 stage downgrade 후보로 본다.

#### 3. blocked confirm leakage

대표 reason:

- `lower_rebound_confirm`
- `energy_soft_block`
- `execution_soft_blocked`

이 family는 hidden이 맞는지,
아니면 observe downgrade가 맞는지 S2에서 가른다.

---

### casebook 한 건에 반드시 남길 항목

각 must-hide case는 아래 형식으로 정리한다.

1. `case_id`
2. `symbol`
3. `chart_time`
4. `scene_family`
5. `user_chart_impression`
6. `current_display`
7. `expected_suppression`
8. `runtime_observe_reason`
9. `blocked_by`
10. `action_none_reason`
11. `probe_scene_id`
12. `consumer_check_stage`
13. `consumer_check_display_ready`
14. `consumer_check_display_score`
15. `consumer_check_display_repeat_count`
16. `entry_ready`
17. `why_must_hide`

---

### S2 case 분류 원칙

모든 case는 아래 셋 중 하나로 분류한다.

#### 1. hide

- 완전히 숨기는 쪽이 맞는 경우

#### 2. downgrade

- 완전 hidden보다 단계만 낮추는 게 맞는 경우

#### 3. reduce

- stage는 유지하되 repetition이나 강도만 줄이면 되는 경우

---

### S2의 핵심 질문

S2는 아래 질문에 답할 수 있어야 한다.

1. 어떤 장면이 실제로 leakage인가
2. 그 leakage는 hidden이 맞는가, downgrade가 맞는가, repeat reduction이 맞는가
3. `BTCUSD`와 `NAS100`의 lower rebound family는 어디까지 보여줘야 하는가
4. `blocked confirm` family는 hidden이 맞는가, must-show와 충돌하는가
5. S4 contract refinement에서 어떤 suppression rule을 추가해야 하는가

---

### 완료 기준

아래가 만족되면 S2는 완료로 본다.

- leakage family별 case가 최소 2건 이상 있다
- 각 case에 suppression 방향(`hide / downgrade / reduce`)이 있다
- `BTCUSD`와 `NAS100`의 대표 leakage case가 정리돼 있다
- S4 contract refinement에 바로 넘길 suppression candidate list가 있다

---

### 다음 단계 연결

- S3: visually similar scene alignment audit
- S4: consumer_check_state contract refinement

즉 S2는
`숨겨야 하는 장면 정의`
를 먼저 고정해 주는 단계다.
