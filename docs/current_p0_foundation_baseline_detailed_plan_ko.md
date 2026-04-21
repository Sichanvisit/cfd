# Current P0 Foundation Baseline Detailed Plan

## 목적

이 문서는 [current_detailed_reinforcement_master_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_detailed_reinforcement_master_roadmap_ko.md)의 `P0 기준면 만들기`를 실제 구현 전에 잠그기 위한 상세 기준서다.

`P0`의 역할은 새 기능을 만드는 것이 아니다. 뒤에 오는 `P1 readiness`, `P2 설명력`, `P3 proposal`, `P4 detector`, `P5 승격`이 **같은 말과 같은 상태를 공유하게 만드는 것**이다.

즉 이 문서가 닫혀야 아래가 가능하다.

- 같은 종류의 준비 상태가 항상 같은 enum으로 표현된다
- 같은 종류의 제안이 항상 같은 room / topic으로 간다
- 보고서와 체크 inbox가 서로 다른 역할을 유지한다
- 실시간 DM과 승인 루프가 다시 섞이지 않는다
- detector / proposal / readiness가 같은 envelope 언어를 쓴다

---

## 한 줄 결론

`P0`는 아래 4개를 고정하는 단계다.

1. `어디로 보낼지`
   - DM / PnL / 체크 topic / 보고서 topic 역할 고정
2. `무슨 상태인지`
   - readiness / proposal stage / approval status 언어 고정
3. `무슨 모양인지`
   - proposal envelope / board field shape 고정
4. `누가 책임지는지`
   - runtime / report / approval / apply ownership 고정

---

## 왜 P0를 먼저 닫아야 하는가

`P0`가 흐리면 뒤 단계에서 아래 같은 문제가 생긴다.

- `ready`와 `pending`을 파일마다 다르게 씀
- check topic, report topic, DM이 같은 메시지를 서로 중복 발송함
- detector가 만든 candidate와 approval loop가 읽는 payload가 달라짐
- 같은 항목이 어떤 곳에선 `proposal`, 어떤 곳에선 `review`, 어떤 곳에선 `pending`으로 불림
- 나중에 사람이 backlog를 봐도 지금 어느 단계인지 헷갈림

따라서 `P0`는 빠르게 끝내되, 애매하게 두지 않는 것이 중요하다.

---

## P0 범위

### 포함

- topic 역할 고정
- 상태 enum 고정
- proposal envelope 고정
- readiness 표현 언어 고정
- master board와 Telegram route의 연결 기준 고정
- 문서와 코드 naming 정합성 고정

### 제외

- 새 detector 구현
- 새 apply logic 구현
- closeout / handoff 판정 로직 변경
- SA live adoption
- detector 자동 승인

즉 `P0`는 **문법과 라우팅을 고정하는 단계**지, 전략 로직을 바꾸는 단계가 아니다.

---

## 1. Telegram 목적지 역할표

### 목적지 A. `Trading_Bot` 1:1 DM

역할:

- 실시간 진입
- 실시간 대기
- 실시간 청산
- 실시간 반전

보내도 되는 것:

- 실행 중인 판단 결과
- 짧은 설명 3줄
- scene 참고 1줄
- 복기 힌트 1줄

보내면 안 되는 것:

- 승인 요청
- apply 확인 요청
- detector 후보 카드
- weight patch 검토 카드

원칙:

- 이 채널은 `실행 관찰 채널`
- 승인 인터페이스가 아니다

### 목적지 B. `CFD 체크방 / 체크 topic`

역할:

- 개선안 inbox
- backlog 누적
- 같은 scope 업데이트

보내도 되는 것:

- proposal 요약 1건
- readiness 요약 1건
- 상태 변경 알림
- `대체됨 / 만료 / 보류` 같은 짧은 상태 변화

보내면 안 되는 것:

- 장문 원문 보고서
- 실시간 entry / exit / wait

원칙:

- 이 채널은 `체크리스트형 inbox`
- 긴 텍스트보다 상태와 backlog가 우선

### 목적지 C. `CFD 체크방 / 보고서 topic`

역할:

- 원문 보고서 1회 발송
- proposal 상세
- review packet 상세

보내도 되는 것:

- 한국어 원문 보고서
- 제안 근거
- 기대 효과
- 범위 / bounded scope
- 승인 / 보류 / 거부 버튼

보내면 안 되는 것:

- 같은 보고서의 중복 원문
- 실시간 실행 메시지

원칙:

- 이 채널은 `원문 보고서 채널`
- 같은 scope는 기존 보고서 갱신 또는 supersede 관계를 남긴다

### 목적지 D. `CFD Pnl`

역할:

- 15분 / 1시간 / 4시간 / 1일 / 1주 / 1달 손익 요약
- 교훈 코멘트
- 일간 readiness 요약

보내도 되는 것:

- 순손익 / 총손익 / 비용 / 랏 / 승패율
- reason 집계
- 오늘의 교훈
- 시스템 상태 요약

보내면 안 되는 것:

- 승인 버튼
- proposal 원문

---

## 2. 상태 enum 기준

`P0`에서는 상태를 한 종류로 섞지 않고, 아래 3축으로 분리한다.

### A. readiness_status

이 상태는 `지금 적용 가능한가`를 보여준다.

권장 enum:

- `NOT_APPLICABLE`
- `PENDING_EVIDENCE`
- `BLOCKED`
- `READY_FOR_REVIEW`
- `READY_FOR_APPLY`
- `APPLIED`

사용 예:

- PA8 closeout
- PA9 handoff
- reverse readiness
- historical cost confidence는 별도 confidence enum을 쓰되, readiness 서브 필드로도 표현 가능

### B. proposal_stage

이 상태는 `지금 어떤 단계인가`를 보여준다.

권장 enum:

- `OBSERVE`
- `REPORT_READY`
- `REVIEW_PENDING`
- `APPROVED_FOR_APPLY`
- `APPLIED`
- `REJECTED`
- `HELD`
- `SUPERSEDED`
- `EXPIRED`

사용 예:

- state25 weight patch review
- candle/weight detector candidate
- reverse pattern detector candidate
- `/propose` 수동 트리거 결과

### C. approval_status

이 상태는 `승인 루프` 전용 상태다.

권장 enum:

- `PENDING`
- `APPROVED`
- `REJECTED`
- `HELD`
- `EXPIRED`
- `APPLIED`

원칙:

- `proposal_stage`와 `approval_status`는 섞지 않는다
- `REVIEW_PENDING`은 proposal 쪽 상태이고, `PENDING`은 approval 쪽 상태다

---

## 3. readiness 보조 enum

### blocking_reason

권장 기본 세트:

- `live_window_pending`
- `replay_insufficient`
- `worsened_rows_present`
- `rollback_risk_present`
- `approval_backlog`
- `historical_cost_limited`
- `reverse_wait_for_flat`
- `reverse_score_not_strong_enough`
- `scene_preview_only`

### confidence_level

권장 기본 세트:

- `HIGH`
- `MEDIUM`
- `LOW`
- `LIMITED`

사용 예:

- historical cost confidence
- detector confidence
- lesson confidence

---

## 4. proposal envelope 표준

모든 개선안 / detector 후보 / readiness report는 아래 공통 envelope를 따른다.

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

### 권장 필드

- `confidence_level`
- `expected_effect_ko`
- `evidence_snapshot`
- `report_message_ref`
- `check_message_ref`
- `supersedes_proposal_id`
- `related_approval_id`
- `related_apply_job_key`

### envelope 예시

```json
{
  "proposal_id": "prop_pa8_closeout_btc_20260412_0130",
  "proposal_type": "PA8_CLOSEOUT_REVIEW",
  "scope_key": "BTCUSD:pa8:closeout",
  "trace_id": "trace_pa8_btc_20260412_0130",
  "proposal_stage": "REPORT_READY",
  "readiness_status": "PENDING_EVIDENCE",
  "summary_ko": "BTCUSD PA8 closeout 준비 상태 점검",
  "why_now_ko": "live window가 아직 목표 봉수에 도달하지 않았습니다.",
  "recommended_action_ko": "closeout 결정을 보류하고 readiness를 계속 관찰합니다.",
  "blocking_reason": "live_window_pending",
  "confidence_level": "MEDIUM",
  "decision_deadline_ts": null,
  "supersedes_proposal_id": null
}
```

---

## 5. room / topic 라우팅 규칙

### 규칙 1. 실시간 판단은 DM만

- entry / wait / exit / reverse
- proposal / approval 카드와 분리

### 규칙 2. 보고서는 보고서 topic 한 번만

- 같은 scope 원문은 원칙적으로 중복 발송 금지
- 변경이 생기면 edit 또는 supersede 처리

### 규칙 3. 체크 topic은 inbox만

- 체크 항목은 누적
- 같은 scope는 새로 쌓지 말고 갱신
- 완료 / 대체 / 만료는 상태 변경으로 표시

### 규칙 4. PnL forum은 운영 결산과 readiness 요약

- proposal 원문을 넣지 않는다
- readiness summary는 넣어도 된다

---

## 6. ownership 기준

### runtime ownership

담당:

- `backend/app/trading_application.py`
- `backend/app/trading_application_runner.py`
- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_service.py`
- `backend/app/trading_application_reverse.py`

책임:

- 실시간 판단
- DM 메시지 payload의 원천 데이터

### report / route ownership

담당:

- `backend/services/telegram_route_policy.py`
- `backend/services/telegram_notification_hub.py`
- `backend/services/checkpoint_improvement_telegram_runtime.py`
- `backend/services/telegram_pnl_digest_formatter.py`

책임:

- route 역할과 목적지 기준면 고정
- 어떤 메시지가 어느 방 / topic으로 가는지
- 한국어 렌더링

### approval / apply ownership

담당:

- `backend/services/telegram_approval_bridge.py`
- `backend/services/approval_loop.py`
- `backend/services/apply_executor.py`

책임:

- 승인 상태 관리
- 승인 후 bounded apply 실행

### board / readiness ownership

담당:

- `backend/services/checkpoint_improvement_master_board.py`
- `backend/services/checkpoint_improvement_watch.py`

책임:

- readiness surface
- 상태판 요약

---

## 7. P0 구현 순서

### P0-1. topic 역할 고정

상세 기준:

- [current_p0_1_telegram_topic_role_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_1_telegram_topic_role_baseline_detailed_plan_ko.md)

완료 조건:

- DM / 체크 / 보고서 / PnL의 역할이 문서와 설정에서 동일하다

핵심 파일:

- `backend/services/telegram_route_policy.py`
- `backend/integrations/notifier.py`
- `.env`

### P0-2. 상태 enum 고정

상세 기준:

- [current_p0_2_status_enum_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_2_status_enum_baseline_detailed_plan_ko.md)

완료 조건:

- readiness_status / proposal_stage / approval_status가 분리되어 있다

### P0-3. proposal envelope 고정

상세 기준:

- [current_p0_3_proposal_envelope_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_3_proposal_envelope_baseline_detailed_plan_ko.md)

완료 조건:

- proposal candidate와 approval bridge가 같은 필드 이름을 쓴다

### P0-4. board field naming 고정

상세 기준:

- [current_p0_4_board_field_naming_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_4_board_field_naming_baseline_detailed_plan_ko.md)

완료 조건:

- `blocking_reason`, `readiness_status`, `confidence_level` 같은 키가 board와 보고서에서 일치한다

### P0-5. route ownership 고정

상세 기준:

- [current_p0_5_route_ownership_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_5_route_ownership_baseline_detailed_plan_ko.md)

완료 조건:

- 어느 레이어가 어디로 보내는지 ownership이 분명하다

### P0-6. 문서/코드 정합성 체크

상세 기준:

- [current_p0_6_doc_code_consistency_check_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_6_doc_code_consistency_check_detailed_plan_ko.md)

완료 조건:

- 로드맵 문서와 실제 코드 naming이 충돌하지 않는다

---

## 8. 완료 체크리스트

- `Trading_Bot` DM이 승인 인터페이스로 오해되지 않는다
- `체크` topic과 `보고서` topic 역할이 명확하다
- `proposal_stage`와 `approval_status`를 혼용하지 않는다
- `readiness_status`가 board, report, inbox에서 같은 이름으로 보인다
- proposal envelope의 필수 필드가 고정된다
- 같은 scope는 같은 `scope_key`를 쓴다
- supersede 관계를 표현할 수 있다
- historical cost confidence가 별도 confidence 축으로 분리된다

---

## 9. P0 다음 단계 진입 조건

아래가 충족되면 `P1 readiness surface`로 넘어간다.

- topic 역할표가 닫혔다
- 상태 enum이 닫혔다
- proposal envelope 필수 필드가 닫혔다
- readiness / proposal / approval 언어가 분리됐다
- 상위 문서와 이 문서가 같은 순서를 말한다

---

## 10. P0 이후 바로 이어질 작업

1. `P2-quick`
   - DM 3줄 설명
2. `P1-1`
   - PA8 closeout readiness
3. `P1-3`
   - reverse readiness
4. `P1-2`
   - PA9 handoff readiness

즉 `P0`는 길게 끄는 단계가 아니라, **뒤 단계에서 서로 다른 언어를 쓰지 않게 막는 짧고 강한 잠금 단계**로 보는 것이 맞다.
