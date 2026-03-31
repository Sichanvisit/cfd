# Consumer-Coupled Check / Entry Scene Refinement
## S6. Acceptance Spec

### 목적

S6의 목적은
`consumer-coupled check / entry scene refinement`
트랙을

- `아직 더 손봐야 한다`
- `일단 종료해도 된다`

로 숫자와 사례 기준으로 판정하는 것이다.

즉 S6는 새 규칙을 많이 만드는 단계가 아니다.

- `S0 baseline`
- `S1 must-show`
- `S2 must-hide`
- `S3 visually similar alignment`
- `S4 contract refinement`
- `S5 symbol balance tuning`

을 거친 뒤,
현재 상태가 실제 recent window에서 수용 가능한지를 판정하는 단계다.

---

### 왜 필요한가

지금까지는 아래를 이미 만들었다.

- must-show / must-hide casebook
- visually similar scene alignment audit
- consumer check state contract
- `display_score -> repeat_count` ladder
- symbol balance tuning

따라서 이제 남은 질문은
`무엇을 더 만들 것인가`보다
`지금 상태를 끝으로 봐도 되는가`이다.

S6는 이 질문에 답한다.

---

### 직접 owner

#### 1. 판단 owner

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`

#### 2. 보조 확인 owner

- `backend/services/consumer_check_state.py`
- `backend/services/entry_try_open_entry.py`
- `backend/trading/chart_painter.py`

#### 3. 입력 문서

- [S1 must-show casebook](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_ko.md)
- [S2 must-hide casebook](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_ko.md)
- [S3 visually similar alignment audit](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_ko.md)
- [S4 reconfirm memo](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_s4_consumer_check_state_contract_refinement_reconfirm_memo_ko.md)
- [S5 reconfirm memo](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_scene_refinement_s5_symbol_balance_tuning_reconfirm_memo_ko.md)

---

### S6에서 판정할 것

#### 1. must-show missing 재발 여부

질문:

- `S1`에서 must-show로 잠근 family가
  최근 window에서 다시 `display=false`로만 반복되는가
- 있더라도 late blocked / conflict / cadence suppression으로 설명 가능한가

대표 확인 family:

- `XAU upper_reject_confirm / upper_reject_probe_observe`
- `XAU middle_sr_anchor_required_observe`
- `BTC lower_rebound_probe_observe`
- `NAS lower_rebound_probe_observe`

#### 2. must-hide leaking 재발 여부

질문:

- `S2`에서 hide/downgrade/reduce로 잠근 family가
  다시 `PROBE` 또는 과한 repeat로 남는가

대표 확인 family:

- `balanced conflict + observe_state_wait`
- `BTC lower structural buy leakage`
- `NAS structural observe spam`
- `energy_soft_block + falling lower rebound buy`

#### 3. symbol balance 수용 가능성

질문:

- `BTC/NAS/XAU`가 서로 완전히 같은 개수로 뜰 필요는 없지만
- 특정 symbol만 압도적으로 과다/과소한가
- 그 차이가 family/context 차이로 설명 가능한가

#### 4. stage mix 건강도

질문:

- `OBSERVE / PROBE / BLOCKED / READY / NONE`
  비율이 symbol별로 과하게 한쪽으로만 쏠리는가
- 특히 `wrong_ready_count`, `display_ready_true`, `display_ready_false`가
  체감과 맞는가

#### 5. display ladder 일관성

질문:

- `70 / 80 / 90`
- `1 / 2 / 3 repeat`

체계가 실제 recent row에서 기대대로 읽히는가

즉,

- weak observe는 1개
- probe는 2개
- ready는 3개

라는 의도가 깨지지 않았는가를 본다.

---

### acceptance 입력 window

기본 입력은 아래 두 window를 같이 본다.

#### 1. immediate window

- 재시작 또는 수정 이후 가장 최근 20~40 rows

역할:

- 새 contract가 실제로 먹는지 본다

#### 2. rolling recent window

- symbol별 최근 60~120 rows

역할:

- 특정 family가 잠깐만 좋아 보이는지
- 아니면 반복적으로 안정됐는지 본다

S6에서는 두 window를 모두 만족해야 한다.

---

### acceptance 판정 축

#### A. Pass

아래를 만족하면 `pass`로 본다.

- must-show missing이 반복 재현되지 않는다
- must-hide leaking이 반복 재현되지 않는다
- symbol별 imbalance가 남아도 설명 가능 범위다
- `wrong_ready_count = 0`
- `READY인데 entry_ready=false` 같은 체감 mismatch가 없다
- display ladder가 stage 체감과 맞는다

#### B. Hold

아래면 `hold`로 본다.

- 즉시 다시 고쳐야 할 버그는 아닌데
- 한 symbol의 특정 family가 여전히 눈에 거슬리게 반복된다
- 재시작 직후 window는 좋아졌지만 rolling recent window에서는 재발한다
- must-show / must-hide는 대체로 맞지만
  `reduce / cadence` 수준의 후속 조정이 더 필요하다

#### C. Fail

아래면 `fail`로 본다.

- must-show가 다시 구조적으로 사라진다
- must-hide가 다시 강한 `PROBE/READY`로 새는 case가 반복된다
- symbol imbalance가 설명 불가능할 정도로 커진다
- wrong-ready / late-block mismatch가 재발한다

---

### S6 정량 기준

#### 1. wrong-ready

- 목표: `0`
- 허용: `0`

#### 2. must-hide leaking

- 동일 leaking family가 immediate window에서
  `display=true`로 3회 이상 반복되면 fail 후보
- rolling recent window에서 5회 이상 반복되면 hold 이상

#### 3. must-show missing

- 동일 must-show family가 immediate window에서
  전부 `display=false`이면 hold 후보
- rolling recent window에서도 계속 0회면 fail 후보

#### 4. symbol imbalance

절대 동일 개수를 요구하지 않는다.

대신 아래를 본다.

- 한 symbol의 `display_ready_true` 비율이 다른 둘보다 압도적으로 크고
- 그 차이가 family/context 차이로 설명되지 않으면 hold

실무 해석:

- `BTC/NAS/XAU` 중 하나만 도배처럼 보이면 hold
- 다르더라도 family/context 차이로 설명되면 pass 가능

#### 5. stage mix

아래는 경고 후보:

- `PROBE`만 계속 남고 `OBSERVE`가 거의 없거나
- `OBSERVE`만 계속 남고 visible cadence가 지나치게 반복되거나
- `BLOCKED`가 화면상 과하게 강하게 보이는 경우

---

### S6 산출물

S6가 끝나면 아래가 있어야 한다.

#### 1. acceptance memo

필수 섹션:

- immediate window result
- rolling recent window result
- must-show result
- must-hide result
- symbol balance result
- final verdict

#### 2. final action

아래 중 하나로 명시한다.

- `accept and freeze`
- `hold and observe one more window`
- `reopen S5 tuning`
- `reopen S4 contract`

---

### 원칙

#### 1. acceptance는 숫자와 사례를 같이 본다

숫자만으로 종료하지 않는다.

반드시:

- recent distribution
- actual row case
- user chart 체감

을 같이 본다.

#### 2. painter 시각 효과만으로 pass 주지 않는다

차트가 예뻐 보여도 runtime row와 어긋나면 pass가 아니다.

#### 3. symbol 차이는 허용하지만 설명 가능해야 한다

`다르게 뜬다` 자체가 문제가 아니라,
`왜 다르게 뜨는지 설명 불가능하다`가 문제다.

---

### S6 이후 분기

#### 1. pass

- scene refinement 트랙은 일단 종료
- 이후는 운영 관찰 또는 bounded-live / promotion 쪽으로 넘어간다

#### 2. hold

- 현재 contract는 유지
- 한 window 더 관찰
- 또는 S5 수준의 최소 balance tuning만 한 번 더

#### 3. fail

- 문제 family를 기준으로
  - contract 문제면 `S4`
  - balance 문제면 `S5`
  로 되돌아간다

---

### 현재 예상 next action

현재까지 흐름상 가장 자연스러운 S6 action은:

1. immediate window acceptance snapshot
2. rolling recent acceptance snapshot
3. acceptance memo 작성
4. `pass / hold / fail` 판정

즉 다음 구현은
`S6 acceptance snapshot + memo`
가 맞다.
