# Profitability / Operations P7 Guarded Size Overlay Experiment Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 P7 결과를 기준으로 지금 당장 실험 가능한 유일한 guarded apply candidate인 `size_overlay_guarded_apply`를 실제 운영 실험 후보로 좁히기 위한 실행 로드맵이다.

현재 active verification 기준과 단계별 실행 순서는 아래 전용 문서를 함께 본다.

- [profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md)
- [profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md)
- [profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md)

핵심 질문은 아래다.

`지금 P7가 허용한 size reduction proposal을 어떻게 작고 안전한 실험으로 내릴 것인가?`

## 2. 왜 size overlay부터 가는가

현재 P7 latest 기준 공식 해석은 아래다.

- `guarded_apply_candidate`: size overlay only
- `review_only`: XAU timing review 계열
- `no_go`: legacy identity restore first 계열

즉 지금 당장 가장 자연스러운 실험은 `scene logic 변경`이 아니라 `size overlay 보수 적용`이다.

## 3. 현재 guarded apply 후보

기준 산출물:

- [profitability_operations_p7_counterfactual_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.json)
- [profitability_operations_p6_health_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.json)

현재 후보는 아래 3개다.

### XAUUSD

- current state: `stressed`
- proposal: `hard_reduce`
- target multiplier: `0.25`
- rationale: `fast_adverse_close_alert` pressure + worst scene 다수

### NAS100

- current state: `stressed`
- proposal: `hard_reduce`
- target multiplier: `0.43`
- rationale: `zero_pnl_information_gap_alert` + legacy pressure

### BTCUSD

- current state: `watch`
- proposal: `reduce`
- target multiplier: `0.57`
- rationale: `blocked_pressure_alert` 중심의 watch 상태

## 4. 실험 원칙

이번 실험은 아래 원칙을 지켜야 한다.

1. semantic core / setup logic / timing rule은 건드리지 않는다.
2. size overlay만 별도 config / policy layer로 붙인다.
3. one-shot 큰 변경이 아니라 `guarded step`으로만 간다.
4. 먼저 dry-run / shadow compare를 보고, 그다음 limited apply로 간다.
5. XAU timing review와 legacy identity restore는 이번 실험 범위에서 제외한다.

## 5. 실행 순서

### Overlay-1. Baseline Freeze

목표:

- size overlay 적용 전 기준선을 잠근다.

필수 산출물:

- current P4 latest
- current P5 latest
- current P6 latest
- current P7 latest

핵심 이유:

- 적용 후 변화가 실제 개선인지 확인하려면 before snapshot이 있어야 한다.

### Overlay-2. Config Surface Identification

목표:

- size overlay를 어디에서 읽고 적용할지 config / policy owner를 고정한다.

권장 방향:

- semantic core가 아니라 policy / execution overlay에서 읽는다.
- symbol별 multiplier override가 가능해야 한다.

예상 owner:

- entry sizing / execution policy 쪽
- live config / overlay loader 쪽

### Overlay-3. Dry-Run Proposal Materialization

목표:

- 실제 live apply 전에 proposal을 dry-run overlay row로 내린다.

권장 shape:

- symbol
- current size mode
- proposed multiplier
- proposal source (`P7`)
- gate reason
- effective from / review by

핵심 이유:

- operator가 적용값을 보기 전에 proposal row를 먼저 검토할 수 있어야 한다.

### Overlay-4. Guarded Limited Apply

목표:

- 작은 폭으로만 실제 overlay를 적용한다.

권장 제약:

- XAU: 바로 `0.25` 전체 적용 대신 `0.10 cap` 기준의 단계적 축소
- NAS: 단계적 축소
- BTC: `reduce` 수준 유지

즉 첫 적용은 `target multiplier를 향한 full jump`가 아니라 `guarded step`이 맞다.

### Overlay-5. Rerun and Delta Review

목표:

- 적용 후 P4~P7을 다시 돌려 delta를 본다.

필수 확인:

- `active_alert_delta` 완화 여부
- `fast_adverse_close_alert` 완화 여부
- `blocked_pressure_alert` 완화 여부
- stressed / watch 분포 변화
- guarded_apply queue 변화

### Overlay-6. Close-Out or Rollback

목표:

- 실험이 의미 있었는지 닫는다.

유지 조건:

- alert pressure 완화
- health state 악화 없음
- no_go / review_only 구조 훼손 없음

롤백 조건:

- alert pressure 악화
- size reduction 후에도 negative pressure 심화
- 기대한 symbol health 개선이 전혀 없음

## 6. 이번 실험에서 제외할 것

아래는 이번 로드맵 범위 밖이다.

- XAU timing rule 변경
- exit profile swap
- legacy identity gap scene counterfactual 적용
- auto-adaptation / self-tuning

## 7. 성공 기준

이번 overlay 실험이 성공이라고 보려면 아래 중 일부가 보여야 한다.

1. XAU / NAS alert pressure가 완화된다.
2. BTC blocked pressure가 완화된다.
3. P6 health가 `stressed -> watch` 또는 `reduce -> hold_small` 쪽으로 완화된다.
4. P7에서 guarded apply가 size overlay 외 proposal로 무리하게 확장되지 않는다.

## 8. 다음 handoff

이 실험 이후 자연스러운 다음 갈래는 아래 둘 중 하나다.

1. guarded size overlay 유지 / 확장
2. XAU timing review를 `review_only -> guarded candidate`로 올릴지 재검토

단, 두 번째는 `legacy identity pressure`가 더 줄어든 뒤에만 보는 것이 맞다.

## 9. 결론

지금 단계에서 가장 맞는 다음 실험은 `작고 보수적인 size overlay`다.

즉 다음은 `전략 개조`가 아니라, 이미 P7가 허용한 가장 작은 적용 후보를 운영적으로 검증하는 단계다.
