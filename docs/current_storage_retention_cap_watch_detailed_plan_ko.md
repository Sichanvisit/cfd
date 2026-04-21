# CFD Storage Retention Cap Watch 상세 계획

## 목표

- `data/` 전체 사용량이 과도하게 커졌을 때 오래된 historical 로그를 먼저 정리한다.
- 기본 상한은 `20GB`로 두고, `manage_cfd`에서 자동으로 관리되게 만든다.
- live/runtime가 바로 쓰는 active 파일은 보존하고, 필요할 때만 `checkpoint_rows.detail.jsonl`을 tail 유지 방식으로 줄인다.

## 핵심 원칙

- active 파일은 지우지 않는다.
  - `data/trades/entry_decisions.csv`
  - `data/trades/entry_decisions.detail.jsonl`
  - `data/runtime/checkpoint_rows.csv`
- historical 파일은 오래된 것부터 cap 기준으로 삭제한다.
  - `entry_decisions.detail.rotate_*`
  - `entry_decisions.legacy_*`
  - `entry_decisions.tail_*`
  - `data/backfill/breakout_event/jobs/**`
- cap을 아직 넘는 경우에만 `checkpoint_rows.detail.jsonl`을 tail 유지 방식으로 줄인다.

## 운영 모드

### preflight

- `manage_cfd start/start_core` 전에 1회 실행
- historical 삭제 + 필요 시 `checkpoint_rows.detail.jsonl` tail trim
- 시작 전 정리라서 가장 안전한 강한 정리 모드

### background watch

- `manage_cfd`가 별도 watch 프로세스로 주기 실행
- 기본 60분 간격
- historical 삭제를 계속 유지
- cap 초과가 심하면 `checkpoint_rows.detail.jsonl`도 best-effort로 trim 시도

## 산출물

- 최신 snapshot
  - `data/analysis/shadow_auto/cfd_storage_retention_latest.json`
  - `data/analysis/shadow_auto/cfd_storage_retention_latest.md`
- history
  - `data/analysis/shadow_auto/cfd_storage_retention_watch_history_latest.json`
- manifest
  - `data/manifests/retention/cfd_storage_retention_*.json`

## manage_cfd 연동

- 새 명령:
  - `manage_cfd.bat storage_retention`
  - `manage_cfd.bat storage_retention_watch`
- `start`, `start_core`에서 preflight 1회 실행
- background watch 자동 기동
- `status`, `stop`, cleanup 경로에도 포함

## 기본 설정값

- cap: `20GB`
- background interval: `60분`
- checkpoint detail 최소 보존: `2GB`

## 완료 기준

- 오래된 historical 로그가 자동으로 정리된다.
- `data/` 총량이 상한을 넘을 때 oldest-first로 줄어든다.
- `manage_cfd`만으로 수동/자동 정리가 가능하다.
