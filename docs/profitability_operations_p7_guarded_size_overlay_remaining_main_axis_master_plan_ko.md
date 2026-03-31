# Profitability / Operations P7 Guarded Size Overlay Remaining Main Axis Master Plan

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 프로젝트에서 남아 있는 `메인축`을
한 장으로 다시 고정하기 위한 문서다.

단, 아래 조건이 성립할 때만 이 문서를 current main axis로 본다.

- 차트 표기
- 자동 진입
- 기다림 / 홀드
- 청산

의 제품 acceptance가 사용자가 보기에 충분히 닫혀 있을 때

만약 위 acceptance가 아직 닫히지 않았다면,
우선순위는 아래 문서의 `product acceptance reorientation`으로 되돌린다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)

핵심 질문은 아래와 같다.

`지금 남은 가장 중요한 작업은 무엇이고, 이미 된 것과 아직 남은 것, 그리고 아직 하면 안 되는 것은 무엇인가?`

이 문서는 새 기능 제안 문서가 아니다.
현재 `P7 guarded size overlay 검증`을
실제 실행 가능한 마스터 플랜으로 다시 정리하는 문서다.

## 2. 왜 지금 이 문서가 필요한가

현재 프로젝트에는 여러 축이 동시에 존재한다.

- 옛 refinement 트랙 `R0~R4`
- scene/display 보강 트랙 `S0~S6`
- actual entry forensic `R0-B`
- decision log coverage gap `C0~C6`
- profitability / operations 트랙 `P0~P7`

이 중 지금 실제 메인축은 하나다.

```text
P7 guarded size overlay verification
```

즉 지금은

- painter를 더 다듬는 단계
- semantic rule을 더 늘리는 단계
- auto-adaptation을 여는 단계

가 아니라,
이미 `P7`이 허용한 유일한 guarded apply 후보인
`size overlay`를 운영적으로 검증하는 단계다.

## 3. 현재 메인축의 공식 이름

현재 메인축의 공식 이름은 아래로 둔다.

```text
P7 guarded size overlay verification
```

기준 문서:

- [profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md)
- [profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md)

## 4. 현재 상태: 된 것

아래는 이미 끝난 것이다.

### 4-1. 구현 완료

아래 코드/설정/trace surface는 이미 구현되어 있다.

- guarded size overlay materialization
- runtime resolver
- entry hook
- hot/detail logging surface
- env/config surface
- dry-run review script

대표 owner:

- [p7_guarded_size_overlay.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p7_guarded_size_overlay.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)
- [storage_compaction.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [profitability_operations_p7_guarded_size_overlay_materialize.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p7_guarded_size_overlay_materialize.py)
- [profitability_operations_p7_guarded_size_overlay_dry_run_review.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p7_guarded_size_overlay_dry_run_review.py)

### 4-2. dry-run 전환 완료

현재 `.env` 기준으로 아래가 적용되어 있다.

- `ENABLE_P7_GUARDED_SIZE_OVERLAY=true`
- `P7_GUARDED_SIZE_OVERLAY_MODE=dry_run`
- `P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH=...profitability_operations_p7_guarded_size_overlay_latest.json`
- `P7_GUARDED_SIZE_OVERLAY_MAX_STEP=0.10`

즉 현재는 live lot은 바꾸지 않고,
trace만 누적하는 dry-run 단계다.

### 4-3. 재시작 완료

runtime 재시작도 이미 완료되었다.
즉 현재 프로세스는 새 env를 읽는 상태다.

### 4-4. schema 준비 완료

현재 [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
헤더에는 이미 `p7_guarded_size_overlay_*` 필드가 존재한다.

즉 더 이상 “스키마가 없어서 안 찍힌다”는 단계는 아니다.

### 4-5. dry-run trace 누적 시작

최신 review 기준:

- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_dry_run_latest.json)

현재 값:

- `p7_trace_row_count = 8`
- `review_state = dry_run_rows_accumulating`

즉 V1은 사실상 통과했다.

## 5. 현재 상태: 아직 남은 것

이제 실제로 남은 것은 아래다.

### 5-1. BTCUSD dry-run trace 확보

현재 dry-run trace 분포는 아래다.

- `XAUUSD = 6`
- `NAS100 = 2`
- `BTCUSD = 0`

즉 첫 apply 후보인 `BTCUSD`가
실제 dry-run 누적에서도 관측되는지 확인해야 한다.

### 5-2. BTC-only apply 준비

dry-run에서 BTC가 잡히면
아래처럼 가장 좁은 범위로만 apply를 연다.

- `P7_GUARDED_SIZE_OVERLAY_MODE=apply`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST=BTCUSD`

즉 전체 symbol apply가 아니라,
가장 작은 검증 범위로만 연다.

### 5-3. BTC-only apply 실행

실제 적용 이후 row에서 아래가 확인돼야 한다.

- `p7_size_overlay_mode = apply`
- `p7_size_overlay_applied = true`
- `p7_size_overlay_effective_multiplier < 1.0`
- `symbol = BTCUSD`

### 5-4. P4~P7 rerun / delta review

apply 이후 아래를 다시 본다.

- P4 compare
- P5 casebook
- P6 health
- P7 guarded proposal

즉 size만 줄였을 때 실제로 pressure가 줄었는지 본다.

### 5-5. keep / rollback / 확장보류 close-out

실험을 마지막에 공식적으로 닫아야 한다.

가능한 결론:

- keep
- rollback
- keep but no expansion

## 6. 현재 상태: 아직 하면 안 되는 것

아래는 지금 건드리면 안 된다.

### 6-1. XAUUSD / NAS100 apply

이유:

- 아직 BTC조차 검증이 끝나지 않았다.
- XAU/NAS는 pressure와 해석 리스크가 더 크다.

### 6-2. XAU timing rule 수정

이유:

- 현재 `review_only`다.
- 아직 guarded apply 후보로 승격된 상태가 아니다.

### 6-3. legacy balanced family live 조정

이유:

- 현재 `identity_first_gate`다.
- 즉 `no_go` 상태다.

### 6-4. auto-adaptation / self-tuning

이유:

- 지금은 controlled experiment 단계다.
- 자동 적응을 열기엔 아직 근거가 부족하다.

## 7. 단계별 실행 로드맵

현재 메인축의 실제 순서는 아래다.

```text
M0. current state freeze
-> M1. BTC dry-run trace 관찰
-> M2. BTC-only apply 준비
-> M3. BTC-only apply 실행
-> M4. P4~P7 rerun + delta review
-> M5. keep / rollback / no-expansion close-out
```

### M0. current state freeze

이미 사실상 완료 상태다.

기준 문서:

- [profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md)

### M1. BTC dry-run trace 관찰

현재 active step이다.

해야 할 일:

1. runtime를 그대로 조금 더 운영
2. dry-run review 재실행
3. `BTCUSD`가 symbol summary에 잡히는지 확인

accept 기준:

- `BTCUSD trace >= 1`

권장 관찰 기준:

- 짧은 재확인 주기: `20~30분`
- 전환 판단 기준: `60~90분` 또는 `BTCUSD trace >= 3`

### M2. BTC-only apply 준비

해야 할 일:

1. `.env`에서 mode를 `apply`로 변경
2. allowlist를 `BTCUSD`로만 제한
3. `max_step=0.10` cap 유지

### M3. BTC-only apply 실행

해야 할 일:

1. runtime 재시작
2. 신규 entry row 누적
3. apply trace 확인

확인 필드:

- `p7_size_overlay_mode`
- `p7_size_overlay_applied`
- `p7_size_overlay_effective_multiplier`
- `p7_size_overlay_gate_reason`

### M4. P4~P7 rerun + delta review

해야 할 일:

1. P4 compare rerun
2. P5 casebook rerun
3. P6 health rerun
4. P7 proposal rerun

핵심 질문:

- BTC blocked pressure가 줄었는가
- alert pressure가 악화되지 않았는가
- P6 health가 더 나빠지지 않았는가
- P7 proposal 구조가 무너지지 않았는가

### M5. keep / rollback / no-expansion close-out

가능한 결론은 아래 셋 중 하나다.

- `keep`
- `rollback`
- `keep but no expansion`

## 8. 이걸 다 하면 어떻게 되나

이 메인축을 다 끝내면 가장 먼저 생기는 것은
`첫 guarded live policy 검증 루프`다.

즉 지금까지는 아래 수준이었다.

- 관측
- 해석
- alert
- compare
- casebook
- health
- guarded proposal

하지만 이번 메인축까지 닫으면
거기서 한 단계 더 나아가 아래가 가능해진다.

```text
proposal
-> 실제 live apply
-> before/after delta review
-> keep / rollback 판단
```

이건 매우 중요하다.
왜냐하면 이때부터는
“좋아 보이는 제안”
이 아니라
“실제로 붙여보니 유지할 가치가 있는 정책”
를 말할 수 있게 되기 때문이다.

### 성공했을 때

- `size overlay`는 실사용 가능한 운영 정책으로 승격된다.
- 이후 NAS/XAU 확장을 검토할 수 있다.
- 그 다음에야 예전 backlog나 P7 후속 실험을 더 자신 있게 고를 수 있다.

### 실패했을 때

- 이것도 가치가 크다.
- `size만 줄여서는 안 풀리는 문제`라는 게 확인된다.
- 그러면 다음 우선순위를 XAU timing review나 legacy identity restore 쪽으로 더 선명하게 옮길 수 있다.

즉 성공해도 의미가 있고, 실패해도 의미가 있다.

## 9. 현재 가장 중요한 한 줄

이 문서의 핵심은 아래 한 줄이다.

```text
지금 남은 메인축은 BTCUSD만을 대상으로 한 guarded size overlay 검증이며,
이걸 닫아야 비로소 첫 live policy 실험 루프가 완성된다.
```

## 10. 다음 기준 문서

이번 마스터 플랜과 함께 직접 참조할 기준 문서는 아래다.

- [profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_detailed_reference_ko.md)
- [profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_verification_execution_roadmap_ko.md)
- [profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_guarded_size_overlay_experiment_roadmap_ko.md)
