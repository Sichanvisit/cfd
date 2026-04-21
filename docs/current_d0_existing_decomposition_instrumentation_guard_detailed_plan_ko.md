# D0 기존 decomposition 계측 안정 유지 상세 계획

## 1. 목적

이 문서는 `state polarity decomposition`을 올리기 전에,
기존 summary와 runtime detail이 깨지지 않게 유지하는 D0 보호막을 정의한다.

핵심 목적은 단순하다.

- decomposition 층을 추가하더라도
- 이미 구축한 `CA2 / R0~R6-A / S0~S7`
- 그리고 `state/dominance/calibration`

계측이 계속 정상적으로 남는지 한 번에 확인할 수 있게 만드는 것이다.

즉 D0는 새 해석층 자체보다 먼저,
"기존 계측을 안 깨고 갈 수 있는가"를 확인하는 안전장치다.

---

## 2. 왜 필요한가

지금 단계에서 가장 위험한 것은
새 decomposition을 더 붙이다가 기존 비교축이 조용히 깨지는 것이다.

특히 아래 계측들은 지금 시스템의 기준축이다.

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `state_structure_dominance_summary_v1`
- `dominance_accuracy_summary_v1`
- `symbol_specific_state_strength_calibration_summary_v1`

이 축이 깨지면 다음 문제가 생긴다.

- decomposition이 좋아졌는지 나빠졌는지 비교 불가
- should-have-done teacher 품질 추적 불가
- canonical divergence 감소 여부 확인 불가
- dominance layer와 decomposition layer 관계 검증 불가
- symbol-specific calibration 품질 추적 불가

즉 D0는 "기능을 하나 더 만들자"가 아니라,
앞으로의 모든 개선을 비교 가능하게 유지하는 기준선이다.

---

## 3. 관찰 대상

### 3-1. summary freshness

각 summary가 계속 `generated_at`을 갱신하는지 본다.

### 3-2. artifact 존재 여부

각 report의

- `json_path`
- `markdown_path`

가 실제로 존재하는지 본다.

### 3-3. upstream status

upstream이 `BLOCKED`면 바로 막아야 한다.
반면 upstream이 `HOLD`라도 summary와 artifact가 계속 surface된다면 D0 기준에선 바로 실패로 보지 않는다.

---

## 4. D0 핵심 규칙

### 4-1. BLOCKED 판정

아래 중 하나면 `BLOCKED`다.

- summary missing
- upstream summary status가 `BLOCKED`

### 4-2. HOLD 판정

아래 중 하나면 `HOLD`다.

- summary timestamp 누락
- summary stale
- artifact path 누락
- artifact file 누락
- artifact stale

### 4-3. READY 판정

아래를 모두 만족하면 `READY`다.

- summary 존재
- artifact 존재
- freshness 유지
- upstream이 `BLOCKED` 아님

---

## 5. 산출물

### runtime detail

- `state_polarity_d0_stability_summary_v1`
- `state_polarity_d0_stability_artifact_paths`

### shadow artifact

- `state_polarity_d0_stability_latest.json`
- `state_polarity_d0_stability_latest.md`

---

## 6. 완료 기준

- 기존 artifact와 runtime detail 필드가 계속 정상 갱신된다.
- dependency 7개를 한 눈에 `READY / HOLD / BLOCKED`로 읽을 수 있다.

---

## 7. 상태 기준

- `READY`: 기존 계측 유지
- `HOLD`: freshness나 일부 surface 흔들림
- `BLOCKED`: decomposition 추가 때문에 기존 계측 깨짐

---

## 8. 한 문장 결론

D0의 목적은 decomposition을 더하는 것이 아니라, decomposition을 더해도 기존 비교축과 검증축이 계속 살아 있음을 보장하는 것이다.
