# 기다림 정리 Phase W5 구현 분해 문서

부제: wait surface / runtime / handoff 마감을 실제 작업 단위로 쪼갠 실행 문서

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 W5 close-out 문서 반영 완료

## 1. 문서 목적

이 문서는 `Phase W5. Wait Surface/Handoff 마감`을
바로 실행 가능한 작업 묶음으로 나누기 위한 문서다.

W5는 로직 대수술보다 문서/운영 표면 마감에 가까우므로,
큰 phase를 아래 4개 묶음으로 나눠서 가는 것이 적절하다.


## 2. W5 전체 목표

최종 목표는 한 문장으로 정리할 수 있다.

`새 스레드 또는 운영 점검 시, wait current state를 runtime summary와 handoff 문서만으로 5분 안에 읽을 수 있게 만든다.`


## 3. W5-1. Surface Inventory / Gap Check

### 목표

이미 존재하는 wait surface를 모두 목록화하고,
문서화된 부분과 아직 누락된 부분을 구분한다.

### 대상 파일

- `backend/app/trading_application.py`
- `backend/services/storage_compaction.py`
- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

### 체크리스트

- latest row에서 노출되는 wait field 목록 정리
- slim runtime summary에서 노출되는 wait summary 목록 정리
- detail diagnostics에서 노출되는 wait summary 목록 정리
- symbol summary에서 읽을 수 있는 wait surface 목록 정리
- handoff/checklist에 이미 설명된 field와 빠진 field 구분

### 산출물

- inventory 메모 또는 W5 detail 문서 내 inventory 섹션
- “이미 있다 / 더 적어야 한다 / 중복이다” 분류표

### 완료 기준

- W5-2와 W5-3에서 실제로 다뤄야 할 항목이 확정된다


## 4. W5-2. Runtime Reading Guide Close-out

### 목표

runtime wait summary를 읽는 표준 순서를 문서로 고정한다.

### 대상 파일

- `docs/thread_restart_first_checklist_ko.md`
- 필요시 새 문서:
  - `docs/current_wait_runtime_read_guide_ko.md`

### 핵심 포함 항목

- latest row first look
- recent wait semantic summary second look
- wait energy trace summary third look
- state-decision bridge fourth look
- symbol summary fifth look
- CSV fallback last look

### 함께 정리해야 할 설명

- wait state taxonomy
- hard wait / soft wait 의미
- wait selected rate의 해석
- state는 많지만 decision은 적은 경우의 의미
- energy trace는 높은데 semantic wait는 낮은 경우의 의미

### 완료 기준

- “최근 wait가 많다” 상황에서 어디를 어떤 순서로 볼지 문서 한 장으로 따라갈 수 있다


## 5. W5-3. Handoff / Checklist Sync

### 목표

기존 handoff와 checklist를 W4 이후 실제 구현 상태에 맞게 맞춘다.

### 대상 파일

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

### 체크리스트

- wait section을 별도 흐름으로 정리
- top-level read order에 wait 요약 경로 추가
- symbol summary read path 추가
- symptom-to-cause quick map 보강
- W4 seam fix 이후 skip/runtime parity 의미 반영

### 추천 추가 항목

- `wait state` 대표 그룹별 설명
- `hard wait`를 먼저 의심할 상황
- `wait_selected_rate`가 낮을 때 보는 포인트
- `state_to_decision_counts` 읽는 법

### 완료 기준

- handoff와 checklist만 읽어도 wait 흐름을 설명할 수 있다
- 두 문서가 서로 다른 용어/읽기 순서를 쓰지 않는다


## 6. W5-4. Completion Summary

### 목표

wait 축 전체 close-out을 한 장으로 선언한다.

### 대상 파일

- `docs/current_wait_architecture_reorganization_phase_w5_completion_summary_ko.md`

### 포함 항목

- W1에서 bias owner가 어떻게 분리됐는지
- W2에서 context/input contract가 어떻게 얼었는지
- W3에서 recent summary가 어떻게 생겼는지
- W4에서 end-to-end contract와 seam fix가 어떻게 들어갔는지
- W5에서 읽기 표면과 handoff가 어떻게 닫혔는지
- 이제 왜 다음이 W6인지

### 완료 기준

- wait 축은 “구조 + 관측 + 테스트 + 문서”까지 닫혔다고 선언 가능하다


## 7. 권장 작업 순서

가장 안전한 순서는 아래와 같다.

1. W5-1 inventory/gap check
2. W5-2 runtime reading guide 정리
3. W5-3 handoff/checklist sync
4. W5-4 completion summary 작성


## 8. 권장 검증

W5는 문서 중심 phase지만, 아래 확인은 같이 하는 편이 좋다.

- `runtime_status.detail.json` sample을 실제로 한 번 열어 문서 경로와 필드명이 맞는지 확인
- `runtime_status.json` slim summary에서 wait field alias가 실제 문서와 같은지 확인
- 기존 wait 관련 테스트가 모두 녹색인지 확인

권장 테스트:

- `pytest tests/unit/test_trading_application_runtime_status.py -q`
- `pytest tests/unit/test_entry_wait_end_to_end_contract.py -q`
- `pytest tests/unit/test_entry_service_guards.py -q`


## 9. 이 단계에서 코드 수정이 필요할 수 있는 경우

원칙적으로 W5는 문서/가이드 마감이 중심이다.
다만 아래 경우에는 작은 코드 수정이 허용될 수 있다.

- runtime summary 이름과 문서 이름이 지나치게 어긋나는 경우
- latest row compact alias가 없어서 handoff에서 매번 깊은 nested path를 써야 하는 경우
- symbol summary read path가 없어 문서만으로는 읽기 순서를 만들기 어려운 경우

하지만 이 경우에도
새 owner 도입이나 구조 변경까지 가면 W5 범위를 넘는다.


## 10. 하지 말아야 할 것

- wait 로직 semantics를 다시 수정하는 것
- chart 의미 체계를 새로 바꾸는 것
- exit/manage 로직까지 같이 여는 것
- semantic tuning을 W5 문서 작업과 섞는 것


## 11. 바로 시작할 첫 구현

첫 구현은 W5-3까지 한 번에 연결되는 형태가 효율적이다.

추천 시작점:

1. `thread_restart_first_checklist_ko.md`에 wait runtime read order를 더 선명하게 정리
2. `thread_restart_handoff_ko.md`에 wait 축 전용 섹션 추가 또는 보강
3. 그 다음 `current_wait_architecture_reorganization_phase_w5_completion_summary_ko.md` 작성

즉 W5는 코드보다
`기존 surface를 잘 읽게 만드는 문서 정리`
를 먼저 치는 것이 가장 자연스럽다.
