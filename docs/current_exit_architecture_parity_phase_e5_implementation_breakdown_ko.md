# 청산 구조 정렬 Phase E5 구현 분해

작성일: 2026-03-29 (KST)  
상태: 완료

## 1. E5는 close-out phase다

E5는 새 청산 로직을 더 잘게 쪼개는 phase가 아니다.
이미 나눠진 owner와 surface를 아래 순서로 닫는 phase다.

1. continuity test
2. runtime / handoff read path
3. lifecycle summary

## 2. E5-1 continuity / contract test close-out

### 목표

대표 청산 장면이 아래 경로를 지나도 의미가 바뀌지 않는지 검증한다.

- exit wait state surface
- exit taxonomy
- trade history row
- latest runtime compact row
- recent exit runtime summary

### 대상 파일

- `tests/unit/test_exit_end_to_end_contract.py`
- `tests/unit/test_trading_application_runtime_status.py`

### 장면 기준

- confirm wait
- recovery wait
- reverse now
- exit pressure / exit now

### 완료 기준

- state family / decision family / bridge status가 row와 runtime summary에서 모두 일치한다.
- slim runtime latest signal에서도 compact exit surface가 보인다.

## 3. E5-2 runtime / handoff close-out

### 목표

청산 recent summary를 새 스레드에서 5분 안에 읽을 수 있게 가이드를 고정한다.

### 대상 파일

- `docs/current_exit_runtime_read_guide_ko.md`
- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

### 완료 기준

- slim에서 먼저 볼 필드가 정리돼 있다.
- detail에서 `state -> decision -> bridge` 순서가 정리돼 있다.
- handoff / checklist에서 exit guide로 바로 내려갈 수 있다.

## 4. E5-3 lifecycle summary

### 목표

entry / wait / exit를 각각 따로 읽는 것이 아니라 한 생애주기로 읽게 만든다.

### 대상 파일

- `docs/current_entry_wait_exit_lifecycle_summary_ko.md`

### 완료 기준

- entry / wait / exit 각각의 역할이 한 장에 정리돼 있다.
- 각 phase를 runtime에서 어디서 읽는지 함께 적혀 있다.
- 새 스레드에서 “지금 어느 구간이 문제인지” 방향을 바로 잡을 수 있다.

## 5. 권장 검증

아래 정도면 E5 close-out 검증으로 충분하다.

- `pytest tests/unit/test_exit_end_to_end_contract.py -q`
- `pytest tests/unit/test_trading_application_runtime_status.py -q`
- `pytest tests/unit/test_storage_compaction.py -q`

## 6. E5 이후 자연스러운 다음 축

E5가 끝나면 청산 parity의 코어는 닫힌다.
그다음은 새 구조 공사보다 아래 후속 트랙이 더 자연스럽다.

- lifecycle-wide correlation view
- alerting / dashboard
- time-series comparison
