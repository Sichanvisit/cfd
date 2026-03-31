# Consumer-Coupled Check/Entry Scene Refinement
## S1. Must-Show Scene Casebook Spec

### 목적

S1의 목적은
`사용자가 보기에 체크가 반드시 있어야 하는 장면`
을 문서와 사례 기준으로 고정하는 것이다.

현재 S0 baseline에서는:

- `must-hide leakage`는 비교적 자동 추출이 잘 되었고
- `visually similar divergence`도 seed를 확보했지만
- `must-show missing`은 recent row 자동 추출만으로는 충분히 잡히지 않았다

즉 S1은 데이터 자동 집계만으로는 부족하고,
실제 차트 screenshot과 최근 row를 같이 묶는
`manual + runtime hybrid casebook`
이 필요하다.

---

### 왜 필요한가

현재 사용자가 가장 강하게 느끼는 불일치 중 하나는 아래다.

- “여긴 분명 체크가 약하게라도 떠야 하는데 안 뜬다”
- “진입까지는 아니어도 관찰 표시는 남아 있어야 한다”

이 문제는 단순 threshold 문제가 아니라,
현재 scene contract에
`must-show scene`
정의가 아직 충분히 잠기지 않았기 때문에 생긴다.

즉 S1은
`어떤 장면은 반드시 표시 대상이어야 한다`
를 먼저 고정하는 단계다.

---

### 범위

이번 S1은 아래만 다룬다.

- `must-show scene` 정의
- screenshot/manual case 수집
- 해당 case의 runtime row/reason/stage/display 매핑
- `must-show`의 최소 display expectation 정의
- 향후 S4 contract refinement에 들어갈 candidate scene 목록 정리

이번 단계에서 하지 않는 것:

- must-hide scene 조정
- leakage suppression 조정
- symbol override 직접 수정
- painter shape/size/offset 조정
- display ladder threshold 수정

즉 “보여야 하는 장면 정의와 사례 고정”까지만 한다.

---

### 직접 owner

- scene meaning owner
  - `backend/services/entry_service.py`
  - `backend/services/consumer_check_state.py`
  - `backend/services/entry_try_open_entry.py`
- chart translation owner
  - `backend/trading/chart_painter.py`
- 관찰 입력
  - 사용자 screenshot
  - `data/trades/entry_decisions.csv`
  - `data/runtime_status.json`
  - `data/analysis/chart_flow_distribution_latest.json`

---

### must-show scene의 정의

S1에서 말하는 `must-show scene`은 아래 조건을 만족하는 장면이다.

1. 실제 진입 ready는 아니어도 된다
2. 방향성은 최소한 약하게라도 존재해야 한다
3. 사용자가 차트상으로 구조적 자리라고 인식할 수 있다
4. runtime row에서도 완전 generic noise가 아니라 scene identity가 설명 가능해야 한다

즉 must-show는
`entry-ready`
가 아니라
`display-worthy`
를 뜻한다.

---

### must-show가 기대하는 최소 결과

must-show scene은 기본적으로 아래 중 하나로 남아야 한다.

- `OBSERVE + display=true`
- `WATCH / WAIT` 계열의 약한 체크
- 필요 시 `PROBE`

반대로 아래는 must-show 실패로 본다.

- `display=false`
- `check_candidate=false`
- 방향성이 완전히 사라짐
- generic neutral `WAIT`로만 묻힘

즉 must-show의 최소 acceptance는:

- “강한 체크까지는 아니어도 약한 directional check는 남아야 한다”

이다.

---

### S1에서 우선 수집할 scene family

아래 family를 우선 must-show 후보로 본다.

#### 1. lower rebound family

- 하단 edge 접근 후 반등 시도
- 예:
  - `lower_rebound_probe_observe`
  - `lower_rebound_confirm`
  - `outer_band_reversal_support_required_observe`

#### 2. upper reject family

- 상단 edge 접근 후 reject 시도
- 예:
  - `upper_reject_probe_observe`
  - `upper_reject_confirm`
  - `upper_break_fail_confirm`

#### 3. middle reclaim / middle reject family

- 중간 회귀/재진입 자리에서 관찰이 필요한 장면
- 예:
  - `middle_sr_anchor_required_observe`
  - 구조적 middle reclaim watch

#### 4. edge watch family

- 진입은 아니지만 관찰을 끊으면 안 되는 구조적 watch
- 예:
  - `*_watch`
  - edge 접근 + side clear + noise not extreme

---

### casebook 한 건에 반드시 남길 항목

각 must-show case는 아래 형식으로 정리한다.

1. `case_id`
2. `symbol`
3. `chart_time`
4. `scene_family`
5. `user_chart_impression`
6. `expected_min_display`
7. `runtime_observe_reason`
8. `blocked_by`
9. `action_none_reason`
10. `probe_scene_id`
11. `consumer_check_stage`
12. `consumer_check_display_ready`
13. `consumer_check_display_score`
14. `entry_ready`
15. `current_status`
16. `why_must_show`

---

### S1 case 분류 원칙

모든 case는 아래 셋 중 하나로 분류한다.

#### 1. good

- 현재도 must-show 기대를 만족하는 경우

#### 2. missing

- 현재는 숨겨져 있거나 너무 약하게 눌려 있는 경우

#### 3. debatable

- 사용자 체감상 떠야 해 보이지만,
  실제론 generic noise일 가능성도 있어 추가 판단이 필요한 경우

---

### S1의 핵심 질문

S1은 아래 질문에 답할 수 있어야 한다.

1. 사용자가 “여긴 떠야 한다”고 느끼는 장면은 어떤 family에 속하는가
2. 그 장면은 현재 runtime에서 어떤 reason/guard/stage로 읽히는가
3. 그 장면은 정말 must-show인가, 아니면 debatable인가
4. must-show라면 최소 어느 단계까지는 보여야 하는가
5. S4 contract refinement에서 어떤 scene rule을 추가/완화해야 하는가

---

### 완료 기준

아래가 만족되면 S1은 완료로 본다.

- must-show family별 case가 최소 2건 이상 있다
- screenshot/manual case와 runtime row가 연결돼 있다
- 각 case에 `expected_min_display`가 명시돼 있다
- good / missing / debatable 분류가 돼 있다
- 이후 S4에서 바로 scene contract refinement 대상으로 넘길 수 있다

---

### 다음 단계 연결

- S2: must-hide scene casebook
- S3: visually similar scene alignment audit
- S4: consumer_check_state contract refinement

즉 S1은
`보여야 하는 장면 정의`
를 먼저 고정해 주는 단계다.
