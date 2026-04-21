# D0 기존 decomposition 계측 안정 유지 실행 로드맵

## 1. 목적

D0는 decomposition 구현의 첫 단계이자 안전장치다.

목표는 하나다.

- 새 decomposition 층이 들어와도
- 기존 summary, artifact, runtime detail이
- 계속 비교 가능한 상태로 남도록 한다.

---

## 2. 실행 순서

### D0-1. dependency 목록 고정

다음 7개를 D0 관찰 대상으로 고정한다.

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `state_structure_dominance_summary_v1`
- `dominance_accuracy_summary_v1`
- `symbol_specific_state_strength_calibration_summary_v1`

### D0-2. stability guard 구현

새 guard는 아래를 함께 기록한다.

- summary 존재 여부
- artifact 존재 여부
- freshness 상태
- upstream status
- dependency별 이유

### D0-3. runtime detail export

`runtime_status.detail.json`에 아래를 surface한다.

- `state_polarity_d0_stability_summary_v1`
- `state_polarity_d0_stability_artifact_paths`

### D0-4. shadow artifact 생성

아래 artifact를 생성한다.

- `state_polarity_d0_stability_latest.json`
- `state_polarity_d0_stability_latest.md`

### D0-5. unit test 추가

최소 테스트:

- 모든 dependency가 fresh면 `READY`
- artifact 누락이면 `HOLD`
- summary missing 또는 upstream blocked면 `BLOCKED`
- runtime detail에 summary/artifact path가 export됨

---

## 3. 완료 기준

- 기존 artifact와 runtime detail 필드가 계속 정상 갱신된다.
- D0 summary가 dependency 7개 상태를 한 번에 보여준다.

---

## 4. 상태 기준

- `READY`: 기존 계측 유지
- `HOLD`: freshness나 일부 surface 흔들림
- `BLOCKED`: decomposition 추가 때문에 기존 계측 깨짐

---

## 5. 한 문장 결론

D0는 decomposition 구현의 시작점이 아니라, decomposition을 올려도 기존 비교축이 무너지지 않게 지켜주는 기준선이다.
