# XAU 세분화 집중 실행 로드맵

## 1. 이 로드맵의 목적

이 문서는 단순히 "XAU를 더 잘 보자"는 메모가 아니다.

지금까지 구축한 `CA2 / R0~R6-A / S0~S7` 위에서,
왜 지금은 XAU를 먼저 더 잘게 쪼개는 것이 효율적인지,
그리고 그 세분화를 어떤 순서로 진행해야 흔들리지 않는지 정리한 실행 로드맵이다.

핵심 목적은 세 가지다.

1. XAU를 `상승/하락 continuation` 기준으로 더 세분화해도 기존 계측이 깨지지 않게 한다.
2. XAU에서 subtype 기준을 먼저 안정화한 뒤, 그 구조를 NAS/BTC로 일반화할 수 있게 만든다.
3. "감으로 subtype를 늘리는 것"이 아니라, retained log / screenshot / should-have-done / dominance validation을 근거로 subtype를 고정한다.

---

## 2. 왜 지금은 XAU만 먼저 깊게 들어가는가

지금까지 로그와 스크린샷을 대조한 결과, XAU는 세 가지 조건을 동시에 만족한다.

### 2-1. 양방향 continuation이 retained log에서 모두 잡힌다

XAU는 이미 보존된 로그에서 아래 두 family가 분명히 보였다.

- `UP_CONTINUATION / RECOVERY_RECLAIM`
- `DOWN_CONTINUATION / UPPER_REJECT_REJECTION`

즉 XAU는 "상승만 잘 읽는 심볼"도 아니고, "하락만 잘 읽는 심볼"도 아니다.
양방향 continuation을 모두 실전 로그에서 확인할 수 있었고,
이건 subtype 세분화의 시작점으로 매우 유리하다.

### 2-2. XAU는 subtype 분해의 값이 바로 크다

XAU에서는 같은 `ABOVE`, 같은 `UPPER_EDGE`, 같은 rejection처럼 보여도 실제 의미가 갈린다.

- 어떤 구간은 `상단 rejection = 진짜 하락 continuation`
- 어떤 구간은 `상단/중단 reclaim = 상승 recovery continuation`

즉 XAU는 subtype를 잘못 묶으면 오판 비용이 바로 커지고,
반대로 subtype를 제대로 나누면 해석 품질이 바로 좋아질 가능성이 높다.

### 2-3. XAU는 review candidate와 calibration teacher 재료가 많다

현재까지 누적된 `should-have-done`, `canonical diverged`, `dominance validation` 후보에서도
XAU는 review 가치가 높은 심볼로 계속 등장했다.

즉 XAU는 지금

- subtype 분해 필요성이 높고
- retained evidence가 충분하고
- calibration teacher 후보도 많은

가장 효율적인 다음 타깃이다.

---

## 3. 현재 출발 상태

이 로드맵은 "처음부터 다시 만들기"가 아니라, 이미 구축한 계층 위에서 시작한다.

현재 살아 있는 기반은 아래와 같다.

- `CA2 / R0 ~ R6-A`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session_bias_shadow_summary_v1`
- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `state_structure_dominance_profile_v1`
- `symbol_specific_state_strength_calibration_contract_v1`

그리고 S7에서는 이미 `symbol × direction × subtype` family 구조로 바뀌어 있다.

현재 XAU는 최소 아래 두 family가 seed 상태가 아니다. 이미 실전 근거가 있는 active candidate다.

- `XAUUSD_UP_CONTINUATION_RECOVERY_V1`
- `XAUUSD_DOWN_CONTINUATION_REJECTION_V1`

즉 지금 단계는 "XAU를 이해할 수 있을까?"가 아니라
"XAU를 어느 수준까지 쪼개야 가장 설명력과 재현성이 좋은가?"를 결정하는 단계다.

---

## 4. 실행 원칙

### 4-1. XAU-only focus는 임시 집중일 뿐, 영구 예외화가 아니다

지금 XAU에 집중하는 이유는 XAU가 구조를 제일 선명하게 보여주기 때문이다.
이건 `XAU 특혜`가 아니라 `XAU가 현재 가장 학습 효율이 좋은 샘플`이라는 뜻이다.

최종 목표는 여전히 아래다.

- NAS 상승 / 하락 continuation
- XAU 상승 / 하락 continuation
- BTC 상승 / 하락 continuation

즉 XAU에서 subtype 분해의 프레임을 먼저 고정하고,
그다음 NAS/BTC에 같은 구조를 적용하는 것이 목표다.

### 4-2. 새 subtype는 로그와 screenshot window로만 올린다

새 XAU subtype를 추가할 때는 아래 중 최소 두 가지가 필요하다.

1. screenshot 장면 근거
2. retained decision log window
3. should-have-done candidate
4. dominance validation mismatch

한 번 보인 장면이나 감으로는 subtype를 올리지 않는다.

### 4-3. execution/state25 연결은 마지막이다

XAU subtype를 세분화한다고 해서 곧바로

- execution bias
- state25 bias
- promotion/guard override

로 올리지 않는다.

먼저 shadow-only / read-only로 충분히 검증한 뒤에만 다음 단계로 넘어간다.

---

## 5. 단계별 로드맵

### X0. 기존 계측 안정 유지

목적:

- XAU subtype 작업을 하더라도 기존 `CA2 / R0~R6-A / S0~S7`가 깨지지 않게 유지한다.

핵심 작업:

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `state_structure_dominance_summary_v1`
- `symbol_specific_state_strength_calibration_summary_v1`

가 계속 정상 surface되는지 본다.

완료 기준:

- 기존 surface와 artifact freshness가 유지된다.

상태 기준:

- `READY`: 기존 계측이 계속 갱신된다.
- `HOLD`: freshness나 일부 surface가 흔들린다.
- `BLOCKED`: subtype 작업 때문에 기존 계측이 깨진다.

### X1. XAU retained window 인벤토리 고정

목적:

- XAU subtype를 논의할 기준 timebox를 먼저 고정한다.

핵심 작업:

- retained log 기준 XAU 주요 window를 확정한다.
- 최소 다음을 고정한다.
  - 상승 recovery core window
  - 하락 rejection core window
  - 애매한 mixed window

예상 결과:

- `xau_up_recovery_*`
- `xau_down_rejection_*`
- `xau_mixed_boundary_*`

같은 artifact naming 규칙이 생긴다.

완료 기준:

- 나중에 다시 봐도 모두 같은 XAU window를 기준으로 비교할 수 있다.

### X2. XAU UP_CONTINUATION subtype 세분화

목적:

- 현재 `RECOVERY_RECLAIM` 하나로 묶인 XAU 상승 continuation을 더 의미 있게 쪼갠다.

후보 subtype 예:

- `LOWER_RECOVERY_RECLAIM`
- `MID_RECLAIM_CONTINUATION`
- `POST_DIP_RECOVERY_DRIVE`

핵심 작업:

- 상승 recovery 구간을 retained window 기준으로 다시 나눈다.
- `state_strength / local_structure / dominance`가 subtype별로 어떻게 다른지 비교한다.
- `consumer veto`가 반복적으로 과대 작동하는 장면이 있는지 찾는다.

완료 기준:

- 최소 2개 이상의 XAU 상승 subtype가 retained evidence와 함께 설명 가능해진다.

상태 기준:

- `READY`: subtype별 특징과 구분 근거가 선명하다.
- `HOLD`: 상승 recovery는 보이지만 subtype 간 경계가 흐리다.
- `BLOCKED`: retained evidence가 부족해 쪼개는 것이 오히려 노이즈가 된다.

### X3. XAU DOWN_CONTINUATION subtype 세분화

목적:

- 현재 `UPPER_REJECT_REJECTION` 하나로 묶인 XAU 하락 continuation을 더 구체화한다.

후보 subtype 예:

- `UPPER_REJECT_BREAKDOWN`
- `MID_REJECT_DRIFT`
- `FAILED_RECLAIM_SELL_CONTINUATION`

핵심 작업:

- 하락 continuation 구간에서 rejection이 실제 reversal override인지, 아니면 continuation under friction인지를 분리한다.
- `upper reject`가 반복될 때 진짜 하락 continuation으로 이어지는 패턴을 분리한다.

완료 기준:

- 최소 2개 이상의 XAU 하락 subtype가 retained evidence와 함께 설명 가능해진다.

### X4. XAU-specific should-have-done calibration 축 추가

목적:

- XAU subtype 오판을 일반 review가 아니라 calibration teacher로 쓸 수 있게 만든다.

핵심 작업:

- XAU row에 대해 subtype-level `should-have-done` candidate를 붙인다.
- 아래류의 필드를 XAU 중심으로 점검한다.
  - `expected_dominant_side`
  - `expected_dominant_mode`
  - `expected_caution_level`
  - `dominance_error_type`
  - `overweighted_caution_fields`
  - `undervalued_continuation_evidence`

완료 기준:

- XAU 오판이 단순 "틀림"이 아니라 "어떤 subtype에서 어떤 caution이 과대했는가"로 기록된다.

### X5. XAU-only dominance validation 강화

목적:

- XAU subtype가 실제로 over-veto / under-veto를 줄이는지 shadow-only로 검증한다.

핵심 작업:

- XAU 전용으로 아래 지표를 본다.
  - `over_veto_rate`
  - `under_veto_rate`
  - `friction_separation_quality`
  - `boundary_dwell_quality`

- subtype 분해 전/후 지표를 비교한다.

완료 기준:

- XAU subtype 분해가 dominance 해석 품질을 실제로 개선하는지 숫자로 읽힌다.

### X6. XAU read-only calibration hint 생성

목적:

- XAU subtype 결과를 runtime row에서 read-only recommendation으로 surface한다.

핵심 작업:

- execution이나 state25는 건드리지 않고,
  XAU에 한해 subtype-aware hint만 남긴다.

예:

- `xau_subtype_hint_v1`
- `xau_subtype_confidence_v1`
- `xau_subtype_bias_effect_v1`

완료 기준:

- XAU row에서 현재 장면이 어떤 subtype family로 읽히는지 바로 보인다.

### X7. XAU framework를 NAS/BTC로 일반화

목적:

- XAU에서 검증된 subtype 분해 프레임을 NAS/BTC에 옮긴다.

핵심 작업:

- XAU에서 유효했던 분해 기준 중
  - 공용 가능한 것
  - XAU 고유로 남겨야 할 것

을 분리한다.

완료 기준:

- NAS/BTC도 `symbol × direction × subtype` family를 같은 언어로 확장할 수 있다.

---

## 6. 당장 외부 조언에서 받고 싶은 핵심 질문

1. XAU는 subtype를 몇 단계까지 쪼개는 것이 적절한가?
2. `UPPER_REJECT_REJECTION`을 실제 하락 continuation으로 볼 최소 근거는 무엇인가?
3. `RECOVERY_RECLAIM`은 `LOWER/MID/POST_DIP` 등으로 더 쪼개는 것이 가치가 있는가?
4. XAU에서 가장 자주 발생하는 dominance 오판은 무엇이며, 그 원인은 `friction / boundary / reversal evidence` 중 어디에 가까운가?
5. XAU subtype 분해를 NAS/BTC 일반화의 프레임으로 삼아도 되는가, 아니면 XAU 고유 규칙을 더 많이 허용해야 하는가?

---

## 7. 하지 말아야 할 것

- `XAU는 원래 이렇다` 식의 심볼 감각론으로 subtype를 늘리지 말 것
- screenshot 한 장만 보고 새 subtype를 만들지 말 것
- subtype 분해를 곧바로 execution override로 연결하지 말 것
- `upper reject = 항상 SELL continuation`처럼 단일 신호를 절대 규칙으로 만들지 말 것
- XAU에서 보인 subtype를 검증 없이 NAS/BTC에 바로 복사하지 말 것

---

## 8. 한 문장 결론

지금은 XAU를 먼저 더 잘게 쪼개는 것이 가장 효율적이다. 이유는 XAU가 retained log와 screenshot 기준으로 양방향 continuation subtype를 가장 선명하게 보여주고 있고, 지금까지 만든 `state/local/dominance/should-have-done` 계층을 실제로 calibration하기에 가장 좋은 심볼이기 때문이다.
