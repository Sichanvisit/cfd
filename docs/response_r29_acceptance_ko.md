# R2-9 Response 6축 재결선 Acceptance Freeze

## 목적

이 문서는 `R2-9 Response 6축 재결선`이 현재 어떤 상태로 완료되었는지,
그리고 앞으로 무엇을 `정상 동작`으로 간주할지를 고정하기 위한 acceptance 문서다.

핵심은 이것이다.

- `Response 6축`은 유지한다.
- 하지만 더 이상 `옛 BB/Box 중심 raw merge`가 의미 owner가 아니다.
- 이제 `Response 6축`의 1차 owner는 `context gate가 만든 pre-axis candidate`다.
- legacy는 오직 `context gate metadata가 통째로 없을 때만` 기술적 fallback으로 허용한다.

즉 `R2-9`는 6축을 바꾼 작업이 아니라,
`6축의 의미 owner를 subsystem/context-gate 기반으로 재배선한 작업`이다.

---

## 이번 단계에서 고정된 의미

### 이전 의미

이전에는 구조가 대체로 아래와 같았다.

```text
BB / Box / candle / pattern raw
-> 바로 Response 6축
```

즉:

- `bb20_lower_hold`
- `box_lower_bounce`
- `bb20_upper_reject`
- `box_upper_reject`

같은 raw가 거의 직접 6축의 의미를 만들었다.

이 구조의 문제는 다음과 같았다.

- `BB/Box`가 지나치게 중심 owner가 된다.
- `candle/pattern`은 확인 또는 증폭 수준에 머문다.
- `S/R`, `trendline`, `micro-TF`, `context gate`가 축 owner로 충분히 못 올라온다.
- 같은 뜻이 여러 raw에서 중복으로 들어갈 수 있다.

### 현재 의미

현재는 구조가 아래처럼 고정된다.

```text
descriptor / pattern / motif / subsystem
-> context gate
-> pre-axis candidates
-> Response 6축
```

즉:

- `candle motif`
- `structure motif`
- `S/R subsystem`
- `trendline subsystem`
- `micro-TF subsystem`

이 먼저 정리되고,
그 뒤에 `context gate`가 현재 위치와 모호성을 반영하여 candidate를 만든다.
그리고 최종 `Response 6축`은 이 candidate를 1차 owner로 사용한다.

---

## 현재 고정되는 6축

### `lower_hold_up`

뜻:

- 하단에서 지지를 받고 위로 올라가려는 힘

현재 owner 재료:

- `support_hold_strength`
- `trend_support_hold_strength`
- `micro_bull_reject_strength`
- `support_hold_confirm`
- gated candle/structure 영향

### `lower_break_down`

뜻:

- 하단 지지가 깨지고 아래로 내려가려는 힘

현재 owner 재료:

- `support_break_strength`
- `trend_support_break_strength`
- `micro_bear_break_strength`

### `mid_reclaim_up`

뜻:

- 중심을 다시 회복하고 위로 가려는 힘

현재 owner 재료:

- `micro reclaim`
- bullish 2봉/3봉 reversal
- lower -> mid 회복 반응

### `mid_lose_down`

뜻:

- 중심을 잃고 다시 아래로 밀리는 힘

현재 owner 재료:

- `micro lose`
- bearish 2봉/3봉 reversal
- mid 상실 반응

### `upper_reject_down`

뜻:

- 상단에서 거절되고 아래로 내려가려는 힘

현재 owner 재료:

- `resistance_reject_strength`
- `trend_resistance_reject_strength`
- `micro_bear_reject_strength`
- `resistance_reject_confirm`
- gated candle/structure 영향

### `upper_break_up`

뜻:

- 상단 저항을 돌파하고 위로 확장하려는 힘

현재 owner 재료:

- `resistance_break_strength`
- `trend_resistance_break_strength`
- `micro_bull_break_strength`

---

## Acceptance 핵심 원칙

### 원칙 1. 6축 이름은 유지한다

즉 아래 6개 축은 계속 유지된다.

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

이번 단계는 이름 교체가 아니라 내부 owner 교체다.

### 원칙 2. 새 구조가 primary owner다

`Response 6축`은 이제 아래 순서의 출력을 primary owner로 삼아야 한다.

```text
subsystem output
-> context gate
-> pre-axis candidate
-> axis value
```

즉 6축은 더 이상 legacy raw의 dominant merge 결과를 primary owner로 사용하지 않는다.

### 원칙 3. legacy는 의미 fallback이 아니다

legacy raw는 더 이상 다음 역할을 하면 안 된다.

- 새 candidate가 약할 때 의미를 대신 만들기
- 새 candidate가 0일 때 예전 BB/Box raw로 축을 살려주기

즉 `legacy semantic blend`는 제거되어야 한다.

### 원칙 4. legacy는 기술적 fallback만 허용한다

아래 경우에만 legacy fallback을 허용한다.

- `response_context_gate_v1` metadata 자체가 통째로 없는 비정상 상황

이 경우는 구조 미생성/계약 누락 대비용 기술 fallback이다.

즉:

- `gate가 있음 + candidate가 0.0` -> 그대로 0.0 유지
- `gate가 없음` -> legacy axis로 임시 계산 가능

이 원칙이 현재 acceptance의 핵심이다.

---

## 현재 고정된 계약

### 전환 모드

현재 `response_vector_v2`는 아래 계약을 따라야 한다.

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`

### metadata 계약

현재 `response_vector_v2.metadata` 안에는 최소한 아래 정보가 있어야 한다.

- `mapping_mode`
- `mapper_version`
- `context_gate_present`
- `technical_legacy_fallback_on_missing_gate_only`
- `legacy_fallback_weight`
- `dominant_source_by_axis`
- `dominant_role_by_axis`

### axis debug 계약

각 축 debug에는 아래 의미가 유지되어야 한다.

- `dominant_role = gated_candidate`
  - gate candidate가 실제 owner일 때
- `dominant_role = gated_zero`
  - gate는 존재하지만 candidate가 0이라 축도 0일 때

즉 `gate가 있는데 legacy가 축을 살리는 현상`은 없어야 한다.

---

## 현재 기준 구현 위치

핵심 구현 파일:

- [transition_vector.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/transition_vector.py)
- [context_gate.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/context_gate.py)
- [builder.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/builder.py)

핵심 검증 파일:

- [test_response_contract.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_response_contract.py)
- [test_forecast_contract.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_forecast_contract.py)
- [test_response_state_engine.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_response_state_engine.py)
- [test_prs_engine.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_prs_engine.py)
- [test_context_classifier.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_context_classifier.py)

---

## 현재 acceptance 체크 결과

### 1. 테스트 기준

실행한 핵심 회귀 묶음:

```text
pytest tests\unit\test_position_contract.py
       tests\unit\test_prs_engine.py
       tests\unit\test_response_contract.py
       tests\unit\test_response_state_engine.py
       tests\unit\test_forecast_contract.py
       tests\unit\test_context_classifier.py
       -q
```

결과:

- `100 passed`

즉 현재 계약 수준에서는 회귀가 없는 상태다.

### 2. live runtime 기준

현재 runtime에서는 아래가 확인되어야 한다.

- `response_vector_v2.metadata.mapping_mode = context_gated_candidate_primary_only`
- `response_vector_v2.metadata.mapper_version = response_vector_v2_r5`
- `response_vector_v2.metadata.context_gate_present = true`
- `response_vector_v2.metadata.technical_legacy_fallback_on_missing_gate_only = true`

또한 axis dominant source는 candidate 기반으로 나와야 한다.

예:

- `lower_hold_up -> lower_hold_candidate`
- `upper_reject_down -> upper_reject_candidate`

즉 live에서도 새 구조가 실제 owner로 올라온 상태여야 한다.

### 3. API / runtime 상태

acceptance 시점 기준 확인 포인트:

- `http://127.0.0.1:8010/health = {"status":"ok"}`
- [runtime_status.json](c:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json) 갱신 정상

즉 코드/테스트뿐 아니라 live contract도 정상이어야 acceptance로 본다.

---

## PASS 판단 기준

아래를 모두 만족하면 `R2-9 PASS`로 간주한다.

### PASS-1

`Response 6축`이 여전히 존재하고, 이름이 바뀌지 않는다.

### PASS-2

`context gate pre-axis candidate`가 6축의 primary owner다.

### PASS-3

`gate가 존재하는데 candidate가 0일 때`, legacy가 semantic하게 축을 살리지 않는다.

### PASS-4

legacy는 오직 `gate metadata가 통째로 없을 때만` 기술 fallback으로 허용된다.

### PASS-5

live runtime metadata에서 아래가 직접 보인다.

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`

### PASS-6

회귀 테스트가 통과한다.

현재 기준:

- `100 passed`

---

## 이번 단계에서 일부러 하지 않은 것

이 acceptance는 아래를 보장하지 않는다.

- 실제 수익이 이미 최적이라는 것
- 진입 품질이 이미 완전히 만족스럽다는 것
- 청산 품질이 이미 완전히 만족스럽다는 것
- candidate 가중치가 최종 수치로 확정됐다는 것

즉 `R2-9 acceptance`는
`구조와 owner가 올바르게 재결선되었는가`를 고정하는 문서다.

트레이딩 품질 자체의 calibration은 그 다음 단계다.

---

## 남은 후속 과제

### 1. R2-9 quality observation

이제부터는 wiring 검증보다
실제 차트 사례에서 다음이 잘 되는지 관찰해야 한다.

- 상단 reject를 더 잘 잡는지
- 하단 hold와 하단 break를 더 잘 나누는지
- middle reclaim / lose가 더 자연스러운지

### 2. weight / threshold calibration

이후에는 다음 영역을 조정할 수 있다.

- context gate weight
- ambiguity penalty
- candidate scaling
- Evidence threshold
- wait/confirm 경계

### 3. ML calibration 대상

이후 ML은 의미 구조를 바꾸는 용도가 아니라,
현재 구조의 숫자를 보정하는 용도로 들어가야 한다.

즉:

- 좋은 진입
- 좋은 기다림
- 좋은 청산
- 기대수익

을 기준으로 `Response/Evidence/Barrier/Wait` 계열의 수치를 보정하는 것이 다음 단계다.

---

## 한 줄 결론

`R2-9는 완료되었다. 이제 Response 6축은 subsystem/context-gate 기반 candidate가 primary owner이며, legacy BB/Box raw는 더 이상 semantic blend를 만들지 않고 gate가 통째로 없을 때만 기술 fallback으로 남는다.`
