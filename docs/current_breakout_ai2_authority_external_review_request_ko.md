# Current Breakout / AI2 Authority External Review Request

## 목적

이 문서는 다른 LLM이나 외부 조언자에게 현재 `breakout -> AI2 candidate bridge -> authority integration` 상태를 정확히 설명하고,
지금 어디가 막혀 있는지와 다음에 무엇을 바꿔야 하는지 조언받기 위한 상세 요청서다.

핵심 질문은 하나다.

> 왜 눈으로 보기엔 breakout/reclaim continuation처럼 보이는 장면이 있는데,
> 현재 live runtime에서는 `breakout_candidate_action_target = WAIT_MORE`,
> `breakout_candidate_direction = NONE`만 나오고 있는가?

---

## 한 줄 현재 진단

현재 breakout 라인은 `runtime detect -> detail-only 저장 -> manual/replay alignment -> canonical seed promotion -> preview dataset export`까지는 잘 닫혀 있다.

하지만 authority integration 단계에서 AI2 bridge에 연결해보니,

- AI2는 실제 live runtime에 올라와 있고
- fresh row에도 새 candidate 필드가 기록되고 있지만
- breakout 쪽은 아직 `ENTER_NOW` 후보를 한 건도 만들지 못하고 있다.

최신 raw audit 기준 현재 병목은 threshold보다 더 앞단이다.

> breakout runtime이 기대하는 `breakout_up / breakout_down` 축이 현재 recent detail payload에서 사실상 비어 있어서,
> direction이 전부 `NONE`, state가 전부 `pre_breakout`, overlay target이 전부 `WAIT_MORE`로 고정되고 있다.

---

## 최신 업데이트 한 줄 진단

이 문서 초안 작성 이후 `AI2a~AI2d`를 실제로 일부 구현했다.

현재 상태는 처음보다 한 단계 더 좁혀졌다.

> 이제 breakout은 아예 못 읽는 상태는 벗어났지만,
> 최근 창에서는 대부분 `direction = NONE`에 머물고,
> 겨우 살아난 `initial_breakout` 1건도 `forecast confirm`이 반대로 잡혀 `confirm_conflict_hold`로 보류된다.

즉 현재 질문은 더 이상

- `breakout을 읽을 수 있는가?`

가 아니라,

- `direction을 더 잘 만들려면 무엇을 바꿔야 하는가?`
- `breakout direction`과 `forecast confirm_side`가 충돌할 때 누가 더 우선해야 하는가?
- `overlay는 지금이 맞게 보수적인가, 아니면 너무 강하게 hold하고 있는가?`

로 바뀌었다.

최근 추가로 받은 조언을 반영하면,
현재 다음 병목은 `direction resolver + confirm conflict 처리 규칙`으로 보는 것이 가장 정확하다.

핵심 권고는 아래 5개다.

1. threshold는 아직 건드리지 않기
2. direction resolver를 더 세분화하기
3. breakout type을 `initial / reclaim / continuation`으로 분리하기
4. forecast confirm을 owner가 아니라 `조정자(adjuster)`로 강등하기
5. `WAIT_MORE`와 `ENTER_NOW` 사이에 `WATCH_BREAKOUT / PROBE_BREAKOUT` 같은 중간 상태를 두기

즉 지금은

- `breakout을 읽느냐`

보다

- `읽은 breakout을 어떤 타입으로 분류하느냐`
- `forecast와 충돌할 때 어떻게 강등하느냐`

가 더 중요한 상태다.

---

## 바로 붙여넣기용 짧은 질문

아래 블록은 다른 LLM에 바로 붙여넣어도 되는 짧은 버전이다.

```text
CFD breakout AI2 authority integration 상황 조언이 필요합니다.

현재 breakout 라인은 runtime detect -> detail-only 저장 -> manual/replay alignment -> canonical seed promotion -> preview dataset export까지는 닫혀 있습니다.

최근 구현:
1. breakout_up/down direct 축이 없어도 upper_break_up / lower_break_down / mid_reclaim_up / mid_lose_down을 proxy breakout axis로 bridge
2. micro_breakout_readiness_state가 비어 있으면 surrogate readiness(COILED/BUILDING/READY)를 생성
3. overlay는 effective readiness를 읽고, surrogate-ready + confirm 정렬 + bounded barrier/failure 조건일 때만 ENTER_NOW를 허용하며, 현재 conflict는 `confirm_conflict_hold`로 기록

최신 raw audit:
- breakout_up_nonzero_count = 94
- breakout_down_nonzero_count = 94
- breakout_axis_mode_counts = {"proxy": 94}
- breakout_direction_counts = {"NONE": 93, "UP": 1}
- breakout_state_counts = {"initial_breakout": 1, "pre_breakout": 93}
- effective_breakout_readiness_counts = {"BUILDING_BREAKOUT": 1, "COILED_BREAKOUT": 3}
- overlay_target_counts = {"WAIT_MORE": 94}
- overlay_reason_summary_counts = {"confirm_conflict_hold|wait_more": 1, "pre_breakout|wait_more": 93}

즉 axis는 살아났고 readiness/state도 일부 생겼지만, 대부분 direction이 NONE이고, 유일한 initial_breakout 1건도 breakout_direction=UP인데 forecast confirm_side=SELL이라 confirm_conflict_hold로 막힙니다.

질문:
1. 지금 다음 병목은 direction resolver 쪽이라고 보는 게 맞나요?
2. breakout_direction과 forecast confirm_side가 충돌할 때, overlay는 지금처럼 hold하는 게 맞나요, 아니면 breakout event 자체를 더 우선해야 하나요?
3. direction NONE이 너무 많은데, 다음은 threshold 조정보다 direction 생성 로직(예: axis weighting, confirm fallback, reclaim vs continuation 분리)을 먼저 손보는 게 맞나요?
4. breakout과 forecast confirm은 서로 다른 owner로 보고 conflict resolver를 따로 둬야 하나요?
5. `WAIT_MORE`와 `ENTER_NOW` 사이에 `WATCH_BREAKOUT / PROBE_BREAKOUT` 같은 중간 상태를 두는 것이 맞나요?

실행 owner를 바로 바꾸려는 게 아니라, log-only/bounded candidate 단계에서 어떤 순서로 조정하는 게 맞는지 조언 부탁드립니다.
```

---

## 최신 조언을 반영한 현재 입장

최근 추가로 받은 조언을 반영하면,
현재 breakout 병목은 `보수적인 threshold`보다 `데이터 의미 연결 문제`로 보는 것이 더 정확하다.

핵심 진단은 아래와 같다.

> 지금은 breakout이 없는 것이 아니라,
> breakout이라는 언어로 번역되지 않은 상태다.

이 해석에서 바로 따라오는 현재 입장은 다음과 같다.

1. 지금은 threshold를 먼저 만지면 안 된다
   - `breakout_up/down = 0`인 상태에서는 threshold를 내려도 효과가 없다
2. `bridge + upstream`를 둘 다 봐야 한다
   - runtime bridge = 응급처치
   - upstream axis materialization = 정식 수선
3. readiness surrogate가 중간에 필요하다
   - direction/state가 조금 살아나더라도 readiness가 비면 overlay가 다시 `WAIT_MORE`에 머물 수 있다
4. breakout type을 분리해야 한다
   - `initial_breakout`
   - `reclaim_breakout`
   - `continuation_breakout`
5. 상단/하단은 1차 구현에서 대칭 proxy로 시작할 수 있다
   - 상단:
     - `upper_break_up`
     - `mid_reclaim_up`
   - 하단:
     - `lower_break_down`
     - `mid_lose_down`
   - 다만 이후 raw audit로 비대칭을 별도 확인해야 한다

즉 현재 구현 방향은:

- threshold tuning 이전에
- axis bridge
- direction/state 재검증
- readiness surrogate
- overlay 재검증
- candidate bridge 재연결

순으로 가는 것이 맞다고 본다.

---

## 큰 구조

현재 관련 시스템은 아래 3개 층으로 보면 된다.

### 1. Breakout Learning Line

- live runtime에서는 breakout을 독립 semantic owner처럼 감지만 한다.
- 실제 action은 바꾸지 않고 detail-only로 저장한다.
- offline에서 manual/replay alignment를 거쳐 canonical seed로 승격한다.
- 마지막에 breakout preview training parquet로 내보낸다.

즉 breakout은 이미:

- runtime detect
- manual/replay validation
- canonical seed promotion
- preview dataset export

까지 도달한 상태다.

### 2. Authority Integration Line

authority map 진단 이후 entry authority를 다시 묶는 로드맵을 시작했다.

- `AI1 Entry Authority Trace Extraction`: 완료
- `AI2 Baseline-No-Action Candidate Bridge`: 완료

현재 AI2는 `baseline_no_action` row에 대해 다음 source를 bounded candidate surface로 계산만 한다.

- `semantic_candidate`
- `shadow_candidate`
- `state25_candidate`
- `breakout_candidate`

아직 live action을 직접 바꾸지는 않는다.

### 3. Semantic / Shadow / Live Rollout Line

- semantic shadow bundle은 bounded candidate/runtime stage까지 이미 검증됨
- semantic live rollout은 현재 `log_only`
- authority integration은 이 위에서 실제 실행권을 조금씩 옮기기 위한 다음 축이다

---

## 현재까지 구현된 breakout 라인 요약

### Runtime Layer

breakout runtime 계약:

- [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
- 핵심 builder: `build_breakout_event_runtime_v1`

overlay 계약:

- [breakout_event_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_overlay.py)
- 핵심 builder:
  - `build_breakout_event_overlay_candidates_v1`
  - `build_breakout_event_overlay_trace_v1`

runtime 주입 지점:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- semantic owner bundle 생성 후 breakout runtime / overlay를 같이 계산한다.

중요한 점:

- 현재 breakout은 live entry/exit policy를 직접 바꾸지 않는다.
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)에서 detail-only payload로 저장된다.

### Manual / Replay Learning Layer

이미 구현된 주요 레이어:

- manual learning bridge
- manual-only review recovery
- overlap seed draft
- backfill scaffold
- replay learning alignment
- aligned training seed promotion
- gap recovery / external source request
- preview training export

즉 breakout은 단순 아이디어가 아니라,
이미 manual/replay/canonical/preview dataset까지 이어진 완성된 offline line이다.

---

## 현재 authority integration에서 relevant한 구현

### AI1. Entry Authority Trace Extraction

관련 파일:

- [entry_authority_trace.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_authority_trace.py)
- [build_entry_authority_trace.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_entry_authority_trace.py)

최신 기준:

- [entry_authority_trace_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_authority_trace_latest.json)
- 최근 200행 중:
  - `baseline_no_action_count = 149`
  - `entered_count = 10`
  - `score_threshold_gate = 24`
  - `post_entry_guard = 1`
  - `utility_gate_veto_count = 0`

해석:

- 현재 live entry 실권은 semantic이 아니라 여전히 baseline 쪽에 있다.
- 가장 큰 병목은 `baseline_no_action`이 너무 많다는 점이다.

### AI2. Baseline-No-Action Candidate Bridge

관련 파일:

- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)
- [baseline_no_action_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/baseline_no_action_bridge.py)
- [build_baseline_no_action_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_baseline_no_action_bridge.py)

AI2는 실제 live runtime에 로드되었고,
`entry_decisions.csv`는 이미 새 candidate 필드를 기록하고 있다.

최신 기준:

- [baseline_no_action_bridge_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/baseline_no_action_bridge_latest.json)
- 최근 105행 중:
  - `baseline_no_action_row_count = 75`
  - `bridge_available_count = 0`
  - `bridge_selected_count = 0`
  - `breakout_candidate_count = 0`

해석:

- AI2가 안 올라온 게 아니다.
- 올라와 있지만, 현재 fresh row에서는 candidate coverage가 0이다.

---

## 최신 AI2a~AI2d 진행 상태

초기에는 breakout source가 전부 `WAIT_MORE / NONE`이었고,
raw blocker도 `missing_breakout_response_axis`였다.

지금은 아래 단계까지 진행했다.

### AI2a. Breakout Response-Axis Bridge

- [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
- 현재는 direct `breakout_up/down`이 없어도
  - `upper_break_up`
  - `lower_break_down`
  - `mid_reclaim_up`
  - `mid_lose_down`
  을 proxy breakout axis로 읽는다.
- recent payload의 `response_vector_v2`가 문자열 JSON이어도 파싱해서 읽는다.

최신 결과:

- `breakout_up_nonzero_count = 94`
- `breakout_down_nonzero_count = 94`
- `breakout_axis_mode_counts = {"proxy": 94}`
- `breakout_up_source_counts = {"mid_reclaim_up_proxy": 43, "upper_break_up": 51}`
- `breakout_down_source_counts = {"lower_break_down": 4, "mid_lose_down_proxy": 90}`

즉 `missing_breakout_response_axis` 단계는 벗어났다.

### AI2b. Direction / State Revalidation

최신 결과:

- `breakout_direction_counts = {"NONE": 93, "UP": 1}`
- `breakout_state_counts = {"initial_breakout": 1, "pre_breakout": 93}`
- `raw_blocker_family_counts = {"direction_threshold_not_met": 93, "overlay_confidence_below_enter_threshold": 1}`

즉 direction/state는 완전히 죽어 있지 않지만, 아직 대부분이 `NONE / pre_breakout`이다.

### AI2c. Readiness Surrogate

현재는 `micro_breakout_readiness_state`가 비어 있으면 runtime에서 surrogate readiness를 만든다.

최신 결과:

- `effective_breakout_readiness_counts = {"BUILDING_BREAKOUT": 1, "COILED_BREAKOUT": 3}`

즉 readiness는 이제 완전 빈 상태가 아니다.

### AI2d. Overlay Recheck

overlay는 이제 `effective_breakout_readiness_state`를 실제로 읽고 있다.

현재 규칙:

- surrogate-ready + confirm 정렬 + bounded barrier/failure 조건이면 `ENTER_NOW`
- 그렇지 않으면 이유를 남기고 `WAIT_MORE`

최신 결과:

- `overlay_target_counts = {"WAIT_MORE": 94}`
- `overlay_reason_summary_counts = {"confirm_conflict_hold|wait_more": 1, "pre_breakout|wait_more": 93}`

즉 overlay는 readiness/state를 읽고는 있지만,
현재 창에서는 아직 `ENTER_NOW`를 하나도 만들지 못했다.

---

## AI2 coverage audit에서 보이는 현재 상태

관련 파일:

- [entry_candidate_coverage_audit.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_coverage_audit.py)
- [build_entry_candidate_coverage_audit.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_entry_candidate_coverage_audit.py)

최신 기준:

- [entry_candidate_coverage_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_candidate_coverage_audit_latest.json)

현재 수치:

- `recent_row_count = 105`
- `baseline_no_action_row_count = 75`
- `bridge_available_count = 0`
- `bridge_selected_count = 0`
- `all_candidate_blank_count = 75`
- `semantic_candidate_available_count = 0`
- `shadow_candidate_available_count = 0`
- `state25_candidate_available_count = 0`
- `breakout_candidate_available_count = 0`
- `breakout_enter_now_count = 0`
- `breakout_wait_more_count = 75`
- `breakout_direction_none_count = 75`

분포:

- `action_none_reason_counts = {"observe_state_wait": 38, "probe_not_promoted": 37}`
- `blocked_by_counts = {"middle_sr_anchor_guard": 37, "outer_band_guard": 10}`
- `core_reason_counts = {"core_shadow_observe_wait": 75}`
- `state25_binding_mode_counts = {"log_only": 75}`
- `state25_threshold_stage_scope_hit_counts = {"false": 75}`

해석:

- breakout은 현재 fresh baseline-no-action rows에서 전부 `WAIT_MORE / NONE`
- state25도 현재 창에서는 실질 candidate로 못 올라온다
- semantic/shadow/state25/breakout 네 source 모두 현재는 candidate action을 만들지 못하고 있다

즉 AI2 문제는 “bridge bug”보다 “source들이 현재 후보를 못 만들고 있음”이었다.
지금은 그중 breakout source를 실제로 살리는 작업을 진행했고,
현재 병목은 `candidate source가 완전히 비어 있음`에서
`direction 대부분 NONE + 살아난 1건의 confirm conflict`로 이동했다.

---

## breakout raw audit에서 확인된 더 직접적인 blocker

이 부분이 가장 중요하다.

관련 파일:

- [breakout_runtime_raw_audit.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_runtime_raw_audit.py)
- [build_breakout_runtime_raw_audit.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_breakout_runtime_raw_audit.py)

이 audit는 `entry_decisions.csv`의 fresh baseline-no-action rows를
`entry_decisions.detail.jsonl`의 detail payload와 다시 붙이고,
그 payload로 breakout runtime/overlay를 재계산해서 raw blocker를 본다.

최신 기준:

- [breakout_runtime_raw_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/breakout_runtime_raw_audit_latest.json)

현재 수치:

- `recent_row_count = 200`
- `baseline_no_action_row_count = 145`
- `detail_match_count = 145`
- `breakout_up_nonzero_count = 0`
- `breakout_down_nonzero_count = 0`
- `direction_none_count = 145`
- `state_pre_breakout_count = 145`
- `overlay_enter_now_count = 0`
- `overlay_wait_more_count = 145`
- `avg_confirm_score = 0.07833`
- `avg_false_break_score = 0.367666`
- `avg_continuation_score = 0.162459`
- `raw_blocker_family_counts = {"missing_breakout_response_axis": 145}`

핵심 해석:

> 지금 문제는 단순히 `ENTER_NOW` 문턱이 높아서가 아니라,
> breakout runtime이 방향을 만들 때 사용하는 `breakout_up / breakout_down` 축 자체가
> recent detail payload에서 사실상 비어 있다는 점이다.

즉 현재는:

- direction이 전부 `NONE`
- state가 전부 `pre_breakout`
- overlay target이 전부 `WAIT_MORE`

로 떨어지는 것이 코드상 자연스러운 결과다.

---

## 샘플에서 직접 확인한 사실

최근 detail payload를 직접 열어보면,

- `breakout_event_runtime_v1` 자체는 detail에 저장되지 않지만
- raw input이 되는 detail payload는 존재한다
- `forecast_state25_runtime_bridge_v1`도 detail에 존재한다

그런데 최근 샘플 payload를 보면:

- `micro_breakout_readiness_state`는 비어 있고
- `response_vector_v2`에는
  - `upper_break_up`
  - `lower_break_down`
  - `mid_reclaim_up`
  - `mid_lose_down`
  는 있지만
  - `breakout_up`
  - `breakout_down`
  축은 없다

현재 [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)의 `_response_breakout_scores(...)`는

- `position_energy_surface_v1.response.breakout_up/down`
- 또는 `response_vector_v2.breakout_up/down`

만 읽는다.

즉 현재 recent row에서는:

- `_response_breakout_scores(...) -> (0.0, 0.0)`
- `_resolve_direction(...) -> NONE`
- `_resolve_breakout_state(...) -> pre_breakout`
- overlay -> `WAIT_MORE`

가 되어버린다.

---

## 왜 이게 중요한가

눈으로 보면 breakout/reclaim continuation처럼 보이는 장면이 있어도,
현재 runtime 계약은 그 장면을 “돌파 축이 살아 있는 breakout”으로 해석할 재료를 못 받고 있을 수 있다.

즉 이 문제는:

1. threshold가 살짝 높다
2. overlay가 너무 보수적이다

보다 더 앞단 문제일 가능성이 크다.

지금은 오히려:

> runtime breakout input contract와 실제 runtime response surface가 서로 안 맞고 있다

는 쪽이 더 강한 가설이다.

즉 지금은 tuning problem이라기보다 translation / contract problem으로 보는 것이 더 타당하다.

---

## 지금 코드에서 중요한 함수 / 지점

### breakout runtime

- [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
- 중요 함수:
  - `_response_breakout_scores`
  - `_resolve_direction`
  - `_resolve_breakout_state`
  - `build_breakout_event_runtime_v1`

현재 핵심 포인트:

- `_response_breakout_scores`가 `breakout_up/down`만 읽는다
- recent detail payload에는 해당 축이 실질적으로 없다

### breakout overlay

- [breakout_event_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_overlay.py)
- 중요 함수:
  - `build_breakout_event_overlay_candidates_v1`

현재 로직:

- `initial_breakout` 또는 `breakout_pullback`
- `breakout_confidence >= 0.55`
- `breakout_failure_risk <= 0.55`

를 만족해야 주로 `ENTER_NOW`

하지만 지금은 direction이 `NONE`, state가 `pre_breakout`이라
overlay까지 가기 전에 이미 `WAIT_MORE`가 된다.

### AI2 bridge

- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)
- 중요 함수:
  - `_build_breakout_candidate`

현재 로직:

- runtime available
- overlay enabled
- `candidate_action_target = ENTER_NOW`
- direction in `UP/DOWN`
- `breakout_detected = true`
- confidence/failure risk 문턱 통과

를 모두 만족해야 `BUY/SELL` 후보가 된다.

즉 runtime/overlay가 `pre_breakout -> WAIT_MORE`면 AI2는 당연히 후보를 못 만든다.

### runtime injection

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- breakout runtime/overlay는 semantic owner bundle 안에서 계산되고
- AI2 bridge는 그 결과를 소비한다

---

## 실무적으로 지금 확정된 것

### 이미 확정된 사실

1. AI2 bridge는 live runtime에 실제로 올라와 있다
2. fresh rows에도 candidate surface 필드가 실제로 기록되고 있다
3. current observation window에서 breakout 후보가 0인 것은 bridge 미작동 때문이 아니다
4. raw audit 기준 현재 recent rows는 breakout runtime input 축이 비어 있다

### 아직 확정되지 않은 것

1. `breakout_up/down` 축을 upstream에서 새로 만들어야 하는지
2. 아니면 `upper_break_up / lower_break_down / mid_reclaim_up / mid_lose_down` 같은 기존 축을
   breakout runtime에서 bridge해서 읽으면 되는지
3. `micro_breakout_readiness_state`가 비어 있는 current payload를
   별도 derivation으로 채워야 하는지
4. 기존 guard가 breakout candidate를 너무 빨리 observe로 눌러버리는지

---

## 외부 조언이 필요한 정확한 질문

### 질문 1. 입력 축을 어떻게 맞추는 게 맞는가

현재 recent detail payload에는 `breakout_up/down` 축이 없고,
기존 response axis는 `upper_break_up / lower_break_down / mid_reclaim_up / mid_lose_down`처럼 나와 있다.

여기서 가장 좋은 선택은 무엇인가?

1. `breakout_event_runtime.py`에서 기존 axis를 bridge해서 `breakout_up/down`처럼 해석한다
2. upstream response surface에서 진짜 `breakout_up/down` 축을 새로 materialize한다
3. 둘 다 하고, runtime은 먼저 bridge로 살리고 나중에 upstream 정식 축으로 교체한다

### 질문 2. 현재 raw blocker를 보면 threshold 문제가 주범인가, 입력 contract mismatch가 주범인가

현재 수치는:

- `breakout_up_nonzero_count = 0`
- `breakout_down_nonzero_count = 0`
- `direction_none_count = 145`
- `raw_blocker_family = missing_breakout_response_axis 145`

이 상태를 보면 threshold 완화보다 입력 축 연결이 먼저라는 해석이 맞는가?

### 질문 3. breakout runtime에서 기존 axis를 bridge한다면 어떤 mapping이 가장 안전한가

예를 들어:

- `upper_break_up` -> breakout up 성격
- `lower_break_down` -> breakout down 성격
- `mid_reclaim_up` -> reclaim-followthrough breakout up 후보
- `mid_lose_down` -> reclaim-fail/breakdown 후보

처럼 읽어도 되는지,
아니면 이런 mapping은 leakage/semantic confusion 위험이 큰지 판단이 필요하다.

### 질문 4. `micro_breakout_readiness_state`가 빈 경우의 처리

현재 recent rows에서는 `micro_breakout_readiness_state`가 거의 비어 있다.

이 경우:

1. 빈 값이면 그냥 pre_breakout 유지
2. response axis + forecast + scene family로 surrogate readiness를 만든다
3. micro breakout readiness 자체를 upstream에서 별도 산출한다

중 어떤 방향이 맞는가?

### 질문 5. AI2에서 breakout candidate를 bounded하게 활성화하려면 어디까지 허용해야 하는가

현재 AI2 breakout candidate는 꽤 보수적이다.

외부 조언이 필요한 부분:

- direction이 `UP/DOWN`만 나오면 `breakout_detected`가 꼭 true여야 하는지
- `initial_breakout`에서만 enter를 허용할지, `breakout_continuation`도 허용할지
- `failure_risk <= 0.55` 같은 문턱을 당분간 유지할지
- 현재는 raw input부터 비어 있으니 overlay threshold는 나중에 보는 게 맞는지

### 질문 6. 다음 구현 순서를 어떻게 잡는 게 좋은가

현재 우리가 생각하는 우선순위는:

1. breakout response-axis bridge 또는 upstream axis materialization
2. raw audit 재실행
3. direction/state/overlay target 분포 재확인
4. 그 다음 overlay threshold / AI2 breakout candidate 문턱 조정
5. 마지막에 utility/guard와의 authority 통합 추가

이 순서가 맞는지,
아니면 먼저 다른 레이어를 건드려야 하는지 조언이 필요하다.

---

## 우리가 지금 원하지 않는 것

다른 LLM이 아래 방향을 바로 추천하면 현재 맥락과 안 맞을 가능성이 크다.

- manual truth를 live breakout runtime에 직접 넣는 것
- breakout을 바로 full live owner로 승격하는 것
- AI2/authority bridge를 건너뛰고 breakout rule을 즉시 진입 규칙으로 박는 것
- raw axis mismatch를 무시한 채 threshold만 풀어버리는 것

현재 우리가 원하는 건:

- no-leakage 유지
- bounded candidate bridge 유지
- raw input contract를 먼저 맞춘 뒤
- 그 다음 authority 통합을 진행하는 것이다.

---

## 요약

지금 breakout 라인은 offline/manual/preview 쪽으로는 상당히 잘 닫혀 있다.

문제는 authority integration에서 AI2 bridge에 연결했을 때,
현재 live recent rows에서 breakout이 `ENTER_NOW` 후보로 전혀 올라오지 않는다는 점이다.

최신 raw audit 기준으로는:

> breakout이 보수적이라서 못 올라오는 수준이 아니라,
> runtime이 읽는 `breakout_up/down` 입력 축 자체가 recent payload에서 비어 있어서
> direction이 `NONE`, state가 `pre_breakout`, overlay가 `WAIT_MORE`로 고정되고 있다.

그래서 지금 필요한 조언은:

- threshold를 조금 풀까?

가 아니라,

- breakout runtime 입력 축을 어떻게 다시 연결할까?
- 기존 response axis를 breakout axis로 bridge해도 될까?
- upstream에 진짜 breakout axis를 만드는 게 더 맞을까?
- 어떤 순서로 authority integration을 계속 진행해야 할까?

에 대한 것이다.
