# Response R2-9 Acceptance Freeze

## 목적

이 문서는 `R2-9. Response 6축 재결선`이 현재 어떤 상태로 완료되었는지 고정하는 acceptance 문서다.

이 문서는 설계 문서가 아니다.

- 무엇을 만들려고 했는지
- 지금 실제로 무엇이 반영되었는지
- 무엇을 완료로 볼지
- 무엇이 아직 다음 단계인지

를 현재 코드 / 테스트 / live runtime 기준으로 고정한다.


## 현재 결론

`R2-9는 완료로 본다.`

단, 이 완료의 의미는 아래와 같다.

- `Response 6축`은 이제 새 subsystem 구조를 1차 owner로 쓴다.
- 옛 `BB / Box 중심 semantic blend`는 제거되었다.
- legacy는 더 이상 semantic 의미를 만드는 owner가 아니다.
- legacy는 `context gate metadata`가 통째로 없는 비정상 상황에서만 기술적 fallback으로 남아 있다.


## 현재 고정 구조

```text
raw
-> descriptor
-> pattern
-> motif
-> subsystem
-> context gate
-> pre-axis candidates
-> Response 6축
```

즉 현재 `Response 6축`은 더 이상 raw를 바로 merge해서 만들지 않는다.


## 현재 6축 owner

### `lower_hold_up`

주 owner:

- `lower_hold_candidate`

candidate를 만드는 주 재료:

- `support_hold_strength`
- `trend_support_hold_strength`
- `micro_bull_reject_strength`
- `support_hold_confirm`
- `reversal_base_up`
- `bull_reject`


### `lower_break_down`

주 owner:

- `lower_break_candidate`

candidate를 만드는 주 재료:

- `support_break_strength`
- `trend_support_break_strength`
- `micro_bear_break_strength`
- `bear_break_body`


### `mid_reclaim_up`

주 owner:

- `mid_reclaim_candidate`

candidate를 만드는 주 재료:

- `micro_reclaim_up_strength`
- bullish 2봉/3봉 reversal motif
- bullish break body


### `mid_lose_down`

주 owner:

- `mid_lose_candidate`

candidate를 만드는 주 재료:

- `micro_lose_down_strength`
- bearish 2봉/3봉 reversal motif
- bearish break body


### `upper_reject_down`

주 owner:

- `upper_reject_candidate`

candidate를 만드는 주 재료:

- `resistance_reject_strength`
- `trend_resistance_reject_strength`
- `micro_bear_reject_strength`
- `resistance_reject_confirm`
- `reversal_top_down`
- `bear_reject`


### `upper_break_up`

주 owner:

- `upper_break_candidate`

candidate를 만드는 주 재료:

- `resistance_break_strength`
- `trend_resistance_break_strength`
- `micro_bull_break_strength`
- `bull_break_body`


## 현재 구현 계약

현재 [transition_vector.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/transition_vector.py)의 핵심 계약은 아래와 같다.

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`
- `context_gate_present = True`일 때
  - 6축은 candidate 값만 사용한다
  - legacy raw merge는 semantic blend에 참여하지 않는다
- `context_gate_present = False`일 때만
  - 기술적 fallback으로 legacy merge를 사용한다

즉 현재 의미는:

```text
gate가 있으면 candidate-only
gate가 없으면 technical legacy fallback
```


## acceptance 기준

아래 조건을 모두 만족하면 `R2-9 완료`로 본다.

### 1. 구조 기준

- `descriptor -> pattern -> motif -> subsystem -> context gate -> 6축` 흐름이 실제 코드에 존재한다.
- `Response 6축`은 직접 raw merge owner가 아니라 `pre-axis candidates`를 owner로 사용한다.

### 2. 계약 기준

- `mapping_mode`가 `context_gated_candidate_primary_only`이다.
- `mapper_version`이 `response_vector_v2_r5`이다.
- `technical_legacy_fallback_on_missing_gate_only`가 `True`다.

### 3. 테스트 기준

핵심 회귀 테스트가 통과해야 한다.

권장 확인 묶음:

```text
pytest tests\unit\test_position_contract.py
       tests\unit\test_prs_engine.py
       tests\unit\test_response_contract.py
       tests\unit\test_response_state_engine.py
       tests\unit\test_forecast_contract.py
       tests\unit\test_context_classifier.py -q
```

현재 확인 결과:

```text
100 passed
```

### 4. live runtime 기준

`runtime_status.json`에서 아래가 실제로 보여야 한다.

- `response_vector_v2.metadata.mapping_mode = context_gated_candidate_primary_only`
- `response_vector_v2.metadata.mapper_version = response_vector_v2_r5`
- `response_vector_v2.metadata.context_gate_present = true`
- `response_vector_v2.metadata.technical_legacy_fallback_on_missing_gate_only = true`
- `dominant_source_by_axis.lower_hold_up = lower_hold_candidate`
- `dominant_source_by_axis.upper_reject_down = upper_reject_candidate`


## 실제 확인 결과

현재 live에서 아래를 확인했다.

### NAS100

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`
- `context_gate_present = True`
- `technical_legacy_fallback_on_missing_gate_only = True`
- `lower_source = lower_hold_candidate`
- `upper_source = upper_reject_candidate`

### XAUUSD

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`
- `context_gate_present = True`
- `technical_legacy_fallback_on_missing_gate_only = True`
- `lower_source = lower_hold_candidate`
- `upper_source = upper_reject_candidate`

### BTCUSD

- `mapping_mode = context_gated_candidate_primary_only`
- `mapper_version = response_vector_v2_r5`
- `context_gate_present = True`
- `technical_legacy_fallback_on_missing_gate_only = True`
- `lower_source = lower_hold_candidate`
- `upper_source = upper_reject_candidate`


## 무엇이 제거되었는가

제거된 것은 `legacy raw 자체`가 아니라, `legacy가 semantic 6축 owner로 섞여 들어가는 구조`다.

즉 아래는 더 이상 메인 semantic owner가 아니다.

- `bb20_lower_hold`
- `box_lower_bounce`
- `bb20_lower_break`
- `box_lower_break`
- `bb20_mid_hold`
- `bb20_mid_reclaim`
- `box_mid_hold`
- `bb20_mid_reject`
- `bb20_mid_lose`
- `box_mid_reject`
- `bb20_upper_reject`
- `box_upper_reject`
- `bb20_upper_break`
- `box_upper_break`

이 raw들은 이제:

- 디버그
- legacy comparison
- gate 부재 시 technical fallback

용도로만 남는다.


## 무엇이 아직 다음 단계인가

`R2-9`는 완료됐지만, 아래는 다음 단계다.

- `R2-10` 이후 calibration
- context gate weight 튜닝
- candidate threshold 튜닝
- wait / confirm / hold의 ML calibration
- subsystem별 contribution 재조정

즉 지금은 wiring이 끝난 것이고,
이제부터는 quality tuning 단계다.


## freeze 선언

현재 시점에서 `R2-9`는 아래 의미로 freeze한다.

```text
Response 6축은 subsystem + context gate 기반 candidate owner를 사용한다.
legacy raw merge는 더 이상 semantic blend owner가 아니다.
legacy는 context gate 부재 시 technical fallback으로만 남는다.
```

이 freeze는 다음 조건이 생기기 전까지 유지한다.

- subsystem 구조 자체를 다시 바꾸는 리팩터링
- context gate contract 변경
- Response 6축 의미 재정의


## 관련 파일

- [transition_vector.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/transition_vector.py)
- [builder.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/builder.py)
- [context_gate.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/context_gate.py)
- [test_response_contract.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_response_contract.py)
- [test_forecast_contract.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_forecast_contract.py)
- [test_context_classifier.py](c:/Users/bhs33/Desktop/project/cfd/tests/unit/test_context_classifier.py)
