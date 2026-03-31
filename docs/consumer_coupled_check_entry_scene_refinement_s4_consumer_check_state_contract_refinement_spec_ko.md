# Consumer-Coupled Check/Entry Scene Refinement
## S4. Consumer Check State Contract Refinement Spec

### 목적

S4의 목적은
S1/S2/S3에서 정리한 casebook 결과를
실제 `consumer_check_state_v1` 계약과 downstream 적용 규칙으로 내리는 것이다.

즉 S4는 다음을 문서 수준이 아니라 contract 수준으로 고정하는 단계다.

- 무엇을 must-show로 남길지
- 무엇을 must-hide로 내릴지
- 어떤 divergence는 유지하고
- 어떤 divergence는 stage/display 수준에서 더 정렬할지

한 줄로 말하면,
S4는 `casebook -> rule contract` 변환 단계다.

---

### 왜 필요한가

현재까지는 아래가 준비됐다.

- `S0`: baseline snapshot
- `S1`: must-show scene casebook
- `S2`: must-hide scene casebook
- `S3`: visually similar scene alignment audit

하지만 지금 상태로는 아직
“무엇을 어떻게 바꿀지”가 문서 설명에 머물러 있다.

실제 시스템이 바뀌려면
아래 owner에서 어떤 contract를 바꿀지 명시해야 한다.

- `consumer_check_state_v1`
- late reconciliation
- chart translation input
- symbol-specific exception boundary

즉 S4는
`설명 가능한 기준`을
`실행 가능한 규칙`으로 바꾸는 단계다.

---

### 범위

이번 S4는 아래만 다룬다.

- `consumer_check_state_v1` 생성/보정 contract
- `entry_service -> entry_try_open_entry` 사이 late reconciliation contract
- `display_score / display_repeat_count`를 어느 시점에 어떻게 재계산할지
- must-show / must-hide / alignment case에 대한 stage/display rule
- symbol-specific exception을 어디까지 허용할지

이번 단계에서 하지 않는 것:

- painter shape/size/style 재설계
- chart_flow 전체 policy 재작성
- semantic ML gate 수정
- runtime rollout mode 변경

즉 S4는
`scene -> consumer_check_state -> chart translation`
사이의 계약만 다룬다.

---

### 직접 owner

#### 1. core contract owner

- `backend/services/consumer_check_state.py`
- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`

#### 2. translation owner

- `backend/trading/chart_painter.py`

#### 3. supporting context owner

- `backend/trading/engine/core/observe_confirm_router.py`

---

### S4 입력 문서

S4는 아래 문서를 직접 입력으로 사용한다.

- `consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_ko.md`

즉 S4는 새로 가설을 만드는 단계가 아니라,
이미 분류된 사례를 규칙화하는 단계다.

---

### 이번 S4에서 다룰 핵심 contract 질문

#### 1. check candidate 생성 조건

- 어떤 scene가 `check_candidate=true`가 되어야 하는가
- 어떤 scene는 아예 candidate가 되면 안 되는가

#### 2. display ready 조건

- 어떤 blocked/probe scene은 `display_ready=true`를 유지할 것인가
- 어떤 blocked/probe scene은 `display_ready=false`로 내릴 것인가

#### 3. stage 결정 조건

- `OBSERVE`
- `PROBE`
- `READY`
- `BLOCKED`

를 어떤 family에서 어떻게 배정할 것인가

#### 4. display ladder 입력

- `display_score`
- `display_repeat_count`

를 stage만으로 결정할지,
scene family와 blocked context를 함께 볼지

#### 5. late reconciliation 범위

- upstream에서 만든 stage/display를
late block가 어디까지 덮어쓸 수 있는가

---

### 현재 contract candidate 요약

#### from S1

- `XAU upper_reject_probe_observe + energy_soft_block`
  - blocked라도 약한 observe를 남길지 검토
- `NAS lower_rebound_confirm + energy_soft_block`
  - debatable must-show candidate
- `middle_sr_anchor_required_observe`
  - middle must-show 최소 조건 정리 필요

#### from S2

- `BTC structural lower-buy observe`
  - hide 후보
- `NAS lower rebound probe`
  - downgrade 후보
- `XAU middle anchor observe`
  - repeat/cadence reduce 후보
- `XAU upper reject probe`
  - defer family

#### from S3

- `BTC lower structural observe` vs `NAS blocked lower confirm`
  - partial alignment candidate
- `BTC/NAS` vs `XAU conflict`
  - intentional divergence, 분리 유지
- `XAU upper_reject_probe` vs `upper_reject_confirm`
  - accidental divergence candidate

---

### S4에서 우선 고정할 refinement 방향

#### A. BTC lower structural observe suppression

현재:

- `outer_band_reversal_support_required_observe`
- `outer_band_guard`
- `probe_not_promoted`
- `OBSERVE`
- `display=true`

방향:

- 같은 signature 반복 시 hide
- 최소 첫 1회만 허용하거나 cadence suppression 도입

#### B. NAS lower rebound probe downgrade

현재:

- `lower_rebound_probe_observe`
- `probe_promotion_gate`
- `probe_not_promoted`
- `PROBE`
- `display_score=0.86`
- `repeat=2`

방향:

- `PROBE -> OBSERVE`
- `0.86 -> 0.75`
- `repeat 2 -> repeat 1`

#### C. XAU middle anchor cadence reduction

현재:

- `middle_sr_anchor_required_observe`
- `middle_sr_anchor_guard`
- `observe_state_wait`
- `OBSERVE`
- `display=true`

방향:

- stage 유지
- display cadence만 줄임

#### D. XAU upper reject family reconciliation

현재:

- `upper_reject_probe_observe`
  - `display=true`
- `upper_reject_confirm`
  - `display=false`

방향:

- 같은 family 내부에서 너무 급격히 갈리지 않게
- confirm도 약한 observe로 남길지 검토

---

### S4 contract 수정 대상 필드

아래 필드를 직접 수정 대상으로 본다.

- `check_candidate`
- `check_display_ready`
- `check_stage`
- `check_side`
- `check_reason`
- `entry_block_reason`
- `blocked_display_reason`
- `display_strength_level`
- `display_score`
- `display_repeat_count`

즉 S4는
`consumer_check_state_v1`의 내용 자체를 다듬는 단계다.

---

### 우선 적용 원칙

#### 1. family rule 우선

- generic string match보다
- scene family contract를 우선 적용한다

#### 2. global rule 우선, symbol exception 최소화

- 먼저 공통 규칙으로 해결
- 정말 필요한 경우만 symbol-specific exception

#### 3. must-show와 must-hide 충돌 시 defer bucket 유지

- 예: `XAU upper reject family`
- 이런 family는 숨기거나 열기 한쪽으로 바로 확정하지 않는다

#### 4. stage와 display를 같이 조정

- stage만 바꾸고 score/repeat를 그대로 두면 안 된다
- `OBSERVE/PROBE/READY`와 `display_score/repeat_count`가 같이 움직여야 한다

---

### acceptance 기준

S4 완료 시 아래가 만족돼야 한다.

- S1/S2/S3 case가 실제 contract rule로 맵핑된다
- 같은 family 안에서 stage/display가 더 설명 가능해진다
- accidental divergence가 줄어든다
- intentional divergence는 그대로 유지된다
- 이후 S5 symbol balance tuning이 family-level이 아니라 값 미세조정 수준으로 내려간다

---

### 다음 단계 연결

- S5: symbol balance tuning
- acceptance / runtime re-observe

즉 S4가 끝나면
큰 의미 contract는 닫히고,
남는 건 symbol-level balancing이 된다.
