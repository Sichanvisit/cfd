# State25 Promotion Gate Rollback Implementation Roadmap

## 목표

이 문서는 `AI4`를 실제 작업 순서로 잘라 놓은 구현 로드맵이다.

쉽게 말하면:

- 무엇부터 만들고
- 무엇까지 검증하면
- 다음 AI5로 넘어갈 수 있는지

를 적는다.

## AI4 단계 분해

### PG1. Offline Gate Ingestion

할 일:

- latest candidate manifest 읽기
- compare report 읽기
- promotion decision 읽기

완료 기준:

- AI3 산출물만으로 `hold_offline / shadow_only / promote_review_ready` 계열 1차 해석이 가능하다

### PG2. Step9 Readiness Bind

할 일:

- Step 9 watch report 읽기
- `execution_handoff_ready`, `blocker_codes`, `rows_to_target` 연결

완료 기준:

- 후보가 좋아도 Step 9가 준비 안 되면 `hold_step9`로 떨어진다

### PG3. Canary Evidence Contract

할 일:

- canary evidence 필드 계약 정의
- `rows_observed`, `utility_delta`, `must_release_delta`, `bad_exit_delta`, `wait_drift_delta`, `symbol_skew_delta`, `watchlist_confusion_delta`를 읽는 구조 만들기

완료 기준:

- canary evidence가 없으면 `shadow_ready`
- 있되 부족하면 `collect_more_canary_rows`
- 충분하면 promote / rollback 분기가 가능하다

### PG4. Rollback Rule Set

할 일:

- utility 악화
- must_release 증가
- bad_exit 증가
- wait drift 증가
- symbol skew 확대
- watchlist confusion 증가

이 6개를 rollback trigger로 묶는다

완료 기준:

- canary failure가 들어오면 `rollback_recommended`를 자동으로 띄운다

### PG5. Human Summary

할 일:

- 사람이 바로 읽는 md summary 생성
- gate stage, blockers, warnings, rollback reasons, next actions를 한 장으로 요약

완료 기준:

- json 안 열고 md만 봐도 지금 candidate 상태를 읽을 수 있다

### PG6. Latest Pointer

할 일:

- 최신 gate 결과를 루트 latest json으로 고정

완료 기준:

- 다음 단계가 `latest_gate_report.json`만 읽어도 된다

## 이번 구현 파일

- `backend/services/teacher_pattern_promotion_gate.py`
- `scripts/teacher_pattern_promotion_gate_report.py`
- `docs/current_state25_promotion_gate_rollback_design_ko.md`
- `docs/current_state25_promotion_gate_rollback_implementation_roadmap_ko.md`

## 실행 명령

기본 실행:

```powershell
python scripts/teacher_pattern_promotion_gate_report.py
```

이 명령은 아래 순서로 동작한다.

1. latest candidate manifest 읽기
2. compare / promotion decision 읽기
3. Step 9 watch 읽기
4. optional canary evidence 읽기
5. gate stage 판단
6. json / md 결과 저장

## 출력 위치

candidate 폴더:

- `teacher_pattern_promotion_gate_report.json`
- `teacher_pattern_promotion_gate_report.md`

candidate root:

- `latest_gate_report.json`

## 해석 방법

### 그냥 보류

- `hold_offline`
- `hold_step9`

의미:

- 아직 live promote를 볼 단계가 아니다

### 관찰 먼저

- `shadow_only`
- `shadow_ready`

의미:

- 후보는 쓸 만할 수 있지만, 아직 canary evidence가 더 필요하다

### 올릴 수 있음

- `promote_ready`

의미:

- AI5 bounded execution integration으로 넘어갈 수 있다

### 되돌려야 함

- `rollback_recommended`

의미:

- canary에서 나빠진 신호가 확인됐다

## AI4 1차 완료 기준

아래가 되면 AI4 1차는 완료다.

1. latest candidate 기준 gate report를 자동 생성한다
2. Step 9 readiness를 gate에 반영한다
3. canary evidence contract를 읽는다
4. rollback trigger를 자동 판정한다
5. md summary로 사람이 바로 읽을 수 있다

## AI5로 넘어가는 조건

AI4 결과가 아래면 AI5로 넘어갈 수 있다.

- `gate_stage = promote_ready`
- `blockers = []`
- rollback reason 없음

그 전까지는:

- `shadow_ready`면 shadow / canary만
- `hold_*`면 current baseline 유지
- `rollback_recommended`면 되돌림 유지
