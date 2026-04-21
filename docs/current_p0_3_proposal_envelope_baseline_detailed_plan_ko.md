# Current P0-3 Proposal Envelope Baseline Detailed Plan

## 목적

`P0-3`의 목적은 개선 제안 payload가 경로마다 다른 이름으로 흩어지지 않게, 공통 proposal envelope를 고정하는 것이다.

이번 단계가 닫히면 아래 두 경로가 같은 문법을 쓴다.

- `state25_weight_patch_review.py`
- `telegram_approval_bridge.py`

즉 proposal이 생성될 때부터 `proposal_id / proposal_stage / readiness_status / summary_ko / why_now_ko / recommended_action_ko`가 같은 shape로 흐르게 만든다.

---

## 왜 먼저 잠가야 하는가

지금 단계에서 envelope가 없으면 이후 단계에서 아래 문제가 다시 생긴다.

- 같은 제안을 어떤 곳은 `proposal_summary_ko`, 어떤 곳은 `reason_summary_ko`로 부름
- bridge는 `reason_summary`만 보고, report는 `report_lines_ko`만 보는 식으로 분리됨
- check topic / report topic / board가 같은 proposal을 서로 다른 이름으로 surface함
- `P1 readiness`, `P2 설명력`, `P3 /propose`가 시작될 때 payload 기준이 흔들림

그래서 `P0-3`은 새 기능이 아니라, 뒤 단계가 같은 proposal 언어를 쓰게 만드는 공통 기준면이다.

---

## 고정할 공통 envelope

### 필수 필드

- `proposal_id`
- `proposal_type`
- `scope_key`
- `trace_id`
- `proposal_stage`
- `readiness_status`
- `summary_ko`
- `why_now_ko`
- `recommended_action_ko`
- `blocking_reason`
- `decision_deadline_ts`

### 권장 보조 필드

- `confidence_level`
- `expected_effect_ko`
- `scope_note_ko`
- `evidence_snapshot`
- `report_message_ref`
- `check_message_ref`
- `supersedes_proposal_id`
- `related_approval_id`
- `related_apply_job_key`

---

## 이번 단계에서 실제로 할 일

### 1. 공통 proposal policy 파일 고정

파일:

- `backend/services/improvement_proposal_policy.py`

역할:

- proposal envelope build
- legacy candidate -> normalized envelope 변환
- required field validation
- baseline snapshot export

### 2. state25 proposal producer를 envelope 생산자로 승격

파일:

- `backend/services/state25_weight_patch_review.py`

역할:

- 기존 review candidate payload 유지
- 동시에 `proposal_envelope`를 같이 싣기
- top-level에도 핵심 필드를 mirror해서 기존 경로와의 호환 유지

### 3. telegram bridge를 envelope consumer로 고정

파일:

- `backend/services/telegram_approval_bridge.py`

역할:

- governance candidate를 받으면 바로 envelope normalize
- check dispatch / report dispatch / store event가 같은 envelope를 참조
- `summary / why_now / recommended_action / stage / readiness`가 dispatch record에 함께 남게 함

---

## 핵심 산출물

- 공통 정책 파일
  - `backend/services/improvement_proposal_policy.py`
- baseline artifact
  - `data/analysis/shadow_auto/improvement_proposal_envelope_baseline_latest.json`
  - `data/analysis/shadow_auto/improvement_proposal_envelope_baseline_latest.md`
- state25 proposal path envelope 반영
- telegram approval bridge envelope 반영

---

## 완료 조건

- `state25_weight_patch_review.py`가 `proposal_envelope`를 실제로 싣는다
- `telegram_approval_bridge.py`가 공통 envelope를 normalize해서 dispatch한다
- check/report record에서 `proposal_id`, `proposal_stage`, `readiness_status`를 읽을 수 있다
- 필수 필드 누락 시 validation이 실패한다
- baseline snapshot이 생성된다

---

## 이번 단계에서 일부러 하지 않는 것

- proposal scoring 로직 변경
- detector 자동 생성
- board readiness logic 확장
- apply 정책 변경

즉 `P0-3`은 제안 payload의 문법을 잠그는 단계이지, 제안 내용의 판단 로직을 바꾸는 단계가 아니다.

---

## 다음 단계 연결

`P0-3`이 닫히면 아래가 쉬워진다.

1. `P2-quick`
   - DM 설명력에서 proposal/report 문구 재사용 가능
2. `P1 readiness surface`
   - readiness 상태와 proposal 상태를 같은 언어로 보일 수 있음
3. `P3 /propose`
   - 수동 proposal도 같은 envelope로 생성 가능
