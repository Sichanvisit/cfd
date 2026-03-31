# 기다림 정리 Phase W3 구현 분해 문서

부제: W3 runtime observability를 실제 작업 단위로 쪼개는 구현 로드맵

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 구현 완료

## 1. 문서 목적

이 문서는
`Phase W3. Wait Runtime Observability`
를 실제 구현 가능한 작업 단위로 쪼개기 위한 문서다.

여기서의 핵심은
새로운 wait rule을 만드는 것이 아니라,
이미 row에 남고 있는 wait semantic을
recent diagnostics와 slim surface에서 읽히게 마감하는 것이다.


## 2. 현재 기준 전제

W3에 들어가기 전에 이미 확보된 전제는 아래다.

- row에 `entry_wait_state`, `entry_wait_hard`, `entry_wait_reason`가 남는다
- row에 `entry_wait_selected`, `entry_wait_decision`이 남는다
- row에 compact `entry_wait_context_v1`, `entry_wait_bias_bundle_v1`, `entry_wait_state_policy_input_v1`가 남는다
- recent diagnostics에는 bias/policy/scene/threshold shift 요약이 이미 있다
- latest signal compact row에도 wait surface 일부가 이미 있다

즉 W3는
배관이 없는 상태에서 시작하는 작업이 아니라,
`이미 저장되는 truth를 운영 summary로 재집계하는 작업`
이다.


## 3. 가장 먼저 봐야 할 파일

### 핵심 구현 파일

- `backend/app/trading_application.py`

W3의 본체는 여기다.
recent window를 읽고 집계하는 함수들이 이미 있으므로,
W3 semantic summary도 같은 레이어에서 붙는 것이 가장 자연스럽다.

### 이미 연결된 row source

- `backend/services/entry_try_open_entry.py`
- `backend/services/entry_engines.py`
- `backend/services/storage_compaction.py`

이 세 파일은 W3의 “새로운 집계 원천”을 다시 만드는 곳이 아니다.
이미 있는 row field와 compact field가 무엇인지 확인하는 참조점이다.

### 핵심 테스트 파일

- `tests/unit/test_trading_application_runtime_status.py`
- `tests/unit/test_storage_compaction.py`


## 4. W3 구현을 3단으로 나누는 이유

W3는 W1/W2만큼 깊은 구조 리팩터링은 아니지만,
한 번에 크게 넣으면 summary 이름과 의미가 섞일 수 있다.

따라서 아래 3단으로 가는 편이 가장 안전하다.

1. semantic summary shape를 먼저 고정한다
2. runtime aggregation을 붙인다
3. handoff/tests를 마감한다


## 5. W3-1. Semantic Summary Shape Freeze

### 목표

recent diagnostics에 추가할 wait semantic summary들의 이름과 shape를 먼저 고정한다.

### 이 단계에서 확정할 것

#### A. `wait_state_semantic_summary`

권장 필드:

- `wait_state_counts`
- `hard_wait_state_counts`
- `wait_reason_counts`
- `hard_wait_true_rows`

#### B. `wait_decision_summary`

권장 필드:

- `wait_decision_counts`
- `wait_selected_rows`
- `wait_skipped_rows`
- `wait_selected_rate`

#### C. `wait_state_decision_bridge_summary`

권장 필드:

- `state_to_decision_counts`
- `selected_by_state_counts`
- `hard_wait_selected_rows`
- `soft_wait_selected_rows`

### 대상 파일

- `backend/app/trading_application.py`
- `tests/unit/test_trading_application_runtime_status.py`

### 완료 기준

- summary 이름이 고정된다
- window summary와 symbol summary에 같은 semantic이 들어갈지 결정된다
- top-level slim surface에 어떤 summary를 꺼낼지도 정해진다


## 6. W3-2. Runtime Aggregation Implementation

### 목표

실제 recent diagnostics 집계 코드에 W3 semantic summary를 추가한다.

### 구현 포인트

#### 6-1. CSV parsing 재사용

지금 row에는 이미 아래 값이 남는다.

- wait state
- hard wait 여부
- wait reason
- wait selected 여부
- wait decision

따라서 parser를 새로 설계할 필요는 없고,
existing recent row buffer에 이 값들을 읽어 넣으면 된다.

#### 6-2. window-level bucket 추가

권장 bucket:

- wait state semantic bucket
- wait decision bucket
- state-decision bridge bucket

#### 6-3. symbol-level bucket 추가

window summary만 보면
실제 운영에서는 다시 symbol 기준으로 CSV를 찾게 된다.

따라서 symbol summary에도 아래가 같이 있어야 한다.

- per-symbol wait state counts
- per-symbol decision counts
- per-symbol bridge summary

#### 6-4. slim top-level default summary 추가

지금 top-level에는 recent stage, blocked reason, display ready가 바로 나온다.
W3 이후에는 아래도 같이 바로 읽히는 편이 좋다.

- `recent_wait_state_semantic_summary`
- `recent_wait_decision_summary`
- `recent_wait_state_decision_bridge_summary`

### 대상 파일

- `backend/app/trading_application.py`

### 권장 구현 순서

1. row parsing field 추가
2. empty bucket helper 추가
3. accumulate helper 추가
4. build summary helper 추가
5. window summary 연결
6. symbol summary 연결
7. slim top-level 연결

### 완료 기준

- detail window에 새 semantic summary가 보인다
- symbol summary에도 보인다
- slim default surface에도 보인다


## 7. W3-3. Read Path and Regression Close-Out

### 목표

운영에서 실제로 “읽히는 단계”까지 닫는다.

### 작업 내용

#### 7-1. runtime tests 추가

`test_trading_application_runtime_status.py`에서 아래를 고정한다.

- wait state counts
- hard wait state counts
- wait decision counts
- selected rate
- state->decision bridge counts
- symbol summary parity

#### 7-2. read path 문서 sync

아래 문서 중 최소 1개 이상은 업데이트하는 편이 좋다.

- `thread_restart_handoff_ko.md`
- `thread_restart_first_checklist_ko.md`

핵심은
“recent wait semantic summary를 어떻게 읽는가”
를 5분 안에 따라갈 수 있게 쓰는 것이다.

#### 7-3. W3 completion note 작성

W3가 끝나면
W1 completion summary처럼
짧은 완료 정리 문서 한 장이 있으면 다음 phase로 넘어가기 편하다.

### 대상 파일

- `tests/unit/test_trading_application_runtime_status.py`
- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

### 완료 기준

- 테스트가 추가돼 있다
- handoff/checklist에 읽는 법이 적혀 있다
- 새 스레드에서 CSV를 덜 뒤져도 된다


## 8. 지금 W3에서 건드리지 말아야 할 것

W3 범위를 지키기 위해 아래는 이번 구현에서 제외하는 것이 좋다.

- alerting
- 어제/오늘 비교 대시보드
- chart correlation view
- exit/manage observability

이 네 가지를 같이 넣으면
W3가 “wait semantic summary 마감”이 아니라
전체 observability 확장으로 번진다.


## 9. 권장 실제 실행 순서

지금 바로 작업에 들어간다면 아래 순서를 권장한다.

1. `W3-1` summary shape freeze
2. `W3-2` trading_application recent aggregation 구현
3. `W3-2` symbol summary / slim top-level 연결
4. `W3-3` runtime status tests 추가
5. `W3-3` handoff/checklist sync


## 10. 구현 난이도와 리스크

### 난이도

중간 정도다.

이유:

- 새 rule을 만드는 작업은 아니다
- 하지만 summary shape를 잘못 잡으면 나중에 읽는 면이 다시 흔들릴 수 있다

### 주요 리스크

- state summary와 decision summary 이름이 겹쳐 의미가 흐려질 수 있음
- bridge summary를 너무 자세하게 잡아 summary가 오히려 무거워질 수 있음
- symbol summary를 빼먹으면 운영자가 다시 CSV를 보게 됨

### 리스크를 줄이는 방법

- count 중심으로 시작한다
- 비율/상관 통계는 최소만 넣는다
- window summary와 symbol summary의 shape를 가능한 한 맞춘다


## 11. W3 이후 자연스러운 다음 단계

W3가 끝나면 다음은 아래 순서가 자연스럽다.

1. `W4` end-to-end contract tests
2. `W5` handoff/runtime 읽기 가이드 마감
3. `W6` exit/manage 연결 준비

즉 W3는
wait observability를 닫고,
그 다음 테스트와 handoff를 더 단단하게 가는
중간 마감 단계로 보는 것이 맞다.
