# CA2 Guard / Promotion / Bounded Live Validation 실행 로드맵

## 1. 현재 위치

지금은 설계 확장 단계보다
`관찰 -> 계측 -> 검증 -> 좁은 rollout`
단계다.

즉 이번 로드맵은 새 축을 더 붙이는 계획이 아니라,
이미 붙은 축을 숫자로 확인하고 bounded live 전환 순서를 고정하는 로드맵이다.

---

## 2. 단계 개요

### CA2-A. live 필드 축적 확인

목표:

- `execution_diff_*`가 live row와 trace에 실제로 쌓이는지 확인
- `directional_continuation_accuracy_*`가 runtime row에 실제로 surface되는지 확인

확인 위치:

- `data/runtime_status.detail.json`
- `ai_entry_traces`
- `directional_continuation_accuracy_tracker_latest.json`

완료 기준:

- symbol row에 accuracy field가 보임
- entry trace에 execution diff field가 보임
- missing rate가 허용 범위 안에 있음

### CA2-B. continuation accuracy 관찰

목표:

- `10 / 20 / 30 bars` horizon에서 resolved sample이 생기기 시작하는지 확인

확인 지표:

- `pending_observation_count`
- `resolved_observation_count`
- `primary_measured_count`
- `primary_correct_rate`
- `direction_bias_gap`

완료 기준:

- resolved sample > 0
- symbol/direction별 summary 생성
- 심볼별 sample 부족 여부 표시 가능
- `early_useful_rate`, `late_useful_rate` 도입 여부 판단

### CA2-C. wrong-side guard KPI 집계

목표:

- guard가 실제로 반대 방향 진입을 얼마나 막는지 집계

입력:

- `execution_diff_guard_applied`
- `execution_diff_changed`
- hindsight 결과

핵심 지표:

- `guard_trigger_count`
- `guard_changed_action_count`
- `guard_helpful_rate`
- `guard_missed_count`
- `guard_overblock_rate`
- `guard_helpful_rate_by_side`
- `guard_overblock_rate_by_side`

완료 기준:

- 최근 50건 기준 guard KPI 표 생성
- 심볼별 KPI 표 생성
- 표본 부족 심볼 태깅
- `helpful / missed / overblock` 정의 고정

### CA2-D. continuation promotion KPI 집계

목표:

- promotion이 실제로 가치 있는 승격인지 집계

입력:

- `execution_diff_promotion_active`
- `execution_diff_promoted_action_side`
- hindsight / pnl

핵심 지표:

- `promotion_trigger_count`
- `promotion_changed_action_count`
- `promotion_win_rate`
- `promotion_false_rate`
- `promotion_candidate_present`
- `promotion_triggered`
- `promotion_suppressed_reason`
- `promotion_vs_baseline_delta`
- `promotion_entry_change_rate`

완료 기준:

- 최근 50건 기준 promotion KPI 표 생성
- 심볼별 KPI 표 생성
- baseline-relative delta 확인

### CA2-E. weight bounded live canary 조건 확정

목표:

- `weight bounded live`를 언제 어떤 범위로 켤지 확정

선행 조건:

- CA2-A ~ D 완료
- continuation accuracy 기준 통과
- guard / promotion KPI 기준 통과
- activation blocker 미해당
- target symbol/stage sample 30건 이상
- 운영 판정이 `READY`

첫 canary 범위:

- symbol 1개
- stage 1개
- 작은 cap
- weight only

완료 기준:

- activation 조건표 + rollback 조건표 확정

### CA2-F. threshold bounded live 조건 확정

목표:

- weight canary 이후 threshold bounded live의 조건을 확정

선행 조건:

- weight bounded live 안정
- threshold delta 계약 안정
- symbol별 delta drift 확인
- activation blocker 미해당
- 운영 판정이 `READY`

완료 기준:

- threshold harden only canary 조건표 확정

### CA2-G. size는 보류

원칙:

- size는 마지막
- 이 단계에서는 rollout하지 않음

---

## 3. 주차별 운영 순서

### Week 1

- CA2-A live 필드 축적 확인
- CA2-B accuracy pending/resolved 첫 샘플 확인
- execution diff가 실제로 쌓이는지 확인
- KPI batch artifact 형식 확정
- `ca2_kpi_latest.json`, `ca2_kpi_latest.md` 산출

산출물:

- 첫 runtime snapshot 점검
- 첫 accuracy artifact 점검

### Week 2

- CA2-C wrong-side guard KPI 집계
- CA2-D continuation promotion KPI 집계
- symbol별 / direction별 차이 확인
- logic conflict 집계
- overblock 집계

산출물:

- guard KPI 표
- promotion KPI 표

### Week 3

- CA2-E weight bounded live canary 조건 확정
- symbol/stage 범위 고정
- rollback 트리거 고정

산출물:

- weight canary activation packet

### Week 4

- weight canary 결과 점검
- threshold bounded live 조건 확정 준비

산출물:

- threshold canary readiness packet

---

## 4. 구현 우선순위

### 1순위

- accuracy / execution diff가 live에서 실제 누적되는지 확인
- KPI 집계 주기 구현
- symbol-first 집계 구조 구현

이유:

- 값이 실제로 쌓이지 않으면 KPI를 만들 수 없음

### 2순위

- guard KPI
- promotion KPI
- logic conflict
- overblock
- activation blocker
- baseline-relative KPI
- READY / HOLD / BLOCKED 판정

이유:

- 이 축이 execution 개선의 핵심 증거

### 3순위

- weight bounded live canary

이유:

- 가장 작은 live 개입

### 4순위

- threshold bounded live canary

이유:

- 행동을 더 크게 바꾸므로 weight 이후가 맞음

### 5순위

- size

이유:

- 가장 마지막 리스크 축

---

## 5. 관찰 체크리스트

### live row

- `directional_continuation_accuracy_horizon_bars`
- `directional_continuation_accuracy_sample_count`
- `directional_continuation_accuracy_measured_count`
- `directional_continuation_accuracy_correct_rate`
- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`

### top-level summary

- `directional_continuation_accuracy_summary_v1.pending_observation_count`
- `directional_continuation_accuracy_summary_v1.resolved_observation_count`
- `directional_continuation_accuracy_summary_v1.primary_correct_rate`

### trace

- `execution_diff_changed`
- `execution_diff_guard_applied`
- `execution_diff_promotion_active`
- `execution_diff_reason_keys`
- `execution_diff_logic_conflict`
- `execution_diff_logic_conflict_type`
- `promotion_candidate_present`
- `promotion_triggered`
- `promotion_suppressed_reason`

---

## 6. 운영 판정표

### 6-1. 전환 조건표

| 항목 | 기준 | READY 조건 |
| --- | --- | --- |
| continuation accuracy | 20봉 기준 | `correct_rate >= 65%` |
| guard helpful rate | 최근 50건 | `>= 70%` |
| promotion win rate | 최근 50건 | `>= 60%` |
| log-only sample | 최근 누적 | `>= 100건` |
| stability | 최근 1주 | 치명적 장애 없음 |
| target scope sample | symbol + stage | `>= 30건` |
| baseline relative delta | target scope | 개선 또는 최소 중립 |

### 6-2. activation blocker 표

| blocker | warning | block |
| --- | --- | --- |
| unresolved rate | `> 25%` | `> 40%` |
| guard overblock rate | `> 15%` | `> 25%` |
| promotion false rate | `> 20%` | `> 30%` |
| execution diff missing rate | `> 5%` | `> 10%` |
| logic conflict rate | `> 2%` | `> 5%` |
| stale / fallback rate | `> 10%` | `> 20%` |

운영 해석:

- warning이면 `HOLD`
- block이면 `BLOCKED`

### 6-3. rollback 조건표

| 항목 | rollback 조건 |
| --- | --- |
| weight bounded live | 첫 50건 helpful rate `< 40%` |
| threshold bounded live | skip 증가만 있고 성과 개선 없음 |
| promotion | false promotion 급증 |
| guard | helpful rate `< 50%` |
| system stability | 예외 / restart / bad loop 반복 |

### 6-4. invalidation 조건표

| 항목 | invalidation 조건 |
| --- | --- |
| sample size | target scope sample 부족 |
| unresolved | unresolved rate 과도 |
| telemetry | trace / summary 누락 |
| schema | detector / promotion schema drift |
| version | bridge version changed mid-window |

### 6-5. canary scope 표

| 순서 | symbol | stage | knob | 상태 | 목표 표본 |
| --- | --- | --- | --- | --- | --- |
| 1 | NAS100 | balanced/probe 계열 | weight | observe | 30+ |
| 2 | BTCUSD | balanced/probe 계열 | weight | observe | 30+ |
| 3 | XAUUSD | balanced/probe 계열 | weight | observe | 30+ |
| 4 | 선행 통과 symbol 1개 | stage 1개 | threshold | blocked until weight pass | 30+ |

---

## 7. 이번 로드맵 완료 조건

아래가 모두 준비되면 CA2 로드맵은 구현 단계에서 관찰 단계로 완전히 넘어간다.

1. accuracy resolved sample 생성
2. execution diff live trace 확인
3. guard KPI 표 생성
4. promotion KPI 표 생성
5. weight bounded live canary 조건 확정
6. threshold bounded live 조건 확정 초안 생성

그 뒤의 운영 모드는:

- 매일 로그 관찰
- 기준 충족 시 canary 전환
- 미충족 시 좁은 패치

운영 판정:

- `READY`
  - canary 진행
- `HOLD`
  - 더 관찰
- `BLOCKED`
  - 전환 금지 및 기준 재검토
