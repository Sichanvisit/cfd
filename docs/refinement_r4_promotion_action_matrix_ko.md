# R4 Promotion Action Matrix

## 1. 목적

이 문서는 현재 semantic rollout 상태에서 가능한 운영 action을
`유지 / 확장 / 승격 / 롤백` 네 갈래로 고정한다.

기준 산출물:

- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)

## 2. 현재 기준선

현재 상태:

- preview gate: `pass`
- warning issues: 없음
- shadow compare: `healthy`
- live mode: `threshold_only`
- symbol allowlist: `BTCUSD` only
- recent runtime reason: `baseline_no_action`, `symbol_not_in_allowlist`, `fallback_heavy`

즉 현재 위치는
`운영 가능한 최소 보수 모드`로 해석하는 것이 맞다.

## 3. action 정의

### Action A. `stay_threshold_only`

의미:

- 현재 mode와 allowlist를 유지한다
- semantic은 계속 shadow/alert/threshold 참고 역할을 한다

언제 선택하나:

- preview/shadow는 healthy지만
- allowlist 확장 근거가 아직 부족할 때
- runtime reason taxonomy는 읽히지만 fallback-heavy 운영 기준이 아직 안 잠겼을 때

현재 추천:

- 기본 추천 action

### Action B. `expand_allowlist`

의미:

- mode는 `threshold_only` 그대로 두고
- symbol allowlist만 제한적으로 확장한다

언제 선택하나:

- preview/shadow pass 유지
- recent runtime reason이 `symbol_not_in_allowlist` 중심일 때
- 해당 symbol의 chart/Stage E/semantic preview 품질이 별도 관측상 납득될 때

주의:

- allowlist 확장은 partial_live보다 한 단계 앞이다
- `BTCUSD -> NAS100` 또는 `BTCUSD -> XAUUSD` 식으로 순차 확장이 안전하다

### Action C. `enable_partial_live`

의미:

- semantic이 threshold 조정뿐 아니라 부분 live weight나 action에 더 직접 관여한다

언제 선택하나:

- preview/shadow pass 유지
- runtime recent에서 trace quality와 fallback reason 해석 기준이 운영상 충분히 잠겼을 때
- allowlist 확장 후에도 이상 징후가 없을 때

현재 추천:

- 아직 이름만 열어두고 실제 진입은 보류

### Action D. `rollback / kill_switch`

의미:

- semantic live 영향도를 즉시 줄이거나 끈다

언제 선택하나:

- preview gate fail 재발
- shadow compare unhealthy 재발
- runtime provenance mismatch 재발
- kill switch owner가 실제로 필요한 이상 증후가 생길 때

현재 추천:

- contingency only

## 4. 현재 상태에서의 판정

### `stay_threshold_only`

- 판정: `pass`
- 근거:
  - 현재 healthy preview/shadow와 모순되지 않음
  - runtime recent도 explainable

### `expand_allowlist`

- 판정: `conditional pass`
- 근거:
  - `symbol_not_in_allowlist`가 recent의 큰 부분을 차지함
  - 즉 확장 후보가 이미 보임
- 조건:
  - 어떤 symbol을 먼저 열지 별도 합의 필요
  - fallback-heavy 운영 해석을 먼저 문서화해야 함

### `enable_partial_live`

- 판정: `hold`
- 근거:
  - 현재 recent가 전부 `threshold_only`
  - fallback-heavy recent를 운영상 어디까지 허용할지 아직 정식 기준이 없음

### `rollback / kill_switch`

- 판정: `standby`
- 근거:
  - 지금은 stop 사유가 보이지 않음
  - 다만 기준은 미리 잠가둘 필요가 있음

## 5. 추천 운영 순서

현재 시점의 추천 순서는 아래와 같다.

1. `stay_threshold_only`
2. rollback / kill switch 기준 문서화
3. symbol allowlist 확장 후보 1개 선택
4. 그 다음에만 `expand_allowlist`
5. `partial_live`는 그 다음 평가 대상

즉 지금은
`바로 partial_live`가 아니라
`threshold_only 유지 + allowlist 확장 기준 고정`
이 맞다.

## 6. 다음 구현 후보

이 문서 기준 다음 구현 후보는 두 가지다.

1. `rollback / kill switch contract memo`
2. `allowlist expansion candidate memo`

둘 중 하나를 고른 뒤 실제 설정 변경 전 문서를 더 잠그는 것이 안전하다.
