# S0 기존 계측 안정 유지 상세 계획

## 1. 목적

`S0. 기존 계측 안정 유지`는 새 `state strength / local structure / dominance` 해석층을 얹기 전에,
이미 살아 있는 `CA2 / R0 ~ R6-A` surface가 깨지지 않도록 지켜보는 안전 가드다.

핵심은 새 해석층이 좋아 보이더라도 아래 기존 축이 흔들리면 바로 감지하는 것이다.

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `ca2_session_split_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session_bias_shadow_summary_v1`

즉 `S0`는 새 판단 로직이 아니라, 기존 검증 체계가 계속 surface되고 artifact로 갱신되는지 확인하는 운영 가드다.

## 2. 왜 S0가 먼저 필요한가

현재 시스템은 이미 다음 계측 축을 갖고 있다.

- `execution_diff`
- `continuation_accuracy`
- `session split`
- `should-have-done`
- `canonical surface`
- `session bias shadow`

이 상태에서 새 dominance 해석층을 바로 얹으면, 좋아진 것처럼 보여도 실제론 기존 계측이 조용히 깨질 수 있다.

예를 들면:

- artifact는 더 이상 갱신되지 않는데 runtime detail만 남는 경우
- runtime detail에는 값이 있는데 실제 shadow artifact는 오래된 경우
- 새 계층 추가 후 일부 summary가 비어 버리는 경우
- upstream summary가 `BLOCKED`가 됐는데 새 계층 쪽 로그에 묻혀 놓치는 경우

그래서 `S0`는 새 해석층 구현의 0단계로, 기존 계측의 생존성과 freshness를 먼저 지키는 역할을 맡는다.

## 3. S0가 실제로 확인할 것

### 3-1. summary surface 존재 여부

각 dependency report에 대해 아래를 본다.

- `summary`가 실제로 존재하는가
- `summary.generated_at`가 있는가

이게 없으면 새 해석층 이전에 기존 관측 surface가 깨진 것이다.

### 3-2. artifact 존재 여부

각 dependency report에 대해 아래를 본다.

- `artifact_paths.json_path`
- `artifact_paths.markdown_path`
- 실제 파일 존재 여부

artifact 경로가 없거나 파일이 없으면 runtime detail만 보고 착각할 수 있기 때문에 `HOLD` 이상으로 잡는다.

### 3-3. artifact freshness

artifact가 있더라도 너무 오래 갱신되지 않았으면 `freshness`가 흔들리는 상태로 본다.

v1에서는 `900초`를 초기 freshness 기준으로 둔다.
다만 이 값은 고정 진리가 아니라 운영 calibration 초기값이다.

### 3-4. upstream status

`S0`는 surface 생존을 보는 guard지만, upstream summary가 이미 `BLOCKED`라면
기존 계측 체계가 깨졌다고 보는 편이 맞다.

반면 upstream summary가 `HOLD`인 것은 곧장 실패로 보지 않는다.
예를 들면 sample flat, observe-only 같은 운영상 보류 상태는 surface가 살아 있으면 허용한다.

## 4. 상태 기준

### READY

아래가 모두 충족되면 `READY`다.

- 6개 dependency summary가 모두 존재
- `generated_at`가 모두 존재
- artifact path가 모두 존재
- artifact 파일이 모두 존재
- freshness가 모두 기준 안
- upstream summary 중 `BLOCKED` 없음

즉 새 해석층을 얹어도 기존 CA2/R0~R6-A 계측이 살아 있는 상태다.

### HOLD

아래 같은 경우는 `HOLD`다.

- summary는 있는데 `generated_at`가 비어 있음
- artifact path는 있는데 파일이 없음
- artifact가 stale
- 일부 dependency가 freshness 기준을 벗어남

즉 기존 surface는 보이지만 운영 신뢰도가 흔들리는 상태다.

### BLOCKED

아래 같은 경우는 `BLOCKED`다.

- dependency summary 자체가 없음
- upstream summary status가 `BLOCKED`

즉 새 해석층을 얹기 전에 기존 계측 체계가 먼저 깨진 상태다.

## 5. 구현 원칙

### 5-1. 기존 계산 로직은 재사용만 한다

`S0`는 아래 기존 summary를 다시 계산하지 않는다.

- `runtime_signal_wiring_audit`
- `ca2_r0_stability`
- `ca2_session_split`
- `should_have_done`
- `canonical_surface`
- `session_bias_shadow`

이미 생성된 report를 받아서 상태만 판정한다.

### 5-2. HOLD와 BLOCKED를 구분한다

artifact stale이나 일부 freshness 흔들림은 `HOLD`다.
summary가 사라졌거나 upstream이 `BLOCKED`면 그때 `BLOCKED`다.

즉 운영상 거칠어지는 경우와 실제 계측 붕괴를 분리한다.

### 5-3. dependency별 이유를 남긴다

최종 summary 하나만 남기면 나중에 왜 `HOLD`였는지 알기 어렵다.
그래서 dependency별로 다음을 남긴다.

- dependency status
- upstream status
- summary freshness
- artifact freshness
- dependency reasons

## 6. 산출물

### runtime detail

- `state_strength_s0_stability_summary_v1`
- `state_strength_s0_stability_artifact_paths`

### artifact

- `data/analysis/shadow_auto/state_strength_s0_stability_latest.json`
- `data/analysis/shadow_auto/state_strength_s0_stability_latest.md`

## 7. S0가 다음 단계에 주는 의미

`S0`는 성능 개선 단계가 아니다.
대신 아래 질문에 먼저 답한다.

- 새 dominance 계층을 붙여도 기존 CA2가 살아 있는가
- 기존 session split / should-have-done / canonical / shadow bias가 계속 갱신되는가
- runtime detail과 shadow artifact가 같은 주기로 유지되는가

즉 `S0`가 있어야 이후 `S1~S8`을 안심하고 올릴 수 있다.
