# CA2 Guard / Promotion / Bounded Live Validation 상세 계획

## 1. 목적

이 문서는 새 규칙을 더 붙이기 위한 설계 문서가 아니다.

이 문서의 목적은 이미 연결된 아래 축이 실제로 맞게 작동하는지 숫자로 검증하고,
그 결과를 기준으로 `weight bounded live -> threshold bounded live`를 안전하게 올릴 준비를 마감하는 것이다.

- `continuation accuracy tracking`
- `execution diff logging`
- `wrong-side guard`
- `continuation promotion`
- `state25 weight bounded live`
- `state25 threshold bounded live`

즉 CA2는 설계 확장 문서가 아니라
**운영 검증과 전환 판정 문서**다.

---

## 2. 현재 진단

현재 시스템은 이미 아래까지 연결돼 있다.

- 차트 재료 수집
- HTF / previous box / context conflict 조립
- continuation 후보 생성
- `/detect -> /propose` surface
- chart overlay
- execution guard / promotion 코드 경로
- state25 bridge log-only
- bounded live apply handler / readiness gate

하지만 아직 아래는 숫자로 닫히지 않았다.

1. `execution_diff_*`가 live row와 trace에 안정적으로 계속 쌓이는지
2. `directional_continuation_accuracy_*`가 10/20/30봉 기준으로 실제 resolved sample을 만들기 시작하는지
3. `wrong-side guard`가 실제로 반대 방향 진입을 줄였는지
4. `continuation promotion`이 실제로 가치 있는 승격인지
5. `weight bounded live`를 언제 canary로 올릴지
6. `threshold bounded live`를 언제 canary로 올릴지

즉 지금 병목은 새 재료 부족이 아니라
**이미 만든 연결이 실제 행동과 성과를 바꾸는지 증명하는 것**이다.

---

## 3. 이번 단계의 범위

### 포함

- accuracy tracker live 관찰
- execution diff live 관찰
- guard KPI 정의 및 집계
- promotion KPI 정의 및 집계
- bounded live activation 조건 정의
- bounded live rollback / invalidation 조건 정의
- symbol/stage 단위 canary 순서 정의

### 제외

- 새 차트 재료 추가
- 새 context 축 추가
- size bounded live rollout
- execution core 대규모 재설계

핵심 규율:

지금은 검증 단계다.
새 규칙을 더 붙여서 KPI 해석이 흔들리게 만들지 않는다.

---

## 4. 핵심 질문

이번 단계에서 답해야 하는 질문은 아래 여섯 개다.

1. continuation이 `UP / DOWN`을 실제로 맞게 읽고 있는가
2. 기존 `SELL / BUY`가 continuation과 충돌할 때 guard가 실제로 작동하는가
3. guard가 작동한 장면은 hindsight 기준으로 막는 게 맞았는가
4. promotion이 실제로 `BUY / SELL` 승격을 만들고 있는가
5. promotion 장면은 일반 진입보다 성과가 좋은가
6. 위 다섯 개가 일정 기준을 넘으면 `weight bounded live`, 그다음 `threshold bounded live`를 켤 수 있는가

---

## 5. 관찰 대상 필드

### 5-1. continuation accuracy

- `directional_continuation_accuracy_summary_v1`
- `directional_continuation_accuracy_horizon_bars`
- `directional_continuation_accuracy_sample_count`
- `directional_continuation_accuracy_measured_count`
- `directional_continuation_accuracy_correct_rate`
- `directional_continuation_accuracy_false_alarm_rate`
- `directional_continuation_accuracy_unresolved_rate`
- `directional_continuation_accuracy_last_state`
- `directional_continuation_accuracy_last_candidate_key`

### 5-2. execution diff

- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`
- `execution_diff_changed`
- `execution_diff_guard_applied`
- `execution_diff_promotion_active`
- `execution_diff_reason_keys`
- `execution_diff_logic_conflict`
- `execution_diff_logic_conflict_type`
- `promotion_candidate_present`
- `promotion_triggered`
- `promotion_suppressed_reason`

### 5-3. state25 bridge / bounded live readiness

- `state25_context_bridge_stage`
- `state25_context_bridge_translator_state`
- `state25_context_bridge_weight_requested_count`
- `state25_context_bridge_weight_effective_count`
- `state25_context_bridge_threshold_requested_points`
- `state25_context_bridge_threshold_effective_points`
- `state25_context_bridge_guard_active`

### 5-4. degraded / fallback

- `degraded_mode_active`
- `degraded_components`
- `partial_context_active`
- `degraded_mode_rate`
- `partial_context_rate`

---

## 6. KPI 집계 주기

### 6-1. continuation accuracy

- 집계 주기: `light_cycle`
- 기대 주기: `3~5분`
- 용도:
  - pending / resolved 상태 감시
  - tracker가 실제로 샘플을 쌓는지 확인

운영 보강:

- `light_cycle accuracy`
  - 감시용
- `operational accuracy snapshot`
  - 1시간 또는 일간 판단용

즉 실시간 수치는 감시용이고,
bounded live 전환 판단은 더 느린 snapshot을 기준으로 한다.

### 6-2. guard / promotion KPI

- 집계 주기: `1시간 batch`
- 용도:
  - 진입 시도 빈도 대비 운영자가 읽기 좋은 리듬
  - rolling 최근 50건과 병행해 해석

### 6-3. bounded live readiness

- 집계 주기: `하루 1번`
- 권장 시점: 일간 마감 이후
- 용도:
  - 급한 전환을 막고 일간 누적 KPI로 판정

### 6-4. 집계 결과 저장

- `data/analysis/shadow_auto/ca2_kpi_latest.json`
- `data/analysis/shadow_auto/ca2_kpi_latest.md`

이 artifact는 아래 용도로 쓴다.

- orchestrator / master board 요약
- bounded live readiness 판단 근거
- 일간 운영 보고 요약

---

## 7. KPI 정의

### 7-1. continuation accuracy KPI

기본 원칙:

- `primary = 심볼별 집계`
- `secondary = 전체 합산`

즉 전체 50건은 참고용이고,
실제 bounded live 전환 판단은 심볼별 결과를 우선한다.

측정 단위:

- symbol별
- direction별 (`UP`, `DOWN`)
- horizon별 (`10`, `20`, `30`)

핵심 지표:

- `sample_count`
- `measured_count`
- `correct_rate`
- `false_alarm_rate`
- `unresolved_rate`
- `up_correct_rate`
- `down_correct_rate`
- `direction_bias_gap`
- `early_useful_rate`  (후속 보강 지표)
- `late_useful_rate`  (후속 보강 지표)

보조 규칙:

- 심볼별 최근 50건을 우선 본다.
- 50건이 안 되면 최근 2주 범위 안에서 집계한다.
- 심볼별 sample이 `30건 미만`이면 `표본 부족`으로 본다.
- `표본 부족` 심볼은 bounded live 전환 후보에서 제외한다.

운영 기준:

- `20봉 기준 correct_rate >= 65%`
  - 안정적
- `20봉 기준 correct_rate 55~65%`
  - 계속 관찰
- `20봉 기준 correct_rate < 55%`
  - continuation 기준 재검토

운영 해석:

- 방향 정확도와 운영 유용성은 분리해서 본다.
- 20봉 뒤에 맞더라도 너무 늦게 맞은 케이스는 `late_useful`로 별도 관리한다.

### 7-2. wrong-side guard KPI

기본 원칙:

- `primary = 심볼별 집계`
- `secondary = 전체 합산`

집계 단위:

- 최근 50건 진입 시도
- symbol별
- side별

핵심 지표:

- `guard_trigger_count`
- `guard_changed_action_count`
- `guard_helpful_count`
- `guard_missed_count`
- `guard_overblock_count`
- `guard_overblock_rate`
- `guard_helpful_rate_by_side`
- `guard_overblock_rate_by_side`

정의:

- `helpful`
  - guard가 막은 action이 hindsight 기준으로 실제로 나쁜 진입이었음
- `missed`
  - guard가 막지 않았지만 hindsight 기준으로 막았어야 했음
- `overblock`
  - guard가 막았지만 hindsight 기준으로 원래 진입이 맞았음

해석 기준:

- `guard_trigger_count = 0`
  - 장면이 없었거나 조건이 너무 빡빡함
- `guard_trigger_count 1~5`
  - 보수적으로 정상
- `guard_trigger_count >= 10`
  - guard가 과민할 가능성

검증 기준:

- hindsight 기준 `guard_helpful_rate >= 70%`
  - 검증 통과
- `guard_helpful_rate < 50%`
  - 기준 재검토

추가 해석:

- `guard_overblock_rate`가 높으면 helpful rate가 괜찮아 보여도 과민 차단일 수 있다.
- bounded live 전환 전에는 helpful만이 아니라 overblock을 같이 본다.
- side별 비대칭도 함께 본다.

### 7-3. continuation promotion KPI

기본 원칙:

- `primary = 심볼별 집계`
- `secondary = 전체 합산`

집계 단위:

- 최근 50건
- symbol별
- stage별

핵심 지표:

- `promotion_trigger_count`
- `promotion_changed_action_count`
- `promotion_win_rate`
- `promotion_false_rate`
- `promotion_vs_baseline_delta`
- `promotion_entry_change_rate`
- `promotion_avg_r`  (가능할 때)
- `promotion_mfe_capture`  (가능할 때)
- `promotion_vs_baseline_r_delta`  (가능할 때)

해석 기준:

- `promotion_trigger_count = 0`
  - 장면이 없었거나 승격 조건이 너무 높음
- `promotion_trigger_count 1~3`
  - 보수적으로 정상
- `promotion_trigger_count >= 10`
  - 승격 과민 가능성

검증 기준:

- `promotion_win_rate >= 60%`
  - 가치 있음
- `promotion_win_rate < 40%`
  - 기준 재검토

추가 해석:

- 승률만 높고 수익 품질이 약할 수 있으므로
  가능하면 `R` 또는 `baseline 대비 수익 차이`를 같이 본다.
- promotion은 절대값 KPI뿐 아니라 baseline-relative KPI로도 평가한다.
- 진입 수를 과하게 늘리면 승격은 가치가 낮다고 본다.

---

## 8. execution diff 해석 규칙

execution diff는 아래 순서로 읽는다.

1. `original_action_side`
   - 원래 기본 엔진이 하려던 행동
2. `guarded_action_side`
   - wrong-side guard 이후 행동
3. `promoted_action_side`
   - continuation promotion 이후 행동
4. `final_action_side`
   - 실제 최종 행동

추가 필드:

- `promotion_candidate_present`
- `promotion_triggered`
- `promotion_suppressed_reason`
- `execution_diff_logic_conflict`
- `execution_diff_logic_conflict_type`

예시 해석:

- `SELL -> SKIP -> null -> SKIP`
  - 반대 방향 진입을 막음
- `SELL -> SKIP -> BUY -> BUY`
  - guard가 막고 promotion이 반대편으로 승격
- `BUY -> BUY -> null -> BUY`
  - 기존 판단 유지

중요 원칙:

- execution diff는 결과 요약이 아니라 `행동 변화 사슬`이다.
- 반드시 `action_change_reason_keys`를 같이 남긴다.
- execution diff는 실행층용 `decision ledger`로 본다.

### 논리 충돌 케이스

아래 케이스는 별도 conflict로 잡는다.

1. guard가 `SKIP`으로 막았는데 promotion이 원래 방향과 같은 action을 밀 때
2. guard는 통과했는데 promotion이 guard 판단과 정면 충돌하는 반대 방향을 밀 때

이 경우:

- `execution_diff_logic_conflict = true`
- `execution_diff_logic_conflict_type`에 유형 기록
- 최종 행동은 guard 우선으로 보수적으로 처리
- conflict 비율이 높으면 guard/promotion 기준을 재검토한다.

---

## 9. bounded live 전환 조건

### 9-0. 운영 판정 상태

- `READY`
  - canary 전환 가능
- `HOLD`
  - 관찰은 유의미하지만 아직 더 데이터가 필요
- `BLOCKED`
  - activation blocker 또는 논리 충돌 때문에 전환 금지

즉 전환 판단은 단순 pass/fail이 아니라
`READY / HOLD / BLOCKED` 세 단계로 본다.

### 9-1. weight bounded live 전환 조건

아래 조건을 모두 충족해야 한다.

1. `execution diff`가 live에서 안정적으로 쌓임
2. guard / promotion KPI가 최소 50건 기준으로 집계 가능
3. continuation accuracy `20봉 기준 65%+`
4. 최근 log-only sample이 최소 100건
5. 최근 1주 시스템 안정성 이상 없음
6. target symbol/stage sample이 최소 30건 이상
7. baseline 대비 `wrong-side 감소` 또는 `promotion 개선`이 확인됨

첫 전환 범위:

- `1 symbol`
- `1 entry_stage`
- `weight only`
- 작은 cap

rollback 조건:

- 첫 50건에서 helpful rate < 40%
- false promotion 급증
- wrong-side 감소 없음
- PnL 악화

### 9-2. threshold bounded live 전환 조건

weight bounded live가 먼저 안정적이어야 한다.

추가 조건:

1. `threshold requested/effective` 차이가 안정적
2. symbol별 delta 계약이 정리됨
3. threshold harden이 과민하지 않음
4. guard / promotion과 이중 반영되지 않음
5. 운영 판정이 `READY`

첫 전환 범위:

- `1 symbol`
- `1 entry_stage`
- `threshold harden only`
- 작은 cap

rollback 조건:

- skip만 늘고 성과 개선 없음
- false alarm 급증
- symbol별 threshold drift 과도

### 9-3. activation blockers

아래 중 하나라도 block band에 걸리면 bounded live를 켜지 않는다.

block band:

- `unresolved_rate > 40%`
- `guard_overblock_rate > 25%`
- `promotion_false_rate > 30%`
- `execution diff missing rate > 10%`
- `stale / fallback rate > 20%`
- `execution_diff_logic_conflict_rate > 5%`

warning band:

- `unresolved_rate > 25%`
- `guard_overblock_rate > 15%`
- `promotion_false_rate > 20%`
- `execution diff missing rate > 5%`
- `stale / fallback rate > 10%`
- `execution_diff_logic_conflict_rate > 2%`

운영 해석:

- warning band에 걸리면 `HOLD`
- block band에 걸리면 `BLOCKED`

### 9-4. size

size는 마지막이다.

조건:

- weight bounded live 안정
- threshold bounded live 안정
- promotion/guard KPI 안정

그 전에는 `log_only` 유지가 맞다.

---

## 10. 장애 / fallback 원칙

체인 어디가 끊겨도 기존 매매는 돌아가야 한다.

시나리오:

- HTF stale
  - 해당 축 보정 0
- previous_box unavailable
  - 해당 축 보정 skip
- context_state_builder 실패
  - bridge 전체 no-op
- detector surface 실패
  - `/propose`는 기존 축 유지
- apply handler 오류
  - 즉시 `log_only` 복귀

partial degraded mode:

- full no-op만 있는 것이 아니라 일부 축만 살아 있는 degraded mode도 허용한다.
- 예:
  - HTF stale, previous_box fresh -> previous_box만 반영
  - previous_box unavailable, late_chase fresh -> late_chase만 반영
  - accuracy unresolved 많음, execution diff는 정상 -> execution diff는 계속 수집

권장 필드:

- `degraded_mode_active`
- `degraded_components`
- `partial_context_active`
- `degraded_mode_rate`
- `partial_context_rate`

핵심 원칙:

- 맥락 축은 있으면 더 좋은 것
- 없다고 매매 전체가 멈추면 안 됨
- degraded mode는 단순 예외 로그가 아니라 readiness 판단 지표로도 쓴다.

---

## 11. rollback과 invalidation

rollback:

- 성과가 나빴으니 되돌리는 경우

invalidation:

- 평가 자체가 성립하지 않아서 다시 측정해야 하는 경우

invalidation 예시:

- sample too small
- unresolved rate too high
- telemetry missing
- detector / promotion schema drift
- `bridge version changed mid-window`

즉 rollback과 invalidation은 별도로 본다.

---

## 12. 운영 판정표

### 12-1. KPI 판정표

| KPI | READY | HOLD | BLOCKED |
| --- | --- | --- | --- |
| continuation correct rate (20 bars) | `>= 65%` | `55~65%` | `< 55%` |
| guard helpful rate | `>= 70%` | `50~70%` | `< 50%` |
| guard overblock rate | `<= 15%` | `15~25%` | `> 25%` |
| promotion win rate | `>= 60%` | `40~60%` | `< 40%` |
| promotion false rate | `<= 20%` | `20~30%` | `> 30%` |
| unresolved rate | `<= 25%` | `25~40%` | `> 40%` |
| execution diff missing rate | `<= 5%` | `5~10%` | `> 10%` |
| logic conflict rate | `<= 2%` | `2~5%` | `> 5%` |

### 12-2. canary scope 표

| 순서 | symbol | stage | knob | cap 방향 | 목표 표본 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | NAS100 | balanced/probe 계열 | weight | 작은 cap | 30+ | observe |
| 2 | BTCUSD | balanced/probe 계열 | weight | 작은 cap | 30+ | observe |
| 3 | XAUUSD | balanced/probe 계열 | weight | 작은 cap | 30+ | observe |
| 4 | 선행 통과 symbol 1개 | stage 1개 | threshold | harden only | 30+ | blocked until weight pass |

이 표의 실제 상태는 KPI 결과에 따라 `READY / HOLD / BLOCKED`로 바뀐다.

---

## 13. 이번 단계 완료 조건

아래 다섯 개가 확인되면 CA2 단계는 닫는다.

1. `execution_diff_*` live row / trace 확인
2. `continuation accuracy` 10/20/30봉 resolved sample 생성 확인
3. wrong-side guard KPI 1차 집계 완료
4. promotion KPI 1차 집계 완료
5. `weight bounded live` canary 전환 조건표 확정

그 다음 단계는:

- `weight bounded live canary`
- 그 다음 `threshold bounded live canary`
