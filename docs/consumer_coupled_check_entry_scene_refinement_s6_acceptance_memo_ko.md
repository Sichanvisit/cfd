# Consumer-Coupled Check / Entry Scene Refinement
## S6. Acceptance Memo

### 목적

S6의 목적은
`S0 ~ S5`까지 진행한 scene refinement 결과를

- `accept and freeze`
- `hold and observe one more window`
- `reopen S5 tuning`
- `reopen S4 contract`

중 무엇으로 볼지 판정하는 것이다.

이번 S6는
immediate window와 rolling recent window를 같이 보고
현재 상태를 숫자와 사례 기준으로 평가했다.

---

### 입력 기준

#### 1. immediate window

- tri-symbol 최근 20 rows

#### 2. rolling recent window

- tri-symbol 최근 100 rows

#### 3. 보조 상태

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

---

### immediate window 결과

#### BTCUSD

최근 20 rows:

- 전부
  - `lower_rebound_probe_observe` 또는
  - `outer_band_reversal_support_required_observe`
- `consumer_check_stage=OBSERVE`
- `consumer_check_display_ready=false`

해석:

- S5 이후 BTC buy-side leakage는 강하게 눌렸다
- 하지만 immediate window 기준으로는
  구조적 lower family가 전부 hidden이라
  `must-show` 관점에서는 과소표시 우려가 생겼다

#### NAS100

최근 20 rows:

- 초반은 `lower_rebound_probe_observe + barrier_guard + probe_not_promoted + PROBE + display=true`
- 후반은 `outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + OBSERVE + display=false`

해석:

- NAS는 immediate window 안에서도
  `강한 lower rebound probe visible`과
  `structural observe hidden`이 같이 섞인다
- 즉 균형은 전보다 좋아졌지만
  아직 `buy-side probe`가 체감상 과할 가능성이 남아 있다

#### XAUUSD

최근 20 rows:

- `outer_band_reversal_support_required_observe + BLOCKED + display=false`
- `middle_sr_anchor_required_observe + OBSERVE + display=true`
- `upper_reject_probe_observe + PROBE + display=true`
- `upper_edge_observe + display=false`

해석:

- XAU는 한 family로만 도배되지는 않는다
- `upper reject / middle anchor / outer band`
  family가 나뉘어 보이므로
  immediate window 기준 multi-family balance는 상대적으로 괜찮다

---

### rolling recent window 결과

#### BTCUSD

최근 100 rows:

- `display_true=0`
- `display_false=100`
- `wrong_ready=0`

주요 family:

- `lower_rebound_probe_observe + barrier_guard + probe_not_promoted + OBSERVE + false` 54
- `lower_rebound_probe_observe + forecast_guard + probe_not_promoted + OBSERVE + false` 27
- `outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + OBSERVE + false` 14

해석:

- leakage suppression은 성공했다
- 하지만 recent 100 rows 기준으론 BTC가 너무 많이 숨겨져 있다
- 즉 `must-hide leak`는 잡혔지만,
  그 대가로 `must-show lower family`까지 같이 사라진 상태에 가깝다

#### NAS100

최근 100 rows:

- `display_true=54`
- `display_false=46`
- `wrong_ready=0`

주요 family:

- `lower_rebound_probe_observe + barrier_guard + probe_not_promoted + PROBE + true` 54
- `lower_rebound_confirm + barrier_guard + observe_state_wait + PROBE + false` 23
- `outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + OBSERVE + false` 21

해석:

- NAS는 BTC와 반대로 여전히 visible lower probe가 많다
- 최근 100 rows에서 `PROBE + true`가 54건이면
  `must-hide leak`는 아니더라도
  symbol balance acceptance로 보기엔 과한 편이다

#### XAUUSD

최근 100 rows:

- `display_true=23`
- `display_false=77`
- `wrong_ready=0`

주요 family:

- `middle_sr_anchor_required_observe + OBSERVE + false` 41
- `conflict_box_upper_bb20_lower_lower_dominant_observe + NONE + false` 18
- `outer_band_reversal_support_required_observe + BLOCKED + false` 13
- `middle_sr_anchor_required_observe + OBSERVE + true` 12
- `upper_reject_probe_observe + PROBE + true` 5

해석:

- XAU는 hidden/visible mix가 비교적 설명 가능하다
- 다만 `middle anchor` 비중이 높아
  다음 tuning 시 cadence를 다시 볼 여지는 남는다

---

### must-show acceptance

판정: `hold`

이유:

- `XAU middle anchor`, `XAU upper reject`는 살아 있다
- `NAS lower rebound family`도 visible이 존재한다
- 하지만 `BTC lower family`는 recent 100 rows 기준 전부 hidden으로 내려가
  must-show 관점에서 과소표시 우려가 크다

즉 must-show는 완전 fail은 아니지만,
BTC 한 축 때문에 acceptance pass로 보기 어렵다.

---

### must-hide acceptance

판정: `hold`

이유:

- `wrong_ready_count=0`이라 S4 contract는 안정적이다
- `balanced conflict -> strong display leak`도 immediate window에서 재발하지 않았다
- 하지만 `NAS lower_rebound_probe_observe + PROBE + true`가 recent 100 rows에서 54건이라
  `leak`는 아니어도 과표시는 여전히 남아 있다

즉 must-hide는 버그형 fail은 아니지만,
symbol balance 관점에서 hold다.

---

### symbol balance acceptance

판정: `fail`

핵심 수치:

- `BTC display_true=0`
- `NAS display_true=54`
- `XAU display_true=23`

해석:

- 절대 같은 수치를 요구하진 않지만,
  현재는 편차가 너무 크다
- 특히
  - BTC는 너무 많이 숨겨졌고
  - NAS는 너무 많이 보이며
  - XAU만 그 중간에 있다

이 정도 차이는 family/context 차이만으로 설명하기 어렵고,
현재 symbol balance는 acceptance 수용 범위를 벗어난다.

---

### ladder / stage mix acceptance

판정: `pass`

이유:

- `wrong_ready=0`
- late blocked mismatch 재발 없음
- `READY인데 entry_ready=false` 재발 없음
- current ladder는
  - weak observe
  - probe
  - blocked
  를 시각 단계로 구분하는 데는 성공했다

즉 문제는 ladder 자체가 아니라
scene family selection과 symbol balance다.

---

### 최종 판정

최종 verdict:

- `reopen S5 tuning`

선택 이유:

- `reopen S4 contract`로 갈 정도의 구조 버그는 없다
- `hold and observe one more window`만 하기엔
  BTC/NAS imbalance가 이미 수치로 충분히 드러난다
- 즉 다음 액션은 contract를 다시 설계하는 것이 아니라
  symbol balance tuning을 한 번 더 미세조정하는 것이다

---

### 다음 tuning 포인트

#### 1. BTC

- 현재는 suppression이 너무 강하다
- `lower_rebound_probe_observe`를
  전부 hidden으로 두기보다
  일부는 weak visible `OBSERVE`로 남길 필요가 있다

#### 2. NAS

- 현재는 `lower_rebound_probe_observe + PROBE + true`가 너무 많다
- `PROBE -> OBSERVE` downgrade 또는
  cadence suppression을 더 강하게 넣는 것이 맞다

#### 3. XAU

- 현재 immediate/rolling window 둘 다 상대적으로 설명 가능하다
- 이번 reopen의 직접 우선순위는 BTC/NAS다

---

### 결론

현재 scene refinement 트랙은

- 구조 안정성: `pass`
- must-show / must-hide: `hold`
- symbol balance: `fail`

로 보는 게 맞다.

따라서 다음 단계는
`S6 accept and freeze`
가 아니라
`S5 tuning reopen`
이다.
