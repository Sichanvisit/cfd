# Current Buildable Vs Conditioned Reinforcement Roadmap

## 목적

이 문서는 현재 CFD 프로젝트에서

- `지금 바로 구축할 수 있는 것`
- `조건이 있어야만 구축 가능한 것`
- `지금은 막아두는 것이 맞는 것`

을 분리해서, 실제 구현 순서와 기준을 한눈에 보이게 하기 위한 상세 로드맵이다.

핵심 질문은 아래 3개다.

1. 지금 당장 손대면 체감 품질이 오르는 것은 무엇인가
2. live sample, PA8 window, 충분한 반복 근거가 있어야만 가능한 것은 무엇인가
3. 지금 만들면 오히려 시스템을 흔들 수 있어서 막아야 하는 것은 무엇인가

이 문서는 아래 문서를 상위 기준으로 함께 본다.

- [current_all_in_one_system_master_playbook_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_all_in_one_system_master_playbook_ko.md)
- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_telegram_alert_message_refresh_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_alert_message_refresh_ko.md)

---

## 한 줄 결론

지금 단계에서 가장 생산적인 방향은

`설명력 -> 수동 proposal -> 관찰 코멘트 -> 반자동 detector`

순서로 가는 것이다.

반면 아래는 `기다리거나 제한해야 하는 영역`이다.

- `PA8 closeout / PA9 handoff`의 최종 판정
- `SA` live adoption
- `완전 자동 detector + 자동 patch 반영`
- `무제한 즉시 강제 반전`

즉 지금은 `설명 가능한 자동매매`와 `제안 가능한 학습 시스템`을 먼저 고도화하는 것이 맞다.

---

## 우선순위 재정렬

처음 보면 `지금 바로 구축 가능한 것`이 먼저처럼 보일 수 있지만, 실제 운영 우선순위는 조금 다르다.

핵심은 아래다.

`조건부 항목을 그냥 기다리는 것`이 아니라,
`조건부 항목을 좁은 관찰 / 보고 / 리뷰 준비 상태로 먼저 끌어올린다`

즉 아래 항목이 지금 더 중요하다.

- `반자동 proposal detector`
- `PA8 closeout readiness`
- `PA9 handoff readiness`
- `scene-aware detector`
- `더 공격적인 reverse 개선`
- `historical cost confidence`

다만 이들을 지금 바로 live 승격으로 연결하지 않고,

1. `observe`
2. `report`
3. `review`
4. `apply`

중 `1~2단계`, 많아도 `3단계`까지만 먼저 올린다.

즉 지금 중요한 건 `최종 판정`보다 `판정 가능 상태를 surface 위로 올리는 것`이다.

---

## 1. 지금 바로 구축할 수 있는 것

아래는 현재 코드와 문서 기준으로, 추가 근거 없이도 바로 구현 가능한 항목이다.

| 구분 | 항목 | 왜 지금 가능한가 | 핵심 파일 |
|---|---|---|---|
| A1 | 실시간 DM 설명력 표준화 | runtime 알림 경로와 formatter가 이미 있음 | `backend/integrations/notifier.py`, `backend/app/trading_application.py`, `backend/app/trading_application_runner.py`, `backend/services/entry_try_open_entry.py`, `backend/services/exit_service.py`, `backend/app/trading_application_reverse.py` |
| A2 | `/propose` 수동 트리거 v0 | proposal payload / Telegram check-report / approval-apply 루프가 이미 있음 | `backend/services/state25_weight_patch_review.py`, `backend/services/checkpoint_improvement_telegram_runtime.py`, `backend/services/telegram_approval_bridge.py`, `backend/services/telegram_notification_hub.py` |
| A3 | PnL 교훈 코멘트 자동 생성 | PnL formatter와 closed trade 원천이 이미 있음 | `backend/services/telegram_pnl_digest_formatter.py`, `backend/services/telegram_ops_service.py`, `data/trades/trade_closed_history.csv` |
| A4 | scene axis를 DM/보고서에 참고축으로 노출 | SA는 preview-only지만 읽어오는 것은 가능 | `backend/services/path_checkpoint_scene_disagreement_audit.py`, `backend/services/path_checkpoint_scene_bias_preview.py`, `backend/integrations/notifier.py`, `backend/services/telegram_notification_hub.py` |
| A5 | 체크방 inbox UX 정리 | check/report room, approval bridge, topic 분리가 이미 됨 | `backend/services/telegram_approval_bridge.py`, `backend/services/telegram_state_store.py`, `backend/services/telegram_notification_hub.py` |
| A6 | weight/action 제안 보고서 한글화 정밀화 | 한국어 label surface가 이미 있음 | `backend/services/teacher_pattern_active_candidate_runtime.py`, `backend/services/state25_weight_patch_review.py` |

---

## 2. 조건이 있어야만 가능한 것

아래는 `구현 코드`는 지금 만들어둘 수 있지만, 최종 품질이나 승격은 반드시 추가 조건이 있어야 하는 항목이다.

| 구분 | 항목 | 필요한 조건 | 지금 할 수 있는 것 |
|---|---|---|---|
| B1 | 반자동 proposal detector | 반복된 실패 패턴, 최소 sample floor, false positive 점검 | detector scaffold / manual override / log-only trigger |
| B2 | PA8 closeout 최종 판정 | live first-window row 축적, closeout-ready symbol 확보 | closeout trigger/보고서/apply 통로 유지 |
| B3 | PA9 handoff 실제 승격 | 최소 1개 symbol closeout 완료 | handoff scaffold / review/apply packet 유지 |
| B4 | historical cost 신뢰도 완전화 | 과거 원천 데이터 보강 또는 보수적 재계산 기준 | recent row 중심 보정, 과거 구간 경고 문구 유지 |
| B5 | scene-aware detector | scene disagreement / preview 변화가 충분히 반복 | scene을 참고축으로 먼저 노출, detector는 나중 승격 |
| B6 | 공격적 reverse 개선 | 실제 반전 실패/성공 pattern의 충분한 반복 근거 | reverse alert / pending reverse / retry 설명 강화 |

---

## 3. 지금은 막아두는 것이 맞는 것

아래는 지금 만들거나 넓히면 오히려 운영 안정성을 해칠 수 있는 영역이다.

| 구분 | 항목 | 지금 막아야 하는 이유 |
|---|---|---|
| C1 | SA live adoption | sample 얇고 worsened row가 존재함 |
| C2 | detector 자동 승인 + 자동 patch 적용 | false positive가 곧 live rule 오염으로 이어짐 |
| C3 | wide-scope multi-symbol rollout | single-scene 학습을 전체 전략으로 과대확장할 위험 |
| C4 | 무제한 즉시 강제 반전 | 포지션 정리/체결 지연/슬리피지/중복 진입 위험이 큼 |
| C5 | PnL 교훈에서 곧바로 weight patch 생성 | 작은 sample의 우연을 규칙으로 굳힐 위험 |

---

## 4. 지금 바로 구축할 것의 상세 설계

## A1. 실시간 DM 설명력 표준화

### 목표

사용자가 DM만 보고 아래를 바로 이해하게 만든다.

- 왜 진입했는가
- 왜 대기했는가
- 왜 청산했는가
- 왜 반전 준비로 읽었는가

### 권장 포맷

#### 진입

- `주도축`
- `핵심리스크`
- `강도`
- `scene`은 옵션 1줄

예:

- `주도축: 상단 저항보다 하단 이탈 압력이 더 강함`
- `핵심리스크: 상방 추진력 재가속 가능`
- `강도: 보통`

#### 대기

- `대기이유`
- `해제조건`
- `참고축: barrier / belief / forecast`

#### 청산

- `청산사유`
- `복기힌트`

#### 반전

- `반전상태`
- `급변근거`
- `강도`

### 완료 조건

- 영문 raw score 중심 메시지가 사라진다
- 동일 type 메시지 포맷이 항상 일정하다
- scene/shock를 넣어도 장문이 되지 않는다

---

## A2. `/propose` 수동 트리거 v0

### 목표

사람이 “이 실패 패턴을 proposal 후보로 올려보자”를 바로 실행할 수 있게 만든다.

### 입력 축

- 최근 N건 closed trade
- reason별
- scene별
- 시간대별
- MFE 포착률
- partial missed
- reverse 실패 / wait 과다 / 조기 진입 역행

### 출력

- 체크방: 짧은 inbox 항목
- 보고서 topic: 원문 보고서 1회

### 원칙

- 처음부터 자동 detector로 가지 않는다
- proposal은 한국어 설명문으로 생성한다
- 같은 scope는 새 카드 폭탄이 아니라 기존 항목 갱신

### 완료 조건

- `/propose` 1회 실행으로 `문제 패턴 상위 3~5개`가 한국어로 나온다
- 승인 시 bounded patch review 루프로 연결된다

---

## A3. PnL 교훈 코멘트 자동 생성

### 목표

PnL 보고가 단순 숫자표가 아니라 `학습 전 단계 코멘트`가 되게 만든다.

### 코멘트 예시

- `오늘은 상단 거부 계열 연속 손실이 많았습니다.`
- `MFE 대비 실현 수익 포착이 약했습니다.`
- `partial timing이 늦어 러너 회수가 약했습니다.`
- `오전 시간대 손실 편중이 관찰됐습니다.`

### 원칙

- 처음에는 patch 제안이 아니라 `관찰 코멘트`
- sample floor 미달 시 “참고 수준”으로만 표시

### 완료 조건

- `15분 / 1시간 / 4시간 / 1일 / 1주 / 1달` 보고 중 최소 `1일 / 1주 / 1달`에 코멘트가 붙는다
- 코멘트가 바로 patch 제안으로 이어지지 않는다

---

## A4. scene axis 참고 노출

### 목표

SA를 live rule에 직접 반영하지는 않더라도, 해석 참고축으로 사용자에게 보여준다.

### 예시

- `scene: breakout_retest_hold / caution`
- `scene: trend_exhaustion / weak`
- `scene gate: none`

### 원칙

- 의사결정 축이 아니라 설명축
- preview-only 상태 유지

### 완료 조건

- DM 또는 보고서에 scene 한 줄이 선택적으로 붙는다
- scene 값이 길고 난해하지 않다

---

## A5. 체크방 inbox UX 정리

### 목표

개선안이 쌓여도 사용자가 “뭘 봐야 할지” 바로 알 수 있게 한다.

### 구조

- `보고서 topic`: 원문 보고서 1회
- `체크 topic`: 누적 inbox

### 체크 inbox 항목 형식

- 상태
- 대상 scope
- 핵심 변경
- 표본 수
- 기대 효과
- `열기` 링크

### 원칙

- 같은 scope는 갱신
- 오래된 항목은 `대체됨`
- 긴급건만 별도 푸시

### 완료 조건

- 카드가 계속 쌓이지 않고 inbox 항목이 갱신된다
- 사용자는 체크 topic만 보고도 backlog를 이해할 수 있다

---

## A6. weight/action 제안 보고서 한글화 정밀화

### 목표

raw key가 아니라 사람이 조정 가능한 언어로 proposal을 본다.

### 예시

- `윗꼬리 반응 비중`
- `아랫꼬리 반응 비중`
- `캔들 몸통 비중`
- `압축 구간 반응 비중`
- `상단/하단 위치 해석 비중`

### 원칙

- 변수명 직송 금지
- `설명 문장 + 괄호 안 기능 조각` 형식 허용
- 번역은 의미를 보존하되 지나치게 시적이지 않게

### 완료 조건

- 보고서만 읽어도 “무엇을 줄이고 늘리는지” 이해 가능

---

## 5. 조건부 항목의 준비 로드맵

## B1. 반자동 proposal detector

### 지금 할 수 있는 준비

- detector interface 만들기
- log-only proposal emit
- same-scope merge 규칙 만들기
- false positive 샘플 저장
- `수동 실행 -> 자동 후보 surface`까지는 먼저 올리기

### 지금은 review-ready까지만 올릴 것

- 체크 topic inbox 생성
- 보고서 topic 원문 생성
- 승인 대기 상태까지 연결

### 아직 기다릴 것

- 바로 approval 기본값으로 올리기
- detector 결과를 wide rollout으로 연결하기

## B2. PA8 closeout

### 지금 할 수 있는 준비

- closeout auto-trigger 유지
- closeout review 템플릿 다듬기
- symbol별 live-window readiness 보고서 강화
- `closeout-ready가 왜 아직 아닌지`를 계속 board/check/report에 올리기

### 지금은 review-ready까지만 올릴 것

- `pending / not-ready / ready` 3상태를 체크방에 표기
- live-window 부족 이유를 보고서에 명시

### 기다려야 하는 것

- 실제 closeout 판정
- promote-ready 판정

## B3. PA9 handoff

### 지금 할 수 있는 준비

- handoff scaffold / review / apply packet 유지
- closeout 이후 자동 전진 경로 유지
- `handoff_state / review_state / apply_state`를 계속 surface에 노출

### 지금은 readiness surfacing까지만 올릴 것

- `HOLD_PENDING_PA8_LIVE_WINDOW`
- `READY_FOR_REVIEW`
- `READY_FOR_APPLY`

상태를 보고서와 상태판에서 사람이 읽을 수 있게 고정

### 기다려야 하는 것

- 실제 승격
- handoff 이후 확대 적용

## B4. historical cost integrity

### 지금 할 수 있는 준비

- old row에는 경고 문구 유지
- recent row 기준 집계는 계속 정확도 보강
- `confidence grade` 또는 `추정치` 표시를 surface에 올리기

### 기다려야 하는 것

- 과거 데이터를 완전히 복원하는 것은 원천 한계가 있음

## B5. scene-aware detector

### 지금 할 수 있는 준비

- scene 값을 설명축으로 DM/보고서에 노출
- scene disagreement / preview change를 체크방 관찰 항목으로 올리기
- scene-aware proposal은 log-only 후보로만 생성

### 아직 기다릴 것

- scene live adoption
- scene 기반 wide rollout

## B6. 더 공격적인 reverse 개선

### 지금 할 수 있는 준비

- reverse 후보 감지를 더 자주 surface에 올리기
- `왜 즉시 뒤집지 않았는지`, `왜 pending reverse인지`를 설명
- reverse missed / reverse late 패턴을 proposal 후보로 log-only 기록

### 아직 기다릴 것

- 무제한 즉시 강제 반전
- 반전 감지 즉시 auto force-close + auto reverse

---

## 6. 실제 구현 순서

### Phase 1. 조건부 과제를 narrow lane으로 먼저 surface

1. `B1` 반자동 detector scaffold
2. `B2` PA8 closeout readiness surface
3. `B3` PA9 handoff readiness surface
4. `B5` scene-aware detector log-only lane
5. `B6` reverse-ready / reverse-blocked surface
6. `B4` historical cost confidence surface

### Phase 2. supporting layer 보강

1. `A1` 실시간 DM 설명력 표준화
2. `A2` `/propose` 수동 트리거 v0
3. `A3` PnL 교훈 코멘트
4. `A4` scene axis 참고 노출
5. `A5` 체크방 inbox UX 정리
6. `A6` weight/action 제안 한글화 정밀화

### Phase 3. live 근거가 들어오면 진행

1. `PA8 closeout 1건`
2. `PA9 handoff 실제 승격`
3. 반복된 detector만 반자동으로 승격

### Phase 4. 지금은 하지 않음

1. `SA live adoption`
2. `detector auto-approve`
3. `wide rollout`
4. `무제한 강제 반전`

---

## 7. 지금 가장 추천하는 다음 3개

1. `PA8 closeout readiness surface`
2. `reverse-ready / reverse-blocked surface`
3. `scene-aware detector log-only lane`

이 3개는

- 조건부 과제를 그냥 기다리지 않고 계속 눈앞에 올려준다
- 사용자가 지금 무엇을 보고 판단해야 하는지 더 분명하게 만든다
- 이후 review/apply 승격의 기준 surface가 된다

---

## 최종 정리

지금 단계에서 중요한 건 `더 복잡한 구조`가 아니라,

`현재 돌아가는 판단을 사람이 이해할 수 있게 드러내고, 반복되는 실패를 제안 가능한 형태로 끌어올리는 것`

이다.

그래서 지금은 아래처럼 나누어 보는 것이 가장 맞다.

- `지금 바로 구축`
  - 설명력
  - 수동 proposal
  - PnL 교훈
  - scene 참고 노출
  - inbox UX
- `조건부 구축`
  - 반자동 detector
  - PA8 closeout
  - PA9 handoff
- `지금은 금지`
  - SA live adoption
  - 자동 승인
  - wide rollout
  - 무제한 강제 반전
