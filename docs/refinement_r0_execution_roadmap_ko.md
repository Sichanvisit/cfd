# R0 구현 로드맵

작성일: 2026-03-29 (KST)

## 1. 목적

이 문서는 R0를 처음 구현하는 계획서가 아니라,
현재 완료된 R0를 기준으로
`어떻게 유지 확인하고`, `현재 문제 해결에 다시 연결하고`,
`필요한 보강을 어떤 순서로 할지`를 정리한 실행 로드맵이다.

즉 이 문서는 아래 두 상황에 모두 쓰인다.

- 새 스레드에서 R0를 다시 이해해야 할 때
- 현재 R0-B actual entry forensic이나 P0 추적성 보강을 시작할 때

관련 기준 문서:

- [refinement_r0_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_detailed_reference_ko.md)
- [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- [refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md)
- [refinement_r0_b6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)
- [decision_log_coverage_gap_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
- [decision_log_coverage_gap_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_execution_roadmap_ko.md)
- [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)
- [external_advice_synthesis_and_master_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\external_advice_synthesis_and_master_roadmap_ko.md)


## 2. 현재 상태 요약

현재 판단은 아래처럼 잡는 것이 맞다.

- R0는 이미 완료된 단계다
- 하지만 R0-B actual entry forensic을 위해 R0를 다시 실전 기준으로 써야 한다
- 즉 새 구현보다 `R0 해석 기준선 재고정 + 현재 row/체결에 대한 적용`이 먼저다

현재 기준 핵심 현실:

- reason triplet과 key linkage는 이미 상당 부분 고정돼 있다
- canary recent-window도 안정화돼 있다
- 다만 현재 현장 문제는 `scene display`보다 `실제 entry timing 품질`이다
- 따라서 R0는 과거 문서가 아니라 현재 forensic의 출발점이다


## 3. 이번 로드맵에서 할 것과 하지 않을 것

### 할 것

- R0 source-of-truth 재정렬
- reason triplet / key linkage / canary 상태 재확인
- recent adverse entry forensic에 R0 해석 표준 적용
- 누락된 trace / 문서 / 테스트 보강 포인트 식별

### 하지 않을 것

- Stage E 재튜닝
- symbol override 재조정
- chart ladder 시각 재설계
- semantic target/split 재설계
- closed-loop adaptation 구현


## 4. 전체 실행 순서

이번 로드맵은 아래 다섯 블록으로 진행한다.

```text
R0-A 기준선 확인
-> R0-B row 해석/forensic 연결
-> R0-C key linkage 검증
-> R0-D canary / runtime reasoning 재검증
-> R0-E close-out + P0 handoff
```


## 5. R0-A. 기준선 확인

목표:

- 현재 코드와 테스트 기준으로 R0 핵심 계약이 여전히 살아 있는지 확인한다

대상:

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\scripts\check_semantic_canary_rollout.py)
- [test_entry_service_guards.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)
- [test_storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_storage_compaction.py)
- [test_check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_check_semantic_canary_rollout.py)

확인 질문:

- `observe_reason / blocked_by / action_none_reason` owner 분리가 유지되는가
- `probe_not_promoted / confirm_suppressed / execution_soft_blocked / policy_hard_blocked` 분리가 유지되는가
- `decision_row_key`가 여전히 reason-bearing key로 기능하는가
- canary recent-window 계산이 deterministic한가

완료 기준:

- R0 기준선 상태를 한 번에 요약한 메모가 있다
- 현재 깨진 계약이 있으면 바로 backlog에 등록된다


## 6. R0-B. Row 해석 표준을 현재 forensic에 연결

목표:

- 현재 남아 있는 actual entry timing 문제를 R0 해석 순서로 읽게 만든다

핵심 이유:

- 지금 남은 핵심 문제는 "실제 entry 직후 adverse move"
- 이걸 잡으려면 display 감각이 아니라 row interpretation 표준이 먼저 필요하다

작업:

- 최근 손실 / 짧은 보유 청산 체결 추출
- 직전 [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) row와 매칭
- 아래 필드로 forensic 테이블 생성

필수 열:

- `symbol`
- `time`
- `setup_id`
- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `quick_trace_state`
- `entry_probe_plan_v1.ready_for_entry`
- `consumer_check_stage`
- `consumer_check_entry_ready`
- `trade_link_key`
- `decision_row_key`

완료 기준:

- 최근 adverse entry 케이스를 공통 family로 묶을 수 있다
- 최소 1회 이상 "어떤 family가 왜 잘못 열렸는가"를 R0 언어로 설명할 수 있다


## 7. R0-C. Key Linkage 검증

목표:

- forensic에 필요한 row 연결이 실제로 끊기지 않는지 다시 확인한다

봐야 할 키:

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`
- `replay_row_key`

핵심 점검:

- entered row에서 `trade_link_key`가 forensic 추적에 충분한가
- sparse wait/non-action row에서 `decision_row_key`가 reason 추적에 충분한가
- replay/export로 넘어가도 동일 해석이 가능한가

완료 기준:

- 실제 adverse entry sample 3건 이상에서 key linkage가 설명 가능하다
- linkage gap이 있으면 actual entry forensic backlog가 아니라 R0 보강 항목으로 분리된다


## 8. R0-D. Canary / Runtime Reasoning 재검증

목표:

- semantic inactive와 fallback reason을 현재 운영 언어로 다시 확인한다

작업:

- canary report latest window 확인
- `semantic_live_reason_counts`
- `semantic_live_fallback_reason`
- `window_start`
- allowlist / mode 상태와 recent row 해석 연결

의도:

- row non-action과 semantic inactive를 혼동하지 않게 한다
- forensic 도중 `baseline_no_action`, `symbol_not_in_allowlist` 같은 운영 이유를 core block처럼 오해하지 않게 한다

완료 기준:

- semantic inactive를 blocked_by와 다른 층으로 설명 가능하다
- canary report를 row forensic과 같은 언어로 읽을 수 있다


## 9. R0-E. Close-Out과 상위 단계 handoff

목표:

- R0를 다시 정리한 결과를 P0로 자연스럽게 넘긴다

R0-B 실행 결과로 남길 것:

- adverse entry forensic 테이블
- 공통 family 후보
- guard 누수 후보
- 실제로 수정해야 할 gate 후보

P0로 넘길 것:

- decision trace에 꼭 들어가야 할 R0 필드
- legacy scorer ↔ semantic ownership 로그에 필요한 최소 필드
- ContextClassifier 분해 시 유지해야 할 reason ownership 규칙

완료 기준:

- R0가 과거 문서가 아니라 현재 문제 해결 입력으로 다시 연결된다


## 10. 테스트 로드맵

### 10-1. 최소 확인

```powershell
python -m pytest tests/unit/test_check_semantic_canary_rollout.py -q
python -m pytest tests/unit/test_entry_service_guards.py -q
python -m pytest tests/unit/test_storage_compaction.py -q
```

### 10-2. R0 인접 회귀

```powershell
python -m pytest tests/unit/test_runtime_alignment_contract.py -q
python -m pytest tests/unit/test_consumer_scope_contract.py -q
python -m pytest tests/unit/test_entry_try_open_entry_policy.py -q
```

### 10-3. 현재 전역 기준선 메모

현재 전체 unit snapshot은 아래처럼 기록한다.

- `1106 passed`
- observe/confirm routing 인접 red test도 해소되어 현재 기준선은 green 상태
- R0 자체의 핵심 계약 테스트는 현재 크게 무너지지 않은 상태


## 11. 산출물 목록

이 로드맵이 끝나면 아래 산출물이 있어야 한다.

- R0 refresh note
- recent adverse entry forensic table
- key linkage audit note
- canary/runtime reasoning note
- R0-B action candidate list
- P0 trace/logging 요구사항 메모


## 12. 우선순위

현재 우선순위는 아래가 가장 자연스럽다.

1. R0-A 기준선 확인
2. R0-B adverse entry forensic 연결
3. R0-C key linkage 검증
4. R0-D canary/runtime reasoning 재검증
5. R0-E close-out + P0 handoff

이 순서가 좋은 이유:

- 먼저 현재 기준선을 확인하고
- 그 기준선을 실제 체결 forensic에 연결하고
- row 연결이 맞는지 확인한 뒤
- semantic inactive 같은 운영 이유를 다시 분리하고
- 마지막에 상위 단계로 넘기는 것이 가장 덜 흔들리기 때문이다


## 13. 한 줄 결론

이번 R0 로드맵의 목적은
R0를 다시 만드는 것이 아니라,
이미 만든 R0를 현재 actual entry timing 문제 해결에 다시 연결하고,
그 결과를 P0로 넘길 수 있게 만드는 것이다.
