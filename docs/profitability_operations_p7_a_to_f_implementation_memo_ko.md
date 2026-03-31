# Profitability / Operations P7 A~F Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 구현 범위

이번 구현에서 P7 `A ~ F`를 첫 canonical surface 수준까지 한 번에 열었다.

- `P7-A`: P4 / P5 / P6 latest input contract freeze
- `P7-B`: scene review candidate extraction
- `P7-C`: proposal typing / evidence scoring
- `P7-D`: safety gate / guarded application filter
- `P7-E`: first canonical P7 report
- `P7-F`: operator handoff memo

## 2. 추가된 파일

- script:
  - [profitability_operations_p7_counterfactual_selective_adaptation_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p7_counterfactual_selective_adaptation_report.py)
- test:
  - [test_profitability_operations_p7_counterfactual_selective_adaptation_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p7_counterfactual_selective_adaptation_report.py)
- latest output:
  - [profitability_operations_p7_counterfactual_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.json)
  - [profitability_operations_p7_counterfactual_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.csv)
  - [profitability_operations_p7_counterfactual_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.md)

## 3. 첫 버전에서 고정한 proposal 타입

- `entry_delay_review`
- `exit_profile_review`
- `size_overlay_guarded_apply`
- `legacy_identity_restore_first`
- `counterfactual_hold_for_more_evidence`

## 4. 첫 버전에서 고정한 safety gate

- `identity_first_gate`
- `coverage_gate`
- `low_evidence_gate`
- `hold_for_more_evidence_gate`
- `stressed_symbol_review_only`
- `passed`

## 5. 현재 latest 해석

현재 latest 기준 핵심 분포는 아래다.

- `proposal_count = 18`
- `guarded_apply_count = 3`
- `review_only_count = 3`
- `no_go_count = 12`
- `top_proposal_type = legacy_identity_restore_first`

즉 현재 P7은 `무엇이든 실험하자`가 아니라, `대부분은 아직 identity-first no-go`, `일부는 review-only`, `size reduction만 guarded apply 가능`이라는 구조로 읽힌다.

## 6. 구현상 중요한 판단

### 6-1. scene proposal과 symbol size proposal을 분리

scene worst candidate는 counterfactual review 중심으로 읽고, symbol health는 `size_overlay_guarded_apply`로 별도 제안 row를 만든다.

### 6-2. identity-first 우선

`legacy_bucket_identity_restore` 계열 scene는 다른 adaptation보다 먼저 `no_go / identity_first_gate`로 묶는다.

### 6-3. stressed symbol timing proposal은 review-only

XAU처럼 `fast_adverse_close`가 강해도 stressed symbol의 entry timing proposal은 바로 guarded apply로 올리지 않고 `review_only`로 유지한다.

### 6-4. size reduction은 guarded apply 허용

반대로 `size_overlay_guarded_apply`는 보수적 축소 제안이므로 첫 버전에서도 guarded apply candidate로 올릴 수 있게 했다.

## 7. 다음 확인 포인트

다음 rerun에서 특히 볼 것은 아래다.

- `legacy_identity_restore_first` 비중이 줄어드는가
- `entry_delay_review`가 review-only에서 guarded apply로 승격될 scene가 생기는가
- XAU / NAS / BTC size overlay recommendation이 더 보수적으로 가야 하는가, 완화되는가
