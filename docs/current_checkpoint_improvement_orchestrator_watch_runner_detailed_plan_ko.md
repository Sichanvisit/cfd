# Current Checkpoint Improvement Orchestrator Watch Runner Detailed Plan

## 목적

`checkpoint_improvement_orchestrator_watch.py`는 `manage_cfd` 아래에서
주기적으로 orchestrator tick을 호출하는 실제 runner다.

핵심은 runner가 스스로 business logic를 많이 가지지 않고

- runtime freshness gate
- orchestrator tick 호출
- recovery/health snapshot 갱신
- latest watch report 출력

만 담당하는 것이다.

## 구성

- service
  - `backend/services/checkpoint_improvement_orchestrator_watch_runner.py`
- script
  - `scripts/checkpoint_improvement_orchestrator_watch.py`

## v0 동작

1. `runtime_status.json` freshness 확인
2. stale이면 `RUNTIME_STATUS_STALE_WAIT`
3. fresh이면 orchestrator tick 1회 수행
4. 직후 recovery/health snapshot 생성
5. watch latest json/md 갱신

## 출력

- `checkpoint_improvement_orchestrator_watch_latest.json`
- `checkpoint_improvement_orchestrator_watch_latest.md`
- `checkpoint_improvement_orchestrator_watch_history_latest.json`

## manage_cfd 연결 원칙

- `main.py`와 분리된 별도 watch 프로세스다
- 중복 기동 금지
- `status / stop / restart / cleanup` 루틴에 포함한다
- candidate watch / calibration watch와 같은 방식으로 유지한다

## 왜 이렇게 두는가

- hot path를 무겁게 만들지 않기 위해
- orchestrator 실패가 곧바로 main runtime 실패로 번지지 않게 하기 위해
- 향후 Telegram control plane이 붙어도 runner는 그대로 유지하기 위해
