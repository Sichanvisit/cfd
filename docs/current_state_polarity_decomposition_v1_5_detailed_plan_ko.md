# State Polarity Decomposition v1.5 상세 계획

## 1. 문서 목적

이 문서는 단순히 XAU를 더 세분화하자는 메모가 아니다.

지금까지 구축한 `CA2 / R0~R6-A / S0~S7` 위에서,
왜 문제가 여기까지 흘러오게 되었는지,
왜 이제는 `state strength / local structure / dominance`만으로는 한 단계 부족한지,
그리고 왜 다음 단계가 `상승/하락 state 자체를 더 작은 해석 단위로 분해하는 일`이어야 하는지를 상세하게 정리하는 문서다.

즉 이 문서의 목적은 아래 네 가지다.

1. 현재 병목을 `못 본다`가 아니라 `너무 두꺼운 state를 너무 거칠게 소비한다`로 재정의한다.
2. XAU 집중 작업이 왜 여전히 맞는지 설명하되, 그것이 XAU 전용 규칙 만들기가 아니라 `공용 state polarity decomposition`의 파일럿임을 명확히 한다.
3. 다음 단계의 해석 계층을 `polarity / intent / stage / texture / context / tempo`로 재구성한다.
4. 이후 구현과 검증이 다시 heuristic 파편화로 돌아가지 않도록 공용 계약과 금지선을 먼저 고정한다.

---

## 2. 왜 지금까지의 구조만으로는 부족했는가

지금까지의 진행은 틀리지 않았다.
오히려 필요한 순서대로 잘 왔다.

우리는 먼저 다음을 해결했다.

- runtime에서 실제로 무엇을 봤는지 surface
- execution과 flow history가 어떻게 어긋나는지 surface
- should-have-done 후보를 자동으로 쌓는 축
- canonical surface로 runtime과 execution을 같은 언어로 비교하는 축
- session split과 session shadow bias
- state strength / local structure / dominance shadow-only 계층
- symbol × direction × subtype calibration scaffold

즉 지금은 더 이상 초기 단계가 아니다.
`보는가 / 남는가 / 비교 가능한가`는 많이 해결된 상태다.

그런데 로그와 스크린샷을 함께 보면 다음 문제가 남았다.

### 2-1. continuation과 reversal의 1차 분리는 되었지만 continuation 내부가 너무 두껍다

현재 구조는 대체로 아래 수준까지 왔다.

- `CONTINUATION`
- `CONTINUATION_WITH_FRICTION`
- `BOUNDARY`
- `REVERSAL_RISK`

이건 해석 계층으로는 유효했지만, 트레이딩 판단 기준으로는 아직 거칠다.

왜냐하면 같은 continuation이어도 실제론 완전히 다른 상태가 섞여 있기 때문이다.

예:

- breakout 직후 막 시작된 continuation
- 구조가 완전히 정착된 continuation
- 이미 많이 연장돼서 continuation은 맞지만 추격 품질이 낮은 continuation
- recovery 구조에서 재상승하는 continuation
- friction은 있지만 여전히 같은 방향 우세인 continuation

이것들이 한 덩어리로 묶이면 다음 문제가 생긴다.

- initiation인데 지나치게 wait한다
- acceptance인데 실행 우세로 못 올린다
- extension인데 같은 continuation으로 과신한다

즉 지금 부족한 것은 `더 많은 신호`가 아니라
`이미 continuation이라고 부르는 것을 더 작은 의미 단위로 분해하는 일`이다.

### 2-2. rejection이 두 종류인데 아직 충분히 분리되지 않았다

현재 문제의 중심 중 하나는 `upper reject`, `wait bias`, `soft block`, `reduce alert`류가 여전히 너무 쉽게 caution 우세권을 가져간다는 점이다.

그런데 rejection은 실제로 두 종류다.

1. 구조를 깨는 rejection
   - higher low 붕괴
   - breakout hold 실패
   - 반대 방향 body drive 발생
   - reclaim 실패 누적
   - 이 경우는 `reversal evidence`

2. 구조는 안 깨고 마찰만 만드는 rejection
   - wick은 커지지만 hold는 유지
   - 상단 reject가 있어도 구조는 살아 있음
   - 이 경우는 `friction`

이 둘을 분리하지 않으면 다음 문제가 계속 반복된다.

- continuation인데 sell 쪽 veto가 과대 작동
- upper reject가 등장할 때마다 reversal처럼 소비
- 실제론 `BULL + CONTINUATION_WITH_FRICTION`이어야 할 장면이 `WAIT`나 `SELL`로 눌림

### 2-3. location과 tempo가 빠져 있어서 같은 state라도 의미가 뒤섞인다

지금까지는 구조와 dominance는 많이 봤지만,
다음 두 층은 아직 약했다.

- **location**
  - 어디에서 발생했는가
- **tempo**
  - 얼마나 오래 지속됐는가

같은 rejection이라도 의미는 완전히 다르다.

- 박스 상단 안쪽 rejection
- breakout 직후 rejection
- extension 말단 rejection
- 이미 drift가 누적된 뒤 rejection

또 같은 hold라도 의미는 다르다.

- hold 1봉
- hold 5봉

같은 reject도 다르다.

- reject 1회
- reject 3회 반복

즉 지금 필요한 건 snapshot 설명의 추가가 아니라
`시간과 위치를 포함한 state decomposition`이다.

---

## 3. 지금 문제를 어떻게 다시 정의할 것인가

이 문서에서 문제는 이렇게 정의한다.

### 기존 정의

- XAU subtype가 부족하다
- NAS에서 upper reject가 너무 쉽게 SELL로 간다
- BTC는 up/down이 아직 혼잡하다

### 새로운 정의

위 현상들은 증상일 뿐이다.
실제 본체는 아래다.

> 상승/하락 polarity state가 continuation / recovery / rejection / breakdown / drift / exhaustion 같은 서로 다른 해석 단위를 너무 두껍게 묶고 있고, 그 결과 dominance / veto / caution 소비 구조가 장면마다 달라져야 하는데도 한 덩어리로 소비된다.

즉 다음 단계의 목표는
`XAU 전용 subtype를 늘리는 것`이 아니라
**상승/하락 state를 더 작은 공용 해석 슬롯으로 분해하는 일**이다.

XAU는 여기서 가장 효율적인 파일럿이다.

---

## 4. XAU를 왜 여전히 먼저 파야 하는가

위 정의를 받아들여도 XAU 우선순위는 여전히 맞다.

다만 이유를 다시 표현해야 한다.

### 잘못된 표현

- 지금은 XAU를 더 잘게 쪼개는 것이 목적이다

### 더 정확한 표현

- 지금은 XAU를 먼저 파는 것이 가장 효율적이다.
- 하지만 그 목적은 XAU 예외 규칙을 늘리는 것이 아니라, 상승/하락 state를 더 작은 해석 단위로 분해하는 공용 프레임을 안정화하는 것이다.

왜 XAU인가?

1. retained evidence가 가장 선명하다
2. 상승/하락 둘 다 분명히 보인다
3. should-have-done candidate가 많다
4. subtype 분해의 효과가 바로 드러난다
5. NAS/BTC 일반화 이전에 공용 slot을 시험하기 좋다

즉 XAU는 목표가 아니라 훈련장이다.

---

## 5. 이제 필요한 해석 구조: State Polarity Decomposition

다음 단계의 핵심은 `심볼 전용 subtype 나열`이 아니라
**공용 state slot을 먼저 정의하고, 각 심볼이 그 slot에 어떻게 탑승하는지 보는 구조**다.

### 5-1. 상위 구조

다음 다층 구조를 사용한다.

#### Layer A. Polarity

- `BULL`
- `BEAR`

이 층은 가장 큰 방향 가설이다.

#### Layer B. Intent

- `CONTINUATION`
- `RECOVERY`
- `REJECTION`
- `BREAKDOWN`
- `BOUNDARY`

이 층은 현재 구조가 무엇을 하려는지에 대한 의도다.

#### Layer C. Stage

특히 continuation/recovery 계열은 stage가 중요하다.

- `INITIATION`
- `ACCEPTANCE`
- `EXTENSION`

이 층은 트레이딩 관점에서 매우 중요하다.
왜냐하면 같은 continuation이어도

- initiation은 진입 품질이 가장 좋을 수 있고
- acceptance는 보유/추격이 가능한 구간이며
- extension은 continuation은 맞지만 추격 품질이 낮을 수 있기 때문이다.

#### Layer D. Texture

같은 intent/stage라도 표면 질감이 다르다.

- `CLEAN`
- `WITH_FRICTION`
- `DRIFT`
- `EXHAUSTING`
- `FAILED_RECLAIM`
- `POST_DIP`

이 층은 execution 품질과 caution 소비 방식에 직접 연결된다.

#### Layer E. Context

이 층은 장면의 위치와 시간을 담당한다.

- `location_context_v1`
- `tempo_profile_v1`

즉 "어디에서 발생했는가", "얼마나 지속됐는가"를 설명한다.

#### Layer F. Ambiguity

이 층은 continuation과 reversal, 또는 recovery와 boundary가 충분히 갈리지 않을 때의 해석 난이도를 담당한다.

- `ambiguity_level_v1 = LOW / MEDIUM / HIGH`

ambiguity는 side를 바꾸는 층이 아니다.
대신 mode와 caution을 조정하는 안전장치다.

즉 ambiguity는 다음 역할을 가진다.

- `LOW`: continuation 또는 reversal 확신을 방해하지 않음
- `MEDIUM`: boundary 경계 가능성을 높임
- `HIGH`: wait/caution 소비를 강화하고, 과잉 해석을 억제함

---

## 6. 공용 state slot 예시

이 문서에서 subtype는 심볼 이름보다 먼저 공용 slot을 가진다.

### 6-1. 공용 상승 슬롯 예시

- `BULL_BREAKOUT_DRIVE`
- `BULL_RECOVERY_RECLAIM`
- `BULL_POST_DIP_RECOVERY`
- `BULL_CONTINUATION_ACCEPTANCE`
- `BULL_CONTINUATION_WITH_FRICTION`
- `BULL_BOUNDARY_EXHAUSTION`

### 6-2. 공용 하락 슬롯 예시

- `BEAR_REJECT_BREAKDOWN`
- `BEAR_FAILED_RECLAIM_CONTINUATION`
- `BEAR_MID_REJECT_DRIFT`
- `BEAR_CONTINUATION_ACCEPTANCE`
- `BEAR_CONTINUATION_WITH_FRICTION`
- `BEAR_BOUNDARY_EXHAUSTION`

이 구조가 중요한 이유는:

- XAU 전용 규칙 남발을 막아주고
- NAS/BTC 일반화가 쉬워지고
- should-have-done teacher를 공용 언어로 축적할 수 있게 해주기 때문이다

즉 심볼이 subtype를 정의하는 것이 아니라,
공용 slot 위에 심볼별 evidence가 얹히는 구조로 가야 한다.

### 6-3. core slot 승격 기준

v1.5에서 가장 중요한 통제 규칙 중 하나는
"무엇을 core slot으로 올리고 무엇을 modifier로 남길 것인가"다.

여기서 기준은 장면의 보기 좋은 이름이 아니다.
기준은 아래 한 문장이다.

> core slot은 단순 장면 구분이 아니라, execution decision이 실제로 달라질 만큼 구조 차이가 있을 때만 정의한다.

즉 다음은 core 후보가 될 수 있다.

- `CONTINUATION_ACCEPTANCE`
- `CONTINUATION_EXTENSION`
- `REJECT_BREAKDOWN`
- `RECOVERY_INITIATION`

반면 아래는 우선 modifier나 세부 evidence로 남기는 것이 맞다.

- `MID_RECLAIM`
- `LOWER_RECLAIM`
- `POST_DIP`
- `AT_EDGE`
- `REJECT_REPEAT_HIGH`

이 기준을 쓰는 이유는 두 가지다.

1. core slot 폭발을 막기 위해서
2. 해석 차이가 실제 행동 차이로 이어지는 경우만 핵심 상태로 승격하기 위해서

즉 core slot은 설명의 편의가 아니라
행동 차이를 만들 정도의 구조적 차이일 때만 허용한다.

---

## 7. 기존 state/dominance 구조와 새 분해 구조의 관계

새 구조는 기존 것을 버리는 것이 아니다.
기존 `state strength / local structure / dominance`는 그대로 기초층으로 남는다.

다만 그 위에 decomposition 층을 얹는다.

### 기존 기초층

- `side_seed`
- `continuation_integrity`
- `reversal_evidence`
- `friction`
- `dominance_gap`
- `dominant_side`
- `dominant_mode`
- `consumer_veto_tier_v1`

### 새 decomposition 층

- `polarity_slot_v1`
- `intent_slot_v1`
- `stage_slot_v1`
- `texture_slot_v1`
- `location_context_v1`
- `tempo_profile_v1`

즉 기존 계층은
"누가 우세한가"를 판정하고,
새 decomposition 층은
"그 우세가 정확히 어떤 종류의 우세인가"를 세밀하게 설명한다.

---

## 8. 핵심 새 요구사항

### 8-1. continuation은 3단계로 분해한다

이건 v1.5의 가장 중요한 추가다.

#### `CONTINUATION_INITIATION`

- breakout 직후
- reclaim 직후
- 구조가 막 시작된 구간

의미:

- 가장 먹기 좋은 continuation일 수 있다
- 동시에 false break 리스크도 있다

#### `CONTINUATION_ACCEPTANCE`

- breakout hold 유지
- higher low 유지
- 구조가 정착된 구간

의미:

- continuation 확률이 높다
- 추격이나 보유 판단이 가능하다

#### `CONTINUATION_EXTENSION`

- 이미 많이 올라왔거나 많이 내려옴
- wick 증가
- body drive 약화
- mean reversion 압력 증가

의미:

- continuation은 맞을 수 있다
- 하지만 entry quality는 낮아질 수 있다

이 3단계를 분리하지 않으면,
계속 "맞는 방향인데 왜 여기서 행동이 달라야 하는지"를 설명하지 못한다.

### 8-2. rejection은 두 종류로 나눈다

문서에 반드시 다음 원칙을 못 박아야 한다.

#### rejection as reversal

- structure break를 동반
- reversal evidence를 키움
- 실제 side 변경 후보

#### rejection as continuation friction

- 구조는 유지
- friction만 상승
- side는 유지

즉 다음 규칙을 강하게 유지한다.

> rejection은 단일 신호가 아니라, structure-breaking rejection과 non-breaking rejection으로 분리한다. 전자는 reversal evidence이고 후자는 friction이다. 이 둘을 절대 같은 무게로 취급하지 않는다.

### 8-3. location_context_v1를 추가한다

같은 signal도 어디에서 발생했는지가 중요하다.

최소 v1.5 후보:

- `IN_BOX`
- `AT_EDGE`
- `POST_BREAKOUT`
- `EXTENDED`

필요 시 추후 확장:

- `POST_RECLAIM`
- `MID_BOX_DRIFT`
- `FAILED_BREAK_ZONE`

location은 다음 해석에 직접 영향을 준다.

- rejection이 friction인지 reversal인지
- continuation stage가 initiation인지 extension인지
- caution을 얼마나 크게 볼지

### 8-4. tempo_profile_v1를 추가한다

흐름의 지속성도 별도 층으로 본다.

최소 v1.5 후보 raw field:

- `breakout_hold_bars`
- `higher_low_count`
- `lower_high_count`
- `reject_repeat_count`
- `counter_drive_repeat_count`

tempo는 처음엔 점수보다 count로 시작하는 게 더 안전하다.

이 층은 다음 판단을 돕는다.

- noise rejection 1회인지
- 의미 있는 반복 rejection인지
- hold가 잠깐인지 충분한지
- recovery가 막 시작인지 이미 소모된 구간인지

---

## 9. XAU는 어떻게 이 프레임의 파일럿이 되는가

XAU에서 관찰된 핵심은 아래다.

### 9-1. XAU 상승에서도 세분화가 필요하다

기존에는 `RECOVERY_RECLAIM`으로 묶였지만,
실제로는 아래처럼 더 분리될 가능성이 높다.

- lower reclaim recovery
- mid reclaim continuation
- post-dip recovery drive
- continuation with friction recovery

즉 XAU 상승은 "상승 recovery" 하나로는 부족하다.

### 9-2. XAU 하락에서도 세분화가 필요하다

기존에는 `UPPER_REJECT_REJECTION`으로 묶였지만,
실제로는 아래가 섞일 수 있다.

- true reject breakdown
- failed reclaim sell continuation
- mid reject drift
- exhaustion after bounce failure

즉 XAU 하락도 "rejection" 하나로는 부족하다.

### 9-3. 그렇다고 XAU 예외 규칙을 늘리면 안 된다

중요한 건 이 세분화가 XAU 전용 규칙 추가가 되면 안 된다는 점이다.

정답은:

- XAU에서 먼저 decomposition slot을 검증
- 그 slot이 공용으로 설명 가능한지 확인
- 이후 NAS/BTC에 맵핑

이다.

즉 XAU는 공용 state decomposition의 첫 실험장이다.

---

## 10. 새 subtype를 만들기 전에 먼저 묻는 질문

v1.5에서는 screenshot variation만으로 subtype를 만들지 않는다.

새 slot 또는 subtype를 만들기 전에 반드시 아래를 묻는다.

1. 이 장면은 기존 상승/하락 state 안에서 정말 다른 해석 소비를 요구하는가?
2. 이 장면은 기존 subtype와 비교해 `consumer veto / dominance / caution` 소비 방식이 구조적으로 다른가?
3. 이 차이는 단순 위치 variation인가, 아니면 다른 state slot으로 분리해야 할 이유가 있는가?
4. 이 장면은 retained evidence와 should-have-done candidate로 다시 확인 가능한가?
5. 이 분해는 공용 slot으로 일반화 가능한가, 아니면 XAU 로컬 현상에 불과한가?

즉 "장면이 다르다"가 아니라
"해석 소비 구조가 다르다"일 때만 새 분해를 인정한다.

---

## 11. dominance와 decomposition의 역할 분담

이 부분은 매우 중요하다.

### dominance layer의 역할

- 방향 우세를 정한다
- reversal과 continuation을 경쟁시킨다
- friction이 side를 바꾸지 못하게 막는다
- veto tier를 정한다

### decomposition layer의 역할

- 같은 continuation 안에서도 initiation / acceptance / extension을 분리한다
- rejection을 reversal vs friction으로 분리한다
- 위치와 지속성으로 의미를 조정한다
- execution 품질을 읽을 수 있는 사전 상태를 만든다

즉 decomposition은 dominance를 대체하지 않는다.
dominance 위에 얹혀서 더 정밀한 해석을 만든다.

---

## 12. v1.5에서 추가할 공용 계약 후보

### 12-1. `polarity_intent_profile_v1`

필드 예:

- `polarity_slot_v1 = BULL / BEAR`
- `intent_slot_v1 = CONTINUATION / RECOVERY / REJECTION / BREAKDOWN / BOUNDARY`
- `intent_confidence_v1`

### 12-2. `continuation_stage_profile_v1`

필드 예:

- `continuation_stage_v1 = INITIATION / ACCEPTANCE / EXTENSION / NONE`
- `stage_reason_summary_v1`

### 12-3. `rejection_type_profile_v1`

필드 예:

- `rejection_type_v1 = NONE / REVERSAL_REJECTION / FRICTION_REJECTION`
- `rejection_structure_break_confirmed_v1`

### 12-4. `location_context_profile_v1`

필드 예:

- `location_context_v1 = IN_BOX / AT_EDGE / POST_BREAKOUT / EXTENDED`
- `location_reason_summary_v1`

### 12-5. `tempo_profile_v1`

필드 예:

- `breakout_hold_bars_v1`
- `higher_low_count_v1`
- `reject_repeat_count_v1`
- `counter_drive_repeat_count_v1`
- `tempo_reason_summary_v1`

### 12-5b. `ambiguity_modifier_profile_v1`

필드 예:

- `ambiguity_level_v1 = LOW / MEDIUM / HIGH`
- `ambiguity_reason_summary_v1`

핵심 원칙:

- ambiguity는 side를 바꾸지 않는다
- ambiguity는 `BOUNDARY` bias와 `caution_level`을 조정한다
- ambiguity는 decomposition이 과하게 확정적으로 굳는 것을 막는 안전장치다

### 12-6. `state_slot_profile_v1`

최종 해석용 요약 슬롯:

- `state_slot_v1`
- `state_slot_reason_summary_v1`

예:

- `BULL_RECOVERY_RECLAIM_INITIATION`
- `BULL_CONTINUATION_ACCEPTANCE_WITH_FRICTION`
- `BEAR_REJECT_BREAKDOWN_ACCEPTANCE`
- `BEAR_FAILED_RECLAIM_DRIFT`

---

## 13. 검증 철학

새 decomposition은 예쁜 라벨을 늘리는 작업이 아니다.
반드시 검증 가능한 구조여야 한다.

### 13-1. should-have-done teacher

새 slot은 아래와 연결되어야 한다.

- `expected_dominant_side`
- `expected_dominant_mode`
- `dominance_error_type`
- `overweighted_caution_fields`
- `undervalued_continuation_evidence`

여기에 앞으로는 slot 관점도 붙일 수 있어야 한다.

- `expected_state_slot_v1`
- `predicted_state_slot_v1`
- `state_slot_error_type_v1`

### 13-2. canonical diverged audit

다음 질문이 가능해야 한다.

- 이 장면은 `BULL_CONTINUATION_ACCEPTANCE`였는데 왜 execution은 wait였는가?
- 이 장면은 `FRICTION_REJECTION`이었는데 왜 reversal처럼 소비됐는가?

### 13-3. shadow validation

새 decomposition이 정말 값이 있는지는 아래로 본다.

- over-veto 감소 여부
- under-veto 증가 여부 감시
- friction separation quality 향상 여부
- boundary dwell quality 향상 여부
- slot별 should-have-done alignment

---

## 14. 하지 말아야 할 것

- XAU subtype를 screenshot variation마다 늘리지 말 것
- 심볼별 예외 규칙을 공용 slot보다 먼저 늘리지 말 것
- rejection 하나를 곧바로 reversal로 해석하지 말 것
- location과 tempo를 무시한 채 slot을 정의하지 말 것
- execution/state25 연결을 너무 일찍 하지 말 것
- stage와 texture를 같은 층으로 섞어버리지 말 것

---

## 15. 한 문장 결론

지금 필요한 다음 단계는 XAU 전용 subtype를 더 늘리는 것이 아니라, XAU를 가장 선명한 파일럿으로 삼아 상승/하락 polarity state를 `continuation / recovery / rejection / breakdown / boundary`와 그 안의 `stage / texture / location / tempo`까지 분해하는 공용 state decomposition 프레임을 만드는 일이다.

---

## 16. v1.5 통제 규칙

이 문서에서 가장 중요한 것은 "더 잘게 쪼갠다"가 아니라
"쪼갠 상태를 통제 가능한 구조로 유지한다"는 점이다.

이 절에서는 v1.5가 반드시 지켜야 할 통제 규칙을 고정한다.

### 16-1. slot은 완전 조합형이 아니라 `core + modifiers` 구조를 쓴다

가장 큰 리스크는 slot 폭발이다.

다음처럼 모든 층을 그대로 결합하면 조합 수가 과도하게 커진다.

- polarity × intent × stage × texture × context × tempo

이 문서는 그런 완전 조합형 slot을 금지한다.

v1.5의 기본 규칙은 아래와 같다.

#### core slot

core는 장면의 가장 중요한 뼈대를 표현한다.

- `polarity`
- `intent`
- `stage`

예:

- `BULL_CONTINUATION_ACCEPTANCE`
- `BEAR_RECOVERY_INITIATION`
- `BULL_BOUNDARY_NONE`

#### modifiers

modifier는 core slot의 의미를 더 세밀하게 꾸며주는 정보다.

- `texture`
- `location`
- `tempo`

예:

- `WITH_FRICTION`
- `AT_EDGE`
- `EXTENDED`
- `REJECT_REPEAT_HIGH`

즉 v1.5에서 slot은 아래 방식으로 읽는다.

- core: `BULL_CONTINUATION_ACCEPTANCE`
- modifier: `WITH_FRICTION`, `AT_EDGE`

이지,

- `BULL_CONTINUATION_ACCEPTANCE_WITH_FRICTION_AT_EDGE_EXTENDED`

같은 완전 결합형 라벨을 기본 상태명으로 사용하지 않는다.

이 규칙의 목적은 세 가지다.

1. slot 폭발 방지
2. 공용 언어 유지
3. NAS/XAU/BTC 일반화 가능성 확보

그리고 아래 기준을 함께 적용한다.

> core slot은 execution decision을 바꿀 만큼 다른 구조 차이가 있을 때만 승격한다.

즉 설명만 다른 장면은 modifier로 남기고,
행동이 달라질 정도로 구조가 다른 장면만 core로 승격한다.

### 16-2. stage와 texture는 반드시 분리한다

v1.5에서 stage와 texture는 서로 다른 차원의 정보다.

#### stage

stage는 구조적 시간 위치다.

- 지금 구조가 막 시작되는가
- 이미 정착되었는가
- 연장 말단으로 갔는가

즉 stage는 "언제인가"를 설명한다.

#### texture

texture는 실행 품질과 소비 질감이다.

- 지금 진입 품질이 깨끗한가
- 마찰이 큰가
- drift 상태인가
- exhausting인가

즉 texture는 "어떻게 소비해야 하는가"를 설명한다.

이 둘을 섞으면 다음 문제가 생긴다.

- acceptance와 extension이 같은 실행 품질로 묶임
- drift와 friction이 stage처럼 소비됨
- timing과 quality가 한 필드로 뭉개짐

그래서 다음 규칙을 문서에 고정한다.

> stage는 구조적 시간 위치를 나타내고, texture는 실행 품질을 나타낸다. 같은 장면은 `ACCEPTANCE + CLEAN`, `ACCEPTANCE + WITH_FRICTION`, `EXTENSION + CLEAN`, `EXTENSION + EXHAUSTING`처럼 분리해서 읽어야 한다.

### 16-3. decomposition layer는 dominant_side를 바꾸지 못한다

이 규칙은 가장 중요한 보호 규칙이다.

dominance layer의 역할은 다음이다.

- `continuation_integrity`
- `reversal_evidence`
- `dominance_gap`
- `dominant_side`

즉 누가 우세권을 가지는지 정하는 것은 dominance layer다.

반면 decomposition layer의 역할은 다음이다.

- 그 우세가 어떤 종류의 continuation인가
- recovery인가
- rejection이 reversal인가 friction인가
- initiation/acceptance/extension 중 어디인가
- location과 tempo는 어떤가

즉 decomposition layer는 dominance를 세밀하게 설명할 뿐, dominance를 대체하지 않는다.

이 문서에서 아래 규칙을 절대 규칙으로 둔다.

> decomposition layer는 `dominant_side`를 변경할 수 없다. side 변경은 반드시 dominance layer에서만 발생한다.

따라서 다음은 금지한다.

- texture를 보고 side를 바꾸는 것
- location을 보고 side를 바꾸는 것
- tempo를 보고 side를 바꾸는 것
- slot 이름만 보고 reversal로 재분류하는 것

### 16-4. rejection 분리 규칙은 decomposition 전체의 안전장치다

`reversal rejection`과 `friction rejection` 분리는 옵션이 아니라 안전장치다.

이 규칙이 무너지면 다시 아래 문제가 재발한다.

- upper reject 하나로 sell bias 과대 작동
- continuation with friction이 reversal로 오인
- XAU/NAS/BTC에서 같은 문제가 반복

즉 rejection 분리는 단순 subtype naming이 아니라
`friction이 dominant_side를 못 뒤집게 막는 핵심 장치`다.

### 16-5. location과 tempo는 우선 modifier로만 사용한다

`location`과 `tempo`는 중요하지만, 처음부터 core slot으로 올리면 slot 수가 급격히 늘어난다.

그래서 v1.5에서는 아래 원칙을 쓴다.

- location은 우선 modifier
- tempo는 우선 raw count + modifier
- 충분한 retained evidence와 validation이 쌓이기 전에는 core 승격 금지

즉 처음엔

- `POST_BREAKOUT`
- `AT_EDGE`
- `breakout_hold_bars = 5`
- `reject_repeat_count = 3`

같은 형태로 남기고,
나중에 정말 공용성이 입증될 때만 일부를 core 규칙으로 승격한다.

### 16-5b. ambiguity는 modifier로 복귀시킨다

v1.5에서는 ambiguity를 core slot에 넣지 않는다.

대신 아래 방식으로 사용한다.

- `ambiguity_level_v1 = LOW / MEDIUM / HIGH`
- mode 조정
- caution 조정
- boundary bias 강화

즉 ambiguity는 다음 규칙을 따른다.

> ambiguity는 side를 바꾸지 않지만, mode와 caution을 강하게 조정한다.

이 규칙의 목적은 두 가지다.

1. continuation도 reversal도 아닌 애매한 상태를 별도 안전장치로 보존
2. ambiguity를 friction이나 continuation 쪽으로 억지 흡수하는 실수를 막기

### 16-6. decomposition은 해석 엔진이고, 행동 엔진은 다음 단계다

지금 문서는 어디까지나 해석 엔진을 정교화하는 문서다.

즉 현재 문서가 직접 답하는 질문은:

- 지금 상태가 무엇인가
- 왜 continuation인가
- 왜 boundary인가
- 왜 friction인가

이지, 아직 직접적으로 아래 질문까지 답하지는 않는다.

- 지금 진입할 것인가
- 지금 추가할 것인가
- 지금 줄일 것인가
- 지금 청산 준비를 할 것인가

이 질문은 다음 단계의 `execution decision layer`가 맡는다.

그래서 v1.5에서는 아래 방향만 고정한다.

- `state_slot -> execution_policy`

라는 연결 방향은 맞다.
하지만 execution policy 구현은 decomposition 검증 뒤로 미룬다.

예시:

- `CONTINUATION_INITIATION` -> 공격적 진입 후보
- `CONTINUATION_ACCEPTANCE` -> 보유/추가 후보
- `CONTINUATION_EXTENSION` -> 신규 진입 억제 후보
- `WITH_FRICTION` -> 진입 지연/보수적 threshold 후보
- `EXHAUSTING` -> exit pressure 후보

즉 행동 레이어는 필요하지만, 지금 문서의 역할은 그 직전 단계까지다.

### 16-7. execution interface는 지금 정의만 하고 적용은 미룬다

현재 문서 단계에서는 execution을 직접 바꾸지 않는다.
하지만 나중에 decomposition을 lifecycle로 넘기기 위한 인터페이스는 미리 고정할 필요가 있다.

v1.5에서 추천하는 최소 bridge는 아래와 같다.

- `entry_bias_v1`
- `hold_bias_v1`
- `add_bias_v1`
- `reduce_bias_v1`
- `exit_bias_v1`

예:

- `BULL_CONTINUATION_INITIATION`
  - `entry_bias_v1 = HIGH`
  - `hold_bias_v1 = MEDIUM`
  - `add_bias_v1 = LOW`
  - `reduce_bias_v1 = LOW`
  - `exit_bias_v1 = LOW`

- `BULL_CONTINUATION_EXTENSION + EXHAUSTING`
  - `entry_bias_v1 = LOW`
  - `hold_bias_v1 = MEDIUM`
  - `add_bias_v1 = LOW`
  - `reduce_bias_v1 = HIGH`
  - `exit_bias_v1 = MEDIUM`

중요한 점은 다음이다.

- 이 인터페이스는 아직 실행이 아니다
- 이 인터페이스는 decomposition 결과를 행동 레이어로 넘기기 위한 bridge다
- 실제 execution/state25 연결은 decomposition 검증 이후에만 허용한다
