# BC3 State25 Runtime Trace Export 실행 로드맵

## 목표

bridge 결과를 runtime / detail / slim / hot payload에 실제로 싣는다.


## BC3-1. Bridge Flat Field Helper

목표:
- nested bridge를 빠르게 읽을 수 있는 flat field helper 추가

대상:
- `backend/services/state25_context_bridge.py`


## BC3-2. Entry Trace Export

목표:
- `entry_try_open_entry.py`에서 entry detail row에 bridge를 싣기

완료 기준:
- entry detail row에 `state25_candidate_context_bridge_v1` 존재
- flat field 요약도 같이 존재


## BC3-3. Runtime Signal Export

목표:
- `trading_application.py`의 symbol별 latest runtime row에 bridge를 싣기

완료 기준:
- `_enrich_runtime_signal_row_with_state_context(...)` 결과 row에 bridge 존재


## BC3-4. Storage Compaction Export

목표:
- compact / hot payload에서 bridge가 사라지지 않게 하기

대상:
- `backend/services/storage_compaction.py`

완료 기준:
- `compact_runtime_signal_row(...)`에 bridge nested field 유지
- `build_entry_decision_hot_payload(...)`에도 bridge nested json 유지


## BC3-5. Tests

최소 테스트:
1. runtime signal row에 bridge가 붙는지
2. compact row에 bridge가 유지되는지
3. hot payload에 bridge json이 유지되는지


## 다음 단계

BC3 완료 후 다음은 자연스럽게:

1. `BC4 Weight-Only Log-Only Review Lane`
