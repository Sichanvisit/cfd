# ST9 Proposal / Hindsight Bridge 상세 계획

## 목표

`ST5` detector bridge와 `ST8` notifier bridge에서 읽기 시작한 state-first context를
[trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)에서도
같은 언어로 이어서 읽게 만든다.

이번 단계의 핵심은 새 판단을 더 만드는 것이 아니라,
detector 최신 issue가 이미 들고 있는:
- `context_bundle_summary_ko`
- `context_conflict_*`
- `late_chase_*`
- `hindsight_status_*`

를 proposal row, report line, proposal envelope로 승격해서
review backlog와 hindsight가 끊기지 않게 하는 것이다.

## 현재 상태

선행 완료:
- `ST5` detector bridge
- `ST8` notifier bridge

즉 detector latest issue row에는 이미:
- `context_bundle_summary_ko`
- `context_conflict_state`
- `context_conflict_label_ko`
- `late_chase_risk_state`
- `late_chase_reason`
- `htf_alignment_state`
- `previous_box_break_state`
- `hindsight_status`
- `hindsight_status_ko`

가 들어 있다.

하지만 [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)는
아직 이 필드를 proposal/report 쪽으로 충분히 승격하지 못한다.

## 이번 단계에서 구현할 것

### 1. Feedback Promotion Row Context Bridge

feedback-aware promotion row를 만들 때,
latest detector issue에서 다음 필드를 같이 복사한다.

- `context_bundle_summary_ko`
- `context_conflict_*`
- `late_chase_*`
- `htf_alignment_*`
- `previous_box_*`
- `hindsight_status`
- `hindsight_status_ko`

그리고 proposal용 요약 필드:
- `proposal_context_summary_ko`

를 만들어

`맥락 요약 / 사후 판정`

형태로 review row에 같이 싣는다.

### 2. Surfaced Problem Pattern Bridge

문제 패턴 row가 feedback-aware promotion과 매칭되면,
top match의 context / hindsight 요약을 같이 복사한다.

예:
- `feedback_priority_context_summary_ko`
- `feedback_priority_hindsight_status_ko`
- `feedback_priority_context_conflict_state`

### 3. Proposal Envelope Why-Now 보강

top surfaced issue 또는 top feedback promotion row에 context/hindsight 요약이 있으면,
`proposal_envelope.why_now_ko`에 같이 붙인다.

즉 이제 proposal envelope도 단순히
- `반복 손실`
- `feedback 누적`

만 말하는 게 아니라,

- `HTF 전체 상승 정렬`
- `직전 박스 상단 돌파 유지`
- `사후 확정 오판`

같은 맥락을 바로 읽게 된다.

### 4. Report Line 보강

feedback-aware 섹션과 문제 패턴 섹션에

`맥락/사후: ...`

라인을 추가한다.

## 이번 단계에서 하지 않을 것

- proposal이 context만으로 바로 apply 결정을 내리지 않음
- hindsight 계산 로직 자체를 다시 쓰지 않음
- semantic cluster / gate review 로직을 다시 구조 변경하지 않음
- detector와 proposal 사이에 새 scoring layer를 추가하지 않음

## 완료 기준

- feedback_promotion_rows가 context/hindsight 요약을 같이 들고 있음
- surfaced_problem_patterns가 top feedback match의 context/hindsight를 같이 들고 있음
- proposal_envelope.why_now_ko가 필요 시 context/hindsight를 같이 surface함
- report_lines_ko에 `맥락/사후:` 줄이 나타남
- trade feedback runtime 테스트가 통과함
