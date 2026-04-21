# Flow Learning Bridge / Bounded Calibration External Review Request

## 1. 이 문서의 목적

이 문서는 단순히 "threshold를 어떻게 튜닝할까"를 묻는 문서가 아니다.

우리는 이미 아래를 상당 부분 구축했다.

- state / local structure / dominance 해석층
- polarity / intent / stage / texture / location / tempo / ambiguity decomposition 층
- exact pilot match를 hard gate에서 bonus로 내린 flow acceptance chain
- read-only execution bridge / lifecycle policy / bounded canary
- should-have-done candidate review와 NAS/BTC hard-opposed audit

즉 지금 부족한 것은 더 많은 해석층이 아니라,

**이미 로그에 남고 있는 구조적 진단 결과를, 구조를 깨지 않으면서 실제 개선으로 연결하는 안전한 다리**

이다.

이 문서는 바로 그 다리,

`learning key -> bounded calibration candidate -> bounded apply / rollback`

가 왜 필요한지, 지금까지의 구축물과 어떻게 연결되는지, 그리고 어떤 부분은 절대 학습 대상으로 풀면 안 되는지를 외부 조언용으로 정리한다.

---

## 2. 지금까지 어떤 구조를 만들었는가

### 2-1. 인식 / 비교 / 계측 층

우리는 먼저 "시장 장면을 보고 있는가", "나중에 비교 가능한가", "왜 그 결론이 나왔는가"를 남기는 계층을 만들었다.

대표적으로:

- `runtime_signal_wiring_audit_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `dominance_accuracy_summary_v1`

이 층의 목적은 정답을 바로 내는 것이 아니라,

- raw runtime row
- runtime detail surface
- hindsight/canonical truth
- candidate review

를 한 자리에서 비교 가능하게 만드는 것이었다.

즉 첫 단계의 핵심은 **"보는 것"과 "비교할 수 있게 남기는 것"** 이었다.

### 2-2. 해석 층

그 다음에는 directional interpretation을 만들었다.

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `state_structure_dominance_profile_v1`

이 층에서 해결하려던 문제는:

- continuation vs reversal
- friction vs real reversal
- wait bias는 원인이 아니라 도출값
- dominance를 absolute strength가 아니라 relative arbitration으로 보기

였다.

즉 두 번째 단계의 핵심은 **"무엇이 실제로 우세한가"** 였다.

### 2-3. decomposition 층

그 다음에는 state 자체가 너무 두껍다는 문제가 나왔다.

예를 들어 같은 continuation 안에도:

- initiation
- acceptance
- extension
- recovery
- continuation with friction
- drift

가 섞여 있었고,
같은 rejection 안에도:

- reversal rejection
- friction rejection

이 섞여 있었다.

그래서 아래 공용 언어를 만들었다.

- `polarity`
- `intent`
- `stage`
- `texture`
- `location`
- `tempo`
- `ambiguity`

그리고 핵심 원칙도 같이 고정했다.

- `core slot = polarity + intent + stage`
- `modifier = texture + location + tempo + ambiguity`
- decomposition은 dominant_side를 바꾸지 못한다
- rejection은 reversal rejection과 friction rejection으로 분리한다
- stage는 "언제", texture는 "어떻게"를 뜻한다

즉 세 번째 단계의 핵심은 **"같은 continuation / rejection도 더 작은 해석 단위로 분해"** 하는 것이었다.

### 2-4. pilot / symbol surface 층

그 다음에는 XAU를 pilot으로 삼아 decomposition 언어가 실제 retained window에 잘 붙는지 확인했다.

- `xau_pilot_mapping_contract_v1`
- `xau_readonly_surface_contract_v1`
- `xau_decomposition_validation_contract_v1`

그리고 그 뒤에 NAS/BTC도 같은 공용 vocabulary로 표면화했다.

- `state_slot_symbol_extension_surface`
- `nas_pilot_mapping_contract_v1`
- `btc_pilot_mapping_contract_v1`

즉 네 번째 단계의 핵심은 **"이 언어가 XAU 전용 예외가 아니라 공용 문법인지 확인"** 하는 것이었다.

### 2-5. flow acceptance 층

그 다음 질문은 이것이었다.

> exact pilot profile과 정확히 같지 않아도,
> 구조와 점수가 충분히 정렬되면 directional flow로 인정해야 하는가?

그래서 다음 권한 구조를 만들었다.

1. `flow_structure_gate_v1`
2. `aggregate_conviction_v1`
3. `flow_persistence_v1`
4. `exact_pilot_match_bonus`
5. `flow_support_state_v1`

핵심 원칙은:

- structure gate가 먼저
- threshold는 판단기가 아니라 확신 분류기
- exact match는 hard gate가 아니라 bonus
- conviction과 persistence는 분리해서 본다

즉 다섯 번째 단계의 핵심은 **"정확히 아는 장면만 처리"에서 "구조가 맞고 충분히 흐르면 인정"으로 전환** 하는 것이었다.

### 2-6. shadow comparison / candidate review 층

그리고 이제 old exact-only와 new flow-enabled chain을 비교할 수 있게 됐다.

- `flow_chain_shadow_comparison_contract_v1`
- `flow_candidate_improvement_review_contract_v1`

여기서 처음으로 아래 질문이 가능해졌다.

- 새 체인이 old exact-only보다 candidate를 더 잘 살렸는가?
- 아니면 과하게 tightening했는가?

즉 여섯 번째 단계의 핵심은 **"새 체인이 좋아졌는지, 나빠졌는지"를 candidate truth 기준으로 평가** 하는 것이었다.

### 2-7. NAS/BTC hard-opposed audit 층

마지막으로, 특히 NAS/BTC에서 `FLOW_OPPOSED`가 과하게 뜨는지 분해하기 위해 아래 audit를 만들었다.

- `nas_btc_hard_opposed_truth_audit_contract_v1`

이 audit는 opposed를 두 층으로 나눈다.

1. **절대 고정해야 하는 hard blocker**
   - `POLARITY_MISMATCH`
   - `REVERSAL_REJECTION`
   - `REVERSAL_OVERRIDE`

2. **학습 가능한 control**
   - ambiguity threshold
   - structure soft score floor
   - conviction building floor
   - persistence building floor
   - ambiguity penalty scale
   - veto penalty scale
   - persistence recency weight

즉 여기서 처음으로,

**"이 row를 학습으로 더 좋게 만들 수 있는가, 아니면 구조상 고정해야 하는가"**

를 row-level에서 분리하게 됐다.

---

## 3. 지금 왜 새 다리가 필요한가

여기까지 오면 시스템은 이미 굉장히 많은 것을 할 수 있다.

예를 들어 지금은 다음을 안다.

- 왜 어떤 장면이 `FLOW_OPPOSED`가 되었는가
- 왜 어떤 장면은 `FLOW_UNCONFIRMED`에 머무는가
- old exact-only보다 새 flow chain이 더 좋아졌는가
- should-have-done candidate를 새 체인이 살렸는가
- NAS/BTC hard-opposed가 fixed blocker인지, tunable score 때문인지

즉 우리는 이미

**"왜 틀렸는지 설명하는 시스템"**

은 만들었다.

그런데 여기서 멈추면 문제가 생긴다.

### 3-1. 설명은 되는데 개선이 수동으로 남는다

예를 들어 BTC row에서 다음이 보인다고 하자.

- `FLOW_OPPOSED`
- `OVER_TIGHTENED`
- fixed blocker 일부 있음
- 동시에 `AMBIGUITY_THRESHOLD`, `CONVICTION_BUILDING_FLOOR`, `RECENCY_WEIGHT_SCALE`도 같이 걸림

이제 우리는 "왜 막혔는지"는 안다.

하지만 그 다음 단계가 없다면 결국:

- 사람이 보고
- threshold를 감으로 조금 내리고
- 다음 날 다시 올리고
- 또 다른 symbol에서 side effect가 생기고

이런 식으로 **수동 튜닝 지옥**으로 돌아가게 된다.

### 3-2. 구조를 보호하면서 개선으로 연결하는 다리가 없다

지금 구조는 이미 아래를 분리하고 있다.

- 절대 건드리면 안 되는 구조
- 조정 가능한 제어값

그런데 이걸 실제 운영 루프로 연결하려면,

- 무엇을 조정 후보로 올릴지
- 어느 폭까지 허용할지
- 어떤 조건일 때만 시험할지
- 나빠지면 어떻게 되돌릴지

를 담당하는 중간 다리가 필요하다.

즉 지금 필요한 것은 또 다른 해석층이 아니라,

**분석 결과를 안전한 개선 후보로 변환하는 운영 브리지**

이다.

---

## 4. 이 다리가 없으면 어떤 문제가 생기는가

### 4-1. 로그는 잘 남는데 실제로는 사람이 감으로 만지게 된다

시스템은 점점 더 설명력이 좋아지는데,
반영은 결국 수동이면
축적된 구조적 진단이 실제 개선으로 연결되지 않는다.

### 4-2. 고정 규칙과 학습 규칙이 다시 섞인다

예를 들어 should-have-done truth를 더 잘 맞추고 싶다는 이유로:

- polarity mismatch
- reversal rejection

같은 hard blocker까지 건드리기 시작하면 구조가 무너진다.

즉 "무엇은 절대 고정"이고 "무엇만 조정 가능"인지를 실제 운영에서 강제하는 레이어가 필요하다.

### 4-3. 작은 개선이 큰 부작용으로 번질 수 있다

예를 들어 BTC에서 ambiguity threshold를 조금 완화하고 싶다고 하자.

그걸 바로 전 심볼 / 전 구간에 반영하면:

- over-veto는 줄지만
- false widening이 늘 수 있다
- NAS/XAU에 예기치 않은 영향을 줄 수 있다

즉 조정은 **bounded** 되어야 한다.

### 4-4. rollback 기준이 없으면 "학습"이 아니라 "위험한 실험"이 된다

조정 후 성능이 나빠졌을 때:

- 무엇을 근거로
- 언제
- 어떤 값으로

되돌릴지 규칙이 없다면, 시스템은 점점 불안정해진다.

---

## 5. 그래서 필요한 것이 무엇인가

우리가 필요한 것은 대략 아래 3단계다.

### 5-1. learning key -> bounded calibration candidate

먼저 조정 가능한 key 중에서,

- 이번 문제와 실제로 관련 있는 것만
- 아주 작은 폭으로
- 근거와 함께

조정 후보로 뽑아야 한다.

예:

- `flow.ambiguity_threshold` 완화 후보
- `flow.persistence_building_floor` 소폭 하향 후보
- `flow.persistence_recency_weight_scale` 재조정 후보

이 단계의 목적은:

**"무엇을 바꿀까"를 감이 아니라 구조적 로그로 좁히는 것**

이다.

여기서 중요한 것은 candidate 단위를 너무 잘게 쪼개지 않는 것이다.

- 기본 candidate id는 `symbol × learning_key`
- `truth_error_type`은 candidate id가 아니라 evidence cluster로 붙인다
- timebox는 candidate 정체성이 아니라 검증 창으로만 쓴다

즉

- `BTCUSD:flow.ambiguity_threshold`
- `NAS100:flow.conviction_building_floor`

같은 형태가 기본 단위이고,
`OVER_TIGHTENED`, `WIDEN_EXPECTED`, `MIXED_REVIEW` 같은 정보는
"왜 이 candidate가 올라왔는가"를 설명하는 근거로 붙는 편이 더 안정적이다.

또한 candidate는 만들 수 있다고 해서 모두 살아남으면 안 된다.
중간에 **candidate filtering layer**가 있어야 한다.

권장 필터는 아래와 같다.

- row 하나에서 review 대상으로 올리는 learning key는 최대 2개
- 실제 shadow / bounded apply에 동시에 활성화하는 key는 가능하면 1개
- fixed blocker만 있는 row는 candidate 생성 금지
- `MIXED_REVIEW`는 tunable 부분만 허용하되 confidence를 낮춘다
- 최근 rollback된 같은 `symbol × learning_key`는 즉시 재제안하지 않는다

즉 이 단계는 단순 후보 생성이 아니라,

**"학습 가능한 손잡이 중 실제로 시험해볼 가치가 있는 아주 좁은 후보만 남기는 정제 단계"**

여야 한다.

### 5-2. bounded apply

후보를 곧바로 전체 시스템에 적용하지 않고,

- 특정 symbol만
- 특정 state만
- 특정 구간만
- shadow 또는 log-only부터

아주 좁게 시험해야 한다.

이 단계의 목적은:

**"좋은 후보를 작은 위험으로 실험"**

하는 것이다.

여기서 한 가지 더 중요한 것은,
한 row에서 좋아졌다고 바로 좋은 candidate라고 결론내리면 안 된다는 점이다.

즉 bounded apply에는 **cross-window validation**이 같이 있어야 한다.

- 같은 symbol의 다른 retained / live window에서도 부작용이 없는가
- 동일 symbol의 다른 state 구간에서 false widening이 급증하지 않는가
- 공용 파라미터라면 다른 symbol에서 drift가 생기지 않는가

즉 timebox는 candidate identity가 아니라,

**"이 candidate가 특정 한 장면에만 맞는 국소 최적화가 아닌지 검증하는 시험장"**

으로 써야 한다.

권장 apply scope는 아래와 같이 아주 좁게 시작하는 편이 좋다.

- symbol 1개만
- learning key 1개만
- shadow_only부터
- 필요한 경우 특정 flow state나 review bucket에만
- 최근 제한된 window에서 먼저 관찰

이 원칙이 있어야 "좋아 보이는 row 하나"가 전체 시스템을 끌고 가는 local optimization trap을 막을 수 있다.

### 5-3. rollback / governance

실험 결과가 나빠지면,

- 어떤 지표를 근거로
- 언제
- 어디까지 되돌릴지

가 같이 있어야 한다.

이 단계의 목적은:

**"개선 루프가 시스템을 깨지 못하게 하는 것"**

이다.

권장 rollback / governance 최소 지표는 아래와 같다.

- `over_veto_rate`
- `under_veto_rate`
- `unverified_widening_rate`
- `cross_symbol_drift`

즉 "통과가 늘었다"만 볼 것이 아니라,

- 과한 tightening이 실제로 줄었는가
- 반대로 놓치지 말아야 할 걸 너무 통과시키기 시작했는가
- 아직 truth로 검증되지 않은 widening이 급증했는가
- 공용 파라미터 변경이 다른 symbol 분포를 흔들었는가

를 같이 봐야 한다.

운영 규칙도 같이 필요하다.

- 동시 active candidate 수는 매우 작게 유지한다
- 같은 key를 연속 RELAX하기 전에는 충분한 shadow 관찰 기간을 둔다
- rollback이 발생한 candidate 이력은 남기고, 즉시 같은 방향으로 반복 제안하지 않는다

즉 governance는 단순한 "되돌리기 버튼"이 아니라,

**"좋은 candidate만 천천히 졸업시키고, 나쁜 candidate는 빨리 격리하는 운영 규칙"**

이어야 한다.

---

## 6. 이 다리는 기존 구조와 어떻게 연결되는가

이 다리는 기존 구조를 대체하지 않는다.
기존 구조 위에 얹힌다.

연결은 대략 이렇게 된다.

1. `flow_structure_gate_v1`
2. `aggregate_conviction_v1 / flow_persistence_v1`
3. `flow_support_state_v1`
4. `flow_chain_shadow_comparison`
5. `flow_candidate_improvement_review`
6. `nas_btc_hard_opposed_truth_audit`
7. **learning key -> bounded calibration candidate**
8. **bounded apply**
9. **rollback / governance**

즉 새 다리는

- 해석층 이후
- shadow comparison 이후
- truth alignment 이후

에 위치해야 한다.

그래야:

- 구조를 건드리지 않고
- 튜닝 가능한 제어부만
- 실제 개선 loop로 연결할 수 있다.

---

## 7. 무엇은 절대 고정하고, 무엇은 학습 대상으로 남겨야 하는가

### 7-1. 고정해야 하는 것

이 부분은 learning으로 풀면 안 된다.

- rejection split 규칙 자체
- dominance 우선권
- `dominance_gap` 계산 구조 자체
- polarity mismatch의 의미
- reversal rejection의 의미
- reversal override의 의미
- decomposition이 dominant_side를 못 바꾸는 원칙
- calibration / learning bridge가 dominant_side를 바꾸지 못하는 원칙
- exact match가 bonus라는 원칙

즉 이건 **시스템의 헌법**이다.

여기서 특히 중요한 것은,
학습이 허용되는 것은 어디까지나

- threshold band
- penalty scale
- recency weighting
- soft qualifier floor

같은 **해석 이후의 제어부**라는 점이다.

반대로 아래는 calibration 대상이 아니다.

- side 자체를 바꾸는 규칙
- gap을 계산하는 구조
- reversal을 friction처럼 취급하게 만드는 규칙 완화

즉 learning bridge는 판단기의 뼈대를 바꾸는 것이 아니라,
이미 고정된 판단기 위에서 조정 가능한 손잡이만 다루는 층이어야 한다.

### 7-2. 학습 가능한 것

이 부분은 bounded calibration 대상으로 둘 수 있다.

- ambiguity threshold
- structure soft score floor
- conviction building/confirmed floor
- persistence building/confirmed floor
- ambiguity penalty scale
- veto penalty scale
- recency/decay weighting
- symbol-specific threshold profile

즉 이건 **구조를 표현하는 제어 손잡이**다.

---

## 8. 지금 live snapshot이 보여주는 것

현재까지 구축된 audit 결과를 보면:

- NAS는 current snapshot에서 `FIXED_HARD_OPPOSED`에 더 가깝다
  - 즉 구조상 반대 정렬이 본체다
- BTC는 `MIXED_REVIEW`다
  - fixed blocker도 있고
  - 동시에 tuning 가능한 driver도 많이 걸려 있다

이건 중요한 신호다.

왜냐하면 "모든 over-tightened row를 학습 후보로 올리는 것"이 틀렸다는 걸 보여주기 때문이다.

현재 구조는 오히려 이렇게 말한다.

- NAS current row는 지금은 learning보다 구조 보호가 우선
- BTC current row는 learning candidate로 좁혀볼 가치가 있음

즉 **symbol마다 동일한 over-tightening처럼 보여도, 실제 대응은 달라야 한다** 는 뜻이다.

이 차이는 learning bridge의 운영 방식에도 바로 반영되어야 한다.

- `FIXED_HARD_OPPOSED`는 설명용으로 남기되 candidate 생성은 막는다
- `MIXED_REVIEW`는 tunable 부분만 제한적으로 candidate로 올린다
- pure tunable over-tightening이 쌓이는 구간이 가장 우선적인 bounded calibration 대상이다

즉 모든 오류를 같은 "학습 후보"로 다루지 말고,
row의 구조적 성격에 따라 candidate confidence와 scope를 다르게 둬야 한다.

---

## 9. 외부 조언이 필요한 핵심 질문

우리는 지금 아래 질문에 대한 외부 검토를 받고 싶다.

### 질문 1

지금까지 구축한

- flow gate
- candidate review
- hard-opposed truth audit

위에

`learning key -> bounded calibration candidate -> bounded apply / rollback`

다리를 얹는 것이 자연스러운 다음 단계인가?

### 질문 2

고정 규칙과 학습 규칙의 현재 분리가 적절한가?

특히 아래를 immutable로 유지하는 것이 맞는가?

- polarity mismatch
- reversal rejection
- reversal override
- `dominance_gap` 계산 구조
- calibration이 dominant_side를 바꾸지 못하는 원칙

### 질문 3

bounded calibration candidate는 어떤 단위로 만들어야 가장 안전한가?

- 기본 단위를 `symbol × learning_key`로 두고
- truth-error-type은 evidence cluster로만 붙이는 방향이 적절한가?
- state별 / timebox별 candidate identity까지 내려가는 것은 아직 과한가?

중 어디가 가장 적절한가?

### 질문 4

learning key를 바로 수치 patch로 만들기 전에,

- candidate score
- confidence
- max delta
- apply scope

를 어떤 구조로 묶는 것이 좋은가?

또한 candidate filtering layer에서

- row당 최대 key 수
- active candidate 수 상한
- recently rolled-back key 억제

같은 규칙을 먼저 두는 것이 적절한가?

### 질문 5

rollback / governance는 어떤 지표를 최소 기준으로 삼는 것이 좋은가?

예:

- over-veto 감소
- under-veto 악화 여부
- unverified widening 증가 여부
- symbol-specific drift 증가 여부

그리고

- same-symbol cross-window validation
- shared/common parameter의 cross-symbol validation

을 rollback 전 확인 항목으로 같이 두는 것이 적절한가?

### 질문 6

BTC처럼 `MIXED_REVIEW`인 row를 calibration 대상으로 다룰 때,
fixed blocker와 tunable driver가 같이 섞여 있으면

- 완전 제외해야 하는가
- 부분적 bounded candidate로 허용해야 하는가

### 질문 7

이 learning bridge가

- 구조를 보호하면서
- 수동 threshold tweaking을 줄이고
- should-have-done truth와 실제 live tuning을 연결하는

안전한 운영 루프로 설계되려면 무엇을 더 추가해야 하는가?

---

## 10. 한 줄 요약

우리는 이제

**"왜 틀렸는지 설명하는 시스템"**

은 만들었다.

지금 필요한 것은,

**그 설명을 구조를 깨지 않고 실제 개선 후보로 바꾸는 안전한 다리**

다.

즉 문제는 더 많은 state를 만들거나 더 많은 threshold를 추가하는 것이 아니라,

**이미 분리된 fixed rule과 tunable control을 이용해,
어떤 tuning만 제한적으로 허용할지를 정하는 운영 브리지**

를 어떻게 설계할 것인가이다.
