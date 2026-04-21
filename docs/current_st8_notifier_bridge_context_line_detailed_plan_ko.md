# ST8 Notifier Bridge Context Line 상세 계획

## 목표

`ST4`에서 runtime payload까지 올린 state-first context contract와
`ST5`에서 detector가 읽기 시작한 context bundle을,
[notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)에서
과하지 않은 한 줄 맥락 요약으로 연결한다.

이번 단계의 목적은 DM을 길게 만드는 것이 아니라,
사용자가 entry / wait / reverse 메시지를 볼 때
`왜 이 방향이 불편한지`, `왜 늦은 추격처럼 보이는지`를
즉시 읽을 수 있게 만드는 것이다.

## 현재 상태

완료된 선행 단계:
- `ST1` HTF cache / HTF state v1
- `ST2` previous box state v1
- `ST3` context_state_builder v1.2
- `ST4` runtime payload context merge
- `ST5` detector bridge context bundle

즉 runtime row에는 이미:
- `htf_alignment_state`
- `htf_alignment_detail`
- `htf_against_severity`
- `previous_box_break_state`
- `previous_box_relation`
- `late_chase_risk_state`
- `late_chase_reason`
- `cluster_share_symbol_band`
- `share_context_label_ko`
- `context_conflict_state`
- `context_conflict_label_ko`

같은 필드가 올라와 있다.

하지만 notifier는 아직 이 필드를 직접 읽어
짧은 `맥락:` 한 줄로 surface하지 못한다.

## 이번 단계에서 구현할 것

### 1. Runtime Context Line Builder

[notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)에
얇은 helper를 추가한다.

핵심 helper:
- `_build_runtime_htf_context_summary(...)`
- `_build_runtime_previous_box_context_summary(...)`
- `_build_runtime_late_chase_context_summary(...)`
- `_build_runtime_share_context_summary(...)`
- `_build_runtime_context_line(...)`

원칙:
- detector helper를 그대로 복붙하지 않는다
- notifier에 필요한 짧은 line만 만든다
- runtime row를 직접 읽는다

### 2. Context Line 우선순위

노출 순서는 다음을 따른다.
1. `HTF`
2. `직전 박스`
3. `늦은 추격`
4. 필요할 때만 `반복성`

즉 notifier의 기본 맥락 한 줄은:

`맥락: <HTF> | <직전 박스> | <늦은 추격>`

형태를 우선한다.

### 3. Entry / Wait / Reverse Formatter 연결

다음 formatter에만 붙인다.
- `format_entry_message(...)`
- `format_wait_message(...)`
- `format_reverse_message(...)`

공통 원칙:
- context line이 비어 있으면 출력하지 않음
- 기존 `위/아래 힘`, `구조 정합`, `scene` 라인은 유지
- `맥락:`은 한 줄만 추가

### 4. Fallback 규칙

직접적인 `HTF / previous box / late chase` 요약이 비어 있으면,
`context_conflict_label_ko`를 fallback으로 사용한다.

즉 notifier는:
- 가능하면 구조화된 3축 요약을 쓰고
- 그게 안 되면 upstream conflict label을 읽는다

## 이번 단계에서 하지 않을 것

- HTF로 BUY/SELL 방향을 뒤집지 않음
- previous box만으로 진입/대기를 차단하지 않음
- share를 방향 authority로 쓰지 않음
- detector context bundle을 notifier로 통째 복사하지 않음
- 긴 설명 paragraph를 추가하지 않음

## 완료 기준

- entry / wait / reverse 메시지에 `맥락:` 한 줄이 붙을 수 있음
- 맥락 line은 최대 3파트만 노출
- `HTF / 직전 박스 / 늦은 추격`이 우선 surface됨
- context가 없으면 기존 메시지 포맷이 유지됨
- notifier 단위 테스트가 통과함
