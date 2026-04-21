# PA8 Closeout Auto-Trigger + PA9 Handoff + Restart Guard

## 목적

- `PA8 closeout`이 준비되면 stale board를 기다리지 않고 watch governance cycle에서 바로 `closeout review` 후보가 올라오게 한다.
- `PA8 closeout apply`가 승인되면 `PA9 action baseline handoff packet`이 즉시 생성되게 한다.
- `manage_cfd.bat restart_core`가 PowerShell JSON 파싱 문제에 흔들리지 않도록 Python guard로 고정한다.

## 이번 반영의 핵심

### 1. restart_core guard fix

- 새 서비스: `backend/services/runtime_flat_guard.py`
- 새 스크립트: `scripts/runtime_flat_guard.py`
- `manage_cfd.bat :guard_flat_before_restart`는 이제 PowerShell `ConvertFrom-Json` 대신 Python helper를 호출한다.
- guard 판단은 아래 둘을 함께 본다.
  - `data/runtime_status.json`
  - `http://127.0.0.1:8010/trades/summary`
- 둘 다 unavailable이면 block, 둘 중 하나라도 fresh flat이면 restart 가능, 하나라도 open count가 있으면 block이다.

### 2. PA8 closeout auto-trigger

- `backend/services/checkpoint_improvement_watch.py`
- governance default loader는 이제 기존 `checkpoint_pa8_canary_refresh_board_latest.json`을 그대로 읽지 않고,
  - resolved dataset 재로딩
  - fresh canary refresh board rebuild
  - output rewrite
  후 최신 payload를 governance cycle에 넘긴다.
- 그래서 `closeout_state = READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW`가 되면 다음 governance tick에서 자동으로 `CANARY_CLOSEOUT_REVIEW` 후보가 생성된다.

### 3. PA9 handoff packet scaffold

- 새 서비스: `backend/services/checkpoint_improvement_pa9_handoff_packet.py`
- 새 스크립트: `scripts/build_checkpoint_improvement_pa9_handoff_packet.py`
- 산출물:
  - `data/analysis/shadow_auto/checkpoint_improvement_pa9_action_baseline_handoff_packet_latest.json`
  - `data/analysis/shadow_auto/checkpoint_improvement_pa9_action_baseline_handoff_packet_latest.md`
- packet은 `NAS100 / BTCUSD / XAUUSD`의 activation/closeout/first-window 상태를 읽어 아래를 요약한다.
  - `prepared_symbol_count`
  - `ready_closeout_symbol_count`
  - `active_canary_symbol_count`
  - `live_window_ready_count`
  - `handoff_state`
  - `recommended_next_action`

## closeout apply 이후 연결

- `backend/services/checkpoint_improvement_pa8_apply_handlers.py`
- `handle_closeout_review()`는 이제:
  - activation apply를 `PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY`로 내리고
  - canary refresh board를 다시 만들고
  - PA9 handoff packet scaffold도 즉시 생성한다

즉 운영 의미는 이렇다.

- closeout ready 감지: `watch/governance`
- closeout 승인/적용: `approval loop + apply executor`
- handoff scaffold 생성: `closeout apply handler`

## 아직 남는 운영 조건

- 실제 `PA8 closeout`은 여전히 live window가 필요하다.
- 지금 추가한 것은 “조건이 만족됐을 때 자동으로 다음 review/handoff 준비가 이어지는 통로”다.
- `SA`는 계속 preview-only 유지다.
