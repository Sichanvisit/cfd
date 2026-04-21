# Teacher-Label State25 Step 9-E5 Execution Handoff Gate

## 목적

이 문서는 `Step 9-E5`에서
현재 `teacher-state 25` 라벨 품질과 pilot baseline 결과가
실제 execution 반영 판단까지 갈 수 있는지 판정하는 gate 기준서다.

핵심은 다음 셋을 한 번에 묶는 것이다.

- `E2 full labeling QA`
- `E3 pilot baseline`
- `E4 top confusion pair tuning`

즉 이 문서는
`지금 execution에 붙여도 되나?`
를 정성 의견이 아니라 정량 gate로 묻는 문서다.

## 입력

Execution handoff gate는 아래 산출물을 입력으로 받는다.

- asset calibration report
- full labeling QA report
- pilot baseline report
- confusion tuning report

실행 기준 스크립트:

- [teacher_pattern_execution_handoff_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_execution_handoff_report.py)

핵심 서비스:

- [teacher_pattern_execution_handoff.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_execution_handoff.py)

## 판정 상태

출력 상태는 아래 셋 중 하나다.

- `READY`
- `READY_WITH_WARNINGS`
- `NOT_READY`

해석 원칙:

- blocker가 하나라도 있으면 `NOT_READY`
- blocker는 없고 warning만 있으면 `READY_WITH_WARNINGS`
- blocker와 warning이 모두 없으면 `READY`

## blocker 기준

아래는 execution handoff를 막는 blocker다.

### 1. labeled seed 부족

- `labeled_rows < 10,000`
- 또는 full QA readiness가 false

이 경우 해석:

- 현재 라벨 분포가 execution handoff에 쓰기엔 아직 작다
- pilot baseline은 가능해도 live handoff는 이르다

### 2. primary coverage 부족

- `covered_primary_count < 8`

이 경우 해석:

- 25개 전체를 다 맞추겠다는 뜻은 아니지만
- execution에 반영하려면 최소한 몇 개 group을 넘어서는 coverage가 필요하다

### 3. supported pattern class 부족

- `supported_pattern_count < 6`

이 경우 해석:

- baseline이 사실상 일부 패턴만 배우고 있는 상태라
- 실행 반영 판단에는 아직 편향이 크다

### 4. pilot baseline readiness 부족

- `baseline_ready = false`
- group task skipped
- pattern task skipped
- group test macro F1 < `0.65`
- pattern test macro F1 < `0.60`

이 경우 해석:

- 현재 라벨/특징 조합으로도 최소한의 구분 성능이 나와야 한다
- 여기서 무너지면 execution handoff로 넘기지 않는다

### 5. high severity confusion 미해결

- confusion tuning report의 high severity candidate 존재

이 경우 해석:

- 지금 실제로 많이 헷갈리는 쌍을 아직 못 정리한 상태다
- 이 상태에선 execution 반영보다 E4 반복이 우선이다

## warning 기준

아래는 execution을 즉시 막지는 않지만
운영/검토에서 반드시 보고 가야 하는 warning이다.

- overall/symbol group skew
- rare pattern scarcity
- medium severity confusion 존재
- watchlist pair 미관측
- asset calibration warning

해석 원칙:

- skew는 시장 현실일 수 있으므로 바로 blocker로 쓰지 않는다
- rare pattern 부족도 장기 누적 문제로 보고 warning으로 둔다
- watchlist pair가 아직 안 잡힌 것도 즉시 blocker는 아니다

## 현재 단계의 해석 원칙

현재 프로젝트는
`희귀 패턴을 억지로 맞추는 단계`가 아니라
`계속 누적되는 실전 데이터에서 skew를 인정한 채 관리하는 단계`다.

그래서 E5는 아래를 구분한다.

- `지금 바로 execution에 붙여도 되는가`
- `아직은 pilot/observation으로 두어야 하는가`

즉 group skew만으로 자동 실패시키지 않는다.
대신 아래 둘을 더 중요하게 본다.

- coverage
- unresolved high confusion

## 권장 후속 액션

E5 결과에 따라 후속 액션은 아래로 분기한다.

### NOT_READY

- labeled row 더 누적
- bounded/richer backfill 확대
- E4 confusion tuning 재반복
- E3 baseline 재실행

### READY_WITH_WARNINGS

- narrow scope shadow rollout
- watchlist pair 관측 유지
- medium confusion 추적 유지

### READY

- execution bias의 좁은 반영 검토
- live monitor와 rollback 조건을 같이 붙여 rollout

## 현재 단계에서 기대되는 실제 결과

현 seed 상태에선 E5가 대체로 `NOT_READY`를 내는 것이 자연스럽다.

주요 이유:

- 아직 `10K` labeled seed가 아님
- primary coverage가 `25개 전체` 대비 좁음
- supported pattern class가 제한적임
- high confusion(`A->D`)이 아직 남아 있음

즉 E5는 실패 문서가 아니라,
`왜 아직 execution handoff가 아닌지`를 명확히 고정하는 문서다.
