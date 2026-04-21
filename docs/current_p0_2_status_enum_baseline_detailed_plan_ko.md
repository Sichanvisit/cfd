# Current P0-2 Status Enum Baseline Detailed Plan

## 목적

이 문서는 `P0-2 상태 enum 고정`을 실제 코드 기준으로 닫은 결과를 정리한다.

상위 기준:

- [current_p0_foundation_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_foundation_baseline_detailed_plan_ko.md)
- [current_detailed_reinforcement_master_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_detailed_reinforcement_master_roadmap_ko.md)

---

## 한 줄 결론

`readiness_status`, `proposal_stage`, `approval_status`를 중앙 정책 파일 하나로 고정했고, approval / reconcile / master board가 그 정책을 공용으로 읽도록 정리했다.

핵심 파일:

- `backend/services/improvement_status_policy.py`

---

## 왜 이 단계가 중요했는가

상태 enum이 흩어져 있으면 아래 문제가 생긴다.

- proposal 쪽 `REVIEW_PENDING`과 approval 쪽 `pending`을 섞어 씀
- board에서는 `approved`를 backlog로 보고, 다른 파일에선 terminal로 읽음
- detector / proposal / approval / apply가 서로 다른 언어를 써서 나중에 해석이 꼬임

이번 단계의 목적은 `상태 문자열을 줄이는 것`이 아니라, **서로 다른 상태 축을 명확히 분리하는 것**이다.

---

## 고정된 상태 축

### 1. readiness_status

의미:

- 지금 이 항목이 적용 가능한가
- 아직 근거가 부족한가
- 차단 사유가 있는가

고정값:

- `NOT_APPLICABLE`
- `PENDING_EVIDENCE`
- `BLOCKED`
- `READY_FOR_REVIEW`
- `READY_FOR_APPLY`
- `APPLIED`

### 2. proposal_stage

의미:

- 관찰 / 보고 / 리뷰 / 적용 중 어디 단계인가

고정값:

- `OBSERVE`
- `REPORT_READY`
- `REVIEW_PENDING`
- `APPROVED_FOR_APPLY`
- `APPLIED`
- `REJECTED`
- `HELD`
- `SUPERSEDED`
- `EXPIRED`

### 3. approval_status

의미:

- 승인 루프 안에서 현재 버튼 상태가 무엇인가

고정값:

- `pending`
- `approved`
- `held`
- `rejected`
- `expired`
- `applied`
- `cancelled`

중요:

- `proposal_stage != approval_status`
- `readiness_status != approval_status`

즉 아래는 같은 말이 아니다.

- `REVIEW_PENDING`
- `pending`

앞은 proposal 단계, 뒤는 approval 상태다.

---

## 구현 내용

### 1. 중앙 상태 정책 파일 추가

- `backend/services/improvement_status_policy.py`

포함:

- 상태 상수
- normalize 함수
- 한국어 label 함수
- baseline snapshot writer

### 2. approval loop 공용화

- `backend/services/approval_loop.py`

변경:

- actionable / terminal approval status를 중앙 정책에서 import
- action -> status 변환도 중앙 정책 사용

### 3. master board / reconcile 공용화

- `backend/services/checkpoint_improvement_master_board.py`
- `backend/services/checkpoint_improvement_reconcile.py`

변경:

- approval backlog 상태와 same-scope conflict 상태를 중앙 정책에서 import

효과:

- backlog 계산과 conflict 계산이 approval loop와 같은 기준을 쓴다

---

## baseline 산출물

생성 파일:

- `data/analysis/shadow_auto/improvement_status_baseline_latest.json`
- `data/analysis/shadow_auto/improvement_status_baseline_latest.md`

역할:

- 현재 상태 enum 기준을 한눈에 확인
- readiness / proposal / approval 축이 분리돼 있는지 확인

---

## 검증

테스트:

- `tests/unit/test_improvement_status_policy.py`
- `tests/unit/test_approval_loop.py`
- `tests/unit/test_telegram_approval_bridge.py`
- `tests/unit/test_checkpoint_improvement_master_board.py`
- `tests/unit/test_checkpoint_improvement_reconcile.py`

검증 포인트:

- normalize 함수 동작
- 상태 축 분리
- approval loop와 board/reconcile가 같은 approval 상태 기준 사용
- baseline snapshot 생성

---

## P0-2 완료 판정

아래를 만족하므로 `P0-2`는 완료로 본다.

- readiness / proposal / approval 상태 축이 분리됨
- approval 관련 핵심 모듈이 중앙 정책을 공용 사용
- baseline artifact 생성 가능
- 상태 문자열을 문서와 코드에서 같은 방식으로 설명 가능

---

## 다음 단계

`P0-3 proposal envelope 고정`

즉 다음엔 상태가 아니라 payload shape를 고정하는 단계로 넘어가는 것이 맞다.
