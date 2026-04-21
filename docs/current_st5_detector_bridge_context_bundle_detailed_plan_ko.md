# ST5 Detector Bridge Context Bundle 상세 계획

## 목표

`ST4`에서 latest runtime row까지 올라온 state-first context contract를
[improvement_log_only_detector.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/improvement_log_only_detector.py)가
직접 계산하지 않고 읽어서 detector evidence bundle로 surface한다.

이번 단계의 핵심은 새 판단 엔진을 만드는 것이 아니라,
detector가 다음 맥락을 같은 언어로 읽게 만드는 것이다.

- `HTF 정렬 / 역행`
- `직전 박스 상태`
- `맥락 충돌`
- `늦은 추격 위험`
- 필요 시 `반복성 share`

## 현재 상태

완료된 선행 단계:
- `ST1` HTF cache / HTF state v1
- `ST2` previous box state v1
- `ST3` context_state_builder v1.2
- `ST4` runtime payload merge

즉 detector 기준으로는 이미 runtime row 안에 context field가 실려 올라오지만,
아직 detector evidence와 registry binding이 이 필드를 핵심 문맥으로 읽어주지 못한다.

## 이번 단계에서 구현할 것

### 1. runtime context field 승격

scene/candle detector row에 아래 state field를 복사한다.

- `htf_alignment_state`
- `htf_alignment_detail`
- `htf_against_severity`
- `previous_box_break_state`
- `previous_box_relation`
- `previous_box_lifecycle`
- `previous_box_confidence`
- `context_conflict_state`
- `context_conflict_flags`
- `context_conflict_intensity`
- `context_conflict_score`
- `context_conflict_label_ko`
- `late_chase_risk_state`
- `late_chase_reason`
- `late_chase_confidence`
- `late_chase_trigger_count`
- `cluster_share_symbol_band`
- `share_context_label_ko`

### 2. detector context bundle 생성

detector row는 raw field만 들고 끝내지 않고 다음 묶음을 만든다.

- `context_bundle_lines_ko`
- `context_bundle_summary_ko`

권장 line 순서:
1. `맥락 충돌`
2. `HTF`
3. `직전 박스`
4. `늦은 추격`
5. `반복성`

### 3. why_now / evidence 연결

- 기존 force/box/wick/recent evidence는 유지
- context bundle line을 evidence 상단에 prepend
- `context_conflict_state != NONE`이면 `why_now_ko` 앞에 짧은 맥락 문장을 붙인다

원칙:
- detector가 HTF를 다시 계산하지 않는다
- detector가 previous box를 다시 계산하지 않는다
- detector는 runtime row의 contract를 읽고 요약만 한다

### 4. registry direct binding 확장

아래 registry key를 detector evidence key에 포함한다.

- `misread:htf_alignment_state`
- `misread:htf_alignment_detail`
- `misread:htf_against_severity`
- `misread:previous_box_break_state`
- `misread:previous_box_relation`
- `misread:previous_box_lifecycle`
- `misread:previous_box_confidence`
- `misread:context_conflict_state`
- `misread:context_conflict_intensity`
- `misread:late_chase_risk_state`
- `misread:late_chase_reason`

primary registry key 우선순위도 context 중심으로 재정렬한다.

## 이번 단계에서 하지 않을 것

- HTF로 BUY/SELL 방향을 뒤집지 않음
- previous box로 entry 차단하지 않음
- share를 direction authority로 쓰지 않음
- reverse pattern detector를 대규모 refactor하지 않음
- notifier 템플릿을 본격 수정하지 않음

## 완료 기준

- scene/candle detector row에 context state field가 직접 들어감
- detector row에 `context_bundle_lines_ko`, `context_bundle_summary_ko`가 생김
- report/check surface에서 `HTF / 직전 박스 / 맥락 충돌 / 늦은 추격` line이 보임
- registry binding이 새 context key까지 포함해도 `binding_ready = true`
- 테스트가 snapshot 수준에서 통과함
