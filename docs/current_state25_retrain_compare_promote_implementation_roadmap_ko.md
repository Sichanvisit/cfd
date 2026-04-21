# State25 Retrain Compare Promote Implementation Roadmap

## 목표

이 문서는 `AI3`를 실제 작업 순서로 쪼갠 구현 로드맵이다.

쉽게 말하면:

- 지금 무엇부터 만들고
- 무엇을 어디까지 검증하면
- 다음 AI4로 넘어갈 수 있는지를 적는다

## AI3 단계 분해

### RCP1. Candidate Run Skeleton

할 일:

- candidate root 디렉터리 정의
- `candidate_id` 생성
- baseline retrain 결과를 candidate 전용 폴더에 저장
- manifest 생성

완료 기준:

- 명령 1개로 candidate bundle이 별도 디렉터리에 저장된다

### RCP2. Compare Report

할 일:

- current baseline metrics 로드
- candidate metrics 로드
- `group_task / pattern_task / economic_total_task / wait_quality_task` 비교
- delta 계산

완료 기준:

- compare report json이 생성된다
- task별 `candidate / reference / delta`가 보인다

### RCP3. Promotion Decision Skeleton

할 일:

- regression blocker 정의
- improvement 신호 정의
- `hold_regression / hold_no_material_gain / promote_review_ready / shadow_only_first_candidate` 판정

완료 기준:

- promote decision json이 생성된다
- 추천 next step이 같이 보인다

### RCP4. Human Summary

할 일:

- 사람이 바로 읽을 md summary 생성
- candidate_id, baseline_ready, supported pattern, economic ready, compare delta, decision 표시

완료 기준:

- summary md 1장으로 candidate 상태를 읽을 수 있다

### RCP5. Operational Hook

할 일:

- 실행 명령 정리
- latest manifest 포인터 생성
- 이후 AI4 gate가 읽을 수 있는 경로 고정

완료 기준:

- 다음 단계가 `latest_candidate_run.json`만 읽어도 된다

## 이번 구현 결과물

이번 단계에서 만들어질 파일:

- `backend/services/teacher_pattern_candidate_pipeline.py`
- `scripts/teacher_pattern_candidate_retrain_compare_promote.py`
- `docs/current_state25_retrain_compare_promote_design_ko.md`
- `docs/current_state25_retrain_compare_promote_implementation_roadmap_ko.md`

## 실행 명령

기본 실행:

```powershell
python scripts/teacher_pattern_candidate_retrain_compare_promote.py
```

이 명령이 하는 일:

1. closed history 읽기
2. candidate retrain 실행
3. current baseline과 compare
4. promote decision skeleton 생성
5. md/json summary 저장

## 해석 방법

### 바로 좋은 신호

- `decision = promote_review_ready`
- `blockers = []`
- primary task delta가 음수 아님

### 그냥 보류

- `decision = hold_no_material_gain`
- regression은 없는데 개선도 크지 않음

### 위험 신호

- `decision = hold_regression`
- primary task regression blocker 존재

## AI3 완료 기준

아래가 되면 AI3 1차는 완료다.

1. candidate retrain이 별도 폴더에 저장됨
2. compare report가 생성됨
3. promotion decision skeleton이 생성됨
4. 사람이 md summary로 빠르게 읽을 수 있음

## AI4로 넘어가는 조건

아래가 되면 AI4 상세 설계로 넘어가면 된다.

- candidate run이 반복 가능
- compare 결과가 안정적으로 남음
- decision skeleton이 일관되게 생성됨
- `promote_review_ready`와 `hold_regression`을 구분할 수 있음

## 한 줄 요약

AI3 구현 로드맵은 `후보 만들기 -> 현재와 비교하기 -> 올려볼 가치가 있는지 표시하기`를 자동화하는 순서다.
