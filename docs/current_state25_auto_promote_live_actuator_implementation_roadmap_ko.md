# State25 Auto Promote / Rollback / Live Actuator Implementation Roadmap

## 목표

이 문서는 `AI6`를 실제 작업 순서로 나눈 구현 로드맵이다.

짧게 말하면:

- 어떤 파일을 만들고
- 어디까지는 dry-run으로 두고
- 어디부터 apply를 열지

를 정리한 문서다.

## AI6 단계 분해

### AP1. Latest Input Contract

할 일:

- latest gate report 읽기
- latest execution policy integration report 읽기
- latest log-only binding report 읽기
- active candidate state 읽기

완료 기준:

- AI6가 필요한 최신 입력 4개를 한 번에 읽을 수 있다

### AP2. Active Candidate Registry

할 일:

- `active_candidate_state.json` 설계
- 초기 기본값 정의
- `auto_promote_history.jsonl` append 규약 만들기

완료 기준:

- 현재 active candidate와 rollout phase를 파일 하나로 확인할 수 있다
- promote / rollback 이력을 남길 수 있다

### AP3. Promote Decision

할 일:

- `promote_ready + log_only_candidate_bind_ready + log_only` 조합을 detect
- `promote_log_only_ready` controller stage 만들기
- proposed active-state patch 만들기

완료 기준:

- 지금 후보를 log-only active candidate로 올릴 수 있는지 자동으로 보인다

### AP4. Rollback Decision

할 일:

- `rollback_recommended` detect
- 현재 active candidate와 비교
- baseline 복귀용 state patch 만들기

완료 기준:

- 언제 rollback 대상인지 자동으로 보인다
- rollback 시 어떤 상태 파일을 써야 하는지 자동으로 나온다

### AP5. Live Actuator Patch Contract

할 일:

- threshold / size log-only patch를 AI6 보고서에 묶기
- apply 전/후에 어떤 patch가 쓰일지 고정

완료 기준:

- runtime이 나중에 읽어갈 수 있는 patch contract가 생긴다

### AP6. Human Summary

할 일:

- md summary 출력
- latest json 출력
- candidate watch summary에 AI6 stage 붙이기

완료 기준:

- 사람은 md만 보고도 현재 자동 승격/롤백 상태를 이해할 수 있다

## 이번에 구현하는 파일

- `backend/services/teacher_pattern_auto_promote_live_actuator.py`
- `scripts/teacher_pattern_auto_promote_live_actuator_report.py`
- `tests/unit/test_teacher_pattern_auto_promote_live_actuator.py`

추가 연결:

- `backend/services/teacher_pattern_candidate_watch.py`
- `scripts/state25_candidate_watch.py`
- `tests/unit/test_teacher_pattern_candidate_watch.py`

## 실행 명령

기본 dry-run:

```powershell
python scripts/teacher_pattern_auto_promote_live_actuator_report.py
```

상태 파일까지 실제 반영:

```powershell
python scripts/teacher_pattern_auto_promote_live_actuator_report.py --apply
```

candidate watch 안에서 AI6까지 같이 계산:

```powershell
python scripts/state25_candidate_watch.py --max-cycles 1
```

candidate watch에서 AI6 apply까지 열기:

```powershell
python scripts/state25_candidate_watch.py --max-cycles 1 --apply-ai6
```

## 현재 1차 완료 기준

이번 1차에서 완료로 보는 기준은 아래다.

1. latest gate/integration/binding을 읽어 controller stage를 만든다
2. promote-ready면 log-only 승격 patch를 계산한다
3. rollback-ready면 baseline 복귀 patch를 계산한다
4. md/json latest 보고서를 남긴다
5. candidate watch에서도 AI6 stage가 같이 보인다

## 아직 일부러 안 하는 것

이번 단계에서 일부러 보류하는 것:

- runtime이 `active_candidate_state.json`을 직접 소비해서 threshold를 실시간으로 바꾸는 일
- candidate watch 기본 루프에서 `--apply-ai6`를 자동으로 켜는 일
- canary evidence 없이 bounded live를 여는 일

이건 나중 단계로 남긴다.

## 다음 단계

AI6 2차는 여기서 시작한다.

### AP7. Runtime Consumption

- runtime이 `active_candidate_state.json`과 `desired_runtime_patch`를 읽도록 연결

### AP8. Promote-Only Auto Apply

- candidate watch에서 promote-ready일 때만 `--apply-ai6`를 제한적으로 켬

### AP9. Rollback Auto Apply

- rollback-recommended면 active candidate를 자동 해제

### AP10. Bounded Live

- log-only를 통과한 candidate만 canary로 올림
- canary까지 통과한 뒤에만 bounded live

## 핵심 해석

AI6의 첫 구현은 `자동으로 live를 바꾸는 단계`가 아니라 `자동으로 언제 바꿀지, 언제 되돌릴지를 정확히 계산하는 단계`다.

그래서 지금 목표는:

`promote / hold / rollback을 사람이 안 섞어도 한 군데서 정확히 읽히게 만드는 것`

이다.
