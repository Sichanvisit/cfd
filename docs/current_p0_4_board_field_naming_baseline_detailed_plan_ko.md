# Current P0-4 Board Field Naming Baseline Detailed Plan

## 목표

`P0-4`의 목표는 master board와 readiness/report 계층에서 같은 상태를 다른 이름으로 부르지 않게, board field 이름과 section 구조를 고정하는 것입니다.

이 단계는 `P1 readiness surface`로 들어가기 전에 공통 naming baseline을 잠그는 준비 작업입니다. 즉 로직을 크게 바꾸는 단계가 아니라, 앞으로 surface될 필드가 어디에 어떤 이름으로 들어갈지 먼저 정리하는 단계입니다.

---

## 왜 지금 필요한가

board가 이미 많은 정보를 갖고 있어도 이름이 흔들리면 이후 단계에서 다시 꼬입니다.

- 어떤 문서에서는 `blocking_reason`, 다른 곳에서는 `block_reason`처럼 부르면 안 됩니다.
- readiness를 한 곳에서는 summary에만 두고, 다른 곳에서는 section 없이 흩뿌리면 안 됩니다.
- confidence를 어떤 곳은 숫자, 어떤 곳은 `HIGH/MEDIUM/LOW`로 부르면 안 됩니다.
- `PA8`, `PA9`, `reverse`, `historical cost`가 서로 다른 naming 규칙을 쓰면 안 됩니다.

그래서 `P0-4`는 실제 로직을 고도화하기보다, 앞으로 무엇을 어떤 이름으로 보여줄지 먼저 고정하는 단계입니다.

---

## 이번 단계에서 고정할 것

### 1. section 이름

master board의 아래 section 이름을 canonical로 봅니다.

- `summary`
- `readiness_state`
- `system_state`
- `watch_state`
- `runtime_state`
- `pa_state`
- `approval_state`
- `health_state`
- `orchestrator_contract`
- `artifacts`

### 2. summary 대표 필드

아래 값은 summary에서 항상 같은 이름으로 surface합니다.

- `blocking_reason`
- `next_required_action`
- `pa8_closeout_readiness_status`
- `pa9_handoff_readiness_status`
- `reverse_readiness_status`
- `historical_cost_confidence_level`

### 3. readiness_state 대표 필드

- `pa8_closeout_readiness_status`
- `pa8_closeout_blocking_reason`
- `pa8_closeout_next_required_action`
- `pa9_handoff_readiness_status`
- `pa9_handoff_blocking_reason`
- `pa9_handoff_next_required_action`
- `reverse_readiness_status`
- `reverse_blocking_reason`
- `reverse_next_required_action`
- `historical_cost_confidence_level`
- `historical_cost_blocking_reason`
- `historical_cost_note`

### 4. confidence naming

confidence는 숫자가 아니라 아래 enum만 씁니다.

- `HIGH`
- `MEDIUM`
- `LOW`
- `LIMITED`

### 5. blocking reason naming

대표 blocking reason은 아래 canonical 값을 우선 사용합니다.

- `none`
- `system_phase_emergency`
- `system_phase_degraded`
- `dependency_degraded`
- `approved_apply_backlog`
- `approval_backlog_pending`
- `pa7_review_backlog`
- `pa8_live_window_pending`
- `pa8_closeout_blocked`
- `pa9_handoff_review_ready`
- `pa8_closeout_apply_pending_before_pa9`
- `historical_cost_limited`
- `reverse_wait_for_flat`
- `reverse_score_not_strong_enough`

---

## 이번 단계에서 실제로 하는 일

### 1. board field policy 파일 추가

파일:

- `backend/services/improvement_board_field_policy.py`

역할:

- canonical section names 정의
- canonical summary/readiness field 목록 정의
- confidence level 정의
- board blocking reason naming 정의
- readiness 파생 helper 제공
- baseline snapshot export

### 2. master board에 field policy 반영

파일:

- `backend/services/checkpoint_improvement_master_board.py`

역할:

- summary에 `field_policy_version` 추가
- `readiness_state` section 추가
- `pa8 / pa9 / reverse / historical cost` naming 통일
- markdown render도 같은 이름으로 출력

### 3. 테스트와 artifact로 baseline 고정

파일:

- `tests/unit/test_improvement_board_field_policy.py`
- `tests/unit/test_checkpoint_improvement_master_board.py`

artifact:

- `data/analysis/shadow_auto/improvement_board_field_baseline_latest.json`
- `data/analysis/shadow_auto/improvement_board_field_baseline_latest.md`

---

## 완료 조건

- master board가 `readiness_state` section을 가진다
- summary에서 readiness 관련 대표 필드가 mirror된다
- confidence naming이 `HIGH / MEDIUM / LOW / LIMITED`로 고정된다
- board field baseline artifact가 생성된다
- master board 테스트가 새 naming을 검증한다

---

## 이번 단계에서 일부러 하지 않는 것

- PA8 closeout readiness 로직 고도화
- reverse detector 로직 추가
- historical cost 복원
- Telegram surface 추가

즉 `P0-4`는 field naming과 section baseline을 잠그는 단계이지, readiness 판단 기준 자체를 넓히거나 바꾸는 단계는 아닙니다.

---

## 다음 단계 연결

`P0-4`가 닫히면 바로 다음 단계가 쉬워집니다.

1. `P1-1`
   - `pa8_closeout_readiness_status`에 실제 더 정교한 조건을 붙이기 쉬워집니다.
2. `P1-2`
   - `pa9_handoff_readiness_status`를 board / report / Telegram에서 같은 이름으로 surface하기 쉬워집니다.
3. `P1-3`
   - reverse readiness를 `reverse_readiness_status / reverse_blocking_reason / reverse_next_required_action` 기준으로 확장할 수 있습니다.
