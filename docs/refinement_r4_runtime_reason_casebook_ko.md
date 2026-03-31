# R4 Runtime Reason Casebook

## 1. 목적

이 문서는 R4에서 `runtime recent`에 surface 되는 semantic rollout reason을
운영 의사결정 언어로 해석하기 위한 casebook이다.

이번 casebook의 목적은

- 어떤 reason이 정상적인 보수 모드의 결과인지
- 어떤 reason이 allowlist 확장 전 보류 항목인지
- 어떤 reason이 실제 rollback / stop 사유인지

를 분리하는 것이다.

## 2. 기준 산출물

- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- preview audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

## 3. 현재 recent snapshot

2026-03-26 21:48 KST 기준 recent 40 rows 요약:

- `mode_counts`
  - `threshold_only = 40`
- `symbol_counts`
  - `BTCUSD = 14`
  - `NAS100 = 13`
  - `XAUUSD = 13`
- `trace_quality_state`
  - `fallback_heavy = 40`
- `fallback_reason`
  - `baseline_no_action = 14`
  - `symbol_not_in_allowlist = 26`

즉 현재 recent는 아래 두 가지 이유가 거의 전부다.

1. baseline이 애초에 no-action이라 semantic도 threshold를 적용하지 않은 경우
2. semantic score는 높아도 symbol이 allowlist 바깥이라 live 조정이 막힌 경우

## 4. owner 기준 해석

직접 owner:

- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)

### 4-1. `baseline_no_action`

의미:

- semantic 예측이 들어와도 baseline action이 비어 있으면
  `threshold_only`에서는 개입하지 않는다는 뜻이다.

코드 owner:

- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
  - `elif not baseline_has_action: fallback_reason = "baseline_no_action"`

운영 해석:

- 버그가 아니다
- 현재 `rule baseline owner` 원칙을 그대로 지키는 정상 동작이다
- bounded live 전 단계에서는 오히려 기대된 보수 동작이다

판정:

- 분류: `정상 / 관측`
- rollback 사유: 아님
- allowlist 확장 blocker: 아님
- partial_live 직행 근거: 아님

### 4-2. `symbol_not_in_allowlist`

의미:

- semantic signal이 있어도 해당 symbol은 아직 운영 적용 대상이 아니므로
  live 조정이 막힌다는 뜻이다.

코드 owner:

- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
  - `elif symbol_allowlist and symbol_u not in symbol_allowlist: fallback_reason = "symbol_not_in_allowlist"`

운영 해석:

- 품질 문제라기보다 운영 확장 정책 문제다
- preview/shadow가 healthy해도 allowlist가 닫혀 있으면 계속 보인다
- `NAS100`, `XAUUSD`에서 반복되는 이유가 바로 이 항목이다

판정:

- 분류: `정상 / 확장 후보`
- rollback 사유: 아님
- allowlist 확장 논의 대상: 맞음
- partial_live 직행 근거: 아님

### 4-3. `trace_quality_state = fallback_heavy`

의미:

- runtime adapter가 현재 row를 `clean`이 아니라 fallback-heavy로 읽는다는 뜻이다.

코드 owner:

- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)
  - `resolve_trace_quality_state(...)`

중요한 현재 해석:

- 이 값 자체가 즉시 구조 버그를 뜻하지는 않는다
- preview / shadow / runtime source cleanup 기준으로는
  provenance mismatch가 이미 정리된 상태다
- 현재 recent에서 계속 보이는 것은
  live row가 compatibility/fallback 성격을 아직 많이 띠고 있다는 뜻에 더 가깝다

판정:

- 분류: `관측 / bounded-live 전 주의`
- rollback 사유: 단독으론 아님
- allowlist 확장 blocker: 단독으론 아님
- partial_live 진입 전 review 필요 항목: 맞음

## 5. 현재 recent를 어떻게 읽어야 하나

현재 recent 40건은 이렇게 읽는 것이 정확하다.

### BTCUSD

- allowlist 안에 있음
- semantic 값은 높아도 `baseline_no_action`이면 threshold 적용이 일어나지 않음
- 즉 BTC의 recent는 `semantic quality 부족`보다 `rule baseline 우선` 성격이 더 강함

### NAS100 / XAUUSD

- semantic 값은 반복적으로 높게 surface 되지만
- 운영상 allowlist 바깥이라 전부 `symbol_not_in_allowlist`
- 즉 현재 recent는 품질 blocker가 아니라 확장 미적용 상태를 보여준다

## 6. stop / hold / advance 분류

### `정상`

- `baseline_no_action`
- `symbol_not_in_allowlist`

둘 다 현재 운영 정책 안에 있는 결과다.

### `hold`

- `fallback_heavy` 반복 surface

이 항목은 즉시 stop은 아니지만,
partial_live 전에 한 번 더 운영상 허용 범위를 정해야 하는 항목이다.

### `stop`

현재 recent에서는 즉시 stop 사유가 보이지 않는다.

예상 stop 후보는 별도:

- `kill_switch_enabled`
- `compatibility_mode_blocked`
- `trace_quality_unknown / incomplete`
- preview gate fail 재발

## 7. 현재 결론

현재 runtime recent는
`품질이 안 좋아서 막힌 상태`라기보다
`운영 정책상 보수적으로 막아둔 상태`에 가깝다.

즉 다음 액션은

- reason taxonomy를 더 손보는 것

보다

- 언제 `allowlist 확장`을 할지
- 언제 `threshold_only 유지`를 계속할지
- 언제 `partial_live`를 논의할지

를 action matrix로 고정하는 것이다.
