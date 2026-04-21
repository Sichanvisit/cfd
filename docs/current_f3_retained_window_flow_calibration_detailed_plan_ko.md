# F3. Retained Window Calibration 상세 계획

## 1. 목적

F3의 목적은 `aggregate_conviction_v1 / flow_persistence_v1`를 나중에 calibration할 때 기준이 되는 retained window 집합을 먼저 고정하는 것이다.

즉 F3는:

- "어떤 window를 calibration truth set처럼 볼 것인가"
- "어떤 window는 confirmed positive이고, 어떤 window는 building positive이며, 어떤 window는 mixed인가"
- "심볼별 provisional threshold band를 어디서부터 시작할 것인가"

를 코드와 문서에서 같은 카탈로그로 보게 만드는 단계다.

---

## 2. 왜 F3가 필요한가

F2까지 오면 이제 공용 숫자는 생겼다.

- `aggregate_conviction_v1`
- `flow_persistence_v1`

하지만 숫자가 생겼다고 바로 threshold를 박으면 다시 tuning 지옥으로 간다.

그래서 F3에서는 threshold를 정하기 전에 먼저 다음을 고정해야 한다.

1. retained window catalog
2. window group
3. symbol-specific provisional threshold profile

즉 F3는 "숫자를 튜닝하는 단계"가 아니라,
"나중에 숫자를 조정할 때 기준으로 삼을 retained set을 잠그는 단계"다.

---

## 3. retained window를 왜 calibration anchor로 쓰는가

지금까지 쌓은 retained evidence는 이미 다음을 통과한 자산이다.

- decomposition 언어로 설명 가능
- pilot mapping에 올라와 있음
- readonly surface로 확인 가능
- validation과 should-have-done에서 다시 볼 수 있음

즉 이 retained windows는 단순 screenshot이 아니라,
"우리가 이미 여러 층에서 검증 가능한 장면"이다.

그래서 F3의 철학은 이렇다.

- exact match를 최종 하드 게이트로 유지하는 대신
- retained windows를 calibration anchor로 유지한다

즉 retained window는 "통과 여부를 영원히 결정하는 문"이 아니라,
"나중에 flow threshold band를 조정할 때 기준이 되는 검증 anchor"다.

---

## 4. F3에서 고정할 그룹

F3는 각 retained window를 아래 그룹 중 하나로 묶는다.

- `CONFIRMED_POSITIVE`
- `BUILDING_POSITIVE`
- `UNCONFIRMED_MIXED`
- `OPPOSED_FALSE`

의미는 다음과 같다.

### 4-1. `CONFIRMED_POSITIVE`

- 사람이 봐도 directional flow가 확실했고
- decomposition slot이 안정적으로 붙었으며
- later threshold calibration에서 confirmed band 하한을 잡는 기준이 되는 window

예:

- XAU의 core bear rejection acceptance
- NAS의 strong bull continuation acceptance

### 4-2. `BUILDING_POSITIVE`

- flow 방향은 맞았지만
- 아직 initiation이거나
- ambiguity / friction / late texture 때문에 confirmed anchor로는 이르지만
- building band calibration에는 충분히 가치가 있는 window

예:

- XAU의 early recovery initiation
- NAS extension continuation

### 4-3. `UNCONFIRMED_MIXED`

- slot 언어로는 설명 가능하지만
- ambiguity가 크거나
- review-pending이거나
- exact pilot validated anchor로 승격되기엔 아직 이른 window

예:

- BTC mixed recovery / drift windows
- NAS down-side pending window

### 4-4. `OPPOSED_FALSE`

- 현재 retained catalog에는 거의 없을 수 있지만
- 나중에 확실한 false directional flow example이 생기면 opposed calibration anchor로 넣는 그룹

중요:

- F3 초기 버전은 `OPPOSED_FALSE`가 0건이어도 괜찮다.
- 지금은 positive / building / mixed를 먼저 고정하는 게 우선이다.

---

## 5. 심볼별 provisional threshold profile

F3에서는 아직 최종 band를 확정하지 않는다.
대신 "첫 calibration 출발점"을 심볼별로 surface한다.

핵심 원칙:

- 구조는 공용
- 숫자 band는 심볼별

예시 출발점:

### XAU

- `flow_threshold_profile_v1 = XAU_TUNED`
- `aggregate conviction confirmed/building floor`
- `flow persistence confirmed/building floor`
- `min persisting bars`

XAU는 retained evidence가 가장 선명하므로,
review anchor보다 common frame 검증 anchor 역할이 크다.

### NAS

- `flow_threshold_profile_v1 = NAS_TUNED`

NAS는 strong continuation evidence가 명확하므로,
confirmed floor는 비교적 높게 잡을 수 있다.

### BTC

- `flow_threshold_profile_v1 = BTC_TUNED`

BTC는 mixed recovery와 drift가 많으므로,
review-pending windows를 더 넓게 가지고 partial-ready 성격으로 시작하는 편이 안전하다.

---

## 6. 공용과 심볼별의 경계

F3에서 다시 한 번 명시해야 할 핵심 경계는 아래와 같다.

### 심볼별로 조정 가능한 것

- conviction confirmed/building floor
- persistence confirmed/building floor
- min persisting bars
- exact bonus strength

### 심볼별 예외로 바꾸면 안 되는 것

- rejection split 규칙
- dominance 우선권
- structure gate hard disqualifier
- extension confirmed cap

즉 F3는 숫자 band를 심볼별로 시작할 수 있게 하지만,
구조 자체를 심볼별로 찢는 단계는 아니다.

---

## 7. row-level surface

F3에서 live row에 남길 최소 필드는 다음과 같다.

- `retained_window_flow_calibration_profile_v1`
- `flow_threshold_profile_v1`
- `aggregate_conviction_confirmed_floor_v1`
- `aggregate_conviction_building_floor_v1`
- `flow_persistence_confirmed_floor_v1`
- `flow_persistence_building_floor_v1`
- `flow_min_persisting_bars_v1`
- `retained_window_calibration_state_v1`
- `retained_window_calibration_reason_summary_v1`

이 필드는 현재 row 자체의 최종 통과 여부를 바꾸기 위한 것이 아니다.
오히려 later phases에서:

- F4 threshold tuning
- F5 exact bonus 재배치
- XAU/NAS/BTC shadow comparison

을 위한 calibration metadata다.

---

## 8. summary artifact

F3 summary는 아래를 포함한다.

- `retained_window_count`
- `retained_window_group_count_summary`
- `threshold_profile_count_summary`
- `retained_window_calibration_state_count_summary`
- `symbol_group_count_summary_v1`
- `threshold_profiles_v1`

즉 summary만 봐도:

- 어느 symbol에 confirmed/building/mixed anchor가 몇 개 있는지
- 현재 provisional band가 어떤 값으로 시작하는지
- 어떤 symbol이 partial-ready인지

를 바로 읽을 수 있어야 한다.

---

## 9. 완료 기준

- XAU/NAS/BTC pilot windows가 한 calibration catalog로 묶인다
- 각 window가 retained group으로 분류된다
- 각 symbol에 provisional threshold profile이 surface된다
- runtime detail에 contract/summary/artifact가 export된다
- 이후 F4에서 숫자 band 조정만 하면 되게 준비된다

상태 기준:

- `READY`
  - retained window catalog와 provisional band profile이 모두 surface됨
- `HOLD`
  - 일부 symbol은 partial-ready지만 catalog는 유지됨
- `BLOCKED`
  - retained window grouping이나 threshold profile export가 깨짐
