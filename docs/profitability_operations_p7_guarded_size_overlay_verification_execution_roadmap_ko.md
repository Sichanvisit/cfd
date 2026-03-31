# Profitability / Operations P7 Guarded Size Overlay Verification Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 메인축인
`P7 guarded size overlay verification`
을 실제 실행 가능한 순서로 쪼개기 위한 로드맵이다.

상세 기준은 아래 문서를 함께 본다.

- [profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md)
- [profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_remaining_main_axis_master_plan_ko.md)

## 2. 전체 흐름

```text
V0. baseline and current state freeze
-> V1. wait for post-restart dry-run rows
-> V2. dry-run review and accept/reject
-> V3. BTC-only apply preparation
-> V4. BTC-only apply
-> V5. rerun + delta review
-> V6. close-out / keep / rollback
```

## 3. 현재 시작점

현재 시작점은 아래처럼 읽는다.

- runtime restart 완료
- `entry_decisions.csv` 헤더에 p7 overlay schema 존재
- dry-run review latest는 `waiting_for_first_dry_run_rows`
- 즉 다음 active step은 `V1`이다

기준 산출물:

- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_dry_run_latest.json)

## 4. V0. Baseline and Current State Freeze

### 목표

현재 운영 기준선과 현재 실험 상태를 함께 고정한다.

### 확인할 것

- current P4 latest
- current P5 latest
- current P6 latest
- current P7 latest
- current guarded overlay latest
- current dry-run latest

### 완료 기준

- 지금부터의 변화가 before/after 비교 가능 상태다

### 현재 상태

이미 사실상 완료 상태로 본다.

## 5. V1. Wait for Post-Restart Dry-Run Rows

### 목표

재시작 이후 실제 신규 entry row가 쌓여
P7 overlay trace가 찍히기 시작하는지 본다.

### 해야 할 일

1. runtime를 그대로 운영한다
2. 신규 entry row가 쌓일 시간을 둔다
3. dry-run review 스크립트를 다시 실행한다

### 사용 스크립트

- [profitability_operations_p7_guarded_size_overlay_dry_run_review.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p7_guarded_size_overlay_dry_run_review.py)

### 완료 기준

- `p7_trace_row_count > 0`
- `review_state != waiting_for_first_dry_run_rows`

## 6. V2. Dry-Run Review and Accept/Reject

### 목표

실제로 누적된 dry-run trace가 apply 준비로 넘어갈 만큼 읽을 가치가 있는지 판단한다.

### 확인할 것

- mode summary
- gate reason summary
- symbol dry-run summary
- BTC trace 존재 여부
- gate reason이 설명 가능한지

### accept 조건

- BTCUSD trace가 관측된다
- dry-run row가 최소한의 수 이상 쌓인다
- gate reason이 노이즈가 아니라 해석 가능한 패턴을 보인다

### reject/hold 조건

- trace가 거의 없거나
- 특정 symbol만 과도하게 몰리거나
- gate reason이 대부분 unexpected / empty 상태면
  apply로 가지 않고 dry-run을 더 본다

## 7. V3. BTC-Only Apply Preparation

### 목표

apply를 가장 좁은 범위로만 연다.

### 해야 할 일

1. allowlist를 `BTCUSD`로만 제한한다
2. mode를 `apply`로 올릴 준비를 한다
3. `max_step` cap은 유지한다
4. XAU/NAS는 이번 단계에서 제외한다

### 변경 surface

- [\.env](C:\Users\bhs33\Desktop\project\cfd\.env)

예상 변경:

- `P7_GUARDED_SIZE_OVERLAY_MODE=apply`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST=BTCUSD`

### 완료 기준

- apply 범위가 BTC only로 제한된 상태에서 재시작 준비가 끝난다

## 8. V4. BTC-Only Apply

### 목표

BTCUSD에만 실제 guarded size reduction을 연다.

### 해야 할 일

1. runtime 재시작
2. 신규 entry row 누적
3. 실제 apply trace 확인

### 확인할 것

- `p7_size_overlay_mode = apply`
- `p7_size_overlay_applied = true`
- `p7_size_overlay_effective_multiplier < current`
- symbol = `BTCUSD`

### 완료 기준

- BTC only apply trace가 실제 row에 남는다

## 9. V5. Rerun + Delta Review

### 목표

apply 이후 운영 pressure가 실제로 나빠지지 않았는지 확인한다.

### 다시 볼 것

- P4 compare
- P5 casebook
- P6 health
- P7 counterfactual / guarded proposal

### 핵심 질문

- BTC blocked pressure가 완화되는가
- alert pressure가 악화되지는 않는가
- health state가 더 나빠지지 않는가
- guarded proposal 구조가 무너지지 않는가

### 완료 기준

- 최소한 악화 없음
- 가능하면 일부 완화 신호 존재

## 10. V6. Close-Out / Keep / Rollback

### 목표

이번 실험을 공식적으로 닫는다.

### keep 조건

- BTC apply 후 악화가 없다
- blocked pressure 또는 관련 alert가 완화된다
- health가 추가 악화되지 않는다

### rollback 조건

- alert pressure 증가
- apply 후 adverse signal 악화
- 기대한 완화 신호 전혀 없음

### 확장 보류 조건

- BTC는 유지 가능하지만
- XAU/NAS는 여전히 timing/identity 이슈가 더 커서 확장 금지

## 11. 지금 당장 해야 할 첫 액션

지금 당장 가장 자연스러운 첫 액션은 아래 한 줄이다.

```text
runtime를 조금 더 운영한 뒤 dry-run review를 다시 실행해서
p7_trace_row_count가 0을 벗어나는지 먼저 확인한다.
```

즉 지금은 재시작을 또 할 때가 아니라,
`V1 wait + review rerun`
을 할 때다.

## 12. 결론

이 로드맵의 핵심은 아래 한 줄이다.

```text
현재 메인축은 dry-run row 누적 확인 -> BTCUSD only apply -> delta review 순서로,
guarded size overlay를 아주 좁고 보수적으로 검증하는 것이다.
```
