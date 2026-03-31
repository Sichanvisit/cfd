# Consumer-Coupled Check / Entry Scene Refinement
## S5. Symbol Balance Tuning Spec

### 목적

S5의 목적은
이미 구축된 `consumer_check_state_v1 + late reconciliation + 7-stage display`
구조를 유지한 채,
`BTCUSD / NAS100 / XAUUSD`의 체크 밀도와 family balance를
사용자 체감상 더 자연스럽게 맞추는 것이다.

즉 S5는 새 체계를 만드는 단계가 아니다.

- 어떤 symbol은 너무 많이 뜨고
- 어떤 symbol은 너무 약하게 뜨고
- 어떤 symbol은 family가 한쪽으로만 몰리는

현재 imbalance를 미세조정하는 단계다.

---

### 왜 필요한가

S4까지 오면서 아래는 이미 정리됐다.

- must-show / must-hide casebook
- visually similar scene alignment audit
- consumer check state contract refinement
- late reconciliation bug 수정
- `display_score -> repeat_count` 사다리 연결

하지만 runtime recent window를 다시 보면,
현재 문제는 구조 버그보다 `symbol balance`에 가깝다.

대표적으로:

- `BTCUSD`
  - `lower_rebound_probe_observe`가 여전히 `BUY PROBE` 비중이 높다
- `NAS100`
  - `lower_rebound_confirm` blocked는 잘 숨겨지지만
  - 최근 window에서는 `outer_band_reversal_support_required_observe`가 주로 남는다
- `XAUUSD`
  - `upper_reject_probe_observe`와 `outer_band / middle anchor` family의 체감 비율이 아직 어색할 수 있다

즉 이제 남은 건
`scene contract` 자체보다
`scene family가 symbol별로 얼마나 자주, 얼마나 강하게 보이는가`
를 다듬는 일이다.

---

### 범위

이번 S5에서 다루는 것:

- symbol별 `scene family` 노출 빈도
- symbol별 `stage` 비율
- symbol별 `display_score / repeat_count` band
- symbol별 family suppression / downgrade / reduce tuning
- tri-symbol recent window 기준 상대 밀도 균형

이번 S5에서 하지 않는 것:

- painter shape/size/color 재설계
- chart 7-stage ladder 기준 자체 변경
- semantic ML threshold / promotion rule 수정
- chart_flow 공통 policy 대규모 재작성

즉 S5는
`scene selection 이후의 symbol-level balance tuning`
단계다.

---

### 직접 owner

#### 1. core balance owner

- `backend/services/consumer_check_state.py`
- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`

#### 2. translation observer

- `backend/trading/chart_painter.py`

#### 3. analysis input

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`

---

### S5 입력 문서

S5는 아래를 직접 입력으로 사용한다.

- `consumer_coupled_check_entry_scene_refinement_s4_consumer_check_state_contract_refinement_reconfirm_memo_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_ko.md`

즉 S5는 새 가설을 많이 만들기보다,
S4 이후 남은 runtime imbalance를 symbol별로 다듬는 단계다.

---

### 현재 기준 핵심 imbalance

#### 1. BTCUSD

현재 주요 family:

- `lower_rebound_probe_observe`
- `blocked_by=forecast_guard`
- `action_none_reason=probe_not_promoted`
- `stage=PROBE`

해석:

- 여전히 buy-side probe family가 강하게 남는다
- 구조적으로는 의미가 있지만
- 체감상 과다할 수 있다

S5 방향:

- 완전 hide보다
- `PROBE -> OBSERVE` downgrade 또는 cadence reduction을 우선 검토

#### 2. NAS100

현재 주요 family:

- `outer_band_reversal_support_required_observe`
- `blocked_by=outer_band_guard`
- `action_none_reason=probe_not_promoted`
- `stage=OBSERVE`

해석:

- S4 이후 lower rebound blocked family는 잘 내려왔지만
- 최근엔 structural observe family가 주 표면이 됐다
- 즉 `너무 눌린 lower rebound`와 `상대적으로 남는 structural observe`의 균형을 다시 봐야 한다

S5 방향:

- `outer_band structural observe`를 유지하되
- lower rebound family가 너무 죽는다면 약한 reopen rule도 검토

#### 3. XAUUSD

현재 주요 family:

- `upper_reject_probe_observe`
- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `upper_reject_confirm`

해석:

- XAU는 family 종류가 더 다양하게 섞인다
- 그래서 `한쪽 family만 과하게 남는지`, `reconciliation이 충분한지`를 같이 봐야 한다

S5 방향:

- `upper reject`
- `outer band`
- `middle anchor`

세 family 사이의 비율과 cadence를 맞춘다

---

### S5의 핵심 contract 질문

#### 1. symbol별 family 노출 상한

- 한 recent window에서 같은 family가 몇 번까지 허용되는가
- symbol별 cadence window가 필요한가

#### 2. symbol별 stage band

- 같은 family라도
  - `BTC`는 `PROBE`
  - `NAS`는 `OBSERVE`
  - `XAU`는 `BLOCKED`
  로 갈리는 게 맞는가

#### 3. symbol별 must-show vs must-hide 우선순위

- `BTC`는 leakage suppression이 더 우선인가
- `NAS`는 reopen이 더 우선인가
- `XAU`는 family balance가 더 우선인가

#### 4. relative density acceptance

- 각 symbol이 절대 같은 개수를 찍어야 하는가
- 아니면 family / stage 비율만 과하지 않으면 되는가

S5에서는 후자를 기본 원칙으로 둔다.

즉 `절대 동일 개수`보다
`과도한 imbalance를 줄이는 것`이 목표다.

---

### 우선 refinement 방향

#### A. BTC probe family soft suppression

대상:

- `lower_rebound_probe_observe`
- `BUY`
- `forecast_guard / barrier_guard`
- `probe_not_promoted`

방향:

- `PROBE -> OBSERVE` downgrade 우선 검토
- 또는 repeat_count를 2에서 1로 고정
- 또는 cadence suppression

#### B. NAS lower rebound reopen vs structural observe balance

대상:

- `lower_rebound_confirm`
- `lower_rebound_probe_observe`
- `outer_band_reversal_support_required_observe`

방향:

- lower rebound family가 너무 죽는지 확인
- 필요하면 약한 observe reopen
- structural observe가 과하면 cadence reduction

#### C. XAU multi-family balance

대상:

- `upper_reject_probe_observe`
- `upper_reject_confirm`
- `middle_sr_anchor_required_observe`
- `outer_band_reversal_support_required_observe`

방향:

- upper reject family internal consistency 유지
- middle anchor는 cadence 과다만 줄임
- outer band family가 과도하면 reduce

---

### acceptance 기준

S5는 아래가 충족되면 완료로 본다.

#### 1. BTC

- recent window에서 동일 lower probe family가 과도하게 반복되지 않는다
- `PROBE` 비율이 줄거나 체감상 덜 공격적으로 보인다

#### 2. NAS

- lower family와 structural family의 균형이 더 자연스럽다
- “아예 안 보이는” 쪽이나 “한 family만 계속 보이는” 쪽이 완화된다

#### 3. XAU

- 특정 family만 압도적으로 도배되지 않는다
- upper reject / middle anchor / outer band family가 더 일관되게 읽힌다

#### 4. 공통

- chart 체감과 runtime reason이 더 잘 맞는다
- `BLOCKED / OBSERVE / PROBE`가 symbol별로 과도하게 쏠리지 않는다

---

### 원칙

#### 1. 공통 ladder는 유지

- `70 / 80 / 90`
- `1 / 2 / 3 repeat`

이 기준은 바꾸지 않는다.

#### 2. painter는 owner가 아니다

조정은 upstream contract에서 한다.

#### 3. symbol override는 마지막 수단

가능하면 공통 family rule에서 먼저 조정하고,
정말 필요할 때만 symbol-specific exception을 넣는다.

#### 4. hide보다 downgrade를 우선

보여줄 가치가 있는 family는
완전 hide보다
`PROBE -> OBSERVE`
또는 `repeat 감소`
를 먼저 검토한다.

---

### 다음 구현 방향

S5는 아래 순서로 구현하는 것이 맞다.

1. symbol balance baseline snapshot
2. BTC probe density casebook
3. NAS reopen/balance casebook
4. XAU multi-family balance casebook
5. least-invasive tuning rule 선택
6. code implementation
7. runtime re-observe
8. reconfirm memo
