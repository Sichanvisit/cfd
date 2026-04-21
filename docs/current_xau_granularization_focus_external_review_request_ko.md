# XAU 세분화 집중 전략 외부 조언 요청 정리

## 1. 이 문서의 목적

이 문서는 단순히 "XAU를 더 손보자"는 메모가 아니다.

지금 시스템이 왜 `state strength / local structure / dominance` 층까지 오게 되었는지,
어떤 배선과 계측을 먼저 구축했는지,
그리고 왜 **지금 시점에서는 XAU만 더 세분화해서 파는 것이 가장 효율적인지**를
다른 모델이나 리뷰어가 바로 이해할 수 있도록 정리한 외부 조언 요청 문서다.

즉 이 문서의 목적은 아래 세 가지다.

1. 지금까지의 구축 흐름을 압축해 설명한다.
2. 현재 시스템이 이미 갖고 있는 것과 아직 부족한 것을 나눈다.
3. 다음 집중 타깃을 `XAU 세분화`로 좁히는 이유를 명확히 한다.

---

## 2. 왜 여기까지 오게 되었는가

처음 문제는 단순히 "차트 표기가 어색하다"였다.
하지만 실제 로그를 까보니 문제는 세 단계로 나뉘었다.

### 2-1. 1단계: 인식조차 안 되는가

초기엔 다음을 먼저 확인해야 했다.

- current-cycle overlay가 row에 실리는가
- execution diff가 실제로 남는가
- flow history와 runtime row가 맞물리는가
- detail payload가 비지 않고 계속 surface되는가

이 단계에서 해결한 것은 주로 배선과 안정성이다.

- `execution_diff_surface_count`
- `flow_sync_match_count`
- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`

즉 "못 보는가"보다 먼저 "본 게 제대로 남는가"를 닫았다.

### 2-2. 2단계: 방향을 보는데 왜 실행이 안 따라가는가

그 다음엔 이런 문제가 드러났다.

- runtime row는 `BUY_WATCH`
- overlay도 `UP`
- 그런데 execution은 `WAIT` 또는 `SELL`

즉 시스템이 방향을 전혀 못 읽는 게 아니라,
**방향을 보고도 guard / promotion / barrier / wait bias에 소비되는 문제**가 컸다.

이걸 보기 위해 다음 층을 만들었다.

- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session_aware_annotation_accuracy_summary_v1`
- `session_bias_shadow_summary_v1`

즉 "무엇을 봤는가"와 "무엇을 했는가"를 분리해서 보기 시작했다.

### 2-3. 3단계: 진짜 병목은 인식 실패가 아니라 dominance 실패다

로그와 스크린샷을 붙여보니 핵심이 더 좁혀졌다.

문제는:

- 방향 후보를 못 만드는가?
  - 아니다.
- continuation 구조를 못 보는가?
  - 아니다.
- 그럼 왜 체감상 자꾸 틀리게 보이는가?
  - **이미 본 신호들 사이에서 누가 우세권을 가져가느냐가 틀어져 있기 때문**이다.

즉 현재 병목은:

- `reversal evidence`
- `continuation with friction`
- `wait/reduce/soft block`

이 셋이 같은 무게로 continuation을 눌러버리는 데 있다.

그래서 다음 구조가 필요해졌다.

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `state_structure_dominance_profile_v1`

---

## 3. 지금까지 실제로 구축된 것

현재 시스템에는 단순 메모 수준이 아니라, 아래 계층이 이미 살아 있다.

### 3-1. 기존 관측/검증 축

- `CA2 / R0 ~ R6-A`
- `execution_diff_*`
- `flow sync`
- `continuation accuracy`
- `session split`
- `should-have-done`
- `canonical surface`
- `session bias shadow`

즉 "잘 보이는지 / 실행이 어긋나는지 / 세션 차이가 있는지 / 나중에 뭐가 정답이었는지"를 이미 비교 가능한 상태다.

### 3-2. state/local structure/dominance 층

이미 구현된 층:

- `S0` 기존 계측 안정 guard
- `S1` `state_strength_profile_v1`
- `S2` `local_structure_profile_v1`
- `S3` runtime read-only surface
- `S4` dominance resolver shadow-only
- `S5` should-have-done / canonical validation
- `S6` dominance accuracy / shadow bias
- `S7` symbol-specific calibration scaffold

즉 지금은 "아이디어만 좋은 상태"가 아니라,
실제 runtime row에 state/local/dominance가 다 surface되는 상태다.

### 3-3. S7의 최근 구조 변화

원래 S7은 너무 거칠었다.

- `NAS100 = ACTIVE_CANDIDATE`
- `XAUUSD = SEPARATE_PENDING`
- `BTCUSD = SEPARATE_PENDING`

하지만 사용자 피드백으로 이 구조를 바꿨다.

이제는:

- `symbol × direction × subtype`

기준으로 profile family를 관리한다.

예:

- `NAS100_UP_CONTINUATION_BREAKOUT_HELD`
- `XAUUSD_UP_CONTINUATION_RECOVERY_RECLAIM`
- `XAUUSD_DOWN_CONTINUATION_UPPER_REJECT_REJECTION`
- `BTCUSD_UP_CONTINUATION_LOWER_RECOVERY_REBOUND`
- `BTCUSD_DOWN_CONTINUATION_UPPER_DRIFT_FADE`

즉 모든 심볼은 양방향 continuation을 가질 수 있고,
각 방향은 구조 subtype으로 더 쪼개서 본다.

---

## 4. 로그와 스크린샷을 보고 어떤 결론에 도달했는가

### 4-1. NAS에서 배운 것

NAS에서는 다음 패턴이 반복됐다.

- 구조는 분명 `UP continuation`
- `BREAKOUT_HELD`, `ABOVE`, `WITH_HTF`
- overlay는 `UP`, runtime은 `BUY_WATCH`
- 그런데 `upper_reject_confirm`, `wait_bias`, `reduce_alert`가 continuation을 눌렀다

즉 NAS는 "강세를 못 본다"가 아니라
**강세를 봐도 상단 caution이 너무 싸게 우세권을 뺏어가는 문제**였다.

이 관찰은 state/local/dominance 층을 만드는 직접 계기가 됐다.

### 4-2. XAU에서 배운 것

XAU는 NAS보다 더 중요했다.
왜냐하면 XAU는 로그상으로 이미 양방향이 둘 다 선명하게 분리됐기 때문이다.

보존된 로그 겹침 구간에서 확인된 것:

- `00:30~02:00`
  - 실제 `DOWN continuation`
  - 상단 rejection이 진짜 하락 continuation으로 작동
- `02:00~03:00`
  - `UP recovery continuation`
  - 그런데 시스템이 SELL probe 습관으로 과잉 veto
- `03:30~04:30`
  - 다시 `DOWN continuation`
- `05:00~06:42`
  - 다시 `UP recovery continuation`

즉 XAU는 지금 이미:

- `UP_CONTINUATION / RECOVERY_RECLAIM`
- `DOWN_CONTINUATION / UPPER_REJECT_REJECTION`

두 family가 로그상으로 꽤 분명하게 잡혔다.

### 4-3. BTC에서 배운 것

BTC는 지금 XAU보다 덜 선명하다.

이번 retained overlap에서 보인 건:

- `UP recovery / reclaim`은 어느 정도 잡힌다
- `DOWN drift/fade`는 차트 체감은 있어도 retained 로그에선 아직 혼합도가 크다

즉 BTC는 방향 family 이름은 잡혔지만,
아직 active candidate로 승격할 만큼 데이터가 깨끗하진 않다.

---

## 5. 왜 지금 XAU만 더 세분화하는 게 효율적인가

핵심은 이거다.

**XAU는 지금 세 가지가 동시에 만족된다.**

### 5-1. 양방향 family가 이미 로그로 잡혔다

XAU는 지금:

- 상승 continuation
- 하락 continuation

둘 다 retained log에서 반복적으로 보였다.

즉 "가설"이 아니라 "이미 보인 구조"를 더 쪼개는 단계다.

### 5-2. XAU는 subtype 분해의 값이 바로 크다

XAU에서는 같은 상단/같은 box 위치라도 의미가 다르다.

- 어떤 구간은 `상단 rejection = 진짜 하락 continuation`
- 어떤 구간은 `상단/중단 회복 = 상승 recovery continuation`

즉 XAU는 subtype을 잘못 묶으면 오판이 크게 난다.
반대로 subtype을 잘 분해하면 곧바로 품질 향상이 나올 가능성이 높다.

### 5-3. XAU는 should-have-done 후보도 가장 많이 쌓였다

최근 요약에서도 XAU가 review 후보를 가장 많이 만들었다.

즉 XAU는:

- 실제 오판/과잉 veto 케이스가 많고
- 로그도 남아 있고
- 양방향 family도 보였고
- subtype 분해 필요성도 분명하다

그래서 지금 가장 효율적인 다음 타깃이 된다.

### 5-4. NAS와 BTC보다 "당장 손댈 수 있는 밀도"가 높다

- NAS는 상승 쪽은 강하지만 하락 family는 아직 pending이다.
- BTC는 상승 쪽도 아직 mixed가 많고 하락은 더 혼합적이다.
- XAU는 양방향이 둘 다 active candidate로 올릴 정도의 설명력이 있다.

즉 XAU는 지금 **가장 먼저 세분화 실험을 해볼 만한 심볼**이다.

---

## 6. 지금 외부 조언이 필요한 이유

현재 시스템은 "뭘 더 붙일까" 단계가 아니라,
**이미 붙은 신호들을 어떻게 더 잘 분해하고 우세권을 재배분할까** 단계다.

이때 외부 조언이 필요한 이유는 다음과 같다.

1. XAU subtype을 어디까지 쪼개는 게 적절한가
2. `upper rejection`이 언제 진짜 하락 continuation이고, 언제 단순 friction인가
3. `recovery continuation`을 `lower reclaim`, `mid reclaim`, `upper reclaim`으로 더 쪼개야 하는가
4. `should-have-done`와 subtype calibration을 어떻게 더 직접 연결할 것인가
5. XAU에서 세분화한 프레임을 NAS/BTC에도 같은 틀로 옮길 때 무엇을 공용화하고 무엇을 심볼별 값으로 남겨야 하는가

즉 지금은 "새 feature 추가"보다
**세분화 기준과 calibration 철학을 검증받는 조언**이 더 값이 크다.

---

## 7. 외부 리뷰어에게 묻고 싶은 핵심 질문

1. XAU `UP_CONTINUATION`은 `RECOVERY_RECLAIM` 하나로 충분한가, 아니면 `LOWER_RECOVERY`, `MID_RECLAIM`, `UPPER_RECLAIM`으로 더 쪼개야 하는가?
2. XAU `DOWN_CONTINUATION`에서 `UPPER_REJECT_REJECTION` 하나로 충분한가, 아니면 `FAIL_CONFIRM`, `MIXED_REJECT`, `OUTER_BAND_DRIFT`로 더 쪼개야 하는가?
3. subtype 분해는 먼저 `reason family` 중심으로 갈지, `local structure state` 중심으로 갈지 어떤 쪽이 더 안정적인가?
4. XAU 세분화에서 가장 먼저 calibration teacher로 삼아야 할 오류 타입은 무엇인가?
5. XAU에서 검증된 subtype family를 NAS/BTC로 옮길 때, 공용 계약은 어디까지 유지하고 값만 어떻게 분리하는 게 맞는가?

---

## 8. 한 문장 결론

지금은 모든 심볼을 동시에 더 깊게 파는 것보다,
**양방향 continuation family가 이미 잡힌 XAU를 먼저 더 세분화해서 subtype calibration 틀을 완성하고, 그 틀을 NAS/BTC에 확장하는 것이 가장 효율적인 단계**다.
