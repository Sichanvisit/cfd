# BC3 State25 Runtime Trace Export 상세 계획

## 목표

`BC3`의 목적은 `BC2`에서 계산된 `state25_candidate_context_bridge_v1`를

- entry decision row
- latest runtime signal row
- compact / hot payload

까지 실제로 보이게 연결하는 것이다.

즉 BC3는 translator를 더 똑똑하게 만드는 단계가 아니라,
**이미 계산된 bridge 결과가 운영에서 실제로 보이게 만드는 export 단계**다.


## 왜 BC3가 필요한가

BC2까지 끝나면 bridge는 내부적으로 weight pair를 계산할 수 있다.
하지만 export를 안 붙이면:

- runtime detail에서 안 보이고
- slim payload에서 안 보이고
- hot payload에서 안 보이고
- detector/propose가 나중에 읽을 수 없고
- 운영자가 “bridge가 계산됐는지” 체감할 수 없다

그래서 BC3는 계산보다 **가시성 확보** 단계다.


## 이번 단계 범위

이번 `BC3`에서 구현할 것:

- `entry_try_open_entry.py`
- `trading_application.py`
- `storage_compaction.py`
- 관련 테스트

이번 단계에서 하지 않을 것:

- threshold translator
- size translator
- detector/propose review lane 연결


## 연결 원칙

### 1. entry row와 runtime row 둘 다 실어야 한다

- `entry_try_open_entry.py`
  - 진입 시점 detail / hot payload용
- `trading_application.py`
  - symbol별 최신 runtime row용

이 두 축이 같이 살아야 나중에 detector/propose/hindsight가 한 언어로 이어진다.

### 2. nested + flat 둘 다 둔다

bridge 본문은 nested object로 싣고,
빠른 관찰용 요약은 flat field로도 같이 싣는다.

예:
- `state25_candidate_context_bridge_v1`
- `state25_context_bridge_stage`
- `state25_context_bridge_bias_side`

### 3. compaction whitelist를 같이 수정한다

`storage_compaction.py`에 새 nested field를 넣지 않으면
detail에는 있는데 slim/hot에선 사라질 수 있다.


## 구현 포인트

### entry_try_open_entry.py

- forecast / belief / barrier / countertrend까지 준비된 후
- `build_state25_candidate_context_bridge_v1(...)` 호출
- detail row에 nested bridge 추가
- flat fields도 같이 merge

### trading_application.py

- `_enrich_runtime_signal_row_with_state_context(...)`에서
  - context_state merge 후
  - state25 candidate runtime state를 bridge input에 얹어서
  - per-symbol bridge 계산
- row에 nested bridge + flat fields 추가

### storage_compaction.py

- `compact_runtime_signal_row(...)` nested whitelist에
  - `state25_candidate_context_bridge_v1`
  추가
- `build_entry_decision_hot_payload(...)` nested json whitelist에도 추가


## 완료 기준

- runtime detail의 `latest_signal_by_symbol[*]` row에 bridge가 보인다
- slim payload compaction 이후에도 bridge nested field가 유지된다
- hot payload에서도 bridge nested json이 남는다
- flat summary field도 함께 보인다


## 다음 단계 연결

BC3 이후 가장 자연스러운 다음 단계는:

1. `BC4 Weight-Only Log-Only Review Lane`

즉 BC3가 닫혀야 비로소 detector/propose가 bridge 결과를 실제로 읽기 시작할 수 있다.
