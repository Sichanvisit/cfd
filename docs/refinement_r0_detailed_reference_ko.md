# R0 상세 기준 문서

작성일: 2026-03-29 (KST)

## 1. 목적

이 문서는 기존 R0 문서들을 덮어쓰는 문서가 아니라,
아래 문서들을 현재 시점 기준으로 다시 묶어서
`R0가 정확히 무엇이었고`, `왜 지금도 중요한지`, `현재 코드와 테스트 기준으로 어디까지 살아 있는지`
한 장에서 볼 수 있게 만든 상세 기준 문서다.

관련 원문:

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)
- [refinement_r0_owner_matrix_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_owner_matrix_casebook_ko.md)
- [refinement_r0_non_action_taxonomy_and_key_linkage_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_non_action_taxonomy_and_key_linkage_ko.md)
- [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- [refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md)


## 2. R0를 한 문장으로 말하면

R0는 `진입하지 않은 이유`, `막힌 이유`, `probe가 승격되지 않은 이유`,
`semantic runtime이 개입하지 않은 이유`를
row 하나만 보고도 설명할 수 있게 만든
`정합성 최소셋` 단계다.

즉 R0는 튜닝 단계가 아니라
이후 모든 refinement와 forensic이 믿고 설 수 있게 만든
`해석 기준선`이다.


## 3. 지금 시점에서 R0가 왜 다시 중요한가

현재 프로젝트는 이미 R1~R4, S0~S6까지 많은 진척이 있었고,
지금 남은 핵심은 `실제 entry timing 품질`을 체결 기준으로 다시 보는 일이다.

하지만 이 작업도 결국 시작은 row 해석이다.

즉 아래 질문은 여전히 R0 규칙으로 읽어야 한다.

- 왜 이 row는 observe에 머물렀는가
- 왜 이 row는 blocked 되었는가
- 왜 probe candidate가 ready_for_entry로 승격되지 않았는가
- 왜 semantic live가 비활성이었는가
- 이 row를 replay/export/trade history와 어떻게 정확히 잇는가

그래서 R0는 과거 완료 단계이면서도,
현재 R0-B actual entry forensic의 시작점으로 다시 쓰인다.


## 4. R0의 범위와 비범위

### 4-1. 포함 범위

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_candidate_v1`
- `entry_probe_plan_v1`
- semantic canary report
- semantic runtime activation reason
- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`

### 4-2. 비포함 범위

- `Position / Response / State / Evidence / Belief / Barrier` 재설계
- Stage E 수치 튜닝
- symbol override 조정
- semantic target/split 재정의
- chart display ladder 자체의 시각 튜닝

즉 R0는 `무엇을 더 잘 보이게 할지`가 아니라
`무슨 일이 일어났는지 왜 그런지 잃지 않게 만들기`에 집중한다.


## 5. R0의 핵심 질문 4개

R0는 아래 질문에 row 기준으로 답할 수 있게 만드는 단계다.

1. 왜 observe인가
2. 왜 blocked인가
3. 왜 probe가 승격되지 않았는가
4. 왜 semantic runtime이 inactive인가

이 네 질문이 즉시 풀리지 않으면,
이후 R1 이상의 튜닝이나 R0-B forensic도 쉽게 왜곡된다.


## 6. R0의 핵심 owner 분리

R0에서 가장 중요한 건 `reason triplet`을 서로 다른 owner로 보는 것이다.

| 필드 | 질문 | owner |
|---|---|---|
| `observe_reason` | 왜 observe/confirm 문맥이 형성됐는가 | semantic / observe owner |
| `blocked_by` | 무엇이 즉시 action을 막았는가 | guard / gate / execution block owner |
| `action_none_reason` | 최종적으로 왜 non-action 결과가 났는가 | consumer / action result owner |

핵심 원칙:

- `observe_reason`는 문맥 설명이다.
- `blocked_by`는 즉시 차단 원인이다.
- `action_none_reason`는 최종 결과 라벨이다.
- 세 필드는 서로 대체재가 아니다.

이 분리가 무너지면,
row 하나를 보고도 "왜 안 들어갔는지"가 모호해진다.


## 7. Row-Only Interpretation Order

runtime row 하나만 보고 non-action을 읽을 때 권장 순서는 아래다.

1. `observe_reason`
2. `blocked_by`
3. `action_none_reason`
4. `quick_trace_state` / `probe_state`
5. `entry_probe_plan_v1`
6. `semantic_live_reason` / `semantic_live_fallback_reason`

이 순서를 지켜야 하는 이유는 간단하다.

- 먼저 semantic 문맥을 본다
- 그 다음 즉시 차단 원인을 본다
- 그 다음 최종 non-action 결과를 본다
- 그 다음 branch 상태와 probe plan을 본다
- 마지막에 semantic live 운영 이유를 본다

즉 `semantic inactive`는 core non-action과 같은 질문이 아니라
운영/rollout 해석에 가깝다.


## 8. R0 Non-Action Taxonomy

R0에서 최소한 구분되어야 하는 non-action family는 아래와 같다.

| 분류 | 대표 `action_none_reason` | 대표 `blocked_by` | 해석 |
|---|---|---|---|
| Semantic Observe Wait | `observe_state_wait` | `barrier_guard`, `middle_sr_anchor_guard` 등 | observe 문맥은 있으나 action으로 승격되기 이르다 |
| Probe Not Promoted | `probe_not_promoted` | `probe_promotion_gate`, `forecast_guard` | probe candidate는 살아 있으나 entry plan이 아직 wait에 남았다 |
| Confirm Suppressed | `confirm_suppressed` | `layer_mode_confirm_suppressed` | confirm semantic은 있었지만 policy가 눌렀다 |
| Execution Soft Blocked | `execution_soft_blocked` | `energy_soft_block` | semantic non-action이 아니라 execution block이다 |
| Policy Hard Blocked | `policy_hard_blocked` | `layer_mode_policy_hard_block` | 명시적 hard block이다 |
| Default Side Blocked / Position Lock | `default_side_blocked`, `opposite_position_lock` | 상황별 | consumer/action 단계 차단이다 |

이 taxonomy가 있어야
`안 들어감`이라는 한 단어를
서로 다른 종류의 실패/대기로 구분할 수 있다.


## 9. Probe Promotion Miss를 왜 따로 봐야 하는가

R0는 단순 blocked taxonomy만이 아니라
`probe_candidate_v1.active=true`인데
`entry_probe_plan_v1.ready_for_entry=false`인 케이스를
별도 casebook으로 분리하는 단계다.

이 구간이 중요한 이유는:

- 후보는 살아 있었는지
- plan까지는 갔는지
- plan이 왜 ready로 못 올라갔는지

를 나눠 보지 않으면
`좋은 장면을 너무 빨리 죽였는지`
혹은
`원래 승격되면 안 되는 장면이었는지`
를 구분할 수 없기 때문이다.


## 10. Key Linkage Contract

R0에서 key 3종의 역할 분리는 아래처럼 고정된다.

| 키 | 역할 | reason 포함 여부 | 해석 |
|---|---|---|---|
| `decision_row_key` | sparse wait/non-action row 식별 | 포함 가능 | reason-bearing key |
| `runtime_snapshot_key` | runtime signal 앵커 식별 | 포함하지 않음 | linkage key |
| `trade_link_key` | 실제 trade/체결 연결 | 포함하지 않음 | execution linkage key |

핵심 원칙:

- `decision_row_key`만 reason-bearing key다.
- `runtime_snapshot_key`는 reason을 담지 않는다.
- `trade_link_key`도 reason을 담지 않는다.

이 구분이 있어야
join 키와 설명 키를 혼동하지 않는다.


## 11. 코드 owner와 현재 기준 구현 위치

### 11-1. Entry / reason triplet / probe plan owner

핵심 파일:

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)

현재 코드 기준 중요한 지점:

- `observe_reason`, `blocked_by`, `action_none_reason` snapshot 정리
- `entry_probe_plan_v1` 생성
- `probe_candidate_v1` observe metadata 수집
- `probe_not_promoted`, `policy_hard_blocked`, `confirm_suppressed`, `execution_soft_blocked`를 분리 기록

대표 근거:

- `probe_promotion_gate -> probe_not_promoted`
- `layer_mode_policy_hard_block -> policy_hard_blocked`
- `layer_mode_confirm_suppressed -> confirm_suppressed`
- `energy_soft_block -> execution_soft_blocked`

### 11-2. Storage / compaction / key linkage owner

핵심 파일:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [r0_row_interpretation.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\r0_row_interpretation.py)

현재 코드 기준 중요한 지점:

- `observe_reason`, `blocked_by`, `action_none_reason` compact/hot payload 보강
- `r0_non_action_family`, `r0_semantic_runtime_state`, `r0_row_interpretation_v1` compact/hot payload 보강
- quick trace source에 reason triplet 유지
- `resolve_entry_decision_row_key()`에서 reason suffix 반영
- `resolve_trade_link_key()` 분리

### 11-3. Semantic canary owner

핵심 파일:

- [check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\scripts\check_semantic_canary_rollout.py)

현재 코드 기준 중요한 지점:

- `build_canary_report(...)`
- `write_canary_report(...)`
- `window_start`
- `semantic_live_reason_counts`
- `now=` 주입 기반 deterministic recent-window 계산


## 12. 테스트 기준 현재 상태

2026-03-29 기준 현재 확인 결과는 아래와 같다.

### 12-1. R0 인접 핵심 축

- canary / consumer / chart / entry / runtime / replay / outcome / semantic_v1 관련 핵심 테스트 묶음은 통과
- 전체 unit suite는 현재 `1106 passed`

### 12-2. R0 관점에서 긍정적 의미

- canary recent-window 테스트는 현재 살아 있다
- entry_service 가드 분류 계약도 현재 살아 있다
- storage compaction / replay / dataset 계열 계약도 전체 suite 기준 깨지지 않았다

### 12-3. 남아 있는 인접 리스크

전체 suite의 남은 1건 실패는
과거에는 observe/confirm routing 축에 남은 red test가 있었지만,
현재는 그 이슈도 해소된 상태다.
현재 R0-B actual entry forensic과 맞닿은 인접 리스크다.

실패 케이스:

- [test_energy_observe_engine.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_energy_observe_engine.py)
- lower-box / BUY_ONLY 문맥인데 `upper_reject_sell` 쪽 archetype이 라우팅되는 케이스

의미:

- R0 reason triplet은 꽤 안정적이지만,
  upstream semantic routing 한 케이스는 아직 더 확인이 필요하다


## 13. R0에서 실제로 완료된 것

현재 문서와 코드 기준으로 보면
R0는 이미 아래 수준까지는 완료된 상태로 보는 것이 맞다.

- owner matrix 정리
- probe promotion miss casebook 정리
- non-action taxonomy 정리
- decision/runtime/trade key linkage 역할 분리
- semantic canary recent-window 안정화

즉 R0는 아직 설계만 있는 상태가 아니라
이미 시스템 전체의 해석 바닥으로 기능하고 있다.


## 14. 하지만 R0가 끝났다고 해서 잊으면 안 되는 것

R0는 완료된 phase이지만,
아래 상황에서 계속 재사용해야 한다.

- 최근 adverse entry forensic
- late block / wrong ready / scene mismatch 해석
- replay/export/dataset join 문제 확인
- semantic inactive 운영 이유 해석

즉 R0는 완료 단계이면서 동시에
`문제 해결용 해석 사전` 역할을 한다.


## 15. 현재 기준 R0의 실제 활용법

최근 체결 또는 non-action row를 볼 때는 아래 순서가 가장 빠르다.

1. `observe_reason`
2. `blocked_by`
3. `action_none_reason`
4. `quick_trace_state`
5. `entry_probe_plan_v1`
6. `consumer_check_stage`
7. `semantic_live_reason / semantic_live_fallback_reason`
8. `decision_row_key / runtime_snapshot_key / trade_link_key`

즉:

- semantic 문맥을 먼저 보고
- 차단 원인을 보고
- 최종 결과를 보고
- probe plan과 consumer stage를 본 뒤
- 마지막에 운영/rollout과 key linkage를 본다


## 16. R0 관점의 done definition

현재 시점에서 R0를 "유지 완료" 상태로 보기 위한 기준은 아래다.

- reason triplet의 owner 분리가 코드/row/compact/export에서 계속 유지된다
- probe promotion miss가 `other/missing-reason`으로 뭉개지지 않는다
- `decision_row_key`가 sparse wait/non-action reason을 잃지 않는다
- canary recent-window 테스트가 날짜 변화에 흔들리지 않는다
- 실제 forensic 시 R0 해석 순서로 최근 row를 설명할 수 있다


## 17. 한 줄 결론

R0는 지나간 초반 단계가 아니라,
지금도 시스템을 읽고 문제를 추적하는 데 쓰이는
`해석과 정합성의 기준선`이다.
