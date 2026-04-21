# Current Advice Gap Reinforcement Execution Roadmap

## 목적

이 문서는 최근 받은 외부 조언과 현재 코드 상태를 합쳐서,

- `받아들일 조언`
- `지금 부족한 것`
- `지금 보강해야 할 것`
- `지금은 하지 말아야 할 것`

을 한 장에서 정리하고, 그걸 실제 구현 순서로 바꾸기 위한 상세 실행 로드맵이다.

핵심 목적은 아래 하나다.

`좋은 조언을 감상으로 남기지 않고, 지금 당장 손댈 실행 순서로 변환한다.`

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_all_in_one_system_master_playbook_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_all_in_one_system_master_playbook_ko.md)
- [current_buildable_vs_conditioned_reinforcement_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_buildable_vs_conditioned_reinforcement_roadmap_ko.md)
- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_telegram_alert_message_refresh_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_alert_message_refresh_ko.md)

---

## 한 줄 결론

조언을 종합하면, 지금 시스템은 `구조 추가`보다 아래 순서가 더 중요하다.

1. `실시간 판단 설명력`
2. `실패 기반 proposal surface`
3. `조건부 항목 readiness surface`
4. `반자동 detector`
5. `PA8 closeout -> PA9 handoff`

즉 지금은 `더 만드는 단계`보다

`지금 있는 판단을 드러내고, 실패를 제안 가능한 형태로 끌어올리는 단계`

로 보는 것이 맞다.

---

## 1. 조언에서 받아들일 핵심

## A. 설명력이 1순위라는 조언

이 조언은 그대로 받는 것이 맞다.

왜 중요한가:

- 설명이 없으면 시스템을 신뢰하지 못한다
- 신뢰하지 못하면 중간 개입이 늘어난다
- 중간 개입이 늘면 자동매매 품질이 실제보다 더 나빠 보인다
- 설명이 있어야 실패를 proposal로 끌어올릴 수 있다

즉 설명력은 `보기 좋은 기능`이 아니라

`신뢰 -> 개입 억제 -> 복기 -> 제안 생성`

루프의 시작점이다.

## B. proposal detector는 반자동으로 시작하라는 조언

이 조언도 그대로 받는 것이 맞다.

권장 단계:

1. 수동 `/propose`
2. 반자동 detector
3. 자동 detector

왜 이렇게 가야 하는가:

- 처음부터 완전 자동 detector로 가면 false positive가 많아진다
- 체크방이 proposal 쓰레기장이 되면 승인 루프가 죽는다
- 먼저 사람이 “어떤 실패 패턴이 진짜 문제인가”를 확인해야 한다

## C. PA8은 기다리는 것이 맞다는 조언

이 조언도 그대로 유지한다.

왜냐하면:

- closeout 기준을 억지로 낮추면 rollback false positive가 늘어난다
- PA9 handoff의 신뢰도까지 같이 무너진다

대신 `그냥 기다리는 것`이 아니라,

`closeout readiness를 surface 위로 끌어올리고`
`기다리는 동안 설명력과 proposal detector를 채우는 것`

이 맞다.

## D. scene / PnL 교훈을 표면으로 끌어올리라는 조언

이 조언은 리스크 대비 효과가 큰 편이다.

왜 좋은가:

- SA는 아직 preview-only지만, 설명축으로 노출하는 것은 가능하다
- PnL은 단순 숫자표보다 `오늘 무엇을 배웠는가`가 더 중요하다

단, 바로 patch 제안으로 올리지 않고

`관찰 코멘트 -> 사람이 확인 -> proposal`

순서로 가야 한다.

---

## 2. 현재 부족한 것

## G1. 실시간 판단 설명력이 약하다

현재 부족함:

- 왜 진입했는지
- 왜 대기했는지
- 왜 청산했는지
- 왜 반전 준비인지

가 사용자 언어로 충분히 surface되지 않는다.

핵심 부족 포인트:

- 구조 설명축 부족
- 힘 설명축 부족
- 전이 설명축 부족

즉 `판단은 있는데 설명이 약한 상태`다.

## G2. proposal을 자동으로 surface하는 detector가 없다

현재 부족함:

- patch review payload는 있음
- Telegram approval/apply 루프도 있음
- 하지만 `무엇을 proposal로 올릴지`를 자동 생성하는 detector가 비어 있다

즉 `승인 루프는 있는데 생각을 올리는 감지기`가 부족하다.

## G3. 조건부 항목이 readiness 상태로 충분히 보이지 않는다

현재 부족함:

- `PA8 closeout`이 왜 아직 아닌지
- `PA9 handoff`가 지금 어떤 상태인지
- `reverse`가 왜 blocked/pending인지
- `historical cost`가 어느 정도까지 믿을 수 있는지

가 surface 위에서 충분히 읽히지 않는다.

즉 `최종 판정은 못 해도 준비 상태는 계속 보여줘야 하는데` 그 부분이 약하다.

## G4. PnL은 숫자는 살아났지만 교훈 surface가 약하다

현재 부족함:

- 구간별 순손익/승률/랏은 보이기 시작함
- 하지만 `오늘 무엇을 배웠는지`가 아직 약하다

즉 `운영 보고`는 되지만 `학습 입력`으로는 아직 덜 올라온 상태다.

---

## 3. 지금 보강해야 할 것

## R1. 실시간 DM 설명력 표준화

목표:

- 모든 DM을 사람이 읽는 판정 언어로 바꾼다

고정 포맷:

### 진입

- `주도축`
- `핵심리스크`
- `강도`
- `scene` 1줄 옵션

### 대기

- `대기이유`
- `해제조건`
- `참고축: barrier / belief / forecast`

### 청산

- `청산사유`
- `복기힌트`

### 반전

- `반전상태`
- `급변근거`
- `강도`

완료 조건:

- 점수 나열형, 영어 raw 위주 문구가 사라진다
- 같은 type 메시지 포맷이 항상 일정하다
- DM만 보고도 “왜?”에 대한 1차 답이 나온다

핵심 파일:

- `backend/integrations/notifier.py`
- `backend/app/trading_application.py`
- `backend/app/trading_application_runner.py`
- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_service.py`
- `backend/app/trading_application_reverse.py`

## R2. `/propose` 수동 트리거

목표:

- 사람이 “이 실패 패턴을 proposal로 올려보자”를 바로 실행할 수 있게 만든다

입력 축:

- 최근 N건 closed trade
- reason별
- scene별
- 시간대별
- MFE 포착률
- partial missed
- reverse missed / reverse late

출력:

- 체크 topic: 짧은 inbox 항목
- 보고서 topic: 원문 보고서 1회

원칙:

- 처음부터 자동 detector로 가지 않는다
- proposal은 한국어 설명문으로 생성한다
- 같은 scope는 기존 inbox 항목 갱신

완료 조건:

- `/propose` 1회 실행으로 `상위 문제 패턴 3~5개`가 한국어로 나온다
- approval/apply 루프로 연결된다

핵심 파일:

- `backend/services/state25_weight_patch_review.py`
- `backend/services/checkpoint_improvement_telegram_runtime.py`
- `backend/services/telegram_approval_bridge.py`
- `backend/services/telegram_notification_hub.py`

## R3. PnL 교훈 코멘트

목표:

- PnL이 숫자표를 넘어 `학습 전 단계 코멘트`가 되게 만든다

예시:

- `오늘은 상단 거부 계열 연속 손실이 많았습니다.`
- `MFE 대비 실현 수익 포착이 약했습니다.`
- `partial timing이 늦었습니다.`
- `특정 시간대 손실 편중이 관찰됐습니다.`

원칙:

- 처음에는 patch 제안이 아니라 관찰 코멘트
- sample floor 미달 시 “참고 수준”으로만 표시

완료 조건:

- `1일 / 1주 / 1달` 보고에는 교훈 코멘트가 붙는다
- 코멘트가 바로 patch apply로 이어지지 않는다

핵심 파일:

- `backend/services/telegram_pnl_digest_formatter.py`
- `backend/services/telegram_ops_service.py`

## R4. 조건부 항목 readiness surface

목표:

- 아직 판정할 수 없는 것들을 `준비 상태`로 계속 보이게 만든다

대상:

- `PA8 closeout readiness`
- `PA9 handoff readiness`
- `reverse-ready / reverse-blocked`
- `historical cost confidence`
- `scene-aware detector log-only state`

핵심 원칙:

- 지금은 `observe / report / review`
까지만 올린다
- `apply`는 조건 충족 전까지 올리지 않는다

완료 조건:

- 사용자가 “지금 무엇이 조건 부족인지”를 상태판/체크방에서 바로 읽을 수 있다

핵심 파일:

- `backend/services/checkpoint_improvement_master_board.py`
- `backend/services/checkpoint_improvement_watch.py`
- `backend/services/checkpoint_improvement_recovery_health.py`
- `backend/app/trading_application_reverse.py`
- `backend/services/telegram_notification_hub.py`

## R5. scene-aware detector log-only lane

목표:

- scene 정보를 live rule에 직접 쓰지 않고, 실패 패턴 proposal의 참고축으로만 먼저 쓴다

예시:

- `scene: breakout_retest_hold / caution`
- `scene: trend_exhaustion / weak`
- `scene disagreement 증가`

원칙:

- preview-only 유지
- detector는 log-only
- scene 단독으로 patch를 만들지 않는다

완료 조건:

- DM/보고서에 scene 참고줄이 붙는다
- scene 관련 proposal candidate가 log-only로 쌓인다

핵심 파일:

- `backend/services/path_checkpoint_scene_disagreement_audit.py`
- `backend/services/path_checkpoint_scene_bias_preview.py`
- `backend/integrations/notifier.py`
- `backend/services/telegram_notification_hub.py`

---

## 4. 지금 하지 말아야 하는 것

## X1. SA live adoption

이유:

- sample이 얇고 worsened row가 존재한다

## X2. detector 자동 승인 + 자동 patch 적용

이유:

- false positive가 곧 live rule 오염으로 이어진다

## X3. wide multi-symbol rollout

이유:

- single-scene 학습을 전체 전략으로 과대확장할 위험이 크다

## X4. 무제한 즉시 강제 반전

이유:

- 포지션 정리 지연
- 슬리피지
- 중복 진입
- 체결 꼬임

위험이 너무 크다

## X5. PnL 교훈 -> 곧바로 patch 적용

이유:

- sample이 적을 때 우연을 규칙으로 굳힐 수 있다

---

## 5. 실제 구현 순서

## Phase 1. 가장 먼저

1. `R4` 조건부 항목 readiness surface
2. `R1` 실시간 DM 설명력 표준화
3. `R5` scene-aware detector log-only lane

이 단계의 목적:

- “지금 무엇이 준비 중인지”
- “왜 이런 판단을 했는지”

를 surface 위에 올리는 것이다.

## Phase 2. 그 다음

1. `R2` `/propose` 수동 트리거
2. `R3` PnL 교훈 코멘트

이 단계의 목적:

- 실패 패턴을 사람이 읽고 제안할 수 있게 만든다

## Phase 3. 반복이 쌓이면

1. 반자동 detector scaffold
2. detector 조건을 좁게 승격
3. same-scope merge / false positive 관리

이 단계의 목적:

- proposal 생성기를 반자동으로 올린다

## Phase 4. live 근거가 충분하면

1. `PA8 closeout 1건`
2. `PA9 handoff 실제 승격`

이 단계의 목적:

- 운영 완성도를 닫는다

---

## 6. 지금 가장 추천하는 다음 3개

1. `PA8 closeout readiness surface`
2. `reverse-ready / reverse-blocked 설명 surface`
3. `DM 설명력 포맷 상세안`

이 3개가 중요한 이유:

- 조건부 항목을 그냥 기다리지 않고 surface 위로 올릴 수 있고
- 사용자가 가장 먼저 체감하며
- 이후 `/propose`, detector, closeout/handoff로 이어지는 기준면이 되기 때문이다

---

## 최종 정리

지금 단계에서 진짜 중요한 건 `더 많은 기능`이 아니다.

중요한 건 아래 순서다.

1. 판단을 설명한다
2. 실패를 surface에 올린다
3. 실패를 proposal로 만든다
4. proposal을 좁게 승인한다
5. live 근거가 쌓이면 closeout과 handoff를 닫는다

즉 지금은

`구조 추가`

보다

`설명 -> 제안 -> 승인 준비`

를 먼저 완성하는 것이 맞다.
