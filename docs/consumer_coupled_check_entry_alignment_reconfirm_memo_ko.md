# Consumer-Coupled Check / Entry Alignment Reconfirm Memo

## 1. 이번 라운드 목적

`체크는 Consumer pre-entry state`, `진입은 같은 chain의 higher gate pass`라는 기준을 실제 코드에 1차로 반영한다.

## 2. 반영 범위

### 2.1 Entry owner

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)

추가 사항:

- `consumer_check_state_v1`
- top-level scalar mirror
  - `consumer_check_candidate`
  - `consumer_check_display_ready`
  - `consumer_check_entry_ready`
  - `consumer_check_side`
  - `consumer_check_stage`
  - `consumer_check_reason`
  - `consumer_check_display_strength_level`

핵심 정책:

- `probe_pair_gap_not_ready`, `probe_forecast_not_ready`, `probe_barrier_blocked`
  - display 가능
  - entry 불가
- `execution_soft_blocked`
  - display 유지 가능
  - entry 불가
- `policy_hard_blocked`, `probe_against_default_side`, `probe_side_mismatch`
  - display 차단
- `upper_approach_observe` 같은 generic directional observe
  - probe scene / probe_not_promoted / explicit confirm surface가 없으면 display 후보로 올리지 않음

### 2.2 Chart owner

- [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

변경 사항:

- `consumer_check_state_v1`가 있으면 chart event translation에서 우선 사용
- signature에도 `check_display_ready / check_side / check_stage`를 포함

매핑:

- `READY` -> `BUY_READY` / `SELL_READY`
- `PROBE` -> `BUY_PROBE` / `SELL_PROBE`
- `OBSERVE`, `BLOCKED` -> `BUY_WAIT` / `SELL_WAIT`

## 3. baseline 근거

기준 문서:

- [consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md)

대표 row:

- `NAS100`
  - `lower_rebound_confirm`
  - `forecast_guard`
  - `observe_state_wait`
- `BTCUSD`
  - `btc_lower_buy_conservative_probe`
  - `probe_barrier_blocked`
- `XAUUSD`
  - `xau_upper_sell_probe`
  - `probe_forecast_not_ready`

## 4. 테스트

실행 결과:

- `pytest tests/unit/test_entry_service_guards.py` -> `58 passed`
- `pytest tests/unit/test_chart_painter.py` -> `55 passed`

추가 회귀 포인트:

- `consumer_check_state_v1` probe stage
- `consumer_check_state_v1` ready stage
- `energy_soft_block` -> `BLOCKED`
- chart가 canonical consumer check payload를 우선 해석

## 5. 현재 해석

이번 1차 구현으로 아래는 닫혔다.

- chart와 entry가 같은 pre-entry state payload를 볼 수 있다
- check와 entry가 서로 다른 owner에서 따로 의미를 만들지 않는다
- painter-only display gate 초안보다 현재 owner 분리에 더 잘 맞는다

아직 남은 것:

- NAS100 실제 runtime window 재관측
- 필요 시 XAU/BTC scene별 stage 미세조정
- core 재시작 후 `consumer_check_*` 실row 반영 확인

## 6. 다음 단계

다음 자연스러운 순서는:

1. runtime 재시작
2. NAS100 실제 관측
3. distribution / rollout / recent rows 확인
4. 필요 시 scene-specific 후속 조정
