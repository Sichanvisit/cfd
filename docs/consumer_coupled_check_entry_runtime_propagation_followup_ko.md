# Consumer-Coupled Runtime Propagation Follow-up

## 1. 목적

`consumer_check_state_v1`가 `entry_service.py`에서 만들어지더라도,
실제 live `entry_decisions.csv`, `entry_decisions.detail.jsonl`, `runtime_status.json`에
같이 내려오지 않으면 chart 표기와 entry chain이 다시 분리된다.

이번 follow-up의 목적은:

- `_decision_payload()` 최종 row에 `consumer_check_*`를 실어 주고
- `latest_signal_by_symbol`에도 같은 payload를 surface해서
- chart / runtime status / CSV / detail sidecar가 같은 Consumer chain을 보게 만드는 것이다.

## 2. 원인

확인 결과:

- `entry_service.py`의 `_core_action_decision()`은 이미 `consumer_check_state_v1`와
  top-level `consumer_check_*` scalar를 만든다.
- 하지만 [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)의
  `_decision_payload()`는 이 값을 최종 row에 싣지 않았다.
- 그래서 live CSV/detail/runtime에서는 필드가 빈 값으로 보였고,
  chart는 consumer-coupled 기준보다 legacy chart-flow 해석에 더 의존했다.

## 3. 반영 내용

수정 파일:

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)

반영 내용:

- `_decision_payload()`가 아래 필드를 최종 row에 포함하도록 수정
  - `consumer_check_candidate`
  - `consumer_check_display_ready`
  - `consumer_check_entry_ready`
  - `consumer_check_side`
  - `consumer_check_stage`
  - `consumer_check_reason`
  - `consumer_check_display_strength_level`
  - `consumer_check_state_v1`
- `latest_signal_by_symbol` 갱신 지점에도 같은 필드를 같이 반영
- `topdown_timeframe_gate_blocked` 같은 실제 skip 경로에서도
  log row와 runtime row 둘 다 consumer check 상태가 보존되는 회귀 테스트 추가

## 4. 테스트

실행 결과:

- `pytest tests/unit/test_entry_service_guards.py -k "topdown_skip_preserves_consumer_check_state or max_positions_skip_does_not_crash_without_consumer_ids"` -> `2 passed`
- `pytest tests/unit/test_entry_service_guards.py tests/unit/test_chart_painter.py tests/unit/test_storage_compaction.py tests/unit/test_entry_engines.py -q` -> `142 passed`

## 5. 라이브 확인

코어 재시작 후 확인 결과:

- 13:53 이전 row는 기존 legacy 흐름이 섞여 `consumer_check_*`가 비어 있을 수 있었다.
- 13:53 이후 새 row부터는 propagation이 정상 확인됐다.

대표 live row:

- `NAS100`
  - `observe_reason=middle_sr_anchor_required_observe`
  - `blocked_by=middle_sr_anchor_guard`
  - `consumer_check_display_ready=false`
  - `consumer_check_stage=BLOCKED`
- `XAUUSD`
  - `observe_reason=upper_break_fail_confirm` 또는 `upper_reject_probe_observe`
  - `blocked_by=forecast_guard` 또는 `energy_soft_block`
  - `consumer_check_display_ready=true`
  - `consumer_check_stage=PROBE`
- `BTCUSD`
  - `observe_reason=outer_band_reversal_support_required_observe`
  - `blocked_by=outer_band_guard`
  - `consumer_check_display_ready=true`
  - `consumer_check_stage=PROBE`

detail sidecar도 동일하게:

- [entry_decisions.detail.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl)
  - `payload.consumer_check_state_v1` populated
  - `payload.consumer_check_display_ready` populated

runtime status도 동일하게:

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
  - `latest_signal_by_symbol.*.consumer_check_*` populated

## 6. 현재 해석

이제 남은 문제는 propagation bug가 아니다.

현재 남은 것은:

- 어떤 `consumer_check_stage`까지 chart에 보여줄지
- `PROBE`와 `BLOCKED`를 symbol/scene별로 얼마나 보수적으로 surface할지

즉 다음 조정 포인트는:

- storage/runtime propagation이 아니라
- 실제 `consumer_check_state_v1` policy와 painter translation density다.

## 7. 다음 단계

다음 자연스러운 작업은:

1. 최근 live row 기준 `PROBE/BLOCKED/READY` 밀도 재관측
2. `generic observe`가 아닌 실제 consumer check candidate만 chart에 남는지 확인
3. 필요하면 `PROBE` display floor를 symbol/scene 기준으로 좁게 조정

