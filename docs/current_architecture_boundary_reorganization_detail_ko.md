# CFD 현재 아키텍처 정리용 상세 문서

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 아래 목적을 위해 만든다.

- 현재 구조를 `정리/고정/분리`하기 위한 상세 작업 기준서
- 새 스레드에서 바로 작업을 이어갈 수 있는 owner map
- 단순 감상이나 평가가 아니라 실제 리팩터링 단위로 쪼갠 정리 문서

이 문서는 [current_architecture_boundary_objective_audit_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_objective_audit_ko.md)의 확장판이다.

차이는 아래와 같다.

- audit 문서는 `어디가 약한가`를 설명한다
- 이 문서는 `그래서 어떻게 정리해야 하는가`를 구조적으로 정리한다


## 2. 현재 정리의 핵심 목표

현재 시스템에서 가장 중요한 정리 목표는 기능 추가가 아니다.

핵심 목표는 아래 네 가지다.

1. `ObserveConfirm -> Consumer -> Execution` 경계의 owner를 다시 분명히 고정한다.
2. `guard -> stage -> display -> visual` 계산이 한 군데에서 끝나도록 만든다.
3. `BLOCKED`를 내부 상태뿐 아니라 runtime/chart에서도 끝까지 보존한다.
4. `latest snapshot` 중심 운영 표면을 `recent-window diagnostics` 중심으로 보강한다.

즉 이번 정리는 “새 rule을 더 넣는 작업”이 아니라 “기존 시스템이 덜 흔들리게 만드는 작업”이다.


## 3. 이상적인 목표 구조

현재 대개편 문서 의도를 다시 정리하면 목표 구조는 아래다.

```text
Semantic layers
-> ObserveConfirmSnapshot v2
-> Consumer
-> Execution
-> Runtime / Chart / Storage
```

여기서 각 owner는 아래처럼 고정되어야 한다.

- `ObserveConfirm`
  - identity owner
  - archetype / invalidation / management_profile / lifecycle state 결정
- `Consumer`
  - observe-confirm 결과를 setup/check/entry/exit/re-entry에 연결
  - semantic meaning을 다시 만들지 않음
- `Execution`
  - 실제 주문 가능 여부만 판단
  - semantic identity를 바꾸지 않음
- `Runtime / Chart`
  - 최종 truth를 번역/요약/표현
  - truth를 재해석하지 않음


## 4. 현재 실제 흐름

현재 코드상 실제 흐름은 대략 아래와 같다.

```text
context_classifier
-> observe_confirm_v1/v2 + energy_snapshot + energy_helper_v2 + layer_mode metadata
-> entry_service
-> consumer_check_state_v1 + entry decision
-> entry_try_open_entry
-> late block / effective consumer check rewrite
-> row/latest signal/runtime status/chart
```

문제는 이 흐름이 “동작은 하지만 경계가 아직 완전히 굳지 않았다”는 점이다.


## 5. 파일별 현재 역할과 목표 역할

### 5-1. owner matrix

| 영역 | 현재 주요 파일 | 현재 역할 | 목표 역할 | 현재 문제 |
| --- | --- | --- | --- | --- |
| ObserveConfirm identity | `backend/trading/engine/core/observe_confirm_router.py` | archetype/state/action/forecast modulation | 그대로 유지 | 비교적 양호 |
| metadata dual-write / bridge | `backend/services/context_classifier.py` | observe_confirm, energy_snapshot, energy_helper, layer_mode를 함께 기록 | bridge 역할 유지 | compatibility field가 많아 경계 인식이 흐릴 수 있음 |
| consumer check / stage | `backend/services/entry_service.py` | check stage, display readiness, block reason 계산 | 공용 resolver owner 또는 consumer owner로 재정리 | execution 파일 안에 정책이 너무 많음 |
| late guard rewrite | `backend/services/entry_try_open_entry.py` | late blocked/action_none 반영, effective state 재작성 | 얇은 finalization 또는 공용 resolver 재사용 | stage/display 정책이 중복 owner |
| visual translation | `backend/trading/chart_painter.py` | row state를 chart event로 번역 | 번역만 수행 | `BLOCKED`가 `WAIT`로 합쳐짐 |
| runtime status export | `backend/app/trading_application.py` | latest signal/runtime rollout 상태 출력 | recent-window diagnostics 추가 | 운영 표면이 latest snapshot 위주 |
| wait/energy hint usage | `backend/services/wait_engine.py` | wait vs enter / readiness 소비 | 유지 | 상대적으로 양호 |
| energy usage trace | `backend/services/energy_contract.py` | consumed fields 추론 및 trace 부착 | branch-level truth 기록으로 고도화 | 결과 기반 추론 비중이 큼 |


## 6. 현재 코드에서 실제로 강한 부분

### 6-1. ObserveConfirm owner는 꽤 잘 서 있다

근거:

- `backend/services/context_classifier.py:1558-1575`
- `backend/trading/engine/core/observe_confirm_router.py:1578-1623`

의미:

- `energy_snapshot`은 계산되지만 observe-confirm identity 입력 owner처럼 직접 쓰이지 않는다.
- forecast는 confidence/action 보정만 하고 identity override는 막혀 있다.

정리 판단:

- 이 축은 지금 뜯어고치기보다 보존/강화 쪽이 맞다.

### 6-2. WaitEngine은 이미 활용 레이어로 들어가 있다

근거:

- `backend/services/wait_engine.py:86-136`

의미:

- `action_readiness`
- `wait_vs_enter_hint`
- `soft_block_hint`

를 실제로 읽고 있어서, 이쪽은 “아직 연결 안 됐다”가 아니라 “연결은 됐고 운영 표면이 약하다” 쪽에 가깝다.

### 6-3. 최근 wrong READY는 최근 데이터 기준으로는 잡혔다

실제 확인:

- 전체 `entry_decisions.csv` 7012행 중 과거 wrong READY 흔적 412건
- 최근 300행 기준 wrong READY 0건

정리 판단:

- 최근 수정은 효과가 있다
- 다만 구조가 완전히 안전해진 것은 아니다


## 7. 현재 코드에서 실제로 약한 부분

### 7-1. consumer check owner가 분산돼 있다

관련 파일:

- `backend/services/entry_service.py:1838-1916`
- `backend/services/entry_try_open_entry.py:618-645`

현재 상태:

- `entry_service`가 1차 check stage/display를 만든다
- `entry_try_open_entry`가 late blocked/action_none를 반영하며 다시 바꾼다

왜 문제인가:

- policy table이 한 군데가 아니다
- 새 guard 추가 시 두 군데 이상을 동시에 갱신해야 한다
- 한쪽만 갱신되면 runtime/chart/trade row truth drift가 생긴다

대표 리스크:

- blocked인데 READY 흔적이 남는 문제 재발
- observe/probe/blocked 경계가 symbol별로 다르게 흔들림

### 7-2. EntryService가 execution guard를 넘어서고 있다

관련 파일:

- `backend/services/entry_service.py:3089-3116`

현재 상태:

- XAU specific energy relief
- scene-specific branch
- probe plan 조건
- box/bb 상태
- energy soft-block reason/strength

가 함께 섞여 있다.

왜 문제인가:

- execution layer가 semantic shaping을 다시 하기 시작한다
- symbol tuning이 execution 파일에 누적된다
- 코드 해석 난이도가 급격히 올라간다

대표 리스크:

- 미래에 `BTC`, `NAS`, `XAU` 별 예외가 더 누적될 가능성
- regression scope 예측 어려움

### 7-3. BLOCKED가 마지막 표면에서 사라진다

관련 파일:

- `backend/trading/chart_painter.py:805-817`

현재 상태:

- `OBSERVE`와 `BLOCKED`가 둘 다 `*_WAIT`로 번역된다

왜 문제인가:

- 운영자가 chart에서 보는 상태와 내부 truth가 다르다
- `candidate existed but blocked`가 `just wait`와 구분되지 않는다

대표 리스크:

- 디버깅이 chart -> runtime -> csv -> code 순으로 길어진다

### 7-4. runtime status가 최신 한 줄 위주다

관련 파일:

- `backend/app/trading_application.py:1216-1232`

현재 상태:

- `latest_signal_by_symbol` 중심
- rollout / live config 요약 중심

왜 문제인가:

- 최근 100~300행의 방향성을 runtime 파일 하나로는 판단하기 어렵다
- 결국 csv를 직접 읽어야 한다

대표 리스크:

- 새 스레드나 운영 점검 때 handoff 비용 증가

### 7-5. energy usage trace가 결과 기반 추론에 많이 의존한다

관련 파일:

- `backend/services/energy_contract.py:1419-1548`

현재 상태:

- 최종 row 결과를 보고 consumed_fields를 재구성한다

왜 문제인가:

- 실제 branch에서 어떤 field를 읽었는지 1:1로 남는 것은 아니다
- replay/forensics에서 오해 소지가 있다

대표 리스크:

- “정말 이 힌트를 읽은 것인가”와 “결과상 그렇게 보이는 것인가”가 완전히 같지 않을 수 있다


## 8. 정리 작업을 위한 실제 분해 단위

이 문서에서는 정리 작업을 6개 작업 묶음으로 나눈다.

### 8-1. Work Package A: Consumer Check Single Owner 정리

목표:

- `check_stage`
- `display_ready`
- `entry_ready`
- `blocked_display_reason`
- `level/strength`

를 한 군데에서 계산하게 만든다.

대상 파일:

- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`
- 새 공용 helper 파일이 필요하면 `backend/services/` 하위에 추가

권장 방향:

- `resolve_consumer_check_effective_state(...)` 같은 단일 resolver를 만든다
- `entry_service`와 `entry_try_open_entry`는 같은 resolver를 호출만 하게 한다
- late display suppress guard도 이 resolver table 안으로 흡수한다

완료 기준:

- 동일 input에 대해 stage/display 계산 owner가 1곳이다
- `entry_service`와 `entry_try_open_entry`가 각자 policy set을 따로 갖지 않는다
- wrong READY 재현 케이스가 resolver test로 바로 잡힌다

필수 테스트:

- hard block
- soft block
- probe blocked
- action none
- late block after initial ready
- symbol-specific exception

### 8-2. Work Package B: BLOCKED Visual Continuity 정리

목표:

- `BLOCKED`를 chart/runtime에서도 `OBSERVE`와 구분되게 한다

대상 파일:

- `backend/trading/chart_painter.py`
- chart 관련 policy/spec 문서들
- 필요 시 chart flow 테스트

선택지:

1. `BUY_BLOCKED` / `SELL_BLOCKED` 별도 event 도입
2. 기존 `WAIT` 유지 + `blocked_kind`/`blocked_reason_class` 별도 시각 필드 유지

권장 방향:

- 가능하면 별도 event family가 더 낫다
- 최소한 WAIT 내부에 묻더라도 blocked reason class는 표면 필수값이어야 한다

완료 기준:

- chart event만 보고도 `OBSERVE`와 `BLOCKED`를 구분할 수 있다
- 테스트가 이 동작을 고정한다

### 8-3. Work Package C: Runtime Recent Diagnostics 정리

목표:

- `runtime_status.json`에서 최근 흐름을 바로 볼 수 있게 한다

대상 파일:

- `backend/app/trading_application.py`
- 필요 시 runtime helper / exporter

권장 추가 필드:

- recent 50/200/300 stage counts
- recent blocked reason top-N
- recent symbol summary
- recent wrong READY count
- recent display_ready false/true 분포

완료 기준:

- 새 스레드에서 csv를 열지 않아도 최근 상태를 1차 파악할 수 있다
- recent diagnostics와 csv 샘플 결과가 대체로 일치한다

### 8-4. Work Package D: Semantic Shadow Diagnostics Export 정리

목표:

- 내부 `semantic_shadow_runtime_diagnostics`를 요약이 아니라 운영 계약으로도 노출한다

대상 파일:

- `backend/app/trading_application.py`

권장 추가 필드:

- `semantic_shadow_runtime_diagnostics`
- `model_dir_exists`
- `load_error`
- `last_checked_ts`
- `available_targets_detail`

완료 기준:

- `inactive` 이유를 runtime status 하나로 더 정확히 설명할 수 있다

### 8-5. Work Package E: Energy Truthful Usage Logging 정리

목표:

- energy usage trace를 결과 추론 중심에서 branch-truth 중심으로 옮긴다

대상 파일:

- `backend/services/energy_contract.py`
- `backend/services/entry_service.py`
- 필요 시 `wait_engine.py`

권장 방향:

- branch 내부에서 consumed field를 append
- 최종 attach 단계는 formatting만 담당
- 결과 기반 재구성은 fallback으로 남긴다

완료 기준:

- trace의 `consumed_fields`가 실제 읽은 분기와 직접 연결된다
- replay 문서/테스트에서 “추정”이 아니라 “기록”으로 설명 가능하다

### 8-6. Work Package F: EntryService 경량화

목표:

- scene-specific policy shaping을 EntryService에서 점진적으로 걷어낸다

대상 파일:

- `backend/services/entry_service.py`
- 필요 시 `consumer_*`, `layer_mode_*`, `energy_*` 관련 모듈

주의:

- 이 작업은 가장 가치가 크지만 회귀 위험도 가장 높다
- 맨 먼저 하면 안 된다

권장 순서:

- 먼저 A/B/C/D를 끝낸다
- 그다음 EntryService 내부 scene-specific branch inventory를 만든다
- 마지막에 policy별 owner로 이동시킨다

완료 기준:

- EntryService는 execution safety 중심으로 읽힌다
- symbol/scenario 특수 룰이 대폭 줄거나 별도 owner로 이동한다


## 9. 작업 순서 권장안

현재 기준 가장 안정적인 순서는 아래다.

### 9-1. 1차 정리

- Work Package A
- Work Package B

이 두 개를 먼저 해야 하는 이유:

- 최근 실제 문제와 직접 연결되어 있다
- truth drift 재발을 가장 빨리 줄인다

### 9-2. 2차 정리

- Work Package C
- Work Package D

이 두 개를 이어서 해야 하는 이유:

- 운영 진단 비용을 줄인다
- 새 스레드/handoff 품질이 올라간다

### 9-3. 3차 정리

- Work Package E

이 단계의 의미:

- future debugging / replay / ML rollout 설명력을 높인다

### 9-4. 4차 정리

- Work Package F

이 단계의 의미:

- 구조 부채를 실질적으로 줄인다
- 다만 앞선 관측/출력/계약이 고정된 뒤에 해야 안전하다


## 10. 선후관계와 의존성

```text
A: consumer check single owner
-> B: blocked visual continuity
-> C: runtime recent diagnostics
-> D: semantic shadow diagnostics export
-> E: truthful energy logging
-> F: entry_service slimming
```

보완 관계는 아래와 같다.

- `A`가 있어야 `B`의 표면 의미가 흔들리지 않는다
- `A`와 `B`가 있어야 `C`의 recent summary가 믿을 만해진다
- `C`와 `D`가 있어야 운영자가 새 스레드에서 빠르게 상태를 잡는다
- `E`가 있어야 향후 `F` 리팩터링 시 usage regression 설명이 쉬워진다


## 11. 실제 정리할 때 건드리면 안 되는 것

이번 정리에서 함부로 건드리면 안 되는 축도 분명하다.

### 11-1. ObserveConfirm identity owner 자체를 다시 흔들지 말 것

현재 이 축은 오히려 잘 맞아 있는 편이다.

따라서 아래 같은 방향은 피하는 편이 좋다.

- energy snapshot을 다시 identity owner처럼 사용
- forecast가 archetype/side를 직접 바꾸게 허용
- consumer에서 archetype를 새로 재판단

### 11-2. EntryService 경량화를 첫 작업으로 하지 말 것

이건 매력적으로 보이지만 가장 위험하다.

이유:

- 지금은 output surface가 아직 충분히 정직하지 않다
- 이 상태에서 내부 branch를 걷어내면 회귀를 빨리 못 잡는다

### 11-3. chart에서 증상만 덮는 식의 수정은 피할 것

예:

- blocked를 그냥 wait styling만 더 세게 보이게 하기
- runtime truth는 그대로인데 painter에서만 보정하기

이런 방식은 당장은 예뻐 보여도 owner 경계를 더 흐리게 만든다.


## 12. 새 스레드에서 바로 쓸 수 있는 정리 체크리스트

새 스레드 시작 시 아래 순서로 보면 된다.

1. [current_architecture_boundary_objective_audit_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_objective_audit_ko.md)를 먼저 읽는다.
2. 이 문서에서 Work Package A~F 중 어디까지 진행할지 정한다.
3. `data/runtime_status.json`에서 `semantic_live_config`, `latest_signal_by_symbol`를 확인한다.
4. `data/runtime_status.detail.json`이 있으면 detail payload를 같이 본다.
5. `data/trades/entry_decisions.csv` 최근 200~300행에서 blocked/stage/display 패턴을 확인한다.
6. `backend/services/entry_service.py`와 `backend/services/entry_try_open_entry.py`의 stage/display owner 분리를 먼저 확인한다.
7. `backend/trading/chart_painter.py`에서 `BLOCKED -> WAIT` 번역 여부를 다시 확인한다.
8. 테스트는 최소한 아래 세 축부터 확인한다.

권장 테스트:

- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_trading_application_runtime_status.py`


## 13. 문서 작성 시점의 운영 메모

작성 시점 기준 확인된 값은 아래와 같다.

### 13-1. semantic rollout 상태

- `mode = threshold_only`
- `symbol_allowlist = ["BTCUSD", "NAS100"]`
- `shadow_runtime_state = inactive`
- `shadow_runtime_reason = model_dir_missing`

### 13-2. 최근 wrong READY 상태

- 전체 7012행 중 과거 wrong READY 412건 존재
- 최근 300행 기준 wrong READY 0건

### 13-3. 최근 샘플 패턴

- `BTCUSD`: `energy_soft_block + BLOCKED + display_ready=false`
- `NAS100`: 최근 샘플에서 `forecast_guard + PROBE + display_ready=false`
- `XAUUSD`: 최근 샘플에서 conflict observe 계열 non-ready

주의:

- 이 최근 패턴은 운영 데이터라 시간이 지나면 바뀔 수 있다
- 항상 최신 runtime/csv 기준으로 다시 확인해야 한다


## 14. 최종 결론

지금 가장 중요한 사실은 아래 두 줄로 정리된다.

- 현재 시스템은 이미 상당 부분 구축되어 있다.
- 지금 필요한 것은 새 기능보다 `경계 고정`, `표면 정직화`, `운영 진단 강화`다.

특히 정리 우선순위는 명확하다.

1. `consumer check single owner`
2. `BLOCKED visual continuity`
3. `runtime recent diagnostics`
4. `semantic diagnostics export`
5. `energy truthful logging`
6. `entry_service slimming`

이 순서를 지키면 지금 구조를 비교적 안전하게 정리할 수 있다.

반대로 이 순서를 무시하고 EntryService 내부 예외부터 늘리거나, chart에서 증상만 덮거나, runtime 표면을 강화하지 않은 채 ML/semantic을 더 얹으면 같은 종류의 drift가 다시 반복될 가능성이 높다.
