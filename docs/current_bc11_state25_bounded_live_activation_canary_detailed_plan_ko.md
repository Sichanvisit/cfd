# BC11 State25 Bounded Live Activation Canary 상세 계획

## 1. 목적

이번 단계의 목적은 이미 준비된 `state25 weight/threshold bounded live` 인프라를 실제 운영에 올릴 수 있도록,

- fresh 후보 재표출을 확인하고
- 심볼/스테이지 범위를 아주 좁게 정한 뒤
- `weight bounded live -> threshold bounded live` 순서로 canary를 적용하고
- rollback / invalidation 기준을 붙여 짧게 운영하는 것

을 하나의 운영 절차로 고정하는 것이다.

즉 이번 단계는 새 판단 로직을 만드는 단계가 아니라,
이미 만든 `state25 bridge`와 `bounded live apply handler`를 실제 active candidate state에 안전하게 연결하는 단계다.

## 2. 현재 전제

이미 된 것:

- `state25_weight_patch_apply_handlers.py`
- `state25_threshold_patch_apply_handlers.py`
- `state25_context_bridge_bounded_live_readiness.py`
- `/detect -> /propose` weight/threshold review surface
- `continuation accuracy tracking`
- `execution diff logging`
- `wrong-side guard / continuation promotion` 코드 경로

아직 안 된 것:

- `active_candidate_state.json`의 실제 `bounded_live` 승격
- `weight bounded live` live canary
- `threshold bounded live` live canary
- `size` live rollout

## 3. 이번 단계에 포함하는 것

- fresh `state25 weight review` / `state25 threshold review` 후보 재표출 확인
- canary 대상 심볼 / stage / knob 선택 기준
- `active_candidate_state.json`을 `bounded_live`로 올리는 실제 apply 절차
- `READY / HOLD / BLOCKED` 판정에 따른 적용 / 대기 / 중단
- rollback / invalidation / partial degraded mode 기준
- canary 기간 중 관찰해야 할 KPI와 로그 필드

## 4. 이번 단계에서 하지 않는 것

- 새 context 축 추가
- 새 continuation 로직 추가
- `size bounded live` 실제 적용
- execution core 대규모 재설계
- 전 심볼 동시 전환

## 5. 핵심 원칙

### 5-1. weight 먼저, threshold 다음, size 마지막

- 첫 live canary는 `weight bounded live`
- `threshold bounded live`는 weight canary가 안정적으로 통과한 뒤
- `size`는 마지막

### 5-2. 전체 전환 금지

- 심볼 1개
- entry stage 1개
- 작은 cap
- 짧은 관찰 윈도우

로 시작한다.

### 5-3. fresh 후보 없으면 apply하지 않는다

`log_only review`가 예전에 한 번 뜬 적이 있다는 이유만으로 올리지 않는다.
반드시 현재 사이클 기준 fresh review 후보와 readiness artifact가 같이 있어야 한다.

## 6. fresh 후보 재표출 확인 기준

`bounded live` 전환 전에 아래가 동시에 만족해야 한다.

### 6-1. weight candidate

- `state25_context_bridge_weight_review_count > 0`
- latest runtime row에서 `state25_context_bridge_weight_requested_count > 0`
- cooldown suppress만 있는 상태가 아님
- review packet에 symbol / stage / reason / requested/effective가 같이 기록됨

### 6-2. threshold candidate

- `state25_context_bridge_threshold_review_count > 0`
- latest runtime row에서 `state25_context_bridge_threshold_requested_points > 0`
- `threshold_delta_direction = HARDEN`
- symbol별 delta 계약이 현재 canary 범위와 충돌하지 않음

### 6-3. 공통 freshness

- runtime row age가 허용 범위 이내
- detector latest snapshot이 stale 아님
- readiness artifact generated_at이 최신

## 7. 첫 canary 대상 선택 기준

첫 canary 심볼은 아래 순서로 고른다.

1. `continuation accuracy`가 가장 높은 심볼
2. `target symbol/stage sample_count`가 가장 많은 심볼
3. `guard_overblock_rate`가 가장 낮은 심볼
4. 최근 2주 성과가 가장 안정적인 심볼

판정은 심볼별로 하고, 전체 합산은 참고용만 쓴다.

### 최초 기본 후보

- 1순위: `NAS100`
- 2순위: `BTCUSD`
- 3순위: `XAUUSD`

단, 실제 KPI가 이 순서를 뒤집으면 canary 순서도 같이 바꾼다.

## 8. canary 범위

### 8-1. Weight bounded live canary

- 대상: 1개 symbol
- stage: `balanced` 우선
- knob: `weight`
- mode: `bounded_live`
- cap: 기존 log-only requested의 작은 부분만 적용
- 기간: 최소 최근 30 sample 또는 2~5 영업일 관찰

### 8-2. Threshold bounded live canary

Weight canary가 통과한 뒤에만 간다.

- 대상: 동일 symbol 우선
- stage: 동일 stage 우선
- knob: `threshold`
- mode: `bounded_live`
- 조건: symbol별 delta 계약이 명확하고, single-delta 충돌이 없음

## 9. activation 조건

### 9-1. Weight bounded live READY 조건

- `execution diff` 집계 가능
- `continuation correct_rate(20 bars) >= 65%`
- `target symbol/stage sample_count >= 30`
- 최근 `log_only` sample 누적 >= 100
- `wrong-side guard` helpful_rate가 안정 범위
- `promotion` KPI가 심하게 나쁘지 않음
- 최근 1주 시스템 안정성 이상 없음

### 9-2. Threshold bounded live READY 조건

- weight canary 결과가 최소 HOLD 이상
- symbol별 threshold delta 계약 정리 완료
- `requested/effective` 차이가 안정적
- 과민 harden 패턴 아님
- guard / promotion / threshold의 이중 반영 아님

## 10. READY / HOLD / BLOCKED 해석

### READY

- canary 진입 가능
- 아주 좁은 범위로 bounded live apply

### HOLD

- 아직 더 관찰
- apply 안 함
- blocker는 아니지만 sample / stability / usefulness가 충분하지 않음

### BLOCKED

- 현재 scope에서는 bounded live 금지
- 기준 수정 또는 데이터 추가가 먼저

## 11. activation blockers

### warning band

- unresolved_rate > 25%
- guard_overblock_rate > 15%
- promotion_false_rate > 20%
- degraded_mode_rate > 10%
- execution_diff_missing_rate > 5%

warning이면 기본 판정은 `HOLD` 쪽으로 내린다.

### block band

- unresolved_rate > 40%
- guard_overblock_rate > 25%
- promotion_false_rate > 30%
- stale / fallback rate > 20%
- execution_diff_logic_conflict_rate > 5%
- telemetry missing rate > 10%

block이면 `BLOCKED`다.

## 12. 적용 절차

### Step 1. 후보 확인

- latest runtime row
- detector latest snapshot
- propose latest snapshot
- readiness latest artifact

에서 동일 symbol 후보가 fresh하게 뜨는지 본다.

### Step 2. scope 확정

- symbol 1개
- stage 1개
- knob 1개

로 scope를 확정한다.

### Step 3. apply

- review packet 기준으로 `active_candidate_state.json` 승격
- `current_rollout_phase`
- `current_binding_mode`
- allowlist / entry stage / cap

를 bounded_live 범위로 갱신한다.

### Step 4. canary 관찰

- 1시간 batch KPI
- 일간 readiness
- live execution diff
- final action quality

를 본다.

### Step 5. 판정

- READY 유지: 기간 완료 후 다음 단계
- HOLD: 추가 관찰
- BLOCKED: rollback 또는 invalidation

## 13. rollback / invalidation

### rollback

성과가 나쁘므로 bounded_live를 되돌린다.

예:

- helpful_rate < 40%
- false promotion 급증
- wrong-side 감소 없음
- PnL 악화

### invalidation

평가 자체가 성립하지 않아 다시 측정한다.

예:

- sample too small
- unresolved too high
- telemetry missing
- schema drift
- bridge version changed mid-window

## 14. partial degraded mode

bounded live 관찰 중 일부 축만 정상인 경우:

- `degraded_mode_active`
- `degraded_components`
- `partial_context_active`

를 따로 기록한다.

이 값이 높으면 canary는 `HOLD` 또는 `BLOCKED`로 간다.

## 15. canary 기간 중 반드시 보는 필드

runtime row:

- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`
- `directional_continuation_accuracy_summary_v1`
- `state25_context_bridge_weight_requested_count`
- `state25_context_bridge_threshold_requested_points`

state25 / rollout:

- `current_rollout_phase`
- `current_binding_mode`
- symbol allowlist
- entry stage allowlist

artifact:

- `state25_context_bridge_bounded_live_readiness_latest.json`
- `ca2_kpi_latest.json`

## 16. 이번 단계의 완료 기준

아래를 만족하면 이번 단계는 완료로 본다.

1. fresh weight 후보가 실제로 다시 표출됨
2. symbol/stage scope가 문서 기준으로 확정됨
3. weight bounded live canary가 실제 active candidate state에 적용됨
4. rollback / invalidation / degraded mode 로그가 정상 수집됨
5. 그 결과로 threshold canary 진입 가능/보류/차단이 판정됨

## 17. 결론

이번 단계는 “state25 bounded live를 언젠가 켠다”가 아니라,

- 어떤 fresh 후보가 보일 때
- 어떤 심볼 / stage 범위로
- 어떤 순서로
- 어떤 blocker / rollback 규칙 아래

실제로 bounded live canary를 시작할지 고정하는 단계다.

즉 BC11의 핵심은
`review 후보 -> active candidate bounded_live 승격 -> canary 관찰 -> rollback/확장 판정`
을 운영 절차로 닫는 것이다.
