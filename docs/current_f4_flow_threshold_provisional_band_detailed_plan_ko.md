# F4. Threshold Provisional Band 상세 계획

## 1. 목적

F4의 목적은 F2에서 만든

- `aggregate_conviction_v1`
- `flow_persistence_v1`

를 F3에서 잠근 retained calibration profile 위에 올려서,

- 현재 row가 confirmed band 위에 있는지
- building band 안에 들어와 있는지
- 아직 building floor 아래인지

를 공용 read-only surface로 고정하는 것이다.

즉 F4는 최종 flow acceptance가 아니라,
"현재 live row가 provisional band 기준으로 어디쯤 와 있는가"를 읽는 단계다.

---

## 2. 왜 F4가 필요한가

F3까지 오면 retained anchors와 symbol-specific provisional threshold profile은 이미 정리되었다.

하지만 아직 부족한 것은:

- 현재 live F2 값이 그 band와 어떻게 겹치는지
- conviction과 persistence가 각각 어느 위치에 있는지
- `ELIGIBLE / WEAK / INELIGIBLE` gate 위에서 어느 provisional candidate 상태로 읽혀야 하는지

다.

즉 F4는

- retained catalog
- live conviction/persistence
- structure gate

를 같은 화면에서 비교 가능하게 만드는 단계다.

---

## 3. F4의 권한

F4는 여전히 threshold를 pass/fail 최종 판정기로 쓰지 않는다.

권한 순서는 다음과 같다.

1. `F1 flow_structure_gate_v1`
2. `F2 aggregate_conviction_v1 / flow_persistence_v1`
3. `F3 retained threshold profile`
4. `F4 provisional band state`

즉 F4는 구조 권한을 빼앗지 않는다.
F4는 단지 현재 숫자가 provisional band 기준으로 어느 위치에 있는지 분류하는 설명층이다.

---

## 4. F4에서 읽을 것

F4는 아래 질문에 답해야 한다.

1. conviction이 confirmed floor 이상인가
2. conviction이 building floor 이상인가
3. persistence가 confirmed floor 이상인가
4. persistence가 building floor 이상인가
5. structure gate가 막고 있는가
6. stage가 `EXTENSION`이라 confirmed 상한을 막아야 하는가

즉 F4는 threshold를 숫자 하나가 아니라,

- conviction position
- persistence position
- structure gate 상태
- extension cap

을 같이 보는 band interpreter다.

---

## 5. row-level surface

F4에서 남길 필드는 다음과 같다.

- `flow_threshold_provisional_band_profile_v1`
- `provisional_flow_band_state_v1`
- `aggregate_conviction_band_position_v1`
- `flow_persistence_band_position_v1`
- `aggregate_conviction_gap_to_confirmed_v1`
- `aggregate_conviction_gap_to_building_v1`
- `flow_persistence_gap_to_confirmed_v1`
- `flow_persistence_gap_to_building_v1`
- `provisional_flow_band_reason_summary_v1`

의미는 아래와 같다.

### 5-1. `aggregate_conviction_band_position_v1`

- `ABOVE_CONFIRMED`
- `WITHIN_BUILDING`
- `BELOW_BUILDING`

### 5-2. `flow_persistence_band_position_v1`

- `ABOVE_CONFIRMED`
- `WITHIN_BUILDING`
- `BELOW_BUILDING`

### 5-3. `provisional_flow_band_state_v1`

- `STRUCTURE_BLOCKED`
- `CONFIRMED_CANDIDATE`
- `BUILDING_CANDIDATE`
- `UNCONFIRMED_CANDIDATE`
- `NOT_APPLICABLE`

중요:

- `CONFIRMED_CANDIDATE`는 conviction과 persistence가 둘 다 confirmed floor 이상일 때만 간다
- `BUILDING_CANDIDATE`는 둘 중 하나가 앞서고 다른 하나가 building floor 이상인 상태를 포함한다
- `STRUCTURE_BLOCKED`는 숫자와 무관하게 F1이 먼저 막는 상태다

---

## 6. 운영 원칙

### 6-1. Structure Gate 우선

`flow_structure_gate_v1`가 `ELIGIBLE / WEAK`가 아니면
F4는 `STRUCTURE_BLOCKED`다.

### 6-2. confirmed는 둘 다 높아야 함

`CONFIRMED_CANDIDATE`는

- conviction above confirmed
- persistence above confirmed
- structure gate eligible

이 세 조건이 같이 있을 때만 된다.

### 6-3. building은 하나가 앞서고 하나가 따라오는 상태 포함

`BUILDING_CANDIDATE`는

- 둘 다 building floor 이상이거나
- 하나는 confirmed 이상이고 다른 하나는 building 이상인 상태

를 포함한다.

### 6-4. extension cap 유지

`EXTENSION`은 structure gate 상으로는 살 수 있어도,
기본적으로 `CONFIRMED_CANDIDATE`로 바로 올리지 않는다.

즉 extension은 provisional band에서도 late continuation 관리 대상으로 본다.

---

## 7. 심볼별 tuning과 공용 규칙의 경계

F4에서도 이 경계를 유지해야 한다.

### 조정 가능한 것

- conviction confirmed/building floor
- persistence confirmed/building floor

### 조정하면 안 되는 것

- hard disqualifier
- rejection split
- dominance ownership
- extension confirmed cap

즉 F4는 symbol-specific threshold profile을 쓸 수 있지만,
구조 규칙을 symbol-specific excuse로 바꾸는 단계는 아니다.

---

## 8. Summary artifact

F4 summary는 최소 아래를 포함한다.

- `provisional_flow_band_state_count_summary`
- `aggregate_conviction_band_position_count_summary`
- `flow_persistence_band_position_count_summary`
- `flow_threshold_profile_count_summary`

이렇게 해야

- 어느 symbol이 아직 structure blocked인지
- 어느 symbol이 building band 근처까지 왔는지
- 어느 symbol profile이 너무 타이트하거나 느슨해 보이는지

를 한 번에 볼 수 있다.

---

## 9. 완료 기준

- F4 contract/summary/artifact가 runtime detail에 export된다
- 각 symbol row에서 conviction/persistence band 위치를 읽을 수 있다
- `CONFIRMED_CANDIDATE / BUILDING_CANDIDATE / UNCONFIRMED_CANDIDATE / STRUCTURE_BLOCKED`가 일관되게 surface된다
- extension cap과 structure block이 숫자보다 먼저 적용된다

상태 기준:

- `READY`
  - contract/summary/row surface 모두 정상
- `HOLD`
  - 일부 upstream 누락으로 provisional state가 약함
- `BLOCKED`
  - 구조 권한과 threshold 권한이 뒤집히거나 export가 깨짐
