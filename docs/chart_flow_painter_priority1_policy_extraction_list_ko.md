# Chart Flow Painter Priority 1 Policy Extraction List

## 목적

이 문서는 `chart_painter.py`에서 가장 먼저 `common_expression_policy_v1`로 추출해야 할 항목만 따로 모은 실행용 목록이다.

중요:

- 이 문서는 아직 코드 변경 문서가 아니다
- 구현 순서와 범위를 좁히기 위한 `Priority 1 extraction checklist`다
- router 항목은 제외하고, painter가 owner이거나 painter에서 먼저 공통 policy를 읽어야 하는 항목만 다룬다


## 기준 문서

- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase1_painter_implementation_checklist_ko.md`

이 문서의 기준은 `common_expression_policy_v1`이며,
여기서 말하는 Priority 1은 `가장 먼저 빼야 하는 painter baseline`을 뜻한다.


## 범위

이번 Priority 1에 포함:

- `semantics`
- `translation`
- painter 쪽 `probe` baseline

이번 Priority 1에 제외:

- `scoring`
- `visual.wait_brightness_by_event_kind`
- `visual.base_color_by_event_kind`
- `anchor`
- symbol override 실제 테이블화

즉 이번 단계의 목표는
`painter가 event family 의미와 probe/wait 번역 규칙을 공통 policy에서 읽게 만드는 것`이다.


## 대상 코드

주 대상 파일:

- `backend/trading/chart_painter.py`

우선 대상 함수:

- `_resolve_flow_event_kind(...)`
- `_resolve_blocked_structural_wait(...)`
- `_resolve_flow_observe_side(...)`
- `_resolve_probe_visual_allowed(...)`

참고 함수:

- `_flow_event_signal_score(...)`
- `_flow_event_color(...)`
- `_event_price(...)`


## Priority 1 추출 원칙

1. event family 의미를 바꾸지 않는다
2. hardcoded baseline만 policy로 뺀다
3. symbol-specific scene 예외는 아직 override hook로 남긴다
4. 구현 순서상 `translation -> probe`가 먼저다
5. rendering 세부값은 다음 단계로 미룬다


## Extraction List

### Group A. Semantics / Translation

| 항목 | 현재 위치 | 새 policy 필드 | 지금 빼야 하는 이유 | 위험도 |
| --- | --- | --- | --- | --- |
| directional wait 허용 | `_resolve_flow_event_kind(...)` | `semantics.directional_wait_enabled` | `WAIT + BUY/SELL` 의미를 하드코딩에서 분리해야 함 | 낮음 |
| soft block downgrade | `_resolve_flow_event_kind(...)` | `semantics.soft_block_downgrades_ready` | `execution_soft_blocked`, `energy_soft_block` 처리 기준을 공통화해야 함 | 낮음 |
| structural wait recovery on/off | `_resolve_flow_event_kind(...)`, `_resolve_blocked_structural_wait(...)` | `semantics.structural_wait_recovery_enabled` | buy/sell이 neutral `WAIT`에 묻히지 않게 하는 공통 규칙 | 낮음 |
| flat exit suppression painter guard | `_resolve_flow_event_kind(...)` | `semantics.flat_exit_suppression_enabled`, `semantics.terminal_exit_requires_position` | flat인데 exit family가 보이는 것을 painter에서도 막아야 함 | 낮음 |
| neutral block guards | `_FLOW_NEUTRAL_BLOCK_GUARDS`, `_resolve_flow_event_kind(...)`, `_resolve_probe_visual_allowed(...)` | `translation.neutral_block_guards` | 가드 목록이 공통 baseline인지 명확히 해야 함 | 낮음 |
| structural wait recovery guards | `_resolve_blocked_structural_wait(...)` | `translation.structural_wait_recovery_guards` | 어떤 guard가 directional wait 복원을 허용하는지 고정 필요 | 낮음 |
| structural wait recovery reasons | `_resolve_blocked_structural_wait(...)` | `translation.structural_wait_recovery_reasons` | 어떤 reason에서만 복원되는지 policy로 분리 필요 | 낮음 |
| watch suffix 매핑 | `_resolve_flow_event_kind(...)`, `_resolve_flow_observe_side(...)` | `translation.watch_reason_suffix_by_side` | `buy_watch`, `sell_watch` 접미사 해석을 baseline으로 뽑아야 함 | 낮음 |
| conflict neutral 유지 | `_resolve_blocked_structural_wait(...)`, `_resolve_flow_event_kind(...)` | `translation.conflict_reason_prefixes` | conflict row가 directional wait로 잘못 보이지 않게 해야 함 | 낮음 |
| probe promotion gate neutralization | `_resolve_flow_event_kind(...)` | `translation.probe_promotion_gate_neutralization_enabled` | probe가 promotion 실패했을 때 neutral 처리 규칙을 고정해야 함 | 중간 |
| edge-pair directional fallback | `_resolve_flow_event_kind(...)` | `translation.edge_pair_directional_wait_fallback_enabled` | side가 비었을 때 edge-pair winner로 wait를 살리는 fallback을 baseline화 | 중간 |
| scene side fallback | `_resolve_flow_observe_side(...)` | `translation.scene_side_fallback_enabled` | `probe_scene_id` 기반 side 보조 추론을 하드코딩에서 분리 | 중간 |


### Group B. Probe Baseline

| 항목 | 현재 위치 | 새 policy 필드 | 지금 빼야 하는 이유 | 위험도 |
| --- | --- | --- | --- | --- |
| upper probe 최소 support | `_resolve_probe_visual_allowed(...)` | `probe.upper_min_support_by_side` | upper probe 시각화 문턱을 공통 baseline으로 뽑아야 함 | 중간 |
| upper probe 최소 pair gap | `_resolve_probe_visual_allowed(...)` | `probe.upper_min_pair_gap_by_side` | upper probe 문턱의 숫자를 policy화해야 함 | 중간 |
| lower probe 최소 support | `_resolve_probe_visual_allowed(...)` | `probe.lower_min_support_by_side` | lower rebound probe 문턱을 공통 baseline으로 뽑아야 함 | 중간 |
| lower probe 최소 pair gap | `_resolve_probe_visual_allowed(...)` | `probe.lower_min_pair_gap_by_side` | lower rebound probe gap 기준을 policy화해야 함 | 중간 |
| promotion gate support penalty | `_resolve_probe_visual_allowed(...)` | `probe.promotion_gate_support_penalty` | promotion gate 추가 문턱을 분리해야 함 | 중간 |
| promotion gate pair gap penalty | `_resolve_probe_visual_allowed(...)` | `probe.promotion_gate_pair_gap_penalty` | promotion gate gap penalty를 공통값으로 만들어야 함 | 중간 |
| blocked quick states | `_resolve_probe_visual_allowed(...)` | `probe.blocked_quick_states` | probe 억제에 쓰는 quick state 목록을 분리해야 함 | 낮음 |


## Priority 1에서 남겨둘 Override Hook

아래 항목은 Priority 1에서 baseline으로 빼지 않고,
일단 `symbol override hook`로 남겨두는 것이 맞다.

| 항목 | 현재 위치 | 남겨두는 이유 |
| --- | --- | --- |
| `xau_second_support_buy_probe` 특수 gate | `_resolve_flow_event_kind(...)`, `_resolve_probe_visual_allowed(...)` | XAU 전용 scene 예외라 baseline이 아님 |
| `xau_upper_sell_probe` 특수 gate | `_resolve_flow_event_kind(...)` | XAU 상단 sell scene 예외 |
| `btc_lower_buy_conservative_probe` 문맥 완화 | `_resolve_probe_visual_allowed(...)` | BTC 전용 probe scene 예외 |
| `nas_clean_confirm_probe` 문맥 완화 | `_resolve_probe_visual_allowed(...)` | NAS 전용 probe scene 예외 |
| `xau_second_support_probe_relief` 연동 | `_resolve_probe_visual_allowed(...)` | router override metadata와 연결된 특수 완화 |

원칙:

- Priority 1에서는 baseline을 먼저 빼고
- scene-specific 완화는 나중에 override table로 이동한다


## Priority 1에서 건드리지 않을 항목

이번 단계에서 일부러 제외하는 항목은 아래다.

| 항목 | 이유 |
| --- | --- |
| `_flow_event_signal_score(...)` | scoring은 Priority 2 |
| `_flow_event_color(...)` | wait brightness는 Priority 2 |
| `_FLOW_EVENT_COLORS` | base color 표준화는 Priority 3 |
| `_event_price(...)` | anchor 비율은 Priority 3 |
| compaction/priority 숫자 | 먼저 semantics/translation을 고정해야 함 |


## 구현 순서 제안

### Step 1. Policy 읽기 진입점 만들기

먼저 painter 안에서 공통 policy를 읽는 단일 진입점을 만든다.

예:

- `self._flow_policy()` 또는
- `self._get_common_expression_policy()`

이 단계에서는 로직을 바꾸지 않고 현재 default를 그대로 반환해도 된다.


### Step 2. `translation` 항목 이관

다음 항목부터 policy로 바꾼다.

- neutral block guards
- structural wait recovery guards/reasons
- watch suffix
- conflict prefix
- probe promotion gate neutralization
- edge-pair fallback
- scene-side fallback

이 단계의 목표:

- `_resolve_flow_event_kind(...)`
- `_resolve_blocked_structural_wait(...)`
- `_resolve_flow_observe_side(...)`

세 함수에서 baseline 하드코딩을 없애는 것


### Step 3. `semantics` 항목 이관

다음으로 semantics 토글을 policy로 뺀다.

- directional wait enabled
- soft block downgrades ready
- structural wait recovery enabled
- flat exit suppression enabled
- terminal exit requires position

이 단계의 목표:

- event family 의미는 유지하되, baseline 토글이 코드 본문에 박혀 있지 않게 만들기


### Step 4. `probe` baseline 이관

마지막으로 probe 관련 baseline을 옮긴다.

- upper/lower min support
- upper/lower min pair gap
- promotion gate penalties
- blocked quick states

중요:

- 이 단계에서는 symbol scene 예외를 건드리지 않는다
- 공통 기준만 policy로 빼고, 예외는 if block에 그대로 남겨둔다


## 완료 기준

Priority 1은 아래 조건을 만족하면 완료로 본다.

1. `_resolve_flow_event_kind(...)`의 baseline 번역 규칙이 policy를 읽는다
2. `_resolve_blocked_structural_wait(...)`의 guard/reason 기준이 policy를 읽는다
3. `_resolve_flow_observe_side(...)`의 fallback 기준이 policy를 읽는다
4. `_resolve_probe_visual_allowed(...)`의 공통 min support/gap 기준이 policy를 읽는다
5. symbol-specific scene 예외는 여전히 분리 가능한 hook로 남아 있다


## 구현 후 바로 확인할 테스트 포인트

Priority 1 반영 후에는 최소 아래를 다시 확인해야 한다.

- blocked middle buy wait가 `BUY_WAIT`로 유지되는지
- blocked lower structural rebound가 `BUY_WAIT`로 유지되는지
- soft-blocked sell ready가 `SELL_WAIT`로 낮춰지는지
- probe promotion gate가 neutral wait로 눌리는지
- flat 상태에서 exit 계열이 painter에서 무시되는지


## 한 줄 결론

Painter Priority 1의 핵심은
`색이나 위치를 손보기 전에, event family 번역 규칙과 probe baseline을 policy로 빼는 것`이다.
