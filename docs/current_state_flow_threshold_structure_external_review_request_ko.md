# Aggregate Directional Flow Threshold / Structure External Review Request

## 1. 문서 목적

이 문서는 단순히 "threshold를 몇으로 둘까"를 묻는 문서가 아니다.

지금까지 우리가 시스템을 어떻게 구축해 왔는지,
왜 초기에는 `정확한 profile match` 중심 구조가 필요했는지,
왜 이제는 `aggregate directional flow`와 `structure gate`를 같이 봐야 한다는 결론에 도달했는지,
그리고 다음 단계에서 어떤 선택지를 두고 고민하고 있는지를 외부 조언 기준으로 상세하게 정리하는 문서다.

핵심 질문은 아래와 같다.

1. 현재 구조에서 `exact profile match`는 어느 위치에 있어야 하는가.
2. `state` 내부의 여러 수치를 종합한 `aggregate conviction / persistence`는 어떤 형태로 해석되어야 하는가.
3. 숫자 threshold는 독립적인 하드 룰이어야 하는가, 아니면 구조 gate를 통과한 뒤 쓰는 보조 확정 장치여야 하는가.
4. XAU에서 먼저 보이는 이 문제를 어떤 방식으로 NAS/BTC에도 일반화해야 하는가.

---

## 2. 여기까지 어떻게 흘러왔는가

### 2-1. 시작점: "인식이 안 된다"가 첫 문제였다

초기 단계의 문제는 방향을 세밀하게 틀리게 읽는 것보다 더 앞단이었다.

- runtime row가 실제 chart 장면을 제대로 못 따라감
- flow history, execution diff, checkpoint row가 끊겨 보임
- "무엇을 보고 있는가"를 설명하는 공통 surface가 부족함

그래서 첫 단계에서는 아래를 먼저 만들었다.

- `CA2 / R0 ~ R6-A`
- `runtime_signal_wiring_audit_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session split / session bias shadow`

즉 초반 목표는 "정답을 잘 맞춘다"가 아니라,
`보는가 / 남기는가 / 나중에 비교 가능한가`를 확보하는 것이었다.

### 2-2. 그다음 문제: "못 보는 것"보다 "봤는데 잘못 소비하는 것"

로그와 스크린샷 대조가 쌓이면서 더 중요한 병목이 드러났다.

대표적으로 NAS에서 반복적으로 보인 현상은 아래였다.

- 구조는 `UP` continuation을 보고 있음
- `breakout held`, `above`, `with htf`, `buy watch`가 보임
- 그런데 consumer/check 계층은 `upper reject`, `wait`, `sell pressure`로 과하게 소비함

즉 문제는 더 이상 "상승을 못 봄"이 아니었다.
문제는 `강세를 보고도 caution / veto가 우세권을 뺏는다`는 쪽이었다.

여기서 등장한 구조가 아래다.

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `state_structure_dominance_profile_v1`
- `dominance validation / shadow bias`

즉 이 단계의 문제 정의는:

> 인식 실패가 아니라 우세 해석 승격 실패다.

였다.

### 2-3. 그다음 문제: continuation 자체가 너무 두껍다

dominance layer를 붙인 뒤에도 실전 장면을 보면 아직 부족했다.

이제는 `continuation vs reversal`만으로는 설명이 부족했다.

왜냐하면 같은 continuation 안에도 아래가 섞여 있었기 때문이다.

- 시작 직후 continuation
- 정착된 continuation
- 너무 연장된 continuation
- recovery continuation
- continuation with friction
- drift continuation

같은 rejection도 아래 두 개가 섞여 있었다.

- 구조를 깨는 rejection
- 구조는 안 깨고 friction만 만드는 rejection

이 문제를 해결하려고 만든 것이 다음 decomposition 계층이다.

- `state_polarity_slot_vocabulary_contract_v1`
- `rejection_split_rule_contract_v1`
- `continuation_stage_contract_v1`
- `location_context_contract_v1`
- `tempo_profile_contract_v1`
- `ambiguity_modifier_contract_v1`

여기서 핵심 원칙은 아래였다.

- `core slot = polarity + intent + stage`
- `modifier = texture + location + tempo + ambiguity`
- decomposition은 `dominant_side`를 바꾸지 못함
- rejection은 `reversal rejection`과 `friction rejection`으로 분리
- stage는 "언제", texture는 "어떻게"로 분리

### 2-4. 그다음 문제: XAU retained evidence가 가장 선명했다

XAU는 retained log와 screenshot overlap에서
상승 recovery와 하락 rejection 양쪽이 비교적 선명하게 잡혔다.

그래서 XAU를 pilot으로 삼아 아래를 붙였다.

- `xau_pilot_mapping_contract_v1`
- `xau_readonly_surface_contract_v1`
- `xau_decomposition_validation_contract_v1`
- `xau bounded lifecycle canary`
- `xau refined gate timebox audit`

즉 XAU는 목적이 아니라 훈련장이었다.
XAU 전용 예외를 늘리기 위한 것이 아니라,
공용 decomposition 언어가 실제 runtime retained window에 붙는지 검증하는 파일럿이었다.

---

## 3. 왜 이제 "threshold + structure" 이야기가 나왔는가

### 3-1. exact profile match는 필요했지만 너무 딱딱했다

지금까지의 XAU canary는 매우 보수적으로 동작했다.

기본 철학은:

- 우리가 이미 검증한 pilot window와 맞는 장면만
- 아주 좁게
- read-only canary 또는 bounded candidate로 올리자

였다.

이 방식은 안전했다.
하지만 시간이 지나며 아래 문제가 보이기 시작했다.

- 현재 row는 decomposition 기준으로는 꽤 정렬되어 있음
- dominance도 같은 쪽으로 흘러 있음
- ambiguity도 낮음
- stage/location/tempo도 "흐름형"으로 읽힘

그런데도 `exact pilot match` 하나가 안 맞으면
전체 gate가 `FAIL_PILOT_MATCH`로 끝나버렸다.

즉 구조가 실제로 "거의 맞는 장면"이어도,
`pilot window와 exact하게 닮지 않았다`는 이유만으로 문 앞에서 멈추는 일이 생겼다.

### 3-2. 사용자 관찰: "수치가 충분히 강하고 계속 그쪽으로 흐르면 그 방향으로 가야 한다"

여기서 중요한 피드백이 나왔다.

핵심은 이거다.

> 지금 시스템이 너무 `이 수치면 맞고 아니면 틀림` 식으로 간다.
> 하지만 실제 시장은 그렇지 않다.
> state 내부의 여러 값이 종합되어 일정 수준 이상으로 한 방향으로 계속 흐른다면,
> exact profile과 조금 달라도 그 방향성은 인정해야 한다.

이건 단순 감상이 아니라,
지금까지 쌓은 decomposition 구조의 다음 자연스러운 질문이었다.

왜냐하면 decomposition을 한 이유 자체가
`장면을 더 잘 설명하기 위해서`였기 때문이다.
그런데 설명은 더 좋아졌는데 최종 gate는 여전히 exact pilot match만 보면,
설명층과 판정층 사이에 단절이 생긴다.

### 3-3. 그래서 새 질문이 생겼다

새 질문은 아래와 같았다.

1. exact pilot match는 계속 필요하지만, 이것이 유일한 통과 문이어야 하는가?
2. 아니면 decomposition 구조에서 읽힌 여러 증거를 종합한 `aggregate directional flow`가
   두 번째 문이 되어야 하는가?
3. 그때 threshold는 단일 숫자 하드코딩인가,
   아니면 `구조 gate를 통과했을 때만 쓰는 확정 기준`이어야 하는가?

이 문서는 바로 그 질문을 다룬다.

---

## 4. 현재 구조에서 이미 만들어진 것

지금 우리는 이미 아래 층을 가지고 있다.

### 4-1. 인식 / 비교 / 회고 층

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `dominance_accuracy_summary_v1`

이 층은 "보는가 / 비교 가능한가 / hindsight review가 가능한가"를 보장한다.

### 4-2. 해석 층

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `state_structure_dominance_profile_v1`

이 층은 `방향`, `continuation vs reversal`, `friction`, `caution`을 설명한다.

### 4-3. decomposition 층

- `polarity`
- `intent`
- `stage`
- `texture`
- `location`
- `tempo`
- `ambiguity`

이 층은 "같은 continuation이어도 어떤 continuation인가"를 설명한다.

### 4-4. pilot / symbol surface 층

- XAU pilot mapping
- NAS/BTC symbol extension surface
- symbol-specific state strength calibration

이 층은 공용 언어와 심볼별 retained evidence를 연결한다.

### 4-5. execution bridge / lifecycle 층

- `state_slot_execution_interface_bridge`
- `state_slot_position_lifecycle_policy`
- `execution_policy_shadow_audit`
- `bounded_lifecycle_canary`

이 층은 아직 실행을 바꾸진 않지만,
해석이 실제 행동 bias로 어떻게 번역되는지를 read-only로 본다.

즉 지금 부족한 것은 "구조가 없다"가 아니라,
`정확히 어느 시점부터 exact match 밖 장면도 directional flow로 인정할 것인가`이다.

---

## 5. 왜 exact match 단독 구조가 한계에 닿았는가

### 5-1. XAU current row에서 드러난 현상

현재 XAU live row를 보면, decomposition 기준으로는 아래처럼 읽히는 순간이 있다.

- `BULL`
- `RECOVERY`
- `ACCEPTANCE`
- `WITH_FRICTION`
- `POST_BREAKOUT`
- `PERSISTING`
- `LOW ambiguity`
- `dominance = CONTINUATION_WITH_FRICTION`

즉 사람이 보기에도 "완전한 random/noise"가 아니라,
상당히 방향성이 정렬된 장면이다.

그런데 exact pilot match gate에서는 아래가 발생할 수 있다.

- `profile_match = OUT_OF_PROFILE`
- `risk_gate = FAIL_PILOT_MATCH`
- `candidate_state = OBSERVE_ONLY`

즉 decomposition 언어로는 많이 설명되는데,
pilot window exact match가 아니면 최종 문은 닫혀 버린다.

### 5-2. 이건 위험한 두 극단을 만든다

이 구조를 계속 유지하면 두 가지 극단으로 간다.

#### 극단 A. 지나치게 보수적

- 실제로는 흐름형 장면인데
- pilot exact match가 아니라서 계속 보류
- 좋은 continuation / recovery 구간을 늦게 인정함

#### 극단 B. 반대로 무리한 예외 추가

이 보수성을 깨려고 억지로 pilot window를 늘리면,

- `XAU 예외`
- `NAS 예외`
- `BTC 예외`
- `이 장면 예외`

처럼 다시 heuristic 예외가 늘어난다.

즉 exact match 단독 구조는
`너무 보수적이거나`, 아니면 `예외가 폭발하거나`
둘 중 하나로 가기 쉽다.

---

## 6. 그래서 도입하려는 것: Aggregate Directional Flow

### 6-1. 개념

`aggregate directional flow`는 "이 장면이 pilot과 똑같은가"를 묻는 층이 아니다.
이미 만들어 놓은 decomposition / dominance / local structure / state strength 증거를 종합해서,

> 이 장면이 directional flow 후보로 볼 자격이 있는가
> 그리고 그 directional 정렬이 얼마나 강하고 얼마나 이어지고 있는가

를 읽는 층이다.

현재 실험적으로 surface한 핵심 필드는 아래다.

- `aggregate_conviction`
- `flow_persistence`
- `flow_support_state`

그리고 상태는 아래처럼 둔다.

- `FLOW_CONFIRMED`
- `FLOW_BUILDING`
- `FLOW_UNCONFIRMED`
- `FLOW_OPPOSED`

### 6-2. 이 층에서 가장 중요한 원칙

이번 외부 조언을 반영했을 때, 가장 중요한 원칙은 아래 한 줄이다.

> threshold는 "판단 기준"이 아니라 "확신 레벨 분류 기준"이다.

즉 aggregate directional flow는

- 숫자 하나만 넘으면 무조건 통과하는 층이 아니고
- decomposition 구조가 directional flow 후보 자격을 먼저 준 뒤
- 그 안에서 확신 수준을 분류하는 층이다.

그리고 여기서 `aggregate_conviction`은 추상적인 "느낌 점수"가 아니라,
최소 아래 세 축을 반드시 포함해야 하는 합성값으로 보는 편이 맞다.

- `dominance_support`
- `structure_support`
- `decomposition_alignment`

즉 conviction은
"dominance가 그 방향을 얼마나 지지하는가",
"local structure가 그 방향을 얼마나 받쳐주는가",
"decomposition slot이 그 방향 정렬과 얼마나 맞는가"
를 최소 공통 구성축으로 가져야 한다.

### 6-3. 그래서 우선순위는 어떻게 되어야 하는가

현재 가장 자연스러운 권한 구조는 아래다.

1. `Structure Gate`
2. `Aggregate Flow`
3. `Exact Match Bonus`

이 순서가 중요한 이유는 단순 절차가 아니라 권한 구조이기 때문이다.

- `Structure Gate`는 directional flow 후보 자격을 준다
- `Aggregate Flow`는 그 자격 안에서 강도와 지속성을 분류한다
- `Exact Match`는 이미 검증된 장면 우대 보너스만 준다

즉 exact match는 더 이상 유일한 문이 아니라,
검증된 사례에 빠른 통과권이나 bonus를 주는 장치로 내려간다.

---

## 7. 현재까지 실험적으로 본 것

현재 워크스페이스에서 다시 계산해 보면,
심볼별 directional flow 분포는 완전히 같지 않다.

대표적으로:

- NAS는 강한 retained continuation window에서 `structural_support_rate`가 거의 `1.0`에 가까웠다
- BTC는 recovery/reclaim 장면도 `0.5 ~ 0.59` 수준의 mixed 성격이 더 많았다
- XAU는 live current row에서 decomposition 정렬이 좋은데 exact pilot match는 실패하는 장면이 보였다

즉 심볼마다 분포가 다르다.
그래서 `0.7` 같은 숫자를 절대 진리로 박는 것은 맞지 않다.

이 관찰에서 바로 나오는 결론은 두 가지다.

1. 구조 gate는 공용 언어로 유지해야 한다
2. threshold band는 심볼별 calibration을 허용해야 한다

---

## 8. 우리가 실제로 버려야 할 선택지와 유지해야 할 선택지

### 선택지 A. exact pilot match를 계속 유일한 문으로 둔다

장점:

- 안전하다
- rollback이 쉽다
- XAU pilot 운영 의미가 분명하다

단점:

- decomposition을 만들어 놓고도 최종 gate가 너무 딱딱하다
- 거의 맞는 장면을 계속 놓칠 수 있다
- pilot 창고를 계속 늘리게 될 위험이 있다

판단:

- 지금 단계에서는 너무 보수적이다

### 선택지 B. 숫자 threshold만 넘으면 directional flow로 본다

장점:

- 구현이 단순하다
- "일정 수치 이상이면 흐름형"이라는 직관에 맞다

단점:

- structure가 이상한데 우연히 점수만 높아도 통과할 수 있다
- decomposition을 무력화한다
- 다시 threshold tuning 지옥으로 갈 수 있다

판단:

- 지금 단계에서는 금지에 가깝다

### 선택지 C. structure gate + aggregate flow + exact match bonus

개념:

1. 먼저 구조가 directional flow 후보 자격이 있는지 본다
2. 그 다음 conviction과 persistence로 상태를 분류한다
3. exact pilot match는 확신을 올리는 bonus로만 쓴다

장점:

- decomposition 언어를 진짜 쓰게 된다
- exact match만 보는 구조보다 유연하다
- pure threshold 구조보다 안전하다

단점:

- gate 설계가 조금 더 복잡하다
- structure와 숫자를 동시에 calibration해야 한다

판단:

- 현재 가장 균형이 좋고, 우리가 임시로 채택한 방향이다

---

## 9. 현재 임시 선택: 구조가 먼저, 숫자는 확신 분류, exact match는 bonus

### 9-1. 기본 철학

정확히 이렇게 정리할 수 있다.

> exact pilot match는 계속 유지하되,
> 그것을 유일한 통과 문으로 두지 않는다.
> 먼저 decomposition 구조가 directional flow 후보 자격을 주는지 보고,
> 그 다음 aggregate conviction / persistence로 `confirmed / building / unconfirmed / opposed`를 분류한다.
> exact pilot match는 마지막에만 validated bonus로 작동한다.

### 9-2. Structure Gate는 무엇을 하는가

Structure Gate는 숫자를 보기 전에
"이 장면을 directional flow 후보로 올릴 자격이 있는가"를 먼저 가르는 층이다.

현재 가장 자연스러운 공용 gate 조건은 아래다.

여기서 중요한 점은 Structure Gate를 단순 조건 모음으로 두지 않고,
`hard disqualifier`와 `soft qualifier`로 나누어 읽는 것이다.

#### Hard disqualifier

아래는 기본적으로 directional flow 후보 자격을 즉시 박탈하는 조건이다.

- `dominant_side`와 slot polarity 불일치
- `rejection_type == REVERSAL_REJECTION`
- `consumer_veto_tier == REVERSAL_OVERRIDE`
- `ambiguity == HIGH`

즉 이 층에서 걸리면 숫자가 아무리 높아도 directional flow 후보가 아니다.

#### Soft qualifier

아래는 directional flow 후보 자격의 강도와 약도를 나누는 조건이다.

- `stage in {INITIATION, ACCEPTANCE}`를 기본 우선 구간으로 둠
- `tempo`는 최소 `PERSISTING` 성격을 보여야 함
- `breakout_hold_quality >= STABLE` 같은 구조 유지 조건이 필요
- `higher_low / lower_high` 같은 swing 구조 유지가 보일수록 좋음

즉 hard disqualifier는 "무조건 탈락",
soft qualifier는 "ELIGIBLE / WEAK를 나누는 기준"이다.

즉 숫자 이전에,
"이 장면은 directional flow 후보 자격이 있는가"를 먼저 본다.

### 9-3. Threshold는 무엇을 하는가

threshold는 장면의 본질을 정의하는 값이 아니라,
구조 gate를 통과한 장면이 어느 정도 확신 수준인지 나누는 값이다.

즉:

- structure 먼저
- threshold 나중

이 순서다.

그리고 threshold는 한 줄 hard rule보다 아래 같은 band 구조가 자연스럽다.

- `FLOW_CONFIRMED`
- `FLOW_BUILDING`
- `FLOW_UNCONFIRMED`
- `FLOW_OPPOSED`

즉 threshold는 `통과/불통과`보다 `확신 수준 분류`에 가깝다.

그리고 운영 정의는 아래처럼 못 박는 편이 좋다.

- `FLOW_CONFIRMED`
  - `aggregate_conviction`과 `flow_persistence`가 둘 다 높아야 함
- `FLOW_BUILDING`
  - 둘 중 하나가 먼저 앞서고 다른 하나가 따라오는 상태
- `FLOW_UNCONFIRMED`
  - structure는 약하게 통과했거나, 두 값 중 하나 이상이 충분히 안 올라온 상태
- `FLOW_OPPOSED`
  - polarity mismatch 또는 structure fail 쪽에 가까운 상태

즉 confirmed는 "둘 다 높음",
building은 "하나는 앞서고 하나는 따라옴"으로 이해하는 것이 운영상 가장 안정적이다.

### 9-4. Conviction과 Persistence를 왜 따로 봐야 하는가

현재 외부 조언에서 특히 중요했던 포인트는
`aggregate_conviction`과 `flow_persistence`를 분리하라는 점이었다.

이건 맞다.

- conviction은 "지금 얼마나 그 방향으로 정렬되어 있는가"
- persistence는 "그 정렬이 얼마나 유지되고 축적되고 있는가"

를 본다.

즉:

- 높은 점수 1번은 conviction만 높을 수 있고
- 중간 점수 여러 번은 persistence가 더 중요할 수 있다

그래서 현재는 두 값을 separate surface로 유지하고,
최종 `flow_support_state` 분류에서 함께 쓰는 것이 맞다.

중요한 보강 원칙 하나는 아래다.

> `conviction`과 `persistence`를 너무 빨리 하나의 합성값으로 접지 않는다.

처음부터 하나로 접어버리면
"지금은 강하지만 짧은 장면"과
"지금은 중간이지만 오래 누적되는 장면"을 분리하기 어렵다.

그리고 `flow_persistence`는 단순 누적값으로 두면 안 되고,
최근 흐름에 더 큰 가중치를 두는 recency/decay 원칙을 가져야 한다.

즉 운영 원칙은 아래처럼 정리하는 편이 자연스럽다.

> `flow_persistence`는 누적뿐 아니라 decay도 고려한다.
> 최근 N-bar의 persistence가 더 높은 가중치를 가지며,
> 오래된 directional 흐름은 시간이 지나면 영향력이 줄어든다.

이 원칙이 없으면
"예전엔 강했지만 지금은 약해진 장면"이 계속 persistence를 과대 점유할 수 있다.

### 9-5. exact pilot match는 무엇을 하는가

exact pilot match는 이제 아래 역할만 해야 한다.

1. `FLOW_CONFIRMED` 쪽 보너스 가중치
2. 같은 숫자대일 때 빠른 통과 우선권
3. validated 사례 anchor

즉 exact pilot match는
"통과 여부 전체를 결정하는 유일한 문"이 아니라,
`검증된 장면 우대 장치`에 더 가까워진다.

여기서 bonus의 상한선도 같이 고정해야 한다.

> exact pilot match bonus는 structure gate를 통과한 장면에만 적용되며,
> `FLOW_UNCONFIRMED`를 단독으로 `FLOW_CONFIRMED`까지 올릴 수는 없다.

즉 bonus는

- `FLOW_BUILDING -> FLOW_CONFIRMED`
- 같은 구간에서 우선권 상향

정도까지만 허용하고,
`UNCONFIRMED -> CONFIRMED` 직행은 금지하는 것이 자연스럽다.

### 9-6. EXTENSION은 왜 따로 다뤄야 하는가

현재 문서 구조상 `stage`와 `texture`는 분리되어 있다.
그래서 "늦은 자리"와 "품질 저하"도 같이 섞지 말고 처리해야 한다.

운영 원칙은 아래가 가장 자연스럽다.

> `EXTENSION`은 structure gate 통과는 가능하되,
> 기본적으로 `FLOW_CONFIRMED` 상한을 갖지 않으며,
> 신규 directional 인정이 아니라 late continuation 관리 대상으로 본다.

즉 extension은 방향이 맞을 수는 있어도,
"지금 새로 강하게 인정할 장면"과는 다르게 다뤄야 한다.

---

## 10. 공용으로 둘 것과 심볼별로 조정할 것을 분리해야 한다

이번 외부 조언에서 아주 중요한 포인트 중 하나는
`구조는 공용, 숫자는 심볼별`이라는 정리였다.

이 방향이 현재 가장 합리적이다.

### 10-1. 공용으로 유지할 것

- structure gate 구성 요소
- gate 통과 / 실패 논리
- decomposition 언어 전체
- `FLOW_CONFIRMED / BUILDING / UNCONFIRMED / OPPOSED` enum
- exact match bonus의 역할 정의

### 10-2. 심볼별로 calibration할 수 있는 것

- `aggregate_conviction` band
- `flow_persistence` band
- exact match boost 강도
- 일부 penalty scale

즉 `NAS 전용 gate`, `XAU 전용 gate`처럼 구조를 나누는 것이 아니라,
같은 gate를 보되 `threshold profile`을 다르게 두는 쪽이 자연스럽다.

여기서 더 분명히 해둘 필요가 있는 것은
"심볼별로 조정 가능한 것"과 "심볼별로 절대 바꾸면 안 되는 것"의 경계다.

#### 심볼별 조정 허용

- conviction band
- persistence band
- exact bonus strength
- 일부 penalty scale

#### 심볼별 조정 금지

- rejection split 규칙
- dominance 우선권
- structure gate hard disqualifier
- decomposition의 upstream 보호 규칙

즉 숫자와 band는 심볼별 calibration이 가능하지만,
구조 자체를 심볼별 예외로 바꾸는 것은 금지하는 편이 맞다.

---

## 11. 지금 외부 조언이 필요한 이유

우리는 이미 충분히 많은 구조를 만들었고,
문제도 꽤 정확하게 재정의했다.

하지만 이제부터는 방향을 잘못 잡으면 다음 두 위험이 있다.

### 위험 1. threshold overfit

- XAU current row 하나를 살리기 위해 숫자를 너무 낮추면
- NAS/BTC noisy 장면도 같이 통과할 수 있다

### 위험 2. decomposition 무력화

- aggregate 점수만 너무 강조하면
- stage / texture / ambiguity / rejection split을 공들여 만든 이유가 사라진다

그래서 외부 조언이 필요한 포인트는
"숫자를 어떻게 줄일까"가 아니라,

> exact match, structure gate, aggregate flow가
> 어떤 권한 구조로 놓여야 decomposition을 살리면서도 너무 딱딱하지 않은 gate가 되는가

이다.

---

## 12. 외부 조언으로 받고 싶은 핵심 질문

### 질문 1. 문제 정의

현재 문제를
`pilot profile 부족`
으로 보기보다
`exact match gate가 decomposition 구조를 충분히 소비하지 못하는 문제`
로 보는 해석이 맞는가?

### 질문 2. gate 권한 구조

아래 세 층의 자연스러운 권한 구조는 무엇인가?

1. `Structure Gate`
2. `Aggregate Conviction / Flow Persistence`
3. `Exact Pilot Match Bonus`

### 질문 3. threshold 성격

threshold는 독립 hard rule이어야 하는가,
아니면 structure gate 통과 후에만 의미를 갖는 확신 분류 단계여야 하는가?

### 질문 4. exact match의 위치

exact pilot match는 계속 hard gate로 남겨야 하는가,
아니면 `validated bonus / priority boost`로 내려도 되는가?

### 질문 5. symbol-specific vs common

XAU에서 먼저 보이는 directional flow 확정 규칙을
어느 정도까지 NAS/BTC와 공용 언어로 묶고,
어느 정도부터는 symbol-specific threshold를 허용해야 하는가?

### 질문 6. 추천하는 첫 calibration 방식

현재 같은 상황에서,

- XAU retained pilot windows
- NAS strong continuation windows
- BTC mixed recovery windows

를 기준으로
`confirmed / building / unconfirmed / opposed`
구간을 어떻게 잡는 것이 가장 안전한가?

---

## 13. 우리가 현재까지 관찰한 방향성

아직 최종 확정은 아니지만,
지금까지 본 로그와 retained window를 기준으로 한 방향성은 아래와 같다.

1. exact pilot match만으로 계속 가는 것은 너무 딱딱하다.
2. pure numeric threshold만으로 가는 것은 위험하다.
3. `structure-first, threshold-second, exact-match-as-bonus`가 가장 균형이 좋다.
4. `threshold`는 "판단 기준"보다 "확신 수준 분류"로 두는 편이 자연스럽다.
5. `aggregate_conviction`과 `flow_persistence`는 분리해서 본 뒤 최종 분류에서 함께 쓰는 편이 맞다.
6. XAU는 이 프레임을 실험하기 가장 좋은 pilot이지만, 목표는 XAU 예외 확장이 아니라 공용 flow gate 정립이다.
7. NAS/BTC를 보면 symbol별 분포가 다르므로 threshold는 처음부터 절대 진리처럼 박지 말고 calibration 대상으로 두는 편이 맞다.

---

## 14. 현재 우리가 외부 조언을 받은 뒤 하고 싶은 다음 단계

외부 조언을 받는 목적은 바로 실행을 바꾸기 위함이 아니다.

받은 조언을 바탕으로 아래를 하려는 것이다.

1. `flow_structure_gate_v1`를 공용 계약으로 먼저 고정
2. `aggregate_conviction_v1`와 `flow_persistence_v1`를 분리 surface
3. XAU / NAS / BTC retained window를 `confirmed / building / mixed / opposed` 그룹으로 묶음
4. provisional threshold band를 심볼별로 calibration
5. exact pilot match를 hard gate가 아니라 bonus gate로 내릴지 최종 결정
6. 그 후에야 bounded lifecycle canary에 아주 좁게 연결

즉 외부 조언의 목표는 "숫자 하나 정해 주세요"가 아니라,
`이제 우리 구조를 어떤 권한 순서로 소비해야 시스템이 덜 깨지고 더 자연스럽게 진화하는가`
를 같이 보는 것이다.

---

## 15. 한 줄 요약

지금까지는 `정확히 아는 장면만` 다루는 쪽으로 구조를 단단히 만들었다.
이제는 그 위에서

> "state 내부의 여러 값이 종합되어 일정 수준 이상으로 한 방향으로 계속 흐른다면,
> exact profile과 조금 달라도 그 방향성을 인정할 것인가"

라는 질문에 답해야 하는 단계다.

그리고 현재 우리의 임시 답은 아래다.

> 그렇다.
> 다만 숫자만으로 인정하는 것이 아니라,
> decomposition 구조가 먼저 directional flow 후보 자격을 주어야 하며,
> threshold는 그 안에서 확신 수준을 분류하는 장치이고,
> exact pilot match는 유일한 문이 아니라 검증된 장면 bonus로 내려가는 쪽이 가장 유망하다.
