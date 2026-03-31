# 기다림 정리 Phase W4 구현 분해 문서

부제: wait end-to-end contract tests를 실제 작업 단위로 쪼개는 구현 로드맵

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 W4-1/W4-3 첫 슬라이스 구현 완료

## 1. 문서 목적

이 문서는
`Phase W4. Wait End-to-End Contract Test 확장`
을 실제 구현 가능한 작업 단위로 쪼개기 위한 문서다.

이번 단계의 목적은
wait rule을 새로 만드는 것이 아니라,
현재 이미 존재하는 wait contract를
`scene -> state -> decision -> row/runtime -> recent summary`
까지 테스트로 잠그는 것이다.


## 2. 현재 시작점

W4 시작 시점에서 이미 확보된 것은 아래다.

- bias owner direct tests
- wait state policy direct tests
- wait decision policy direct tests
- `WaitEngine` unit tests
- runtime status recent wait semantic summary tests
- handoff/checklist read path 정리

즉 W4는 바닥부터 시작하는 단계가 아니라,
이미 있는 테스트 층 사이의 공백을 메우는 단계다.


## 3. W4를 4단으로 나누는 이유

W4를 한 파일에 한 번에 크게 넣으면
어느 단계의 회귀를 잡는 테스트인지 흐려진다.

따라서 아래 4단으로 가는 편이 가장 안전하다.

1. 대표 scene fixture를 고정한다
2. orchestration continuity를 잠근다
3. runtime aggregation parity를 잠근다
4. 회귀 matrix와 읽기 기준을 마감한다


## 4. W4-1. Scenario Fixture Freeze

### 목표

end-to-end contract test에서 반복 사용할 대표 장면을 고정한다.

### 권장 대표 장면

#### A. helper soft block 장면

의도:

- blocked 성격이 분명하다
- helper soft block trace가 남는다
- hard/soft wait 해석이 같이 걸린다

기대 결과:

- wait state는 helper soft block 계열
- wait decision은 helper block 계열
- recent summary에서 helper soft block counts가 올라간다

#### B. probe candidate 장면

의도:

- probe scene 기반 wait 의미를 잠근다
- scene-specific wait가 aggregation까지 이어지는지 본다

기대 결과:

- wait state는 probe candidate 계열
- wait decision은 probe candidate 계열
- bridge summary에서 probe candidate -> wait 계열 연결이 보인다

#### C. center but skip 장면

의도:

- state는 잡히지만 decision 단계에서 wait가 선택되지 않는 경우를 잠근다

기대 결과:

- wait state는 center
- wait decision은 skip
- selected rate는 낮게 반영된다

#### D. none/clean ready control 장면

의도:

- wait가 실제로 거의 개입하지 않는 control row를 둔다
- recent summary의 baseline row를 만든다

기대 결과:

- wait state는 none
- wait decision은 skip

### 대상 파일

- 새 파일 권장: `tests/unit/test_entry_wait_end_to_end_contract.py`

### 완료 기준

- 대표 장면 4개가 fixture/helper 형태로 고정된다
- 이후 W4-2, W4-3에서 같은 fixture를 재사용할 수 있다


## 5. W4-2. Orchestration Continuity Test

### 목표

한 장면이 wait state와 wait decision을 거쳐
row/runtime payload까지 같은 의미로 남는지 잠근다.

### 권장 대상

- `backend/services/entry_try_open_entry.py`
- `tests/unit/test_entry_wait_end_to_end_contract.py`

### 권장 검증 포인트

#### 5-1. state parity

장면별로 기대한 wait state가 그대로 저장되는지 본다.

#### 5-2. decision parity

장면별로 기대한 wait decision과 selected flag가 그대로 저장되는지 본다.

#### 5-3. metadata parity

아래 contract가 row/runtime path에서도 유지되는지 본다.

- wait context
- wait bias bundle
- wait state policy input
- wait energy traces

#### 5-4. compact runtime row parity

compact surface에서도
wait policy state / reason / release source / threshold shift가
동일한 장면 해석을 가리키는지 본다.

### 완료 기준

- engine 내부 state/decision과 저장 표면 값이 같은 의미를 가진다
- orchestration 경로에서 wait contract 누락이 없음을 장면별로 확인한다


## 6. W4-3. Runtime Aggregation Continuity Test

### 목표

같은 장면 세트를 recent diagnostics에 넣었을 때
window summary, symbol summary, slim default summary가
같은 truth를 가리키는지 잠근다.

### 권장 대상

- `backend/app/trading_application.py`
- `tests/unit/test_trading_application_runtime_status.py`
- 필요하면 `tests/unit/test_entry_wait_end_to_end_contract.py`

### 권장 검증 포인트

#### 6-1. wait state semantic parity

- wait state counts
- hard wait state counts
- wait reason counts

#### 6-2. wait decision parity

- wait decision counts
- wait selected rows
- wait selected rate

#### 6-3. state-decision bridge parity

- state -> decision counts
- selected by state counts

#### 6-4. symbol/detail/slim parity

같은 장면 세트를 넣었을 때

- detail window
- symbol summary
- slim top-level recent summary

가 서로 같은 의미를 가리키는지 본다.

### 완료 기준

- detail과 slim이 같은 truth를 가리킨다
- symbol summary가 window summary와 같은 규칙으로 집계된다


## 7. W4-4. Regression Matrix Close-Out

### 목표

새 wait rule이 붙어도 어느 테스트가 어떤 회귀를 잡는지 분명하게 만든다.

### 권장 작업

#### 7-1. 대표 장면 표 정리

문서 또는 테스트 파일 상단에
scene -> expected state -> expected decision -> key runtime summary
매핑을 짧게 적어 둔다.

#### 7-2. 테스트 역할 분리

역할을 아래처럼 나누는 편이 좋다.

- helper direct tests: owner별 계산 정확성
- `WaitEngine` tests: state/decision 본문 정확성
- end-to-end contract test: 단계 연속성
- runtime status test: recent aggregation 정확성

#### 7-3. 다음 phase 연결 메모

W4가 끝나면
W5나 exit/manage 쪽으로 갈 때
어떤 scene을 기준 fixture로 재사용할지 짧은 메모를 남긴다.

### 완료 기준

- 새로운 wait rule 추가 시 먼저 확인할 테스트 레이어가 분명하다
- end-to-end contract 테스트의 역할이 helper/unit 테스트와 구분된다


## 8. 권장 파일 배치

### 새로 추가 권장

- `tests/unit/test_entry_wait_end_to_end_contract.py`

### 기존 파일 강화

- `tests/unit/test_trading_application_runtime_status.py`

### 직접 수정 가능성이 높은 구현 파일

- `backend/services/entry_try_open_entry.py`
- `backend/services/storage_compaction.py`
- `backend/app/trading_application.py`


## 9. 가장 추천하는 실제 구현 순서

1. `W4-1` 대표 scene fixture를 먼저 만든다
2. 같은 fixture로 `W4-2` orchestration continuity 테스트를 붙인다
3. 같은 fixture 의미를 `W4-3` runtime aggregation assertions로 확장한다
4. 마지막에 `W4-4` 역할 표와 completion note를 남긴다

이 순서가 좋은 이유는
scene truth를 먼저 얼려야
orchestration과 aggregation 테스트가 같은 언어를 쓸 수 있기 때문이다.


## 10. W4 완료 선언 조건

W4는 아래 상태가 되면 완료로 본다.

- 대표 장면 fixture가 고정돼 있다
- end-to-end contract 전용 테스트 파일이 생겨 있다
- state/decision/row/runtime/recent summary 연속성이 잠겨 있다
- detail/symbol/slim parity가 테스트로 잠겨 있다
- 다음 phase에서 재사용할 기준 scene이 정리돼 있다
