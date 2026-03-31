# CFD 현재 아키텍처 경계 객관 진단

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 아카이브에 정리된 대개편 의도와 현재 코드/런타임 상태를 교차검증해서, 지금 시스템이 어디까지 구축되었고 어디의 연결이 아직 약한지 객관적으로 정리하기 위한 진단 문서다.

핵심 질문은 아래 네 가지다.

- `ObserveConfirm -> Consumer -> Execution` 경계가 실제 코드에서 얼마나 지켜지고 있는가
- 최근에 생겼던 `blocked인데 READY처럼 보이던 현상`은 구조적으로 얼마나 해결되었는가
- semantic ML / rollout / runtime observability가 지금 수준에서 어디까지 신뢰 가능한가
- 지금 손보지 않으면 어떤 종류의 문제가 반복될 가능성이 큰가


## 2. 검증 범위

이번 진단은 문서만 읽고 추정한 것이 아니라, 아래 네 축을 함께 맞대어 본 targeted cross-check다.

### 2-1. 기준 문서

- `C:\Users\bhs33\Desktop\옵시디언(시찬)\Sichan\10_AI_Engineering\99_Projects_Archive\04_CFD_Analysis\대 개편\- 10. Observe_Confirm_Action Contract.md`
- `C:\Users\bhs33\Desktop\옵시디언(시찬)\Sichan\10_AI_Engineering\99_Projects_Archive\04_CFD_Analysis\대 개편\- 11. Consumer Roadmap.md`
- `C:\Users\bhs33\Desktop\옵시디언(시찬)\Sichan\10_AI_Engineering\99_Projects_Archive\04_CFD_Analysis\대 개편\- 14. Runtime Alignment_Handoff Hardening.md`

### 2-2. 실제 코드 검증 구간

- `backend/services/context_classifier.py:1004-1053`
- `backend/services/context_classifier.py:1558-1598`
- `backend/trading/engine/core/observe_confirm_router.py:1206-1218`
- `backend/trading/engine/core/observe_confirm_router.py:1255-1267`
- `backend/trading/engine/core/observe_confirm_router.py:1578-1623`
- `backend/services/entry_service.py:1838-1916`
- `backend/services/entry_service.py:3089-3116`
- `backend/services/entry_try_open_entry.py:618-645`
- `backend/trading/chart_painter.py:805-817`
- `backend/app/trading_application.py:416-444`
- `backend/app/trading_application.py:1216-1232`
- `backend/services/wait_engine.py:86-136`
- `backend/services/energy_contract.py:1419-1548`

### 2-3. 실제 런타임 / 데이터 검증 구간

- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- `data/trades/entry_decisions.csv`

### 2-4. 회귀 테스트 재확인

아래 테스트는 2026-03-27 기준으로 다시 실행해서 통과를 확인했다.

- `pytest tests/unit/test_entry_service_guards.py -k "energy_soft_block or layer_mode_policy_hard_block or probe_not_promoted" -q`
- `pytest tests/unit/test_chart_painter.py -k "prefers_consumer_check_ready_state or downgrades_soft_blocked_sell_ready_into_sell_wait" -q`
- `pytest tests/unit/test_trading_application_runtime_status.py -q`

주의:

- 이번 검증은 전체 레포 full audit이 아니라 핵심 경계 구간 집중 검증이다.
- full suite 전체는 이번 문서 작성 시점에 다시 돌리지 않았다.


## 3. 한 줄 총평

현재 구조는 `핵심 엔진이 없는 상태`가 아니라 `핵심 엔진은 상당 부분 구축되었지만, ownership 경계와 마지막 출력 표면이 아직 완전히 동결되지 않은 상태`에 가깝다.

즉 문제의 본질은 알고리즘 미구축보다 아래 세 가지다.

- `Consumer -> Execution` 경계가 아직 두껍고 중복 owner가 있다
- `Decision -> Visualization` 단계에서 의미가 일부 손실된다
- `Runtime -> Handoff` 표면이 아직 최근 흐름보다 마지막 한 줄 위주다


## 4. 상대 성숙도 평가

이 평가는 절대 점수가 아니라 현재 대개편 의도 대비 상대 성숙도를 나타낸다.

| 영역 | 상대 상태 | 평가 |
| --- | --- | --- |
| ObserveConfirm identity ownership | 양호 | 대개편 의도와 가장 잘 맞춰진 축 |
| Consumer input / migration wiring | 양호 | v2 중심 + compatibility bridge가 꽤 정리됨 |
| Consumer -> Execution boundary freeze | 미완 | EntryService가 아직 semantic/policy shaping을 일부 품고 있음 |
| Guard -> Stage -> Display 단일 owner | 미완 | 정책 owner가 2곳 이상으로 분리됨 |
| BLOCKED visual continuity | 부족 | 내부의 `BLOCKED`가 마지막 chart 레이어에서 `WAIT`로 뭉개짐 |
| Runtime observability | 보통 이하 | latest snapshot은 있으나 recent-window 진단이 약함 |
| Semantic rollout diagnostics export | 보통 이하 | 내부 진단은 있으나 운영 출력은 요약 중심 |
| Energy truthful usage logging | 미완 | 실제 branch-level usage보다 결과 기반 추론 비중이 큼 |
| Point-fix regression coverage | 양호 | 최근 이슈 관련 targeted test는 존재함 |
| End-to-end contract coverage | 미완 | observe-confirm부터 chart/runtime까지 한 번에 묶는 테스트는 약함 |


## 5. 현재 잘 구축된 연결

### 5-1. ObserveConfirm의 identity ownership은 생각보다 잘 정렬되어 있다

대개편 문서의 핵심은 `state는 lifecycle`, `archetype_id는 trade identity`, `forecast는 identity를 바꾸지 못한다`는 점이었다.

현재 코드에서 이 부분은 비교적 잘 살아 있다.

- `backend/services/context_classifier.py:1558-1575`에서 `energy_snapshot`은 계산하지만 `route_observe_confirm(...)`의 직접 입력으로 사용하지 않는다.
- `backend/trading/engine/core/observe_confirm_router.py:1578-1623`에서 routing policy를 메타데이터로 남기며, forecast의 역할을 `confidence_modulation_and_confirm_wait_split_only`로 명시한다.
- 같은 구간에서 `identity_override_allowed = False`, `side_override_allowed = False`를 못박고 있다.

이 뜻은, 적어도 router 수준에서는 `legacy energy가 identity owner`로 복귀한 상태는 아니라는 것이다.

### 5-2. WaitEngine은 이미 energy/layer hints를 실제로 읽고 있다

대개편 문서에서는 `ObserveConfirm -> Layer Mode -> Energy`를 실제 live branch가 소비해야 한다는 요구가 있었다.

현재 `backend/services/wait_engine.py:86-136`과 후속 계산 구간에서는 아래 항목을 실제로 읽는다.

- `action_readiness`
- `wait_vs_enter_hint`
- `soft_block_hint`

즉 WaitEngine 쪽은 개념만 있는 상태가 아니라 이미 hint-aware branch로 들어가 있다.

### 5-3. 최근 wrong READY 현상은 데이터 기준으로는 일단 잡힌 상태다

`data/trades/entry_decisions.csv` 전체 7012행을 기준으로 보면, 과거에는 `blocked_by != ""`이면서 `consumer_check_stage = READY` 또는 `consumer_check_entry_ready = true`였던 행이 412건 존재한다.

하지만 최근 300행에서는 그 수가 0건이었다.

즉 과거 기록은 남아 있지만, 최근 런타임 기준으로는 이번 수정이 실제로 먹히고 있다고 보는 편이 맞다.


## 6. 아직 부족한 연결과 구조적 약점

### 6-1. 가장 큰 약점: Guard -> Stage -> Display -> Visual contract의 단일 owner가 없다

현재 check stage와 display readiness의 1차 판정은 `backend/services/entry_service.py:1838-1916`에서 이뤄진다.

여기서는 아래를 함께 결정한다.

- `hard_block_reasons`
- `hard_block_guards`
- `display_blocked`
- `entry_ready`
- `probe_ready_but_blocked`
- 최종 `check_stage`
- 최종 `display_ready`

그런데 late block이나 execution-stage rewrite는 `backend/services/entry_try_open_entry.py:618-645`에서 다시 한 번 손본다.

여기서는 별도의 `late_display_suppress_guards`가 존재하고, 이 값에 따라 stage/display가 다시 바뀐다.

이 구조의 의미는 명확하다.

- 이번 bug는 고쳐졌지만
- 다음 guard가 추가될 때
- `entry_service`와 `entry_try_open_entry`를 동시에 맞추지 않으면
- 같은 종류의 어긋남이 다른 이름으로 재발할 가능성이 높다

즉 지금 시스템에서 가장 먼저 굳혀야 할 것은 `rule -> consumer check state -> final effective display state`를 한 곳에서 계산하는 공용 contract다.

### 6-2. EntryService가 아직 execution guard only보다 무겁다

대개편 문서의 의도는 `EntryService`를 execution guard 중심으로 얇게 만드는 것이었다.

그런데 현재 `backend/services/entry_service.py:3089-3116`에는 XAU symbol-specific energy relief가 남아 있다.

이 구간은 아래를 함께 본다.

- `symbol`
- `probe_plan_v1`
- `box_state`
- `bb_state`
- `energy_soft_block_reason`
- `energy_soft_block_strength`
- `candidate_support`
- `pair_gap`
- `same_side_barrier`

이 정도면 execution guard라기보다 scene-specific policy shaping에 가깝다.

이 구조를 오래 끌고 가면 생기는 문제는 아래와 같다.

- symbol tuning이 EntryService 내부에 계속 누적된다
- semantic/consumer/execution 경계가 다시 흐려진다
- 하나의 튜닝이 다른 setup이나 symbol에 예상치 않게 영향을 줄 수 있다

### 6-3. BLOCKED가 마지막 출력 표면에서 first-class 의미를 잃는다

현재 `backend/trading/chart_painter.py:805-817`의 번역 규칙은 아래와 같다.

- `READY -> *_READY`
- `PROBE -> *_PROBE`
- `OBSERVE 또는 BLOCKED -> *_WAIT`

이건 운영 관점에서 매우 중요한 약점이다.

내부에서는 `OBSERVE`와 `BLOCKED`를 분리해서 계산하지만, 운영자가 보는 마지막 레이어에서는 둘 다 `WAIT`로 보이기 때문이다.

이 상태에서는 아래 질문이 계속 어려워진다.

- 지금 이건 단순 관찰 단계인가
- 아니면 candidate는 있었는데 guard 때문에 막힌 것인가
- 왜 안 들어갔는가

즉 최근 bug의 뿌리는 단순히 잘못된 stage 한 건이 아니라, 시스템 마지막 표면에서 `BLOCKED`가 1급 상태로 유지되지 않는 구조와도 연결되어 있다.

### 6-4. runtime status가 recent-window 진단보다 latest snapshot 중심이다

`backend/app/trading_application.py:1216-1232`를 보면 현재 runtime status는 다음을 포함한다.

- `semantic_live_config`
- `semantic_rollout_state`
- `latest_signal_by_symbol`
- 기타 주문/루프 상태

이 자체는 유용하지만, 운영자가 실제로 알고 싶은 질문은 보통 아래와 같다.

- 최근 100행에서 blocked/observe/probe 비율이 어떻게 바뀌었는가
- 최근에도 wrong READY가 남는가
- 특정 guard가 급증했는가
- symbol별로 어떤 blocked reason이 지배적인가

이 질문에는 `latest_signal_by_symbol`만으로 답할 수 없다.

결국 지금도 `entry_decisions.csv`의 최근 200~300행을 따로 읽어야 진단이 가능하다.

즉 runtime status는 존재하지만, 운영용 진단 shape는 아직 얇다.

### 6-5. semantic shadow diagnostics는 내부에 있는데 운영 표면으로는 얇게 노출된다

`backend/app/trading_application.py:416-444`를 보면 `semantic_live_config` 안에 아래와 같은 요약은 담긴다.

- `mode`
- `symbol_allowlist`
- `shadow_runtime_state`
- `shadow_runtime_reason`
- `shadow_runtime_available_targets`

그리고 실제 2026-03-27 기준 런타임은 아래와 같았다.

- `mode = threshold_only`
- `symbol_allowlist = ["BTCUSD", "NAS100"]`
- `shadow_runtime_state = inactive`
- `shadow_runtime_reason = model_dir_missing`

하지만 앱 내부에는 `semantic_shadow_runtime_diagnostics` 객체가 더 자세하게 존재한다.

문제는 이 상세 진단이 runtime status의 1급 top-level 운영 계약으로 그대로 실리지 않는다는 점이다.

즉 현재는 `inactive인 건 알겠는데 왜 inactive인지 더 깊게 보려면 코드나 내부 객체를 다시 따라가야 하는` 상태다.

### 6-6. energy usage trace는 아직 branch-truth logging으로 보긴 어렵다

`backend/services/energy_contract.py:1419-1464`의 `resolve_entry_service_energy_usage(...)`는 payload 결과를 보고 `consumed_fields`를 추론한다.

예를 들면 아래와 같다.

- `soft_block_active`
- `core_reason == "energy_soft_block"`
- `block_reason == "energy_soft_block"`
- `confidence_delta`
- `forecast_gap_live_gate_used`

이 값들을 바탕으로 `action_readiness`, `soft_block_hint`, `priority_hint` 등을 사용했다고 판정한다.

그 후 `backend/services/energy_contract.py:1467-1548`에서 trace를 붙인다.

즉 trace가 완전히 무의미한 것은 아니지만, 가장 이상적인 형태는 아니다.

가장 강한 형태의 truthful logging은 아래와 같아야 한다.

- 실제 decision branch 내부에서
- 어떤 field를 읽었는지
- 어떤 분기 때문에 적용되었는지
- 그 자리에서 바로 기록하는 구조

현재는 그보다 한 단계 약한 `결과 기반 재구성` 성격이 남아 있다.

### 6-7. end-to-end contract tests가 아직 얇다

최근 수정과 관련된 targeted test는 있다.

- `tests/unit/test_entry_service_guards.py:4241` 부근의 `layer_mode_policy_hard_block`
- `tests/unit/test_entry_service_guards.py:4320` 부근의 `energy_soft_block`
- `tests/unit/test_chart_painter.py:398`의 soft-block downgrade
- `tests/unit/test_chart_painter.py:524`의 consumer check ready 우선 사용
- `tests/unit/test_trading_application_runtime_status.py:26`

하지만 아직 약한 것은 아래 형태의 통합 계약 테스트다.

- 동일 input에서 `observe_confirm_v2`
- `consumer_check_state_v1`
- `latest_signal_by_symbol`
- chart overlay event

가 한 번에 이어져서, `BLOCKED`와 `OBSERVE`가 끝까지 구분되는지 검증하는 형태다.

즉 지금은 point-fix 회귀는 괜찮아졌지만, contract continuity 회귀는 아직 약하다.


## 7. 최근 wrong READY 현상이 왜 생겼는가

이번 이슈의 구조적 원인은 단순히 if문 하나가 잘못되어서가 아니었다.

핵심 원인은 아래 세 가지가 겹친 결과로 보는 편이 맞다.

### 7-1. stage 계산과 최종 effective display 계산이 분리되어 있었다

`entry_service`에서 생성한 초기 check state가 있었고, 이후 `entry_try_open_entry`에서 late block을 반영하면서 실제 진실이 한 번 더 바뀌었다.

이때 두 owner가 완전히 같은 정책표를 공유하지 않으면 `blocked인데 READY 흔적이 남는` 문제가 생긴다.

### 7-2. runtime/visual 단계가 마지막 truth owner가 아니었다

최근 문제는 결국 운영자가 보는 표면에서 드러났는데, chart/runtime는 이미 한 번 계산된 값을 소비하는 쪽이었다.

즉 upstream에서 truth가 흔들리면 downstream이 그 흔들림을 그대로 드러내게 된다.

### 7-3. BLOCKED와 WAIT가 운영 표면에서 분리되지 않았다

`BLOCKED`가 시각적으로 별도 상태로 살아 있지 않으면, 실제 원인 분해가 늦어진다.

이번 문제도 단순 READY mismatch가 아니라 `candidate 존재 + execution/late guard block`이라는 의미가 충분히 표면화되지 않았던 점이 컸다.


## 8. 이 상태를 그대로 두면 어떻게 되는가

### 8-1. 같은 종류의 버그가 이름만 바꿔서 반복된다

다음에 새 guard가 추가되거나 symbol-specific 예외가 하나 더 붙으면, 이번과 유사한 `truth drift`가 다른 모양으로 반복될 가능성이 높다.

예:

- blocked인데 READY처럼 보임
- observe여야 하는데 probe처럼 보임
- chart는 wait인데 latest signal은 ready로 남음

### 8-2. 운영자가 보는 표면과 내부 진실의 거리감이 계속 남는다

chart와 runtime status가 끝단 truth surface 역할을 해야 하는데, 지금은 일부 의미가 중간에서 손실된다.

이 상태가 지속되면 디버깅 비용은 아래처럼 커진다.

- 먼저 chart를 보고
- 그다음 runtime_status를 보고
- 그래도 부족해서 csv 최근행을 열고
- 마지막에 코드 분기를 추적하게 된다

즉 운영 진단이 문서/사람 의존으로 남는다.

### 8-3. EntryService 내부의 정책 부채가 계속 누적된다

scene-specific relief가 EntryService 안에 더 쌓이면, 결국 이 파일이 `execution guard`가 아니라 `semantic afterburner`처럼 비대해진다.

그 결과는 아래와 같다.

- 변경 영향 범위를 예측하기 어려워짐
- symbol별 분기 증가
- 테스트 비용 증가
- 새 스레드 handoff 난이도 상승

### 8-4. semantic ML rollout 검증이 느려진다

ML rollout은 `semantic이 무엇을 말했는가`, `consumer가 어떻게 해석했는가`, `execution이 왜 막았는가`가 분리돼 보여야 빠르게 검증할 수 있다.

현재처럼 runtime observability가 얇으면 rollout이 붙을수록 아래 질문이 어려워진다.

- 지금 안 들어간 이유가 semantic 때문인가
- 아니면 consumer check 정책 때문인가
- 아니면 execution guard 때문인가

즉 ML을 더 붙일수록 오히려 운영 해석 비용이 올라갈 수 있다.


## 9. 우선순위 높은 보강 방향

### 9-1. 최우선: consumer check 계산 owner를 하나로 모아야 한다

우선순위 1번은 `guard -> stage -> display_ready -> blocked_display_reason -> visual severity`를 한 곳에서 계산하는 것이다.

의도는 간단하다.

- `entry_service`와 `entry_try_open_entry`에 흩어진 정책을 하나의 공용 resolver로 모은다
- upstream truth를 final truth로 사용한다
- runtime/chart는 그 결과를 번역만 한다

이 작업이 끝나면 다음 guard 추가 시 회귀 가능성이 크게 줄어든다.

### 9-2. BLOCKED를 끝까지 1급 상태로 보존해야 한다

차트에서 `OBSERVE`와 `BLOCKED`를 모두 `WAIT`로 번역하는 구조는 운영 진단을 약하게 만든다.

개선 방향은 두 가지 중 하나다.

- `BUY_BLOCKED` / `SELL_BLOCKED` 같은 별도 event family를 만든다
- 최소한 `WAIT` 안에 있어도 `blocked_kind` 또는 `blocked_reason_class`를 필수 표면 필드로 노출한다

핵심은 운영자가 마지막 표면만 봐도 `단순 관찰`과 `실제 차단`을 구분할 수 있어야 한다는 점이다.

### 9-3. EntryService에서 scene-specific policy를 점진적으로 걷어내야 한다

특히 symbol/scenario relief는 가능하면 아래 중 하나로 이동하는 편이 바람직하다.

- Consumer-level policy
- Layer mode policy
- Energy helper advisory layer

즉 EntryService는 아래에 더 가까워져야 한다.

- cooldown
- opposite lock
- position cap
- liquidity/spread
- order send safety

지금처럼 scene-specific semantic shaping이 남아 있으면 구조 부채가 누적된다.

### 9-4. runtime status에 recent-window diagnostics를 추가해야 한다

최소한 아래 정도는 top-level 운영 계약으로 있으면 좋다.

- 최근 50/200/300행 기준 stage 분포
- 최근 blocked reason top-N
- 최근 wrong READY count
- symbol별 blocked/probe/observe/ready 비율

이 값들이 있으면 csv를 직접 뒤지지 않고도 새 스레드나 운영 점검이 가능해진다.

### 9-5. semantic shadow diagnostics를 요약이 아니라 상세 계약으로도 내보내야 한다

현재는 `semantic_live_config`에 요약이 들어간다.

여기에 더해 아래가 별도 필드로 나가면 운영성이 좋아진다.

- shadow runtime diagnostics raw/detail payload
- model directory 존재 여부
- load 실패 상세
- available targets 계산 근거

### 9-6. energy usage logging은 decision branch 안에서 바로 기록하는 쪽이 이상적이다

현재의 결과 기반 재구성도 가치가 있지만, 장기적으로는 아래 형태가 더 좋다.

- 실제 분기점에서 consumed field를 append
- 분기 이름과 적용 이유를 함께 기록
- 사후 추론은 fallback 역할만 수행


## 10. 바로 손대야 하는 것 / 조금 뒤로 미뤄도 되는 것

### 10-1. 지금 바로 손대야 하는 것

- consumer check single-owner resolver
- `BLOCKED` visual/runtime continuity
- recent-window runtime diagnostics

이 세 가지는 최근에 실제로 문제를 만들었거나, 문제 재발 가능성을 크게 좌우하는 축이다.

### 10-2. 그다음 손대도 되는 것

- semantic shadow diagnostics 상세 export
- energy truthful usage logging 고도화
- end-to-end contract tests 확장

이쪽은 당장 엔진 오동작을 일으키는 축이라기보다, 운영성과 추적 가능성을 크게 높여주는 축이다.

### 10-3. 조심해서 손대야 하는 것

- EntryService 내부의 scene-specific relief 제거

이건 장기적으로 꼭 필요한 방향이지만, 이미 symbol별 tuning이 묻어 있기 때문에 한 번에 걷어내면 회귀 범위가 커질 수 있다.

따라서 아래 순서가 적합하다.

- 먼저 owner contract를 굳힌다
- 그다음 scene-specific branch를 inventory화한다
- 마지막에 Consumer/LayerMode/Energy로 점진 분리한다


## 11. 현재 시점의 객관 결론

현재 코드는 `개편 의도와 완전히 어긋난 상태`는 아니다.

오히려 아래는 분명한 진전이다.

- ObserveConfirm identity ownership은 상당히 정렬되었다
- WaitEngine은 실제 hint-aware 구조를 사용하고 있다
- 최근 wrong READY는 최근 300행 기준으로는 사라졌다
- semantic rollout도 bounded mode로 관리 가능한 형태를 갖추고 있다

하지만 아래 네 가지는 아직 미완 상태다.

- `Consumer -> Execution` 경계 동결
- `Guard -> Stage -> Display -> Visual` 단일 owner
- `BLOCKED`의 first-class 운영 표면화
- recent-window 중심 observability

따라서 지금 단계의 가장 정확한 평가는 다음과 같다.

`핵심 엔진은 이미 구축되었고, 지금 필요한 것은 기능 추가보다 경계 고정과 운영 표면 정직화다.`


## 12. 부록: 2026-03-27 기준 런타임 메모

### 12-1. semantic live / shadow 상태

- `semantic_live_config.mode = threshold_only`
- `semantic_live_config.symbol_allowlist = ["BTCUSD", "NAS100"]`
- `semantic_live_config.shadow_runtime_state = inactive`
- `semantic_live_config.shadow_runtime_reason = model_dir_missing`

### 12-2. 최근 300행 기준 wrong READY 점검

- 전체 csv 7012행 중 과거 wrong READY 흔적 412건
- 최근 300행 기준 wrong READY 0건

### 12-3. 최근 12행 관찰 패턴

- `BTCUSD`: 주로 `energy_soft_block + BLOCKED + display_ready=false`
- `NAS100`: 최근 샘플에서는 `forecast_guard + PROBE + display_ready=false`
- `XAUUSD`: 최근 샘플에서는 conflict observe 계열로 non-ready

주의:

- 위 패턴은 2026-03-27 당시 recent row 기준이며, 운영 데이터는 시간이 지나면 바뀔 수 있다.
- 새 스레드에서는 항상 `runtime_status.json`, `runtime_status.detail.json`, `entry_decisions.csv` 최근 200~300행을 함께 확인하는 것이 안전하다.
