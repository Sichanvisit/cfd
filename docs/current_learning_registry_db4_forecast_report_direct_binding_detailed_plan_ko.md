# DB4. forecast/report Direct Binding 상세 계획

## 목표

forecast 보조 판단 축이 detector/proposal과 같은 `registry_key` 언어를 쓰게 만들고,
report 계열이 forecast 항목을 중앙 레지스트리 기준 label로 바로 읽을 수 있게 만든다.

이번 단계의 핵심은 forecast 계산식을 중앙화하는 것이 아니다.
계산은 그대로 두고,

- 어떤 forecast 항목을 보고 있는지
- 그 항목을 한국어로 어떻게 읽을지
- report에서 어떤 줄로 노출할지

를 중앙 레지스트리 기준으로 고정하는 단계다.

## 왜 지금 이 단계인가

- `DB1` detector가 evidence key를 직접 싣기 시작했다.
- `DB2` weight review가 target key를 직접 읽기 시작했다.
- `DB3` proposal runtime이 detector evidence와 promotion policy를 같은 key 언어로 잇기 시작했다.

이제 forecast/report만 따로 raw field 이름을 계속 쓰면,
runtime 보조 판단 축이 나머지 학습/제안 언어와 분리된 채 남는다.

따라서 `DB4`는 forecast를 새로 똑똑하게 만드는 작업이 아니라,
이미 쓰고 있는 forecast 보조축을 같은 언어 체계 안으로 넣는 작업이다.

## 이번 단계의 바인딩 원칙

### 1. forecast summary는 composite payload로 본다

`forecast_runtime_summary_v1`는 단일 키 하나가 아니라
여러 forecast 항목을 묶은 composite payload다.

따라서 primary key는 아래로 잡는다.

- `forecast:decision_hint`

하지만 실제 relation은 아래 전체 field를 같이 싣는다.

- `forecast:confirm_side`
- `forecast:confirm_score`
- `forecast:false_break_score`
- `forecast:continuation_score`
- `forecast:continue_favor_score`
- `forecast:fail_now_score`
- `forecast:wait_confirm_gap`
- `forecast:hold_exit_gap`
- `forecast:same_side_flip_gap`
- `forecast:belief_barrier_tension_gap`
- `forecast:decision_hint`

### 2. entry/wait/exit bridge는 forecast 보조 판단의 downstream surface다

`entry_wait_exit_bridge_v1`도 forecast 카테고리 key를 직접 싣는다.

- `forecast:prefer_entry_now`
- `forecast:prefer_wait_now`
- `forecast:prefer_hold_if_entered`
- `forecast:prefer_fast_cut_if_entered`

즉 bridge는 별도 임시 언어를 만들지 않고,
forecast category 안에서 직접 연결된다.

### 3. report용 줄은 registry label을 우선 사용한다

report line은 자유 문장 영역이지만,
항목 표시명은 중앙 레지스트리의 `label_ko`를 우선 사용한다.

예:

- `확정 우세 방향: SELL`
- `가짜 돌파 경계 점수: 0.49`
- `지금 대기 선호: 예`

## 구현 범위

대상 파일:

- [forecast_state25_runtime_bridge.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/forecast_state25_runtime_bridge.py)

이번 단계에서 한다:

- resolver import
- forecast summary direct binding
- entry/wait/exit bridge direct binding
- top-level bridge에 combined report lines 추가
- audit에서 forecast direct binding 잡히게 연결

이번 단계에서 하지 않는다:

- forecast scoring 변경
- decision_hint 규칙 변경
- entry/wait/hold/fast-cut 판단식 변경

## 주요 필드 계약

`forecast_runtime_summary_v1`와 `entry_wait_exit_bridge_v1`는 가능하면 아래를 가진다.

- `registry_key`
- `registry_label_ko`
- `registry_binding_mode`
- `registry_binding_version`
- `registry_binding_ready`
- `evidence_registry_keys`
- `target_registry_keys`
- `evidence_bindings`
- `target_bindings`
- `registry_report_lines_ko`

top-level `forecast_state25_runtime_bridge_v1`는 추가로 아래를 가진다.

- `forecast_registry_report_lines_ko`

## 완료 조건

- forecast summary payload가 direct binding 필드를 가진다
- entry/wait/exit bridge payload가 direct binding 필드를 가진다
- top-level bridge가 registry 기반 report lines를 가진다
- audit에서 `forecast_direct_binding = true`가 된다

## 기대 효과

- detector/proposal/report가 같은 forecast key를 같은 한국어로 읽는다
- 나중에 forecast 관련 제안이나 hindsight를 붙일 때도 raw field 이름 대신 registry key로 연결할 수 있다
- “forecast가 지금 뭘 밀고 있는지”를 report에서 더 또렷하게 보여줄 수 있다
