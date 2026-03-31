# Consumer-Coupled Check/Entry Scene Refinement
## S3. Visually Similar Scene Alignment Audit Spec

### 목적

S3의 목적은
차트상으로는 비슷하게 보이는데 내부에서는 서로 다른 side / scene / stage로 해석되는 장면을
의도된 divergence와 비의도된 divergence로 나누는 것이다.

현재 S0/S1/S2를 거치며 드러난 핵심은 다음이다.

- `BTCUSD`, `NAS100`은 하락 말단 장면을 `lower rebound buy` family로 자주 읽는다
- `XAUUSD`는 비슷하게 보이는 장면을 `conflict_box_upper_bb20_lower_*` 또는 `upper reject sell` family로 자주 읽는다
- 이 차이가 모두 틀린 것은 아니지만,
  사용자 체감상 지나치게 다르게 보이는 구간이 존재한다

즉 S3는
`비슷한 장면을 어디까지 같은 family로 정렬할 것인가`
를 정하는 단계다.

---

### 왜 필요한가

S1은 `떠야 할 장면`,
S2는 `숨겨야 할 장면`을 정리했다.

하지만 아래 질문은 아직 남아 있다.

- 차트상으로 거의 비슷해 보이는 장면이 왜 심볼마다 정반대로 읽히는가
- 그 divergence는 구조적으로 타당한가
- 아니면 scene contract가 너무 갈라져 있어서 생긴 문제인가

이 문제를 정리하지 않으면,
S4 contract refinement에서

- must-show를 열다가 leakage를 키우거나
- must-hide를 줄이다가 심볼별 해석 균형을 망칠 수 있다

따라서 S3는
`scene alignment의 기준선`
을 만드는 필수 단계다.

---

### 범위

이번 S3는 아래만 다룬다.

- visually similar scene pair / cluster 수집
- pair별 runtime row 비교
- divergence를 일으키는 핵심 feature 축 정리
- intentional vs accidental divergence 분류
- alignment candidate와 non-alignment candidate 분리

이번 단계에서 하지 않는 것:

- scene contract 직접 수정
- threshold 변경
- painter shape/size 수정
- symbol override 직접 수정

즉 “정렬이 필요한지 아닌지”를 판단하는 audit까지만 한다.

---

### 직접 owner

- scene meaning owner
  - `backend/services/entry_service.py`
  - `backend/services/consumer_check_state.py`
  - `backend/services/entry_try_open_entry.py`
- upstream semantic context
  - `backend/trading/engine/core/observe_confirm_router.py`
- 관찰 입력
  - 사용자 screenshot
  - `data/trades/entry_decisions.csv`
  - `data/runtime_status.json`
  - `data/analysis/chart_flow_distribution_latest.json`

---

### visually similar scene의 정의

S3에서 말하는 `visually similar scene`은 아래 조건을 만족하는 pair 또는 cluster다.

1. 사용자가 차트만 보면 같은 family처럼 읽을 수 있다
2. 시간축/위치축에서 구조적으로 유사하다
3. 하지만 내부에서는 side, reason, stage, display가 다르게 나온다

즉 S3는
`차트 체감은 유사한데 semantic output이 다르다`
를 다룬다.

---

### 우선 감사 대상 cluster

#### 1. lower rebound end-of-drop cluster

대표 pair:

- `BTCUSD lower_rebound_probe_observe`
- `NAS100 lower_rebound_probe_observe`
- `XAUUSD conflict_box_upper_bb20_lower_*`

핵심 질문:

- 이 셋은 정말 같은 family로 봐야 하는가
- 아니면 XAU만 다르게 읽는 구조적 이유가 충분한가

#### 2. upper reject / upper conflict cluster

대표 pair:

- `XAUUSD upper_reject_probe_observe`
- `BTCUSD upper reject manual carry-over`

핵심 질문:

- 상단 reject 계열을 심볼별로 너무 다르게 읽고 있지 않은가

#### 3. middle anchor / middle wait cluster

대표 pair:

- `XAUUSD middle_sr_anchor_required_observe`
- `BTC/NAS`의 middle 계열 generic or hidden scene

핵심 질문:

- middle anchor observe를 XAU에서만 과도하게 열고 있지는 않은가

---

### pair 한 건에 반드시 남길 항목

각 alignment audit case는 아래 형식으로 정리한다.

1. `case_id`
2. `cluster_name`
3. `left_symbol`
4. `right_symbol`
5. `chart_similarity_summary`
6. `left_observe_reason`
7. `right_observe_reason`
8. `left_blocked_by`
9. `right_blocked_by`
10. `left_action_none_reason`
11. `right_action_none_reason`
12. `left_probe_scene_id`
13. `right_probe_scene_id`
14. `left_stage`
15. `right_stage`
16. `left_display`
17. `right_display`
18. `left_box_bb_context`
19. `right_box_bb_context`
20. `divergence_axis`
21. `alignment_recommendation`

---

### divergence axis 정의

S3에서는 divergence를 아래 축으로 분리해서 본다.

#### 1. context divergence

- `box_state`
- `bb_state`
- `default_side`
- `context_label`

이 다름 때문에 scene이 달라지는 경우

#### 2. rule divergence

- 같은 context처럼 보이는데
- `observe_reason` / `probe_scene_id` / `blocked_by`가 너무 다르게 갈라지는 경우

#### 3. symbol temperament divergence

- 심볼별 relief / suppression 차이 때문에 결과가 달라지는 경우

#### 4. display translation divergence

- upstream scene은 비슷한데 최종 `consumer_check_stage` / display에서만 크게 달라지는 경우

---

### S3 분류 원칙

모든 pair는 아래 셋 중 하나로 분류한다.

#### 1. intentional divergence

- 실제로 다르게 읽는 게 맞는 경우

#### 2. accidental divergence

- 같은 family로 더 정렬돼야 하는데 현재 contract가 과하게 갈라진 경우

#### 3. partial alignment

- 완전 통일은 아니지만
- 일부 stage / display 수준에서는 더 가까워질 필요가 있는 경우

---

### S3의 핵심 질문

S3는 아래 질문에 답할 수 있어야 한다.

1. 어떤 divergence가 구조적으로 타당한가
2. 어떤 divergence가 사용자가 보기엔 과도한가
3. 같은 family로 묶을 scene은 무엇인가
4. 심볼별 temperament 차이로 남겨야 할 divergence는 무엇인가
5. S4 contract refinement에서 무엇을 통일하고 무엇을 남겨야 하는가

---

### 완료 기준

아래가 만족되면 S3는 완료로 본다.

- visually similar cluster별 case가 최소 2건 이상 있다
- 각 case에 divergence axis가 정리돼 있다
- intentional / accidental / partial alignment 분류가 돼 있다
- S4 contract refinement에 바로 넘길 alignment candidate list가 있다

---

### 다음 단계 연결

- S4: consumer_check_state contract refinement
- S5: symbol balance tuning

즉 S3는
`같은 장면을 어디까지 같은 family로 볼 것인가`
를 정하는 단계다.
