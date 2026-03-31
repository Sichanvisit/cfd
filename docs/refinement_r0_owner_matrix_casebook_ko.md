# R0 Owner Matrix and Probe Promotion Casebook

## 1. 목적

이 문서는 R0의 `Step 1 owner matrix`와 `Step 2 probe promotion miss casebook`을 실제 운영 row와 테스트 계약 기준으로 고정한 기록 문서다.

기준 문서:

- [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)


## 2. 샘플 기준

현재 스냅샷은 아래 기준으로 정리했다.

- live row source:
  - [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- sampling window:
  - 2026-03-25 KST 기준 recent tail 200~400 rows
- contract-backed source:
  - [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)
  - [test_storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_storage_compaction.py)

즉 이 문서는 `live에서 실제로 최근 관찰된 케이스`와 `코드가 반드시 보장해야 하는 계약 케이스`를 같이 묶는다.


## 3. Owner Matrix

| 필드 | 주 질문 | primary producer | key/replay 해석 우선순위 | 현재 해석 |
| --- | --- | --- | --- | --- |
| `observe_reason` | 왜 observe/confirm 문맥이 형성됐는가 | `entry_service._core_action_decision()` | row `observe_reason` -> `entry_decision_result_v1.metrics.observe_reason` -> `observe_confirm.reason` | semantic / observe owner |
| `blocked_by` | 무엇이 즉시 action을 막았는가 | `entry_service._core_action_decision()` | row `blocked_by` -> `entry_decision_result_v1.blocked_by` -> `entry_decision_result_v1.metrics.blocked_by` | gate / block owner |
| `action_none_reason` | 최종적으로 왜 non-action인가 | `entry_service._core_action_decision()` | row `action_none_reason` -> `entry_decision_result_v1.metrics.action_none_reason` | consumer result owner |
| `probe_candidate_v1` | probe 후보가 살아 있었는가 | observe metadata / router handoff | row payload 직접 해석 | observe-side probe owner |
| `entry_probe_plan_v1` | probe 후보가 실제 entry plan으로 승격됐는가 | `entry_service` planning branch | row payload 직접 해석 | entry planning owner |
| `semantic_live_reason` | semantic runtime이 왜 live 적용/비적용됐는가 | semantic runtime adapter / rollout path | row field 직접 해석 | semantic runtime owner |

핵심 원칙:

- `observe_reason`는 문맥 설명이다.
- `blocked_by`는 차단 가드다.
- `action_none_reason`는 최종 non-action 라벨이다.
- 세 필드는 같은 뜻이 아니라 서로 다른 질문에 답한다.


## 4. 최근 live 스냅샷 요약

recent tail 200 rows 기준 분포는 아래처럼 보였다.

### action_none_reason

| 값 | 건수 |
| --- | ---: |
| `observe_state_wait` | 168 |
| `probe_not_promoted` | 36 |

### blocked_by

| 값 | 건수 |
| --- | ---: |
| `barrier_guard` | 68 |
| `middle_sr_anchor_guard` | 39 |
| `probe_promotion_gate` | 26 |
| `forecast_guard` | 9 |

즉 현재 live tail에서는 `observe_state_wait`와 `probe_not_promoted`가 R0 관점의 주된 non-action 패턴이다.


## 5. Live Row Owner Examples

### Example A. BTC barrier wait

| 필드 | 값 |
| --- | --- |
| `time` | `2026-03-25T22:09:52` |
| `symbol` | `BTCUSD` |
| `observe_reason` | `upper_break_fail_confirm` |
| `blocked_by` | `barrier_guard` |
| `action_none_reason` | `observe_state_wait` |
| `quick_trace_state` | `BLOCKED` |
| `probe_plan_reason` | `probe_candidate_inactive` |
| `semantic_live_fallback_reason` | `baseline_no_action` |

해석:

- observe 문맥은 형성됐다.
- 즉시 차단 원인은 `barrier_guard`다.
- 최종 non-action은 `observe_state_wait`다.
- semantic runtime도 별도 fallback reason을 남기므로, semantic inactive와 core non-action은 분리해서 읽어야 한다.


### Example B. NAS middle sr anchor wait

| 필드 | 값 |
| --- | --- |
| `time` | `2026-03-25T22:09:57` |
| `symbol` | `NAS100` |
| `observe_reason` | `middle_sr_anchor_required_observe` |
| `blocked_by` | `middle_sr_anchor_guard` |
| `action_none_reason` | `observe_state_wait` |
| `quick_trace_state` | `BLOCKED` |
| `probe_plan_reason` | `probe_candidate_inactive` |
| `semantic_live_fallback_reason` | `symbol_not_in_allowlist` |

해석:

- semantic/observe owner는 `middle_sr_anchor_required_observe`
- gate owner는 `middle_sr_anchor_guard`
- consumer 결과는 `observe_state_wait`
- semantic live fallback은 별도 운영 정책 이유다


## 6. Probe Promotion Miss Casebook

### Case P1. XAU upper sell probe forecast wait

| 필드 | 값 |
| --- | --- |
| `time` | `2026-03-25T22:10:25` |
| `symbol` | `XAUUSD` |
| `observe_reason` | `upper_reject_probe_observe` |
| `blocked_by` | `forecast_guard` |
| `action_none_reason` | `probe_not_promoted` |
| `quick_trace_state` | `PROBE_WAIT` |
| `probe_plan_reason` | `probe_forecast_not_ready` |
| `probe_scene_id` | `xau_upper_sell_probe` |
| `probe_candidate_support` | `0.1886052552524254` |
| `probe_pair_gap` | `0.06333546877897003` |

해석:

- observe 문맥과 probe candidate는 살아 있다.
- 하지만 forecast readiness가 부족해서 entry probe plan이 wait에 남는다.
- 이 경우 `blocked_by=forecast_guard`, `action_none_reason=probe_not_promoted`를 함께 읽어야 한다.


### Case P2. NAS clean confirm probe promotion gate

| 필드 | 값 |
| --- | --- |
| `time` | `2026-03-25T22:10:32` |
| `symbol` | `NAS100` |
| `observe_reason` | `upper_reject_probe_observe` |
| `blocked_by` | `probe_promotion_gate` |
| `action_none_reason` | `probe_not_promoted` |
| `quick_trace_state` | `PROBE_WAIT` |
| `probe_plan_reason` | `probe_forecast_not_ready` |
| `probe_scene_id` | `nas_clean_confirm_probe` |
| `probe_candidate_support` | `0.17359383694534805` |
| `probe_pair_gap` | `0.04338589300323484` |

해석:

- candidate는 있지만 promotion gate를 못 넘었다.
- `forecast_guard`와 달리 이 케이스는 명시적으로 `probe_promotion_gate`가 남아 있다.
- 같은 `probe_not_promoted`라도 어떤 guard가 먼저 보이는지 구분해서 봐야 한다.


### Case P3. BTC observe wait without active probe

| 필드 | 값 |
| --- | --- |
| `time` | `2026-03-25T22:10:02` |
| `symbol` | `BTCUSD` |
| `observe_reason` | `upper_break_fail_confirm` |
| `blocked_by` | `barrier_guard` |
| `action_none_reason` | `observe_state_wait` |
| `quick_trace_state` | `BLOCKED` |
| `probe_plan_reason` | `probe_candidate_inactive` |

해석:

- 이 케이스는 probe promotion miss가 아니라, probe candidate 자체가 inactive인 observe wait다.
- 따라서 `probe_not_promoted` 케이스와 섞으면 안 된다.


## 7. Contract-Backed Categories Not Seen in Recent Tail

최근 live tail에는 아래 범주가 대표적으로 보이지 않았지만, 코드 계약상 반드시 분리되어야 한다.

| 분류 | 기대 blocked_by | 기대 action_none_reason | 현재 근거 |
| --- | --- | --- | --- |
| confirm suppression | `layer_mode_confirm_suppressed` | `confirm_suppressed` | [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py) + unit test |
| execution soft block | `energy_soft_block` | `execution_soft_blocked` | [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py) |
| policy hard block | `layer_mode_policy_hard_block` | `policy_hard_blocked` | [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py) |

즉 R0 casebook은 `live 샘플 + contract 샘플`을 같이 봐야 완성된다.


## 8. 현재 결론

- Step 1 owner matrix는 현재 코드/row 기준으로 해석 가능하다.
- Step 2 casebook은 live row 기준으로 `observe_state_wait`, `probe_not_promoted`가 먼저 채워졌다.
- `confirm_suppressed`, `execution_soft_blocked`, `policy_hard_blocked`는 현재 contract-backed 항목으로 유지한다.

즉 R0의 다음 남은 중심은 `Step 3 non-action taxonomy`를 이 matrix와 casebook 위에 고정하는 것이다.
