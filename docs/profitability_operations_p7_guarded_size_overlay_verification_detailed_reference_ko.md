# Profitability / Operations P7 Guarded Size Overlay Verification Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 가장 중요한 메인축인
`P7 guarded size overlay 검증`
을 독립적으로 설명하기 위한 상세 기준 문서다.

핵심 질문은 아래다.

`우리가 이미 구현한 guarded size overlay를 어떤 순서와 어떤 판단 기준으로 검증하고, 어디까지를 안전한 apply 범위로 볼 것인가?`

이 문서는 새 기능을 더 만드는 문서가 아니다.
이미 구현된 overlay surface를
운영 검증 대상으로 읽기 위한 기준 문서다.

## 2. 왜 지금 이 트랙이 메인축인가

현재 P0~P7 close-out 기준으로,
실제로 guarded apply 후보로 남아 있는 것은 `size overlay`뿐이다.

현재 공식 해석:

- `guarded apply`: size overlay only
- `review_only`: XAU timing 계열
- `no_go`: legacy identity restore first 계열

즉 지금 시점의 메인축은
차트 표시를 더 다듬는 일이나
새 semantic rule을 추가하는 일이 아니라,
`이미 허용된 가장 작은 적용 후보를 운영적으로 검증하는 일`이다.

대표 기준 문서:

- [profitability_operations_p0_to_p7_master_close_out_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_to_p7_master_close_out_ko.md)
- [profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md)
- [profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md)

## 3. 현재까지 구현된 것

이번 검증은 바닥부터 새로 만드는 것이 아니다.
아래는 이미 구현 완료 상태다.

### 3-1. Proposal materialization

P7 latest에서 guarded apply 가능 후보만 따로 추려
overlay latest로 materialize하는 스크립트가 있다.

- [profitability_operations_p7_guarded_size_overlay_materialize.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p7_guarded_size_overlay_materialize.py)

최신 산출물:

- [profitability_operations_p7_guarded_size_overlay_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_latest.json)

현재 후보 3개:

- `XAUUSD -> 0.25`
- `NAS100 -> 0.43`
- `BTCUSD -> 0.57`

### 3-2. Runtime resolver

entry 실행 직전 overlay source를 읽고,
`disabled / dry_run / apply`에 따라 effective multiplier를 계산하는 resolver가 있다.

- [p7_guarded_size_overlay.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p7_guarded_size_overlay.py)

### 3-3. Entry hook

overlay는 semantic core가 아니라 execution lot 계산 직전에만 붙는다.

- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

즉 setup, side, timing rule은 건드리지 않는다.
오직 lot sizing만 보수적으로 조정한다.

### 3-4. Logging surface

entry decision row에는 아래 trace가 남도록 확장되어 있다.

- `p7_guarded_size_overlay_v1`
- `p7_size_overlay_enabled`
- `p7_size_overlay_mode`
- `p7_size_overlay_matched`
- `p7_size_overlay_target_multiplier`
- `p7_size_overlay_effective_multiplier`
- `p7_size_overlay_apply_allowed`
- `p7_size_overlay_applied`
- `p7_size_overlay_gate_reason`
- `p7_size_overlay_source`

관련 owner:

- [entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)
- [storage_compaction.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

### 3-5. Config surface

현재 env/config surface도 이미 있다.

- [config.py](C:\Users\bhs33\Desktop\project\cfd\backend\core\config.py)
- [\.env](C:\Users\bhs33\Desktop\project\cfd\.env)

현재 기준:

- `ENABLE_P7_GUARDED_SIZE_OVERLAY=true`
- `P7_GUARDED_SIZE_OVERLAY_MODE=dry_run`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST=` (비워둠)

## 4. 현재 실제 상태

가장 중요한 현재 상태는 아래다.

### 4-1. 재시작 완료

runtime는 이미 재시작되었다.
즉 `.env`의 `dry_run` 설정은 새 프로세스부터 반영되는 상태다.

### 4-2. 새 row 스키마 준비 완료

현재 [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
헤더에는 이미 `p7_guarded_size_overlay_*` 컬럼이 포함되어 있다.

즉 schema 준비는 끝났다.

### 4-3. 아직 dry-run trace는 쌓이지 않음

최신 review:

- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_dry_run_latest.json)

현재 핵심 값:

- `entry_decision_row_count = 26`
- `p7_schema_present = true`
- `p7_trace_row_count = 0`
- `review_state = waiting_for_first_dry_run_rows`

이 의미는 분명하다.

- 설정이 안 먹은 게 아니다.
- schema가 없는 것도 아니다.
- 단지 재시작 이후 첫 신규 entry row가 아직 충분히 쌓이지 않은 상태다.

즉 지금은 `재시작을 또 해야 하는 단계`가 아니라
`조금 더 운영한 뒤 review를 다시 돌려야 하는 단계`다.

## 5. 이번 검증에서 확인해야 하는 것

이번 검증의 목표는 “기능이 돌아간다” 수준이 아니다.
아래 네 질문에 답해야 한다.

### 5-1. dry-run trace가 실제로 남는가

즉 entry row에 아래가 실제로 찍히는가를 본다.

- `p7_size_overlay_mode = dry_run`
- `p7_size_overlay_matched = true/false`
- `p7_size_overlay_target_multiplier`
- `p7_size_overlay_effective_multiplier`
- `p7_size_overlay_gate_reason`

### 5-2. 어떤 symbol에서 실제 후보가 잡히는가

현재 후보는 XAU / NAS / BTC지만,
실제 신규 row에서 어떤 symbol이 trace를 남기는지 확인해야 한다.

### 5-3. gate reason이 합리적인가

예를 들어 다음 구분이 읽혀야 한다.

- overlay candidate가 없어서 unmatched인지
- symbol allowlist가 비어 있어서 관측만 되는지
- current multiplier 대비 줄일 값이 없어 no-op인지
- max step cap 때문에 부분 축소로만 반영되는지

### 5-4. first apply 후보는 정말 BTC만이 맞는가

현재 운영 판단은 BTC가 가장 좁은 guarded candidate다.
dry-run 누적에서도 이 판단이 유지되는지 확인해야 한다.

## 6. 왜 BTCUSD first apply인가

현재 해석은 아래 때문이다.

- XAUUSD는 `stressed / hard_reduce`이긴 하지만 timing review와 fast-adverse pressure가 더 강하다.
- NAS100은 `stressed / hard_reduce`이지만 zero-pnl information gap과 legacy pressure가 더 크다.
- BTCUSD는 `watch / reduce` 수준으로 상대적으로 좁고 보수적인 apply 후보다.

즉 첫 apply는
`가장 큰 문제가 있는 symbol`
이 아니라
`가장 작은 범위로 안전하게 검증 가능한 symbol`
을 택해야 한다.

그래서 현재 1차 apply 후보는 `BTCUSD only`다.

## 7. 이번 검증에서 하지 않을 것

아래는 이번 검증 범위 밖이다.

- XAU timing rule 수정
- setup logic 변경
- exit profile swap
- legacy identity restore live 적용
- auto-adaptation / self-tuning

즉 이번 트랙은 `전략 개조`가 아니라
`size overlay 운영 검증`이다.

## 8. acceptance 기준

이번 검증은 아래 순서로 acceptance를 본다.

### A. dry-run acceptance

- `p7_schema_present = true`
- `p7_trace_row_count > 0`
- symbol / mode / gate_reason summary가 실제로 채워짐

### B. narrow apply readiness

- dry-run에서 BTCUSD trace가 최소한의 수로 반복 관측됨
- gate reason이 설명 가능함
- apply 전에 no_go/review_only 계열을 건드리지 않음

### C. apply acceptance

- BTC only apply 후 lot reduction trace가 실제 row에 남음
- alert pressure가 악화되지 않음
- P6 health가 추가 악화되지 않음
- P7 proposal 구조가 무리하게 확장되지 않음

## 9. close-out 후 갈래

이번 검증 이후 갈래는 두 개다.

### 유지 / 확장

- BTC only apply가 안정적이면 유지
- 이후 NAS 또는 XAU를 볼지 재검토

### 롤백 / 보류

- dry-run은 잘 되지만 apply 후 압력이 악화되면 롤백
- 여전히 XAU timing이나 legacy identity가 더 큰 문제면 size overlay 확장은 보류

## 10. 결론

이 문서의 핵심은 아래 한 줄이다.

```text
지금 메인축은 새 로직을 만드는 것이 아니라,
이미 구현된 guarded size overlay가 실제 row에 어떻게 남는지 확인하고,
그 뒤 BTCUSD만 좁게 apply할 수 있는지 검증하는 것이다.
```
