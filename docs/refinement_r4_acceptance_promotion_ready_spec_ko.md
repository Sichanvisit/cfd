# R4 Acceptance / Promotion-Ready Spec

## 1. 목적

이 문서는 R3와 post-Step7 follow-up이 정리된 이후,
`preview audit = healthy`, `shadow compare = healthy`, `promotion_gate = pass`
상태를 실제 운영 승격 기준으로 어떻게 해석할지 고정한다.

핵심 질문은 세 가지다.

- 지금 상태를 `promotion-ready`로 봐도 되는가
- 된다면 어디까지를 `bounded live`로 허용할 것인가
- 아직 확장하면 안 되는 운영 리스크는 무엇인가

이번 단계는 모델을 더 좋게 만드는 단계가 아니라,
이미 건강해진 결과를 운영 게이트와 runbook으로 바꾸는 단계다.

## 2. 현재 baseline

### preview / shadow 기준

- latest audit: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- latest healthy shadow compare baseline: [semantic_shadow_compare_report_20260326_200401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_200401.json)
- latest slice-sparsity follow-up memo: [refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md)

현재 확인된 상태:

- `promotion_gate.status = pass`
- `promotion_gate.warning_issues = []`
- `shadow_compare_status = healthy`
- `entry_quality / exit_management`의 남아 있던 split warning은 unsupported sparse slice taxonomy로 정리됨

### runtime rollout 기준

- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

현재 runtime 기준 상태:

- `semantic_live_config.mode = threshold_only`
- `symbol_allowlist = ["BTCUSD"]`
- `kill_switch = false`
- `shadow_runtime_state = active`
- recent rollout state는 여전히 `trace_quality_state = fallback_heavy`와 `symbol_not_in_allowlist`를 자주 surface 함

즉 preview/shadow는 건강하지만, live rollout은 아직 매우 보수적이고 제한적인 상태다.

## 3. 이번 단계의 목표

1. `promotion-ready`를 문서상 pass와 운영상 pass로 분리한다.
2. `threshold_only -> bounded live` 승격 조건을 고정한다.
3. symbol / mode / kill switch / rollback 기준을 runbook 수준으로 정리한다.
4. 현재 runtime fallback-heavy recent를 bounded-live 확장의 blocker로 볼지, 관측 항목으로만 둘지 결정한다.

## 4. 이번 단계에서 다룰 owner

직접 owner:

- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)
- [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)
- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)
- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

간접 owner:

- [trading_application.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- semantic rollout manifest / preview audit 산출물

## 5. 이번 단계에서 다루지 않을 것

- chart / Stage E 추가 미세조정
- timing / entry_quality / exit_management target 재정의
- shadow compare source alignment 재수정
- 새로운 bounded live 확장 실행

즉 이번 단계는 `지금 바로 확장`이 아니라
`확장할 수 있는지 판단하는 기준을 고정`하는 단계다.

## 6. promotion-ready 해석 기준

### A. 문서상 promotion-ready

아래가 모두 충족되면 문서상 promotion-ready로 본다.

- preview audit `promotion_gate.status = pass`
- `warning_issues = []`
- shadow compare `healthy`
- split / join / source provenance 이슈가 닫혀 있음

### B. 운영상 promotion-ready

아래가 추가로 충족돼야 운영상 promotion-ready로 본다.

- runtime recent rollout이 기대한 domain/symbol에서 정상 surface 됨
- kill switch / rollback path가 실제로 설명 가능함
- allowlist 확장 순서가 고정돼 있음
- fallback-heavy recent를 감수할지, clean-trace를 요구할지 policy가 명시돼 있음

즉 문서상 pass가 곧바로 live expansion을 뜻하지는 않는다.

## 7. bounded live 기본 원칙

### 1. 단계 확장

권장 순서:

1. `threshold_only + single symbol`
2. `threshold_only + multi symbol`
3. `partial_live + single symbol`
4. `partial_live + multi symbol`

이번 spec의 기본 가정은
현재가 `1단계 후반` 혹은 `2단계 직전`이라는 것이다.

### 2. symbol 확장 원칙

기본 원칙:

- 이미 allowlist에 있는 `BTCUSD`를 기준 심볼로 유지
- 확장은 `NAS100`과 `XAUUSD`를 동시에 여는 방식보다 단계적으로 연다
- symbol 확장 전에는 최근 rollout recent와 fallback reason이 설명 가능해야 한다

### 3. trace quality 해석

현재 runtime recent에서 `fallback_heavy`가 자주 보여도,
preview/shadow/source cleanup 기준으로는 구조 bug가 아닐 수 있다.

그래서 R4에서는 다음처럼 읽는다.

- `fallback_heavy` 자체는 즉시 blocker가 아니다
- 그러나 bounded live로 갈 때는 최소한 reason taxonomy가 해석 가능해야 한다
- `fallback_heavy + baseline_no_action`과
  `fallback_heavy + symbol_not_in_allowlist`는 서로 다른 운영 의미로 본다

## 8. gate 분류

### Gate A. Audit Gate

소스:

- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

판정:

- `pass`: warning 없음, shadow compare healthy
- `hold`: warning 또는 source/split 이슈 존재
- `stop`: blocking issue 존재

### Gate B. Runtime Gate

소스:

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

판정:

- `pass`: current mode / allowlist / kill switch / recent reason이 설명 가능
- `hold`: recent reason 해석은 되지만 확장 근거가 아직 약함
- `stop`: kill switch 필요, unexpected fallback spike, unresolved runtime mismatch

### Gate C. Promotion Action Gate

판정 대상:

- `stay_threshold_only`
- `expand_allowlist`
- `enable_partial_live`
- `rollback`

이번 단계의 기본 목표는
`stay_threshold_only`와 `expand_allowlist` 사이를 판단 가능하게 만드는 것이다.

## 9. 권장 실행 순서

1. runtime baseline snapshot 고정
2. current mode / allowlist / fallback reason casebook 작성
3. promotion action matrix 정의
4. rollback / kill switch 기준 정리
5. implementation checklist 작성
6. 그 뒤에만 bounded live 관련 실제 코드/설정 변경 검토

## 10. 완료 기준

- `promotion-ready`가 문서상/운영상으로 분리 정의된다.
- `threshold_only 유지`, `allowlist 확장`, `partial_live 진입`, `rollback` 기준을 설명 가능하다.
- 현재 runtime 상태가 왜 아직 보수적인지 문서와 산출물로 설명 가능하다.
- 다음 턴에서 구현/설정 변경에 들어가도 기준이 흔들리지 않는다.
