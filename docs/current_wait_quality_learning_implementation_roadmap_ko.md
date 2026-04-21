# Wait 품질 학습 구현 로드맵

작성일: 2026-04-03 (KST)

## 1. 목표

이 로드맵의 목표는
`good wait / bad wait`를 entry-side에서 직접 판단하는 shadow audit를 만들고,
그 결과를 state25 / ML 실험으로 연결하는 것이다.

이번 턴에서 끝난 것은 `WQ4` 기본 enrichment까지로 본다.

## 2. 현재 상태

이미 있음:

- wait runtime architecture
- wait state / decision taxonomy
- wait context / bias contract
- runtime wait surface
- exit/loss 쪽 wait quality 보조 라벨

이번 턴에 추가함:

- `backend/services/entry_wait_quality_audit.py`
- `tests/unit/test_entry_wait_quality_audit.py`
- `backend/services/entry_wait_quality_replay_bridge.py`
- `scripts/entry_wait_quality_replay_report.py`
- `backend/services/entry_wait_quality_seed_enrichment.py`
- `scripts/backfill_entry_wait_quality_learning_seed.py`

즉 지금은 `entry-side wait quality owner + replay bridge + on-demand report + closed history enrichment`의 기본 뼈대가 생긴 상태다.

## 3. 단계별 로드맵

### WQ1. Owner와 contract 세우기

상태:

- 완료

목표:

- 새 owner 이름 고정
- label family 고정
- context / result / summary contract 고정

파일:

- `backend/services/entry_wait_quality_audit.py`
- `tests/unit/test_entry_wait_quality_audit.py`

완료 기준:

- 네 가지 질문을 다루는 label family가 있음
- synthetic unit test로 기본 판정이 가능함

### WQ2. Replay input bridge 만들기

상태:

- 기본 구현 완료

목표:

- 실제 `entry_decisions.csv` wait row를 audit 입력으로 바꾸는 bridge 작성
- 같은 symbol, 같은 side의 next entry row 연결
- 가능한 경우 next closed trade 연결

구현 파일:

- `backend/services/entry_wait_quality_replay_bridge.py`
- `scripts/entry_wait_quality_replay_report.py`

해야 할 일:

- wait-selected rows 추출
- same-side next entry 찾기
- same-side next closed trade 찾기
- anchor price fallback 규칙 정의

현재 완료 범위:

- wait-selected / wait outcome row 추출
- 중복 wait row dedupe
- same-side next entered row 연결
- exact key 우선 next closed trade 연결
- future bar companion CSV 연결

남은 보강:

- bridge 정확도 샘플 검토
- anchor price fallback 세부 튜닝
- insufficient evidence 분포 해석

### WQ3. Markdown / JSON 보고서 만들기

상태:

- 기본 구현 완료

목표:

- 사람이 읽을 수 있는 wait quality 요약을 만든다

출력 권장:

- `data/analysis/wait_quality/entry_wait_quality_latest.json`
- `data/analysis/wait_quality/entry_wait_quality_latest.md`

보고서 핵심 항목:

- better entry count
- avoided loss count
- missed move count
- delayed loss count
- insufficient evidence count
- symbol별 분포
- wait_state별 분포
- wait_decision별 분포

구현 파일:

- `scripts/entry_wait_quality_replay_report.py`

현재 출력:

- `data/analysis/wait_quality/entry_wait_quality_replay_latest.json`
- `data/analysis/wait_quality/entry_wait_quality_replay_latest.md`

### WQ4. Closed history / learning seed enrichment

상태:

- 기본 구현 완료

목표:

- entry-side wait quality를 학습용 표본에 남긴다

권장 컬럼:

- `entry_wait_quality_label`
- `entry_wait_quality_score`
- `entry_wait_quality_reason`

연결 후보 파일:

- `backend/services/trade_csv_schema.py`
- `backend/services/teacher_pattern_backfill.py`
- `backend/services/teacher_pattern_experiment_seed.py`
- `backend/services/entry_wait_quality_seed_enrichment.py`
- `scripts/backfill_entry_wait_quality_learning_seed.py`

현재 완료 범위:

- `trade_closed_history.csv`에 `entry_wait_quality_*` 컬럼 추가
- replay report를 closed history row와 매칭하는 enrichment plan 구현
- on-demand backfill 스크립트 구현
- experiment seed report에 `entry_wait_quality_distribution`과 `entry_wait_quality_coverage` 추가
- 현재 seed 기준 실제 labeled row에도 coverage가 잡히는 것 확인

지금 기준 실제 확인:

- `total_rows = 8708`
- `labeled_rows = 2598`
- `rows_with_entry_wait_quality = 3`
- `valid_rows = 3`
- label 분포는 `better_entry_after_wait / delayed_loss_after_wait / neutral_wait`

주의:

- 기존 `wait_quality_label`은 exit/loss 의미가 강하므로
  이름 충돌을 피하려면 `entry_wait_quality_*`로 분리하는 것이 안전하다.

### WQ5. state25 / pilot baseline 연결

상태:

- 기본 auxiliary 연결 완료

목표:

- state25 baseline이 `무슨 wait였는가`만 아니라
  `그 wait가 결과적으로 어땠는가`도 먹을 수 있게 한다

연결 방식 후보:

- feature로 연결
- auxiliary target으로 연결
- quality bucket summary로 연결

권장 순서:

1. future leakage가 없는 연결 방식을 먼저 고정
2. auxiliary target으로 먼저 연결
3. 그 다음 quality bucket summary나 downstream feature 검토

현재 구현:

- `teacher_pattern_pilot_baseline.py`에 `wait_quality_integration` 섹션 추가
- `tasks.wait_quality_task` 추가
- 기존 pattern/group baseline feature는 그대로 유지
- `entry_wait_quality_*`는 현재 baseline 입력 feature로 직접 넣지 않음

왜 이렇게 했나:

- `entry_wait_quality_*`는 wait 이후 future path와 next trade 결과에서 나온 값이라
  pattern/group baseline 입력 feature로 직접 쓰면 future leakage가 생긴다
- 그래서 현재는 `entry-time feature -> entry_wait_quality_label`을 예측하는
  auxiliary target 방식으로 먼저 연결하는 것이 안전하다

지금 기준 해석:

- 연결 자체는 완료
- 다만 실제 seed는 `target_rows = 3`이라 아직 `wait_quality_task`는 `skipped`
- 즉 구조는 붙었고, 표본이 더 쌓이면 바로 auxiliary 실험이 가능하다

### WQ6. Step 9 watch 항목으로 승격

상태:

- 이후 단계

목표:

- Step 9 watch에 wait quality coverage를 넣는다

예시 watch 항목:

- better entry coverage
- avoided loss coverage
- delayed loss coverage
- insufficient evidence rate

## 4. 왜 이 순서가 맞는가

바로 live 엔진을 바꾸면 안 된다.

먼저 필요한 것은:

- owner
- contract
- replay
- report
- enrichment

즉 `판단 엔진 수정`보다 먼저
`평가 엔진과 학습 재료`를 만드는 것이 맞다.

그래야 나중에
`좋은 wait는 유지하고 나쁜 wait만 줄이는 튜닝`
이 가능해진다.

## 5. 이번 턴 이후 바로 추천하는 다음 작업

1. 실데이터 기준으로 `insufficient evidence`가 왜 많이 나오는지 확인
2. anchor price를 어디서 가장 안정적으로 가져올지 고정
3. bridge가 연결한 next entry / next trade 샘플을 case review 한다
4. `wait_quality_task`가 실제로 열릴 만큼 seed를 더 쌓고 auxiliary 성능을 관찰한다

## 6. 완료 판단 기준

이 로드맵이 실제로 끝났다고 보려면 최소한 아래가 필요하다.

- 실데이터 wait row를 shadow audit할 수 있음
- 사람이 읽는 md 보고서가 있음
- `entry_wait_quality_*` 컬럼이 학습용 표본에 남음
- state25 또는 baseline이 그 정보를 feature로 사용함
- Step 9 watch에서 coverage를 재확인할 수 있음
