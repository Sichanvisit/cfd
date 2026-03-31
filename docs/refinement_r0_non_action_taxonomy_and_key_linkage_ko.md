# R0 Non-Action Taxonomy and Key Linkage

## 1. 목적

이 문서는 R0의 `Step 3 non-action taxonomy`와 `Step 4 storage/key 연결 점검`을 고정하는 문서다.

관련 문서:

- [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)
- [refinement_r0_owner_matrix_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_owner_matrix_casebook_ko.md)


## 2. Row-Only Interpretation Order

runtime row 하나만 보고 non-action을 읽을 때 권장 순서는 아래와 같다.

1. `observe_reason`
2. `blocked_by`
3. `action_none_reason`
4. `quick_trace_state` / `probe_state`
5. `entry_probe_plan_v1`
6. `semantic_live_reason` / `semantic_live_fallback_reason`

이 순서의 의미는 이렇다.

- `observe_reason`
  - 어떤 semantic/observe 문맥이 잡혔는가
- `blocked_by`
  - 어떤 guard 또는 gate가 action을 막았는가
- `action_none_reason`
  - 최종 non-action 라벨은 무엇인가
- `quick_trace_state`
  - 현재 branch가 `BLOCKED`, `PROBE_WAIT`, `PROBE_READY` 중 어디에 있는가
- `entry_probe_plan_v1`
  - probe candidate는 살아 있는가, ready로 승격됐는가
- `semantic_live_reason`
  - semantic runtime이 왜 live 개입을 했거나 하지 않았는가


## 3. Non-Action Taxonomy

### 3-1. Semantic Observe Wait

판정 기준:

- `action_none_reason=observe_state_wait`

주로 같이 보이는 필드:

- `blocked_by=barrier_guard`
- `blocked_by=middle_sr_anchor_guard`
- `observe_reason=middle_sr_anchor_required_observe`
- `observe_reason=upper_break_fail_confirm`
- `quick_trace_state=BLOCKED`

해석:

- observe 문맥은 잡혔지만 confirm/action으로 승격되기엔 아직 이르다.
- probe promotion miss와 섞지 않는다.


### 3-2. Probe Not Promoted

판정 기준:

- `action_none_reason=probe_not_promoted`

주로 같이 보이는 필드:

- `blocked_by=probe_promotion_gate`
- `blocked_by=forecast_guard`
- `quick_trace_state=PROBE_WAIT`
- `entry_probe_plan_v1.active=true`
- `entry_probe_plan_v1.ready_for_entry=false`

해석:

- probe candidate는 살아 있다.
- 하지만 forecast/pair_gap/readiness가 부족해 entry plan이 wait에 남았다.


### 3-3. Confirm Suppressed

판정 기준:

- `action_none_reason=confirm_suppressed`
- `blocked_by=layer_mode_confirm_suppressed`

해석:

- confirm semantic은 있었지만 layer mode policy가 confirm을 observe/wait로 눌렀다.
- 이는 `probe_not_promoted`와 다른 계층의 이유다.


### 3-4. Execution Soft Blocked

판정 기준:

- `action_none_reason=execution_soft_blocked`
- `blocked_by=energy_soft_block`

해석:

- semantic non-action이 아니라 execution block이다.
- action readiness나 forecast drag 때문에 실제 진입을 막았다.


### 3-5. Policy Hard Blocked

판정 기준:

- `action_none_reason=policy_hard_blocked`
- `blocked_by=layer_mode_policy_hard_block`

해석:

- 명시적 정책 hard block이다.
- `execution_soft_blocked`보다 강한 차단이다.


### 3-6. Default Side Blocked / Position Lock

판정 기준:

- `action_none_reason=default_side_blocked`
- 또는 `action_none_reason=opposite_position_lock`

해석:

- semantic 문맥보다 consumer/action 단계에서 최종 차단된 경우다.


## 4. Semantic Inactive Interpretation

`semantic inactive`는 core non-action과 같은 질문이 아니다.

row에서 아래 필드를 함께 본다.

- `semantic_live_rollout_mode`
- `semantic_live_reason`
- `semantic_live_fallback_reason`
- `semantic_shadow_compare_label`

대표 예:

- `fallback=baseline_no_action`
  - baseline이 이미 non-action이라 semantic live가 개입하지 않음
- `fallback=symbol_not_in_allowlist`
  - semantic live 운영 정책상 현재 심볼은 비활성

즉 semantic inactive는 `blocked_by`가 아니라 운영/rollout 정책 해석에 가깝다.


## 5. Key Linkage Contract

R0 관점에서 key 3종의 역할은 아래처럼 분리한다.

| 키 | 역할 | reason triplet 포함 여부 | 해석 |
| --- | --- | --- | --- |
| `decision_row_key` | sparse wait/non-action row 식별 | 포함 가능 | non-action reason을 dataset/replay에서 잃지 않기 위한 키 |
| `runtime_snapshot_key` | runtime signal 앵커 식별 | 포함하지 않음 | signal 시점과 hint를 묶는 키 |
| `trade_link_key` | 실제 포지션/체결 연결 | 포함하지 않음 | ticket/symbol/direction/open_ts 중심의 execution linkage |

핵심 원칙:

- `decision_row_key`만 reason-bearing key다.
- `runtime_snapshot_key`는 reason을 담지 않는다.
- `trade_link_key`도 reason을 담지 않는다.


## 6. 현재 코드 기준 연결 구조

### decision_row_key

위치:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

현재 suffix 후보:

- `decision_time`
- `observe_reason`
- `probe_state`
- `blocked_by`
- `action_none_reason`

의미:

- sparse wait/non-action row를 replay/export에서 충돌 없이 식별한다.


### runtime_snapshot_key

위치:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

현재 구성:

- `symbol`
- `anchor_field`
- `anchor_value`
- `hint`

의미:

- runtime signal 시점과 next action hint를 식별한다.
- non-action reason을 넣지 않는다.


### trade_link_key

위치:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

현재 구성:

- `ticket`
- `symbol`
- `direction`
- `open_ts`

의미:

- 실제 open trade 또는 closed trade와 연결하는 execution key다.
- observe/block/non-action reason을 넣지 않는다.


## 7. Export / Replay 기대 동작

- export parquet/CSV에는
  - `observe_reason`
  - `blocked_by`
  - `action_none_reason`
  - `decision_row_key`
  - `runtime_snapshot_key`
  - `trade_link_key`
  - `replay_row_key`
  가 함께 존재해야 한다.
- replay intermediate는 `decision_row_key == replay_row_key`를 우선 기본으로 본다.
- non-action 해석은 열 기반으로 하고, key는 join/identity를 보조하는 역할로만 본다.


## 8. 현재 결론

- Step 3에서는 `row-only interpretation order`와 `non-action taxonomy`가 고정됐다.
- Step 4에서는 `decision_row_key`만 reason-bearing key이고, `runtime_snapshot_key / trade_link_key`는 linkage key라는 역할 분리가 고정됐다.

즉 R0 관점에서 남은 일은 taxonomy 자체보다, 이 계약이 runtime/export/replay 전 구간에서 계속 유지되는지 확인하는 정도다.
